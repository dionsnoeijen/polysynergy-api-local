import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from db.session import get_db
from services.scheduled_lambda_service import ScheduledLambdaService, get_scheduled_lambda_service
from services.lambda_service import LambdaService, get_lambda_service
from models import Schedule
from models import NodeSetup

logger = logging.getLogger(__name__)


class ScheduleUnpublishService:

    def __init__(self,
        db: Session,
        scheduled_lambda_service: ScheduledLambdaService,
        lambda_service: LambdaService
    ):
        self.db = db
        self.scheduled_lambda_service = scheduled_lambda_service
        self.lambda_service = lambda_service

    def unpublish(self, schedule: Schedule, stage: str = 'prod'):
        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="schedule",
            object_id=schedule.id
        ).first()

        if not node_setup:
            raise ValueError(f"No NodeSetup found for schedule {schedule.id}")

        try:
            with self.db.begin():
                logger.debug(f"Unpublishing schedule: {schedule.id}")

                node_setup_version = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)[0]
                function_name = f"node_setup_{node_setup_version.id}_{stage}"

                self.scheduled_lambda_service.remove_scheduled_lambda(function_name)
                logger.debug(f"Deleted scheduled lambda for {function_name}")

                self.lambda_service.delete_lambda(function_name)
                logger.debug(f"Deleted lambda function {function_name}")

                self.db.add(node_setup_version)
                self.db.commit()

                logger.debug(f"NodeSetupVersion Schedule {node_setup_version.id} unpublished")
        except Exception as e:
            logger.error(f"Error during unpublishing schedule {schedule.id}: {str(e)}", exc_info=True)
            raise

def get_schedule_unpublish_service(
    db: Session = Depends(get_db),
    scheduled_lambda_service: ScheduledLambdaService = Depends(get_scheduled_lambda_service),
    lambda_service: LambdaService = Depends(get_lambda_service)
) -> ScheduleUnpublishService:
    return ScheduleUnpublishService(
        db=db,
        scheduled_lambda_service=scheduled_lambda_service,
        lambda_service=lambda_service
    )