from uuid import UUID, uuid4
from typing import List

from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi import HTTPException

from db.session import get_db
from models import ChatWindow, NodeSetup, NodeSetupVersion, Project
from schemas.chat_window import ChatWindowCreateIn, ChatWindowUpdateIn


class ChatWindowRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_by_project(self, project: Project) -> List[ChatWindow]:
        return self.db.query(ChatWindow).filter(ChatWindow.project_id == project.id).all()

    def get_one_with_versions_by_id(self, chat_window_id: UUID, project: Project) -> ChatWindow | None:
        chat_window = self.db.query(ChatWindow).filter(
            ChatWindow.id == str(chat_window_id),
            ChatWindow.project_id == project.id
        ).first()

        if not chat_window:
            raise HTTPException(status_code=404, detail="Chat window not found")

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="chat_window",
            object_id=chat_window.id
        ).first()

        chat_window.node_setup = node_setup

        return chat_window

    def get_by_id_or_404(self, chat_window_id: UUID) -> ChatWindow:
        chat_window = self.db.query(ChatWindow).filter(
            ChatWindow.id == str(chat_window_id)
        ).first()

        if not chat_window:
            raise HTTPException(status_code=404, detail="Chat window not found")

        return chat_window

    def create(self, data: ChatWindowCreateIn, project: Project) -> ChatWindow:
        chat_window = ChatWindow(
            id=uuid4(),
            name=data.name,
            description=data.description,
            project_id=project.id,
        )
        self.db.add(chat_window)
        self.db.flush()

        node_setup = NodeSetup(id=uuid4(), content_type="chat_window", object_id=chat_window.id)
        self.db.add(node_setup)
        self.db.flush()

        version = NodeSetupVersion(
            id=uuid4(),
            node_setup_id=node_setup.id,
            content={}
        )
        self.db.add(version)

        self.db.commit()
        self.db.refresh(chat_window)

        chat_window.node_setup = node_setup
        return chat_window

    def update(self, chat_window_id: UUID, data: ChatWindowUpdateIn, project: Project) -> ChatWindow:
        chat_window = self.get_one_with_versions_by_id(chat_window_id, project)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(chat_window, key, value)

        self.db.commit()
        self.db.refresh(chat_window)

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="chat_window",
            object_id=chat_window.id
        ).first()

        chat_window.node_setup = node_setup
        return chat_window

    def delete(self, chat_window_id: UUID, project: Project):
        chat_window = self.get_one_with_versions_by_id(chat_window_id, project)
        self.db.delete(chat_window)
        self.db.commit()


def get_chat_window_repository(db: Session = Depends(get_db)) -> ChatWindowRepository:
    return ChatWindowRepository(db)
