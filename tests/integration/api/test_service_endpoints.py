import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from uuid import uuid4

from models import Service, Project, NodeSetup, NodeSetupVersion
from repositories.service_repository import ServiceRepository


@pytest.mark.integration
class TestServiceEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.project_id = uuid4()
        self.service_id = uuid4()
        self.version_id = uuid4()
        self.tenant_id = uuid4()
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.name = "Test Project"
        self.mock_project.tenant_id = self.tenant_id
        
        # Mock service
        self.mock_service = Mock(spec=Service)
        self.mock_service.id = self.service_id
        self.mock_service.name = "Test Service"
        self.mock_service.meta = {
            "icon": "test-icon",
            "category": "database",
            "description": "Test database service"
        }
        self.mock_service.tenant_id = self.tenant_id
        self.mock_service.created_at = datetime.now(timezone.utc)
        self.mock_service.updated_at = datetime.now(timezone.utc)
        self.mock_service.projects = [self.mock_project]
        
        # Mock node setup and version
        self.mock_node_setup = Mock(spec=NodeSetup)
        self.mock_node_setup.id = uuid4()
        
        self.mock_version = Mock(spec=NodeSetupVersion)
        self.mock_version.id = self.version_id
        self.mock_version.version_number = 1
    
    def teardown_method(self):
        """Clean up after each test."""
        from main import app
        app.dependency_overrides.clear()
    
    def test_list_services_success(self, client: TestClient):
        """Test successful retrieval of services list."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ServiceRepository)
        services = [self.mock_service]
        mock_repo.get_all_by_project.return_value = services
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/services/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        mock_repo.get_all_by_project.assert_called_once_with(self.mock_project)
    
    def test_list_services_empty(self, client: TestClient):
        """Test retrieval of empty services list."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository with empty results
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.get_all_by_project.return_value = []
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/services/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_get_service_success(self, client: TestClient):
        """Test successful retrieval of single service."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_service
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(self.service_id)
        mock_repo.get_one_with_versions_by_id.assert_called_once()
    
    def test_get_service_not_found(self, client: TestClient):
        """Test retrieval of non-existent service."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.get_one_with_versions_by_id.side_effect = HTTPException(
            status_code=404, detail="Service not found"
        )
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Service not found"
    
    def test_create_service_success(self, client: TestClient):
        """Test successful service creation."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.create.return_value = self.mock_service
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        service_data = {
            "name": "Test Service",
            "meta": {
                "icon": "database-icon",
                "category": "storage",
                "description": "Test database service"
            },
            "node_setup_content": {
                "environment": {
                    "DATABASE_URL": "postgresql://localhost:5432/test"
                }
            }
        }
        
        response = client.post(f"/api/v1/services/?project_id={self.project_id}", json=service_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == str(self.service_id)
        mock_repo.create.assert_called_once()
    
    def test_create_service_minimal_data(self, client: TestClient):
        """Test service creation with minimal required data."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.create.return_value = self.mock_service
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        service_data = {
            "name": "Minimal Service",
            "meta": {
                "icon": "",
                "category": "",
                "description": ""
            }
        }
        
        response = client.post(f"/api/v1/services/?project_id={self.project_id}", json=service_data)
        
        assert response.status_code == 201
        mock_repo.create.assert_called_once()
    
    def test_create_service_validation_error(self, client: TestClient):
        """Test service creation with validation errors."""
        from utils.get_current_account import get_project_or_403
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Send invalid data (missing required fields)
        response = client.post(f"/api/v1/services/?project_id={self.project_id}", json={})
        
        assert response.status_code == 422
    
    def test_create_service_with_complex_node_setup(self, client: TestClient):
        """Test service creation with complex node setup content."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.create.return_value = self.mock_service
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        service_data = {
            "name": "Complex Service",
            "meta": {
                "icon": "microservice-icon",
                "category": "microservice",
                "description": "Complex microservice with full configuration"
            },
            "node_setup_content": {
                "replicas": 3,
                "resources": {
                    "cpu": "500m",
                    "memory": "512Mi"
                },
                "environment": {
                    "NODE_ENV": "production",
                    "LOG_LEVEL": "info"
                },
                "ports": [8080, 9090],
                "healthcheck": {
                    "path": "/health",
                    "interval": 30,
                    "timeout": 5
                }
            }
        }
        
        response = client.post(f"/api/v1/services/?project_id={self.project_id}", json=service_data)
        
        assert response.status_code == 201
        mock_repo.create.assert_called_once()
    
    def test_update_service_success(self, client: TestClient):
        """Test successful service update."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ServiceRepository)
        updated_service = Mock(spec=Service)
        updated_service.id = self.service_id
        updated_service.name = "Updated Service"
        updated_service.meta = {
            "icon": "updated-icon",
            "category": "web",
            "description": "Updated web service"
        }
        updated_service.created_at = datetime.now(timezone.utc)
        updated_service.updated_at = datetime.now(timezone.utc)
        
        mock_repo.update.return_value = updated_service
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        service_data = {
            "name": "Updated Service",
            "meta": {
                "icon": "updated-icon",
                "category": "web",
                "description": "Updated web service"
            },
            "node_setup_content": {
                "updated": "configuration"
            }
        }
        
        response = client.put(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}", json=service_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Service"
        mock_repo.update.assert_called_once()
    
    def test_update_service_not_found(self, client: TestClient):
        """Test update of non-existent service."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.update.side_effect = HTTPException(status_code=404, detail="Service not found")
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        service_data = {
            "name": "Updated Service",
            "meta": {
                "icon": "icon",
                "category": "category",
                "description": "description"
            }
        }
        
        response = client.put(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}", json=service_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Service not found"
    
    def test_update_service_without_node_setup_content(self, client: TestClient):
        """Test service update without node setup content."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.update.return_value = self.mock_service
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        service_data = {
            "name": "Updated Service Name Only",
            "meta": {
                "icon": "simple-icon",
                "category": "utility",
                "description": "Simple update"
            }
        }
        
        response = client.put(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}", json=service_data)
        
        assert response.status_code == 200
        mock_repo.update.assert_called_once()
    
    def test_delete_service_success(self, client: TestClient):
        """Test successful service deletion."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ServiceRepository)
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}")
        
        assert response.status_code == 204
        # Verify delete was called
        args, kwargs = mock_repo.delete.call_args
        assert args[0] == str(self.service_id)  # First arg is the service_id as string
        assert args[1] == self.mock_project      # Second arg is the project
    
    def test_delete_service_not_found(self, client: TestClient):
        """Test deletion of non-existent service."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.delete.side_effect = HTTPException(status_code=404, detail="Service not found")
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Service not found"
    
    def test_service_invalid_uuid(self, client: TestClient):
        """Test endpoints with invalid UUID format."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises HTTPException for invalid UUID
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.get_one_with_versions_by_id.side_effect = HTTPException(
            status_code=400, detail="Invalid UUID format"
        )
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        invalid_id = "not-a-uuid"
        
        # Test get service with invalid UUID
        response = client.get(f"/api/v1/services/{invalid_id}/?project_id={self.project_id}")
        # This should return 400 due to invalid UUID format
        assert response.status_code == 400
    
    def test_service_endpoints_no_authentication(self, client: TestClient):
        """Test service endpoints without authentication."""
        # Don't override get_project_or_403, so it should fail with 401
        
        service_data = {
            "name": "Test Service",
            "meta": {
                "icon": "test",
                "category": "test",
                "description": "Test"
            }
        }
        
        response = client.get(f"/api/v1/services/?project_id={self.project_id}")
        assert response.status_code == 401
        
        response = client.get(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}")
        assert response.status_code == 401
        
        response = client.post(f"/api/v1/services/?project_id={self.project_id}", json=service_data)
        assert response.status_code == 401
        
        response = client.put(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}", json=service_data)
        assert response.status_code == 401
        
        response = client.delete(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}")
        assert response.status_code == 401
    
    def test_create_service_with_empty_meta_fields(self, client: TestClient):
        """Test service creation with explicitly empty meta fields."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.create.return_value = self.mock_service
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        service_data = {
            "name": "Service with Empty Meta",
            "meta": {
                "icon": None,
                "category": None,
                "description": None
            }
        }
        
        response = client.post(f"/api/v1/services/?project_id={self.project_id}", json=service_data)
        
        assert response.status_code == 201
        mock_repo.create.assert_called_once()
    
    def test_update_service_partial_meta(self, client: TestClient):
        """Test service update with partial meta information."""
        from utils.get_current_account import get_project_or_403
        from repositories.service_repository import get_service_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ServiceRepository)
        mock_repo.update.return_value = self.mock_service
        app.dependency_overrides[get_service_repository] = lambda: mock_repo
        
        service_data = {
            "name": "Partially Updated Service",
            "meta": {
                "icon": "new-icon",
                "category": "",  # Empty category
                "description": "Only icon and description updated"
            }
        }
        
        response = client.put(f"/api/v1/services/{self.service_id}/?project_id={self.project_id}", json=service_data)
        
        assert response.status_code == 200
        mock_repo.update.assert_called_once()