from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from models import Project, ChatWindow
from repositories.chat_window_repository import (
    ChatWindowRepository,
    get_chat_window_repository,
)
from repositories.chat_window_access_repository import (
    ChatWindowAccessRepository,
    get_chat_window_access_repository,
)
from schemas.chat_window_access import (
    ChatWindowAccessOut,
    ChatWindowAccessCreateIn,
    ChatWindowAccessUpdateIn,
)
from utils.get_current_account import get_project_or_403

router = APIRouter()


@router.get(
    "/chat-windows/{chat_window_id}/users/",
    response_model=list[ChatWindowAccessOut]
)
def list_chat_window_users(
    chat_window_id: UUID = Path(),
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
    access_repository: ChatWindowAccessRepository = Depends(
        get_chat_window_access_repository
    ),
):
    """Get all users assigned to a chat window with their permissions."""
    chat_window = chat_window_repository.get_one_with_versions_by_id(
        chat_window_id, project
    )
    return access_repository.get_all_by_chat_window(chat_window)


@router.post(
    "/chat-windows/{chat_window_id}/users/",
    response_model=ChatWindowAccessOut,
    status_code=status.HTTP_201_CREATED,
)
def assign_user_to_chat_window(
    chat_window_id: UUID,
    data: ChatWindowAccessCreateIn,
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
    access_repository: ChatWindowAccessRepository = Depends(
        get_chat_window_access_repository
    ),
):
    """Assign a user to a chat window with specific permissions."""
    chat_window = chat_window_repository.get_one_with_versions_by_id(
        chat_window_id, project
    )
    return access_repository.create(data, chat_window)


@router.patch(
    "/chat-windows/{chat_window_id}/users/{account_id}/",
    response_model=ChatWindowAccessOut,
)
def update_chat_window_user_permissions(
    chat_window_id: UUID,
    account_id: UUID,
    data: ChatWindowAccessUpdateIn,
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
    access_repository: ChatWindowAccessRepository = Depends(
        get_chat_window_access_repository
    ),
):
    """Update user permissions for a chat window."""
    # Verify chat window exists and belongs to project
    chat_window_repository.get_one_with_versions_by_id(chat_window_id, project)
    return access_repository.update(account_id, chat_window_id, data)


@router.delete(
    "/chat-windows/{chat_window_id}/users/{account_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_user_from_chat_window(
    chat_window_id: UUID,
    account_id: UUID,
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
    access_repository: ChatWindowAccessRepository = Depends(
        get_chat_window_access_repository
    ),
):
    """Remove user access from a chat window."""
    # Verify chat window exists and belongs to project
    chat_window_repository.get_one_with_versions_by_id(chat_window_id, project)
    access_repository.delete(account_id, chat_window_id)
    return None
