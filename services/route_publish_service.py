import logging

from sqlalchemy.orm import Session
from fastapi import HTTPException

from fastapi import Depends
from db.session import get_db
from models import Route, NodeSetupVersion, Stage, NodeSetupVersionStage, NodeSetup
from services.lambda_service import LambdaService, get_lambda_service
from services.router_service import RouterService, get_router_service
from services.sync_checker_service import SyncCheckerService, get_sync_checker_service
from core.settings import settings

logger = logging.getLogger(__name__)


class RoutePublishService:
    def __init__(
        self,
        db: Session,
        lambda_service: LambdaService,
        router_service: RouterService,
        sync_checker: SyncCheckerService
    ):
        self.db = db
        self.lambda_service = lambda_service
        self.router_service = router_service
        self.sync_checker = sync_checker

    def sync_lambda(self, route: Route, stage: str = 'prod'):
        node_setup_version = self._validate(route)

        project = route.project
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
            if sync_status['needs_s3_update']:
                self.lambda_service.upload_code_to_s3(
                    settings.AWS_S3_LAMBDA_BUCKET_NAME,
                    sync_status['s3_key'],
                    node_setup_version.executable
                )

    def update_route(self, route: Route, version: NodeSetupVersion, stage: str):
        response = self.router_service.update_route(route, version, stage)
        if response.status_code != 200:
            logger.error(f"Router update failed: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail="Router update failed")
        return response.json()

    def publish(self, route: Route, stage: str = 'prod'):
        node_setup_version = self._validate(route)

        logger.info(f"Publishing route {route.id} to stage '{stage}'")
        self.sync_lambda(route, stage)
        response = self.update_route(route, node_setup_version, stage)

        stage_obj = self.db.query(Stage).filter_by(
            project=route.project, name=stage
        ).one()

        self.db.merge(NodeSetupVersionStage(
            stage_id=stage_obj.id,
            node_setup_id=node_setup_version.node_setup.id,
            version_id=node_setup_version.id,
            executable_hash=node_setup_version.executable_hash
        ))
        self.db.commit()

        return response

    def _validate(self, route: Route) -> NodeSetupVersion:
        if not isinstance(route, Route):
            raise HTTPException(status_code=400, detail="Only Route publishing is supported")

        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="route",
            object_id=route.id
        ).first()

        if not node_setup:
            raise HTTPException(status_code=404, detail="NodeSetup not found for this schedule.")

        version = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)
        node_setup_version = version[0] if version else None
        if not node_setup_version:
            raise HTTPException(status_code=404, detail="No version found for this route")

        if not node_setup_version.executable:
            raise HTTPException(status_code=400, detail="No executable defined")

        return node_setup_version


def get_route_publish_service(
    db: Session = Depends(get_db),
    lambda_service: LambdaService = Depends(get_lambda_service),
    router_service: RouterService = Depends(get_router_service),
    sync_checker: SyncCheckerService = Depends(get_sync_checker_service),
) -> RoutePublishService:
    return RoutePublishService(
        db=db,
        lambda_service=lambda_service,
        router_service=router_service,
        sync_checker=sync_checker
    )