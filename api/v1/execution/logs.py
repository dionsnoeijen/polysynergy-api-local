from fastapi import APIRouter, Depends, Query
from typing import Optional
from services.log_router_service import LogRouterService
from utils.get_current_account import get_current_account
from models import Account

router = APIRouter()


@router.get("/{version_id}/logs/")
def get_execution_logs(
    version_id: str,
    after: Optional[int] = Query(None),
    _: Account = Depends(get_current_account)
):
    """Get execution logs, automatically routing to CloudWatch or local logs based on execution mode."""
    logs = LogRouterService.get_logs(version_id, after)
    return {"logs": logs}


@router.get("/{version_id}/logs/debug/")
def get_logs_debug_info(
    version_id: str,
    _: Account = Depends(get_current_account)
):
    """Get debug information about the log system (useful for troubleshooting)."""
    return LogRouterService.get_debug_info(version_id)


@router.delete("/{version_id}/logs/")
def clear_execution_logs(
    version_id: str,
    _: Account = Depends(get_current_account)
):
    """Clear logs for a version (only works for local logs)."""
    LogRouterService.clear_logs(version_id)
    return {"message": f"Logs cleared for version {version_id} (if using local execution)"}
