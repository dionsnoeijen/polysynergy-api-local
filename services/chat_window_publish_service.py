import logging

from sqlalchemy.orm import Session
from fastapi import HTTPException

from fastapi import Depends
from db.session import get_db
from models import ChatWindow, NodeSetupVersion, Stage, NodeSetupVersionStage, NodeSetup
from services.lambda_service import LambdaService, get_lambda_service
from services.sync_checker_service import SyncCheckerService, get_sync_checker_service
from core.settings import settings

logger = logging.getLogger(__name__)


class ChatWindowPublishService:
    def __init__(
        self,
        db: Session,
        lambda_service: LambdaService,
        sync_checker: SyncCheckerService
    ):
        self.db = db
        self.lambda_service = lambda_service
        self.sync_checker = sync_checker

    def sync_lambda(self, chat_window: ChatWindow, stage: str = 'mock'):
        # Skip Lambda operations when in local execution mode
        if settings.EXECUTE_NODE_SETUP_LOCAL:
            logger.info(f"Local mode: Skipping Lambda sync for chat window {chat_window.id}")
            return

        node_setup_version = self._validate(chat_window)

        project = chat_window.project
        function_name = f"node_setup_{node_setup_version.id}_{stage}"

        sync_status = self.sync_checker.check_sync_needed(
            node_setup_version,
            str(project.tenant.id),
            str(project.id),
            stage
        )
        logger.debug(f"Sync status: {sync_status}")

        if not sync_status['lambda_exists']:
            self.lambda_service.create_or_update_lambda(
                function_name, node_setup_version.executable,
                str(project.tenant.id), str(project.id)
            )
        else:
            if sync_status['needs_image_update']:
                self.lambda_service.update_function_image(
                    function_name, str(project.tenant.id), str(project.id)
                )
            else:
                # Skip configuration updates for mock stage to avoid Lambda restarts on every save
                if stage != 'mock':
                    # Always update environment variables to ensure they're current
                    self.lambda_service.update_function_configuration(
                        function_name, str(project.tenant.id), str(project.id)
                    )
            if sync_status['needs_s3_update']:
                self.lambda_service.upload_code_to_s3(
                    settings.AWS_S3_LAMBDA_BUCKET_NAME,
                    sync_status['s3_key'],
                    node_setup_version.executable
                )

    def publish(self, chat_window: ChatWindow):
        # Chat windows always use "mock" stage
        stage = 'mock'

        node_setup_version = self._validate(chat_window)

        logger.info(f"Publishing chat window {chat_window.id} to stage '{stage}'")
        self.sync_lambda(chat_window, stage)

        stage_obj = self.db.query(Stage).filter_by(
            project=chat_window.project, name=stage
        ).one()

        self.db.merge(NodeSetupVersionStage(
            stage_id=stage_obj.id,
            node_setup_id=node_setup_version.node_setup.id,
            version_id=node_setup_version.id,
            executable_hash=node_setup_version.executable_hash
        ))
        self.db.commit()

        return {"message": f"Chat window successfully published to {stage}"}

    def _validate(self, chat_window: ChatWindow) -> NodeSetupVersion:
        if not isinstance(chat_window, ChatWindow):
            raise HTTPException(status_code=400, detail="Only ChatWindow publishing is supported")

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="chat_window",
            object_id=chat_window.id
        ).first()

        if not node_setup:
            raise HTTPException(status_code=404, detail="NodeSetup not found for this chat window.")

        version = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)
        node_setup_version = version[0] if version else None
        if not node_setup_version:
            raise HTTPException(status_code=404, detail="No version found for this chat window")

        if not node_setup_version.executable:
            raise HTTPException(status_code=400, detail="No executable defined")

        return node_setup_version


def get_chat_window_publish_service(
    db: Session = Depends(get_db),
    lambda_service: LambdaService = Depends(get_lambda_service),
    sync_checker: SyncCheckerService = Depends(get_sync_checker_service),
) -> ChatWindowPublishService:
    return ChatWindowPublishService(
        db=db,
        lambda_service=lambda_service,
        sync_checker=sync_checker
    )
