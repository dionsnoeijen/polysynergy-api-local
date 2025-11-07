"""Migration Generator Service - Generate SQL for section table migrations"""

from typing import List
from uuid import UUID

from models import Section, SectionFieldAssignment
from services.field_type_loader_service import get_field_type_loader


class MigrationGeneratorService:
    """
    Generates SQL migrations for section tables.

    Each section table gets standard columns:
    - id (UUID PRIMARY KEY)
    - created_at (TIMESTAMP)
    - updated_at (TIMESTAMP)

    Plus columns for each assigned field based on field type.
    """

    def __init__(self):
        self.field_type_loader = get_field_type_loader()

    def generate_create_table_sql(
        self,
        section: Section,
        field_assignments: List[SectionFieldAssignment],
        schema_name: str
    ) -> str:
        """
        Generate CREATE TABLE SQL for a new section.

        Args:
            section: The section to create a table for
            field_assignments: List of field assignments for this section
            schema_name: PostgreSQL schema name for the project

        Returns:
            SQL string to create the schema and table
        """
        table_name = section.table_name
        full_table_name = f'"{schema_name}"."{table_name}"'

        # Start with standard columns
        columns = [
            '"id" UUID PRIMARY KEY DEFAULT gen_random_uuid()',
            '"created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL',
            '"updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL'
        ]

        # Add column for each field assignment
        for assignment in field_assignments:
            field = assignment.field
            column_sql = self._generate_column_sql(field, assignment, schema_name)
            if column_sql:  # Skip virtual fields (one-to-many)
                columns.append(column_sql)

        columns_sql = ',\n    '.join(columns)

        # Create schema and table
        sql = f'''-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS "{schema_name}";

-- Create table in schema
CREATE TABLE IF NOT EXISTS {full_table_name} (
    {columns_sql}
);'''

        return sql

    def generate_add_column_sql(
        self,
        section: Section,
        field_assignment: SectionFieldAssignment,
        schema_name: str
    ) -> str:
        """
        Generate ALTER TABLE SQL to add a new column.

        Args:
            section: The section whose table to alter
            field_assignment: The field assignment to add as a column
            schema_name: PostgreSQL schema name

        Returns:
            SQL string to add the column
        """
        table_name = section.table_name
        full_table_name = f'"{schema_name}"."{table_name}"'
        field = field_assignment.field

        column_sql = self._generate_column_sql(field, field_assignment, schema_name)

        if not column_sql:
            # Virtual field (one-to-many) - no column to add
            return ""

        # Extract column name and definition from column_sql
        # Format: '"column_name" TYPE CONSTRAINTS'
        sql = f'ALTER TABLE {full_table_name} ADD COLUMN IF NOT EXISTS {column_sql};'

        return sql

    def generate_drop_column_sql(
        self,
        section: Section,
        field_handle: str
    ) -> str:
        """
        Generate ALTER TABLE SQL to drop a column.

        Args:
            section: The section whose table to alter
            field_handle: The handle of the field to remove

        Returns:
            SQL string to drop the column
        """
        table_name = section.table_name

        sql = f'ALTER TABLE "{table_name}" DROP COLUMN IF EXISTS "{field_handle}";'

        return sql

    def _generate_column_sql(
        self,
        field,
        assignment: SectionFieldAssignment,
        schema_name: str = None
    ) -> str:
        """
        Generate SQL for a single column based on field type.

        Args:
            field: The field definition
            assignment: The field assignment (contains context like is_required_override)
            schema_name: PostgreSQL schema name (for foreign key references)

        Returns:
            SQL column definition string or empty string for virtual fields
        """
        field_type = self.field_type_loader.get_field_type(field.field_type_handle)

        if not field_type:
            raise ValueError(f"Unknown field type: {field.field_type_handle}")

        # Get postgres type from field type
        postgres_type = field_type.postgres_type

        # Virtual fields (one-to-many) don't create columns
        if postgres_type == "VIRTUAL":
            return ""

        # Junction tables (many-to-many) are handled separately
        if postgres_type == "JUNCTION_TABLE":
            # These need special handling - create separate table
            # For now, skip in main table creation
            return ""

        column_name = field.handle

        # Determine if field is required
        is_required = assignment.is_required_override or field.is_required

        # Build column definition
        parts = [f'"{column_name}"', postgres_type]

        # Add constraints
        if field.default_value:
            # Escape single quotes in default value
            default_escaped = field.default_value.replace("'", "''")
            parts.append(f"DEFAULT '{default_escaped}'")
        elif is_required and postgres_type not in ["UUID"]:
            # For required fields without default, add a safe default
            if postgres_type in ["VARCHAR(255)", "TEXT"]:
                parts.append("DEFAULT ''")
            elif postgres_type in ["INTEGER", "NUMERIC"]:
                parts.append("DEFAULT 0")
            elif postgres_type == "BOOLEAN":
                parts.append("DEFAULT FALSE")
            elif postgres_type == "TIMESTAMP WITH TIME ZONE":
                parts.append("DEFAULT NOW()")

        # NOT NULL constraint
        if is_required:
            parts.append("NOT NULL")

        # UNIQUE constraint
        if field.is_unique:
            parts.append("UNIQUE")

        # Foreign key for many-to-one relations
        if field.field_type_handle == "relation_many_to_one" and field.related_section_id:
            related_section_table = field.related_section.table_name
            on_delete = field.field_settings.get("onDelete", "CASCADE")
            # Use schema-qualified table name for foreign key
            if schema_name:
                fk_table = f'"{schema_name}"."{related_section_table}"'
            else:
                fk_table = f'"{related_section_table}"'
            parts.append(f'REFERENCES {fk_table}("id") ON DELETE {on_delete}')

        return ' '.join(parts)

    def generate_junction_table_sql(
        self,
        section: Section,
        field
    ) -> str:
        """
        Generate CREATE TABLE SQL for a many-to-many junction table.

        Args:
            section: The source section
            field: The many-to-many field

        Returns:
            SQL to create the junction table
        """
        if field.field_type_handle != "relation_many_to_many":
            return ""

        if not field.related_section_id:
            raise ValueError("Many-to-many field must have a related_section_id")

        junction_table = f"{section.table_name}_{field.handle}_relations"
        source_table = section.table_name
        target_table = field.related_section.table_name

        sql = f'''CREATE TABLE IF NOT EXISTS "{junction_table}" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "source_id" UUID NOT NULL REFERENCES "{source_table}"("id") ON DELETE CASCADE,
    "target_id" UUID NOT NULL REFERENCES "{target_table}"("id") ON DELETE CASCADE,
    "sort_order" INTEGER DEFAULT 0,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    UNIQUE("source_id", "target_id")
);'''

        return sql


def get_migration_generator() -> MigrationGeneratorService:
    """Get migration generator service instance"""
    return MigrationGeneratorService()
