import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from services.env_var_manager import get_env_var_manager


@pytest.mark.unit
class TestEnvVarService:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.project_id = str(uuid4())
        self.tenant_id = str(uuid4())
    
    @patch('services.env_var_manager.settings')
    @patch('services.env_var_manager.EnvVarManager')
    def test_get_env_var_manager_initialization(self, mock_env_var_manager_class, mock_settings):
        """Test EnvVarManager initialization with correct AWS settings."""
        # Mock settings
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.AWS_REGION = "us-east-1"
        
        # Mock the EnvVarManager instance
        mock_manager_instance = Mock()
        mock_env_var_manager_class.return_value = mock_manager_instance
        
        # Call the function
        result = get_env_var_manager()
        
        # Verify EnvVarManager was created with correct parameters
        mock_env_var_manager_class.assert_called_once_with(
            access_key="test-access-key",
            secret_key="test-secret-key",
            region="us-east-1"
        )
        
        assert result == mock_manager_instance
    
    @patch('services.env_var_manager.settings')
    @patch('services.env_var_manager.EnvVarManager')
    def test_get_env_var_manager_with_different_settings(self, mock_env_var_manager_class, mock_settings):
        """Test EnvVarManager initialization with different AWS settings."""
        # Mock different settings
        mock_settings.AWS_ACCESS_KEY_ID = "different-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "different-secret-key"
        mock_settings.AWS_REGION = "eu-west-1"
        
        mock_manager_instance = Mock()
        mock_env_var_manager_class.return_value = mock_manager_instance
        
        result = get_env_var_manager()
        
        mock_env_var_manager_class.assert_called_once_with(
            access_key="different-access-key",
            secret_key="different-secret-key",
            region="eu-west-1"
        )
        
        assert result == mock_manager_instance
    
    @patch('services.env_var_manager.settings')
    @patch('services.env_var_manager.EnvVarManager')
    def test_get_env_var_manager_creation_error(self, mock_env_var_manager_class, mock_settings):
        """Test EnvVarManager creation when initialization fails."""
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.AWS_REGION = "us-east-1"
        
        # Mock EnvVarManager constructor to raise an exception
        mock_env_var_manager_class.side_effect = Exception("AWS credentials invalid")
        
        with pytest.raises(Exception, match="AWS credentials invalid"):
            get_env_var_manager()
    
    @patch('services.env_var_manager.settings')
    @patch('services.env_var_manager.EnvVarManager')
    def test_get_env_var_manager_returns_new_instance_each_time(self, mock_env_var_manager_class, mock_settings):
        """Test that get_env_var_manager returns a new instance each time."""
        mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.AWS_REGION = "us-east-1"
        
        # Mock different instances
        mock_instance_1 = Mock()
        mock_instance_2 = Mock()
        mock_env_var_manager_class.side_effect = [mock_instance_1, mock_instance_2]
        
        result_1 = get_env_var_manager()
        result_2 = get_env_var_manager()
        
        assert result_1 == mock_instance_1
        assert result_2 == mock_instance_2
        assert result_1 != result_2
        assert mock_env_var_manager_class.call_count == 2
    
    @patch('services.env_var_manager.settings')
    @patch('services.env_var_manager.EnvVarManager')
    def test_get_env_var_manager_with_none_settings(self, mock_env_var_manager_class, mock_settings):
        """Test EnvVarManager creation with None/empty settings."""
        # Mock None settings
        mock_settings.AWS_ACCESS_KEY_ID = None
        mock_settings.AWS_SECRET_ACCESS_KEY = None
        mock_settings.AWS_REGION = None
        
        mock_manager_instance = Mock()
        mock_env_var_manager_class.return_value = mock_manager_instance
        
        result = get_env_var_manager()
        
        mock_env_var_manager_class.assert_called_once_with(
            access_key=None,
            secret_key=None,
            region=None
        )
        
        assert result == mock_manager_instance
    
    @patch('services.env_var_manager.settings')
    @patch('services.env_var_manager.EnvVarManager')
    def test_get_env_var_manager_with_empty_string_settings(self, mock_env_var_manager_class, mock_settings):
        """Test EnvVarManager creation with empty string settings."""
        # Mock empty string settings
        mock_settings.AWS_ACCESS_KEY_ID = ""
        mock_settings.AWS_SECRET_ACCESS_KEY = ""
        mock_settings.AWS_REGION = ""
        
        mock_manager_instance = Mock()
        mock_env_var_manager_class.return_value = mock_manager_instance
        
        result = get_env_var_manager()
        
        mock_env_var_manager_class.assert_called_once_with(
            access_key="",
            secret_key="",
            region=""
        )
        
        assert result == mock_manager_instance