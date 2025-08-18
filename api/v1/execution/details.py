from fastapi import APIRouter, Depends, Query, HTTPException

from models import Project
from services.execution_storage_service import get_execution_storage_service
from polysynergy_node_runner.services.execution_storage_service import (
    DynamoDbExecutionStorageService
)

from utils.get_current_account import get_project_or_403

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


@router.get("/runs/{flow_id}")
def get_available_runs(
    flow_id: str,
    _: Project = Depends(get_project_or_403),
    storage: DynamoDbExecutionStorageService = Depends(get_execution_storage_service),
):
    try:
        runs = storage.get_available_runs(flow_id)
        return {"runs": runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{flow_id}/{run_id}/nodes/")
def get_all_nodes_for_run(
    flow_id: str,
    run_id: str,
    _: Project = Depends(get_project_or_403),
    stage: str = Query("mock"),
    sub_stage: str = Query("mock"),
    storage: DynamoDbExecutionStorageService = Depends(get_execution_storage_service),
):
    try:
        nodes = storage.get_all_nodes_for_run(flow_id, run_id, stage, sub_stage)
        return {"nodes": nodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{flow_id}/{run_id}/mock-nodes/")
def store_mock_nodes(
    flow_id: str,
    run_id: str,
    request: dict,
    _: Project = Depends(get_project_or_403),
    storage: DynamoDbExecutionStorageService = Depends(get_execution_storage_service),
):
    try:
        mock_nodes = request.get('mock_nodes', [])
        storage.store_mock_nodes_result(flow_id, run_id, mock_nodes)
        return {"message": "Mock nodes stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{flow_id}/{run_id}/mock-nodes/")
def get_mock_nodes(
    flow_id: str,
    run_id: str,
    _: Project = Depends(get_project_or_403),
    storage: DynamoDbExecutionStorageService = Depends(get_execution_storage_service),
):
    try:
        mock_nodes = storage.get_mock_nodes_result(flow_id, run_id)
        return {"mock_nodes": mock_nodes or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/runs/{flow_id}")
def clear_all_runs(
    flow_id: str,
    _: Project = Depends(get_project_or_403),
    storage: DynamoDbExecutionStorageService = Depends(get_execution_storage_service),
):
    try:
        storage.clear_all_runs(flow_id)
        return {"message": "All runs cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))