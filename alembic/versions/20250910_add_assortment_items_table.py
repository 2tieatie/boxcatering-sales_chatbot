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
down_revision = "a2e5b7c9d3f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.drop_table("assortment_items")


