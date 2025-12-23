from uuid import UUID

from models import Project
from repositories.embed_token_repository import EmbedTokenRepository, get_embed_token_repository
from schemas.embed_token import EmbedTokenOut, EmbedTokenListOut, EmbedTokenCreateIn, EmbedTokenUpdateIn
from utils.get_current_account import get_project_or_403

import logging
from fastapi import APIRouter, Depends, Path, status

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[EmbedTokenListOut])
def list_embed_tokens(
    chat_window_id: UUID | None = None,
    project: Project = Depends(get_project_or_403),
    embed_token_repository: EmbedTokenRepository = Depends(get_embed_token_repository),
):
    """List all embed tokens for the project, optionally filtered by chat window."""
    if chat_window_id:
        return embed_token_repository.get_all_by_chat_window(chat_window_id, project)
    return embed_token_repository.get_all_by_project(project)


@router.post("/", response_model=EmbedTokenOut, status_code=status.HTTP_201_CREATED)
def create_embed_token(
    data: EmbedTokenCreateIn,
    project: Project = Depends(get_project_or_403),
    embed_token_repository: EmbedTokenRepository = Depends(get_embed_token_repository),
):
    """Create a new embed token for a chat window."""
    return embed_token_repository.create(data, project)


@router.get("/{token_id}/", response_model=EmbedTokenOut)
def get_embed_token(
    token_id: UUID = Path(),
    project: Project = Depends(get_project_or_403),
    embed_token_repository: EmbedTokenRepository = Depends(get_embed_token_repository),
):
    """Get embed token details."""
    return embed_token_repository.get_by_id_or_404(token_id, project)


@router.patch("/{token_id}/", response_model=EmbedTokenOut)
def update_embed_token(
    token_id: UUID,
    data: EmbedTokenUpdateIn,
    project: Project = Depends(get_project_or_403),
    embed_token_repository: EmbedTokenRepository = Depends(get_embed_token_repository),
):
    """Update embed token settings."""
    return embed_token_repository.update(token_id, data, project)


@router.delete("/{token_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_embed_token(
    token_id: UUID,
    project: Project = Depends(get_project_or_403),
    embed_token_repository: EmbedTokenRepository = Depends(get_embed_token_repository),
):
    """Delete an embed token."""
    embed_token_repository.delete(token_id, project)
    return None
