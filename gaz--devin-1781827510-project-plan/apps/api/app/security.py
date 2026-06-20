import base64
import binascii
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac, sha256
from hmac import compare_digest, new
from secrets import choice, token_bytes
from typing import Any, cast
from uuid import UUID, uuid4


@dataclass(frozen=True)
class PasswordHash:
    algorithm: str
    iterations: int
    salt: str
    digest: str


@dataclass(frozen=True)
class AccessTokenClaims:
    tenant_id: UUID
    user_id: UUID
    expires_at: datetime


@dataclass(frozen=True)
class RefreshTokenClaims:
    session_id: UUID
    token_hash: str


class AccessTokenError(ValueError):
    pass


class ExpiredAccessTokenError(AccessTokenError):
    pass


class RefreshTokenError(ValueError):
    pass


MFA_RECOVERY_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def hash_password(password: str, iterations: int = 210_000) -> PasswordHash:
    salt = token_bytes(16)
    digest = pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return PasswordHash(
        algorithm="pbkdf2_sha256",
        iterations=iterations,
        salt=_b64encode(salt),
        digest=_b64encode(digest),
    )


def verify_password(password: str, password_hash: PasswordHash) -> bool:
    if password_hash.algorithm != "pbkdf2_sha256":
        return False
    salt = _b64decode(password_hash.salt)
    expected_digest = _b64decode(password_hash.digest)
    actual_digest = pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        password_hash.iterations,
    )
    return compare_digest(actual_digest, expected_digest)


def issue_access_token(
    tenant_id: UUID,
    user_id: UUID,
    secret: str,
    ttl_minutes: int = 15,
) -> str:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=ttl_minutes)
    header = {
        "alg": "HS256",
        "typ": "JWT",
    }
    payload = {
        "iss": "gaz-api",
        "jti": str(uuid4()),
        "type": "access",
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    header_part = _b64json(header)
    payload_part = _b64json(payload)
    signing_input = f"{header_part}.{payload_part}"
    signature = new(secret.encode(), signing_input.encode(), "sha256").digest()
    return f"{signing_input}.{_b64encode(signature)}"


def verify_access_token(
    token: str,
    secret: str,
    now: datetime | None = None,
) -> AccessTokenClaims:
    parts = token.split(".")
    if len(parts) != 3:
        raise AccessTokenError("access token format is invalid")

    header_part, payload_part, signature_part = parts
    signing_input = f"{header_part}.{payload_part}"
    expected_signature = new(secret.encode(), signing_input.encode(), "sha256").digest()
    try:
        actual_signature = _b64decode(signature_part)
    except AccessTokenError as exc:
        raise AccessTokenError("access token signature is invalid") from exc
    if not compare_digest(actual_signature, expected_signature):
        raise AccessTokenError("access token signature is invalid")

    try:
        header = _json_object(_b64decode(header_part))
        payload = _json_object(_b64decode(payload_part))
    except (AccessTokenError, json.JSONDecodeError) as exc:
        raise AccessTokenError("access token payload is invalid") from exc

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise AccessTokenError("access token header is invalid")
    if payload.get("iss") != "gaz-api" or payload.get("type") != "access":
        raise AccessTokenError("access token claims are invalid")

    try:
        tenant_id = UUID(str(payload["tenant_id"]))
        user_id = UUID(str(payload["sub"]))
        expires_at = datetime.fromtimestamp(int(payload["exp"]), UTC)
    except (KeyError, TypeError, ValueError) as exc:
        raise AccessTokenError("access token claims are invalid") from exc

    current_time = now if now is not None else datetime.now(UTC)
    if expires_at <= current_time:
        raise ExpiredAccessTokenError("access token has expired")

    return AccessTokenClaims(tenant_id=tenant_id, user_id=user_id, expires_at=expires_at)


def issue_refresh_token(session_id: UUID, secret: str) -> tuple[str, str]:
    verifier = _b64encode(token_bytes(32))
    token_hash = _refresh_token_hash(verifier, secret)
    return f"gaz-refresh.{session_id}.{verifier}", token_hash


def parse_refresh_token(token: str, secret: str) -> RefreshTokenClaims:
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "gaz-refresh":
        raise RefreshTokenError("refresh token format is invalid")
    try:
        session_id = UUID(parts[1])
    except ValueError as exc:
        raise RefreshTokenError("refresh token session id is invalid") from exc
    verifier = parts[2]
    if not verifier:
        raise RefreshTokenError("refresh token verifier is invalid")
    return RefreshTokenClaims(
        session_id=session_id,
        token_hash=_refresh_token_hash(verifier, secret),
    )


def issue_mfa_recovery_codes(count: int = 8) -> list[str]:
    return [f"{_mfa_recovery_segment()}-{_mfa_recovery_segment()}" for _ in range(count)]


def hash_mfa_recovery_code(code: str, secret: str) -> str:
    normalized_code = normalize_mfa_recovery_code(code)
    return sha256(f"{secret}:mfa-recovery:{normalized_code}".encode()).hexdigest()


def normalize_mfa_recovery_code(code: str) -> str:
    return code.strip().upper().replace("-", "").replace(" ", "")


def _mfa_recovery_segment() -> str:
    return "".join(choice(MFA_RECOVERY_CODE_ALPHABET) for _ in range(4))


def _refresh_token_hash(verifier: str, secret: str) -> str:
    return sha256(f"{secret}:{verifier}".encode()).hexdigest()


def _b64json(value: Mapping[str, object]) -> str:
    return _b64encode(json.dumps(value, separators=(",", ":"), sort_keys=True).encode())


def _json_object(value: bytes) -> dict[str, Any]:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise AccessTokenError("json value is not an object")
    return cast(dict[str, Any], payload)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (binascii.Error, ValueError) as exc:
        raise AccessTokenError("base64 value is invalid") from exc
