from fastapi import APIRouter
from . import feedback

router = APIRouter()

router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
