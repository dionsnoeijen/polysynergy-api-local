import pytest
import json
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4

from models import Project, Stage
from polysynergy_node_runner.services.secrets_manager import SecretsManager


@pytest.mark.integration
class TestSecretEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.project_id = uuid4()
        
        # Mock project with stages
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.name = "Test Project"
        
        # Mock stages
        mock_stage1 = Mock(spec=Stage)
        mock_stage1.name = "development"
        mock_stage2 = Mock(spec=Stage)
        mock_stage2.name = "production"
        self.mock_project.stages = [mock_stage1, mock_stage2]
        
        # Mock secrets manager
        self.mock_secrets_manager = Mock(spec=SecretsManager)
        self.mock_secrets_manager.client = Mock()
        
        # Create a proper ResourceNotFoundException class
        class ResourceNotFoundException(Exception):
            pass
        
        self.mock_secrets_manager.client.exceptions = Mock()
        self.mock_secrets_manager.client.exceptions.ResourceNotFoundException = ResourceNotFoundException
    
    def teardown_method(self):
        """Clean up after each test."""
        from main import app
        app.dependency_overrides.clear()
    
    def test_list_secrets_success(self, client: TestClient):
        """Test successful retrieval of secrets list."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        # Mock secrets manager response
        mock_secrets = [
            {"Name": f"polysynergy@development@api_key"},
            {"Name": f"polysynergy@production@api_key"},
            {"Name": f"polysynergy@development@db_password"},
        ]
        self.mock_secrets_manager.list_secrets.return_value = mock_secrets
        
        response = client.get(f"/api/v1/secrets/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # api_key and db_password
        
        # Check api_key secret
        api_key_secret = next((s for s in data if s["key"] == "api_key"), None)
        assert api_key_secret is not None
        assert set(api_key_secret["stages"]) == {"development", "production"}
        
        # Check db_password secret
        db_password_secret = next((s for s in data if s["key"] == "db_password"), None)
        assert db_password_secret is not None
        assert db_password_secret["stages"] == ["development"]
    
    def test_list_secrets_empty(self, client: TestClient):
        """Test retrieval of empty secrets list."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        # Mock empty secrets response
        self.mock_secrets_manager.list_secrets.return_value = []
        
        response = client.get(f"/api/v1/secrets/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_list_secrets_invalid_format_ignored(self, client: TestClient):
        """Test that secrets with invalid name format are ignored."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        # Mock secrets with invalid formats
        mock_secrets = [
            {"Name": "invalid_format"},  # Should be ignored
            {"Name": "also@invalid"},    # Should be ignored
            {"Name": f"polysynergy@development@valid_key"},  # Should be included
        ]
        self.mock_secrets_manager.list_secrets.return_value = mock_secrets
        
        response = client.get(f"/api/v1/secrets/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["key"] == "valid_key"
    
    def test_list_secrets_error(self, client: TestClient):
        """Test secrets listing with service error."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        # Mock secrets manager error
        self.mock_secrets_manager.list_secrets.side_effect = Exception("AWS Error")
        
        response = client.get(f"/api/v1/secrets/?project_id={self.project_id}")
        
        assert response.status_code == 500
        data = response.json()
        assert "Error retrieving secrets" in data["detail"]
    
    def test_create_secret_success(self, client: TestClient):
        """Test successful secret creation."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        secret_data = {
            "key": "new_api_key",
            "secret_value": "secret123",
            "stage": "development"
        }
        
        response = client.post(f"/api/v1/secrets/?project_id={self.project_id}", json=secret_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "new_api_key"
        assert data["project_id"] == str(self.project_id)
        assert data["stages"] == ["development"]
        
        # Verify service was called
        self.mock_secrets_manager.create_secret.assert_called_once_with(
            "new_api_key", "secret123", str(self.project_id), "development"
        )
    
    def test_create_secret_missing_fields(self, client: TestClient):
        """Test secret creation with missing required fields."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        # Test missing key
        response = client.post(f"/api/v1/secrets/?project_id={self.project_id}", json={
            "secret_value": "secret123",
            "stage": "development"
        })
        assert response.status_code == 422  # Pydantic validation error
        
        # Test missing secret_value
        response = client.post(f"/api/v1/secrets/?project_id={self.project_id}", json={
            "key": "api_key",
            "stage": "development"
        })
        assert response.status_code == 422  # Pydantic validation error
        
        # Test missing stage
        response = client.post(f"/api/v1/secrets/?project_id={self.project_id}", json={
            "key": "api_key",
            "secret_value": "secret123"
        })
        assert response.status_code == 422  # Pydantic validation error
    
    def test_create_secret_empty_fields(self, client: TestClient):
        """Test secret creation with empty fields."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        secret_data = {
            "key": "",
            "secret_value": "secret123",
            "stage": "development"
        }
        
        response = client.post(f"/api/v1/secrets/?project_id={self.project_id}", json=secret_data)
        
        assert response.status_code == 400
        assert "Missing 'key'" in response.json()["detail"]
    
    def test_create_secret_service_error(self, client: TestClient):
        """Test secret creation with service error."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        # Mock service error
        self.mock_secrets_manager.create_secret.side_effect = Exception("AWS Error")
        
        secret_data = {
            "key": "api_key",
            "secret_value": "secret123",
            "stage": "development"
        }
        
        response = client.post(f"/api/v1/secrets/?project_id={self.project_id}", json=secret_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Error creating secret" in data["detail"]
    
    def test_update_secret_success(self, client: TestClient):
        """Test successful secret update."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        secret_data = {
            "key": "existing_key",
            "secret_value": "new_secret_value",
            "stage": "production"
        }
        
        response = client.put(f"/api/v1/secrets/?project_id={self.project_id}", json=secret_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "existing_key"
        assert data["project_id"] == str(self.project_id)
        assert data["stages"] == ["production"]
        
        # Verify service was called
        self.mock_secrets_manager.update_secret_by_key.assert_called_once_with(
            "existing_key", "new_secret_value", str(self.project_id), "production"
        )
    
    def test_update_secret_missing_value(self, client: TestClient):
        """Test secret update with missing secret value."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        secret_data = {
            "key": "existing_key",
            "stage": "production"
        }
        
        response = client.put(f"/api/v1/secrets/?project_id={self.project_id}", json=secret_data)
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_update_secret_empty_value(self, client: TestClient):
        """Test secret update with empty secret value."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        secret_data = {
            "key": "existing_key",
            "secret_value": "",
            "stage": "production"
        }
        
        response = client.put(f"/api/v1/secrets/?project_id={self.project_id}", json=secret_data)
        
        assert response.status_code == 400
        assert "Missing 'secret_value'" in response.json()["detail"]
    
    def test_update_secret_service_error(self, client: TestClient):
        """Test secret update with service error."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        # Mock service error
        self.mock_secrets_manager.update_secret_by_key.side_effect = Exception("AWS Error")
        
        secret_data = {
            "key": "existing_key",
            "secret_value": "new_value",
            "stage": "production"
        }
        
        response = client.put(f"/api/v1/secrets/?project_id={self.project_id}", json=secret_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Error updating secret" in data["detail"]
    
    def test_delete_secret_success(self, client: TestClient):
        """Test successful secret deletion."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        delete_data = {"key": "secret_to_delete"}
        
        response = client.request(
            "DELETE",
            f"/api/v1/secrets/?project_id={self.project_id}", 
            content=json.dumps(delete_data),
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        
        # Should try to delete from all stages plus mock
        expected_stages = {"development", "production", "mock"}
        actual_stages = {result["stage"] for result in data["results"]}
        assert actual_stages == expected_stages
        
        # All should be marked as deleted (since no exception was raised)
        for result in data["results"]:
            assert result["deleted"] is True
            assert result["error"] is None
        
        # Verify service was called for each stage
        assert self.mock_secrets_manager.delete_secret_by_key.call_count == 3
    
    def test_delete_secret_partial_success(self, client: TestClient):
        """Test secret deletion with some failures."""
        from utils.get_current_account import get_project_or_403
        from services.secrets_manager import get_secrets_manager
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        app.dependency_overrides[get_secrets_manager] = lambda: self.mock_secrets_manager
        
        # Mock partial failure - ResourceNotFoundException for development stage
        def mock_delete_side_effect(key, project_id, stage):
            if stage == "development":
                raise self.mock_secrets_manager.client.exceptions.ResourceNotFoundException("Not found")
            if stage == "production":
                raise Exception("Other error")
            # mock stage succeeds
        
        self.mock_secrets_manager.delete_secret_by_key.side_effect = mock_delete_side_effect
        
        delete_data = {"key": "secret_to_delete"}
        
        response = client.request(
            "DELETE",
            f"/api/v1/secrets/?project_id={self.project_id}", 
            content=json.dumps(delete_data),
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check results
        results_by_stage = {r["stage"]: r for r in data["results"]}
        
        # Mock should succeed
        assert results_by_stage["mock"]["deleted"] is True
        assert results_by_stage["mock"]["error"] is None
        
        # Development should fail with ResourceNotFoundException (marked as not deleted, no error)
        assert results_by_stage["development"]["deleted"] is False
        assert results_by_stage["development"]["error"] is None
        
        # Production should fail with other error
        assert results_by_stage["production"]["deleted"] is False
        assert results_by_stage["production"]["error"] == "Other error"
    
    def test_delete_secret_validation_error(self, client: TestClient):
        """Test secret deletion with validation error."""
        from utils.get_current_account import get_project_or_403
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Missing key in request body
        response = client.request(
            "DELETE",
            f"/api/v1/secrets/?project_id={self.project_id}", 
            content=json.dumps({}),
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_secret_endpoints_invalid_project(self, client: TestClient):
        """Test secret endpoints with invalid project access."""
        # Don't override get_project_or_403, so it should fail with 401/403
        
        response = client.get(f"/api/v1/secrets/?project_id={self.project_id}")
        assert response.status_code == 401
        
        response = client.post(f"/api/v1/secrets/?project_id={self.project_id}", json={
            "key": "test", "secret_value": "value", "stage": "dev"
        })
        assert response.status_code == 401
        
        response = client.put(f"/api/v1/secrets/?project_id={self.project_id}", json={
            "key": "test", "secret_value": "value", "stage": "dev"
        })
        assert response.status_code == 401
        
        response = client.request(
            "DELETE",
            f"/api/v1/secrets/?project_id={self.project_id}", 
            content=json.dumps({"key": "test"}),
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401