"""Add agent profile and tool registry fields

Revision ID: 7d9e0f12a345
Revises: 6b7c8d9e0f12
Create Date: 2026-07-07 06:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7d9e0f12a345"
down_revision: Union[str, Sequence[str], None] = "6b7c8d9e0f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("agents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("business_profile", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("agent_role", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("agent_tone", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("agent_language", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("business_hours", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("escalation_rules", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("sales_rules", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("forbidden_topics", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("enabled_tools", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("agents", schema=None) as batch_op:
        batch_op.drop_column("enabled_tools")
        batch_op.drop_column("forbidden_topics")
        batch_op.drop_column("sales_rules")
        batch_op.drop_column("escalation_rules")
        batch_op.drop_column("business_hours")
        batch_op.drop_column("agent_language")
        batch_op.drop_column("agent_tone")
        batch_op.drop_column("agent_role")
        batch_op.drop_column("business_profile")
