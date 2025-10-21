"""add correlation_id to prompt_logs

Revision ID: 20251021_add_correlation_id
Revises: 20251020_fix_migration_transaction_error
Create Date: 2025-10-21
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251021_add_correlation_id"
down_revision = "20251020_add_prompt_log_trace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add correlation_id field to prompt_logs table if missing."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_columns = {c["name"] for c in inspector.get_columns("prompt_logs")}
    except Exception:
        existing_columns = set()

    with op.batch_alter_table("prompt_logs") as batch_op:
        if "correlation_id" not in existing_columns:
            batch_op.add_column(sa.Column("correlation_id", sa.String(), nullable=True))
            # Add index for correlation_id field
            batch_op.create_index("ix_prompt_logs_correlation_id", ["correlation_id"])


def downgrade() -> None:
    """Drop correlation_id field from prompt_logs if it exists."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_columns = {c["name"] for c in inspector.get_columns("prompt_logs")}
    except Exception:
        existing_columns = set()

    with op.batch_alter_table("prompt_logs") as batch_op:
        if "correlation_id" in existing_columns:
            # Drop index first
            try:
                batch_op.drop_index("ix_prompt_logs_correlation_id")
            except Exception:
                pass
            batch_op.drop_column("correlation_id")
