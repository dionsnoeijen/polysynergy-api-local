import logging
from uuid import UUID

from sqlalchemy.orm import Session

from db.session import get_db
from models import Blueprint, NodeSetupVersion, NodeSetup
from services.lambda_service import LambdaService, get_lambda_service
from services.sync_checker_service import SyncCheckerService, get_sync_checker_service
from core.settings import settings
from fastapi import HTTPException, Depends

logger = logging.getLogger(__name__)

class BlueprintPublishService:

    def __init__(self,
        db: Session,
        lambda_service: LambdaService = Depends(get_lambda_service),
        sync_checker: SyncCheckerService = Depends(get_sync_checker_service)
    ):
        self.db = db
        self.lambda_service = lambda_service
        self.sync_checker = sync_checker

    def publish(self, blueprint: Blueprint, project_id: UUID):
        node_setup_version = self._validate(blueprint)

        logger.debug(f"Publishing Blueprint: {blueprint.id}")

        function_name = f"node_setup_{node_setup_version.id}_mock"
        executable_code = node_setup_version.executable

        sync_status = self.sync_checker.check_sync_needed(
            node_setup_version,
            str(blueprint.tenant_id),
            str(project_id),
            stage='mock'
        )

        logger.debug(f"Sync status: {sync_status}")

        lambda_arn = None

        if not sync_status['lambda_exists']:
            lambda_arn = self.lambda_service.create_or_update_lambda(
                function_name,
                executable_code,
                str(blueprint.tenant_id),
                str(project_id)
            )
        else:
            if sync_status['needs_image_update']:
                lambda_arn = self.lambda_service.update_function_image(
                    function_name,
                    str(blueprint.tenant_id),
                    str(project_id)
                )
            else:
                # Always update environment variables to ensure they're current
                self.lambda_service.update_function_configuration(
                    function_name,
                    str(blueprint.tenant_id),
                    str(project_id)
                )

            if sync_status['needs_s3_update']:
                self.lambda_service.upload_code_to_s3(
                    settings.AWS_S3_LAMBDA_BUCKET_NAME,
                    sync_status['s3_key'],
                    executable_code
                )

            if not lambda_arn:
                lambda_arn = self.lambda_service.get_function_arn(function_name)

        logger.debug(f"Blueprint Lambda created/updated with ARN: {lambda_arn}")

        node_setup_version.lambda_arn = lambda_arn
        self.db.commit()

        logger.debug(f"NodeSetupVersion {node_setup_version.id} published")

    def _validate(self, blueprint: Blueprint) -> NodeSetupVersion:
        if not isinstance(blueprint, Blueprint):
            raise HTTPException(status_code=400, detail="Only Blueprint publishing is supported")

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="blueprint",
            object_id=blueprint.id
        ).first()

        if not node_setup:
            raise HTTPException(status_code=404, detail="No published version found for this Blueprint")

        if not node_setup.versions:
            raise HTTPException(status_code=404, detail="No published version found for this Blueprint")

        node_setup_version = node_setup.versions[-1]
        if not node_setup_version:
            raise HTTPException(status_code=404, detail="No published version found for this Blueprint")

        return node_setup_version

def get_blueprint_publish_service(
    db: Session = Depends(get_db),
    lambda_service: LambdaService = Depends(get_lambda_service),
    sync_checker_service: SyncCheckerService = Depends(get_sync_checker_service)
) -> BlueprintPublishService:
    return BlueprintPublishService(db, lambda_service, sync_checker_service)