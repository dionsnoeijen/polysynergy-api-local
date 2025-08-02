import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException

from repositories.project_repository import ProjectRepository
from models import Project, Account, Membership, Stage
from schemas.project import ProjectCreate


@pytest.mark.unit
class TestProjectRepository:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.mock_session = Mock()
        self.repository = ProjectRepository(self.mock_session)
        
        self.account_id = str(uuid4())
        self.tenant_id = str(uuid4())
        self.project_id = str(uuid4())
        
        # Mock account
        self.mock_account = Mock(spec=Account)
        self.mock_account.id = self.account_id
        
        # Mock membership
        self.mock_membership = Mock(spec=Membership)
        self.mock_membership.account_id = self.account_id
        self.mock_membership.tenant_id = self.tenant_id
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.name = "Test Project"
        self.mock_project.tenant_id = self.tenant_id
        self.mock_project.created_at = datetime.now(timezone.utc)
        self.mock_project.updated_at = datetime.now(timezone.utc)
        self.mock_project.deleted_at = None

    def test_get_or_404_success(self):
        """Test successful project retrieval."""
        self.mock_session.scalar.return_value = self.mock_project
        
        result = self.repository.get_or_404(self.project_id, self.mock_account)
        
        assert result == self.mock_project
        self.mock_session.scalar.assert_called_once()

    def test_get_or_404_not_found(self):
        """Test project not found raises 404."""
        self.mock_session.scalar.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.get_or_404(self.project_id, self.mock_account)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Project not found or access denied"

    def test_get_all_by_account_no_trashed(self):
        """Test retrieval of active projects only."""
        projects = [self.mock_project, Mock(spec=Project)]
        mock_scalars = Mock()
        mock_scalars.all.return_value = projects
        self.mock_session.scalars.return_value = mock_scalars
        
        result = self.repository.get_all_by_account(self.mock_account, include_trashed=False)
        
        assert result == projects
        self.mock_session.scalars.assert_called_once()

    def test_get_all_by_account_include_trashed(self):
        """Test retrieval of trashed projects only."""
        trashed_projects = [Mock(spec=Project)]
        mock_scalars = Mock()
        mock_scalars.all.return_value = trashed_projects
        self.mock_session.scalars.return_value = mock_scalars
        
        result = self.repository.get_all_by_account(self.mock_account, include_trashed=True)
        
        assert result == trashed_projects
        self.mock_session.scalars.assert_called_once()

    def test_create_success(self):
        """Test successful project creation."""
        # Mock memberships query
        mock_query = Mock()
        mock_filter_by = Mock()
        mock_query.filter_by.return_value = mock_filter_by
        mock_filter_by.all.return_value = [self.mock_membership]
        self.mock_session.query.return_value = mock_query
        
        project_data = ProjectCreate(name="New Project")
        
        # Mock Project constructor to return our mock project
        with patch('repositories.project_repository.Project') as mock_project_class:
            mock_project_class.return_value = self.mock_project
            
            # Mock Stage constructor
            with patch('repositories.project_repository.Stage') as mock_stage_class:
                mock_stage = Mock(spec=Stage)
                mock_stage_class.return_value = mock_stage
                
                result = self.repository.create(project_data, self.mock_account)
        
        assert result == self.mock_project
        self.mock_session.add.assert_called()
        self.mock_session.flush.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(self.mock_project)

    def test_create_no_memberships(self):
        """Test project creation when user has no memberships."""
        # Mock empty memberships query
        mock_query = Mock()
        mock_filter_by = Mock()
        mock_query.filter_by.return_value = mock_filter_by
        mock_filter_by.all.return_value = []
        self.mock_session.query.return_value = mock_query
        
        project_data = ProjectCreate(name="New Project")
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.create(project_data, self.mock_account)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "No tenants available for this user"

    def test_update_success(self):
        """Test successful project update."""
        update_data = {"name": "Updated Project Name"}
        
        result = self.repository.update(self.mock_project, update_data)
        
        assert result == self.mock_project
        assert self.mock_project.name == "Updated Project Name"
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(self.mock_project)

    def test_update_invalid_attribute(self):
        """Test update with invalid attribute is ignored."""
        original_name = self.mock_project.name
        update_data = {"invalid_field": "value", "name": "Updated Name"}
        
        result = self.repository.update(self.mock_project, update_data)
        
        assert result == self.mock_project
        assert self.mock_project.name == "Updated Name"
        # Should not have set invalid_field

    def test_soft_delete_success(self):
        """Test successful soft delete."""
        self.repository.soft_delete(self.mock_project)
        
        assert self.mock_project.deleted_at is not None
        self.mock_session.commit.assert_called_once()

    def test_restore_success(self):
        """Test successful project restoration."""
        self.mock_project.deleted_at = datetime.now(timezone.utc)
        
        result = self.repository.restore(self.mock_project)
        
        assert result == self.mock_project
        assert self.mock_project.deleted_at is None
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(self.mock_project)

    def test_restore_not_deleted(self):
        """Test restoration of project that is not deleted."""
        self.mock_project.deleted_at = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.restore(self.mock_project)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Project is not deleted"

    def test_get_for_update_or_404_success(self):
        """Test successful retrieval for update (includes deleted projects)."""
        self.mock_session.scalar.return_value = self.mock_project
        
        result = self.repository.get_for_update_or_404(self.project_id, self.mock_account)
        
        assert result == self.mock_project
        self.mock_session.scalar.assert_called_once()

    def test_get_for_update_or_404_not_found(self):
        """Test retrieval for update when project not found."""
        self.mock_session.scalar.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.get_for_update_or_404(self.project_id, self.mock_account)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Project not found or access denied"