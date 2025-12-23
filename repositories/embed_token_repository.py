from uuid import UUID, uuid4
from typing import List
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from models import EmbedToken, ChatWindow, Project
from schemas.embed_token import EmbedTokenCreateIn, EmbedTokenUpdateIn


class EmbedTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_by_project(self, project: Project) -> List[EmbedToken]:
        """Get all embed tokens for a project."""
        return self.db.query(EmbedToken).filter(EmbedToken.project_id == project.id).all()

    def get_all_by_chat_window(self, chat_window_id: UUID, project: Project) -> List[EmbedToken]:
        """Get all embed tokens for a specific chat window."""
        return self.db.query(EmbedToken).filter(
            EmbedToken.chat_window_id == chat_window_id,
            EmbedToken.project_id == project.id
        ).all()

    def get_by_id(self, token_id: UUID, project: Project) -> EmbedToken | None:
        """Get embed token by ID."""
        return self.db.query(EmbedToken).filter(
            EmbedToken.id == token_id,
            EmbedToken.project_id == project.id
        ).first()

    def get_by_id_or_404(self, token_id: UUID, project: Project) -> EmbedToken:
        """Get embed token by ID or raise 404."""
        token = self.get_by_id(token_id, project)
        if not token:
            raise HTTPException(status_code=404, detail="Embed token not found")
        return token

    def get_by_token(self, token: str) -> EmbedToken | None:
        """Get embed token by the token string (for public API auth)."""
        return self.db.query(EmbedToken).filter(
            EmbedToken.token == token,
            EmbedToken.is_active == True
        ).first()

    def get_by_token_or_401(self, token: str) -> EmbedToken:
        """Get embed token by token string or raise 401."""
        embed_token = self.get_by_token(token)
        if not embed_token:
            raise HTTPException(status_code=401, detail="Invalid or inactive embed token")
        return embed_token

    def create(self, data: EmbedTokenCreateIn, project: Project) -> EmbedToken:
        """Create a new embed token."""
        # Verify chat window exists and belongs to project
        chat_window = self.db.query(ChatWindow).filter(
            ChatWindow.id == data.chat_window_id,
            ChatWindow.project_id == project.id
        ).first()

        if not chat_window:
            raise HTTPException(status_code=404, detail="Chat window not found")

        embed_token = EmbedToken(
            id=uuid4(),
            chat_window_id=data.chat_window_id,
            project_id=project.id,
            sessions_enabled=data.sessions_enabled if data.sessions_enabled is not None else True,
            sidebar_visible=data.sidebar_visible if data.sidebar_visible is not None else True,
            is_active=True,
        )

        self.db.add(embed_token)
        self.db.commit()
        self.db.refresh(embed_token)

        return embed_token

    def update(self, token_id: UUID, data: EmbedTokenUpdateIn, project: Project) -> EmbedToken:
        """Update an embed token."""
        embed_token = self.get_by_id_or_404(token_id, project)

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(embed_token, key, value)

        self.db.commit()
        self.db.refresh(embed_token)

        return embed_token

    def delete(self, token_id: UUID, project: Project) -> None:
        """Delete an embed token."""
        embed_token = self.get_by_id_or_404(token_id, project)
        self.db.delete(embed_token)
        self.db.commit()

    def record_usage(self, embed_token: EmbedToken) -> None:
        """Record usage of an embed token."""
        embed_token.last_used_at = datetime.now(timezone.utc)
        embed_token.usage_count += 1
        self.db.commit()


def get_embed_token_repository(db: Session = Depends(get_db)) -> EmbedTokenRepository:
    return EmbedTokenRepository(db)
