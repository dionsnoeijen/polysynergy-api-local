"""Section Repository - Data access layer for sections"""

from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from db.session import get_db
from models import Section, Project, SectionFieldAssignment
from schemas.section import SectionCreate


class SectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_404(self, section_id: UUID, project: Project) -> Section:
        """Get a section by ID within a project"""
        stmt = (
            select(Section)
            .where(Section.id == section_id)
            .where(Section.project_id == project.id)
            .where(Section.deleted_at.is_(None))
            .options(
                joinedload(Section.field_assignments).joinedload(SectionFieldAssignment.field)
            )
        )
        section = self.session.scalar(stmt)
        if not section:
            raise HTTPException(status_code=404, detail="Section not found")
        return section

    def get_for_update_or_404(self, section_id: UUID, project: Project) -> Section:
        """Get a section for update"""
        return self.get_or_404(section_id, project)

    def get_all_by_project(
        self,
        project: Project,
        include_inactive: bool = False
    ) -> list[Section]:
        """Get all sections in a project"""
        stmt = (
            select(Section)
            .where(Section.project_id == project.id)
            .where(Section.deleted_at.is_(None))
        )

        if not include_inactive:
            stmt = stmt.where(Section.is_active == True)

        return list(self.session.scalars(stmt.order_by(Section.label)).all())

    def create(self, section_data: SectionCreate, project: Project) -> Section:
        """Create a new section"""
        # Check if handle is unique within project
        existing = self.session.query(Section).filter(
            Section.project_id == project.id,
            Section.handle == section_data.handle,
            Section.deleted_at.is_(None)
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Section with handle '{section_data.handle}' already exists in this project"
            )

        # Create section
        section = Section(**section_data.model_dump())
        self.session.add(section)
        self.session.commit()
        self.session.refresh(section)

        return section

    def update(self, section: Section, update_data: dict) -> Section:
        """Update a section with the provided data"""
        for key, value in update_data.items():
            if hasattr(section, key):
                setattr(section, key, value)

        self.session.commit()
        self.session.refresh(section)
        return section

    def merge_layout_config(self, section: Section, new_config: dict) -> Section:
        """
        Merge new layout config with existing config.

        This allows updating specific parts of layout_config (like table_columns)
        without overwriting other parts (like tabs, rows, cells).

        Args:
            section: The section to update
            new_config: New layout config to merge (partial or complete)

        Returns:
            Updated section
        """
        # Get current layout config or empty dict
        current_config = section.layout_config if section.layout_config else {}

        # Deep merge: update existing keys, add new keys
        merged_config = {**current_config, **new_config}

        # Update the section
        section.layout_config = merged_config
        self.session.commit()
        self.session.refresh(section)

        return section

    def soft_delete(self, section: Section) -> None:
        """
        Soft delete a section.

        WARNING: This does NOT drop the database table!
        """
        section.deleted_at = datetime.now(timezone.utc)
        self.session.commit()

    def restore(self, section: Section) -> Section:
        """Restore a soft-deleted section"""
        if section.deleted_at is None:
            raise HTTPException(status_code=400, detail="Section is not deleted")

        section.deleted_at = None
        self.session.commit()
        self.session.refresh(section)
        return section


def get_section_repository(db: Session = Depends(get_db)) -> SectionRepository:
    """Dependency for section repository"""
    return SectionRepository(db)
