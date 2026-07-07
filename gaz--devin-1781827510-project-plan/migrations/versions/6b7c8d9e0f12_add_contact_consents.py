"""Add contact consents

Revision ID: 6b7c8d9e0f12
Revises: 40f2a7a8d9bb
Create Date: 2026-07-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b7c8d9e0f12"
down_revision: Union[str, Sequence[str], None] = "40f2a7a8d9bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "contact_consents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("contact_type", sa.String(length=40), nullable=False),
        sa.Column("value", sa.String(length=160), nullable=False),
        sa.Column("consent_type", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "channel",
            "contact_type",
            "value",
            "consent_type",
            name="uq_contact_consent_key",
        ),
    )
    with op.batch_alter_table("contact_consents", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_contact_consents_tenant_id"), ["tenant_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_contact_consents_value"), ["value"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("contact_consents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_contact_consents_value"))
        batch_op.drop_index(batch_op.f("ix_contact_consents_tenant_id"))
    op.drop_table("contact_consents")
