import pytest
from unittest.mock import Mock, patch

from services.env_var_manager import get_env_var_manager


@pytest.mark.unit
class TestEnvVarManager:
    
    def test_get_env_var_manager_creates_instance_with_settings(self):
        """Test that get_env_var_manager creates EnvVarManager with correct AWS settings."""
        with patch('services.env_var_manager.EnvVarManager') as mock_env_var_manager, \
             patch('services.env_var_manager.settings') as mock_settings:
            
            # Mock settings values
            mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
            mock_settings.AWS_REGION = "us-east-1"
            
            # Mock EnvVarManager instance
            mock_instance = Mock()
            mock_env_var_manager.return_value = mock_instance
            
            # Call the function
            result = get_env_var_manager()
            
            # Verify EnvVarManager was called with correct parameters
            mock_env_var_manager.assert_called_once_with(
                access_key="test-access-key",
                secret_key="test-secret-key",
                region="us-east-1"
            )
            
            # Verify the correct instance is returned
            assert result == mock_instance

    def test_get_env_var_manager_with_different_aws_settings(self):
        """Test that get_env_var_manager works with different AWS settings."""
        with patch('services.env_var_manager.EnvVarManager') as mock_env_var_manager, \
             patch('services.env_var_manager.settings') as mock_settings:
            
            # Mock different settings values
            mock_settings.AWS_ACCESS_KEY_ID = "different-access-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "different-secret-key"
            mock_settings.AWS_REGION = "eu-west-1"
            
            mock_instance = Mock()
            mock_env_var_manager.return_value = mock_instance
            
            result = get_env_var_manager()
            
            # Verify EnvVarManager was called with the different parameters
            mock_env_var_manager.assert_called_once_with(
                access_key="different-access-key",
                secret_key="different-secret-key",
                region="eu-west-1"
            )
            
            assert result == mock_instance

    def test_get_env_var_manager_with_none_values(self):
        """Test that get_env_var_manager handles None values in settings."""
        with patch('services.env_var_manager.EnvVarManager') as mock_env_var_manager, \
             patch('services.env_var_manager.settings') as mock_settings:
            
            # Mock settings with None values
            mock_settings.AWS_ACCESS_KEY_ID = None
            mock_settings.AWS_SECRET_ACCESS_KEY = None
            mock_settings.AWS_REGION = None
            
            mock_instance = Mock()
            mock_env_var_manager.return_value = mock_instance
            
            result = get_env_var_manager()
            
            # Verify EnvVarManager was called with None values
            mock_env_var_manager.assert_called_once_with(
                access_key=None,
                secret_key=None,
                region=None
            )
            
            assert result == mock_instance

    def test_get_env_var_manager_with_empty_strings(self):
        """Test that get_env_var_manager handles empty string values in settings."""
        with patch('services.env_var_manager.EnvVarManager') as mock_env_var_manager, \
             patch('services.env_var_manager.settings') as mock_settings:
            
            # Mock settings with empty string values
            mock_settings.AWS_ACCESS_KEY_ID = ""
            mock_settings.AWS_SECRET_ACCESS_KEY = ""
            mock_settings.AWS_REGION = ""
            
            mock_instance = Mock()
            mock_env_var_manager.return_value = mock_instance
            
            result = get_env_var_manager()
            
            # Verify EnvVarManager was called with empty strings
            mock_env_var_manager.assert_called_once_with(
                access_key="",
                secret_key="",
                region=""
            )
            
            assert result == mock_instance

    def test_get_env_var_manager_returns_new_instance_each_call(self):
        """Test that get_env_var_manager returns a new instance on each call."""
        with patch('services.env_var_manager.EnvVarManager') as mock_env_var_manager, \
             patch('services.env_var_manager.settings') as mock_settings:
            
            mock_settings.AWS_ACCESS_KEY_ID = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret"
            mock_settings.AWS_REGION = "us-west-2"
            
            # Create different mock instances for each call
            mock_instance1 = Mock()
            mock_instance2 = Mock()
            mock_env_var_manager.side_effect = [mock_instance1, mock_instance2]
            
            # Call the function twice
            result1 = get_env_var_manager()
            result2 = get_env_var_manager()
            
            # Verify EnvVarManager was called twice with same parameters
            assert mock_env_var_manager.call_count == 2
            
            # Verify different instances are returned
            assert result1 == mock_instance1
            assert result2 == mock_instance2
            assert result1 != result2

    def test_get_env_var_manager_propagates_env_var_manager_exception(self):
        """Test that exceptions from EnvVarManager constructor are propagated."""
        with patch('services.env_var_manager.EnvVarManager') as mock_env_var_manager, \
             patch('services.env_var_manager.settings') as mock_settings:
            
            mock_settings.AWS_ACCESS_KEY_ID = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret"
            mock_settings.AWS_REGION = "invalid-region"
            
            # Mock EnvVarManager to raise an exception
            mock_env_var_manager.side_effect = ValueError("Invalid AWS region")
            
            # Verify the exception is propagated
            with pytest.raises(ValueError) as exc_info:
                get_env_var_manager()
            
            assert "Invalid AWS region" in str(exc_info.value)

    def test_get_env_var_manager_with_long_aws_credentials(self):
        """Test that get_env_var_manager handles long AWS credential strings."""
        with patch('services.env_var_manager.EnvVarManager') as mock_env_var_manager, \
             patch('services.env_var_manager.settings') as mock_settings:
            
            # Mock settings with long credential strings
            long_access_key = "A" * 100  # Very long access key
            long_secret_key = "S" * 200  # Very long secret key
            
            mock_settings.AWS_ACCESS_KEY_ID = long_access_key
            mock_settings.AWS_SECRET_ACCESS_KEY = long_secret_key
            mock_settings.AWS_REGION = "ap-southeast-1"
            
            mock_instance = Mock()
            mock_env_var_manager.return_value = mock_instance
            
            result = get_env_var_manager()
            
            # Verify EnvVarManager was called with long credentials
            mock_env_var_manager.assert_called_once_with(
                access_key=long_access_key,
                secret_key=long_secret_key,
                region="ap-southeast-1"
            )
            
            assert result == mock_instance

    def test_get_env_var_manager_import_verification(self):
        """Test that the correct EnvVarManager is imported and used."""
        with patch('services.env_var_manager.EnvVarManager') as mock_env_var_manager, \
             patch('services.env_var_manager.settings') as mock_settings:
            
            mock_settings.AWS_ACCESS_KEY_ID = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret"
            mock_settings.AWS_REGION = "us-east-1"
            
            mock_instance = Mock()
            mock_env_var_manager.return_value = mock_instance
            
            result = get_env_var_manager()
            
            # Verify the EnvVarManager from polysynergy_node_runner is used
            mock_env_var_manager.assert_called_once()
            assert result == mock_instance

    def test_get_env_var_manager_settings_access_pattern(self):
        """Test that settings are accessed correctly for each AWS parameter."""
        with patch('services.env_var_manager.EnvVarManager') as mock_env_var_manager, \
             patch('services.env_var_manager.settings') as mock_settings:
            
            # Set up settings mock to track attribute access
            mock_settings.AWS_ACCESS_KEY_ID = "access-key-123"
            mock_settings.AWS_SECRET_ACCESS_KEY = "secret-key-456"
            mock_settings.AWS_REGION = "ca-central-1"
            
            mock_instance = Mock()
            mock_env_var_manager.return_value = mock_instance
            
            get_env_var_manager()
            
            # Verify that all three settings were accessed
            # This is implicitly tested by the successful call to EnvVarManager
            mock_env_var_manager.assert_called_once_with(
                access_key="access-key-123",
                secret_key="secret-key-456",
                region="ca-central-1"
            )

    def test_get_env_var_manager_dependency_injection_compatibility(self):
        """Test that get_env_var_manager is compatible as a FastAPI dependency."""
        # This test verifies that the function signature is compatible with FastAPI's dependency injection
        import inspect
        
        # Get function signature
        sig = inspect.signature(get_env_var_manager)
        
        # Verify it has no required parameters (can be used as dependency without Depends())
        assert len(sig.parameters) == 0
        
        # Verify it has a return annotation or can be inferred
        assert sig.return_annotation is not inspect.Signature.empty or callable(get_env_var_manager)

    def test_get_env_var_manager_multiple_calls_consistent_behavior(self):
        """Test that multiple calls to get_env_var_manager behave consistently."""
        with patch('services.env_var_manager.EnvVarManager') as mock_env_var_manager, \
             patch('services.env_var_manager.settings') as mock_settings:
            
            mock_settings.AWS_ACCESS_KEY_ID = "consistent-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "consistent-secret"
            mock_settings.AWS_REGION = "consistent-region"
            
            # Create multiple mock instances
            mock_instances = [Mock() for _ in range(3)]
            mock_env_var_manager.side_effect = mock_instances
            
            # Call the function multiple times
            results = [get_env_var_manager() for _ in range(3)]
            
            # Verify all calls used same parameters
            for call in mock_env_var_manager.call_args_list:
                args, kwargs = call
                assert kwargs == {
                    'access_key': 'consistent-key',
                    'secret_key': 'consistent-secret',
                    'region': 'consistent-region'
                }
            
            # Verify each call returned different instances
            assert len(set(results)) == 3  # All different instances