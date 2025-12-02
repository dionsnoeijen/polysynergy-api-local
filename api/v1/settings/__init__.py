from fastapi import APIRouter
from . import branding

router = APIRouter()

router.include_router(branding.router, prefix="/branding", tags=["Settings - Branding"])
