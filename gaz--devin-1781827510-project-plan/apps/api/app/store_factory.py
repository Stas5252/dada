from functools import lru_cache
from uuid import UUID

from app.database import build_engine, build_session_factory
from app.settings import get_settings
from app.sqlalchemy_store import SqlAlchemyStore
from app.store import InMemoryStore, store

AppStore = InMemoryStore | SqlAlchemyStore

from typing import Any
GLOBAL_ARQ_POOL: Any = None


@lru_cache
def get_app_store() -> AppStore:
    settings = get_settings()
    if settings.store_backend == "sqlalchemy":
        engine = build_engine(settings.database_url)
        app_store: AppStore = SqlAlchemyStore(build_session_factory(engine), settings)
    else:
        app_store = store
    if settings.seed_demo_data:
        app_store.seed_demo_data(UUID(settings.demo_tenant_id), settings.access_token_secret)
    return app_store
