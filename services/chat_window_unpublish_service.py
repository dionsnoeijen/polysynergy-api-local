import logging

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from models import ChatWindow, NodeSetup, NodeSetupVersionStage, Stage
from services.lambda_service import LambdaService, get_lambda_service

logger = logging.getLogger(__name__)


class ChatWindowUnpublishService:
    def __init__(
        self,
        db: Session,
        lambda_service: LambdaService,
    ):
        self.db = db
        self.lambda_service = lambda_service

    def unpublish(self, chat_window: ChatWindow):
        # Chat windows always use "mock" stage
        stage = 'mock'

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="chat_window",
            object_id=chat_window.id
        ).first()

        if not node_setup:
            raise HTTPException(status_code=404, detail="NodeSetup not found")

        version = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)
        node_setup_version = version[0] if version else None

        if not node_setup_version:
            raise HTTPException(status_code=404, detail="NodeSetupVersion not found")

        function_name = f"node_setup_{str(node_setup_version.id)}_{stage}"

        self.lambda_service.delete_lambda(function_name)
        logger.debug(f"Deleted Lambda function: {function_name}")

        # Delete the stage link
        deleted = self.db.query(NodeSetupVersionStage).filter(
            NodeSetupVersionStage.stage.has(name=stage, project=chat_window.project),
            NodeSetupVersionStage.node_setup == node_setup
        ).delete(synchronize_session=False)

        self.db.commit()
        logger.debug(f"Deleted {deleted} NodeSetupVersionStage link(s)")


def get_chat_window_unpublish_service(
    db: Session = Depends(get_db),
    lambda_service: LambdaService = Depends(get_lambda_service),
) -> ChatWindowUnpublishService:
    return ChatWindowUnpublishService(
        db=db,
        lambda_service=lambda_service,
    )
