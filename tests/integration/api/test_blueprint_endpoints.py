import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime

from models import Project, Account, Blueprint, NodeSetup
from schemas.blueprint import BlueprintMetadata


@pytest.mark.integration
class TestBlueprintEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.tenant_id = str(uuid4())
        self.project_id = str(uuid4())
        self.blueprint_id = str(uuid4())
        self.account_id = str(uuid4())
        
        # Mock account
        self.mock_account = Mock(spec=Account)
        self.mock_account.id = self.account_id
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.tenant_id = self.tenant_id
        self.mock_project.name = "Test Project"
        
        # Mock blueprint data
        self.mock_blueprint_data = {
            "id": self.blueprint_id,
            "name": "Test Blueprint",
            "meta": {
                "icon": "blueprint-icon",
                "category": "utilities",
                "description": "A test blueprint for unit testing"
            },
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "node_setup": None
        }
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('repositories.blueprint_repository.BlueprintRepository.get_all_by_project')
    def test_list_blueprints_success(self, mock_get_all, mock_get_project, mock_get_account, client: TestClient):
        """Test successful blueprint listing."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        # Mock repository response
        mock_blueprints = [
            Mock(**self.mock_blueprint_data),
            Mock(**{**self.mock_blueprint_data, "id": str(uuid4()), "name": "Another Blueprint"})
        ]
        mock_get_all.return_value = mock_blueprints
        
        response = client.get(f"/api/v1/blueprints/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Test Blueprint"
        assert data[0]["meta"]["category"] == "utilities"
        assert data[1]["name"] == "Another Blueprint"
        
        mock_get_all.assert_called_once_with(self.mock_project)
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('repositories.blueprint_repository.BlueprintRepository.get_all_by_project')
    def test_list_blueprints_empty(self, mock_get_all, mock_get_project, mock_get_account, client: TestClient):
        """Test blueprint listing when no blueprints exist."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        mock_get_all.return_value = []
        
        response = client.get(f"/api/v1/blueprints/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('repositories.blueprint_repository.BlueprintRepository.create')
    def test_create_blueprint_success(self, mock_create, mock_get_project, mock_get_account, client: TestClient):
        """Test successful blueprint creation."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        # Mock repository response
        created_blueprint = Mock(**self.mock_blueprint_data)
        mock_create.return_value = created_blueprint
        
        payload = {
            "name": "New Test Blueprint",
            "meta": {
                "icon": "new-icon",
                "category": "automation", 
                "description": "A new blueprint for testing creation"
            }
        }
        
        response = client.post(f"/api/v1/blueprints/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Blueprint"
        assert data["meta"]["category"] == "utilities"
        
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[0][0].name == "New Test Blueprint"
        assert call_args[0][0].meta.category == "automation"
        assert call_args[0][1] == self.mock_project
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    def test_create_blueprint_validation_error(self, mock_get_project, mock_get_account, client: TestClient):
        """Test blueprint creation with validation errors."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        # Missing required 'name' field
        payload = {
            "meta": {
                "icon": "test-icon",
                "category": "test",
                "description": "Test description"
            }
        }
        
        response = client.post(f"/api/v1/blueprints/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('repositories.blueprint_repository.BlueprintRepository.get_one_with_versions_by_id')
    def test_get_blueprint_success(self, mock_get_one, mock_get_project, mock_get_account, client: TestClient):
        """Test successful blueprint detail retrieval."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        # Mock repository response
        blueprint_detail = Mock(**self.mock_blueprint_data)
        mock_get_one.return_value = blueprint_detail
        
        response = client.get(f"/api/v1/blueprints/{self.blueprint_id}/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.blueprint_id
        assert data["name"] == "Test Blueprint"
        assert data["meta"]["description"] == "A test blueprint for unit testing"
        
        mock_get_one.assert_called_once_with(self.blueprint_id, self.mock_project)
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('repositories.blueprint_repository.BlueprintRepository.get_one_with_versions_by_id')
    def test_get_blueprint_not_found(self, mock_get_one, mock_get_project, mock_get_account, client: TestClient):
        """Test blueprint detail retrieval when blueprint doesn't exist."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        from fastapi import HTTPException
        mock_get_one.side_effect = HTTPException(status_code=404, detail="Blueprint not found")
        
        response = client.get(f"/api/v1/blueprints/{self.blueprint_id}/?project_id={self.project_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Blueprint not found"
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('repositories.blueprint_repository.BlueprintRepository.update')
    def test_update_blueprint_success(self, mock_update, mock_get_project, mock_get_account, client: TestClient):
        """Test successful blueprint update."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        # Mock repository response
        updated_blueprint = Mock(**{**self.mock_blueprint_data, "name": "Updated Blueprint"})
        mock_update.return_value = updated_blueprint
        
        payload = {
            "name": "Updated Blueprint Name",
            "meta": {
                "icon": "updated-icon",
                "category": "updated-category",
                "description": "Updated description"
            }
        }
        
        response = client.put(f"/api/v1/blueprints/{self.blueprint_id}/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Blueprint"
        
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][0] == self.blueprint_id
        assert call_args[0][1].name == "Updated Blueprint Name"
        assert call_args[0][1].meta.category == "updated-category"
        assert call_args[0][2] == self.mock_project
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('repositories.blueprint_repository.BlueprintRepository.delete')
    def test_delete_blueprint_success(self, mock_delete, mock_get_project, mock_get_account, client: TestClient):
        """Test successful blueprint deletion."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        mock_delete.return_value = None
        
        response = client.delete(f"/api/v1/blueprints/{self.blueprint_id}/?project_id={self.project_id}")
        
        assert response.status_code == 204
        
        mock_delete.assert_called_once_with(self.blueprint_id, self.mock_project)
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('repositories.blueprint_repository.BlueprintRepository.delete')
    def test_delete_blueprint_not_found(self, mock_delete, mock_get_project, mock_get_account, client: TestClient):
        """Test blueprint deletion when blueprint doesn't exist."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        from fastapi import HTTPException
        mock_delete.side_effect = HTTPException(status_code=404, detail="Blueprint not found")
        
        response = client.delete(f"/api/v1/blueprints/{self.blueprint_id}/?project_id={self.project_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Blueprint not found"
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('repositories.blueprint_repository.BlueprintRepository.create')
    def test_create_blueprint_with_minimal_meta(self, mock_create, mock_get_project, mock_get_account, client: TestClient):
        """Test blueprint creation with minimal metadata."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        created_blueprint = Mock(**self.mock_blueprint_data)
        mock_create.return_value = created_blueprint
        
        payload = {
            "name": "Minimal Blueprint",
            "meta": {}  # Empty metadata should be allowed
        }
        
        response = client.post(f"/api/v1/blueprints/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Blueprint"
        
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[0][0].name == "Minimal Blueprint"
        assert call_args[0][0].meta.icon == ""  # Default empty string
        assert call_args[0][0].meta.category == ""
        assert call_args[0][0].meta.description == ""
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('repositories.blueprint_repository.BlueprintRepository.create')
    def test_create_blueprint_with_node_setup(self, mock_create, mock_get_project, mock_get_account, client: TestClient):
        """Test blueprint creation with node setup data."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        created_blueprint = Mock(**self.mock_blueprint_data)
        mock_create.return_value = created_blueprint
        
        payload = {
            "name": "Blueprint with Node Setup",
            "meta": {
                "icon": "setup-icon",
                "category": "advanced",
                "description": "Blueprint with node setup"
            },
            "node_setup": {
                "nodes": ["node1", "node2"],
                "connections": [{"from": "node1", "to": "node2"}]
            }
        }
        
        response = client.post(f"/api/v1/blueprints/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 201
        
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[0][0].node_setup is not None
        assert call_args[0][0].node_setup["nodes"] == ["node1", "node2"]
    
    def test_blueprint_endpoints_no_authentication(self, client: TestClient):
        """Test blueprint endpoints without authentication."""
        # List blueprints
        response = client.get(f"/api/v1/blueprints/?project_id={self.project_id}")
        assert response.status_code == 401
        
        # Create blueprint
        payload = {
            "name": "Test Blueprint",
            "meta": {"icon": "", "category": "", "description": ""}
        }
        response = client.post(f"/api/v1/blueprints/?project_id={self.project_id}", json=payload)
        assert response.status_code == 401
        
        # Get blueprint
        response = client.get(f"/api/v1/blueprints/{self.blueprint_id}/?project_id={self.project_id}")
        assert response.status_code == 401
        
        # Update blueprint
        response = client.put(f"/api/v1/blueprints/{self.blueprint_id}/?project_id={self.project_id}", json=payload)
        assert response.status_code == 401
        
        # Delete blueprint
        response = client.delete(f"/api/v1/blueprints/{self.blueprint_id}/?project_id={self.project_id}")
        assert response.status_code == 401