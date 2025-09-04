"""add preferred_language to users

Revision ID: a2e5b7c9d3f1
Revises: 7b1a5d3cb3c1
Create Date: 2025-09-03
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2e5b7c9d3f1'
down_revision = '7b1a5d3cb3c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch operations for compatibility
    try:
        with op.batch_alter_table('users') as batch_op:
            batch_op.add_column(
                sa.Column('preferred_language', sa.String(), nullable=False, server_default='uk')
            )
        # Remove server default after backfilling existing rows
        op.alter_column('users', 'preferred_language', server_default=None)
    except Exception:
        # If the column already exists, make migration idempotent
        pass


def downgrade() -> None:
    try:
        with op.batch_alter_table('users') as batch_op:
            batch_op.drop_column('preferred_language')
    except Exception:
        pass


