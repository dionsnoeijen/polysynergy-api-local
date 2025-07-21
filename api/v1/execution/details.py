from fastapi import APIRouter, Depends, Query, HTTPException
from services.execution_storage_service import get_execution_storage_service
from polysynergy_node_runner.services.execution_storage_service import (
    DynamoDbExecutionStorageService
)

router = APIRouter()

@router.get("/{flow_id}/{run_id}/{node_id}/{order}")
def get_node_result(
    flow_id: str,
    run_id: str,
    node_id: str,
    order: int,
    stage: str = Query("mock"),
    sub_stage: str = Query("mock"),
    storage: DynamoDbExecutionStorageService = Depends(get_execution_storage_service),
):
    try:
        data = storage.get_node_result(flow_id, run_id, node_id, order, stage, sub_stage)
        if data is None:
            raise HTTPException(status_code=404, detail="No result found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{flow_id}/{run_id}/connections/")
def get_connection_result(
    flow_id: str,
    run_id: str,
    storage: DynamoDbExecutionStorageService = Depends(get_execution_storage_service),
):
    try:
        data = storage.get_connections_result(flow_id, run_id)
        if data is None:
            raise HTTPException(status_code=404, detail="No result found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))