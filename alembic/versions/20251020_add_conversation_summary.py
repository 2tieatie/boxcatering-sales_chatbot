"""add summary column to conversations

Revision ID: 20251020_add_conversation_summary
Revises: 20251017_add_bot_name
Create Date: 2025-10-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251020_add_conv_summary"
down_revision = "20251017_add_bot_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add conversations.summary if missing."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = set()
    try:
        existing_columns = {col["name"] for col in inspector.get_columns("conversations")}
    except Exception:
        # Table may not exist in some environments; skip safely
        existing_columns = set()

    if "summary" not in existing_columns:
        with op.batch_alter_table("conversations") as batch_op:
            batch_op.add_column(sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop conversations.summary if exists."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_columns = {col["name"] for col in inspector.get_columns("conversations")}
    except Exception:
        existing_columns = set()

    if "summary" in existing_columns:
        with op.batch_alter_table("conversations") as batch_op:
            batch_op.drop_column("summary")


