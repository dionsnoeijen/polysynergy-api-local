"""Remove ui_width from section_field_assignments

The ui_width column was moved to Section.layout_config but the column
was never dropped from the database. This caused NOT NULL constraint
violations when creating new field assignments.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove ui_width column from section_field_assignments."""
    op.drop_column('section_field_assignments', 'ui_width')


def downgrade() -> None:
    """Re-add ui_width column to section_field_assignments."""
    op.add_column('section_field_assignments',
        sa.Column('ui_width', sa.String(length=20), nullable=False, server_default='full'))
