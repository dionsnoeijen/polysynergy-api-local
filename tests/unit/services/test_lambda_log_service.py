import pytest
from unittest.mock import patch, Mock
from botocore.exceptions import ClientError
from fastapi import HTTPException
from uuid import uuid4

from services.lambda_log_service import LambdaLogService


@pytest.mark.unit
class TestLambdaLogService:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.version_id = str(uuid4())
        self.mock_settings = Mock()
        self.mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        self.mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        self.mock_settings.AWS_REGION = "us-east-1"
    
    @patch('services.lambda_log_service.boto3.client')
    def test_get_lambda_logs_success(self, mock_boto_client, mock_settings):
        """Test successful lambda logs retrieval."""
        # Mock CloudWatch logs client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock log streams response (same for all variants)
        mock_client.describe_log_streams.return_value = {
            'logStreams': [
                {'logStreamName': 'stream1', 'lastEventTime': 1640995200000}
            ]
        }
        
        # Mock log events response (same for all variants)
        mock_client.get_log_events.return_value = {
            'events': [
                {
                    'timestamp': 1640995200000,
                    'message': '[INFO] Test log message 1'
                },
                {
                    'timestamp': 1640995210000,
                    'message': '[ERROR] Test error message'
                }
            ]
        }
        
        with patch('services.lambda_log_service.settings', mock_settings):
            result = LambdaLogService.get_lambda_logs("test-version-id")
        
        # Should get 6 logs total (2 events × 3 variants)
        assert len(result) == 6
        
        # Check that we have logs from all 3 variants
        variants = {log['variant'] for log in result}
        assert variants == {'mock', 'published', 'config'}
        
        # Check that logs are sorted by timestamp
        timestamps = [log['timestamp'] for log in result]
        assert timestamps == sorted(timestamps)
        
        # Verify each log has the expected structure
        for log in result:
            assert 'function' in log
            assert 'timestamp' in log
            assert 'message' in log
            assert 'variant' in log
        
        # Verify boto3 client was created with correct parameters
        mock_boto_client.assert_called_with(
            "logs",
            aws_access_key_id=mock_settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=mock_settings.AWS_SECRET_ACCESS_KEY,
            region_name=mock_settings.AWS_REGION
        )
    
    @patch('services.lambda_log_service.boto3.client')
    def test_get_lambda_logs_with_after_parameter(self, mock_boto_client, mock_settings):
        """Test lambda logs retrieval with after parameter."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.describe_log_streams.return_value = {
            'logStreams': [
                {'logStreamName': 'stream1', 'lastEventTime': 1640995200000}
            ]
        }
        
        mock_client.get_log_events.return_value = {
            'events': [
                {
                    'timestamp': 1640995220000,
                    'message': '[INFO] Recent log message'
                }
            ]
        }
        
        with patch('services.lambda_log_service.settings', mock_settings):
            result = LambdaLogService.get_lambda_logs("test-version-id", after=1640995210)
        
        # Should get 3 logs (1 event × 3 variants)
        assert len(result) == 3
        assert all(log['message'] == '[INFO] Recent log message' for log in result)
        
        # Verify get_log_events was called with startTime parameter
        # Get the last call (there will be 3 calls for 3 variants)
        call_args = mock_client.get_log_events.call_args
        assert 'startTime' in call_args[1]
        assert call_args[1]['startTime'] == 1640995210 + 1  # Service adds 1 to after value
    
    @patch('services.lambda_log_service.boto3.client')
    def test_get_lambda_logs_no_streams(self, mock_boto_client, mock_settings):
        """Test lambda logs retrieval when no log streams exist."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.describe_log_streams.return_value = {
            'logStreams': []
        }
        
        with patch('services.lambda_log_service.settings', mock_settings):
            result = LambdaLogService.get_lambda_logs("test-version-id")
        
        assert result == []
        # Verify get_log_events was not called since no streams exist
        mock_client.get_log_events.assert_not_called()
    
    @patch('services.lambda_log_service.boto3.client')
    def test_get_lambda_logs_log_group_not_found(self, mock_boto_client, mock_settings):
        """Test lambda logs retrieval when log group doesn't exist."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Add the ResourceNotFoundException to the client's exceptions
        mock_client.exceptions.ResourceNotFoundException = ClientError
        
        # Mock ResourceNotFoundException for log group
        mock_client.describe_log_streams.side_effect = ClientError(
            error_response={'Error': {'Code': 'ResourceNotFoundException'}},
            operation_name='DescribeLogStreams'
        )
        
        with patch('services.lambda_log_service.settings', mock_settings):
            result = LambdaLogService.get_lambda_logs("test-version-id")
        
        # Should return empty list when log group doesn't exist
        assert result == []
    
    @patch('services.lambda_log_service.boto3.client')
    def test_get_lambda_logs_multiple_variants(self, mock_boto_client, mock_settings):
        """Test lambda logs retrieval across multiple log variants."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock different responses for different log groups
        def mock_describe_streams(*args, **kwargs):
            log_group = kwargs.get('logGroupName', '')
            if 'mock' in log_group:
                return {'logStreams': [{'logStreamName': 'mock_stream'}]}
            elif 'published' in log_group:
                return {'logStreams': [{'logStreamName': 'published_stream'}]}
            else:
                return {'logStreams': []}
        
        def mock_get_events(*args, **kwargs):
            log_group = args[0] if args else kwargs.get('logGroupName', '')
            if 'mock' in log_group:
                return {'events': [{'timestamp': 1640995200000, 'message': 'Mock log'}]}
            elif 'published' in log_group:
                return {'events': [{'timestamp': 1640995210000, 'message': 'Published log'}]}
            else:
                return {'events': []}
        
        mock_client.describe_log_streams.side_effect = mock_describe_streams
        mock_client.get_log_events.side_effect = mock_get_events
        
        with patch('services.lambda_log_service.settings', mock_settings):
            result = LambdaLogService.get_lambda_logs("test-version-id")
        
        # Should collect logs from multiple variants
        assert len(result) == 2
        messages = [log['message'] for log in result]
        assert 'Mock log' in messages
        assert 'Published log' in messages
    
    @patch('services.lambda_log_service.boto3.client')
    def test_get_lambda_logs_empty_events(self, mock_boto_client, mock_settings):
        """Test lambda logs retrieval when log streams exist but have no events."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.describe_log_streams.return_value = {
            'logStreams': [
                {'logStreamName': 'stream1', 'lastEventTime': 1640995200000}
            ]
        }
        
        mock_client.get_log_events.return_value = {
            'events': []
        }
        
        with patch('services.lambda_log_service.settings', mock_settings):
            result = LambdaLogService.get_lambda_logs("test-version-id")
        
        assert result == []

    @patch('services.lambda_log_service.boto3.client')
    @patch('services.lambda_log_service.settings')
    def test_get_lambda_logs_complete_workflow(self, mock_settings, mock_boto_client):
        """Test complete lambda logs retrieval workflow with all variants."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful response for all variants
        mock_client.describe_log_streams.return_value = {
            "logStreams": [{"logStreamName": "stream1"}]
        }
        mock_client.get_log_events.return_value = {
            "events": [
                {"timestamp": 1640995200000, "message": "START RequestId"},
                {"timestamp": 1640995210000, "message": "Custom log message"},
                {"timestamp": 1640995220000, "message": "END RequestId"}
            ]
        }
        
        result = LambdaLogService.get_lambda_logs(self.version_id)
        
        # Should have 9 logs (3 events × 3 variants)
        assert len(result) == 9
        
        # Should have all three variants
        variants = set(log["variant"] for log in result)
        assert variants == {"mock", "published", "config"}
        
        # Verify logs are sorted by timestamp
        timestamps = [log["timestamp"] for log in result]
        assert timestamps == sorted(timestamps)

    @patch('services.lambda_log_service.boto3.client')
    @patch('services.lambda_log_service.settings')
    def test_get_lambda_logs_function_name_construction(self, mock_settings, mock_boto_client):
        """Test that function names are constructed correctly for all variants."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.describe_log_streams.return_value = {
            "logStreams": [{"logStreamName": "stream1"}]
        }
        mock_client.get_log_events.return_value = {
            "events": [{"timestamp": 1640995200000, "message": "test message"}]
        }
        
        result = LambdaLogService.get_lambda_logs(self.version_id)
        
        # Verify function names in results
        function_names = [log["function"] for log in result]
        expected_names = [
            f"node_setup_{self.version_id}_mock",
            f"node_setup_{self.version_id}_published",
            f"node_setup_{self.version_id}_config"
        ]
        assert set(function_names) == set(expected_names)

    @patch('services.lambda_log_service.boto3.client')
    @patch('services.lambda_log_service.settings')
    def test_get_lambda_logs_parameters_verification(self, mock_settings, mock_boto_client):
        """Test that AWS API calls use correct parameters."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.describe_log_streams.return_value = {"logStreams": []}
        
        LambdaLogService.get_lambda_logs(self.version_id)
        
        # Verify describe_log_streams was called with correct parameters
        call_args = mock_client.describe_log_streams.call_args_list[0]
        call_kwargs = call_args[1]
        
        assert call_kwargs["orderBy"] == "LastEventTime"
        assert call_kwargs["descending"] is True
        assert call_kwargs["limit"] == 1

    @patch('services.lambda_log_service.boto3.client')
    @patch('services.lambda_log_service.settings')
    def test_get_lambda_logs_boto3_client_creation(self, mock_settings, mock_boto_client):
        """Test that boto3 client is created with correct AWS credentials."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {"logStreams": []}
        
        LambdaLogService.get_lambda_logs(self.version_id)
        
        # Verify boto3 client was created with correct credentials
        mock_boto_client.assert_called_once_with(
            "logs",
            aws_access_key_id=self.mock_settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.mock_settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.mock_settings.AWS_REGION
        )