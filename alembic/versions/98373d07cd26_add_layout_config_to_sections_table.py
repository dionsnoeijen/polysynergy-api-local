"""Add layout_config to sections table

Revision ID: 98373d07cd26
Revises: 79e207c0e05c
Create Date: 2025-10-31 13:11:45.027170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '98373d07cd26'
down_revision: Union[str, Sequence[str], None] = '79e207c0e05c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add layout_config JSONB column to sections table for grid layout storage."""
    op.add_column('sections', sa.Column(
        'layout_config',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'{}'::jsonb")
    ))


def downgrade() -> None:
    """Remove layout_config column from sections table."""
    op.drop_column('sections', 'layout_config')
