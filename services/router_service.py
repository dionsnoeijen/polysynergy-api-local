import logging
import requests

from models import Route
from models import NodeSetupVersion
from core.settings import settings

logger = logging.getLogger(__name__)


class RouterService:
    def __init__(self, base_url: str | None = None):
        self.router_url = base_url or settings.ROUTER_URL

    def _route_payload(
        self,
        route: Route,
        node_setup_version: NodeSetupVersion,
        stage: str | list[str]
    ) -> dict:
        segments = [
            {
                "type": s.type,
                "name": s.name,
                "variable_type": s.variable_type or "any"
            }
            for s in sorted(route.segments, key=lambda s: s.segment_order)
        ]

        # Handle both single stage and multiple stages
        active_stages = stage if isinstance(stage, list) else [stage]
        
        payload = {
            "project_id": str(route.project.id),
            "tenant_id": str(route.project.tenant.id),
            "route": {
                "id": str(route.id),
                "method": route.method.value,
                "require_api_key": route.require_api_key,
                "segments": segments,
                "node_setup_version_id": str(node_setup_version.id),
                "tenant_id": str(route.project.tenant.id),
                "active_stages": active_stages
            }
        }
        
        # Add stage field for backwards compatibility with single stage calls
        if not isinstance(stage, list):
            payload["stage"] = stage
            
        return payload

    def update_route(
        self,
        route: Route,
        node_setup_version: NodeSetupVersion,
        stage: str
    ):
        payload = self._route_payload(route, node_setup_version, stage)
        return requests.post(f"{self.router_url}/update-route", json=payload)

    def update_route_all_stages(
        self,
        route: Route,
        node_setup_version: NodeSetupVersion,
        active_stages: list[str]
    ):
        """Update route for all active stages in a single call"""
        payload = self._route_payload(route, node_setup_version, active_stages)
        logger.debug(f"Sending multi-stage update payload: {payload}")
        response = requests.post(f"{self.router_url}/update-route", json=payload)
        logger.debug(f"Router response: {response.status_code} - {response.text}")
        return response

    def deactivate_route_stage(
        self,
        route: Route,
        stage: str
    ):
        return requests.post(f"{self.router_url}/deactivate-route", json={
            "project_id": str(route.project.id),
            "stage": stage,
            "route": {
                "id": str(route.id)
            }
        })

    def delete_route(self, route: Route):
        return requests.delete(f"{self.router_url}/delete-route", json={
            "project_id": str(route.project.id),
            "route": {
                "id": str(route.id)
            }
        })

    def route_needs_update(
        self,
        route: Route,
        node_setup_version: NodeSetupVersion,
        stage: str = "mock"
    ) -> bool:
        segment_payload = [
            {
                "type": s.type,
                "name": s.name,
                "variable_type": s.variable_type or "any"
            }
            for s in sorted(route.segments, key=lambda s: s.segment_order)
        ]

        try:
            router_response = requests.get(
                f"{self.router_url}/routes/{route.project.id}"
            )
            router_response.raise_for_status()
            all_routes = router_response.json()
            # Filter routes by stage and find our specific route
            existing = next((
                r for r in all_routes 
                if r["SK"].endswith(str(route.id)) and stage in r.get("active_stages", [])
            ), None)
        except Exception as e:
            logger.warning(f"Router query failed: {e}")
            existing = None

        return (
            not existing or
            existing.get("method") != route.method.value or
            existing.get("require_api_key") != getattr(route, 'require_api_key', False) or
            existing.get("node_setup_version_id") != str(node_setup_version.id) or
            existing.get("segments") != segment_payload
        )

def get_router_service() -> RouterService:
    return RouterService()