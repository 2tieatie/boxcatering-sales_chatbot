"""add prompt trace fields to prompt_logs

Revision ID: 20251020_add_prompt_log_trace_fields
Revises: 20251020_add_assortment_guests
Create Date: 2025-10-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251020_add_prompt_log_trace"
down_revision = "20251020_add_assortment_guests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add prompt trace fields to prompt_logs table if missing."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_columns = {c["name"] for c in inspector.get_columns("prompt_logs")}
    except Exception:
        existing_columns = set()

    with op.batch_alter_table("prompt_logs") as batch_op:
        if "system_prompt_preview" not in existing_columns:
            batch_op.add_column(sa.Column("system_prompt_preview", sa.Text(), nullable=True))
        if "system_prompt_length" not in existing_columns:
            batch_op.add_column(sa.Column("system_prompt_length", sa.Integer(), nullable=True))
        if "prompt_trace_json" not in existing_columns:
            batch_op.add_column(sa.Column("prompt_trace_json", sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop prompt trace fields from prompt_logs if they exist."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_columns = {c["name"] for c in inspector.get_columns("prompt_logs")}
    except Exception:
        existing_columns = set()

    with op.batch_alter_table("prompt_logs") as batch_op:
        if "prompt_trace_json" in existing_columns:
            batch_op.drop_column("prompt_trace_json")
        if "system_prompt_length" in existing_columns:
            batch_op.drop_column("system_prompt_length")
        if "system_prompt_preview" in existing_columns:
            batch_op.drop_column("system_prompt_preview")
