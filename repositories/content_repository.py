"""Content Repository - Dynamic CRUD operations for section content tables"""

import os
import json
import asyncio
from uuid import UUID
from typing import Any, Optional
from datetime import datetime, timezone

from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import Section


class ContentRepository:
    """
    Repository for dynamic CRUD operations on section content tables.

    Each section has its own table in a project-specific schema.
    This repository handles dynamic queries to those tables.
    """

    def __init__(self, session: Session, section: Section):
        self.session = session
        self.section = section
        self.schema_name = section.project.schema_name
        self.table_name = section.table_name
        self.full_table_name = f'"{self.schema_name}"."{self.table_name}"'

        # Get content database connection
        self.content_engine = self._get_content_engine()

        # Initialize vector database if vectorization is enabled
        self.section_vector_db = None
        if section.vectorization_config and section.vectorization_config.get('enabled'):
            self.section_vector_db = self._init_section_vector_db()

    def _get_content_engine(self):
        """Get SQLAlchemy engine for content database"""
        if self.section.database_connection:
            connection_string = self.section.database_connection.get_connection_string()
            return create_engine(connection_string)
        else:
            # Use default sections_db
            sections_db_url = os.getenv(
                'SECTIONS_DATABASE_URL',
                'postgresql://sections_user:sections_password@sections_db:5432/sections_db'
            )
            return create_engine(sections_db_url)

    def _init_section_vector_db(self):
        """Initialize Agno PgVector for this section"""
        try:
            from polysynergy_nodes.section.vectordb.section_pgvector import SectionPgVector
            from agno.vectordb.search import SearchType
            from agno.vectordb.distance import Distance

            config = self.section.vectorization_config

            # Get embedder based on provider
            embedder = self._get_embedder(config)

            # Get database URL
            if self.section.database_connection:
                db_url = self.section.database_connection.get_connection_string()
            else:
                db_url = os.getenv(
                    'SECTIONS_DATABASE_URL',
                    'postgresql://sections_user:sections_password@sections_db:5432/sections_db'
                )

            # Initialize section vector db
            vector_db = SectionPgVector(
                section_id=str(self.section.id),
                project_schema=self.schema_name,
                db_url=db_url,
                embedder=embedder,
                search_type=SearchType[config.get('search_type', 'hybrid')],
                distance=Distance[config.get('distance', 'cosine')]
            )

            # Create table if it doesn't exist
            vector_db.create()

            return vector_db
        except Exception as e:
            print(f"Error initializing section vector db: {e}")
            return None

    def _get_embedder(self, config: dict):
        """Get embedder instance based on provider"""
        provider = config.get('provider', 'openai')
        model = config.get('model', 'text-embedding-3-small')
        dimensions = config.get('dimensions')

        # Get API key from secrets
        api_key = self._get_api_key(config.get('api_key_secret_id'))

        if provider == 'openai':
            from agno.knowledge.embedder.openai import OpenAIEmbedder
            kwargs = {'id': model, 'api_key': api_key}
            if dimensions:
                kwargs['dimensions'] = dimensions
            return OpenAIEmbedder(**kwargs)
        elif provider == 'mistral':
            from agno.knowledge.embedder.mistral import MistralEmbedder
            kwargs = {'id': model, 'api_key': api_key}
            if dimensions:
                kwargs['dimensions'] = dimensions
            return MistralEmbedder(**kwargs)
        else:
            raise ValueError(f"Unsupported embedder provider: {provider}")

    def _get_api_key(self, secret_id: Optional[str]) -> Optional[str]:
        """Fetch API key from secrets table"""
        if not secret_id:
            return None

        from models import Secret
        secret = self.session.query(Secret).filter(Secret.id == secret_id).first()
        if secret:
            return secret.value
        return None

    def _serialize_jsonb_fields(self, data: dict) -> dict:
        """
        Serialize JSONB fields (dict/list) to JSON strings for psycopg2.

        psycopg2 can't adapt Python dict/list objects directly to JSONB columns.
        We need to convert them to JSON strings first.
        """
        serialized_data = data.copy()

        # Get JSONB field handles from section field assignments
        jsonb_field_types = ['json', 'list', 'key_value']  # Field types that use JSONB storage
        jsonb_fields = set()

        for assignment in self.section.field_assignments:
            if assignment.field.field_type_handle in jsonb_field_types:
                jsonb_fields.add(assignment.field.handle)

        # Serialize dict/list values to JSON strings
        for field_handle in jsonb_fields:
            if field_handle in serialized_data:
                value = serialized_data[field_handle]
                if value is not None and isinstance(value, (dict, list)):
                    serialized_data[field_handle] = json.dumps(value)

        return serialized_data

    def _serialize_metadata_value(self, value: Any) -> Any:
        """Convert non-JSON-serializable values to JSON-serializable types."""
        if value is None:
            return None
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (dict, list)):
            # Already JSON serializable
            return value
        # For other types, convert to string
        return str(value)

    def _sync_to_embeddings(self, record: dict):
        """
        Sync record to Agno embeddings table (blocking version for sync callers).

        This is called from sync contexts (create/update methods).
        """
        if not self.section_vector_db:
            return

        try:
            config = self.section.vectorization_config

            # Combine source fields into content text
            source_fields = config.get('source_fields', [])
            content_parts = [
                str(record.get(field, ''))
                for field in source_fields
                if record.get(field)
            ]
            content = ' '.join(content_parts)

            if not content.strip():
                print(f"Warning: No content to vectorize for record {record.get('id')}")
                return

            # Extract metadata fields and serialize to JSON-compatible types
            metadata_fields = config.get('metadata_fields', [])
            metadata = {
                field: self._serialize_metadata_value(record.get(field))
                for field in metadata_fields
                if field in record
            }

            # Use first source field as name, or fallback to record id
            name = record.get(source_fields[0]) if source_fields else str(record.get('id'))

            # Sync to embeddings table
            self.section_vector_db.sync_from_section_record(
                record_id=str(record['id']),
                content=content,
                meta_data=metadata,
                name=str(name) if name else None
            )
        except Exception as e:
            print(f"Error syncing record to embeddings: {e}")

    async def _sync_to_embeddings_async(self, record: dict):
        """
        Async version that runs vectorization in background without blocking request.

        Wraps sync _sync_to_embeddings in thread pool.
        """
        try:
            await asyncio.to_thread(self._sync_to_embeddings, record)
        except Exception as e:
            print(f"Error in background vectorization: {e}")

    def create(self, data: dict) -> dict:
        """
        Create a new record in the content table.

        Args:
            data: Dictionary with field values

        Returns:
            Created record with id and timestamps
        """
        # Serialize JSONB fields (dict/list) to JSON strings
        serialized_data = self._serialize_jsonb_fields(data)

        # Build column and value lists
        columns = list(serialized_data.keys())
        placeholders = [f":{col}" for col in columns]

        columns_sql = ', '.join([f'"{col}"' for col in columns])
        placeholders_sql = ', '.join(placeholders)

        # Insert query with RETURNING
        sql = f"""
            INSERT INTO {self.full_table_name} ({columns_sql})
            VALUES ({placeholders_sql})
            RETURNING id, created_at, updated_at, {columns_sql}
        """

        with self.content_engine.connect() as conn:
            result = conn.execute(text(sql), serialized_data)
            conn.commit()

            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=500, detail="Failed to create record")

            # Convert row to dict
            record = dict(row._mapping)

            # Note: Vectorization is handled by caller (API endpoint via background task)
            # to avoid blocking the HTTP response

            return record

    def get_by_id(self, record_id: UUID) -> Optional[dict]:
        """
        Get a single record by ID.

        Args:
            record_id: UUID of the record

        Returns:
            Record dict or None if not found
        """
        sql = f"""
            SELECT * FROM {self.full_table_name}
            WHERE id = :record_id
        """

        with self.content_engine.connect() as conn:
            result = conn.execute(text(sql), {"record_id": str(record_id)})
            row = result.fetchone()

            if not row:
                return None

            return dict(row._mapping)

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        order_direction: str = "DESC",
        search: Optional[str] = None
    ) -> list[dict]:
        """
        Get all records with pagination and optional search.

        Args:
            limit: Max number of records to return
            offset: Number of records to skip
            order_by: Column to order by
            order_direction: ASC or DESC
            search: Optional search term (searches all text/varchar columns)

        Returns:
            List of record dicts
        """
        # Validate order_direction
        if order_direction.upper() not in ["ASC", "DESC"]:
            order_direction = "DESC"

        # Build WHERE clause for search
        where_clause = ""
        params = {"limit": limit, "offset": offset}

        if search:
            # Get all searchable columns from field assignments
            text_columns = []
            for assignment in self.section.field_assignments:
                field_type = assignment.field.field_type_handle
                # Include text, email, url fields in search
                if field_type in ['text', 'email', 'url']:
                    text_columns.append(assignment.field.handle)

            if text_columns:
                # Use PostgreSQL Full Text Search with to_tsvector
                # Concatenate all text columns and search them
                columns_concat = ' || \' \' || '.join([
                    f'COALESCE("{col}"::text, \'\')'
                    for col in text_columns
                ])

                # Use plainto_tsquery for simple search (handles spaces, etc.)
                where_clause = f"""
                    WHERE to_tsvector('simple', {columns_concat}) @@ plainto_tsquery('simple', :search)
                """
                params['search'] = search

        sql = f"""
            SELECT * FROM {self.full_table_name}
            {where_clause}
            ORDER BY "{order_by}" {order_direction}
            LIMIT :limit OFFSET :offset
        """

        with self.content_engine.connect() as conn:
            result = conn.execute(text(sql), params)
            return [dict(row._mapping) for row in result.fetchall()]

    def count(self) -> int:
        """
        Count total number of records.

        Returns:
            Total record count
        """
        sql = f"SELECT COUNT(*) as count FROM {self.full_table_name}"

        with self.content_engine.connect() as conn:
            result = conn.execute(text(sql))
            row = result.fetchone()
            return row[0] if row else 0

    def update(self, record_id: UUID, data: dict) -> dict:
        """
        Update a record.

        Args:
            record_id: UUID of the record
            data: Dictionary with field values to update

        Returns:
            Updated record dict
        """
        # Add updated_at timestamp
        data['updated_at'] = datetime.now(timezone.utc)

        # Serialize JSONB fields (dict/list) to JSON strings
        serialized_data = self._serialize_jsonb_fields(data)

        # Build SET clause
        set_clauses = [f'"{col}" = :{col}' for col in serialized_data.keys()]
        set_sql = ', '.join(set_clauses)

        # Get all columns for RETURNING
        columns = list(serialized_data.keys())

        sql = f"""
            UPDATE {self.full_table_name}
            SET {set_sql}
            WHERE id = :record_id
            RETURNING *
        """

        params = {**serialized_data, "record_id": str(record_id)}

        with self.content_engine.connect() as conn:
            result = conn.execute(text(sql), params)
            conn.commit()

            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Record not found")

            record = dict(row._mapping)

            # Note: Vectorization is handled by caller (API endpoint via background task)
            # to avoid blocking the HTTP response

            return record

    def delete(self, record_id: UUID) -> bool:
        """
        Delete a record.

        Args:
            record_id: UUID of the record

        Returns:
            True if deleted, False if not found
        """
        sql = f"""
            DELETE FROM {self.full_table_name}
            WHERE id = :record_id
        """

        with self.content_engine.connect() as conn:
            result = conn.execute(text(sql), {"record_id": str(record_id)})
            conn.commit()

            success = result.rowcount > 0

            # Delete from embeddings if vectorization enabled
            if success and self.section_vector_db:
                try:
                    self.section_vector_db.delete_by_record_id(str(record_id))
                except Exception as e:
                    print(f"Error deleting from embeddings: {e}")

            return success

    def get_selected_fields(
        self,
        field_handles: list[str],
        limit: int = 1000,
        offset: int = 0,
        search: Optional[str] = None
    ) -> list[dict]:
        """
        Get records with only selected fields.

        Args:
            field_handles: List of field handles to include in results
            limit: Max number of records
            offset: Number of records to skip
            search: Optional search term

        Returns:
            List of records with only selected fields
        """
        # Always include system fields
        system_fields = ["id", "created_at", "updated_at"]
        all_fields = system_fields + field_handles

        # Build SELECT clause with only requested fields
        columns_sql = ', '.join([f'"{col}"' for col in all_fields])

        # Build WHERE clause for search if needed
        where_clause = ""
        params = {"limit": limit, "offset": offset}

        if search:
            # Get all searchable columns from section field assignments
            text_columns = []
            for assignment in self.section.field_assignments:
                field_type = assignment.field.field_type_handle
                if field_type in ['text', 'email', 'url'] and assignment.field.handle in field_handles:
                    text_columns.append(assignment.field.handle)

            if text_columns:
                columns_concat = ' || \' \' || '.join([
                    f'COALESCE("{col}"::text, \'\')'
                    for col in text_columns
                ])
                where_clause = f"""
                    WHERE to_tsvector('simple', {columns_concat}) @@ plainto_tsquery('simple', :search)
                """
                params['search'] = search

        sql = f"""
            SELECT {columns_sql}
            FROM {self.full_table_name}
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """

        with self.content_engine.connect() as conn:
            result = conn.execute(text(sql), params)
            return [dict(row._mapping) for row in result.fetchall()]


def get_content_repository(session: Session, section: Section) -> ContentRepository:
    """Dependency for content repository"""
    return ContentRepository(session, section)
