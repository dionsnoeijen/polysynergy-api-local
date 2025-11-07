"""Add vectorization_config to sections

Revision ID: e5f8a9b2c3d4
Revises: d75d7affcece
Create Date: 2025-11-04 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5f8a9b2c3d4'
down_revision: Union[str, Sequence[str], None] = 'd75d7affcece'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add vectorization_config JSONB column to sections table."""
    op.add_column('sections', sa.Column('vectorization_config', postgresql.JSONB, nullable=True))


def downgrade() -> None:
    """Remove vectorization_config column from sections table."""
    op.drop_column('sections', 'vectorization_config')
