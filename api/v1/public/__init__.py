"""Public API endpoints"""

from fastapi import APIRouter
from . import content

router = APIRouter()
router.include_router(content.router, prefix="/content", tags=["Public Content"])
