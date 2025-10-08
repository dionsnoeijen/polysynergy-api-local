"""add_role_to_account_remove_can_edit_flow

Revision ID: 15c5f5e78d09
Revises: 982a0dfcb6ad
Create Date: 2025-10-06 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '15c5f5e78d09'
down_revision: Union[str, Sequence[str], None] = '982a0dfcb6ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum type for account role with explicit values
    # Using native postgres ENUM to ensure values match exactly what the model expects
    op.execute("CREATE TYPE accountrole AS ENUM ('admin', 'editor', 'chat_user')")

    # Add role column to accounts table with default 'chat_user'
    op.add_column('accounts', sa.Column('role', sa.Enum('admin', 'editor', 'chat_user', name='accountrole', create_type=False), nullable=False, server_default='chat_user'))

    # Drop can_edit_flow column from chat_window_access table
    op.drop_column('chat_window_access', 'can_edit_flow')


def downgrade() -> None:
    """Downgrade schema."""
    # Add can_edit_flow back to chat_window_access
    op.add_column('chat_window_access', sa.Column('can_edit_flow', sa.Boolean(), nullable=False, server_default='false'))

    # Drop role column from accounts
    op.drop_column('accounts', 'role')

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS accountrole")
