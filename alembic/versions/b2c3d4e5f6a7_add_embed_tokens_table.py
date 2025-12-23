"""Add embed_tokens table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create embed_tokens table for embeddable chat authentication."""
    op.create_table(
        'embed_tokens',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('chat_window_id', UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),

        # Configuration
        sa.Column('sessions_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sidebar_visible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Usage tracking
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['chat_window_id'], ['chat_windows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    )

    # Unique constraint on token
    op.create_unique_constraint(
        'uq_embed_tokens_token',
        'embed_tokens',
        ['token']
    )

    # Index for faster lookups by token
    op.create_index(
        'ix_embed_tokens_token',
        'embed_tokens',
        ['token']
    )

    # Index for lookups by chat_window_id
    op.create_index(
        'ix_embed_tokens_chat_window_id',
        'embed_tokens',
        ['chat_window_id']
    )


def downgrade() -> None:
    """Drop embed_tokens table."""
    op.drop_index('ix_embed_tokens_chat_window_id', table_name='embed_tokens')
    op.drop_index('ix_embed_tokens_token', table_name='embed_tokens')
    op.drop_constraint('uq_embed_tokens_token', 'embed_tokens', type_='unique')
    op.drop_table('embed_tokens')
