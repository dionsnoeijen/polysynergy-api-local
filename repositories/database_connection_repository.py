"""Database Connection Repository - Data access layer for database connections"""

from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from db.session import get_db
from models import DatabaseConnection, Project
from schemas.database_connection import DatabaseConnectionCreate, DatabaseConnectionUpdate


class DatabaseConnectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_404(self, connection_id: UUID, project: Project) -> DatabaseConnection:
        """Get a database connection by ID within a project"""
        stmt = (
            select(DatabaseConnection)
            .where(DatabaseConnection.id == connection_id)
            .where(DatabaseConnection.project_id == project.id)
            .where(DatabaseConnection.deleted_at.is_(None))
        )
        connection = self.session.scalar(stmt)
        if not connection:
            raise HTTPException(status_code=404, detail="Database connection not found")
        return connection

    def get_for_update_or_404(self, connection_id: UUID, project: Project) -> DatabaseConnection:
        """Get a database connection for update"""
        return self.get_or_404(connection_id, project)

    def get_all_by_project(
        self,
        project: Project,
        include_inactive: bool = False
    ) -> list[DatabaseConnection]:
        """Get all database connections in a project"""
        stmt = (
            select(DatabaseConnection)
            .where(DatabaseConnection.project_id == project.id)
            .where(DatabaseConnection.deleted_at.is_(None))
        )

        if not include_inactive:
            stmt = stmt.where(DatabaseConnection.is_active == True)

        return list(self.session.scalars(stmt.order_by(DatabaseConnection.label)).all())

    def create(self, connection_data: DatabaseConnectionCreate, project: Project) -> DatabaseConnection:
        """Create a new database connection"""
        # Check if handle is unique within project
        existing = self.session.query(DatabaseConnection).filter(
            DatabaseConnection.project_id == project.id,
            DatabaseConnection.handle == connection_data.handle,
            DatabaseConnection.deleted_at.is_(None)
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Database connection with handle '{connection_data.handle}' already exists in this project"
            )

        connection = DatabaseConnection(
            **connection_data.model_dump(),
            project_id=project.id
        )

        self.session.add(connection)
        self.session.commit()
        self.session.refresh(connection)

        return connection

    def update(
        self,
        connection_id: UUID,
        connection_data: DatabaseConnectionUpdate,
        project: Project
    ) -> DatabaseConnection:
        """Update an existing database connection"""
        connection = self.get_for_update_or_404(connection_id, project)

        # Update only provided fields
        update_data = connection_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(connection, field, value)

        connection.updated_at = datetime.now(timezone.utc)

        self.session.commit()
        self.session.refresh(connection)

        return connection

    def delete(self, connection_id: UUID, project: Project) -> None:
        """Soft delete a database connection"""
        connection = self.get_or_404(connection_id, project)

        # Check if any sections are using this connection
        from models import Section
        sections_using = self.session.query(Section).filter(
            Section.database_connection_id == connection_id,
            Section.deleted_at.is_(None)
        ).count()

        if sections_using > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete database connection. {sections_using} section(s) are still using it."
            )

        connection.deleted_at = datetime.now(timezone.utc)
        self.session.commit()


def get_database_connection_repository(db: Session = Depends(get_db)) -> DatabaseConnectionRepository:
    """Dependency for database connection repository"""
    return DatabaseConnectionRepository(db)
