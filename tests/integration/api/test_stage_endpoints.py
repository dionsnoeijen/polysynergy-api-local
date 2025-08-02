import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from uuid import uuid4

from models import Stage, Project
from repositories.stage_repository import StageRepository


@pytest.mark.integration
class TestStageEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.project_id = uuid4()
        self.stage_id = uuid4()
        self.tenant_id = uuid4()
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.name = "Test Project"
        self.mock_project.tenant_id = self.tenant_id
        
        # Mock stage
        self.mock_stage = Mock(spec=Stage)
        self.mock_stage.id = str(self.stage_id)
        self.mock_stage.name = "development"
        self.mock_stage.is_production = False
        self.mock_stage.order = 1
        self.mock_stage.project_id = self.project_id
        self.mock_stage.created_at = datetime.now(timezone.utc)
        self.mock_stage.updated_at = datetime.now(timezone.utc)
    
    def teardown_method(self):
        """Clean up after each test."""
        from main import app
        app.dependency_overrides.clear()
    
    def test_list_stages_success(self, client: TestClient):
        """Test successful retrieval of stages list."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        stages = [self.mock_stage]
        mock_repo.get_all_by_project.return_value = stages
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/stages/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        mock_repo.get_all_by_project.assert_called_once_with(self.mock_project)
    
    def test_list_stages_empty(self, client: TestClient):
        """Test retrieval of empty stages list."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository with empty results
        mock_repo = Mock(spec=StageRepository)
        mock_repo.get_all_by_project.return_value = []
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/stages/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_get_stage_success(self, client: TestClient):
        """Test successful retrieval of single stage."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        mock_repo.get_by_id.return_value = self.mock_stage
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(self.stage_id)
        mock_repo.get_by_id.assert_called_once_with(str(self.stage_id), self.mock_project)
    
    def test_get_stage_not_found(self, client: TestClient):
        """Test retrieval of non-existent stage."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=StageRepository)
        mock_repo.get_by_id.side_effect = HTTPException(
            status_code=404, detail="Stage not found"
        )
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Stage not found"
    
    def test_create_stage_success(self, client: TestClient):
        """Test successful stage creation."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        mock_repo.create.return_value = self.mock_stage
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_data = {
            "name": "Testing",
            "is_production": False
        }
        
        response = client.post(f"/api/v1/stages/?project_id={self.project_id}", json=stage_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == str(self.stage_id)
        mock_repo.create.assert_called_once()
    
    def test_create_stage_production(self, client: TestClient):
        """Test creating a production stage."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        production_stage = Mock(spec=Stage)
        production_stage.id = str(self.stage_id)
        production_stage.name = "production"
        production_stage.is_production = True
        production_stage.order = 2
        mock_repo.create.return_value = production_stage
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_data = {
            "name": "Production",
            "is_production": True
        }
        
        response = client.post(f"/api/v1/stages/?project_id={self.project_id}", json=stage_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["is_production"] is True
    
    def test_create_stage_reserved_name(self, client: TestClient):
        """Test stage creation with reserved name 'mock'."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises error for reserved name
        mock_repo = Mock(spec=StageRepository)
        mock_repo.create.side_effect = HTTPException(
            status_code=400, detail="'mock' is a reserved stage name."
        )
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_data = {
            "name": "mock",
            "is_production": False
        }
        
        response = client.post(f"/api/v1/stages/?project_id={self.project_id}", json=stage_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "'mock' is a reserved stage name" in data["detail"]
    
    def test_create_stage_duplicate_name(self, client: TestClient):
        """Test stage creation with duplicate name."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises error for duplicate name
        mock_repo = Mock(spec=StageRepository)
        mock_repo.create.side_effect = HTTPException(
            status_code=400, detail="Stage with this name already exists."
        )
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_data = {
            "name": "Development",
            "is_production": False
        }
        
        response = client.post(f"/api/v1/stages/?project_id={self.project_id}", json=stage_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Stage with this name already exists" in data["detail"]
    
    def test_create_stage_validation_error(self, client: TestClient):
        """Test stage creation with validation errors."""
        from utils.get_current_account import get_project_or_403
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Send invalid data (missing required fields)
        response = client.post(f"/api/v1/stages/?project_id={self.project_id}", json={})
        
        assert response.status_code == 422
    
    def test_update_stage_success(self, client: TestClient):
        """Test successful stage update."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        updated_stage = Mock(spec=Stage)
        updated_stage.id = str(self.stage_id)
        updated_stage.name = "updated"
        updated_stage.is_production = False
        updated_stage.order = 1
        
        mock_repo.update.return_value = updated_stage
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_data = {
            "name": "Updated",
            "is_production": False
        }
        
        response = client.put(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}", json=stage_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated"
        mock_repo.update.assert_called_once()
    
    def test_update_stage_not_found(self, client: TestClient):
        """Test update of non-existent stage."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=StageRepository)
        mock_repo.update.side_effect = HTTPException(status_code=404, detail="Stage not found")
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_data = {
            "name": "Updated Stage"
        }
        
        response = client.put(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}", json=stage_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Stage not found"
    
    def test_update_stage_production_flag(self, client: TestClient):
        """Test updating stage production flag."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        production_stage = Mock(spec=Stage)
        production_stage.id = str(self.stage_id)
        production_stage.name = "production"
        production_stage.is_production = True
        production_stage.order = 1
        
        mock_repo.update.return_value = production_stage
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_data = {
            "is_production": True
        }
        
        response = client.put(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}", json=stage_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_production"] is True
    
    def test_update_stage_reserved_name(self, client: TestClient):
        """Test update fails with reserved name 'mock'."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises error for reserved name
        mock_repo = Mock(spec=StageRepository)
        mock_repo.update.side_effect = HTTPException(
            status_code=400, detail="'mock' is a reserved name."
        )
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_data = {
            "name": "mock"
        }
        
        response = client.put(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}", json=stage_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "'mock' is a reserved name" in data["detail"]
    
    def test_delete_stage_success(self, client: TestClient):
        """Test successful stage deletion."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Stage deleted successfully."
        mock_repo.delete.assert_called_once_with(str(self.stage_id), self.mock_project)
    
    def test_delete_stage_not_found(self, client: TestClient):
        """Test deletion of non-existent stage."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=StageRepository)
        mock_repo.delete.side_effect = HTTPException(status_code=404, detail="Stage not found")
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Stage not found"
    
    def test_delete_reserved_stage_mock(self, client: TestClient):
        """Test deletion fails for reserved 'mock' stage."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises error for reserved stage
        mock_repo = Mock(spec=StageRepository)
        mock_repo.delete.side_effect = HTTPException(
            status_code=400, detail="Cannot delete reserved stage 'mock'."
        )
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}")
        
        assert response.status_code == 400
        data = response.json()
        assert "Cannot delete reserved stage 'mock'" in data["detail"]
    
    def test_reorder_stages_success(self, client: TestClient):
        """Test successful stage reordering."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        reorder_data = {
            "stage_ids": stage_ids
        }
        
        response = client.post(f"/api/v1/stages/reorder?project_id={self.project_id}", json=reorder_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Stages reordered successfully."
        mock_repo.reorder.assert_called_once()
    
    def test_reorder_stages_empty_list(self, client: TestClient):
        """Test stage reordering with empty list."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        reorder_data = {
            "stage_ids": []
        }
        
        response = client.post(f"/api/v1/stages/reorder?project_id={self.project_id}", json=reorder_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Stages reordered successfully."
    
    def test_stage_endpoints_no_authentication(self, client: TestClient):
        """Test stage endpoints without authentication."""
        # Don't override get_project_or_403, so it should fail with 401
        
        stage_data = {
            "name": "Test Stage",
            "is_production": False
        }
        
        response = client.get(f"/api/v1/stages/?project_id={self.project_id}")
        assert response.status_code == 401
        
        response = client.get(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}")
        assert response.status_code == 401
        
        response = client.post(f"/api/v1/stages/?project_id={self.project_id}", json=stage_data)
        assert response.status_code == 401
        
        response = client.put(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}", json=stage_data)
        assert response.status_code == 401
        
        response = client.delete(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}")
        assert response.status_code == 401
        
        reorder_data = {"stage_ids": [str(self.stage_id)]}
        response = client.post(f"/api/v1/stages/reorder?project_id={self.project_id}", json=reorder_data)
        assert response.status_code == 401
    
    def test_create_stage_minimal_data(self, client: TestClient):
        """Test stage creation with minimal required data."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        minimal_stage = Mock(spec=Stage)
        minimal_stage.id = str(self.stage_id)
        minimal_stage.name = "minimal"
        minimal_stage.is_production = False
        minimal_stage.order = 1
        mock_repo.create.return_value = minimal_stage
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_data = {
            "name": "Minimal"
            # is_production defaults to False
        }
        
        response = client.post(f"/api/v1/stages/?project_id={self.project_id}", json=stage_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["is_production"] is False
    
    def test_update_stage_partial_data(self, client: TestClient):
        """Test stage update with partial data."""
        from utils.get_current_account import get_project_or_403
        from repositories.stage_repository import get_stage_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=StageRepository)
        mock_repo.update.return_value = self.mock_stage
        app.dependency_overrides[get_stage_repository] = lambda: mock_repo
        
        stage_data = {
            "name": "Only Name Update"
            # No is_production field
        }
        
        response = client.put(f"/api/v1/stages/{self.stage_id}/?project_id={self.project_id}", json=stage_data)
        
        assert response.status_code == 200
        mock_repo.update.assert_called_once()