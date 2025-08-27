"""add delivery fields to orders

Revision ID: 20250827_add_order_delivery_fields
Revises: 
Create Date: 2025-08-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b1a5d3cb3c1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('orders') as batch_op:
        batch_op.add_column(sa.Column('delivery_date', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('delivery_time', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('menu_items', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_column('menu_items')
        batch_op.drop_column('delivery_time')
        batch_op.drop_column('delivery_date')


