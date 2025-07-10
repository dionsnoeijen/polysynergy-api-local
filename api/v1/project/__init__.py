from fastapi import APIRouter
from . import project, blueprint, node_setup, stage, route, schedule, service, secret

router = APIRouter()

router.include_router(project.router, prefix="/projects", tags=["Project"])
router.include_router(blueprint.router, prefix="/blueprints", tags=["Blueprints"])
router.include_router(node_setup.router, prefix="/node-setup", tags=["Node Setup"])
router.include_router(stage.router, prefix="/stages", tags=["Stages"])
router.include_router(route.router, prefix="/routes", tags=["Routes"])
router.include_router(schedule.router, prefix="/schedules", tags=["Schedules"])
router.include_router(service.router, prefix="/services", tags=["Services"])
router.include_router(secret.router, prefix="/secrets", tags=["Secrets"])