"""Database Connections API endpoints - CRUD operations for database connections"""

from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import time

from models import Project
from schemas.database_connection import (
    DatabaseConnectionCreate,
    DatabaseConnectionUpdate,
    DatabaseConnectionRead,
    DatabaseConnectionTest
)
from utils.get_current_account import get_project_or_403
from repositories.database_connection_repository import (
    DatabaseConnectionRepository,
    get_database_connection_repository
)

router = APIRouter()


@router.post("/", response_model=DatabaseConnectionRead, status_code=status.HTTP_201_CREATED)
def create_database_connection(
    connection_data: DatabaseConnectionCreate,
    project: Project = Depends(get_project_or_403),
    connection_repo: DatabaseConnectionRepository = Depends(get_database_connection_repository),
):
    """
    Create a new database connection.

    This configures an external database where section tables can be created.
    If no connection is specified for a section, the internal PolySynergy database is used.
    """
    return connection_repo.create(connection_data, project)


@router.get("/", response_model=list[DatabaseConnectionRead])
def list_database_connections(
    project: Project = Depends(get_project_or_403),
    connection_repo: DatabaseConnectionRepository = Depends(get_database_connection_repository),
    include_inactive: bool = Query(False, description="Include inactive connections"),
):
    """
    List all database connections in a project.

    Returns empty list if no external databases are configured.
    Sections can always use the internal PolySynergy database (no connection needed).
    """
    return connection_repo.get_all_by_project(project, include_inactive)


@router.get("/{connection_id}/", response_model=DatabaseConnectionRead)
def get_database_connection(
    connection_id: UUID,
    project: Project = Depends(get_project_or_403),
    connection_repo: DatabaseConnectionRepository = Depends(get_database_connection_repository),
):
    """Get database connection details (password redacted)"""
    return connection_repo.get_or_404(connection_id, project)


@router.patch("/{connection_id}/", response_model=DatabaseConnectionRead)
def update_database_connection(
    connection_id: UUID,
    update_data: DatabaseConnectionUpdate,
    project: Project = Depends(get_project_or_403),
    connection_repo: DatabaseConnectionRepository = Depends(get_database_connection_repository),
):
    """Update database connection settings"""
    return connection_repo.update(connection_id, update_data, project)


@router.delete("/{connection_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_database_connection(
    connection_id: UUID,
    project: Project = Depends(get_project_or_403),
    connection_repo: DatabaseConnectionRepository = Depends(get_database_connection_repository),
):
    """
    Soft delete a database connection.

    WARNING: Cannot delete if sections are still using this connection.
    """
    connection_repo.delete(connection_id, project)


@router.post("/{connection_id}/test/", response_model=DatabaseConnectionTest)
def test_database_connection(
    connection_id: UUID,
    project: Project = Depends(get_project_or_403),
    connection_repo: DatabaseConnectionRepository = Depends(get_database_connection_repository),
):
    """
    Test if database connection is working.

    Attempts to connect and measure latency.
    """
    connection = connection_repo.get_or_404(connection_id, project)

    try:
        start_time = time.time()
        connection_string = connection.get_connection_string()

        # Attempt to create engine and connect
        engine = create_engine(connection_string, pool_pre_ping=True)
        with engine.connect() as conn:
            # Simple query to test connection
            conn.execute("SELECT 1")

        latency_ms = (time.time() - start_time) * 1000

        return DatabaseConnectionTest(
            success=True,
            message="Connection successful",
            latency_ms=round(latency_ms, 2)
        )

    except OperationalError as e:
        return DatabaseConnectionTest(
            success=False,
            message=f"Connection failed: {str(e)}",
            latency_ms=None
        )
    except Exception as e:
        return DatabaseConnectionTest(
            success=False,
            message=f"Unexpected error: {str(e)}",
            latency_ms=None
        )
