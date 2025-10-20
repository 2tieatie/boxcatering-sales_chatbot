"""add assortment items table

Revision ID: 20250910_add_assortment_items
Revises: 20250903_add_user_preferred_language
Create Date: 2025-09-10 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250910_add_assortment_items"
down_revision = "20251020_fix_migration_error"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create table only if it doesn't already exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "assortment_items" not in existing_tables:
        op.create_table(
            "assortment_items",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("name", sa.String(), nullable=False, index=True),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("price_uah", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    # Drop table only if it exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "assortment_items" in existing_tables:
        op.drop_table("assortment_items")


