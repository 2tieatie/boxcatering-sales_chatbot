"""add prompt template fields to chatbot_configs

Revision ID: 20251017_add_cfg_prompt_fields
Revises: 20251017_add_prompt_logs
Create Date: 2025-10-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251017_add_cfg_prompt_fields'
down_revision = '20251017_add_prompt_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = set()
    try:
        existing_columns = {col['name'] for col in inspector.get_columns('chatbot_configs')}
    except Exception:
        # Table not found; nothing to do
        return

    with op.batch_alter_table('chatbot_configs') as batch_op:
        if 'language_instruction' not in existing_columns:
            batch_op.add_column(sa.Column('language_instruction', sa.Text(), nullable=True))
        if 'persona_instruction' not in existing_columns:
            batch_op.add_column(sa.Column('persona_instruction', sa.Text(), nullable=True))
        if 'system_instruction' not in existing_columns:
            batch_op.add_column(sa.Column('system_instruction', sa.Text(), nullable=True))
        if 'order_flow_block' not in existing_columns:
            batch_op.add_column(sa.Column('order_flow_block', sa.Text(), nullable=True))
        if 'other_instruction' not in existing_columns:
            batch_op.add_column(sa.Column('other_instruction', sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    try:
        existing_columns = {col['name'] for col in inspector.get_columns('chatbot_configs')}
    except Exception:
        existing_columns = set()

    with op.batch_alter_table('chatbot_configs') as batch_op:
        if 'other_instruction' in existing_columns:
            batch_op.drop_column('other_instruction')
        if 'order_flow_block' in existing_columns:
            batch_op.drop_column('order_flow_block')
        if 'system_instruction' in existing_columns:
            batch_op.drop_column('system_instruction')
        if 'persona_instruction' in existing_columns:
            batch_op.drop_column('persona_instruction')
        if 'language_instruction' in existing_columns:
            batch_op.drop_column('language_instruction')


