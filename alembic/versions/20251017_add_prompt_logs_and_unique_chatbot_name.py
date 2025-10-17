"""add prompt_logs and unique chatbot_configs.name

Revision ID: 20251017_add_prompt_logs
Revises: 20250910_add_assortment_items
Create Date: 2025-10-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251017_add_prompt_logs'
down_revision = '20250910_add_assortment_items'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) Deduplicate chatbot_configs.name so we can enforce uniqueness safely
    try:
        bind.execute(sa.text(
            """
            WITH dupe AS (
                SELECT id, name,
                       ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) rn
                FROM chatbot_configs
            )
            UPDATE chatbot_configs AS c
            SET name = c.name || ' - copy - ' || TO_CHAR(NOW(), 'YYYYMMDD-HH24MI') || '-' || dupe.rn
            FROM dupe
            WHERE c.id = dupe.id AND dupe.rn > 1;
            """
        ))
    except Exception:
        # Best-effort; if the table doesn't exist or DB disallows, ignore
        pass

    # 2) Enforce uniqueness via unique index (IF NOT EXISTS avoids failures on re-run)
    try:
        bind.execute(sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_chatbot_configs_name ON chatbot_configs (name)"
        ))
    except Exception:
        pass

    # 3) Create prompt_logs table only if it doesn't exist
    existing_tables = set(inspector.get_table_names())
    if 'prompt_logs' not in existing_tables:
        op.create_table(
            'prompt_logs',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('conversation_id', sa.Integer(), nullable=True),
            sa.Column('config_id', sa.Integer(), nullable=True),
            sa.Column('model', sa.String(), nullable=True),
            sa.Column('system_prompt_hash', sa.String(), nullable=True),
            sa.Column('user_message', sa.Text(), nullable=True),
            sa.Column('request_json', sa.Text(), nullable=True),
            sa.Column('response_json', sa.Text(), nullable=True),
            sa.Column('duration_ms', sa.Integer(), nullable=True),
            sa.Column('error', sa.Text(), nullable=True),
        )
    # 4) Create supporting indexes with IF NOT EXISTS
    try:
        bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_prompt_logs_created_at ON prompt_logs (created_at)"))
        bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_prompt_logs_conversation_id ON prompt_logs (conversation_id)"))
        bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_prompt_logs_config_id ON prompt_logs (config_id)"))
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index('ix_prompt_logs_config_id', table_name='prompt_logs')
    except Exception:
        pass
    try:
        op.drop_index('ix_prompt_logs_conversation_id', table_name='prompt_logs')
    except Exception:
        pass
    try:
        op.drop_index('ix_prompt_logs_created_at', table_name='prompt_logs')
    except Exception:
        pass
    op.drop_table('prompt_logs')
    try:
        op.drop_constraint("uq_chatbot_configs_name", "chatbot_configs", type_="unique")
    except Exception:
        pass


