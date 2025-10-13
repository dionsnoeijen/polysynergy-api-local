from fastapi import APIRouter
from . import mock, details, logs, resume

router = APIRouter()

router.include_router(logs.router, prefix="/execution", tags=["Execution Logs"])
router.include_router(mock.router, prefix="/execution", tags=["Accounts"])
router.include_router(details.router, prefix="/execution", tags=["Execution Details"])
router.include_router(resume.router, prefix="/execution", tags=["Execution Resume"])

