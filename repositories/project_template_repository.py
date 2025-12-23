from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from models import ProjectTemplate, Project
from schemas.project_template import ProjectTemplateCreate, ProjectTemplateUpdate


class ProjectTemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_by_project(self, project: Project) -> list[ProjectTemplate]:
        """Get all templates for a project."""
        return (
            self.db.query(ProjectTemplate)
            .filter(ProjectTemplate.project_id == project.id)
            .order_by(ProjectTemplate.name)
            .all()
        )

    def get_by_id(self, template_id: UUID, project: Project) -> ProjectTemplate:
        """Get a template by ID, ensuring it belongs to the project."""
        template = (
            self.db.query(ProjectTemplate)
            .filter(
                ProjectTemplate.id == template_id,
                ProjectTemplate.project_id == project.id
            )
            .first()
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template

    def get_by_name(self, name: str, project: Project) -> ProjectTemplate | None:
        """Get a template by name within a project."""
        return (
            self.db.query(ProjectTemplate)
            .filter(
                ProjectTemplate.name == name,
                ProjectTemplate.project_id == project.id
            )
            .first()
        )

    def create(self, data: ProjectTemplateCreate, project: Project) -> ProjectTemplate:
        """Create a new template."""
        # Check for existing template with same name
        existing = self.get_by_name(data.name, project)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Template with name '{data.name}' already exists."
            )

        template = ProjectTemplate(
            project_id=project.id,
            name=data.name,
            content=data.content,
        )

        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)

        return template

    def update(self, template_id: UUID, data: ProjectTemplateUpdate, project: Project) -> ProjectTemplate:
        """Update an existing template."""
        template = self.get_by_id(template_id, project)

        if data.name is not None and data.name != template.name:
            # Check for name uniqueness
            existing = self.get_by_name(data.name, project)
            if existing and existing.id != template_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Template with name '{data.name}' already exists."
                )
            template.name = data.name

        if data.content is not None:
            template.content = data.content

        template.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(template)

        return template

    def delete(self, template_id: UUID, project: Project) -> None:
        """Delete a template."""
        template = self.get_by_id(template_id, project)
        self.db.delete(template)
        self.db.commit()


def get_project_template_repository(db: Session = Depends(get_db)) -> ProjectTemplateRepository:
    return ProjectTemplateRepository(db)
