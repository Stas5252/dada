"""enable_rls

Revision ID: b5eb053a82d0
Revises: bf853ac3a600
Create Date: 2026-07-07 07:30:30.793973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5eb053a82d0'
down_revision: Union[str, Sequence[str], None] = 'bf853ac3a600'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    if context.dialect.name != 'postgresql':
        return

    # Tables that have a tenant_id column
    tables = [
        "users", "memberships", "auth_sessions", "audit_logs",
        "agents", "knowledge_sources", "knowledge_ingestion_jobs", "knowledge_chunks",
        "customers", "crm_sources", "contact_suppressions", "contact_consents",
        "conversations", "conversation_tags", "handoff_assignments", "internal_notes",
        "messages", "order_drafts", "api_keys", "campaigns", "campaign_leads",
        "billing_ledger", "webhook_subscriptions", "test_cases", "test_runs",
        "crm_leads", "crm_deals", "crm_tasks", "crm_notes"
    ]
    for table in tables:
        # We allow BYPASSRLS or superuser to see everything.
        # Otherwise, tenant_id must match the context var.
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        
        # Policy: Only rows where tenant_id matches app.current_tenant_id
        # We use coalesce to ensure if app.current_tenant_id is not set, it fails or returns nothing
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
            AS PERMISSIVE
            FOR ALL
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', true)
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.current_tenant_id', true)
            );
        """)


def downgrade() -> None:
    context = op.get_context()
    if context.dialect.name != 'postgresql':
        return

    tables = [
        "users", "memberships", "auth_sessions", "audit_logs",
        "agents", "knowledge_sources", "knowledge_ingestion_jobs", "knowledge_chunks",
        "customers", "crm_sources", "contact_suppressions", "contact_consents",
        "conversations", "conversation_tags", "handoff_assignments", "internal_notes",
        "messages", "order_drafts", "api_keys", "campaigns", "campaign_leads",
        "billing_ledger", "webhook_subscriptions", "test_cases", "test_runs",
        "crm_leads", "crm_deals", "crm_tasks", "crm_notes"
    ]
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
