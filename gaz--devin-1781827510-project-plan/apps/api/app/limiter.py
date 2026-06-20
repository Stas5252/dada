import sys

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.settings import get_settings


def _rate_limits_enabled() -> bool:
    return get_settings().app_env != "test" and "pytest" not in sys.modules


def get_storage_uri() -> str:
    settings = get_settings()
    if settings.rate_limit_storage_uri:
        return settings.rate_limit_storage_uri
    if settings.app_env in {"local", "test"}:
        return "memory://"
    return settings.redis_url if settings.redis_url else "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    enabled=_rate_limits_enabled(),
    storage_uri=get_storage_uri(),
)
