from fastapi import Depends, APIRouter, HTTPException

from models import Project
from repositories.publish_matrix_repository import PublishMatrixRepository, get_publish_matrix_repository
from schemas.publish_matrix import PublishMatrixOut
from utils.get_current_account import get_project_or_403

router = APIRouter()

@router.get("/", response_model=PublishMatrixOut)
def get_publish_matrix(
    project: Project = Depends(get_project_or_403),
    publish_matrix_repo: PublishMatrixRepository = Depends(get_publish_matrix_repository)
):
    try:
        return publish_matrix_repo.get_publish_matrix(project)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in publish matrix: {str(e)}")