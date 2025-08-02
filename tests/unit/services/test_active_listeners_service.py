import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from services.active_listeners_service import get_active_listeners_service


@pytest.mark.unit
class TestActiveListenersService:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.version_id = str(uuid4())
    
    @patch('services.active_listeners_service.settings')
    @patch('services.active_listeners_service.get_active_listeners_service_from_env')
    def test_get_active_listeners_service_initialization(self, mock_get_service_from_env, mock_settings):
        """Test ActiveListenersService initialization with correct AWS settings."""
        # Mock settings
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.AWS_REGION = "us-east-1"
        
        # Mock the service instance
        mock_service_instance = Mock()
        mock_get_service_from_env.return_value = mock_service_instance
        
        # Call the function
        result = get_active_listeners_service()
        
        # Verify get_active_listeners_service_from_env was called with correct parameters
        mock_get_service_from_env.assert_called_once_with(
            access_key="test-access-key",
            secret_key="test-secret-key",
            region="us-east-1"
        )
        
        assert result == mock_service_instance
    
    @patch('services.active_listeners_service.settings')
    @patch('services.active_listeners_service.get_active_listeners_service_from_env')
    def test_get_active_listeners_service_with_different_settings(self, mock_get_service_from_env, mock_settings):
        """Test ActiveListenersService initialization with different AWS settings."""
        # Mock different settings
        mock_settings.AWS_ACCESS_KEY_ID = "different-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "different-secret-key"
        mock_settings.AWS_REGION = "eu-west-1"
        
        mock_service_instance = Mock()
        mock_get_service_from_env.return_value = mock_service_instance
        
        result = get_active_listeners_service()
        
        mock_get_service_from_env.assert_called_once_with(
            access_key="different-access-key",
            secret_key="different-secret-key",
            region="eu-west-1"
        )
        
        assert result == mock_service_instance
    
    @patch('services.active_listeners_service.settings')
    @patch('services.active_listeners_service.get_active_listeners_service_from_env')
    def test_get_active_listeners_service_creation_error(self, mock_get_service_from_env, mock_settings):
        """Test ActiveListenersService creation when initialization fails."""
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.AWS_REGION = "us-east-1"
        
        # Mock get_active_listeners_service_from_env to raise an exception
        mock_get_service_from_env.side_effect = Exception("AWS credentials invalid")
        
        with pytest.raises(Exception, match="AWS credentials invalid"):
            get_active_listeners_service()
    
    @patch('services.active_listeners_service.settings')
    @patch('services.active_listeners_service.get_active_listeners_service_from_env')
    def test_get_active_listeners_service_returns_new_instance_each_time(self, mock_get_service_from_env, mock_settings):
        """Test that get_active_listeners_service returns value from get_active_listeners_service_from_env each time."""
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.AWS_REGION = "us-east-1"
        
        # Mock different instances
        mock_instance_1 = Mock()
        mock_instance_2 = Mock()
        mock_get_service_from_env.side_effect = [mock_instance_1, mock_instance_2]
        
        result_1 = get_active_listeners_service()
        result_2 = get_active_listeners_service()
        
        assert result_1 == mock_instance_1
        assert result_2 == mock_instance_2
        assert result_1 != result_2
        assert mock_get_service_from_env.call_count == 2
    
    @patch('services.active_listeners_service.settings')
    @patch('services.active_listeners_service.get_active_listeners_service_from_env')
    def test_get_active_listeners_service_with_none_settings(self, mock_get_service_from_env, mock_settings):
        """Test ActiveListenersService creation with None/empty settings."""
        # Mock None settings
        mock_settings.AWS_ACCESS_KEY_ID = None
        mock_settings.AWS_SECRET_ACCESS_KEY = None
        mock_settings.AWS_REGION = None
        
        mock_service_instance = Mock()
        mock_get_service_from_env.return_value = mock_service_instance
        
        result = get_active_listeners_service()
        
        mock_get_service_from_env.assert_called_once_with(
            access_key=None,
            secret_key=None,
            region=None
        )
        
        assert result == mock_service_instance
    
    @patch('services.active_listeners_service.settings')
    @patch('services.active_listeners_service.get_active_listeners_service_from_env')
    def test_get_active_listeners_service_with_empty_string_settings(self, mock_get_service_from_env, mock_settings):
        """Test ActiveListenersService creation with empty string settings."""
        # Mock empty string settings
        mock_settings.AWS_ACCESS_KEY_ID = ""
        mock_settings.AWS_SECRET_ACCESS_KEY = ""
        mock_settings.AWS_REGION = ""
        
        mock_service_instance = Mock()
        mock_get_service_from_env.return_value = mock_service_instance
        
        result = get_active_listeners_service()
        
        mock_get_service_from_env.assert_called_once_with(
            access_key="",
            secret_key="",
            region=""
        )
        
        assert result == mock_service_instance