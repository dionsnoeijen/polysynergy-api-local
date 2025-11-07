from fastapi import APIRouter, Depends, HTTPException, status, Body

from models import Project
from schemas.secret import SecretCreateIn, SecretOut, SecretUpdateIn, SecretDeleteResult, SecretDeleteOut, \
    SecretDeleteIn
from services.secrets_manager import get_secrets_manager
from utils.get_current_account import get_project_or_403
from polysynergy_node_runner.services.secrets_manager import SecretsManager

router = APIRouter()

@router.get("/", response_model=list[SecretOut])
def list_secrets(
    project: Project = Depends(get_project_or_403),
    secrets_manager: SecretsManager = Depends(get_secrets_manager),
):
    try:
        secret_list = secrets_manager.list_secrets(str(project.id))
        result: dict[str, SecretOut] = {}

        for secret in secret_list:
            try:
                _, stage, key = secret['Name'].rsplit('@', 2)
            except ValueError:
                continue

            if key not in result:
                result[key] = SecretOut(
                    key=key,
                    project_id=str(project.id),
                    stages=[]
                )

            result[key].stages.append(stage)

        print(f"Found {len(result)} secrets for project {project.id}")

        return list(result.values())

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving secrets: {str(e)}"
        )

@router.post("/", response_model=SecretOut, status_code=status.HTTP_201_CREATED)
def create_secret(
    data: SecretCreateIn,
    project: Project = Depends(get_project_or_403),
    secrets_manager: SecretsManager = Depends(get_secrets_manager),
):
    if not data.key or not data.secret_value or not data.stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'key', 'secret_value' or 'stage'"
        )

    try:
        secrets_manager.create_secret(data.key, data.secret_value, str(project.id), data.stage)
        return SecretOut(
            key=data.key,
            project_id=str(project.id),
            stages=[data.stage]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating secret: {e}"
        )

@router.put("/", response_model=SecretOut)
def update_secret(
    data: SecretUpdateIn,
    project: Project = Depends(get_project_or_403),
    secrets_manager: SecretsManager = Depends(get_secrets_manager),
):
    if not data.secret_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'secret_value'"
        )

    try:
        secrets_manager.update_secret_by_key(data.key, data.secret_value, str(project.id), data.stage)

        return SecretOut(
            key=data.key,
            project_id=str(project.id),
            stages=[data.stage]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating secret: {e}"
        )

@router.delete("/", response_model=SecretDeleteOut)
def delete_secret(
    data: SecretDeleteIn = Body(...),
    project: Project = Depends(get_project_or_403),
    secrets_manager: SecretsManager = Depends(get_secrets_manager),
):
    key = data.key
    project_id = str(project.id)
    stage_names = {stage.name for stage in project.stages}
    stage_names.add("mock")

    results = []

    for stage_name in stage_names:
        try:
            secrets_manager.delete_secret_by_key(key, project_id, stage_name)
            results.append(SecretDeleteResult(stage=stage_name, deleted=True))
        except Exception as e:
            # Handle both Secrets Manager ResourceNotFoundException and DynamoDB errors
            error_msg = str(e)
            if 'ResourceNotFoundException' in error_msg or 'does not exist' in error_msg:
                results.append(SecretDeleteResult(stage=stage_name, deleted=False))
            else:
                results.append(SecretDeleteResult(stage=stage_name, deleted=False, error=error_msg))

    return SecretDeleteOut(results=results)