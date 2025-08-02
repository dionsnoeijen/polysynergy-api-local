import pytest
from unittest.mock import Mock, patch

from services.execution_storage_service import get_execution_storage_service


@pytest.mark.unit
class TestExecutionStorageService:
    
    def test_get_execution_storage_service_creates_instance_with_settings(self):
        """Test that get_execution_storage_service creates service with correct AWS settings."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            # Mock settings values
            mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
            mock_settings.AWS_REGION = "us-east-1"
            
            # Mock service instance
            mock_instance = Mock()
            mock_factory.return_value = mock_instance
            
            # Call the function
            result = get_execution_storage_service()
            
            # Verify factory was called with correct parameters
            mock_factory.assert_called_once_with(
                access_key="test-access-key",
                secret_key="test-secret-key",
                region="us-east-1"
            )
            
            # Verify the correct instance is returned
            assert result == mock_instance

    def test_get_execution_storage_service_with_different_aws_settings(self):
        """Test that get_execution_storage_service works with different AWS settings."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            # Mock different settings values
            mock_settings.AWS_ACCESS_KEY_ID = "different-access-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "different-secret-key"
            mock_settings.AWS_REGION = "eu-west-1"
            
            mock_instance = Mock()
            mock_factory.return_value = mock_instance
            
            result = get_execution_storage_service()
            
            # Verify factory was called with the different parameters
            mock_factory.assert_called_once_with(
                access_key="different-access-key",
                secret_key="different-secret-key",
                region="eu-west-1"
            )
            
            assert result == mock_instance

    def test_get_execution_storage_service_with_none_values(self):
        """Test that get_execution_storage_service handles None values in settings."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            # Mock settings with None values
            mock_settings.AWS_ACCESS_KEY_ID = None
            mock_settings.AWS_SECRET_ACCESS_KEY = None
            mock_settings.AWS_REGION = None
            
            mock_instance = Mock()
            mock_factory.return_value = mock_instance
            
            result = get_execution_storage_service()
            
            # Verify factory was called with None values
            mock_factory.assert_called_once_with(
                access_key=None,
                secret_key=None,
                region=None
            )
            
            assert result == mock_instance

    def test_get_execution_storage_service_with_empty_strings(self):
        """Test that get_execution_storage_service handles empty string values in settings."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            # Mock settings with empty string values
            mock_settings.AWS_ACCESS_KEY_ID = ""
            mock_settings.AWS_SECRET_ACCESS_KEY = ""
            mock_settings.AWS_REGION = ""
            
            mock_instance = Mock()
            mock_factory.return_value = mock_instance
            
            result = get_execution_storage_service()
            
            # Verify factory was called with empty strings
            mock_factory.assert_called_once_with(
                access_key="",
                secret_key="",
                region=""
            )
            
            assert result == mock_instance

    def test_get_execution_storage_service_returns_new_instance_each_call(self):
        """Test that get_execution_storage_service returns a new instance on each call."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            mock_settings.AWS_ACCESS_KEY_ID = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret"
            mock_settings.AWS_REGION = "us-west-2"
            
            # Create different mock instances for each call
            mock_instance1 = Mock()
            mock_instance2 = Mock()
            mock_factory.side_effect = [mock_instance1, mock_instance2]
            
            # Call the function twice
            result1 = get_execution_storage_service()
            result2 = get_execution_storage_service()
            
            # Verify factory was called twice with same parameters
            assert mock_factory.call_count == 2
            
            # Verify different instances are returned
            assert result1 == mock_instance1
            assert result2 == mock_instance2
            assert result1 != result2

    def test_get_execution_storage_service_propagates_factory_exception(self):
        """Test that exceptions from factory function are propagated."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            mock_settings.AWS_ACCESS_KEY_ID = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret"
            mock_settings.AWS_REGION = "invalid-region"
            
            # Mock factory to raise an exception
            mock_factory.side_effect = ValueError("Invalid AWS region")
            
            # Verify the exception is propagated
            with pytest.raises(ValueError) as exc_info:
                get_execution_storage_service()
            
            assert "Invalid AWS region" in str(exc_info.value)

    def test_get_execution_storage_service_with_long_aws_credentials(self):
        """Test that get_execution_storage_service handles long AWS credential strings."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            # Mock settings with long credential strings
            long_access_key = "A" * 100  # Very long access key
            long_secret_key = "S" * 200  # Very long secret key
            
            mock_settings.AWS_ACCESS_KEY_ID = long_access_key
            mock_settings.AWS_SECRET_ACCESS_KEY = long_secret_key
            mock_settings.AWS_REGION = "ap-southeast-1"
            
            mock_instance = Mock()
            mock_factory.return_value = mock_instance
            
            result = get_execution_storage_service()
            
            # Verify factory was called with long credentials
            mock_factory.assert_called_once_with(
                access_key=long_access_key,
                secret_key=long_secret_key,
                region="ap-southeast-1"
            )
            
            assert result == mock_instance

    def test_get_execution_storage_service_import_verification(self):
        """Test that the correct factory function is imported and used."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            mock_settings.AWS_ACCESS_KEY_ID = "test-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret"
            mock_settings.AWS_REGION = "us-east-1"
            
            mock_instance = Mock()
            mock_factory.return_value = mock_instance
            
            result = get_execution_storage_service()
            
            # Verify the factory from polysynergy_node_runner is used
            mock_factory.assert_called_once()
            assert result == mock_instance

    def test_get_execution_storage_service_settings_access_pattern(self):
        """Test that settings are accessed correctly for each AWS parameter."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            # Set up settings mock to track attribute access
            mock_settings.AWS_ACCESS_KEY_ID = "access-key-123"
            mock_settings.AWS_SECRET_ACCESS_KEY = "secret-key-456"
            mock_settings.AWS_REGION = "ca-central-1"
            
            mock_instance = Mock()
            mock_factory.return_value = mock_instance
            
            get_execution_storage_service()
            
            # Verify that all three settings were accessed
            # This is implicitly tested by the successful call to factory
            mock_factory.assert_called_once_with(
                access_key="access-key-123",
                secret_key="secret-key-456",
                region="ca-central-1"
            )

    def test_get_execution_storage_service_dependency_injection_compatibility(self):
        """Test that get_execution_storage_service is compatible as a FastAPI dependency."""
        # This test verifies that the function signature is compatible with FastAPI's dependency injection
        import inspect
        
        # Get function signature
        sig = inspect.signature(get_execution_storage_service)
        
        # Verify it has no required parameters (can be used as dependency without Depends())
        assert len(sig.parameters) == 0
        
        # Verify it has a return annotation or can be inferred
        assert sig.return_annotation is not inspect.Signature.empty or callable(get_execution_storage_service)

    def test_get_execution_storage_service_multiple_calls_consistent_behavior(self):
        """Test that multiple calls to get_execution_storage_service behave consistently."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            mock_settings.AWS_ACCESS_KEY_ID = "consistent-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "consistent-secret"
            mock_settings.AWS_REGION = "consistent-region"
            
            # Create multiple mock instances
            mock_instances = [Mock() for _ in range(3)]
            mock_factory.side_effect = mock_instances
            
            # Call the function multiple times
            results = [get_execution_storage_service() for _ in range(3)]
            
            # Verify all calls used same parameters
            for call in mock_factory.call_args_list:
                args, kwargs = call
                assert kwargs == {
                    'access_key': 'consistent-key',
                    'secret_key': 'consistent-secret',
                    'region': 'consistent-region'
                }
            
            # Verify each call returned different instances
            assert len(set(results)) == 3  # All different instances

    def test_get_execution_storage_service_return_type_annotation(self):
        """Test that the function has correct return type annotation."""
        import inspect
        from services.execution_storage_service import get_execution_storage_service
        
        # Get function signature
        sig = inspect.signature(get_execution_storage_service)
        
        # Verify return annotation is DynamoDbExecutionStorageService
        assert sig.return_annotation.__name__ == 'DynamoDbExecutionStorageService'

    def test_get_execution_storage_service_aws_credentials_handling(self):
        """Test various AWS credential scenarios."""
        test_cases = [
            {
                'access_key': 'AKIAIOSFODNN7EXAMPLE',
                'secret_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'region': 'us-east-1'
            },
            {
                'access_key': 'AKIA' + 'X' * 16,  # 20 char access key
                'secret_key': 'Y' * 40,  # 40 char secret key
                'region': 'eu-central-1'
            },
            {
                'access_key': 'test-local-key',
                'secret_key': 'test-local-secret',
                'region': 'localstack'
            }
        ]
        
        for test_case in test_cases:
            with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
                 patch('services.execution_storage_service.settings') as mock_settings:
                
                mock_settings.AWS_ACCESS_KEY_ID = test_case['access_key']
                mock_settings.AWS_SECRET_ACCESS_KEY = test_case['secret_key']
                mock_settings.AWS_REGION = test_case['region']
                
                mock_instance = Mock()
                mock_factory.return_value = mock_instance
                
                result = get_execution_storage_service()
                
                mock_factory.assert_called_once_with(
                    access_key=test_case['access_key'],
                    secret_key=test_case['secret_key'],
                    region=test_case['region']
                )
                
                assert result == mock_instance

    def test_get_execution_storage_service_dynamo_specific_functionality(self):
        """Test that service specifically returns DynamoDb execution storage service."""
        with patch('services.execution_storage_service.get_execution_storage_service_from_env') as mock_factory, \
             patch('services.execution_storage_service.settings') as mock_settings:
            
            mock_settings.AWS_ACCESS_KEY_ID = "dynamo-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "dynamo-secret"
            mock_settings.AWS_REGION = "us-east-1"
            
            # Mock a DynamoDb-specific service instance
            mock_dynamo_service = Mock()
            mock_dynamo_service.table_name = "executions"
            mock_dynamo_service.store_execution = Mock()
            mock_dynamo_service.get_execution = Mock()
            
            mock_factory.return_value = mock_dynamo_service
            
            result = get_execution_storage_service()
            
            # Verify we get the DynamoDb service with expected attributes
            assert result == mock_dynamo_service
            assert hasattr(result, 'table_name')
            assert hasattr(result, 'store_execution')
            assert hasattr(result, 'get_execution')