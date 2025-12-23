"""Public API endpoints"""

from fastapi import APIRouter
from . import content, embedded

router = APIRouter()
router.include_router(content.router, prefix="/content", tags=["Public Content"])
router.include_router(embedded.router, prefix="/embedded", tags=["Embedded Chat"])
