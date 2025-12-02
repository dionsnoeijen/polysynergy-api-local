import logging

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from models import Route, NodeSetup, NodeSetupVersionStage, Stage
from services.lambda_service import LambdaService, get_lambda_service
from services.router_service import RouterService, get_router_service
from core.settings import settings

logger = logging.getLogger(__name__)


class RouteUnpublishService:
    def __init__(
        self,
        db: Session,
        lambda_service: LambdaService,
        router_service: RouterService,
    ):
        self.db = db
        self.lambda_service = lambda_service
        self.router_service = router_service

    def unpublish(self, route: Route, stage: str):
        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="route",
            object_id=route.id
        ).first()

        if not node_setup:
            raise HTTPException(status_code=404, detail="NodeSetup not found")

        version = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)
        node_setup_version = version[0] if version else None

        if not node_setup_version:
            raise HTTPException(status_code=404, detail="NodeSetupVersion not found")

        function_name = f"node_setup_{str(node_setup_version.id)}_{stage}"

        # Skip Lambda operations when in local execution mode
        if not settings.EXECUTE_NODE_SETUP_LOCAL:
            self.lambda_service.delete_lambda(function_name)
            logger.debug(f"Deleted Lambda function: {function_name}")
        else:
            logger.info(f"Local mode: Skipping Lambda deletion for {function_name}")

        # Delete the stage link
        deleted = self.db.query(NodeSetupVersionStage).filter(
            NodeSetupVersionStage.stage.has(name=stage, project=route.project),
            NodeSetupVersionStage.node_setup == node_setup
        ).delete(synchronize_session=False)

        self.db.commit()
        logger.debug(f"Deleted {deleted} NodeSetupVersionStage link(s)")

        # Deactivate the route in the router
        response = self.router_service.deactivate_route_stage(route, stage)
        if response.status_code != 200:
            logger.error(f"Failed to deactivate route {route.id} on stage {stage}: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail="Failed to deactivate route in router")


def get_route_unpublish_service(
    db: Session = Depends(get_db),
    lambda_service: LambdaService = Depends(get_lambda_service),
    router_service: RouterService = Depends(get_router_service),
) -> RouteUnpublishService:
    return RouteUnpublishService(
        db=db,
        lambda_service=lambda_service,
        router_service=router_service,
    )