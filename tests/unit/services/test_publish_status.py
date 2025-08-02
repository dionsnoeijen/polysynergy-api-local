import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from services.publish_status import (
    get_route_publish_status,
    get_schedule_publish_status,
    get_stage_data
)
from models import Route, Schedule, Stage, NodeSetup, NodeSetupVersion, NodeSetupVersionStage, RouteSegment
from schemas.publish_matrix import RoutePublishStatusOut, SchedulePublishStatusOut, StageOut, SegmentOut


@pytest.mark.unit
class TestPublishStatus:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.route_id = uuid4()
        self.schedule_id = uuid4()
        self.project_id = uuid4()
        self.node_setup_id = uuid4()
        self.stage_id = uuid4()
        self.version_id = uuid4()
        
        # Mock route
        self.mock_route = Mock(spec=Route)
        self.mock_route.id = self.route_id
        self.mock_route.__str__ = Mock(return_value="test-route")
        
        # Mock schedule
        self.mock_schedule = Mock(spec=Schedule)
        self.mock_schedule.id = self.schedule_id
        self.mock_schedule.name = "test-schedule"
        self.mock_schedule.cron_expression = "0 0 * * *"
        
        # Mock session
        self.mock_session = Mock()

    def test_get_route_publish_status_no_node_setup(self):
        """Test get_route_publish_status when no node setup exists."""
        # Mock session.scalar to return None for NodeSetup
        self.mock_session.scalar.return_value = None
        
        result = get_route_publish_status(self.mock_route, self.mock_session)
        
        assert result is None
        # Verify the correct query was made
        self.mock_session.scalar.assert_called_once()

    def test_get_route_publish_status_no_versions(self):
        """Test get_route_publish_status when node setup exists but no versions."""
        # Mock node setup exists
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = self.node_setup_id
        
        # Mock session calls
        def session_scalar_side_effect(*args, **kwargs):
            # First call returns NodeSetup, second call returns None for NodeSetupVersion
            if not hasattr(session_scalar_side_effect, 'call_count'):
                session_scalar_side_effect.call_count = 0
            session_scalar_side_effect.call_count += 1
            
            if session_scalar_side_effect.call_count == 1:
                return mock_node_setup
            elif session_scalar_side_effect.call_count == 2:
                return None
        
        self.mock_session.scalar.side_effect = session_scalar_side_effect
        
        # Mock empty stage links and segments
        mock_execute_result = Mock()
        mock_execute_result.scalars.return_value.all.return_value = []
        self.mock_session.execute.return_value = mock_execute_result
        
        result = get_route_publish_status(self.mock_route, self.mock_session)
        
        assert result is not None
        assert isinstance(result, RoutePublishStatusOut)
        assert result.id == str(self.route_id)
        assert result.name == "test-route"
        assert result.published_stages == []
        assert result.stages_can_update == []
        assert result.segments == []

    def test_get_route_publish_status_with_versions_and_stages(self):
        """Test get_route_publish_status with versions and stages."""
        # Mock node setup
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = self.node_setup_id
        
        # Mock latest version
        mock_latest_version = Mock(spec=NodeSetupVersion)
        mock_latest_version.executable_hash = "latest_hash_123"
        
        # Mock session scalar calls
        def session_scalar_side_effect(*args, **kwargs):
            if not hasattr(session_scalar_side_effect, 'call_count'):
                session_scalar_side_effect.call_count = 0
            session_scalar_side_effect.call_count += 1
            
            if session_scalar_side_effect.call_count == 1:
                return mock_node_setup
            elif session_scalar_side_effect.call_count == 2:
                return mock_latest_version
        
        self.mock_session.scalar.side_effect = session_scalar_side_effect
        
        # Mock stage links
        mock_stage1 = Mock(spec=Stage)
        mock_stage1.name = "development"
        mock_stage2 = Mock(spec=Stage)
        mock_stage2.name = "production"
        
        mock_stage_link1 = Mock(spec=NodeSetupVersionStage)
        mock_stage_link1.stage = mock_stage1
        mock_stage_link1.executable_hash = "latest_hash_123"  # Same as latest
        
        mock_stage_link2 = Mock(spec=NodeSetupVersionStage)
        mock_stage_link2.stage = mock_stage2
        mock_stage_link2.executable_hash = "old_hash_456"  # Different from latest
        
        # Mock route segments
        mock_segment = Mock(spec=RouteSegment)
        mock_segment.id = uuid4()
        mock_segment.segment_order = 1
        mock_segment.type = "literal"
        mock_segment.name = "api"
        mock_segment.default_value = None
        mock_segment.variable_type = None
        
        # Mock session execute calls
        def session_execute_side_effect(*args, **kwargs):
            if not hasattr(session_execute_side_effect, 'call_count'):
                session_execute_side_effect.call_count = 0
            session_execute_side_effect.call_count += 1
            
            mock_result = Mock()
            if session_execute_side_effect.call_count == 1:
                # First execute call for stage links
                mock_result.scalars.return_value.all.return_value = [mock_stage_link1, mock_stage_link2]
            elif session_execute_side_effect.call_count == 2:
                # Second execute call for route segments
                mock_result.scalars.return_value.all.return_value = [mock_segment]
            
            return mock_result
        
        self.mock_session.execute.side_effect = session_execute_side_effect
        
        result = get_route_publish_status(self.mock_route, self.mock_session)
        
        assert result is not None
        assert isinstance(result, RoutePublishStatusOut)
        assert result.id == str(self.route_id)
        assert result.name == "test-route"
        assert set(result.published_stages) == {"development", "production"}
        assert result.stages_can_update == ["production"]  # Only production can update
        assert len(result.segments) == 1
        assert result.segments[0].name == "api"

    def test_get_route_publish_status_with_segments(self):
        """Test get_route_publish_status with detailed segment information."""
        # Mock node setup and version
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = self.node_setup_id
        
        mock_latest_version = Mock(spec=NodeSetupVersion)
        mock_latest_version.executable_hash = "hash123"
        
        def session_scalar_side_effect(*args, **kwargs):
            if not hasattr(session_scalar_side_effect, 'call_count'):
                session_scalar_side_effect.call_count = 0
            session_scalar_side_effect.call_count += 1
            
            if session_scalar_side_effect.call_count == 1:
                return mock_node_setup
            elif session_scalar_side_effect.call_count == 2:
                return mock_latest_version
        
        self.mock_session.scalar.side_effect = session_scalar_side_effect
        
        # Mock segments with different types
        segment_id1 = uuid4()
        segment_id2 = uuid4()
        
        mock_segment1 = Mock(spec=RouteSegment)
        mock_segment1.id = segment_id1
        mock_segment1.segment_order = 1
        mock_segment1.type = "literal"
        mock_segment1.name = "api"
        mock_segment1.default_value = None
        mock_segment1.variable_type = None
        
        mock_segment2 = Mock(spec=RouteSegment)
        mock_segment2.id = segment_id2
        mock_segment2.segment_order = 2
        mock_segment2.type = "variable"
        mock_segment2.name = "user_id"
        mock_segment2.default_value = "123"
        mock_segment2.variable_type = "integer"
        
        def session_execute_side_effect(*args, **kwargs):
            if not hasattr(session_execute_side_effect, 'call_count'):
                session_execute_side_effect.call_count = 0
            session_execute_side_effect.call_count += 1
            
            mock_result = Mock()
            if session_execute_side_effect.call_count == 1:
                # Stage links
                mock_result.scalars.return_value.all.return_value = []
            elif session_execute_side_effect.call_count == 2:
                # Route segments
                mock_result.scalars.return_value.all.return_value = [mock_segment1, mock_segment2]
            
            return mock_result
        
        self.mock_session.execute.side_effect = session_execute_side_effect
        
        result = get_route_publish_status(self.mock_route, self.mock_session)
        
        assert result is not None
        assert len(result.segments) == 2
        
        # Check first segment
        seg1 = result.segments[0]
        assert seg1.id == str(segment_id1)
        assert seg1.segment_order == 1
        assert seg1.type == "literal"
        assert seg1.name == "api"
        assert seg1.default_value is None
        assert seg1.variable_type is None
        
        # Check second segment
        seg2 = result.segments[1]
        assert seg2.id == str(segment_id2)
        assert seg2.segment_order == 2
        assert seg2.type == "variable"
        assert seg2.name == "user_id"
        assert seg2.default_value == "123"
        assert seg2.variable_type == "integer"

    def test_get_schedule_publish_status_no_node_setup(self):
        """Test get_schedule_publish_status when no node setup exists."""
        # Mock session.scalar to return None for NodeSetup
        self.mock_session.scalar.return_value = None
        
        result = get_schedule_publish_status(self.mock_schedule, self.mock_session)
        
        assert result is None
        # Verify the correct query was made
        self.mock_session.scalar.assert_called_once()

    def test_get_schedule_publish_status_no_versions(self):
        """Test get_schedule_publish_status when node setup exists but no versions."""
        # Mock node setup exists
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = self.node_setup_id
        
        # Mock session calls
        def session_scalar_side_effect(*args, **kwargs):
            if not hasattr(session_scalar_side_effect, 'call_count'):
                session_scalar_side_effect.call_count = 0
            session_scalar_side_effect.call_count += 1
            
            if session_scalar_side_effect.call_count == 1:
                return mock_node_setup
            elif session_scalar_side_effect.call_count == 2:
                return None
        
        self.mock_session.scalar.side_effect = session_scalar_side_effect
        
        # Mock empty stage links
        mock_execute_result = Mock()
        mock_execute_result.scalars.return_value.all.return_value = []
        self.mock_session.execute.return_value = mock_execute_result
        
        result = get_schedule_publish_status(self.mock_schedule, self.mock_session)
        
        assert result is not None
        assert isinstance(result, SchedulePublishStatusOut)
        assert result.id == str(self.schedule_id)
        assert result.name == "test-schedule"
        assert result.cron_expression == "0 0 * * *"
        assert result.published_stages == []
        assert result.stages_can_update == []

    def test_get_schedule_publish_status_with_versions_and_stages(self):
        """Test get_schedule_publish_status with versions and stages."""
        # Mock node setup
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = self.node_setup_id
        
        # Mock latest version
        mock_latest_version = Mock(spec=NodeSetupVersion)
        mock_latest_version.executable_hash = "latest_hash_789"
        
        # Mock session scalar calls
        def session_scalar_side_effect(*args, **kwargs):
            if not hasattr(session_scalar_side_effect, 'call_count'):
                session_scalar_side_effect.call_count = 0
            session_scalar_side_effect.call_count += 1
            
            if session_scalar_side_effect.call_count == 1:
                return mock_node_setup
            elif session_scalar_side_effect.call_count == 2:
                return mock_latest_version
        
        self.mock_session.scalar.side_effect = session_scalar_side_effect
        
        # Mock stage links
        mock_stage1 = Mock(spec=Stage)
        mock_stage1.name = "staging"
        mock_stage2 = Mock(spec=Stage)
        mock_stage2.name = "production"
        
        mock_stage_link1 = Mock(spec=NodeSetupVersionStage)
        mock_stage_link1.stage = mock_stage1
        mock_stage_link1.executable_hash = "latest_hash_789"  # Same as latest
        
        mock_stage_link2 = Mock(spec=NodeSetupVersionStage)
        mock_stage_link2.stage = mock_stage2
        mock_stage_link2.executable_hash = "old_hash_999"  # Different from latest
        
        # Mock session execute
        mock_execute_result = Mock()
        mock_execute_result.scalars.return_value.all.return_value = [mock_stage_link1, mock_stage_link2]
        self.mock_session.execute.return_value = mock_execute_result
        
        result = get_schedule_publish_status(self.mock_schedule, self.mock_session)
        
        assert result is not None
        assert isinstance(result, SchedulePublishStatusOut)
        assert result.id == str(self.schedule_id)
        assert result.name == "test-schedule"
        assert result.cron_expression == "0 0 * * *"
        assert set(result.published_stages) == {"staging", "production"}
        assert result.stages_can_update == ["production"]  # Only production can update

    def test_get_schedule_publish_status_all_stages_up_to_date(self):
        """Test get_schedule_publish_status when all stages are up to date."""
        # Mock node setup
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = self.node_setup_id
        
        # Mock latest version
        mock_latest_version = Mock(spec=NodeSetupVersion)
        mock_latest_version.executable_hash = "current_hash"
        
        def session_scalar_side_effect(*args, **kwargs):
            if not hasattr(session_scalar_side_effect, 'call_count'):
                session_scalar_side_effect.call_count = 0
            session_scalar_side_effect.call_count += 1
            
            if session_scalar_side_effect.call_count == 1:
                return mock_node_setup
            elif session_scalar_side_effect.call_count == 2:
                return mock_latest_version
        
        self.mock_session.scalar.side_effect = session_scalar_side_effect
        
        # Mock stage links - all up to date
        mock_stage1 = Mock(spec=Stage)
        mock_stage1.name = "development"
        mock_stage2 = Mock(spec=Stage)
        mock_stage2.name = "production"
        
        mock_stage_link1 = Mock(spec=NodeSetupVersionStage)
        mock_stage_link1.stage = mock_stage1
        mock_stage_link1.executable_hash = "current_hash"  # Same as latest
        
        mock_stage_link2 = Mock(spec=NodeSetupVersionStage)
        mock_stage_link2.stage = mock_stage2
        mock_stage_link2.executable_hash = "current_hash"  # Same as latest
        
        mock_execute_result = Mock()
        mock_execute_result.scalars.return_value.all.return_value = [mock_stage_link1, mock_stage_link2]
        self.mock_session.execute.return_value = mock_execute_result
        
        result = get_schedule_publish_status(self.mock_schedule, self.mock_session)
        
        assert result is not None
        assert set(result.published_stages) == {"development", "production"}
        assert result.stages_can_update == []  # No stages need updating

    def test_get_stage_data_empty_project(self):
        """Test get_stage_data with no stages in project."""
        # Mock empty stages
        mock_execute_result = Mock()
        mock_execute_result.scalars.return_value.all.return_value = []
        self.mock_session.execute.return_value = mock_execute_result
        
        result = get_stage_data(str(self.project_id), self.mock_session)
        
        assert result == []
        # Verify the correct query was made
        self.mock_session.execute.assert_called_once()

    def test_get_stage_data_with_stages(self):
        """Test get_stage_data with multiple stages."""
        stage_id1 = uuid4()
        stage_id2 = uuid4()
        stage_id3 = uuid4()
        
        # Mock stages
        mock_stage1 = Mock(spec=Stage)
        mock_stage1.id = stage_id1
        mock_stage1.name = "development"
        mock_stage1.is_production = False
        
        mock_stage2 = Mock(spec=Stage)
        mock_stage2.id = stage_id2
        mock_stage2.name = "staging"
        mock_stage2.is_production = False
        
        mock_stage3 = Mock(spec=Stage)
        mock_stage3.id = stage_id3
        mock_stage3.name = "production"
        mock_stage3.is_production = True
        
        mock_execute_result = Mock()
        mock_execute_result.scalars.return_value.all.return_value = [mock_stage1, mock_stage2, mock_stage3]
        self.mock_session.execute.return_value = mock_execute_result
        
        result = get_stage_data(str(self.project_id), self.mock_session)
        
        assert len(result) == 3
        assert all(isinstance(stage, StageOut) for stage in result)
        
        # Check first stage
        assert result[0].id == str(stage_id1)
        assert result[0].name == "development"
        assert result[0].is_production is False
        
        # Check second stage
        assert result[1].id == str(stage_id2)
        assert result[1].name == "staging"
        assert result[1].is_production is False
        
        # Check third stage
        assert result[2].id == str(stage_id3)
        assert result[2].name == "production"
        assert result[2].is_production is True

    def test_get_stage_data_single_production_stage(self):
        """Test get_stage_data with single production stage."""
        stage_id = uuid4()
        
        mock_stage = Mock(spec=Stage)
        mock_stage.id = stage_id
        mock_stage.name = "production"
        mock_stage.is_production = True
        
        mock_execute_result = Mock()
        mock_execute_result.scalars.return_value.all.return_value = [mock_stage]
        self.mock_session.execute.return_value = mock_execute_result
        
        result = get_stage_data(str(self.project_id), self.mock_session)
        
        assert len(result) == 1
        assert result[0].id == str(stage_id)
        assert result[0].name == "production"
        assert result[0].is_production is True

    def test_get_route_publish_status_no_latest_hash(self):
        """Test get_route_publish_status when latest version exists but has no hash."""
        # Mock node setup
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = self.node_setup_id
        
        # Mock latest version with None hash
        mock_latest_version = Mock(spec=NodeSetupVersion)
        mock_latest_version.executable_hash = None
        
        def session_scalar_side_effect(*args, **kwargs):
            if not hasattr(session_scalar_side_effect, 'call_count'):
                session_scalar_side_effect.call_count = 0
            session_scalar_side_effect.call_count += 1
            
            if session_scalar_side_effect.call_count == 1:
                return mock_node_setup
            elif session_scalar_side_effect.call_count == 2:
                return mock_latest_version
        
        self.mock_session.scalar.side_effect = session_scalar_side_effect
        
        # Mock stage with some hash
        mock_stage = Mock(spec=Stage)
        mock_stage.name = "development"
        
        mock_stage_link = Mock(spec=NodeSetupVersionStage)
        mock_stage_link.stage = mock_stage
        mock_stage_link.executable_hash = "some_hash"
        
        def session_execute_side_effect(*args, **kwargs):
            if not hasattr(session_execute_side_effect, 'call_count'):
                session_execute_side_effect.call_count = 0
            session_execute_side_effect.call_count += 1
            
            mock_result = Mock()
            if session_execute_side_effect.call_count == 1:
                # Stage links
                mock_result.scalars.return_value.all.return_value = [mock_stage_link]
            elif session_execute_side_effect.call_count == 2:
                # Route segments
                mock_result.scalars.return_value.all.return_value = []
            
            return mock_result
        
        self.mock_session.execute.side_effect = session_execute_side_effect
        
        result = get_route_publish_status(self.mock_route, self.mock_session)
        
        assert result is not None
        assert result.published_stages == ["development"]
        assert result.stages_can_update == []  # No updates possible when latest_hash is None

    def test_get_schedule_publish_status_no_latest_hash(self):
        """Test get_schedule_publish_status when latest version exists but has no hash."""
        # Mock node setup
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = self.node_setup_id
        
        # Mock latest version with None hash
        mock_latest_version = Mock(spec=NodeSetupVersion)
        mock_latest_version.executable_hash = None
        
        def session_scalar_side_effect(*args, **kwargs):
            if not hasattr(session_scalar_side_effect, 'call_count'):
                session_scalar_side_effect.call_count = 0
            session_scalar_side_effect.call_count += 1
            
            if session_scalar_side_effect.call_count == 1:
                return mock_node_setup
            elif session_scalar_side_effect.call_count == 2:
                return mock_latest_version
        
        self.mock_session.scalar.side_effect = session_scalar_side_effect
        
        # Mock stage with some hash
        mock_stage = Mock(spec=Stage)
        mock_stage.name = "production"
        
        mock_stage_link = Mock(spec=NodeSetupVersionStage)
        mock_stage_link.stage = mock_stage
        mock_stage_link.executable_hash = "some_hash"
        
        mock_execute_result = Mock()
        mock_execute_result.scalars.return_value.all.return_value = [mock_stage_link]
        self.mock_session.execute.return_value = mock_execute_result
        
        result = get_schedule_publish_status(self.mock_schedule, self.mock_session)
        
        assert result is not None
        assert result.published_stages == ["production"]
        assert result.stages_can_update == []  # No updates possible when latest_hash is None

    def test_get_route_publish_status_complex_scenario(self):
        """Test get_route_publish_status with complex mixed scenario."""
        # Mock node setup
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = self.node_setup_id
        
        # Mock latest version
        mock_latest_version = Mock(spec=NodeSetupVersion)
        mock_latest_version.executable_hash = "latest_v3"
        
        def session_scalar_side_effect(*args, **kwargs):
            if not hasattr(session_scalar_side_effect, 'call_count'):
                session_scalar_side_effect.call_count = 0
            session_scalar_side_effect.call_count += 1
            
            if session_scalar_side_effect.call_count == 1:
                return mock_node_setup
            elif session_scalar_side_effect.call_count == 2:
                return mock_latest_version
        
        self.mock_session.scalar.side_effect = session_scalar_side_effect
        
        # Mock multiple stages with different hash states
        mock_stage_dev = Mock(spec=Stage)
        mock_stage_dev.name = "development"
        mock_stage_staging = Mock(spec=Stage)
        mock_stage_staging.name = "staging"
        mock_stage_prod = Mock(spec=Stage)
        mock_stage_prod.name = "production"
        
        mock_link_dev = Mock(spec=NodeSetupVersionStage)
        mock_link_dev.stage = mock_stage_dev
        mock_link_dev.executable_hash = "latest_v3"  # Up to date
        
        mock_link_staging = Mock(spec=NodeSetupVersionStage)
        mock_link_staging.stage = mock_stage_staging
        mock_link_staging.executable_hash = "old_v2"  # Needs update
        
        mock_link_prod = Mock(spec=NodeSetupVersionStage)
        mock_link_prod.stage = mock_stage_prod
        mock_link_prod.executable_hash = "very_old_v1"  # Needs update
        
        # Mock complex segments
        segment_id1 = uuid4()
        segment_id2 = uuid4()
        segment_id3 = uuid4()
        
        mock_segment1 = Mock(spec=RouteSegment)
        mock_segment1.id = segment_id1
        mock_segment1.segment_order = 1
        mock_segment1.type = "literal"
        mock_segment1.name = "api"
        mock_segment1.default_value = None
        mock_segment1.variable_type = None
        
        mock_segment2 = Mock(spec=RouteSegment)
        mock_segment2.id = segment_id2
        mock_segment2.segment_order = 2
        mock_segment2.type = "literal"
        mock_segment2.name = "v1"
        mock_segment2.default_value = None
        mock_segment2.variable_type = None
        
        mock_segment3 = Mock(spec=RouteSegment)
        mock_segment3.id = segment_id3
        mock_segment3.segment_order = 3
        mock_segment3.type = "variable"
        mock_segment3.name = "resource_id"
        mock_segment3.default_value = "0"
        mock_segment3.variable_type = "string"
        
        def session_execute_side_effect(*args, **kwargs):
            if not hasattr(session_execute_side_effect, 'call_count'):
                session_execute_side_effect.call_count = 0
            session_execute_side_effect.call_count += 1
            
            mock_result = Mock()
            if session_execute_side_effect.call_count == 1:
                # Stage links
                mock_result.scalars.return_value.all.return_value = [mock_link_dev, mock_link_staging, mock_link_prod]
            elif session_execute_side_effect.call_count == 2:
                # Route segments
                mock_result.scalars.return_value.all.return_value = [mock_segment1, mock_segment2, mock_segment3]
            
            return mock_result
        
        self.mock_session.execute.side_effect = session_execute_side_effect
        
        result = get_route_publish_status(self.mock_route, self.mock_session)
        
        assert result is not None
        assert set(result.published_stages) == {"development", "staging", "production"}
        assert set(result.stages_can_update) == {"staging", "production"}  # Only these need updates
        assert len(result.segments) == 3
        
        # Verify segments are correctly mapped
        segments_by_order = {seg.segment_order: seg for seg in result.segments}
        assert segments_by_order[1].name == "api"
        assert segments_by_order[1].type == "literal"
        assert segments_by_order[2].name == "v1"
        assert segments_by_order[2].type == "literal"
        assert segments_by_order[3].name == "resource_id"
        assert segments_by_order[3].type == "variable"
        assert segments_by_order[3].default_value == "0"
        assert segments_by_order[3].variable_type == "string"