"""Add project_templates table

Revision ID: a1b2c3d4e5f6
Revises: 1d9370a370a8
Create Date: 2025-12-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '1d9370a370a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create project_templates table."""
    op.create_table(
        'project_templates',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    )

    # Create unique constraint on (project_id, name)
    op.create_unique_constraint(
        'uq_project_templates_project_name',
        'project_templates',
        ['project_id', 'name']
    )

    # Create index on project_id for faster lookups
    op.create_index(
        'ix_project_templates_project_id',
        'project_templates',
        ['project_id']
    )


def downgrade() -> None:
    """Drop project_templates table."""
    op.drop_index('ix_project_templates_project_id', table_name='project_templates')
    op.drop_constraint('uq_project_templates_project_name', 'project_templates', type_='unique')
    op.drop_table('project_templates')
