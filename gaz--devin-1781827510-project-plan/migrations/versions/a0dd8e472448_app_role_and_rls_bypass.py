"""app_role_and_rls_bypass

Revision ID: a0dd8e472448
Revises: b5eb053a82d0
Create Date: 2026-07-07 15:53:09.174336

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0dd8e472448'
down_revision: Union[str, Sequence[str], None] = 'b5eb053a82d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only run these statements if the dialect is postgresql
    bind = op.get_bind()
    if bind.engine.dialect.name == "postgresql":
        # Create unprivileged role for the app
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'callforce_app') THEN CREATE ROLE callforce_app LOGIN PASSWORD 'callforce_app_password'; END IF; END $$;")
        
        # Grant usage on schema public
        op.execute("GRANT USAGE ON SCHEMA public TO callforce_app;")
        
        # Grant DML permissions on all current tables and sequences
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO callforce_app;")
        op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO callforce_app;")
        
        # Set default privileges for future tables
        op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO callforce_app;")
        op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO callforce_app;")

        # Create SECURITY DEFINER function to bypass RLS for agent lookup
        op.execute("""
            CREATE OR REPLACE FUNCTION get_tenant_for_agent_bypass_rls(p_agent_id uuid) 
            RETURNS text AS $$
                SELECT tenant_id::text FROM agents WHERE id::uuid = p_agent_id;
            $$ LANGUAGE sql SECURITY DEFINER;
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.engine.dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS get_tenant_for_agent_bypass_rls(uuid);")
        
        # Revoke privileges
        op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM callforce_app;")
        op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM callforce_app;")
        op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM callforce_app;")
        op.execute("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM callforce_app;")
        op.execute("REVOKE USAGE ON SCHEMA public FROM callforce_app;")
        
        # Drop role
        op.execute("DROP ROLE IF EXISTS callforce_app;")
