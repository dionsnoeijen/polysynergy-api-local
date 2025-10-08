from uuid import UUID, uuid4
from typing import List

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from db.session import get_db
from models import ChatWindowAccess, ChatWindow, Account
from schemas.chat_window_access import ChatWindowAccessCreateIn, ChatWindowAccessUpdateIn


class ChatWindowAccessRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_by_chat_window(self, chat_window: ChatWindow) -> List[ChatWindowAccess]:
        """Get all user accesses for a chat window."""
        return (
            self.db.query(ChatWindowAccess)
            .filter(ChatWindowAccess.chat_window_id == chat_window.id)
            .options(joinedload(ChatWindowAccess.account))
            .all()
        )

    def get_by_account_and_chat_window(
        self, account_id: UUID, chat_window_id: UUID
    ) -> ChatWindowAccess | None:
        """Get access record for specific account and chat window."""
        return (
            self.db.query(ChatWindowAccess)
            .filter(
                ChatWindowAccess.account_id == account_id,
                ChatWindowAccess.chat_window_id == chat_window_id,
            )
            .options(joinedload(ChatWindowAccess.account))
            .first()
        )

    def create(
        self, data: ChatWindowAccessCreateIn, chat_window: ChatWindow
    ) -> ChatWindowAccess:
        """Assign a user to a chat window with permissions."""
        # Check if account exists
        account = self.db.query(Account).filter(Account.id == data.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Check if access already exists
        existing = self.get_by_account_and_chat_window(
            data.account_id, chat_window.id
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="This user already has access to this chat window",
            )

        access = ChatWindowAccess(
            id=uuid4(),
            account_id=data.account_id,
            chat_window_id=chat_window.id,
            can_view_flow=data.can_view_flow,
            can_view_output=data.can_view_output,
            show_response_transparency=data.show_response_transparency,
        )
        self.db.add(access)
        self.db.commit()
        self.db.refresh(access)

        return access

    def update(
        self,
        account_id: UUID,
        chat_window_id: UUID,
        data: ChatWindowAccessUpdateIn,
    ) -> ChatWindowAccess:
        """Update user permissions for a chat window."""
        access = self.get_by_account_and_chat_window(account_id, chat_window_id)
        if not access:
            raise HTTPException(status_code=404, detail="Access record not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(access, key, value)

        self.db.commit()
        self.db.refresh(access)

        return access

    def delete(self, account_id: UUID, chat_window_id: UUID):
        """Remove user access from a chat window."""
        access = self.get_by_account_and_chat_window(account_id, chat_window_id)
        if not access:
            raise HTTPException(status_code=404, detail="Access record not found")

        self.db.delete(access)
        self.db.commit()

    def get_chat_windows_for_account(self, account_id: UUID) -> List[ChatWindowAccess]:
        """Get all chat windows that a user has access to."""
        return (
            self.db.query(ChatWindowAccess)
            .filter(ChatWindowAccess.account_id == account_id)
            .options(joinedload(ChatWindowAccess.chat_window))
            .all()
        )

    def get_chat_windows_with_details_for_account(self, account_id: UUID):
        """Get all chat windows for an account with project and tenant details."""
        from models import ChatWindow, Project

        accesses = (
            self.db.query(ChatWindowAccess)
            .filter(ChatWindowAccess.account_id == account_id)
            .options(joinedload(ChatWindowAccess.chat_window))
            .all()
        )

        # Manually load project and tenant for each chat window
        for access in accesses:
            if access.chat_window:
                project = (
                    self.db.query(Project)
                    .filter(Project.id == access.chat_window.project_id)
                    .options(joinedload(Project.tenant))
                    .first()
                )
                access.chat_window.project = project

        return accesses


def get_chat_window_access_repository(
    db: Session = Depends(get_db),
) -> ChatWindowAccessRepository:
    return ChatWindowAccessRepository(db)
