import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from uuid import uuid4

from models import Project, Account
from schemas.api_key import ApiKeyOut


@pytest.mark.integration  
class TestApiKeyEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.tenant_id = str(uuid4())
        self.project_id = str(uuid4())
        self.key_id = str(uuid4())
        self.api_key = "test-api-key-12345"
        
        # Mock project data
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.tenant_id = self.tenant_id
        self.mock_project.name = "Test Project"
        
        # Mock account data
        self.mock_account = Mock(spec=Account)  
        self.mock_account.id = str(uuid4())
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('services.api_key_service.ApiKeyService.list_keys')
    def test_list_api_keys_success(self, mock_list_keys, mock_get_project, mock_get_account, client: TestClient):
        """Test successful API key listing."""
        # Mock authentication and project access
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        # Mock service response
        mock_keys = [
            ApiKeyOut(
                key_id=self.key_id,
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                label="Test Key 1",
                key=self.api_key,
                type="api_key",
                created_at="2024-01-01T00:00:00"
            ),
            ApiKeyOut(
                key_id=str(uuid4()),
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                label="Test Key 2",
                key="test-api-key-67890",
                type="api_key",
                created_at="2024-01-02T00:00:00"
            )
        ]
        mock_list_keys.return_value = mock_keys
        
        response = client.get(f"/api/v1/api-keys/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["label"] == "Test Key 1"
        assert data[0]["key_id"] == self.key_id
        assert data[1]["label"] == "Test Key 2"
        
        mock_list_keys.assert_called_once_with(self.mock_project)
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('services.api_key_service.ApiKeyService.list_keys')
    def test_list_api_keys_empty(self, mock_list_keys, mock_get_project, mock_get_account, client: TestClient):
        """Test API key listing when no keys exist."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        mock_list_keys.return_value = []
        
        response = client.get(f"/api/v1/api-keys/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('services.api_key_service.ApiKeyService.create')
    def test_create_api_key_success(self, mock_create, mock_get_project, mock_get_account, client: TestClient):
        """Test successful API key creation."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        created_key = ApiKeyOut(
            key_id=self.key_id,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            label="New Test Key",
            key=self.api_key,
            type="api_key",
            created_at="2024-01-01T00:00:00"
        )
        mock_create.return_value = created_key
        
        payload = {
            "label": "New Test Key",
            "key": self.api_key
        }
        
        response = client.post(f"/api/v1/api-keys/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "New Test Key"
        assert data["key"] == self.api_key
        assert data["key_id"] == self.key_id
        
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[0][0].label == "New Test Key"
        assert call_args[0][0].key == self.api_key
        assert call_args[0][1] == self.mock_project
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    def test_create_api_key_validation_error(self, mock_get_project, mock_get_account, client: TestClient):
        """Test API key creation with validation errors."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        # Missing required fields
        payload = {"label": "Test Key"}  # Missing 'key' field
        
        response = client.post(f"/api/v1/api-keys/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('services.api_key_service.ApiKeyService.get_one')
    def test_get_api_key_detail_success(self, mock_get_one, mock_get_project, mock_get_account, client: TestClient):
        """Test successful API key detail retrieval."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        api_key_detail = ApiKeyOut(
            key_id=self.key_id,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            label="Detailed Test Key",
            key=self.api_key,
            type="api_key",
            created_at="2024-01-01T00:00:00"
        )
        mock_get_one.return_value = api_key_detail
        
        response = client.get(f"/api/v1/api-keys/{self.key_id}/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["key_id"] == self.key_id
        assert data["label"] == "Detailed Test Key"
        
        mock_get_one.assert_called_once_with(self.key_id, self.mock_project)
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('services.api_key_service.ApiKeyService.get_one')
    def test_get_api_key_detail_not_found(self, mock_get_one, mock_get_project, mock_get_account, client: TestClient):
        """Test API key detail retrieval when key doesn't exist."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        mock_get_one.side_effect = ValueError("API key not found or doesn't belong to this project.")
        
        response = client.get(f"/api/v1/api-keys/{self.key_id}/?project_id={self.project_id}")
        
        assert response.status_code == 500
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('services.api_key_service.ApiKeyService.update')
    def test_update_api_key_success(self, mock_update, mock_get_project, mock_get_account, client: TestClient):
        """Test successful API key update."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        updated_key = ApiKeyOut(
            key_id=self.key_id,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            label="Updated Test Key",
            key=self.api_key,
            type="api_key",
            created_at="2024-01-01T00:00:00"
        )
        mock_update.return_value = updated_key
        
        payload = {"label": "Updated Test Key"}
        
        response = client.patch(f"/api/v1/api-keys/{self.key_id}/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Updated Test Key"
        assert data["key_id"] == self.key_id
        
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][0] == self.key_id
        assert call_args[0][1].label == "Updated Test Key"
        assert call_args[0][2] == self.mock_project
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('services.api_key_service.ApiKeyService.delete')
    def test_delete_api_key_success(self, mock_delete, mock_get_project, mock_get_account, client: TestClient):
        """Test successful API key deletion."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        mock_delete.return_value = None
        
        response = client.delete(f"/api/v1/api-keys/{self.key_id}/?project_id={self.project_id}")
        
        assert response.status_code == 204
        
        mock_delete.assert_called_once_with(self.key_id, self.mock_project)
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('services.api_key_service.ApiKeyService.delete')
    def test_delete_api_key_not_found(self, mock_delete, mock_get_project, mock_get_account, client: TestClient):
        """Test API key deletion when key doesn't exist."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        mock_delete.side_effect = ValueError("API key not found or doesn't belong to this project.")
        
        response = client.delete(f"/api/v1/api-keys/{self.key_id}/?project_id={self.project_id}")
        
        assert response.status_code == 500
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('services.api_key_service.ApiKeyService.assign_keys_to_route')
    def test_assign_api_keys_to_route_success(self, mock_assign, mock_get_project, mock_get_account, client: TestClient):
        """Test successful API key assignment to route."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        route_id = str(uuid4())
        api_key_refs = ["key1", "key2", "key3"]
        expected_result = {"route_id": route_id, "api_keys_assigned": api_key_refs}
        mock_assign.return_value = expected_result
        
        response = client.patch(
            f"/api/v1/api-keys/assign/{route_id}/?project_id={self.project_id}",
            json=api_key_refs
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["route_id"] == route_id
        assert data["api_keys_assigned"] == api_key_refs
        
        mock_assign.assert_called_once_with(route_id, api_key_refs, self.mock_project)
    
    @patch('utils.get_current_account.get_current_account')
    @patch('utils.get_current_account.get_project_or_403')
    @patch('services.api_key_service.ApiKeyService.assign_keys_to_route')
    def test_assign_api_keys_to_route_empty_list(self, mock_assign, mock_get_project, mock_get_account, client: TestClient):
        """Test API key assignment with empty key list."""
        mock_get_account.return_value = self.mock_account
        mock_get_project.return_value = self.mock_project
        
        route_id = str(uuid4())
        api_key_refs = []
        expected_result = {"route_id": route_id, "api_keys_assigned": api_key_refs}
        mock_assign.return_value = expected_result
        
        response = client.patch(
            f"/api/v1/api-keys/assign/{route_id}/?project_id={self.project_id}",
            json=api_key_refs
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["route_id"] == route_id
        assert data["api_keys_assigned"] == []