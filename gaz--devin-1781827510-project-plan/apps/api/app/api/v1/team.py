"""
Team management API endpoints.
Supports listing members, inviting new users, updating roles, and removing members.
"""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.api.v1.dependencies import AuthContext, require_permission
from app.rbac import Permission, Role
from app.schemas import User
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/team", tags=["team"])

MANAGE_AUTH = require_permission(Permission.MANAGE_AUTH)
READ_AUTH = require_permission(Permission.READ_AUTH)


class TeamMemberResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    email_verified: bool
    mfa_enabled: bool
    created_at: datetime
    last_active: datetime | None = None


class InviteRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    role: str = "viewer"


class InviteResponse(BaseModel):
    user: TeamMemberResponse
    invite_token: str
    message: str


class UpdateRoleRequest(BaseModel):
    role: str = Field(min_length=1)


@router.get("/members", response_model=list[TeamMemberResponse])
async def list_team_members(
    auth: AuthContext = Depends(READ_AUTH),
    app_store: AppStore = Depends(get_app_store),
) -> list[TeamMemberResponse]:
    tenant_id = UUID(auth.tenant_id)
    users = app_store.list_tenant_users(tenant_id)
    members = [_user_to_member(user) for user in users]
    return sorted(members, key=lambda member: member.created_at)


@router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_team_member(
    payload: InviteRequest,
    auth: AuthContext = Depends(MANAGE_AUTH),
    app_store: AppStore = Depends(get_app_store),
) -> InviteResponse:
    tenant_id = UUID(auth.tenant_id)

    try:
        role = Role(payload.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_ROLE", "message": f"Invalid role: {payload.role}"},
        ) from None

    if role == Role.owner and auth.role != Role.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "CANNOT_ASSIGN_OWNER",
                "message": "Only owner can assign owner role.",
            },
        )

    existing = app_store.get_user_by_email(payload.email)
    if existing and existing.tenant_id == tenant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "EMAIL_EXISTS",
                "message": "User with this email already exists in team.",
            },
        )

    invite_token = uuid4().hex[:16]
    temp_password = uuid4().hex[:12]

    new_user = User(
        tenant_id=tenant_id,
        email=payload.email,
        name=payload.name,
        role=role,
        email_verified=False,
    )

    app_store.create_tenant_user(new_user, temp_password)
    app_store.create_audit_log(
        event_type="team.invite",
        user_id=auth.user.id,
        tenant_id=tenant_id,
        details={
            "invited_email": payload.email,
            "invited_role": payload.role,
            "invited_user_id": str(new_user.id),
        },
    )

    return InviteResponse(
        user=_user_to_member(new_user),
        invite_token=invite_token,
        message=(
            f"Приглашение отправлено на {payload.email}. " f"Временный пароль: {temp_password}"
        ),
    )


@router.patch("/members/{member_id}/role", response_model=TeamMemberResponse)
async def update_member_role(
    member_id: UUID,
    payload: UpdateRoleRequest,
    auth: AuthContext = Depends(MANAGE_AUTH),
    app_store: AppStore = Depends(get_app_store),
) -> TeamMemberResponse:
    tenant_id = UUID(auth.tenant_id)

    try:
        new_role = Role(payload.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_ROLE", "message": f"Invalid role: {payload.role}"},
        ) from None

    if member_id == auth.user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "CANNOT_CHANGE_OWN_ROLE",
                "message": "Cannot change your own role.",
            },
        )

    if new_role == Role.owner and auth.role != Role.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "CANNOT_ASSIGN_OWNER",
                "message": "Only owner can assign owner role.",
            },
        )

    user = app_store.get_user(member_id)
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    updated_user = app_store.update_user_role(tenant_id, member_id, new_role)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    app_store.create_audit_log(
        event_type="team.role_change",
        user_id=auth.user.id,
        tenant_id=tenant_id,
        details={
            "member_id": str(member_id),
            "old_role": str(user.role) if user else "",
            "new_role": payload.role,
        },
    )

    return _user_to_member(updated_user)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    member_id: UUID,
    auth: AuthContext = Depends(MANAGE_AUTH),
    app_store: AppStore = Depends(get_app_store),
) -> None:
    tenant_id = UUID(auth.tenant_id)

    if member_id == auth.user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "CANNOT_REMOVE_SELF",
                "message": "Cannot remove yourself from team.",
            },
        )

    user = app_store.get_user(member_id)
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if user.role == Role.owner:
        owners = [
            team_user
            for team_user in app_store.list_tenant_users(tenant_id)
            if team_user.role == Role.owner
        ]
        if len(owners) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "LAST_OWNER", "message": "Cannot remove the last owner."},
            )

    app_store.remove_tenant_user(tenant_id, member_id)
    app_store.create_audit_log(
        event_type="team.remove",
        user_id=auth.user.id,
        tenant_id=tenant_id,
        details={"removed_user_id": str(member_id), "removed_email": user.email},
    )


def _user_to_member(user: User) -> TeamMemberResponse:
    return TeamMemberResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value if isinstance(user.role, Role) else str(user.role),
        email_verified=user.email_verified,
        mfa_enabled=user.totp_secret is not None,
        created_at=user.created_at,
    )
