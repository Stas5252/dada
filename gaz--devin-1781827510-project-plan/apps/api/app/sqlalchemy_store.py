from sqlalchemy.orm import Session, sessionmaker
from app.settings import Settings
from app.jobs import BackgroundJobBackend, InlineBackgroundJobBackend

from uuid import UUID
from datetime import datetime, UTC
from sqlalchemy import select
from app.schemas import Tenant, AuditLog, User, AuthSession
from app.db_models import TenantModel, UserModel, AuditLogModel, AuthSessionModel
from app.security import verify_password, issue_access_token

# Let's import the internal helpers from the auth mixin or redefine them?
# Wait! They are not exported?
# They were originally in sqlalchemy_store_old.py.
# Actually I'll just import from app.store.auth, app.store.billing etc if needed.
# Let's copy the internal helpers too? No, they were left in auth.py by scratch_extract.py!
# Wait! Did scratch_extract.py put _load_password_hash in auth.py?
from app.store.auth import _load_password_hash, _is_refresh_session_model_usable
from app.store.conversations import _timestamp

from app.store.base import BaseSqlAlchemyStore, _SessionScope
from app.store.auth import AuthStoreMixin
from app.store.agents import AgentsStoreMixin
from app.store.conversations import ConversationsStoreMixin
from app.store.crm import CrmStoreMixin
from app.store.analytics import AnalyticsStoreMixin
from app.store.billing import BillingStoreMixin

class SqlAlchemyStore(
    AuthStoreMixin,
    AgentsStoreMixin,
    ConversationsStoreMixin,
    CrmStoreMixin,
    AnalyticsStoreMixin,
    BillingStoreMixin,
    BaseSqlAlchemyStore,
):
    def __init__(self, session_factory: sessionmaker[Session], settings: Settings) -> None:
        super().__init__(session_factory)
        self.settings = settings
        self.background_jobs: BackgroundJobBackend
        import sys
        if settings.app_env == "test" or "pytest" in sys.modules:
            self.background_jobs = InlineBackgroundJobBackend()
        else:
            from app.jobs import ArqBackgroundJobBackend
            from app.store_factory import GLOBAL_ARQ_POOL
            self.background_jobs = ArqBackgroundJobBackend(redis_pool=GLOBAL_ARQ_POOL)

    def create_audit_log(
        self,
        event_type: str,
        user_id: UUID | None = None,
        tenant_id: UUID | None = None,
        ip_address: str | None = None,
        details: dict[str, str] | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            event_type=event_type,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            details=details or {},
        )
        with self._session_scope() as session:
            session.add(
                AuditLogModel(
                    id=str(audit_log.id),
                    tenant_id=str(audit_log.tenant_id) if audit_log.tenant_id else None,
                    user_id=str(audit_log.user_id) if audit_log.user_id else None,
                    event_type=audit_log.event_type,
                    ip_address=audit_log.ip_address,
                    details=audit_log.details,
                )
            )
        return audit_log

    def get_tenant(self, tenant_id: UUID) -> Tenant | None:
        with self.session_factory() as session:
            tenant_model = session.get(TenantModel, str(tenant_id))
            return self._tenant_from_model(tenant_model) if tenant_model else None

    def list_all_tenants(self) -> list[Tenant]:
        with self.session_factory() as session:
            models = session.query(TenantModel).all()
            return [self._tenant_from_model(m) for m in models]

    def list_audit_logs(self, tenant_id: UUID) -> list[AuditLog]:
        with self.session_factory() as session:
            models = session.scalars(
                select(AuditLogModel)
                .where(AuditLogModel.tenant_id == str(tenant_id))
                .order_by(AuditLogModel.created_at.desc())
            ).all()
            return [
                AuditLog(
                    id=UUID(m.id),
                    tenant_id=UUID(m.tenant_id) if m.tenant_id else None,
                    user_id=UUID(m.user_id) if m.user_id else None,
                    event_type=m.event_type,
                    ip_address=m.ip_address,
                    details=m.details,
                    created_at=_timestamp(m.created_at),
                    updated_at=_timestamp(m.created_at),
                )
                for m in models
            ]

    def login(
        self,
        email: str,
        password: str,
        token_secret: str,
        access_token_ttl_minutes: int = 15,
    ) -> tuple[Tenant, User, str] | None:
        with self.session_factory() as session:
            user_model = session.scalar(select(UserModel).where(UserModel.email == email))
            if user_model is None:
                return None
            if not verify_password(password, _load_password_hash(user_model.password_hash)):
                return None
            tenant_model = session.get(TenantModel, user_model.tenant_id)
            if tenant_model is None:
                return None
            user = self._user_from_model(session, user_model)
            tenant = self._tenant_from_model(tenant_model)
        token: str | None = None
        if not user.totp_secret:
            token = issue_access_token(
                tenant.id,
                user.id,
                token_secret,
                ttl_minutes=access_token_ttl_minutes,
            )
        return tenant, user, token or "".join(())

    def rotate_auth_session(
        self,
        session_id: UUID,
        presented_refresh_token_hash: str,
        new_session_id: UUID,
        new_refresh_token_hash: str,
        new_expires_at: datetime,
    ) -> AuthSession | None:
        now = datetime.now(UTC)
        with self._session_scope() as session:
            current_model = session.get(AuthSessionModel, str(session_id))
            if not _is_refresh_session_model_usable(
                current_model,
                presented_refresh_token_hash,
                now,
            ):
                return None
            if current_model is None:
                return None
            new_model = AuthSessionModel(
                id=str(new_session_id),
                tenant_id=current_model.tenant_id,
                user_id=current_model.user_id,
                refresh_token_hash=new_refresh_token_hash,
                expires_at=new_expires_at,
            )
            current_model.revoked_at = now
            current_model.replaced_by_session_id = str(new_session_id)
            current_model.updated_at = now
            session.add(new_model)
            session.flush()
            return self._auth_session_from_model(new_model)

    def update_tenant_plan(self, tenant_id: UUID, plan: str) -> Tenant | None:
        with self._session_scope() as session:
            tenant_model = session.get(TenantModel, str(tenant_id))
            if not tenant_model:
                return None
            tenant_model.plan = plan
            session.flush()
            return self._tenant_from_model(tenant_model)

    def update_tenant_settings(self, tenant_id: UUID, settings: dict[str, object]) -> Tenant | None:
        with self._session_scope() as session:
            tenant_model = session.get(TenantModel, str(tenant_id))
            if not tenant_model:
                return None
            current_settings = tenant_model.settings or {}
            tenant_model.settings = {**current_settings, **settings}
            session.flush()
            return self._tenant_from_model(tenant_model)

