from fastapi import APIRouter, Depends, HTTPException, status, Body, Path

from models import Project
from schemas.env_var import EnvVarOut, EnvVarCreateIn
from polysynergy_node_runner.services.env_var_manager import EnvVarManager
from services.env_var_manager import get_env_var_manager
from utils.get_current_account import get_project_or_403

router = APIRouter()

@router.get("/", response_model=list[EnvVarOut])
def list_env_vars(
    project: Project = Depends(get_project_or_403),
    env_var_manager: EnvVarManager = Depends(get_env_var_manager)
):
    try:
        return env_var_manager.list_vars(str(project.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving env vars: {str(e)}")


@router.post("/", response_model=EnvVarOut, status_code=201)
def create_env_var(
    data: EnvVarCreateIn,
    project: Project = Depends(get_project_or_403),
    env_var_manager: EnvVarManager = Depends(get_env_var_manager)
):
    try:
        return env_var_manager.set_var(str(project.id), data.stage, data.key, data.value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating env var: {str(e)}")


@router.delete("/{stage}/{key}/", status_code=204)
def delete_env_var(
    stage: str = Path(...),
    key: str = Path(...),
    project: Project = Depends(get_project_or_403),
    env_var_manager: EnvVarManager = Depends(get_env_var_manager)
):
    try:
        env_var_manager.delete_var(str(project.id), stage, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting env var: {str(e)}")