"""add chatbot_name to chatbot_configs

Revision ID: 20251017_add_bot_name
Revises: 20251017_add_cfg_prompt_fields
Create Date: 2025-10-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251017_add_bot_name'
down_revision = '20251017_add_cfg_prompt_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    try:
        existing_columns = {col['name'] for col in inspector.get_columns('chatbot_configs')}
    except Exception:
        existing_columns = set()

    with op.batch_alter_table('chatbot_configs') as batch_op:
        if 'chatbot_name' not in existing_columns:
            batch_op.add_column(sa.Column('chatbot_name', sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    try:
        existing_columns = {col['name'] for col in inspector.get_columns('chatbot_configs')}
    except Exception:
        existing_columns = set()

    with op.batch_alter_table('chatbot_configs') as batch_op:
        if 'chatbot_name' in existing_columns:
            batch_op.drop_column('chatbot_name')


