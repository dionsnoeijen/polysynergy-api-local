"""Field Repository - Data access layer for fields"""

from uuid import UUID

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from db.session import get_db
from models import Field, Project
from schemas.field import FieldCreate
from services.field_type_loader_service import get_field_type_loader


class FieldRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_404(self, field_id: UUID, project: Project) -> Field:
        """Get a field by ID within a project"""
        stmt = (
            select(Field)
            .where(Field.id == field_id)
            .where(Field.project_id == project.id)
        )
        field = self.session.scalar(stmt)
        if not field:
            raise HTTPException(status_code=404, detail="Field not found")
        return field

    def get_for_update_or_404(self, field_id: UUID, project: Project) -> Field:
        """Get a field for update"""
        return self.get_or_404(field_id, project)

    def get_all_by_project(self, project: Project) -> list[Field]:
        """Get all fields in a project (field library)"""
        stmt = (
            select(Field)
            .where(Field.project_id == project.id)
            .order_by(Field.label)
        )
        return list(self.session.scalars(stmt).all())

    def get_by_handle(self, handle: str, project: Project) -> Field | None:
        """Get a field by handle within a project"""
        stmt = (
            select(Field)
            .where(Field.project_id == project.id)
            .where(Field.handle == handle)
        )
        return self.session.scalar(stmt)

    def create(self, field_data: FieldCreate, project: Project) -> Field:
        """Create a new field in the field library"""
        # Verify field type exists
        field_type_loader = get_field_type_loader()
        if not field_type_loader.field_type_exists(field_data.field_type_handle):
            raise HTTPException(
                status_code=400,
                detail=f"Field type '{field_data.field_type_handle}' not found"
            )

        # Check if handle is unique within project
        existing = self.get_by_handle(field_data.handle, project)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Field with handle '{field_data.handle}' already exists in this project"
            )

        # Create field
        field_dict = field_data.model_dump()
        field_dict['project_id'] = project.id
        field = Field(**field_dict)

        self.session.add(field)
        self.session.commit()
        self.session.refresh(field)

        return field

    def update(self, field: Field, update_data: dict) -> Field:
        """Update a field with the provided data"""
        # If updating field_type_handle, verify it exists
        if 'field_type_handle' in update_data:
            field_type_loader = get_field_type_loader()
            if not field_type_loader.field_type_exists(update_data['field_type_handle']):
                raise HTTPException(
                    status_code=400,
                    detail=f"Field type '{update_data['field_type_handle']}' not found"
                )

        for key, value in update_data.items():
            if hasattr(field, key):
                setattr(field, key, value)

        self.session.commit()
        self.session.refresh(field)
        return field

    def delete(self, field: Field) -> None:
        """
        Delete a field from the field library.

        Note: This will fail if the field is still assigned to any sections
        due to CASCADE foreign key constraints.
        """
        self.session.delete(field)
        self.session.commit()


def get_field_repository(db: Session = Depends(get_db)) -> FieldRepository:
    """Dependency for field repository"""
    return FieldRepository(db)
