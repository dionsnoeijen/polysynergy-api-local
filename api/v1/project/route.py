import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Path, HTTPException
from starlette import status

from models import Project
from repositories.route_repository import RouteRepository, get_route_repository
from schemas.route import RouteListOut, RouteDetailOut, RouteCreateIn, RoutePublishIn, RouteUnpublishIn
from services.route_publish_service import RoutePublishService, get_route_publish_service
from services.route_unpublish_service import RouteUnpublishService, get_route_unpublish_service
from services.router_service import RouterService, get_router_service
from utils.get_current_account import get_project_or_403

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=list[RouteListOut])
def list_routes(
    project: Project = Depends(get_project_or_403),
    route_repo: RouteRepository = Depends(get_route_repository)
):
    return route_repo.get_all_with_versions_by_project(project)

@router.post("/", response_model=RouteDetailOut, status_code=status.HTTP_201_CREATED)
def create_route(
    data: RouteCreateIn,
    project: Project = Depends(get_project_or_403),
    route_repo: RouteRepository = Depends(get_route_repository),
):
    return route_repo.create(data, project)

@router.get("/{route_id}/", response_model=RouteDetailOut)
def get_route_detail(
    route_id: UUID = Path(),
    project: Project = Depends(get_project_or_403),
    route_repo: RouteRepository = Depends(get_route_repository),
):
    return route_repo.get_one_with_versions_by_id(route_id, project)

@router.patch("/{route_id}/versions/{version_id}/", response_model=RouteDetailOut)
def update_route(
    data: RouteCreateIn,
    route_id: UUID = Path(),
    version_id: UUID = Path(),
    project: Project = Depends(get_project_or_403),
    route_repo: RouteRepository = Depends(get_route_repository),
    router_service: RouterService = Depends(get_router_service),
):
    # Update the route in the database
    updated_route = route_repo.update(route_id, version_id, data)
    
    # Update router for all published stages
    from models import NodeSetupVersion, NodeSetupVersionStage, Stage
    version = route_repo.db.query(NodeSetupVersion).filter_by(id=str(version_id)).first()
    if version:
        # Get all published stage names for this version
        published_stages = route_repo.db.query(Stage).join(
            NodeSetupVersionStage, Stage.id == NodeSetupVersionStage.stage_id
        ).filter(NodeSetupVersionStage.version_id == version.id).all()
        
        stage_names = [stage.name for stage in published_stages]
        
        if stage_names:
            try:
                # Update router for all published stages in one call
                response = router_service.update_route_all_stages(updated_route, version, stage_names)
                if response.status_code == 200:
                    logger.info(f"Successfully updated route {route_id} in router for stages: {', '.join(stage_names)}")
                else:
                    logger.warning(f"Failed to update router for route {route_id}: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Error updating router for route {route_id}: {str(e)}")
                # Don't fail the entire operation if router update fails
    
    return updated_route

@router.delete("/{route_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: UUID,
    project: Project = Depends(get_project_or_403),
    route_repo: RouteRepository = Depends(get_route_repository),
):
    route_repo.delete(route_id, project)
    return None

@router.post("/{route_id}/publish/", status_code=status.HTTP_202_ACCEPTED)
def publish_route(
    route_id: UUID,
    body: RoutePublishIn,
    project: Project = Depends(get_project_or_403),
    route_repository: RouteRepository = Depends(get_route_repository),
    publish_service: RoutePublishService = Depends(get_route_publish_service)
):
    route = route_repository.get_one_with_versions_by_id(route_id, project)

    try:
        return publish_service.publish(route, body.stage.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during route publish for {route_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during publish")

@router.post("/{route_id}/unpublish/", status_code=status.HTTP_202_ACCEPTED)
def unpublish_route(
    route_id: UUID,
    body: RouteUnpublishIn,
    project: Project = Depends(get_project_or_403),
    route_repository: RouteRepository = Depends(get_route_repository),
    unpublish_service: RouteUnpublishService = Depends(get_route_unpublish_service)
):
    route = route_repository.get_one_with_versions_by_id(route_id, project)

    try:
        unpublish_service.unpublish(route, body.stage.strip())
        return {"message": "Route successfully unpublished"}
    except Exception as e:
        logger.error(f"Error during route unpublish for {route_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during unpublish")
