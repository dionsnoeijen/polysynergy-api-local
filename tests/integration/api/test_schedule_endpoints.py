import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from uuid import uuid4

from models import Schedule, Project, NodeSetup, NodeSetupVersion
from repositories.schedule_repository import ScheduleRepository
from services.schedule_publish_service import SchedulePublishService
from services.schedule_unpublish_service import ScheduleUnpublishService


@pytest.mark.integration
class TestScheduleEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.project_id = uuid4()
        self.schedule_id = uuid4()
        self.version_id = uuid4()
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.name = "Test Project"
        
        # Mock schedule
        self.mock_schedule = Mock(spec=Schedule)
        self.mock_schedule.id = self.schedule_id
        self.mock_schedule.project_id = self.project_id
        self.mock_schedule.name = "Test Schedule"
        self.mock_schedule.cron_expression = "0 9 * * *"
        self.mock_schedule.start_time = datetime.now(timezone.utc)
        self.mock_schedule.end_time = None
        self.mock_schedule.is_active = True
        
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
    
    def test_list_schedules_success(self, client: TestClient):
        """Test successful retrieval of schedules list."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        schedules = [self.mock_schedule]
        mock_repo.get_all_by_project.return_value = schedules
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/schedules/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        mock_repo.get_all_by_project.assert_called_once_with(self.mock_project)
    
    def test_list_schedules_empty(self, client: TestClient):
        """Test retrieval of empty schedules list."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository with empty results
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.get_all_by_project.return_value = []
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/schedules/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_create_schedule_success(self, client: TestClient):
        """Test successful schedule creation."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.create.return_value = self.mock_schedule
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        schedule_data = {
            "name": "Test Schedule",
            "cron_expression": "0 9 * * *",
            "start_time": "2024-01-01T09:00:00Z",
            "end_time": None,
            "is_active": True
        }
        
        response = client.post(f"/api/v1/schedules/?project_id={self.project_id}", json=schedule_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == str(self.schedule_id)
        mock_repo.create.assert_called_once()
    
    def test_create_schedule_validation_error(self, client: TestClient):
        """Test schedule creation with validation errors."""
        from utils.get_current_account import get_project_or_403
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Send invalid data (missing required fields)
        response = client.post(f"/api/v1/schedules/?project_id={self.project_id}", json={})
        
        assert response.status_code == 422
    
    def test_create_schedule_minimal_data(self, client: TestClient):
        """Test schedule creation with minimal required data."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.create.return_value = self.mock_schedule
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        schedule_data = {
            "name": "Minimal Schedule",
            "cron_expression": "0 0 * * *",
            "is_active": False
        }
        
        response = client.post(f"/api/v1/schedules/?project_id={self.project_id}", json=schedule_data)
        
        assert response.status_code == 201
        mock_repo.create.assert_called_once()
    
    def test_get_schedule_detail_success(self, client: TestClient):
        """Test successful retrieval of single schedule."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_schedule
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/schedules/{self.schedule_id}/?project_id={self.project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(self.schedule_id)
        mock_repo.get_one_with_versions_by_id.assert_called_once()
    
    def test_get_schedule_detail_not_found(self, client: TestClient):
        """Test retrieval of non-existent schedule."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.get_one_with_versions_by_id.side_effect = HTTPException(
            status_code=404, detail="Schedule not found"
        )
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        response = client.get(f"/api/v1/schedules/{self.schedule_id}/?project_id={self.project_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Schedule not found"
    
    def test_update_schedule_success(self, client: TestClient):
        """Test successful schedule update."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        updated_schedule = Mock(spec=Schedule)
        updated_schedule.id = self.schedule_id
        updated_schedule.name = "Updated Schedule"
        updated_schedule.cron_expression = "0 10 * * *"
        updated_schedule.start_time = datetime.now(timezone.utc)
        updated_schedule.end_time = None
        updated_schedule.is_active = False
        
        mock_repo.update.return_value = updated_schedule
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        schedule_data = {
            "name": "Updated Schedule",
            "cron_expression": "0 10 * * *",
            "is_active": False
        }
        
        response = client.patch(f"/api/v1/schedules/{self.schedule_id}/?project_id={self.project_id}", json=schedule_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Schedule"
        mock_repo.update.assert_called_once()
    
    def test_update_schedule_not_found(self, client: TestClient):
        """Test update of non-existent schedule."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.update.side_effect = HTTPException(status_code=404, detail="Schedule not found")
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        schedule_data = {
            "name": "Updated Schedule",
            "is_active": False
        }
        
        response = client.patch(f"/api/v1/schedules/{self.schedule_id}/?project_id={self.project_id}", json=schedule_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Schedule not found"
    
    def test_update_schedule_partial(self, client: TestClient):
        """Test partial update of schedule."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.update.return_value = self.mock_schedule
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        schedule_data = {"name": "Only Name Updated"}
        
        response = client.patch(f"/api/v1/schedules/{self.schedule_id}/?project_id={self.project_id}", json=schedule_data)
        
        assert response.status_code == 200
        mock_repo.update.assert_called_once()
    
    def test_delete_schedule_success(self, client: TestClient):
        """Test successful schedule deletion."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/schedules/{self.schedule_id}/?project_id={self.project_id}")
        
        assert response.status_code == 204
        # Verify delete was called
        args, kwargs = mock_repo.delete.call_args
        assert args[0] == self.schedule_id  # First arg is the UUID
        assert args[1] == self.mock_project   # Second arg is the project
    
    def test_delete_schedule_not_found(self, client: TestClient):
        """Test deletion of non-existent schedule."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository that raises 404
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.delete.side_effect = HTTPException(status_code=404, detail="Schedule not found")
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        response = client.delete(f"/api/v1/schedules/{self.schedule_id}/?project_id={self.project_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Schedule not found"
    
    def test_publish_schedule_success(self, client: TestClient):
        """Test successful schedule publishing."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from services.schedule_publish_service import get_schedule_publish_service
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_schedule
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        # Mock publish service
        mock_publish_service = Mock(spec=SchedulePublishService)
        app.dependency_overrides[get_schedule_publish_service] = lambda: mock_publish_service
        
        publish_data = {"stage": "production"}
        
        response = client.post(f"/api/v1/schedules/{self.schedule_id}/publish/?project_id={self.project_id}", json=publish_data)
        
        assert response.status_code == 202
        data = response.json()
        assert data["message"] == "Schedule successfully published"
        mock_publish_service.publish.assert_called_once_with(self.mock_schedule, "production")
    
    def test_publish_schedule_validation_error(self, client: TestClient):
        """Test schedule publishing with validation error."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from services.schedule_publish_service import get_schedule_publish_service
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_schedule
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        # Mock publish service that raises ValueError
        mock_publish_service = Mock(spec=SchedulePublishService)
        mock_publish_service.publish.side_effect = ValueError("Invalid stage")
        app.dependency_overrides[get_schedule_publish_service] = lambda: mock_publish_service
        
        publish_data = {"stage": "invalid"}
        
        response = client.post(f"/api/v1/schedules/{self.schedule_id}/publish/?project_id={self.project_id}", json=publish_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Invalid stage"
    
    def test_publish_schedule_unexpected_error(self, client: TestClient):
        """Test schedule publishing with unexpected error."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from services.schedule_publish_service import get_schedule_publish_service
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_schedule
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        # Mock publish service that raises unexpected error
        mock_publish_service = Mock(spec=SchedulePublishService)
        mock_publish_service.publish.side_effect = Exception("AWS Error")
        app.dependency_overrides[get_schedule_publish_service] = lambda: mock_publish_service
        
        publish_data = {"stage": "production"}
        
        response = client.post(f"/api/v1/schedules/{self.schedule_id}/publish/?project_id={self.project_id}", json=publish_data)
        
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Unexpected error during publish"
    
    def test_unpublish_schedule_success(self, client: TestClient):
        """Test successful schedule unpublishing."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from services.schedule_unpublish_service import get_schedule_unpublish_service
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_schedule
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        # Mock unpublish service
        mock_unpublish_service = Mock(spec=ScheduleUnpublishService)
        app.dependency_overrides[get_schedule_unpublish_service] = lambda: mock_unpublish_service
        
        unpublish_data = {"stage": "production"}
        
        response = client.post(f"/api/v1/schedules/{self.schedule_id}/unpublish/?project_id={self.project_id}", json=unpublish_data)
        
        assert response.status_code == 202
        data = response.json()
        assert data["message"] == "Schedule unpublished successfully"
        mock_unpublish_service.unpublish.assert_called_once_with(self.mock_schedule, "production")
    
    def test_unpublish_schedule_unexpected_error(self, client: TestClient):
        """Test schedule unpublishing with unexpected error."""
        from utils.get_current_account import get_project_or_403
        from repositories.schedule_repository import get_schedule_repository
        from services.schedule_unpublish_service import get_schedule_unpublish_service
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock repository
        mock_repo = Mock(spec=ScheduleRepository)
        mock_repo.get_one_with_versions_by_id.return_value = self.mock_schedule
        app.dependency_overrides[get_schedule_repository] = lambda: mock_repo
        
        # Mock unpublish service that raises error
        mock_unpublish_service = Mock(spec=ScheduleUnpublishService)
        mock_unpublish_service.unpublish.side_effect = Exception("AWS Error")
        app.dependency_overrides[get_schedule_unpublish_service] = lambda: mock_unpublish_service
        
        unpublish_data = {"stage": "production"}
        
        response = client.post(f"/api/v1/schedules/{self.schedule_id}/unpublish/?project_id={self.project_id}", json=unpublish_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Unexpected error during unpublish" in data["detail"]
    
    def test_schedule_invalid_uuid(self, client: TestClient):
        """Test endpoints with invalid UUID format."""
        from utils.get_current_account import get_project_or_403
        from main import app
        
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        invalid_id = "not-a-uuid"
        
        response = client.get(f"/api/v1/schedules/{invalid_id}/?project_id={self.project_id}")
        assert response.status_code == 422
        
        response = client.patch(f"/api/v1/schedules/{invalid_id}/?project_id={self.project_id}", json={"name": "Test"})
        assert response.status_code == 422
        
        response = client.delete(f"/api/v1/schedules/{invalid_id}/?project_id={self.project_id}")
        assert response.status_code == 422
        
        response = client.post(f"/api/v1/schedules/{invalid_id}/publish/?project_id={self.project_id}", json={"stage": "production"})
        assert response.status_code == 422
        
        response = client.post(f"/api/v1/schedules/{invalid_id}/unpublish/?project_id={self.project_id}", json={"stage": "production"})
        assert response.status_code == 422