from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.v1.dependencies import AuthContext, resolve_current_principal
from app.email_service import send_password_reset_email, send_verification_email
from app.limiter import limiter
from app.schemas import (
    EmailVerificationRequest,
    LoginMFARequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MFACodeRequest,
    MFARecoveryCodesResponse,
    MFASetupResponse,
    MFAVerifyRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    TokenPairResponse,
    User,
    UserPublic,
)
from app.security import (
    AccessTokenError,
    RefreshTokenClaims,
    RefreshTokenError,
    hash_mfa_recovery_code,
    hash_password,
    issue_access_token,
    issue_mfa_recovery_codes,
    issue_refresh_token,
    normalize_mfa_recovery_code,
    parse_refresh_token,
    verify_access_token,
)
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    payload: RegisterRequest,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
) -> RegisterResponse:
    tenant, user, _ = app_store.register(
        payload,
        settings.access_token_secret,
        settings.access_token_ttl_minutes,
    )

    from secrets import token_urlsafe

    verification_token_str = token_urlsafe(32)
    app_store.create_verification_token(
        user.id,
        verification_token_str,
        datetime.now(UTC) + timedelta(hours=24),
    )
    send_verification_email(user.email, verification_token_str)

    token_pair = _issue_token_pair(user, settings, app_store)
    app_store.create_audit_log(
        "auth.register",
        user_id=user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host if request.client else None,
    )
    return RegisterResponse(tenant=tenant, user=_public_user(user), **token_pair.model_dump())


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
) -> LoginResponse:
    result = app_store.login(
        str(payload.email),
        payload.password,
        settings.access_token_secret,
        settings.access_token_ttl_minutes,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    tenant, user, _token = result

    ip_address = request.client.host if request.client else None

    if user.totp_secret:
        # User has MFA enabled, token is just an intermediate token to pass to /login/mfa
        access_expires_at = datetime.now(UTC) + timedelta(minutes=5)
        intermediate_token = issue_access_token(
            tenant.id,
            user.id,
            settings.access_token_secret,
            ttl_minutes=5,
        )
        app_store.create_audit_log(
            "auth.login.mfa_required", user_id=user.id, tenant_id=tenant.id, ip_address=ip_address
        )
        return LoginResponse(
            access_token=intermediate_token,
            refresh_token="".join(()),
            access_expires_at=access_expires_at,
            refresh_expires_at=datetime.now(UTC),
            requires_mfa=True,
        )

    app_store.create_audit_log(
        "auth.login", user_id=user.id, tenant_id=tenant.id, ip_address=ip_address
    )
    token_pair = _issue_token_pair(user, settings, app_store)
    return LoginResponse(tenant=tenant, user=_public_user(user), **token_pair.model_dump())


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh(
    payload: RefreshTokenRequest,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
) -> RefreshTokenResponse:
    refresh_claims = _parse_refresh_or_unauthorized(payload.refresh_token, settings)
    new_session_id = uuid4()
    new_refresh_token, new_refresh_token_hash = issue_refresh_token(
        new_session_id,
        settings.access_token_secret,
    )
    refresh_expires_at = _refresh_expires_at(settings)
    session = app_store.rotate_auth_session(
        refresh_claims.session_id,
        refresh_claims.token_hash,
        new_session_id,
        new_refresh_token_hash,
        refresh_expires_at,
    )
    if session is None:
        raise _invalid_refresh_token()
    user = app_store.get_user(session.user_id)
    if user is None:
        raise _invalid_refresh_token()
    access_token = issue_access_token(
        session.tenant_id,
        session.user_id,
        settings.access_token_secret,
        ttl_minutes=settings.access_token_ttl_minutes,
    )
    access_expires_at = verify_access_token(access_token, settings.access_token_secret).expires_at
    app_store.create_audit_log(
        "auth.refresh",
        user_id=user.id,
        tenant_id=session.tenant_id,
    )
    return RefreshTokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
) -> Response:
    refresh_claims = _parse_refresh_or_unauthorized(payload.refresh_token, settings)
    if not app_store.revoke_auth_session(
        refresh_claims.session_id,
        refresh_claims.token_hash,
    ):
        raise _invalid_refresh_token()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserPublic)
async def get_current_user(
    auth_context: AuthContext = Depends(resolve_current_principal),
) -> UserPublic:
    return _public_user(auth_context.user)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(
    payload: EmailVerificationRequest,
    app_store: AppStore = Depends(get_app_store),
) -> Response:
    now = datetime.now(UTC)
    token = app_store.consume_verification_token(payload.token, now)
    if not token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if not app_store.verify_user_email(token.user_id):
        raise HTTPException(status_code=400, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/request-password-reset", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    payload: PasswordResetRequest,
    app_store: AppStore = Depends(get_app_store),
) -> Response:
    user = app_store.get_user_by_email(str(payload.email))
    if user:
        from secrets import token_urlsafe

        reset_token_str = token_urlsafe(32)
        app_store.create_password_reset_token(
            user.id,
            reset_token_str,
            datetime.now(UTC) + timedelta(hours=1),
        )
        send_password_reset_email(user.email, reset_token_str)
        app_store.create_audit_log(
            "auth.password_reset_requested",
            user_id=user.id,
            tenant_id=user.tenant_id,
            ip_address=request.client.host if request.client else None,
        )
    # Always return 204 to prevent email enumeration
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    payload: PasswordResetConfirmRequest,
    app_store: AppStore = Depends(get_app_store),
) -> Response:
    now = datetime.now(UTC)
    token = app_store.consume_password_reset_token(payload.token, now)
    if not token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    new_hash = hash_password(payload.new_password)
    if not app_store.update_user_password(token.user_id, new_hash):
        raise HTTPException(status_code=400, detail="User not found")
    
    app_store.create_audit_log(
        "auth.password_reset_completed",
        user_id=token.user_id,
        ip_address=request.client.host if request.client else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _issue_token_pair(
    user: User,
    settings: Settings,
    app_store: AppStore,
) -> TokenPairResponse:
    access_token = issue_access_token(
        user.tenant_id,
        user.id,
        settings.access_token_secret,
        ttl_minutes=settings.access_token_ttl_minutes,
    )
    access_expires_at = verify_access_token(access_token, settings.access_token_secret).expires_at
    session_id = uuid4()
    refresh_token, refresh_token_hash = issue_refresh_token(
        session_id,
        settings.access_token_secret,
    )
    refresh_expires_at = _refresh_expires_at(settings)
    app_store.create_auth_session(
        session_id,
        user.tenant_id,
        user.id,
        refresh_token_hash,
        refresh_expires_at,
    )
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )


def _refresh_expires_at(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)


def _parse_refresh_or_unauthorized(
    refresh_token: str,
    settings: Settings,
) -> RefreshTokenClaims:
    try:
        return parse_refresh_token(refresh_token, settings.access_token_secret)
    except RefreshTokenError as exc:
        raise _invalid_refresh_token() from exc


def _invalid_refresh_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error_code": "INVALID_REFRESH_TOKEN",
            "message": "Refresh token is invalid, expired, or revoked.",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/login/mfa", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login_mfa(
    request: Request,
    payload: LoginMFARequest,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
) -> LoginResponse:
    # The intermediate token is essentially a short-lived access token.
    try:
        claims = verify_access_token(payload.token, settings.access_token_secret)
    except AccessTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    user = app_store.get_user(claims.user_id)
    if not user or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not enabled")

    if not _verify_mfa_code(user, payload.code, settings, app_store, consume_recovery=True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
    user = app_store.get_user(user.id) or user

    tenant = app_store.get_tenant(user.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant not found")

    ip_address = request.client.host if request.client else None
    app_store.create_audit_log(
        "auth.login", user_id=user.id, tenant_id=tenant.id, ip_address=ip_address
    )
    token_pair = _issue_token_pair(user, settings, app_store)
    return LoginResponse(tenant=tenant, user=_public_user(user), **token_pair.model_dump())


def _public_user(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        name=user.name,
        role=user.role,
        email_verified=user.email_verified,
        mfa_enabled=user.totp_secret is not None,
        mfa_recovery_codes_remaining=len(user.mfa_recovery_code_hashes) if user.totp_secret else 0,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    auth_context: AuthContext = Depends(resolve_current_principal),
) -> MFASetupResponse:
    import pyotp

    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=auth_context.user.email, issuer_name="CallForce"
    )
    return MFASetupResponse(secret=secret, provisioning_uri=uri)


@router.post("/mfa/verify", response_model=MFARecoveryCodesResponse)
async def verify_mfa(
    payload: MFAVerifyRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    auth_context: AuthContext = Depends(resolve_current_principal),
    app_store: AppStore = Depends(get_app_store),
) -> MFARecoveryCodesResponse:
    import pyotp

    totp = pyotp.TOTP(payload.secret)
    if not totp.verify(payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code")

    recovery_codes, recovery_code_hashes = _issue_mfa_recovery_code_pair(settings)
    if not app_store.update_user_mfa(
        auth_context.user.id,
        payload.secret,
        recovery_code_hashes,
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to enable MFA"
        )

    app_store.create_audit_log(
        "auth.mfa_enabled",
        user_id=auth_context.user.id,
        tenant_id=auth_context.tenant.id,
        ip_address=request.client.host if request.client else None,
    )
    return MFARecoveryCodesResponse(codes=recovery_codes, remaining=len(recovery_codes))


@router.post("/mfa/recovery-codes", response_model=MFARecoveryCodesResponse)
async def regenerate_mfa_recovery_codes(
    payload: MFACodeRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    auth_context: AuthContext = Depends(resolve_current_principal),
    app_store: AppStore = Depends(get_app_store),
) -> MFARecoveryCodesResponse:
    if not auth_context.user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not enabled")
    if not _verify_mfa_code(
        auth_context.user,
        payload.code,
        settings,
        app_store,
        consume_recovery=True,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    recovery_codes, recovery_code_hashes = _issue_mfa_recovery_code_pair(settings)
    if not app_store.replace_mfa_recovery_code_hashes(
        auth_context.user.id,
        recovery_code_hashes,
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate recovery codes",
        )

    app_store.create_audit_log(
        "auth.mfa_recovery_codes_regenerated",
        user_id=auth_context.user.id,
        tenant_id=auth_context.tenant.id,
        ip_address=request.client.host if request.client else None,
    )
    return MFARecoveryCodesResponse(codes=recovery_codes, remaining=len(recovery_codes))


@router.post("/mfa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_mfa(
    payload: MFACodeRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    auth_context: AuthContext = Depends(resolve_current_principal),
    app_store: AppStore = Depends(get_app_store),
) -> Response:
    if not auth_context.user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not enabled")
    if not _verify_mfa_code(
        auth_context.user,
        payload.code,
        settings,
        app_store,
        consume_recovery=True,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
    if not app_store.update_user_mfa(auth_context.user.id, None, []):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to disable MFA"
        )

    app_store.create_audit_log(
        "auth.mfa_disabled",
        user_id=auth_context.user.id,
        tenant_id=auth_context.tenant.id,
        ip_address=request.client.host if request.client else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _issue_mfa_recovery_code_pair(settings: Settings) -> tuple[list[str], list[str]]:
    recovery_codes = issue_mfa_recovery_codes()
    recovery_code_hashes = [
        hash_mfa_recovery_code(code, settings.access_token_secret) for code in recovery_codes
    ]
    return recovery_codes, recovery_code_hashes


def _verify_mfa_code(
    user: User,
    code: str,
    settings: Settings,
    app_store: AppStore,
    consume_recovery: bool,
) -> bool:
    import pyotp

    if not user.totp_secret:
        return False
    if code.isdigit() and len(code) == 6 and pyotp.TOTP(user.totp_secret).verify(code):
        return True

    normalized_code = normalize_mfa_recovery_code(code)
    if len(normalized_code) != 8:
        return False
    recovery_code_hash = hash_mfa_recovery_code(normalized_code, settings.access_token_secret)
    if consume_recovery:
        return app_store.consume_mfa_recovery_code(user.id, recovery_code_hash)
    return any(
        compare_digest(stored_hash, recovery_code_hash)
        for stored_hash in user.mfa_recovery_code_hashes
    )
