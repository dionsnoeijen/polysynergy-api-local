import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from uuid import uuid4

from models import Project, Account
from schemas.env_var import EnvVarOut, EnvVarStageValue


@pytest.mark.integration
class TestEnvVarEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.tenant_id = str(uuid4())
        self.project_id = str(uuid4())
        self.account_id = str(uuid4())
        
        # Mock account
        self.mock_account = Mock(spec=Account)
        self.mock_account.id = self.account_id
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.tenant_id = self.tenant_id
        self.mock_project.name = "Test Project"
        
        # Mock env var data
        self.mock_env_var_data = {
            "key": "DATABASE_URL",
            "values": {
                "development": EnvVarStageValue(
                    id="dev-id-123",
                    value="postgres://localhost:5432/test_dev"
                ),
                "production": EnvVarStageValue(
                    id="prod-id-456", 
                    value="postgres://prod:5432/test_prod"
                )
            }
        }
    
    def teardown_method(self):
        """Clean up after each test."""
        from main import app
        app.dependency_overrides.clear()
    
    def test_list_env_vars_success(self, client: TestClient):
        """Test successful environment variable listing."""
        # Override authentication dependencies
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock env var manager
        mock_manager = Mock()
        mock_env_vars = [
            EnvVarOut(**self.mock_env_var_data),
            EnvVarOut(
                key="API_KEY",
                values={
                    "development": EnvVarStageValue(id="dev-api-123", value="dev-key-123"),
                    "production": EnvVarStageValue(id="prod-api-456", value="prod-key-456")
                }
            )
        ]
        mock_manager.list_vars.return_value = mock_env_vars
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        response = client.get(f"/api/v1/env-vars/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["key"] == "DATABASE_URL"
        assert data[0]["values"]["development"]["value"] == "postgres://localhost:5432/test_dev"
        assert data[1]["key"] == "API_KEY"
        
        mock_manager.list_vars.assert_called_once_with(self.project_id)
    
    def test_list_env_vars_empty(self, client: TestClient):
        """Test environment variable listing when no variables exist."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        mock_manager = Mock()
        mock_manager.list_vars.return_value = []
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        response = client.get(f"/api/v1/env-vars/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_list_env_vars_manager_error(self, client: TestClient):
        """Test environment variable listing when manager raises an error."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        mock_manager = Mock()
        mock_manager.list_vars.side_effect = Exception("DynamoDB connection failed")
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        response = client.get(f"/api/v1/env-vars/?project_id={self.project_id}")
        
        assert response.status_code == 500
        data = response.json()
        assert "Error retrieving env vars" in data["detail"]
        assert "DynamoDB connection failed" in data["detail"]
    
    def test_create_env_var_success(self, client: TestClient):
        """Test successful environment variable creation."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        mock_manager = Mock()
        created_env_var = EnvVarOut(**self.mock_env_var_data)
        mock_manager.set_var.return_value = created_env_var
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        payload = {
            "key": "NEW_VAR",
            "value": "new-value-123",
            "stage": "development"
        }
        
        response = client.post(f"/api/v1/env-vars/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "DATABASE_URL"  # From mock data
        
        mock_manager.set_var.assert_called_once_with(
            self.project_id, "development", "NEW_VAR", "new-value-123"
        )
    
    def test_create_env_var_validation_error(self, client: TestClient):
        """Test environment variable creation with validation errors."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Missing required fields
        payload = {
            "key": "TEST_VAR",
            "value": "test-value"
            # Missing 'stage' field
        }
        
        response = client.post(f"/api/v1/env-vars/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_create_env_var_manager_error(self, client: TestClient):
        """Test environment variable creation when manager raises an error."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        mock_manager = Mock()
        mock_manager.set_var.side_effect = Exception("AWS Secrets Manager access denied")
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        payload = {
            "key": "TEST_VAR",
            "value": "test-value", 
            "stage": "development"
        }
        
        response = client.post(f"/api/v1/env-vars/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 500
        data = response.json()
        assert "Error creating env var" in data["detail"]
        assert "AWS Secrets Manager access denied" in data["detail"]
    
    def test_delete_env_var_success(self, client: TestClient):
        """Test successful environment variable deletion."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        mock_manager = Mock()
        mock_manager.delete_var.return_value = None
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        stage = "development"
        key = "OLD_VAR"
        
        response = client.delete(f"/api/v1/env-vars/{stage}/{key}/?project_id={self.project_id}")
        
        assert response.status_code == 204
        
        mock_manager.delete_var.assert_called_once_with(self.project_id, stage, key)
    
    def test_delete_env_var_manager_error(self, client: TestClient):
        """Test environment variable deletion when manager raises an error."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        mock_manager = Mock()
        mock_manager.delete_var.side_effect = Exception("Variable not found in AWS")
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        stage = "production"
        key = "NONEXISTENT_VAR"
        
        response = client.delete(f"/api/v1/env-vars/{stage}/{key}/?project_id={self.project_id}")
        
        assert response.status_code == 500
        data = response.json()
        assert "Error deleting env var" in data["detail"]
        assert "Variable not found in AWS" in data["detail"]
    
    def test_create_env_var_special_characters(self, client: TestClient):
        """Test environment variable creation with special characters."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        mock_manager = Mock()
        created_env_var = EnvVarOut(**self.mock_env_var_data)
        mock_manager.set_var.return_value = created_env_var
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        payload = {
            "key": "COMPLEX_VAR",
            "value": "value-with-@special#chars$and%symbols&123",
            "stage": "testing"
        }
        
        response = client.post(f"/api/v1/env-vars/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 201
        
        mock_manager.set_var.assert_called_once_with(
            self.project_id, "testing", "COMPLEX_VAR", "value-with-@special#chars$and%symbols&123"
        )
    
    def test_delete_env_var_with_special_characters(self, client: TestClient):
        """Test environment variable deletion with special characters in key/stage."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        mock_manager = Mock()
        mock_manager.delete_var.return_value = None
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        stage = "pre-production"
        key = "API_KEY_V2"
        
        response = client.delete(f"/api/v1/env-vars/{stage}/{key}/?project_id={self.project_id}")
        
        assert response.status_code == 204
        
        mock_manager.delete_var.assert_called_once_with(self.project_id, stage, key)
    
    def test_create_env_var_empty_value(self, client: TestClient):
        """Test environment variable creation with empty value."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        mock_manager = Mock()
        created_env_var = EnvVarOut(**self.mock_env_var_data)
        mock_manager.set_var.return_value = created_env_var
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        payload = {
            "key": "EMPTY_VAR",
            "value": "",
            "stage": "development"
        }
        
        response = client.post(f"/api/v1/env-vars/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 201
        
        mock_manager.set_var.assert_called_once_with(
            self.project_id, "development", "EMPTY_VAR", ""
        )
    
    def test_create_env_var_long_value(self, client: TestClient):
        """Test environment variable creation with long value."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.env_var_manager import get_env_var_manager
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        mock_manager = Mock()
        created_env_var = EnvVarOut(**self.mock_env_var_data)
        mock_manager.set_var.return_value = created_env_var
        app.dependency_overrides[get_env_var_manager] = lambda: mock_manager
        
        long_value = "x" * 1000  # Very long value
        payload = {
            "key": "LONG_VAR",
            "value": long_value,
            "stage": "development"
        }
        
        response = client.post(f"/api/v1/env-vars/?project_id={self.project_id}", json=payload)
        
        assert response.status_code == 201
        
        mock_manager.set_var.assert_called_once_with(
            self.project_id, "development", "LONG_VAR", long_value
        )
    
    def test_env_var_endpoints_no_authentication(self, client: TestClient):
        """Test environment variable endpoints without authentication."""
        # List env vars
        response = client.get(f"/api/v1/env-vars/?project_id={self.project_id}")
        assert response.status_code == 401
        
        # Create env var
        payload = {
            "key": "TEST_VAR",
            "value": "test-value",
            "stage": "development"
        }
        response = client.post(f"/api/v1/env-vars/?project_id={self.project_id}", json=payload)
        assert response.status_code == 401
        
        # Delete env var
        response = client.delete(f"/api/v1/env-vars/development/TEST_VAR/?project_id={self.project_id}")
        assert response.status_code == 401