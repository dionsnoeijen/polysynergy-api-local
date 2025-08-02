import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from uuid import uuid4

from models import (
    Project, Route, Schedule, Stage, NodeSetup, NodeSetupVersion,
    NodeSetupVersionStage, RouteSegment
)
from repositories.publish_matrix_repository import PublishMatrixRepository


@pytest.mark.integration
class TestPublishMatrixEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.project_id = str(uuid4())
        self.route_id = str(uuid4())
        self.schedule_id = str(uuid4())
        self.stage_id = str(uuid4())
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.name = "Test Project"
        
        # Mock route
        self.mock_route = Mock(spec=Route)
        self.mock_route.id = self.route_id
        self.mock_route.__str__ = Mock(return_value="GET /api/test")
        
        # Mock schedule
        self.mock_schedule = Mock(spec=Schedule)
        self.mock_schedule.id = self.schedule_id
        self.mock_schedule.name = "Test Schedule"
        self.mock_schedule.cron_expression = "0 0 * * *"
        
        # Mock stage
        self.mock_stage = Mock(spec=Stage)
        self.mock_stage.id = self.stage_id
        self.mock_stage.name = "production"
        self.mock_stage.is_production = True
        
        # Mock route segment
        self.mock_segment = Mock(spec=RouteSegment)
        self.mock_segment.id = str(uuid4())
        self.mock_segment.segment_order = 1
        self.mock_segment.type = "static"
        self.mock_segment.name = "api"
        self.mock_segment.default_value = None
        self.mock_segment.variable_type = None
    
    def teardown_method(self):
        """Clean up after each test."""
        from main import app
        app.dependency_overrides.clear()
    
    def test_get_publish_matrix_success(self, client: TestClient):
        """Test successful retrieval of publish matrix."""
        from utils.get_current_account import get_project_or_403
        from repositories.publish_matrix_repository import get_publish_matrix_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=PublishMatrixRepository)
        mock_matrix = Mock()
        mock_matrix.routes = [{
            "id": self.route_id,
            "name": "GET /api/test",
            "segments": [{
                "id": str(self.mock_segment.id),
                "segment_order": 1,
                "type": "static",
                "name": "api",
                "default_value": None,
                "variable_type": None
            }],
            "published_stages": ["production"],
            "stages_can_update": []
        }]
        mock_matrix.schedules = [{
            "id": self.schedule_id,
            "name": "Test Schedule",
            "cron_expression": "0 0 * * *",
            "published_stages": ["production"],
            "stages_can_update": []
        }]
        mock_matrix.stages = [{
            "id": self.stage_id,
            "name": "production",
            "is_production": True
        }]
        
        mock_repo.get_publish_matrix.return_value = mock_matrix
        app.dependency_overrides[get_publish_matrix_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/publish-matrix/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "routes" in data
        assert "schedules" in data
        assert "stages" in data
        
        assert len(data["routes"]) == 1
        assert data["routes"][0]["id"] == self.route_id
        assert data["routes"][0]["name"] == "GET /api/test"
        
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["id"] == self.schedule_id
        assert data["schedules"][0]["name"] == "Test Schedule"
        
        assert len(data["stages"]) == 1
        assert data["stages"][0]["id"] == self.stage_id
        assert data["stages"][0]["name"] == "production"
    
    def test_get_publish_matrix_empty_project(self, client: TestClient):
        """Test publish matrix for project with no content."""
        from utils.get_current_account import get_project_or_403
        from repositories.publish_matrix_repository import get_publish_matrix_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository with empty results
        mock_repo = Mock(spec=PublishMatrixRepository)
        mock_matrix = Mock()
        mock_matrix.routes = []
        mock_matrix.schedules = []
        mock_matrix.stages = []
        
        mock_repo.get_publish_matrix.return_value = mock_matrix
        app.dependency_overrides[get_publish_matrix_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/publish-matrix/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["routes"] == []
        assert data["schedules"] == []
        assert data["stages"] == []
    
    def test_get_publish_matrix_repository_error(self, client: TestClient):
        """Test publish matrix when repository raises an error."""
        from utils.get_current_account import get_project_or_403
        from repositories.publish_matrix_repository import get_publish_matrix_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises an exception
        mock_repo = Mock(spec=PublishMatrixRepository)
        mock_repo.get_publish_matrix.side_effect = Exception("Database error")
        app.dependency_overrides[get_publish_matrix_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/publish-matrix/?project_id={self.project_id}")
        
        assert response.status_code == 500
        data = response.json()
        assert "Error in publish matrix" in data["detail"]
    
    def test_get_publish_matrix_no_authentication(self, client: TestClient):
        """Test publish matrix endpoint without authentication."""
        response = client.get(f"/api/v1/publish-matrix/?project_id={self.project_id}")
        
        assert response.status_code == 401
    
    def test_get_publish_matrix_project_not_found(self, client: TestClient):
        """Test publish matrix when project is not found or access denied."""
        from utils.get_current_account import get_project_or_403
        from main import app
        
        # Mock get_project_or_403 to raise HTTPException
        def mock_get_project():
            raise HTTPException(status_code=403, detail="Project not found or access denied")
        
        app.dependency_overrides[get_project_or_403] = mock_get_project
        
        response = client.get(f"/api/v1/publish-matrix/?project_id={self.project_id}")
        
        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Project not found or access denied"
    
    def test_get_publish_matrix_invalid_project_id(self, client: TestClient):
        """Test publish matrix with invalid project ID format."""
        from utils.get_current_account import get_project_or_403
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        invalid_id = "not-a-uuid"
        
        response = client.get(f"/api/v1/publish-matrix/?project_id={invalid_id}")
        
        # The validation should happen at the FastAPI level, but might be 500 due to UUID parsing
        assert response.status_code in [422, 500]
    
    def test_get_publish_matrix_with_update_needed(self, client: TestClient):
        """Test publish matrix showing routes/schedules that need updates."""
        from utils.get_current_account import get_project_or_403
        from repositories.publish_matrix_repository import get_publish_matrix_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository with updates needed
        mock_repo = Mock(spec=PublishMatrixRepository)
        mock_matrix = Mock()
        mock_matrix.routes = [{
            "id": self.route_id,
            "name": "GET /api/test",
            "segments": [],
            "published_stages": ["production"],
            "stages_can_update": ["production"]  # Indicates update needed
        }]
        mock_matrix.schedules = [{
            "id": self.schedule_id,
            "name": "Test Schedule",
            "cron_expression": "0 0 * * *",
            "published_stages": ["production"],
            "stages_can_update": ["production"]  # Indicates update needed
        }]
        mock_matrix.stages = [{
            "id": self.stage_id,
            "name": "production",
            "is_production": True
        }]
        
        mock_repo.get_publish_matrix.return_value = mock_matrix
        app.dependency_overrides[get_publish_matrix_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/publish-matrix/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify that stages_can_update indicates updates are needed
        assert data["routes"][0]["stages_can_update"] == ["production"]
        assert data["schedules"][0]["stages_can_update"] == ["production"]
    
    def test_get_publish_matrix_multiple_stages(self, client: TestClient):
        """Test publish matrix with multiple stages."""
        from utils.get_current_account import get_project_or_403
        from repositories.publish_matrix_repository import get_publish_matrix_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository with multiple stages
        mock_repo = Mock(spec=PublishMatrixRepository)
        mock_matrix = Mock()
        mock_matrix.routes = []
        mock_matrix.schedules = []
        mock_matrix.stages = [
            {
                "id": self.stage_id,
                "name": "development", 
                "is_production": False
            },
            {
                "id": str(uuid4()),
                "name": "production",
                "is_production": True
            }
        ]
        
        mock_repo.get_publish_matrix.return_value = mock_matrix
        app.dependency_overrides[get_publish_matrix_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/publish-matrix/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["stages"]) == 2
        stage_names = [stage["name"] for stage in data["stages"]]
        assert "development" in stage_names
        assert "production" in stage_names
    
    def test_get_publish_matrix_complex_route_segments(self, client: TestClient):
        """Test publish matrix with complex route segments."""
        from utils.get_current_account import get_project_or_403
        from repositories.publish_matrix_repository import get_publish_matrix_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository with complex route segments
        mock_repo = Mock(spec=PublishMatrixRepository)
        mock_matrix = Mock()
        mock_matrix.routes = [{
            "id": self.route_id,
            "name": "GET /api/users/{id}",
            "segments": [
                {
                    "id": str(uuid4()),
                    "segment_order": 1,
                    "type": "static",
                    "name": "api",
                    "default_value": None,
                    "variable_type": None
                },
                {
                    "id": str(uuid4()),
                    "segment_order": 2,
                    "type": "static",
                    "name": "users",
                    "default_value": None,
                    "variable_type": None
                },
                {
                    "id": str(uuid4()),
                    "segment_order": 3,
                    "type": "variable",
                    "name": "id",
                    "default_value": "1",
                    "variable_type": "integer"
                }
            ],
            "published_stages": ["production"],
            "stages_can_update": []
        }]
        mock_matrix.schedules = []
        mock_matrix.stages = []
        
        mock_repo.get_publish_matrix.return_value = mock_matrix
        app.dependency_overrides[get_publish_matrix_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/publish-matrix/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        route = data["routes"][0]
        assert len(route["segments"]) == 3
        
        # Check static segments
        static_segments = [s for s in route["segments"] if s["type"] == "static"]
        assert len(static_segments) == 2
        
        # Check variable segment
        variable_segments = [s for s in route["segments"] if s["type"] == "variable"]
        assert len(variable_segments) == 1
        assert variable_segments[0]["name"] == "id"
        assert variable_segments[0]["default_value"] == "1"
        assert variable_segments[0]["variable_type"] == "integer"