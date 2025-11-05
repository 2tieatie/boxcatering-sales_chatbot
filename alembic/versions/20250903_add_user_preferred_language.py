"""add preferred_language to users

Revision ID: a2e5b7c9d3f1
Revises: 7b1a5d3cb3c1
Create Date: 2025-09-03
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a2e5b7c9d3f1"
down_revision = "7b1a5d3cb3c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch operations for compatibility and keep everything in one transaction
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_columns = {col["name"] for col in inspector.get_columns("users")}
    except Exception:
        # Table doesn't exist, nothing to do
        return

    # Check if column already exists
    if "preferred_language" in existing_columns:
        print("Column 'preferred_language' already exists, skipping migration")
        return

    # Add column with server default, then remove it - all in one batch operation
    with op.batch_alter_table("users") as batch_op:
        # Add the column with server default
        batch_op.add_column(
            sa.Column(
                "preferred_language", sa.String(), nullable=False, server_default="uk"
            )
        )

        # Update existing rows to have the default value
        # This is done within the batch context to avoid transaction issues
        bind.execute(
            sa.text(
                "UPDATE users SET preferred_language = 'uk' WHERE preferred_language IS NULL"
            )
        )

        # Remove the server default
        batch_op.alter_column("preferred_language", server_default=None)


def downgrade() -> None:
    try:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("preferred_language")
    except Exception:
        pass
