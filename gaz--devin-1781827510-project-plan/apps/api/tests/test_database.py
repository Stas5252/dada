from sqlalchemy import inspect

from app.database import build_session_factory, create_schema, session_scope
from app.db_models import Base, TenantModel


def test_sqlalchemy_metadata_creates_core_schema(sqlite_engine) -> None:
    create_schema(sqlite_engine)
    inspector = inspect(sqlite_engine)

    assert set(Base.metadata.tables).issubset(set(inspector.get_table_names()))


def test_session_scope_commits_and_closes(sqlite_engine) -> None:
    create_schema(sqlite_engine)
    session_factory = build_session_factory(sqlite_engine)

    with session_scope(session_factory) as session:
        session.add(TenantModel(id="tenant-1", name="Tenant One"))

    with session_scope(session_factory) as session:
        tenant = session.get(TenantModel, "tenant-1")

    assert tenant is not None
    assert tenant.name == "Tenant One"
