"""
API Key authentication for public endpoints
"""
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from models import Project
from services.api_key_service import ApiKeyService, get_api_key_service


async def get_project_by_api_key(
    x_api_key: Optional[str] = Header(None, description="API Key for authentication"),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
    db: Session = Depends(get_db)
) -> Project:
    """
    Validate API key from X-API-Key header and return the associated project.

    Args:
        x_api_key: API key from X-API-Key header
        api_key_service: API key service instance
        db: Database session

    Returns:
        Project associated with the API key

    Raises:
        HTTPException: If API key is missing, invalid, or project not found
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    try:
        # Query DynamoDB for API key
        # The ApiKeyService uses GSI to find by key value
        # We need to add a method to find by key string
        item = api_key_service.get_by_key(x_api_key)

        if not item:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Get the project from database
        project = db.query(Project).filter(Project.id == item.project_id).first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found for this API key"
            )

        return project

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API key validation failed: {str(e)}"
        )
