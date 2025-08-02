from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from db.session import get_db
from models import Project, Membership, Account, Stage
from schemas.project import ProjectCreate


class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_404(self, project_id: UUID, account: Account) -> Project:
        """Get a project by ID with access control based on account membership."""
        stmt = (
            select(Project)
            .join(Membership, Membership.tenant_id == Project.tenant_id)
            .where(Project.id == project_id)
            .where(Membership.account_id == account.id)
            .where(Project.deleted_at.is_(None))
        )
        project = self.session.scalar(stmt)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        return project

    def get_all_by_account(self, account: Account, include_trashed: bool = False) -> list[Project]:
        """Get all projects accessible to an account."""
        stmt = (
            select(Project)
            .join(Membership, Membership.tenant_id == Project.tenant_id)
            .where(Membership.account_id == account.id)
        )

        if include_trashed:
            stmt = stmt.where(Project.deleted_at.is_not(None))
        else:
            stmt = stmt.where(Project.deleted_at.is_(None))

        return list(self.session.scalars(stmt).all())

    def create(self, project_data: ProjectCreate, account: Account) -> Project:
        """Create a new project with automatic stage creation."""
        # Get user's first tenant membership
        memberships = self.session.query(Membership).filter_by(account_id=account.id).all()
        
        if not memberships:
            raise HTTPException(
                status_code=400,
                detail="No tenants available for this user"
            )

        tenant_id = memberships[0].tenant_id
        
        # Create project
        project = Project(name=project_data.name, tenant_id=tenant_id)
        self.session.add(project)
        self.session.flush()

        # Create default mock stage
        stage = Stage(
            project_id=project.id,
            name="mock",
            is_production=False
        )
        self.session.add(stage)
        self.session.commit()
        self.session.refresh(project)

        return project

    def update(self, project: Project, update_data: dict) -> Project:
        """Update a project with the provided data."""
        for key, value in update_data.items():
            if hasattr(project, key):
                setattr(project, key, value)

        self.session.commit()
        self.session.refresh(project)
        return project

    def soft_delete(self, project: Project) -> None:
        """Soft delete a project by setting deleted_at timestamp."""
        project.deleted_at = datetime.now(timezone.utc)
        self.session.commit()

    def restore(self, project: Project) -> Project:
        """Restore a soft-deleted project."""
        if project.deleted_at is None:
            raise HTTPException(status_code=400, detail="Project is not deleted")
        
        project.deleted_at = None
        self.session.commit()
        self.session.refresh(project)
        return project

    def get_for_update_or_404(self, project_id: UUID, account: Account) -> Project:
        """Get a project for update operations (includes soft-deleted projects)."""
        stmt = (
            select(Project)
            .join(Membership, Membership.tenant_id == Project.tenant_id)
            .where(Project.id == project_id)
            .where(Membership.account_id == account.id)
        )
        project = self.session.scalar(stmt)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        return project


def get_project_repository(db: Session = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(db)