import os
from collections.abc import Generator
from contextlib import suppress

import pytest
from sqlalchemy import Engine, create_engine

from app.settings import get_settings
from app.store_factory import get_app_store

# Set env before anything loads
os.environ["DATABASE_URL"] = "sqlite:///test_run.db"


@pytest.fixture
def sqlite_engine() -> Generator[Engine, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    get_settings.cache_clear()
    get_app_store.cache_clear()

    db_file = "test_run.db"
    if os.path.exists(db_file):
        with suppress(Exception):
            os.remove(db_file)

    yield

    get_settings.cache_clear()
    get_app_store.cache_clear()
    if os.path.exists(db_file):
        with suppress(Exception):
            os.remove(db_file)
