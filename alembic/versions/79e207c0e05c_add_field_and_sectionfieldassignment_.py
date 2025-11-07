"""Add Field and SectionFieldAssignment models

Revision ID: 79e207c0e05c
Revises: e4ce6ad430c2
Create Date: 2025-10-31 12:16:38.351809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '79e207c0e05c'
down_revision: Union[str, Sequence[str], None] = 'e4ce6ad430c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create tables in correct order to avoid circular dependencies."""

    # Step 1: Create database_connections (no dependencies)
    op.create_table('database_connections',
    sa.Column('handle', sa.String(length=100), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('database_type', sa.String(length=50), nullable=False),
    sa.Column('host', sa.String(length=255), nullable=True),
    sa.Column('port', sa.Integer(), nullable=True),
    sa.Column('database_name', sa.String(length=255), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=True),
    sa.Column('password', sa.Text(), nullable=True),
    sa.Column('connection_options', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('file_path', sa.String(length=500), nullable=True),
    sa.Column('use_ssl', sa.Boolean(), nullable=False),
    sa.Column('ssl_options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('last_tested_at', sa.DateTime(), nullable=True),
    sa.Column('test_status', sa.String(length=50), nullable=True),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_database_connections_handle'), 'database_connections', ['handle'], unique=False)
    op.create_index(op.f('ix_database_connections_project_id'), 'database_connections', ['project_id'], unique=False)

    # Step 2: Create sections (without circular FK)
    op.create_table('sections',
    sa.Column('handle', sa.String(length=100), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('icon', sa.String(length=100), nullable=True),
    sa.Column('table_name', sa.String(length=100), nullable=False),
    sa.Column('title_field_handle', sa.String(length=100), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('migration_status', sa.String(length=50), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('database_connection_id', sa.UUID(), nullable=True),
    sa.Column('last_migration_id', sa.UUID(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['database_connection_id'], ['database_connections.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sections_handle'), 'sections', ['handle'], unique=False)
    op.create_index(op.f('ix_sections_project_id'), 'sections', ['project_id'], unique=False)

    # Step 3: Create section_migrations
    op.create_table('section_migrations',
    sa.Column('section_id', sa.UUID(), nullable=False),
    sa.Column('migration_type', sa.String(length=50), nullable=False),
    sa.Column('migration_sql', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('generated_by', sa.String(length=200), nullable=True),
    sa.Column('applied_by', sa.String(length=200), nullable=True),
    sa.Column('generated_at', sa.DateTime(), nullable=False),
    sa.Column('applied_at', sa.DateTime(), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_section_migrations_section_id'), 'section_migrations', ['section_id'], unique=False)

    # Step 4: Add circular FK to sections (now that section_migrations exists)
    op.create_foreign_key('fk_sections_last_migration', 'sections', 'section_migrations', ['last_migration_id'], ['id'], ondelete='SET NULL')

    # Step 5: Create fields
    op.create_table('fields',
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('handle', sa.String(length=100), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=False),
    sa.Column('field_type_handle', sa.String(length=100), nullable=False),
    sa.Column('field_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('default_value', sa.Text(), nullable=True),
    sa.Column('help_text', sa.Text(), nullable=True),
    sa.Column('placeholder', sa.String(length=200), nullable=True),
    sa.Column('is_required', sa.Boolean(), nullable=False),
    sa.Column('is_unique', sa.Boolean(), nullable=False),
    sa.Column('custom_validation_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('related_section_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['related_section_id'], ['sections.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'handle', name='uq_field_handle_per_project')
    )
    op.create_index(op.f('ix_fields_handle'), 'fields', ['handle'], unique=False)
    op.create_index(op.f('ix_fields_project_id'), 'fields', ['project_id'], unique=False)

    # Step 6: Create section_field_assignments
    op.create_table('section_field_assignments',
    sa.Column('section_id', sa.UUID(), nullable=False),
    sa.Column('field_id', sa.UUID(), nullable=False),
    sa.Column('ui_width', sa.String(length=20), nullable=False),
    sa.Column('tab_name', sa.String(length=100), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_visible', sa.Boolean(), nullable=False),
    sa.Column('is_required_override', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['field_id'], ['fields.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('section_id', 'field_id', name='uq_section_field_assignment')
    )
    op.create_index(op.f('ix_section_field_assignments_field_id'), 'section_field_assignments', ['field_id'], unique=False)
    op.create_index(op.f('ix_section_field_assignments_section_id'), 'section_field_assignments', ['section_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_section_field_assignments_section_id'), table_name='section_field_assignments')
    op.drop_index(op.f('ix_section_field_assignments_field_id'), table_name='section_field_assignments')
    op.drop_table('section_field_assignments')
    op.drop_index(op.f('ix_fields_project_id'), table_name='fields')
    op.drop_index(op.f('ix_fields_handle'), table_name='fields')
    op.drop_table('fields')
    op.drop_foreign_key('fk_sections_last_migration', 'sections')
    op.drop_index(op.f('ix_section_migrations_section_id'), table_name='section_migrations')
    op.drop_table('section_migrations')
    op.drop_index(op.f('ix_sections_project_id'), table_name='sections')
    op.drop_index(op.f('ix_sections_handle'), table_name='sections')
    op.drop_table('sections')
    op.drop_index(op.f('ix_database_connections_project_id'), table_name='database_connections')
    op.drop_index(op.f('ix_database_connections_handle'), table_name='database_connections')
    op.drop_table('database_connections')
