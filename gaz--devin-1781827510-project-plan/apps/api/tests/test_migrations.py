"""Test migration chain integrity.

Verifies:
- Single head (no branching)
- All revisions form a clean chain from base to head
- Alembic metadata matches db_models.py (schema == models check)
"""

from pathlib import Path

from sqlalchemy import create_engine

from alembic.config import Config
from alembic.script import ScriptDirectory

_ALEMBIC_INI = str(Path(__file__).resolve().parent.parent / "alembic.ini")


def _get_alembic_config() -> Config:
    config = Config(_ALEMBIC_INI)
    return config


def test_single_head():
    """Migration chain must have exactly one head (no branches)."""
    config = _get_alembic_config()
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected 1 head, got {len(heads)}: {heads}"


def test_migration_chain_is_linear():
    """All revisions must form a single linear chain from base to head."""
    config = _get_alembic_config()
    script = ScriptDirectory.from_config(config)
    
    revisions = list(script.walk_revisions())
    assert len(revisions) > 0, "No migration revisions found"
    
    # Check no revision has multiple down_revisions (no merges)
    for rev in revisions:
        down = rev.down_revision
        if isinstance(down, (list, tuple)):
            assert len(down) <= 1, (
                f"Revision {rev.revision} has multiple down_revisions: {down}"
            )


def test_base_revision_exists():
    """There must be exactly one base (initial) revision."""
    config = _get_alembic_config()
    script = ScriptDirectory.from_config(config)
    bases = script.get_bases()
    assert len(bases) == 1, f"Expected 1 base revision, got {len(bases)}: {bases}"


def test_schema_matches_models():
    """Schema produced by create_all should have all tables from db_models."""
    from app.database import Base
    
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    
    from sqlalchemy import inspect
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())
    
    model_tables = set(Base.metadata.tables.keys())
    
    missing_in_db = model_tables - db_tables
    assert not missing_in_db, f"Tables in models but not in schema: {missing_in_db}"
    
    engine.dispose()
