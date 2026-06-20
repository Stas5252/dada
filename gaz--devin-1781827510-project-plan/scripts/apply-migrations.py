import os
from pathlib import Path

from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[1]

MIGRATIONS_DIR = REPO_ROOT / "migrations" / "versions"
DEFAULT_DATABASE_URL = "postgresql://gaz:gaz@localhost:5432/gaz"


def main() -> None:
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = create_engine(database_url, pool_pre_ping=True)
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        raise SystemExit("No migrations found.")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT now())"
            )
        )
        applied_versions = {
            row[0]
            for row in connection.execute(text("SELECT version FROM schema_migrations"))
        }
        for migration_file in migration_files:
            version = migration_file.name
            if version in applied_versions:
                print(f"skip {version}")
                continue
            for statement in _split_sql(migration_file.read_text()):
                connection.execute(text(statement))
            connection.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": version},
            )
            print(f"applied {version}")


def _split_sql(sql: str) -> list[str]:
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


if __name__ == "__main__":
    main()
