"""fix migration transaction error and ensure chatbot_name column exists

Revision ID: 20251020_fix_migration_error
Revises: a2e5b7c9d3f1
Create Date: 2025-10-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251020_fix_migration_error'
down_revision = 'a2e5b7c9d3f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix migration transaction error and ensure all required columns exist."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if chatbot_configs table exists
    try:
        existing_columns = {col['name'] for col in inspector.get_columns('chatbot_configs')}
    except Exception:
        # Table doesn't exist, nothing to do
        return
    
    # Add missing columns that should exist based on the model
    with op.batch_alter_table('chatbot_configs') as batch_op:
        # Add chatbot_name if it doesn't exist
        if 'chatbot_name' not in existing_columns:
            batch_op.add_column(sa.Column('chatbot_name', sa.String(), nullable=True))
        
        # Add company_name if it doesn't exist
        if 'company_name' not in existing_columns:
            batch_op.add_column(sa.Column('company_name', sa.String(), nullable=True))
        
        # Add specializations if it doesn't exist
        if 'specializations' not in existing_columns:
            batch_op.add_column(sa.Column('specializations', sa.Text(), nullable=True))
        
        # Add friendly_tone if it doesn't exist
        if 'friendly_tone' not in existing_columns:
            batch_op.add_column(sa.Column('friendly_tone', sa.Boolean(), nullable=True))
        
        # Add professional_style if it doesn't exist
        if 'professional_style' not in existing_columns:
            batch_op.add_column(sa.Column('professional_style', sa.Boolean(), nullable=True))
        
        # Add suggestive_responses if it doesn't exist
        if 'suggestive_responses' not in existing_columns:
            batch_op.add_column(sa.Column('suggestive_responses', sa.Boolean(), nullable=True))
        
        # Add manager_handover if it doesn't exist
        if 'manager_handover' not in existing_columns:
            batch_op.add_column(sa.Column('manager_handover', sa.Boolean(), nullable=True))
        
        # Add fallback_message if it doesn't exist
        if 'fallback_message' not in existing_columns:
            batch_op.add_column(sa.Column('fallback_message', sa.Text(), nullable=True))
        
        # Add handover_message if it doesn't exist
        if 'handover_message' not in existing_columns:
            batch_op.add_column(sa.Column('handover_message', sa.Text(), nullable=True))
        
        # Add response_timeout if it doesn't exist
        if 'response_timeout' not in existing_columns:
            batch_op.add_column(sa.Column('response_timeout', sa.Integer(), nullable=True))
        
        # Add conversation_logging if it doesn't exist
        if 'conversation_logging' not in existing_columns:
            batch_op.add_column(sa.Column('conversation_logging', sa.Boolean(), nullable=True))
        
        # Add performance_analytics if it doesn't exist
        if 'performance_analytics' not in existing_columns:
            batch_op.add_column(sa.Column('performance_analytics', sa.Boolean(), nullable=True))
        
        # Add error_reporting if it doesn't exist
        if 'error_reporting' not in existing_columns:
            batch_op.add_column(sa.Column('error_reporting', sa.Boolean(), nullable=True))
        
        # Add language_instruction if it doesn't exist
        if 'language_instruction' not in existing_columns:
            batch_op.add_column(sa.Column('language_instruction', sa.Text(), nullable=True))
        
        # Add persona_instruction if it doesn't exist
        if 'persona_instruction' not in existing_columns:
            batch_op.add_column(sa.Column('persona_instruction', sa.Text(), nullable=True))
        
        # Add system_instruction if it doesn't exist
        if 'system_instruction' not in existing_columns:
            batch_op.add_column(sa.Column('system_instruction', sa.Text(), nullable=True))
        
        # Add order_flow_block if it doesn't exist
        if 'order_flow_block' not in existing_columns:
            batch_op.add_column(sa.Column('order_flow_block', sa.Text(), nullable=True))
        
        # Add other_instruction if it doesn't exist
        if 'other_instruction' not in existing_columns:
            batch_op.add_column(sa.Column('other_instruction', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove the columns that were added in this migration."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    try:
        existing_columns = {col['name'] for col in inspector.get_columns('chatbot_configs')}
    except Exception:
        return
    
    with op.batch_alter_table('chatbot_configs') as batch_op:
        # Remove columns in reverse order
        columns_to_remove = [
            'other_instruction', 'order_flow_block', 'system_instruction',
            'persona_instruction', 'language_instruction', 'error_reporting',
            'performance_analytics', 'conversation_logging', 'response_timeout',
            'handover_message', 'fallback_message', 'manager_handover',
            'suggestive_responses', 'professional_style', 'friendly_tone',
            'specializations', 'company_name', 'chatbot_name'
        ]
        
        for column in columns_to_remove:
            if column in existing_columns:
                batch_op.drop_column(column)
