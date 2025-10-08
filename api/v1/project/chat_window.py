from uuid import UUID

from models import Project, ChatWindow
from repositories.chat_window_repository import ChatWindowRepository, get_chat_window_repository
from schemas.chat_window import ChatWindowListOut, ChatWindowCreateIn, ChatWindowDetailOut, ChatWindowUpdateIn, \
    ChatWindowUnpublishIn, ChatWindowPublishIn
from services.chat_window_unpublish_service import ChatWindowUnpublishService, get_chat_window_unpublish_service
from utils.get_current_account import get_project_or_403

import logging
from fastapi import APIRouter, Depends, Path, HTTPException, status

from services.chat_window_publish_service import ChatWindowPublishService, get_chat_window_publish_service
from core.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=list[ChatWindowListOut])
def list_chat_windows(
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
):
    return chat_window_repository.get_all_by_project(project)

@router.post("/", response_model=ChatWindowDetailOut, status_code=status.HTTP_201_CREATED)
def create_chat_window(
    data: ChatWindowCreateIn,
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
):
    return chat_window_repository.create(data, project)

@router.get("/{chat_window_id}/", response_model=ChatWindowDetailOut)
def get_chat_window_detail(
    chat_window_id: UUID = Path(),
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
):
    return chat_window_repository.get_one_with_versions_by_id(chat_window_id, project)

@router.patch("/{chat_window_id}/", response_model=ChatWindowDetailOut)
def update_chat_window(
    chat_window_id: UUID,
    data: ChatWindowUpdateIn,
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
):
    return chat_window_repository.update(chat_window_id, data, project)

@router.delete("/{chat_window_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_window(
    chat_window_id: UUID,
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
):
    chat_window_repository.delete(chat_window_id, project)
    return None


@router.post("/{chat_window_id}/publish/", status_code=status.HTTP_202_ACCEPTED)
def publish_chat_window(
    chat_window_id: UUID,
    body: ChatWindowPublishIn,
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
    publish_service: ChatWindowPublishService = Depends(get_chat_window_publish_service)
):
    chat_window = chat_window_repository.get_one_with_versions_by_id(chat_window_id, project)

    try:
        # Skip Lambda operations when in local execution mode
        if settings.EXECUTE_NODE_SETUP_LOCAL:
            logger.info(f"Local mode: Skipping Lambda publish for chat window {chat_window_id}")
            return {"message": "Chat window publish skipped in local execution mode"}

        return publish_service.publish(chat_window)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during chat window publish for {chat_window_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during publish")

@router.post("/{chat_window_id}/unpublish/", status_code=status.HTTP_202_ACCEPTED)
def unpublish_chat_window(
    chat_window_id: UUID,
    body: ChatWindowUnpublishIn,
    project: Project = Depends(get_project_or_403),
    chat_window_repository: ChatWindowRepository = Depends(get_chat_window_repository),
    chat_window_unpublish_service: ChatWindowUnpublishService = Depends(get_chat_window_unpublish_service)
):
    chat_window = chat_window_repository.get_one_with_versions_by_id(chat_window_id, project)

    try:
        # Skip Lambda operations when in local execution mode
        if settings.EXECUTE_NODE_SETUP_LOCAL:
            logger.info(f"Local mode: Skipping Lambda unpublish for chat window {chat_window_id}")
            return {"message": "Chat window unpublish skipped in local execution mode"}

        chat_window_unpublish_service.unpublish(chat_window)
        return {"message": "Chat window successfully unpublished"}
    except Exception as e:
        logger.error(f"Error during chat window unpublish for {chat_window_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during unpublish")
