from collections.abc import Generator
from contextlib import AbstractContextManager
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

class _SessionScope:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> Session:
        self.session = self.session_factory()
        
        from app.context import current_tenant_id
        from sqlalchemy import text
        
        tenant_id = current_tenant_id.get()
        if tenant_id and self.session.bind and self.session.bind.dialect.name == "postgresql":
            # Set the RLS session variable
            self.session.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            
        return self.session

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        if self.session is None:
            return
        if exc_type is None:
            self.session.commit()
        else:
            self.session.rollback()
        self.session.close()

class BaseSqlAlchemyStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def _session_scope(self) -> AbstractContextManager[Session]:
        return _SessionScope(self.session_factory)
