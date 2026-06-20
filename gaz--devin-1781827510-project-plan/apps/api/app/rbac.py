from enum import StrEnum


class Role(StrEnum):
    owner = "owner"
    admin = "admin"
    agent = "agent"
    viewer = "viewer"


class Permission(StrEnum):
    READ_AUTH = "auth:read"
    MANAGE_AUTH = "auth:manage"
    READ_AGENTS = "agents:read"
    MANAGE_AGENTS = "agents:manage"
    READ_KNOWLEDGE = "knowledge:read"
    MANAGE_KNOWLEDGE = "knowledge:manage"
    READ_CHAT = "chat:read"
    MANAGE_CHAT = "chat:manage"
    READ_BILLING = "billing:read"
    MANAGE_BILLING = "billing:manage"
    READ_AUDIT = "audit:read"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.owner: frozenset(Permission),
    Role.admin: frozenset(
        {
            Permission.READ_AUTH,
            Permission.READ_AGENTS,
            Permission.MANAGE_AGENTS,
            Permission.READ_KNOWLEDGE,
            Permission.MANAGE_KNOWLEDGE,
            Permission.READ_CHAT,
            Permission.MANAGE_CHAT,
            Permission.READ_BILLING,
            Permission.MANAGE_BILLING,
            Permission.READ_AUDIT,
        }
    ),
    Role.agent: frozenset(
        {
            Permission.READ_AGENTS,
            Permission.READ_KNOWLEDGE,
            Permission.READ_CHAT,
            Permission.MANAGE_CHAT,
        }
    ),
    Role.viewer: frozenset(
        {
            Permission.READ_AGENTS,
            Permission.READ_KNOWLEDGE,
            Permission.READ_CHAT,
        }
    ),
}


class PermissionDeniedError(ValueError):
    pass


def normalize_role(role: Role | str) -> Role:
    try:
        return Role(role)
    except ValueError as exc:
        raise PermissionDeniedError("unknown role") from exc


def role_has_permission(role: Role | str, permission: Permission) -> bool:
    normalized_role = normalize_role(role)
    return permission in ROLE_PERMISSIONS[normalized_role]


def assert_role_allowed(role: Role | str, permission: Permission) -> None:
    if not role_has_permission(role, permission):
        raise PermissionDeniedError(f"{role} does not include {permission}")
