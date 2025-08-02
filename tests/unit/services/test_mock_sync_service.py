import pytest
import hashlib
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from services.mock_sync_service import MockSyncService, get_mock_sync_service
from models import Blueprint, Route, Schedule, NodeSetupVersion, NodeSetup, Project


@pytest.mark.unit
class TestMockSyncService:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.project_id = str(uuid4())
        self.version_id = str(uuid4())
        self.node_setup_id = str(uuid4())
        
        # Mock dependencies
        self.mock_db = Mock()
        self.mock_blueprint_service = Mock()
        self.mock_route_service = Mock()
        self.mock_schedule_service = Mock()
        
        # Create service instance
        self.service = MockSyncService(
            self.mock_db,
            self.mock_blueprint_service,
            self.mock_route_service,
            self.mock_schedule_service
        )
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        
        # Mock node setup
        self.mock_node_setup = Mock(spec=NodeSetup)
        self.mock_node_setup.id = self.node_setup_id
        
        # Mock version
        self.mock_version = Mock(spec=NodeSetupVersion)
        self.mock_version.id = self.version_id
        self.mock_version.node_setup = self.mock_node_setup
    
    def test_sync_if_needed_no_executable(self):
        """Test sync_if_needed when version has no executable."""
        self.mock_version.executable = None
        
        self.service.sync_if_needed(self.mock_version, self.mock_project)
        
        # Should not try to resolve parent or publish
        self.mock_node_setup.resolve_parent.assert_not_called()
        self.mock_blueprint_service.publish.assert_not_called()
        self.mock_route_service.sync_lambda.assert_not_called()
        self.mock_schedule_service.publish.assert_not_called()
        self.mock_db.commit.assert_not_called()
    
    def test_sync_if_needed_hash_unchanged(self):
        """Test sync_if_needed when executable hash hasn't changed."""
        executable_content = "test executable code"
        expected_hash = hashlib.sha256(executable_content.encode()).hexdigest()
        
        self.mock_version.executable = executable_content
        self.mock_version.executable_hash = expected_hash
        
        self.service.sync_if_needed(self.mock_version, self.mock_project)
        
        # Should not try to resolve parent or publish
        self.mock_node_setup.resolve_parent.assert_not_called()
        self.mock_blueprint_service.publish.assert_not_called()
        self.mock_route_service.sync_lambda.assert_not_called()
        self.mock_schedule_service.publish.assert_not_called()
        self.mock_db.commit.assert_not_called()
    
    def test_sync_if_needed_blueprint_parent(self):
        """Test sync_if_needed with Blueprint parent."""
        executable_content = "test executable code"
        new_hash = hashlib.sha256(executable_content.encode()).hexdigest()
        
        self.mock_version.executable = executable_content
        self.mock_version.executable_hash = None  # No previous hash
        
        # Mock parent as Blueprint
        mock_blueprint = Mock(spec=Blueprint)
        self.mock_node_setup.resolve_parent.return_value = mock_blueprint
        
        self.service.sync_if_needed(self.mock_version, self.mock_project)
        
        # Should call blueprint publish
        self.mock_node_setup.resolve_parent.assert_called_once_with(self.mock_db)
        self.mock_blueprint_service.publish.assert_called_once_with(mock_blueprint, self.project_id)
        self.mock_route_service.sync_lambda.assert_not_called()
        self.mock_schedule_service.publish.assert_not_called()
        
        # Should update hash and commit
        assert self.mock_version.executable_hash == new_hash
        self.mock_db.commit.assert_called_once()
    
    def test_sync_if_needed_route_parent(self):
        """Test sync_if_needed with Route parent."""
        executable_content = "test executable code"
        new_hash = hashlib.sha256(executable_content.encode()).hexdigest()
        
        self.mock_version.executable = executable_content
        self.mock_version.executable_hash = "old_hash"  # Different hash
        
        # Mock parent as Route
        mock_route = Mock(spec=Route)
        self.mock_node_setup.resolve_parent.return_value = mock_route
        
        self.service.sync_if_needed(self.mock_version, self.mock_project)
        
        # Should call route sync_lambda
        self.mock_node_setup.resolve_parent.assert_called_once_with(self.mock_db)
        self.mock_blueprint_service.publish.assert_not_called()
        self.mock_route_service.sync_lambda.assert_called_once_with(mock_route, stage='mock')
        self.mock_schedule_service.publish.assert_not_called()
        
        # Should update hash and commit
        assert self.mock_version.executable_hash == new_hash
        self.mock_db.commit.assert_called_once()
    
    def test_sync_if_needed_schedule_parent(self):
        """Test sync_if_needed with Schedule parent."""
        executable_content = "test executable code"
        new_hash = hashlib.sha256(executable_content.encode()).hexdigest()
        
        self.mock_version.executable = executable_content
        self.mock_version.executable_hash = "old_hash"
        
        # Mock parent as Schedule
        mock_schedule = Mock(spec=Schedule)
        self.mock_node_setup.resolve_parent.return_value = mock_schedule
        
        self.service.sync_if_needed(self.mock_version, self.mock_project)
        
        # Should call schedule publish
        self.mock_node_setup.resolve_parent.assert_called_once_with(self.mock_db)
        self.mock_blueprint_service.publish.assert_not_called()
        self.mock_route_service.sync_lambda.assert_not_called()
        self.mock_schedule_service.publish.assert_called_once_with(mock_schedule, stage='mock')
        
        # Should update hash and commit
        assert self.mock_version.executable_hash == new_hash
        self.mock_db.commit.assert_called_once()
    
    def test_sync_if_needed_unsupported_parent(self):
        """Test sync_if_needed with unsupported parent type."""
        executable_content = "test executable code"
        
        self.mock_version.executable = executable_content
        self.mock_version.executable_hash = None
        
        # Mock parent as unsupported type
        mock_unsupported = Mock()
        self.mock_node_setup.resolve_parent.return_value = mock_unsupported
        
        self.service.sync_if_needed(self.mock_version, self.mock_project)
        
        # Should not call any publish methods
        self.mock_blueprint_service.publish.assert_not_called()
        self.mock_route_service.sync_lambda.assert_not_called()
        self.mock_schedule_service.publish.assert_not_called()
        
        # Should not update hash or commit
        assert self.mock_version.executable_hash != hashlib.sha256(executable_content.encode()).hexdigest()
        self.mock_db.commit.assert_not_called()
    
    @patch('services.mock_sync_service.get_schedule_publish_service')
    @patch('services.mock_sync_service.get_route_publish_service')
    @patch('services.mock_sync_service.get_blueprint_publish_service')
    @patch('services.mock_sync_service.get_db')
    def test_get_mock_sync_service(self, mock_get_db, mock_get_blueprint, mock_get_route, mock_get_schedule):
        """Test get_mock_sync_service factory function."""
        # Mock dependencies
        mock_db = Mock()
        mock_blueprint_service = Mock()
        mock_route_service = Mock()
        mock_schedule_service = Mock()
        
        mock_get_db.return_value = mock_db
        mock_get_blueprint.return_value = mock_blueprint_service
        mock_get_route.return_value = mock_route_service
        mock_get_schedule.return_value = mock_schedule_service
        
        # Call factory function
        result = get_mock_sync_service(
            db=mock_db,
            blueprint_publish_service=mock_blueprint_service,
            route_publish_service=mock_route_service,
            schedule_publish_service=mock_schedule_service
        )
        
        # Verify instance creation
        assert isinstance(result, MockSyncService)
        assert result.db == mock_db
        assert result.blueprint_publish_service == mock_blueprint_service
        assert result.route_publish_service == mock_route_service
        assert result.schedule_publish_service == mock_schedule_service
    
    def test_sync_if_needed_with_unicode_executable(self):
        """Test sync_if_needed with unicode characters in executable."""
        executable_content = "test code with unicode: 你好世界 🚀"
        new_hash = hashlib.sha256(executable_content.encode()).hexdigest()
        
        self.mock_version.executable = executable_content
        self.mock_version.executable_hash = None
        
        # Mock parent as Blueprint
        mock_blueprint = Mock(spec=Blueprint)
        self.mock_node_setup.resolve_parent.return_value = mock_blueprint
        
        self.service.sync_if_needed(self.mock_version, self.mock_project)
        
        # Should handle unicode correctly
        assert self.mock_version.executable_hash == new_hash
        self.mock_db.commit.assert_called_once()
    
    def test_sync_if_needed_publish_error_handling(self):
        """Test sync_if_needed when publish raises an error."""
        executable_content = "test executable code"
        
        self.mock_version.executable = executable_content
        self.mock_version.executable_hash = None
        
        # Mock parent as Blueprint
        mock_blueprint = Mock(spec=Blueprint)
        self.mock_node_setup.resolve_parent.return_value = mock_blueprint
        
        # Make publish raise an error
        self.mock_blueprint_service.publish.side_effect = Exception("Publish failed")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Publish failed"):
            self.service.sync_if_needed(self.mock_version, self.mock_project)
        
        # Should not commit if publish fails
        self.mock_db.commit.assert_not_called()