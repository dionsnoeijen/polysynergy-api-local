import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, PropertyMock
from uuid import uuid4

from repositories.publish_matrix_repository import PublishMatrixRepository
from models import (
    Project, Route, Schedule, Stage, NodeSetup, NodeSetupVersion,
    NodeSetupVersionStage, RouteSegment
)
from schemas.publish_matrix import PublishMatrixOut


@pytest.mark.unit
class TestPublishMatrixRepository:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.mock_session = Mock()
        self.repository = PublishMatrixRepository(self.mock_session)
        
        self.project_id = str(uuid4())
        self.route_id = str(uuid4())
        self.schedule_id = str(uuid4())
        self.stage_id = str(uuid4())
        self.node_setup_id = str(uuid4())
        
        # Mock project
        self.mock_project = Mock()
        self.mock_project.id = self.project_id
        
        # Mock route
        self.mock_route = Mock()
        self.mock_route.id = self.route_id
        self.mock_route.__str__ = Mock(return_value="GET /api/test")
        
        # Mock schedule  
        self.mock_schedule = Mock()
        self.mock_schedule.id = self.schedule_id
        self.mock_schedule.name = "Test Schedule"
        self.mock_schedule.cron_expression = "0 0 * * *"
        
        # Mock stage
        self.mock_stage = Mock()
        self.mock_stage.id = self.stage_id
        self.mock_stage.name = "production"
        self.mock_stage.is_production = True
        self.mock_stage.order = 1
        
        # Mock node setup
        self.mock_node_setup = Mock()
        self.mock_node_setup.id = self.node_setup_id
        
        # Mock node setup version
        self.mock_version = Mock()
        self.mock_version.executable_hash = "abc123"
        self.mock_version.created_at = datetime.now(timezone.utc)
        
        # Mock stage link
        self.mock_stage_link = Mock()
        self.mock_stage_link.stage = self.mock_stage
        self.mock_stage_link.executable_hash = "abc123"
        
        # Mock route segment
        segment_id = str(uuid4())
        self.mock_segment = Mock()
        type(self.mock_segment).id = PropertyMock(return_value=segment_id)
        type(self.mock_segment).segment_order = PropertyMock(return_value=1)
        type(self.mock_segment).type = PropertyMock(return_value="static")
        type(self.mock_segment).name = PropertyMock(return_value="api")
        type(self.mock_segment).default_value = PropertyMock(return_value=None)
        type(self.mock_segment).variable_type = PropertyMock(return_value=None)

    def test_get_publish_matrix_success(self):
        """Test successful retrieval of complete publish matrix."""
        # Mock empty results for simplicity
        empty_scalars = Mock()
        empty_scalars.all.return_value = []
        self.mock_session.scalars.return_value = empty_scalars
        
        result = self.repository.get_publish_matrix(self.mock_project)
        
        assert isinstance(result, PublishMatrixOut)
        assert result.routes == []
        assert result.schedules == []
        assert result.stages == []

    def test_get_routes_by_project(self):
        """Test retrieval of routes by project."""
        mock_scalars = Mock()
        mock_scalars.all.return_value = [self.mock_route]
        self.mock_session.scalars.return_value = mock_scalars
        
        result = self.repository._get_routes_by_project(self.mock_project)
        
        assert result == [self.mock_route]
        self.mock_session.scalars.assert_called_once()

    def test_get_schedules_by_project(self):
        """Test retrieval of schedules by project."""
        mock_scalars = Mock()
        mock_scalars.all.return_value = [self.mock_schedule]
        self.mock_session.scalars.return_value = mock_scalars
        
        result = self.repository._get_schedules_by_project(self.mock_project)
        
        assert result == [self.mock_schedule]
        self.mock_session.scalars.assert_called_once()

    def test_get_stages_by_project(self):
        """Test retrieval of stages by project."""
        mock_scalars = Mock()
        mock_scalars.all.return_value = [self.mock_stage]
        self.mock_session.scalars.return_value = mock_scalars
        
        result = self.repository._get_stages_by_project(self.mock_project)
        
        assert len(result) == 1
        assert result[0].id == self.stage_id
        assert result[0].name == "production"
        assert result[0].is_production is True

    def test_get_route_publish_status_success(self):
        """Test successful route publish status retrieval."""
        # Mock node setup and version
        self.mock_session.scalar.side_effect = [
            self.mock_node_setup,  # Node setup
            self.mock_version       # Latest version
        ]
        
        # Mock stage links
        mock_stage_links = Mock()
        mock_stage_links.all.return_value = [self.mock_stage_link]
        
        mock_segments = Mock()
        mock_segments.all.return_value = [self.mock_segment]
        
        self.mock_session.scalars.side_effect = [
            mock_stage_links,  # Stage links
            mock_segments      # Segments
        ]
        
        result = self.repository._get_route_publish_status(self.mock_route)
        
        assert result is not None
        assert result.id == self.route_id
        assert result.name == "GET /api/test"
        assert len(result.segments) == 1
        assert result.published_stages == ["production"]
        assert result.stages_can_update == []

    def test_get_route_publish_status_no_node_setup(self):
        """Test route publish status when no node setup exists."""
        self.mock_session.scalar.return_value = None
        
        result = self.repository._get_route_publish_status(self.mock_route)
        
        assert result is None

    def test_get_route_publish_status_with_updates_needed(self):
        """Test route publish status when updates are needed."""
        # Mock different hashes to indicate update needed
        self.mock_stage_link.executable_hash = "old123"
        
        self.mock_session.scalar.side_effect = [
            self.mock_node_setup,  # Node setup
            self.mock_version       # Latest version (hash="abc123")
        ]
        
        mock_stage_links = Mock()
        mock_stage_links.all.return_value = [self.mock_stage_link]
        
        mock_segments = Mock()
        mock_segments.all.return_value = [self.mock_segment]
        
        self.mock_session.scalars.side_effect = [
            mock_stage_links,  # Stage links
            mock_segments      # Segments
        ]
        
        result = self.repository._get_route_publish_status(self.mock_route)
        
        assert result is not None
        assert result.published_stages == ["production"]
        assert result.stages_can_update == ["production"]

    def test_get_schedule_publish_status_success(self):
        """Test successful schedule publish status retrieval."""
        self.mock_session.scalar.side_effect = [
            self.mock_node_setup,  # Node setup
            self.mock_version       # Latest version
        ]
        
        mock_stage_links = Mock()
        mock_stage_links.all.return_value = [self.mock_stage_link]
        self.mock_session.scalars.return_value = mock_stage_links
        
        result = self.repository._get_schedule_publish_status(self.mock_schedule)
        
        assert result is not None
        assert result.id == self.schedule_id
        assert result.name == "Test Schedule"
        assert result.cron_expression == "0 0 * * *"
        assert result.published_stages == ["production"]
        assert result.stages_can_update == []

    def test_get_schedule_publish_status_no_node_setup(self):
        """Test schedule publish status when no node setup exists."""
        self.mock_session.scalar.return_value = None
        
        result = self.repository._get_schedule_publish_status(self.mock_schedule)
        
        assert result is None

    def test_get_route_segments(self):
        """Test retrieval of route segments."""
        mock_scalars = Mock()
        mock_scalars.all.return_value = [self.mock_segment]
        self.mock_session.scalars.return_value = mock_scalars
        
        result = self.repository._get_route_segments(self.mock_route)
        
        assert len(result) == 1
        segment = result[0]
        assert segment.id == str(self.mock_segment.id)
        assert segment.segment_order == 1
        assert segment.type == "static"
        assert segment.name == "api"
        assert segment.default_value is None
        assert segment.variable_type is None

    def test_get_publish_matrix_empty_project(self):
        """Test publish matrix for project with no routes, schedules, or stages."""
        # Mock empty results
        empty_scalars = Mock()
        empty_scalars.all.return_value = []
        self.mock_session.scalars.return_value = empty_scalars
        
        result = self.repository.get_publish_matrix(self.mock_project)
        
        assert isinstance(result, PublishMatrixOut)
        assert len(result.routes) == 0
        assert len(result.schedules) == 0
        assert len(result.stages) == 0

    def test_get_publish_matrix_with_routes_without_node_setup(self):
        """Test publish matrix when routes exist but have no node setup."""
        # Mock routes exist but node setup returns None
        mock_routes_scalars = Mock()
        mock_routes_scalars.all.return_value = [self.mock_route]
        
        empty_scalars = Mock()
        empty_scalars.all.return_value = []
        
        self.mock_session.scalars.side_effect = [
            mock_routes_scalars,  # Routes query
            empty_scalars,        # Schedules query
            empty_scalars,        # Stages query
        ]
        
        # Node setup not found
        self.mock_session.scalar.return_value = None
        
        result = self.repository.get_publish_matrix(self.mock_project)
        
        assert isinstance(result, PublishMatrixOut)
        assert len(result.routes) == 0  # Route filtered out due to no node setup
        assert len(result.schedules) == 0
        assert len(result.stages) == 0