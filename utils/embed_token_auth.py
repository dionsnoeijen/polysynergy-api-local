"""
Embed token authentication for embedded chat endpoints
"""
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from models import EmbedToken, ChatWindow, Project
from repositories.embed_token_repository import EmbedTokenRepository, get_embed_token_repository


class EmbedTokenContext:
    """Context object containing validated embed token data."""

    def __init__(
        self,
        embed_token: EmbedToken,
        chat_window: ChatWindow,
        project: Project
    ):
        self.embed_token = embed_token
        self.chat_window = chat_window
        self.project = project

    @property
    def sessions_enabled(self) -> bool:
        return self.embed_token.sessions_enabled

    @property
    def sidebar_visible(self) -> bool:
        return self.embed_token.sidebar_visible


async def get_embed_token_context(
    x_embed_token: Optional[str] = Header(None, alias="X-Embed-Token", description="Embed token for authentication"),
    embed_token_repository: EmbedTokenRepository = Depends(get_embed_token_repository),
    db: Session = Depends(get_db)
) -> EmbedTokenContext:
    """
    Validate embed token from X-Embed-Token header and return context.

    Args:
        x_embed_token: Embed token from X-Embed-Token header
        embed_token_repository: Repository instance
        db: Database session

    Returns:
        EmbedTokenContext with embed token, chat window, and project

    Raises:
        HTTPException: If token is missing, invalid, or inactive
    """
    if not x_embed_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Embed-Token header",
            headers={"WWW-Authenticate": "EmbedToken"},
        )

    try:
        # Find embed token
        embed_token = embed_token_repository.get_by_token(x_embed_token)

        if not embed_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive embed token",
                headers={"WWW-Authenticate": "EmbedToken"},
            )

        # Get chat window
        chat_window = db.query(ChatWindow).filter(
            ChatWindow.id == embed_token.chat_window_id
        ).first()

        if not chat_window:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat window not found"
            )

        # Get project
        project = db.query(Project).filter(
            Project.id == embed_token.project_id
        ).first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Record usage
        embed_token_repository.record_usage(embed_token)

        return EmbedTokenContext(
            embed_token=embed_token,
            chat_window=chat_window,
            project=project
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embed token validation failed: {str(e)}"
        )
