"""Field Assignment API endpoints - Assign/unassign fields to sections"""

from uuid import UUID
from fastapi import APIRouter, Depends, status

from models import Project
from schemas.section_field_assignment import (
    SectionFieldAssignmentCreate,
    SectionFieldAssignmentUpdate,
    SectionFieldAssignmentRead,
    BulkAssignmentCreate,
    BulkAssignmentResponse,
)
from utils.get_current_account import get_project_or_403
from repositories.section_field_assignment_repository import (
    SectionFieldAssignmentRepository,
    get_section_field_assignment_repository,
)

router = APIRouter()


@router.post("/", response_model=SectionFieldAssignmentRead, status_code=status.HTTP_201_CREATED)
def assign_field_to_section(
    assignment_data: SectionFieldAssignmentCreate,
    project: Project = Depends(get_project_or_403),
    assignment_repo: SectionFieldAssignmentRepository = Depends(get_section_field_assignment_repository),
):
    """
    Assign a field from the field library to a section.

    After assigning fields, generate a migration to add the column to the section's table.
    """
    return assignment_repo.create(assignment_data, project)


@router.post("/bulk/", response_model=BulkAssignmentResponse, status_code=status.HTTP_201_CREATED)
def bulk_assign_fields_to_section(
    bulk_data: BulkAssignmentCreate,
    project: Project = Depends(get_project_or_403),
    assignment_repo: SectionFieldAssignmentRepository = Depends(get_section_field_assignment_repository),
):
    """
    Bulk assign multiple fields to sections at once.

    This is more efficient than creating assignments one by one.
    Useful for section builder where you configure multiple fields before saving.

    Returns all assignments (both newly created and already existing).
    The created_count field indicates how many were newly created.
    """
    # Get initial count for this section
    initial_count = len(assignment_repo.get_all_by_section(
        bulk_data.assignments[0].section_id if bulk_data.assignments else None,
        project
    )) if bulk_data.assignments else 0

    # Bulk create (returns both new and existing)
    all_assignments = assignment_repo.bulk_create(bulk_data.assignments, project)

    # Calculate how many were actually created
    created_count = len(all_assignments) - initial_count

    return BulkAssignmentResponse(
        created_count=created_count,
        assignments=all_assignments
    )


@router.get("/section/{section_id}/", response_model=list[SectionFieldAssignmentRead])
def list_section_field_assignments(
    section_id: UUID,
    project: Project = Depends(get_project_or_403),
    assignment_repo: SectionFieldAssignmentRepository = Depends(get_section_field_assignment_repository),
):
    """List all field assignments for a section"""
    return assignment_repo.get_all_by_section(section_id, project)


@router.get("/{assignment_id}/", response_model=SectionFieldAssignmentRead)
def get_assignment(
    assignment_id: UUID,
    project: Project = Depends(get_project_or_403),
    assignment_repo: SectionFieldAssignmentRepository = Depends(get_section_field_assignment_repository),
):
    """Get assignment details"""
    return assignment_repo.get_or_404(assignment_id, project)


@router.patch("/{assignment_id}/", response_model=SectionFieldAssignmentRead)
def update_assignment(
    assignment_id: UUID,
    update_data: SectionFieldAssignmentUpdate,
    project: Project = Depends(get_project_or_403),
    assignment_repo: SectionFieldAssignmentRepository = Depends(get_section_field_assignment_repository),
):
    """
    Update field assignment configuration (layout, visibility, etc).

    This only updates the assignment settings, not the field definition itself.
    """
    assignment = assignment_repo.get_for_update_or_404(assignment_id, project)
    update_dict = update_data.model_dump(exclude_unset=True)
    return assignment_repo.update(assignment, update_dict)


@router.delete("/{assignment_id}/", status_code=status.HTTP_204_NO_CONTENT)
def unassign_field_from_section(
    assignment_id: UUID,
    project: Project = Depends(get_project_or_403),
    assignment_repo: SectionFieldAssignmentRepository = Depends(get_section_field_assignment_repository),
):
    """
    Remove a field assignment from a section.

    After removing fields, generate a migration to drop the column from the section's table.
    """
    assignment = assignment_repo.get_or_404(assignment_id, project)
    assignment_repo.delete(assignment)
