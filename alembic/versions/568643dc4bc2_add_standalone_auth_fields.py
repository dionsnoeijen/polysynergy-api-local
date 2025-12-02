"""add_standalone_auth_fields

Revision ID: 568643dc4bc2
Revises: e5f8a9b2c3d4
Create Date: 2025-11-21 08:12:30.431726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '568643dc4bc2'
down_revision: Union[str, Sequence[str], None] = 'e5f8a9b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add standalone authentication fields to accounts table."""
    # Rename cognito_id to external_user_id (generic for all auth providers)
    op.alter_column('accounts', 'cognito_id', new_column_name='external_user_id')

    # Add auth provider field
    op.add_column('accounts', sa.Column('auth_provider', sa.String(length=50), nullable=False, server_default='cognito'))

    # Add standalone auth fields
    op.add_column('accounts', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.add_column('accounts', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))

    # Add 2FA/TOTP fields
    op.add_column('accounts', sa.Column('totp_secret', sa.String(length=255), nullable=True))
    op.add_column('accounts', sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Remove standalone authentication fields from accounts table."""
    # Drop 2FA fields
    op.drop_column('accounts', 'totp_enabled')
    op.drop_column('accounts', 'totp_secret')

    # Drop standalone auth fields
    op.drop_column('accounts', 'email_verified')
    op.drop_column('accounts', 'password_hash')

    # Drop auth provider field
    op.drop_column('accounts', 'auth_provider')

    # Rename external_user_id back to cognito_id
    op.alter_column('accounts', 'external_user_id', new_column_name='cognito_id')
