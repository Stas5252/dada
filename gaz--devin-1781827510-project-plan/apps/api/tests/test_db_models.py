from app.db_models import Base


def test_core_mvp_tables_are_declared() -> None:
    expected_tables = {
        "tenants",
        "users",
        "memberships",
        "auth_sessions",
        "agents",
        "knowledge_sources",
        "knowledge_ingestion_jobs",
        "knowledge_chunks",
        "conversations",
        "messages",
    }

    assert expected_tables.issubset(Base.metadata.tables)
    assert "mfa_recovery_code_hashes" in Base.metadata.tables["users"].columns
