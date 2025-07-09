from fastapi import APIRouter
from . import project, blueprint

router = APIRouter()

router.include_router(project.router, prefix="/projects", tags=["Project"])
router.include_router(blueprint.router, prefix="/blueprints", tags=["Blueprints"])