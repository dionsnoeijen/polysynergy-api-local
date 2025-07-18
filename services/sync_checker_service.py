import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from db.session import get_db
from models import Route
from services.lambda_service import LambdaService, get_lambda_service
from services.router_service import RouterService, get_router_service
from models import NodeSetupVersion

logger = logging.getLogger(__name__)


class SyncCheckerService:
    def __init__(self,
        lambda_service: LambdaService,
        router_service: RouterService,
        db: Session
    ):
        self.lambda_service = lambda_service
        self.router_service = router_service
        self.db = db

    def _get_s3_key(self, tenant_id: str, project_id: str, function_name: str) -> str:
        return f"{tenant_id}/{project_id}/{function_name}.py"

    def check_sync_needed(
        self,
        node_setup_version: NodeSetupVersion,
        tenant_id: str,
        project_id: str,
        stage: str = "mock"
    ) -> dict:
        function_name = f"node_setup_{str(node_setup_version.id)}_{stage}"
        s3_key = self._get_s3_key(tenant_id, project_id, function_name)

        try:
            current_image = self.lambda_service.get_function_image_uri(function_name)
            lambda_exists = current_image is not None

            latest_digest = self.lambda_service.get_latest_image_digest()

            needs_image_update = (
                lambda_exists and
                latest_digest and
                latest_digest not in current_image
            )

            parent_object = node_setup_version.node_setup.resolve_parent(self.db)
            needs_router_update = (
                isinstance(parent_object, Route)
                and self.router_service.route_needs_update(parent_object, node_setup_version, stage)
            )

            return {
                "lambda_exists": lambda_exists,
                "needs_image_update": needs_image_update,
                "needs_s3_update": True,
                "needs_router_update": needs_router_update,
                "function_name": function_name,
                "s3_key": s3_key
            }

        except Exception as e:
            logger.error(
                f"Error checking sync status for {function_name} in stage {stage}: {str(e)}",
                exc_info=True
            )
            raise

def get_sync_checker_service(
    db: Session = Depends(get_db),
    lambda_service: LambdaService = Depends(get_lambda_service),
    router_service: RouterService = Depends(get_router_service)
) -> SyncCheckerService:
    return SyncCheckerService(
        lambda_service=lambda_service,
        router_service=router_service,
        db=db
    )