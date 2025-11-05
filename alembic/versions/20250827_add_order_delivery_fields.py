"""add delivery fields to orders

Revision ID: 20250827_add_order_delivery_fields
Revises: 
Create Date: 2025-08-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7b1a5d3cb3c1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make migration idempotent: add columns only if they don't exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("orders")}

    with op.batch_alter_table("orders") as batch_op:
        if "delivery_date" not in existing_columns:
            batch_op.add_column(
                sa.Column("delivery_date", sa.DateTime(timezone=True), nullable=True)
            )
        if "delivery_time" not in existing_columns:
            batch_op.add_column(sa.Column("delivery_time", sa.String(), nullable=True))
        if "menu_items" not in existing_columns:
            batch_op.add_column(sa.Column("menu_items", sa.Text(), nullable=True))


def downgrade() -> None:
    # Drop columns only if they exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("orders")}

    with op.batch_alter_table("orders") as batch_op:
        if "menu_items" in existing_columns:
            batch_op.drop_column("menu_items")
        if "delivery_time" in existing_columns:
            batch_op.drop_column("delivery_time")
        if "delivery_date" in existing_columns:
            batch_op.drop_column("delivery_date")
