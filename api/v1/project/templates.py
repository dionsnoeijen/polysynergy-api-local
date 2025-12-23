from uuid import UUID

from fastapi import APIRouter, Depends
from starlette import status

from models import Project
from repositories.project_template_repository import (
    ProjectTemplateRepository,
    get_project_template_repository,
)
from schemas.project_template import (
    ProjectTemplateCreate,
    ProjectTemplateUpdate,
    ProjectTemplateRead,
)
from utils.get_current_account import get_project_or_403

router = APIRouter()


@router.get("/", response_model=list[ProjectTemplateRead])
def list_templates(
    project: Project = Depends(get_project_or_403),
    template_repository: ProjectTemplateRepository = Depends(get_project_template_repository),
):
    """List all templates for the project."""
    return template_repository.get_all_by_project(project)


@router.post("/", response_model=ProjectTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    data: ProjectTemplateCreate,
    project: Project = Depends(get_project_or_403),
    template_repository: ProjectTemplateRepository = Depends(get_project_template_repository),
):
    """Create a new template."""
    return template_repository.create(data, project)


@router.get("/{template_id}/", response_model=ProjectTemplateRead)
def get_template(
    template_id: UUID,
    project: Project = Depends(get_project_or_403),
    template_repository: ProjectTemplateRepository = Depends(get_project_template_repository),
):
    """Get a specific template by ID."""
    return template_repository.get_by_id(template_id, project)


@router.put("/{template_id}/", response_model=ProjectTemplateRead)
def update_template(
    template_id: UUID,
    data: ProjectTemplateUpdate,
    project: Project = Depends(get_project_or_403),
    template_repository: ProjectTemplateRepository = Depends(get_project_template_repository),
):
    """Update an existing template."""
    return template_repository.update(template_id, data, project)


@router.delete("/{template_id}/")
def delete_template(
    template_id: UUID,
    project: Project = Depends(get_project_or_403),
    template_repository: ProjectTemplateRepository = Depends(get_project_template_repository),
):
    """Delete a template."""
    template_repository.delete(template_id, project)
    return {"message": "Template deleted successfully."}
