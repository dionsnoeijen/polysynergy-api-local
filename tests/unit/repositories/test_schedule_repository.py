import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi import HTTPException

from repositories.schedule_repository import ScheduleRepository
from models import Schedule, NodeSetup, NodeSetupVersion, Project
from schemas.schedule import ScheduleCreateIn, ScheduleUpdateIn


@pytest.mark.unit
class TestScheduleRepository:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.mock_db = Mock()
        self.repository = ScheduleRepository(self.mock_db)
        
        self.project_id = uuid4()
        self.schedule_id = uuid4()
        self.node_setup_id = uuid4()
        self.version_id = uuid4()
        
        # Mock project
        self.mock_project = Mock()
        self.mock_project.id = self.project_id
        
        # Mock schedule
        self.mock_schedule = Mock()
        self.mock_schedule.id = self.schedule_id
        self.mock_schedule.project_id = self.project_id
        self.mock_schedule.name = "Test Schedule"
        self.mock_schedule.cron_expression = "0 9 * * *"
        self.mock_schedule.start_time = datetime.now(timezone.utc)
        self.mock_schedule.end_time = None
        self.mock_schedule.is_active = True
        
        # Mock node setup
        self.mock_node_setup = Mock()
        self.mock_node_setup.id = self.node_setup_id
        self.mock_node_setup.content_type = "schedule"
        self.mock_node_setup.object_id = self.schedule_id
        
        # Mock node setup version
        self.mock_version = Mock()
        self.mock_version.id = self.version_id
        self.mock_version.node_setup_id = self.node_setup_id
        self.mock_version.version_number = 1
        self.mock_version.content = {}

    def test_get_all_by_project(self):
        """Test retrieval of all schedules by project."""
        schedules = [self.mock_schedule]
        self.mock_db.query.return_value.filter.return_value.all.return_value = schedules
        
        result = self.repository.get_all_by_project(self.mock_project)
        
        assert result == schedules
        self.mock_db.query.assert_called_once_with(Schedule)

    def test_get_one_with_versions_by_id_found(self):
        """Test successful retrieval of single schedule with versions."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_schedule
        
        # Mock the node setup query call
        mock_filter_by = Mock()
        mock_filter_by.first.return_value = self.mock_node_setup
        self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
        
        result = self.repository.get_one_with_versions_by_id(self.schedule_id, self.mock_project)
        
        assert result == self.mock_schedule
        assert result.node_setup == self.mock_node_setup

    def test_get_one_with_versions_by_id_not_found(self):
        """Test schedule not found raises 404."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.get_one_with_versions_by_id(self.schedule_id, self.mock_project)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Schedule not found"

    def test_get_by_id_or_404_found(self):
        """Test successful get_by_id_or_404."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_schedule
        
        result = self.repository.get_by_id_or_404(self.schedule_id)
        
        assert result == self.mock_schedule

    def test_get_by_id_or_404_not_found(self):
        """Test get_by_id_or_404 raises 404 when not found."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.get_by_id_or_404(self.schedule_id)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Schedule not found"

    def test_create_success(self):
        """Test successful schedule creation."""
        schedule_data = ScheduleCreateIn(
            name="Test Schedule",
            cron_expression="0 9 * * *",
            start_time=datetime.now(timezone.utc),
            end_time=None,
            is_active=True
        )
        
        # Mock successful creation
        with patch('repositories.schedule_repository.Schedule') as mock_schedule_class, \
             patch('repositories.schedule_repository.NodeSetup') as mock_node_setup_class, \
             patch('repositories.schedule_repository.NodeSetupVersion') as mock_version_class:
            
            mock_schedule_class.return_value = self.mock_schedule
            mock_node_setup_class.return_value = self.mock_node_setup
            mock_version_class.return_value = self.mock_version
            
            result = self.repository.create(schedule_data, self.mock_project)
            
            assert result == self.mock_schedule
            assert result.node_setup == self.mock_node_setup
            self.mock_db.add.assert_called()
            self.mock_db.flush.assert_called()
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(self.mock_schedule)

    def test_create_with_optional_fields(self):
        """Test schedule creation with minimal required fields."""
        schedule_data = ScheduleCreateIn(
            name="Minimal Schedule",
            cron_expression="0 0 * * *",
            is_active=False
        )
        
        with patch('repositories.schedule_repository.Schedule') as mock_schedule_class, \
             patch('repositories.schedule_repository.NodeSetup') as mock_node_setup_class, \
             patch('repositories.schedule_repository.NodeSetupVersion') as mock_version_class:
            
            mock_schedule_class.return_value = self.mock_schedule
            mock_node_setup_class.return_value = self.mock_node_setup
            mock_version_class.return_value = self.mock_version
            
            result = self.repository.create(schedule_data, self.mock_project)
            
            assert result == self.mock_schedule
            self.mock_db.commit.assert_called_once()

    def test_update_success(self):
        """Test successful schedule update."""
        schedule_data = ScheduleUpdateIn(
            name="Updated Schedule",
            cron_expression="0 10 * * *",
            is_active=False
        )
        
        # Mock get_one_with_versions_by_id to return schedule
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_schedule):
            # Mock node setup query
            mock_filter_by = Mock()
            mock_filter_by.first.return_value = self.mock_node_setup
            self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
            
            result = self.repository.update(self.schedule_id, schedule_data, self.mock_project)
            
            assert result == self.mock_schedule
            assert result.node_setup == self.mock_node_setup
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(self.mock_schedule)

    def test_update_partial_fields(self):
        """Test partial update of schedule fields."""
        schedule_data = ScheduleUpdateIn(name="Only Name Updated")
        
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_schedule):
            mock_filter_by = Mock()
            mock_filter_by.first.return_value = self.mock_node_setup
            self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
            
            result = self.repository.update(self.schedule_id, schedule_data, self.mock_project)
            
            assert result == self.mock_schedule
            self.mock_db.commit.assert_called_once()

    def test_update_schedule_not_found(self):
        """Test update fails when schedule not found."""
        schedule_data = ScheduleUpdateIn(name="Updated Schedule")
        
        with patch.object(self.repository, 'get_one_with_versions_by_id') as mock_get:
            mock_get.side_effect = HTTPException(status_code=404, detail="Schedule not found")
            
            with pytest.raises(HTTPException) as exc_info:
                self.repository.update(self.schedule_id, schedule_data, self.mock_project)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Schedule not found"

    def test_delete_success(self):
        """Test successful schedule deletion."""
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_schedule):
            self.repository.delete(self.schedule_id, self.mock_project)
            
            self.mock_db.delete.assert_called_once_with(self.mock_schedule)
            self.mock_db.commit.assert_called_once()

    def test_delete_schedule_not_found(self):
        """Test delete fails when schedule not found."""
        with patch.object(self.repository, 'get_one_with_versions_by_id') as mock_get:
            mock_get.side_effect = HTTPException(status_code=404, detail="Schedule not found")
            
            with pytest.raises(HTTPException) as exc_info:
                self.repository.delete(self.schedule_id, self.mock_project)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Schedule not found"

    def test_create_with_end_time(self):
        """Test schedule creation with end time."""
        end_time = datetime.now(timezone.utc)
        schedule_data = ScheduleCreateIn(
            name="Schedule with End Time",
            cron_expression="0 9 * * *",
            start_time=datetime.now(timezone.utc),
            end_time=end_time,
            is_active=True
        )
        
        with patch('repositories.schedule_repository.Schedule') as mock_schedule_class, \
             patch('repositories.schedule_repository.NodeSetup') as mock_node_setup_class, \
             patch('repositories.schedule_repository.NodeSetupVersion') as mock_version_class:
            
            mock_schedule_class.return_value = self.mock_schedule
            mock_node_setup_class.return_value = self.mock_node_setup
            mock_version_class.return_value = self.mock_version
            
            result = self.repository.create(schedule_data, self.mock_project)
            
            assert result == self.mock_schedule
            self.mock_db.commit.assert_called_once()

    def test_update_with_datetime_fields(self):
        """Test update with datetime fields."""
        new_start_time = datetime.now(timezone.utc)
        new_end_time = datetime.now(timezone.utc)
        
        schedule_data = ScheduleUpdateIn(
            start_time=new_start_time,
            end_time=new_end_time
        )
        
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_schedule):
            mock_filter_by = Mock()
            mock_filter_by.first.return_value = self.mock_node_setup
            self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
            
            result = self.repository.update(self.schedule_id, schedule_data, self.mock_project)
            
            assert result == self.mock_schedule
            self.mock_db.commit.assert_called_once()

    def test_get_one_with_versions_no_node_setup(self):
        """Test retrieval when no node setup exists."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_schedule
        
        # Mock no node setup found
        mock_filter_by = Mock()
        mock_filter_by.first.return_value = None
        self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
        
        result = self.repository.get_one_with_versions_by_id(self.schedule_id, self.mock_project)
        
        assert result == self.mock_schedule
        assert result.node_setup is None