"""Section Field API routes"""

from fastapi import APIRouter
from . import field_types, sections, fields, assignments, schemas, database_connections, content

router = APIRouter()

router.include_router(field_types.router, prefix="/field-types", tags=["Field Types"])
router.include_router(sections.router, prefix="/sections", tags=["Sections"])
router.include_router(fields.router, prefix="/fields", tags=["Fields"])
router.include_router(assignments.router, prefix="/assignments", tags=["Field Assignments"])
router.include_router(schemas.router, prefix="/schemas", tags=["UI Schemas"])
router.include_router(database_connections.router, prefix="/database-connections", tags=["Database Connections"])
router.include_router(content.router, prefix="/content", tags=["Content Records"])
