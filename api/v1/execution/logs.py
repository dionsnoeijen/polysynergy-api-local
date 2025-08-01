from fastapi import APIRouter, Depends, Query
from typing import Optional
from services.lambda_log_service import LambdaLogService
from utils.get_current_account import get_current_account
from models import Account

router = APIRouter()


@router.get("/{version_id}/logs/")
def get_lambda_logs(
    version_id: str,
    after: Optional[int] = Query(None),
    _: Account = Depends(get_current_account)
):
    logs = LambdaLogService.get_lambda_logs(version_id, after)
    return {"logs": logs}
