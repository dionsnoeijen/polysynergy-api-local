"""Migration Service - Handles generation and execution of section migrations"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine

from models import Section, SectionMigration, SectionFieldAssignment
from services.migration_generator_service import MigrationGeneratorService


class MigrationService:
    """
    Service for managing section migrations.

    This service:
    - Generates SQL for content table migrations
    - Saves migration records to section_migrations table
    - Executes migrations on the content database
    - Tracks migration status and errors
    """

    def __init__(self, session: Session):
        self.session = session
        self.generator = MigrationGeneratorService()

    def generate_and_apply_migration(
        self,
        section: Section,
        migration_type: str = "auto",
        applied_by: str = "system"
    ) -> SectionMigration | None:
        """
        Generate and immediately apply a migration for a section.

        Automatically detects if table needs to be created or just updated.

        Args:
            section: The section to migrate
            migration_type: Type of migration (auto, create_table, add_field, etc.)
            applied_by: Username/identifier of who triggered the migration

        Returns:
            The created migration record, or None if no migration needed

        Raises:
            Exception: If migration fails to apply
        """
        # Get all field assignments for this section
        field_assignments = section.field_assignments

        # Get project schema name
        schema_name = section.project.schema_name

        # Check if table exists
        table_exists = self._table_exists(section.table_name, schema_name, section)

        # Determine migration type if auto
        if migration_type == "auto":
            if not table_exists:
                migration_type = "create_table"
            else:
                migration_type = "alter_table"

        # Generate SQL based on migration type
        if migration_type == "create_table":
            migration_sql = self.generator.generate_create_table_sql(section, field_assignments, schema_name)
            db_info = f" in {section.database_connection.label}" if section.database_connection else ""
            description = f"Create schema '{schema_name}' and table '{schema_name}.{section.table_name}'{db_info} for section '{section.label}'"
        elif migration_type == "alter_table":
            # Get full schema from database (column -> {type, nullable, default})
            existing_columns = self._get_existing_columns(section.table_name, schema_name, section)
            existing_col_names = set(existing_columns.keys())

            # Get expected columns from field assignments
            expected_col_names = {assignment.field.handle for assignment in field_assignments}

            # Find NEW columns (in expected but not in existing)
            columns_to_add = expected_col_names - existing_col_names

            # Find REMOVED columns (in existing but not in expected)
            # For safety, we DON'T automatically drop columns
            columns_removed = existing_col_names - expected_col_names
            if columns_removed:
                print(f"⚠ Warning: Columns exist in DB but not in section: {columns_removed}")
                print(f"   These will NOT be automatically dropped for data safety")

            if not columns_to_add:
                # No new columns to add
                print(f"✓ Section '{section.label}' schema is up to date (no new columns)")
                return None

            # Generate ALTER TABLE statements for new columns
            alter_statements = []
            for assignment in field_assignments:
                if assignment.field.handle in columns_to_add:
                    alter_sql = self.generator.generate_add_column_sql(section, assignment, schema_name)
                    if alter_sql:  # Skip virtual fields
                        alter_statements.append(alter_sql)

            if not alter_statements:
                return None

            migration_sql = '\n'.join(alter_statements)
            db_info = f" in {section.database_connection.label}" if section.database_connection else ""
            description = f"Add {len(alter_statements)} column(s) to '{schema_name}.{section.table_name}'{db_info}: {', '.join(columns_to_add)}"
        else:
            raise ValueError(f"Unsupported migration type: {migration_type}")

        # Get next version number for this section
        last_migration = (
            self.session.query(SectionMigration)
            .filter(SectionMigration.section_id == section.id)
            .order_by(SectionMigration.version.desc())
            .first()
        )
        next_version = (last_migration.version + 1) if last_migration else 1

        # Create migration record
        migration = SectionMigration(
            section_id=section.id,
            migration_type=migration_type,
            migration_sql=migration_sql,
            description=description,
            status="generated",
            generated_by=applied_by,
            version=next_version
        )

        self.session.add(migration)
        self.session.flush()  # Get the ID but don't commit yet

        # Try to apply the migration
        try:
            self._execute_migration_sql(migration_sql, section)

            # Mark migration as applied
            migration.status = "applied"
            migration.applied_by = applied_by
            migration.applied_at = datetime.now(timezone.utc)

            # Update section migration status
            section.migration_status = "migrated"
            section.last_migration_id = migration.id

            self.session.commit()

            return migration

        except Exception as e:
            # Mark as failed
            migration.status = "failed"
            migration.error_message = str(e)
            section.migration_status = "failed"
            self.session.commit()

            raise Exception(f"Migration failed: {str(e)}") from e

    def _get_content_db_connection(self, section: Section):
        """
        Get database connection for the section's content.

        Args:
            section: The section to get connection for

        Returns:
            Database connection (engine or session connection)
        """
        if section.database_connection:
            # Use section's specific database connection
            connection_string = section.database_connection.get_connection_string()
            engine = create_engine(connection_string)
            return engine.connect()
        else:
            # Use default sections_db for content storage
            import os
            sections_db_url = os.getenv(
                'SECTIONS_DATABASE_URL',
                'postgresql://sections_user:sections_password@sections_db:5432/sections_db'
            )
            engine = create_engine(sections_db_url)
            return engine.connect()

    def _table_exists(self, table_name: str, schema_name: str, section: Section) -> bool:
        """
        Check if a table exists in the database schema.

        Args:
            table_name: Name of the table to check
            schema_name: PostgreSQL schema name
            section: Section to get database connection from

        Returns:
            True if table exists, False otherwise
        """
        try:
            conn = self._get_content_db_connection(section)
            result = conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = :schema_name
                        AND table_name = :table_name
                    );
                """),
                {"schema_name": schema_name, "table_name": table_name}
            )
            exists = result.scalar()

            # Always close the connection (it's always a separate engine now)
            conn.close()

            return exists
        except Exception:
            return False

    def _get_existing_columns(self, table_name: str, schema_name: str, section: Section) -> dict[str, dict]:
        """
        Get existing columns with their full definition from database.

        Args:
            table_name: Name of the table
            schema_name: PostgreSQL schema name
            section: Section to get database connection from

        Returns:
            Dict of column_name -> {type, nullable, default} (excluding standard columns)
        """
        try:
            conn = self._get_content_db_connection(section)
            result = conn.execute(
                text("""
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = :schema_name
                    AND table_name = :table_name
                    AND column_name NOT IN ('id', 'created_at', 'updated_at')
                    ORDER BY ordinal_position;
                """),
                {"schema_name": schema_name, "table_name": table_name}
            )

            columns = {}
            for row in result.fetchall():
                col_name = row[0]
                data_type = row[1]
                if row[4]:  # character_maximum_length
                    data_type = f"{data_type}({row[4]})"

                columns[col_name] = {
                    "type": data_type.upper(),
                    "nullable": row[2] == "YES",
                    "default": row[3]
                }

            conn.close()

            return columns
        except Exception as e:
            print(f"Error getting columns: {e}")
            return {}

    def _execute_migration_sql(self, sql: str, section: Section) -> None:
        """
        Execute migration SQL on the content database.

        Args:
            sql: The SQL to execute
            section: Section to get database connection from

        Raises:
            Exception: If SQL execution fails
        """
        conn = None
        try:
            conn = self._get_content_db_connection(section)

            # Execute the raw SQL
            conn.execute(text(sql))
            conn.commit()

        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            # Always close the connection (it's always a separate engine now)
            if conn:
                conn.close()

    def get_pending_migrations(self, section_id) -> list[SectionMigration]:
        """Get all generated but not yet applied migrations for a section"""
        return (
            self.session.query(SectionMigration)
            .filter(
                SectionMigration.section_id == section_id,
                SectionMigration.status == "generated"
            )
            .order_by(SectionMigration.version)
            .all()
        )

    def get_migration_history(self, section_id) -> list[SectionMigration]:
        """Get all migrations for a section, ordered by version"""
        return (
            self.session.query(SectionMigration)
            .filter(SectionMigration.section_id == section_id)
            .order_by(SectionMigration.version)
            .all()
        )
