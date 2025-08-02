import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from uuid import uuid4

from models import Project, Account, Membership, Stage
from repositories.project_repository import ProjectRepository


@pytest.mark.integration
class TestProjectEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
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
        
        # Mock stage
        self.mock_stage = Mock(spec=Stage)
        self.mock_stage.project_id = self.project_id
        self.mock_stage.name = "mock"
        self.mock_stage.is_production = False
    
    def teardown_method(self):
        """Clean up after each test."""
        from main import app
        app.dependency_overrides.clear()
    
    
    def test_create_project_no_memberships(self, client: TestClient):
        """Test project creation when user has no tenant memberships."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.create.side_effect = HTTPException(status_code=400, detail="No tenants available for this user")
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        project_data = {"name": "New Test Project"}
        
        response = client.post("/api/v1/projects/", json=project_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "No tenants available for this user"
    
    def test_create_project_validation_error(self, client: TestClient):
        """Test project creation with validation errors."""
        from utils.get_current_account import get_current_account
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Send invalid data (missing name)
        response = client.post("/api/v1/projects/", json={})
        
        assert response.status_code == 422
    
    def test_create_project_name_too_long(self, client: TestClient):
        """Test project creation with name exceeding max length."""
        from utils.get_current_account import get_current_account
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Send name that's too long (over 255 characters)
        long_name = "a" * 256
        project_data = {"name": long_name}
        
        response = client.post("/api/v1/projects/", json=project_data)
        
        assert response.status_code == 422
    
    def test_get_projects_success(self, client: TestClient):
        """Test successful retrieval of projects."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        projects = [self.mock_project, Mock(spec=Project)]
        projects[1].id = str(uuid4())
        projects[1].name = "Another Project"
        projects[1].tenant_id = self.tenant_id
        projects[1].created_at = datetime.now(timezone.utc)
        projects[1].updated_at = datetime.now(timezone.utc)
        
        mock_repo.get_all_by_account.return_value = projects
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        response = client.get("/api/v1/projects/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_get_projects_trashed(self, client: TestClient):
        """Test retrieval of trashed projects."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        trashed_project = Mock(spec=Project)
        trashed_project.id = str(uuid4())
        trashed_project.name = "Trashed Project"
        trashed_project.tenant_id = self.tenant_id
        trashed_project.created_at = datetime.now(timezone.utc)
        trashed_project.updated_at = datetime.now(timezone.utc)
        trashed_project.deleted_at = datetime.now(timezone.utc)
        
        mock_repo.get_all_by_account.return_value = [trashed_project]
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        response = client.get("/api/v1/projects/?trashed=true")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    def test_get_project_success(self, client: TestClient):
        """Test successful retrieval of single project."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.get_or_404.return_value = self.mock_project
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/projects/{self.project_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.project_id
        assert data["name"] == "Test Project"
    
    def test_get_project_not_found(self, client: TestClient):
        """Test retrieval of non-existent project."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.get_or_404.side_effect = HTTPException(status_code=404, detail="Project not found or access denied")
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/projects/{self.project_id}/")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Project not found or access denied"
    
    def test_update_project_success(self, client: TestClient):
        """Test successful project update."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        updated_project = Mock(spec=Project)
        updated_project.id = self.project_id
        updated_project.name = "Updated Project Name"
        updated_project.tenant_id = self.tenant_id
        updated_project.created_at = datetime.now(timezone.utc)
        updated_project.updated_at = datetime.now(timezone.utc)
        updated_project.deleted_at = None
        
        mock_repo.get_for_update_or_404.return_value = self.mock_project
        mock_repo.update.return_value = updated_project
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        update_data = {"name": "Updated Project Name"}
        
        response = client.patch(f"/api/v1/projects/{self.project_id}/", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project Name"
    
    def test_update_project_not_found(self, client: TestClient):
        """Test update of non-existent project."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.get_for_update_or_404.side_effect = HTTPException(status_code=404, detail="Project not found or access denied")
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        update_data = {"name": "Updated Project Name"}
        
        response = client.patch(f"/api/v1/projects/{self.project_id}/", json=update_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Project not found or access denied"
    
    def test_update_project_partial(self, client: TestClient):
        """Test partial project update (no fields provided)."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.get_for_update_or_404.return_value = self.mock_project
        mock_repo.update.return_value = self.mock_project
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        original_name = self.mock_project.name
        
        # Send empty update data
        response = client.patch(f"/api/v1/projects/{self.project_id}/", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == original_name
    
    def test_delete_project_success(self, client: TestClient):
        """Test successful project deletion (soft delete)."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.get_for_update_or_404.return_value = self.mock_project
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/projects/{self.project_id}/")
        
        assert response.status_code == 204
        mock_repo.soft_delete.assert_called_once_with(self.mock_project)
    
    def test_delete_project_not_found(self, client: TestClient):
        """Test deletion of non-existent project."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.get_for_update_or_404.side_effect = HTTPException(status_code=404, detail="Project not found or access denied")
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/projects/{self.project_id}/")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Project not found or access denied"
    
    def test_restore_project_success(self, client: TestClient):
        """Test successful project restoration."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        restored_project = Mock(spec=Project)
        restored_project.id = self.project_id
        restored_project.name = "Test Project"
        restored_project.tenant_id = self.tenant_id
        restored_project.created_at = datetime.now(timezone.utc)
        restored_project.updated_at = datetime.now(timezone.utc)
        restored_project.deleted_at = None
        
        mock_repo.get_for_update_or_404.return_value = self.mock_project
        mock_repo.restore.return_value = restored_project
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        response = client.patch(f"/api/v1/projects/{self.project_id}/restore/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.project_id
    
    def test_restore_project_not_found(self, client: TestClient):
        """Test restoration of non-existent project."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.get_for_update_or_404.side_effect = HTTPException(status_code=404, detail="Project not found or access denied")
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        response = client.patch(f"/api/v1/projects/{self.project_id}/restore/")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Project not found or access denied"
    
    def test_restore_project_not_deleted(self, client: TestClient):
        """Test restoration of project that is not deleted."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository
        mock_repo = Mock(spec=ProjectRepository)
        mock_repo.get_for_update_or_404.return_value = self.mock_project
        mock_repo.restore.side_effect = HTTPException(status_code=400, detail="Project is not deleted")
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        response = client.patch(f"/api/v1/projects/{self.project_id}/restore/")
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Project is not deleted"
    
    def test_project_endpoints_no_authentication(self, client: TestClient):
        """Test project endpoints without authentication."""
        project_data = {"name": "Test Project"}
        
        # Test all endpoints without authentication
        response = client.post("/api/v1/projects/", json=project_data)
        assert response.status_code == 401
        
        response = client.get("/api/v1/projects/")
        assert response.status_code == 401
        
        response = client.get(f"/api/v1/projects/{self.project_id}/")
        assert response.status_code == 401
        
        response = client.patch(f"/api/v1/projects/{self.project_id}/", json={"name": "Updated"})
        assert response.status_code == 401
        
        response = client.delete(f"/api/v1/projects/{self.project_id}/")
        assert response.status_code == 401
        
        response = client.patch(f"/api/v1/projects/{self.project_id}/restore/")
        assert response.status_code == 401
    
    def test_project_invalid_uuid(self, client: TestClient):
        """Test endpoints with invalid UUID format."""
        from utils.get_current_account import get_current_account
        from repositories.project_repository import get_project_repository
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock repository (won't be called due to validation error)
        mock_repo = Mock(spec=ProjectRepository)
        app.dependency_overrides[get_project_repository] = lambda: mock_repo
        
        invalid_id = "not-a-uuid"
        
        response = client.get(f"/api/v1/projects/{invalid_id}/")
        assert response.status_code == 422
        
        response = client.patch(f"/api/v1/projects/{invalid_id}/", json={"name": "Updated"})
        assert response.status_code == 422
        
        response = client.delete(f"/api/v1/projects/{invalid_id}/")
        assert response.status_code == 422
        
        response = client.patch(f"/api/v1/projects/{invalid_id}/restore/")
        assert response.status_code == 422