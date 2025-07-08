from fastapi import APIRouter
from . import projects, tenants

router = APIRouter()
router.include_router(projects.router, prefix="/projects", tags=["Projects"])
router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
# router.include_router(nodes.router, prefix="/nodes", tags=["Nodes"])
# router.include_router(services.router, prefix="/services", tags=["Services"])