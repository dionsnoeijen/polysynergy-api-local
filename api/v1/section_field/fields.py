"""Fields API endpoints - CRUD operations for the field library"""

from uuid import UUID
from fastapi import APIRouter, Depends, status

from models import Project
from schemas.field import FieldCreate, FieldUpdate, FieldRead
from utils.get_current_account import get_project_or_403
from repositories.field_repository import FieldRepository, get_field_repository

router = APIRouter()


@router.post("/", response_model=FieldRead, status_code=status.HTTP_201_CREATED)
def create_field(
    field_data: FieldCreate,
    project: Project = Depends(get_project_or_403),
    field_repo: FieldRepository = Depends(get_field_repository),
):
    """
    Create a new field in the field library.

    Fields are reusable and can be assigned to multiple sections.
    """
    return field_repo.create(field_data, project)


@router.get("/", response_model=list[FieldRead])
def list_fields(
    project: Project = Depends(get_project_or_403),
    field_repo: FieldRepository = Depends(get_field_repository),
):
    """List all fields in the field library for this project"""
    return field_repo.get_all_by_project(project)


@router.get("/{field_id}/", response_model=FieldRead)
def get_field(
    field_id: UUID,
    project: Project = Depends(get_project_or_403),
    field_repo: FieldRepository = Depends(get_field_repository),
):
    """Get field details"""
    return field_repo.get_or_404(field_id, project)


@router.patch("/{field_id}/", response_model=FieldRead)
def update_field(
    field_id: UUID,
    update_data: FieldUpdate,
    project: Project = Depends(get_project_or_403),
    field_repo: FieldRepository = Depends(get_field_repository),
):
    """
    Update field configuration.

    Note: Changing a field will affect all sections where it's assigned.
    After updating fields, generate migrations for affected sections.
    """
    field = field_repo.get_for_update_or_404(field_id, project)
    update_dict = update_data.model_dump(exclude_unset=True)
    return field_repo.update(field, update_dict)


@router.delete("/{field_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(
    field_id: UUID,
    project: Project = Depends(get_project_or_403),
    field_repo: FieldRepository = Depends(get_field_repository),
):
    """
    Delete a field from the field library.

    This will fail if the field is still assigned to any sections.
    Remove all assignments first before deleting the field.
    """
    field = field_repo.get_or_404(field_id, project)
    field_repo.delete(field)
