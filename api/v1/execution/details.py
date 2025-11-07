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


@router.get("/{flow_id}/{run_id}/mock-nodes/")
def get_mock_nodes(
    flow_id: str,
    run_id: str,
    _: Project = Depends(get_project_or_403),
    storage: DynamoDbExecutionStorageService = Depends(get_execution_storage_service),
):
    try:
        # Get stage info from run metadata first
        runs = storage.get_available_runs(flow_id)
        run_info = next((r for r in runs if r["run_id"] == run_id), None)

        # Use stage from run metadata, default to "mock" if not found
        stage = run_info.get("stage", "mock") if run_info else "mock"
        sub_stage = run_info.get("sub_stage", "mock") if run_info else "mock"

        # Use the existing get_all_nodes_for_run method to get the execution data
        nodes = storage.get_all_nodes_for_run(flow_id, run_id, stage, sub_stage)

        # Convert to mock node format expected by frontend
        mock_nodes = []
        for node in nodes:
            node_data = node.get('data', {})

            mock_node = {
                "id": f"{node_data.get('node_id', node['node_id'])}-{node_data.get('order', node['order'])}",
                "handle": node_data.get('handle', ''),
                "order": node_data.get('order', node['order']),
                "type": node_data.get('type', 'Unknown'),
                "killed": node_data.get('killed', False),
                "runId": node_data.get('run_id', run_id),
                "started": True,
                "variables": node_data.get('variables', {}),
                "status": "killed" if node_data.get('killed') else ("error" if node_data.get('error') else "success")
            }
            mock_nodes.append(mock_node)

        # Include stage information in the response so frontend can build correct links
        return {
            "mock_nodes": mock_nodes,
            "stage": stage,
            "sub_stage": sub_stage
        }

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