"""add priority and guests_count to orders

Revision ID: 20251020_add_order_priority_and_guests_count
Revises: 20251020_add_conversation_summary
Create Date: 2025-10-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251020_add_order_priority"
down_revision = "20251020_add_conv_summary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add orders.priority and orders.guests_count if missing."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_columns = {c["name"] for c in inspector.get_columns("orders")}
    except Exception:
        existing_columns = set()

    with op.batch_alter_table("orders") as batch_op:
        if "priority" not in existing_columns:
            batch_op.add_column(sa.Column("priority", sa.String(), nullable=True))
        if "guests_count" not in existing_columns:
            batch_op.add_column(sa.Column("guests_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Drop orders.priority and orders.guests_count if they exist."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_columns = {c["name"] for c in inspector.get_columns("orders")}
    except Exception:
        existing_columns = set()

    with op.batch_alter_table("orders") as batch_op:
        if "guests_count" in existing_columns:
            batch_op.drop_column("guests_count")
        if "priority" in existing_columns:
            batch_op.drop_column("priority")
