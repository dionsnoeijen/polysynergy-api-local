"""Section Field Assignment Repository - Data access layer for field assignments"""

from uuid import UUID

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from db.session import get_db
from models import SectionFieldAssignment, Section, Field, Project
from schemas.section_field_assignment import SectionFieldAssignmentCreate
from typing import List


class SectionFieldAssignmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_404(self, assignment_id: UUID, project: Project) -> SectionFieldAssignment:
        """Get an assignment by ID within a project"""
        stmt = (
            select(SectionFieldAssignment)
            .join(Section)
            .where(SectionFieldAssignment.id == assignment_id)
            .where(Section.project_id == project.id)
            .options(joinedload(SectionFieldAssignment.field))
        )
        assignment = self.session.scalar(stmt)
        if not assignment:
            raise HTTPException(status_code=404, detail="Field assignment not found")
        return assignment

    def get_for_update_or_404(self, assignment_id: UUID, project: Project) -> SectionFieldAssignment:
        """Get an assignment for update"""
        return self.get_or_404(assignment_id, project)

    def get_all_by_section(self, section_id: UUID, project: Project) -> list[SectionFieldAssignment]:
        """Get all field assignments for a section"""
        stmt = (
            select(SectionFieldAssignment)
            .join(Section)
            .where(SectionFieldAssignment.section_id == section_id)
            .where(Section.project_id == project.id)
            .options(joinedload(SectionFieldAssignment.field))
            .order_by(SectionFieldAssignment.sort_order)
        )
        return list(self.session.scalars(stmt).all())

    def get_by_section_and_field(
        self,
        section_id: UUID,
        field_id: UUID,
        project: Project
    ) -> SectionFieldAssignment | None:
        """Get an assignment by section and field"""
        stmt = (
            select(SectionFieldAssignment)
            .join(Section)
            .where(SectionFieldAssignment.section_id == section_id)
            .where(SectionFieldAssignment.field_id == field_id)
            .where(Section.project_id == project.id)
        )
        return self.session.scalar(stmt)

    def create(
        self,
        assignment_data: SectionFieldAssignmentCreate,
        project: Project
    ) -> SectionFieldAssignment:
        """Assign a field to a section"""
        # Verify section belongs to project
        section = self.session.get(Section, assignment_data.section_id)
        if not section or section.project_id != project.id:
            raise HTTPException(status_code=404, detail="Section not found")

        # Verify field belongs to project
        field = self.session.get(Field, assignment_data.field_id)
        if not field or field.project_id != project.id:
            raise HTTPException(status_code=404, detail="Field not found")

        # Check if assignment already exists
        existing = self.get_by_section_and_field(
            assignment_data.section_id,
            assignment_data.field_id,
            project
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Field is already assigned to this section"
            )

        # Create assignment
        assignment = SectionFieldAssignment(**assignment_data.model_dump())
        self.session.add(assignment)
        self.session.commit()
        self.session.refresh(assignment)

        return assignment

    def bulk_create(
        self,
        assignments_data: List[SectionFieldAssignmentCreate],
        project: Project
    ) -> List[SectionFieldAssignment]:
        """
        Bulk assign multiple fields to sections.

        Returns all assignments (both newly created and already existing).
        """
        assignments = []

        for assignment_data in assignments_data:
            # Verify section belongs to project
            section = self.session.get(Section, assignment_data.section_id)
            if not section or section.project_id != project.id:
                raise HTTPException(status_code=404, detail=f"Section {assignment_data.section_id} not found")

            # Verify field belongs to project
            field = self.session.get(Field, assignment_data.field_id)
            if not field or field.project_id != project.id:
                raise HTTPException(status_code=404, detail=f"Field {assignment_data.field_id} not found")

            # Check if assignment already exists
            existing = self.get_by_section_and_field(
                assignment_data.section_id,
                assignment_data.field_id,
                project
            )
            if existing:
                # Add existing assignment to response
                assignments.append(existing)
                continue

            # Create new assignment
            assignment = SectionFieldAssignment(**assignment_data.model_dump())
            self.session.add(assignment)
            assignments.append(assignment)

        # Commit all new assignments at once
        self.session.commit()

        # Refresh all assignments
        for assignment in assignments:
            self.session.refresh(assignment)

        return assignments

    def update(
        self,
        assignment: SectionFieldAssignment,
        update_data: dict
    ) -> SectionFieldAssignment:
        """Update an assignment with the provided data"""
        for key, value in update_data.items():
            if hasattr(assignment, key):
                setattr(assignment, key, value)

        self.session.commit()
        self.session.refresh(assignment)
        return assignment

    def delete(self, assignment: SectionFieldAssignment) -> None:
        """Remove a field assignment from a section"""
        self.session.delete(assignment)
        self.session.commit()


def get_section_field_assignment_repository(
    db: Session = Depends(get_db)
) -> SectionFieldAssignmentRepository:
    """Dependency for section field assignment repository"""
    return SectionFieldAssignmentRepository(db)
