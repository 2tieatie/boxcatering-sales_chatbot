"""add guests and weight to assortment_items

Revision ID: 20251020_add_assortment_guests_and_weight
Revises: 20251020_add_order_priority_and_guests_count
Create Date: 2025-10-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251020_add_assortment_guests"
down_revision = "20251020_add_order_priority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add assortment_items.guests and assortment_items.weight if missing."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_columns = {
            c["name"] for c in inspector.get_columns("assortment_items")
        }
    except Exception:
        existing_columns = set()

    with op.batch_alter_table("assortment_items") as batch_op:
        if "guests" not in existing_columns:
            batch_op.add_column(sa.Column("guests", sa.Integer(), nullable=True))
        if "weight" not in existing_columns:
            batch_op.add_column(sa.Column("weight", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    """Drop assortment_items.guests and assortment_items.weight if they exist."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_columns = {
            c["name"] for c in inspector.get_columns("assortment_items")
        }
    except Exception:
        existing_columns = set()

    with op.batch_alter_table("assortment_items") as batch_op:
        if "weight" in existing_columns:
            batch_op.drop_column("weight")
        if "guests" in existing_columns:
            batch_op.drop_column("guests")
