import logging
from sqlalchemy.orm import Session

from fastapi import HTTPException

from models import Schedule, NodeSetupVersion, NodeSetup
from services.lambda_service import LambdaService, get_lambda_service
from services.sync_checker_service import SyncCheckerService, get_sync_checker_service
from services.scheduled_lambda_service import ScheduledLambdaService, get_scheduled_lambda_service
from core.settings import settings
from fastapi import Depends
from db.session import get_db

logger = logging.getLogger(__name__)


class SchedulePublishService:
    def __init__(self,
        db: Session,
        lambda_service: LambdaService,
        scheduled_lambda_service: ScheduledLambdaService,
        sync_checker: SyncCheckerService
    ):
        self.db = db
        self.lambda_service = lambda_service
        self.scheduled_lambda_service = scheduled_lambda_service
        self.sync_checker = sync_checker

    def publish(self, schedule: Schedule, stage: str = 'prod'):
        # Skip Lambda operations when in local execution mode
        if settings.EXECUTE_NODE_SETUP_LOCAL:
            logger.info(f"Local mode: Skipping Lambda publish for schedule {schedule.id}")
            return

        node_setup_version = self._validate(schedule)

        project = schedule.project
        function_name = f"node_setup_{node_setup_version.id}_{stage}"
        executable_code = node_setup_version.executable

        sync_status = self.sync_checker.check_sync_needed(
            node_setup_version,
            str(project.tenant.id),
            str(project.id),
            stage
        )

        logger.debug(f"Schedule sync status: {sync_status}")
        lambda_arn = None

        if not sync_status["lambda_exists"]:
            lambda_arn = self.lambda_service.create_or_update_lambda(
                function_name, executable_code, str(project.tenant.id), str(project.id)
            )
        else:
            if sync_status["needs_image_update"]:
                lambda_arn = self.lambda_service.update_function_image(
                    function_name, str(project.tenant.id), str(project.id)
                )
            else:
                # Always update environment variables to ensure they're current
                self.lambda_service.update_function_configuration(
                    function_name, str(project.tenant.id), str(project.id)
                )
            if sync_status["needs_s3_update"]:
                self.lambda_service.upload_code_to_s3(
                    settings.AWS_S3_LAMBDA_BUCKET_NAME,
                    sync_status["s3_key"],
                    executable_code
                )
            if not lambda_arn:
                lambda_arn = self.lambda_service.get_function_arn(function_name)

        if stage != "mock":
            existing_versions = (
                self.db.query(NodeSetupVersion)
                .filter(NodeSetupVersion.node_setup_id == node_setup_version.node_setup_id)
                .filter(NodeSetupVersion.draft.is_(False))
                .filter(NodeSetupVersion.id != node_setup_version.id)
                .all()
            )

            self._disable_existing(existing_versions, stage)
            self._unpublish_existing(existing_versions)
            self._publish_this(node_setup_version, lambda_arn, function_name, schedule)

        else:
            logger.debug("Skipping mock-scheduled publish.")

    def _disable_existing(self, versions: list[NodeSetupVersion], stage: str):
        for v in versions:
            fn = f"node_setup_{v.id}_{stage}"
            try:
                self.scheduled_lambda_service.remove_scheduled_lambda(fn)
                logger.debug(f"Disabled scheduled lambda: {fn}")
            except Exception as e:
                logger.warning(f"Failed to disable scheduled lambda {fn}: {e}")

    def _unpublish_existing(self, versions: list[NodeSetupVersion]):
        # Note: published field has been removed, this method may no longer be needed
        self.db.commit()
        logger.debug(f"Unpublished {len(versions)} old versions")

    def _validate(self, schedule: Schedule) -> NodeSetupVersion:
        if not isinstance(schedule, Schedule):
            raise HTTPException(status_code=400, detail="Only Schedule publishing is supported")

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="schedule",
            object_id=schedule.id
        ).first()

        if not node_setup:
            raise HTTPException(status_code=404, detail="NodeSetup not found for this schedule.")

        version = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)
        node_setup_version = version[0] if version else None

        if not node_setup_version:
            raise HTTPException(status_code=400, detail="No version found for this schedule.")
        if not node_setup_version.executable:
            raise HTTPException(status_code=400, detail="No executable defined")
        if not schedule.cron_expression:
            raise HTTPException(status_code=400, detail="No cron expression defined")

        return node_setup_version

    def _publish_this(self, version: NodeSetupVersion, lambda_arn: str, function_name: str, schedule: Schedule):
        project = schedule.project
        s3_key = f"{project.tenant.id}/{project.id}/{function_name}.py"

        self.scheduled_lambda_service.create_scheduled_lambda(
            function_name, schedule.cron_expression, s3_key
        )
        logger.debug(f"Schedule created with cron expression: {schedule.cron_expression}")

        version.lambda_arn = lambda_arn
        self.db.commit()
        logger.debug(f"Published NodeSetupVersion {version.id}")


def get_schedule_publish_service(
    db: Session = Depends(get_db),
    lambda_service: LambdaService = Depends(get_lambda_service),
    scheduled_lambda_service: ScheduledLambdaService = Depends(get_scheduled_lambda_service),
    sync_checker: SyncCheckerService = Depends(get_sync_checker_service),
) -> SchedulePublishService:
    return SchedulePublishService(
        db=db,
        lambda_service=lambda_service,
        scheduled_lambda_service=scheduled_lambda_service,
        sync_checker=sync_checker
    )
