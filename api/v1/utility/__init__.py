from fastapi import APIRouter
from . import jmes

router = APIRouter()
router.include_router(jmes.router, prefix="/utility", tags=["Utility"])
