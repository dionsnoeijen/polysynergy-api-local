from fastapi import APIRouter
from . import oauth_callback

router = APIRouter()

router.include_router(oauth_callback.router, prefix="/oauth", tags=["Oauth"])