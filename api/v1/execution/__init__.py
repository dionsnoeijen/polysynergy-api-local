from fastapi import APIRouter
from . import mock, details

router = APIRouter()

router.include_router(mock.router, prefix="/execution", tags=["Accounts"])

router.include_router(details.router, prefix="/execution", tags=["Execution Details"])
