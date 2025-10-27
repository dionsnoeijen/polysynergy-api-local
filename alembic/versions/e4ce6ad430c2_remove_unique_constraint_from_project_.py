"""remove_unique_constraint_from_project_name

Revision ID: e4ce6ad430c2
Revises: 15c5f5e78d09
Create Date: 2025-10-27 07:48:11.178115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4ce6ad430c2'
down_revision: Union[str, Sequence[str], None] = '15c5f5e78d09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop unique constraint on project name
    # Different tenants should be able to have projects with the same name
    op.drop_constraint('projects_name_key', 'projects', type_='unique')


def downgrade() -> None:
    """Downgrade schema."""
    # Re-add unique constraint on project name
    op.create_unique_constraint('projects_name_key', 'projects', ['name'])
