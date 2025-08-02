import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from uuid import uuid4

from models import Route, Project, RouteSegment, NodeSetup, NodeSetupVersion
from models.route import Method
from models.route_segment import RouteSegmentType, VariableType
from repositories.route_repository import RouteRepository
from services.route_publish_service import RoutePublishService
from services.route_unpublish_service import RouteUnpublishService


@pytest.mark.integration
class TestRouteEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.project_id = uuid4()
        self.route_id = uuid4()
        self.version_id = uuid4()
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.name = "Test Project"
        
        # Mock route
        self.mock_route = Mock(spec=Route)
        self.mock_route.id = self.route_id
        self.mock_route.project_id = self.project_id
        self.mock_route.description = "Test Route"
        self.mock_route.method = Method.GET
        self.mock_route.created_at = datetime.now(timezone.utc)
        self.mock_route.updated_at = datetime.now(timezone.utc)
        self.mock_route.segments = []
        
        # Mock route segment
        self.mock_segment = Mock(spec=RouteSegment)
        self.mock_segment.id = uuid4()
        self.mock_segment.route_id = self.route_id
        self.mock_segment.segment_order = 1
        self.mock_segment.type = RouteSegmentType.STATIC
        self.mock_segment.name = "api"
        self.mock_segment.default_value = None
        self.mock_segment.variable_type = None
        
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
    
    def test_list_routes_success(self, client: TestClient):
        """Test successful retrieval of routes list."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=RouteRepository)
        routes = [self.mock_route]
        mock_repo.get_all_with_versions_by_project.return_value = routes
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/routes/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        mock_repo.get_all_with_versions_by_project.assert_called_once_with(self.mock_project)
    
    def test_list_routes_empty(self, client: TestClient):
        """Test retrieval of empty routes list."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository with empty results
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.get_all_with_versions_by_project.return_value = []
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/routes/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_create_route_success(self, client: TestClient):
        """Test successful route creation."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.create.return_value = self.mock_route
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        route_data = {
            "description": "Test Route",
            "method": "GET",
            "segments": [
                {
                    "segment_order": 1,
                    "type": "static",
                    "name": "api",
                    "default_value": None,
                    "variable_type": None
                }
            ]
        }
        
        response = client.post(f"/api/v1/routes/?project_id={self.project_id}", json=route_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == str(self.route_id)
        mock_repo.create.assert_called_once()
    
    def test_create_route_validation_error(self, client: TestClient):
        """Test route creation with validation errors."""
        from utils.get_current_account import get_project_or_403
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Send invalid data (missing required fields)
        response = client.post(f"/api/v1/routes/?project_id={self.project_id}", json={})
        
        assert response.status_code == 422
    
    def test_create_route_duplicate_error(self, client: TestClient):
        """Test route creation with duplicate route error."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises duplicate error
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.create.side_effect = HTTPException(
            status_code=400, 
            detail="Duplicate route with the same structure is not allowed."
        )
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        route_data = {
            "description": "Test Route",
            "method": "GET",
            "segments": [
                {
                    "segment_order": 1,
                    "type": "static",
                    "name": "api"
                }
            ]
        }
        
        response = client.post(f"/api/v1/routes/?project_id={self.project_id}", json=route_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Duplicate route" in data["detail"]
    
    def test_get_route_detail_success(self, client: TestClient):
        """Test successful retrieval of single route."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_route
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/routes/{self.route_id}/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(self.route_id)
        mock_repo.get_one_with_versions_by_id.assert_called_once()
    
    def test_get_route_detail_not_found(self, client: TestClient):
        """Test retrieval of non-existent route."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.get_one_with_versions_by_id.side_effect = HTTPException(
            status_code=404, detail="Route not found"
        )
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/routes/{self.route_id}/?project_id={self.project_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Route not found"
    
    def test_update_route_success(self, client: TestClient):
        """Test successful route update."""
        from repositories.route_repository import get_route_repository
        from main import app
        
        # Mock repository
        mock_repo = Mock(spec=RouteRepository)
        updated_route = Mock(spec=Route)
        updated_route.id = self.route_id
        updated_route.description = "Updated Route"
        updated_route.method = Method.POST
        updated_route.created_at = datetime.now(timezone.utc)
        updated_route.updated_at = datetime.now(timezone.utc)
        updated_route.segments = []
        
        mock_repo.update.return_value = updated_route
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        route_data = {
            "description": "Updated Route",
            "method": "POST",
            "segments": []
        }
        
        response = client.patch(f"/api/v1/routes/{self.route_id}/versions/{self.version_id}/", json=route_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated Route"
        mock_repo.update.assert_called_once()
    
    def test_update_route_not_found(self, client: TestClient):
        """Test update of non-existent route."""
        from repositories.route_repository import get_route_repository
        from main import app
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.update.side_effect = HTTPException(status_code=404, detail="Route not found")
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        route_data = {
            "description": "Updated Route",
            "method": "POST",
            "segments": []
        }
        
        response = client.patch(f"/api/v1/routes/{self.route_id}/versions/{self.version_id}/", json=route_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Route not found"
    
    def test_delete_route_success(self, client: TestClient):
        """Test successful route deletion."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=RouteRepository)
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/routes/{self.route_id}/?project_id={self.project_id}")
        
        assert response.status_code == 204
        # Verify delete was called
        args, kwargs = mock_repo.delete.call_args
        assert args[0] == self.route_id  # First arg is the UUID
        assert args[1] == self.mock_project   # Second arg is the project
    
    def test_delete_route_not_found(self, client: TestClient):
        """Test deletion of non-existent route."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.delete.side_effect = HTTPException(status_code=404, detail="Route not found")
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/routes/{self.route_id}/?project_id={self.project_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Route not found"
    
    def test_publish_route_success(self, client: TestClient):
        """Test successful route publishing."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from services.route_publish_service import get_route_publish_service
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_route
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        # Mock publish service
        mock_publish_service = Mock(spec=RoutePublishService)
        app.dependency_overrides[get_route_publish_service] = lambda: mock_publish_service
        
        publish_data = {"stage": "production"}
        
        response = client.post(f"/api/v1/routes/{self.route_id}/publish/?project_id={self.project_id}", json=publish_data)
        
        assert response.status_code == 202
        mock_publish_service.sync_lambda.assert_called_once_with(self.mock_route, "production")
    
    def test_publish_route_validation_error(self, client: TestClient):
        """Test route publishing with validation error."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from services.route_publish_service import get_route_publish_service
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_route
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        # Mock publish service that raises ValueError
        mock_publish_service = Mock(spec=RoutePublishService)
        mock_publish_service.sync_lambda.side_effect = ValueError("Invalid stage")
        app.dependency_overrides[get_route_publish_service] = lambda: mock_publish_service
        
        publish_data = {"stage": "invalid"}
        
        response = client.post(f"/api/v1/routes/{self.route_id}/publish/?project_id={self.project_id}", json=publish_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Invalid stage"
    
    def test_publish_route_unexpected_error(self, client: TestClient):
        """Test route publishing with unexpected error."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from services.route_publish_service import get_route_publish_service
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_route
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        # Mock publish service that raises unexpected error
        mock_publish_service = Mock(spec=RoutePublishService)
        mock_publish_service.sync_lambda.side_effect = Exception("AWS Error")
        app.dependency_overrides[get_route_publish_service] = lambda: mock_publish_service
        
        publish_data = {"stage": "production"}
        
        response = client.post(f"/api/v1/routes/{self.route_id}/publish/?project_id={self.project_id}", json=publish_data)
        
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Unexpected error during publish"
    
    def test_unpublish_route_success(self, client: TestClient):
        """Test successful route unpublishing."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from services.route_unpublish_service import get_route_unpublish_service
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_route
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        # Mock unpublish service
        mock_unpublish_service = Mock(spec=RouteUnpublishService)
        app.dependency_overrides[get_route_unpublish_service] = lambda: mock_unpublish_service
        
        unpublish_data = {"stage": "production"}
        
        response = client.post(f"/api/v1/routes/{self.route_id}/unpublish/?project_id={self.project_id}", json=unpublish_data)
        
        assert response.status_code == 202
        mock_unpublish_service.unpublish.assert_called_once_with(self.mock_route, "production")
    
    def test_unpublish_route_unexpected_error(self, client: TestClient):
        """Test route unpublishing with unexpected error."""
        from utils.get_current_account import get_project_or_403
        from repositories.route_repository import get_route_repository
        from services.route_unpublish_service import get_route_unpublish_service
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=RouteRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_route
        app.dependency_overrides[get_route_repository] = lambda: mock_repo
        
        # Mock unpublish service that raises error
        mock_unpublish_service = Mock(spec=RouteUnpublishService)
        mock_unpublish_service.unpublish.side_effect = Exception("AWS Error")
        app.dependency_overrides[get_route_unpublish_service] = lambda: mock_unpublish_service
        
        unpublish_data = {"stage": "production"}
        
        response = client.post(f"/api/v1/routes/{self.route_id}/unpublish/?project_id={self.project_id}", json=unpublish_data)
        
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Unexpected error during unpublish"
    
    # Note: Authentication tests are handled by the general authentication middleware
    # and don't require specific testing here as they would require database connection
    # which is complex in integration tests
    
    def test_route_invalid_uuid(self, client: TestClient):
        """Test endpoints with invalid UUID format."""
        from utils.get_current_account import get_project_or_403
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        invalid_id = "not-a-uuid"
        
        response = client.get(f"/api/v1/routes/{invalid_id}/?project_id={self.project_id}")
        assert response.status_code == 422
        
        response = client.patch(f"/api/v1/routes/{invalid_id}/versions/{self.version_id}/", json={"description": "Test", "method": "GET", "segments": []})
        assert response.status_code == 422
        
        response = client.delete(f"/api/v1/routes/{invalid_id}/?project_id={self.project_id}")
        assert response.status_code == 422
        
        response = client.post(f"/api/v1/routes/{invalid_id}/publish/?project_id={self.project_id}", json={"stage": "production"})
        assert response.status_code == 422
        
        response = client.post(f"/api/v1/routes/{invalid_id}/unpublish/?project_id={self.project_id}", json={"stage": "production"})
        assert response.status_code == 422