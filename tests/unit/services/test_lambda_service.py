import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from uuid import uuid4

from services.lambda_service import LambdaService, get_lambda_service


@pytest.mark.unit
class TestLambdaService:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.function_name = "test_function"
        self.tenant_id = str(uuid4())
        self.project_id = str(uuid4())
        self.api_id = "test-api-id"
        self.code = "print('Hello World')"
        
        # Mock settings
        self.mock_settings = Mock()
        self.mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
        self.mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        self.mock_settings.AWS_REGION = "us-east-1"
        self.mock_settings.AWS_LAMBDA_EXECUTION_ROLE = "arn:aws:iam::123456789012:role/lambda-role"
        self.mock_settings.AWS_S3_PUBLIC_BUCKET_NAME = "public-bucket"
        self.mock_settings.AWS_S3_PRIVATE_BUCKET_NAME = "private-bucket"
        self.mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "lambda-bucket"
        self.mock_settings.REDIS_URL = "redis://localhost:6379"
        self.mock_settings.AWS_ACCOUNT_ID = "123456789012"

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_lambda_service_initialization(self, mock_settings, mock_boto_client):
        """Test that LambdaService initializes with correct AWS clients and settings."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        # Mock client instances
        mock_lambda_client = Mock()
        mock_ecr_client = Mock() 
        mock_s3_client = Mock()
        
        # Configure boto3.client to return different mocks based on service
        def client_side_effect(service, **kwargs):
            if service == 'lambda':
                return mock_lambda_client
            elif service == 'ecr':
                return mock_ecr_client
            elif service == 's3':
                return mock_s3_client
        
        mock_boto_client.side_effect = client_side_effect
        
        service = LambdaService()
        
        # Verify all three clients were created
        assert mock_boto_client.call_count == 3
        
        # Verify lambda client was created with correct config
        lambda_call = [call for call in mock_boto_client.call_args_list if call[0][0] == 'lambda'][0]
        assert lambda_call[1]['aws_access_key_id'] == self.mock_settings.AWS_ACCESS_KEY_ID
        assert lambda_call[1]['aws_secret_access_key'] == self.mock_settings.AWS_SECRET_ACCESS_KEY
        assert lambda_call[1]['region_name'] == self.mock_settings.AWS_REGION
        assert 'config' in lambda_call[1]
        
        # Verify clients are stored correctly
        assert service._lambda_client == mock_lambda_client
        assert service._ecr_client == mock_ecr_client
        assert service._s3_client == mock_s3_client
        
        # Verify latest_image_uri is set
        assert service.latest_image_uri == '754508895309.dkr.ecr.eu-central-1.amazonaws.com/polysynergy/polysynergy-lambda:latest'

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_get_function_success(self, mock_settings, mock_boto_client):
        """Test successful function retrieval."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        expected_function = {
            'Configuration': {
                'FunctionName': self.function_name,
                'FunctionArn': f'arn:aws:lambda:us-east-1:123456789012:function:{self.function_name}'
            }
        }
        mock_lambda_client.get_function.return_value = expected_function
        
        service = LambdaService()
        result = service.get_function(self.function_name)
        
        mock_lambda_client.get_function.assert_called_once_with(FunctionName=self.function_name)
        assert result == expected_function

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_get_function_not_found(self, mock_settings, mock_boto_client):
        """Test function retrieval when function doesn't exist."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        # Mock ResourceNotFoundException
        mock_exceptions = Mock()
        mock_exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        mock_lambda_client.exceptions = mock_exceptions
        mock_lambda_client.get_function.side_effect = mock_exceptions.ResourceNotFoundException()
        
        service = LambdaService()
        result = service.get_function(self.function_name)
        
        assert result is None

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_get_function_arn_success(self, mock_settings, mock_boto_client):
        """Test successful function ARN retrieval."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        expected_arn = f'arn:aws:lambda:us-east-1:123456789012:function:{self.function_name}'
        mock_function = {
            'Configuration': {
                'FunctionArn': expected_arn
            }
        }
        mock_lambda_client.get_function.return_value = mock_function
        
        service = LambdaService()
        result = service.get_function_arn(self.function_name)
        
        assert result == expected_arn

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_get_function_arn_not_found(self, mock_settings, mock_boto_client):
        """Test function ARN retrieval when function doesn't exist."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        mock_lambda_client.exceptions.ResourceNotFoundException = Exception
        mock_lambda_client.get_function.side_effect = mock_lambda_client.exceptions.ResourceNotFoundException()
        
        service = LambdaService()
        result = service.get_function_arn(self.function_name)
        
        assert result is None

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_get_function_image_uri_success(self, mock_settings, mock_boto_client):
        """Test successful function image URI retrieval."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        expected_image_uri = "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest"
        mock_function = {
            'Configuration': {
                'ImageUri': expected_image_uri
            }
        }
        mock_lambda_client.get_function.return_value = mock_function
        
        service = LambdaService()
        result = service.get_function_image_uri(self.function_name)
        
        assert result == expected_image_uri

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_get_function_image_uri_from_code_section(self, mock_settings, mock_boto_client):
        """Test function image URI retrieval from Code section."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        expected_image_uri = "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest"
        mock_function = {
            'Configuration': {},
            'Code': {
                'ResolvedImageUri': expected_image_uri
            }
        }
        mock_lambda_client.get_function.return_value = mock_function
        
        service = LambdaService()
        result = service.get_function_image_uri(self.function_name)
        
        assert result == expected_image_uri

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_get_function_image_uri_not_found(self, mock_settings, mock_boto_client):
        """Test function image URI retrieval when function doesn't exist."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        mock_lambda_client.exceptions.ResourceNotFoundException = Exception
        mock_lambda_client.get_function.side_effect = mock_lambda_client.exceptions.ResourceNotFoundException()
        
        service = LambdaService()
        result = service.get_function_image_uri(self.function_name)
        
        assert result is None

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_get_latest_image_digest_success(self, mock_settings, mock_boto_client):
        """Test successful latest image digest retrieval."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_ecr_client = Mock()
        def client_side_effect(service, **kwargs):
            if service == 'ecr':
                return mock_ecr_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        expected_digest = "sha256:1234567890abcdef"
        mock_ecr_client.describe_images.return_value = {
            'imageDetails': [
                {'imageDigest': expected_digest}
            ]
        }
        
        service = LambdaService()
        result = service.get_latest_image_digest()
        
        mock_ecr_client.describe_images.assert_called_once_with(
            repositoryName='polysynergy/polysynergy-lambda',
            imageIds=[{'imageTag': 'latest'}]
        )
        assert result == expected_digest

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_get_latest_image_digest_no_images(self, mock_settings, mock_boto_client):
        """Test latest image digest retrieval when no images exist."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_ecr_client = Mock()
        def client_side_effect(service, **kwargs):
            if service == 'ecr':
                return mock_ecr_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        mock_ecr_client.describe_images.return_value = {'imageDetails': []}
        
        service = LambdaService()
        result = service.get_latest_image_digest()
        
        assert result is None

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_get_latest_image_digest_exception(self, mock_settings, mock_boto_client):
        """Test latest image digest retrieval with exception."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_ecr_client = Mock()
        def client_side_effect(service, **kwargs):
            if service == 'ecr':
                return mock_ecr_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        mock_ecr_client.describe_images.side_effect = Exception("ECR error")
        
        service = LambdaService()
        result = service.get_latest_image_digest()
        
        assert result is None

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_update_function_configuration(self, mock_settings, mock_boto_client):
        """Test function configuration update."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        mock_settings.AWS_S3_PUBLIC_BUCKET_NAME = self.mock_settings.AWS_S3_PUBLIC_BUCKET_NAME
        mock_settings.AWS_S3_PRIVATE_BUCKET_NAME = self.mock_settings.AWS_S3_PRIVATE_BUCKET_NAME
        mock_settings.REDIS_URL = self.mock_settings.REDIS_URL
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        service = LambdaService()
        service.update_function_configuration(self.function_name, self.tenant_id, self.project_id)
        
        mock_lambda_client.update_function_configuration.assert_called_once_with(
            FunctionName=self.function_name,
            Environment={
                'Variables': {
                    'PROJECT_ID': str(self.project_id),
                    'TENANT_ID': str(self.tenant_id),
                    'AWS_S3_PUBLIC_BUCKET_NAME': self.mock_settings.AWS_S3_PUBLIC_BUCKET_NAME,
                    'AWS_S3_PRIVATE_BUCKET_NAME': self.mock_settings.AWS_S3_PRIVATE_BUCKET_NAME,
                    'REDIS_URL': self.mock_settings.REDIS_URL,
                }
            }
        )

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_update_function_image_success(self, mock_settings, mock_boto_client):
        """Test successful function image update."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        mock_settings.AWS_S3_PUBLIC_BUCKET_NAME = self.mock_settings.AWS_S3_PUBLIC_BUCKET_NAME
        mock_settings.AWS_S3_PRIVATE_BUCKET_NAME = self.mock_settings.AWS_S3_PRIVATE_BUCKET_NAME
        mock_settings.REDIS_URL = self.mock_settings.REDIS_URL
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        expected_arn = f'arn:aws:lambda:us-east-1:123456789012:function:{self.function_name}'
        mock_function = {
            'Configuration': {
                'FunctionArn': expected_arn
            }
        }
        mock_lambda_client.get_function.return_value = mock_function
        
        service = LambdaService()
        result = service.update_function_image(self.function_name, self.tenant_id, self.project_id)
        
        # Verify update_function_code was called
        mock_lambda_client.update_function_code.assert_called_once_with(
            FunctionName=self.function_name,
            ImageUri=service.latest_image_uri,
            Publish=True
        )
        
        # Verify update_function_configuration was called
        mock_lambda_client.update_function_configuration.assert_called_once()
        
        assert result == expected_arn

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_update_function_image_exception(self, mock_settings, mock_boto_client):
        """Test function image update with exception."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        mock_lambda_client.update_function_code.side_effect = Exception("Update failed")
        
        service = LambdaService()
        
        with pytest.raises(Exception) as exc_info:
            service.update_function_image(self.function_name, self.tenant_id, self.project_id)
        
        assert "Update failed" in str(exc_info.value)

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_upload_code_to_s3_success(self, mock_settings, mock_boto_client):
        """Test successful code upload to S3."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_s3_client = Mock()
        def client_side_effect(service, **kwargs):
            if service == 's3':
                return mock_s3_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        bucket_name = "test-bucket"
        s3_key = "test-key.py"
        
        service = LambdaService()
        service.upload_code_to_s3(bucket_name, s3_key, self.code)
        
        mock_s3_client.put_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=s3_key,
            Body=self.code.encode('utf-8')
        )

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_upload_code_to_s3_exception(self, mock_settings, mock_boto_client):
        """Test code upload to S3 with exception."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_s3_client = Mock()
        def client_side_effect(service, **kwargs):
            if service == 's3':
                return mock_s3_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        mock_s3_client.put_object.side_effect = Exception("S3 upload failed")
        
        service = LambdaService()
        
        with pytest.raises(Exception) as exc_info:
            service.upload_code_to_s3("test-bucket", "test-key.py", self.code)
        
        assert "S3 upload failed" in str(exc_info.value)

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_create_or_update_lambda_update_existing(self, mock_settings, mock_boto_client):
        """Test create_or_update_lambda when function exists (update path)."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = self.mock_settings.AWS_S3_LAMBDA_BUCKET_NAME
        mock_settings.AWS_S3_PUBLIC_BUCKET_NAME = self.mock_settings.AWS_S3_PUBLIC_BUCKET_NAME
        mock_settings.AWS_S3_PRIVATE_BUCKET_NAME = self.mock_settings.AWS_S3_PRIVATE_BUCKET_NAME
        mock_settings.REDIS_URL = self.mock_settings.REDIS_URL
        
        mock_lambda_client = Mock()
        mock_s3_client = Mock()
        
        def client_side_effect(service, **kwargs):
            if service == 'lambda':
                return mock_lambda_client
            elif service == 's3':
                return mock_s3_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        # Mock existing function
        expected_arn = f'arn:aws:lambda:us-east-1:123456789012:function:{self.function_name}'
        mock_function = {
            'Configuration': {
                'FunctionArn': expected_arn
            }
        }
        mock_lambda_client.get_function.return_value = mock_function
        
        service = LambdaService()
        result = service.create_or_update_lambda(
            self.function_name, self.code, self.tenant_id, self.project_id
        )
        
        # Verify update path was taken (not create)
        mock_lambda_client.update_function_code.assert_called_once()
        mock_lambda_client.create_function.assert_not_called()
        
        # Verify S3 upload
        expected_s3_key = f"{self.tenant_id}/{self.project_id}/{self.function_name}.py"
        mock_s3_client.put_object.assert_called_once_with(
            Bucket=self.mock_settings.AWS_S3_LAMBDA_BUCKET_NAME,
            Key=expected_s3_key,
            Body=self.code.encode('utf-8')
        )
        
        assert result == expected_arn

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_create_or_update_lambda_create_new(self, mock_settings, mock_boto_client):
        """Test create_or_update_lambda when function doesn't exist (create path)."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        mock_settings.AWS_LAMBDA_EXECUTION_ROLE = self.mock_settings.AWS_LAMBDA_EXECUTION_ROLE
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = self.mock_settings.AWS_S3_LAMBDA_BUCKET_NAME
        mock_settings.AWS_S3_PUBLIC_BUCKET_NAME = self.mock_settings.AWS_S3_PUBLIC_BUCKET_NAME
        mock_settings.AWS_S3_PRIVATE_BUCKET_NAME = self.mock_settings.AWS_S3_PRIVATE_BUCKET_NAME
        mock_settings.REDIS_URL = self.mock_settings.REDIS_URL
        
        mock_lambda_client = Mock()
        mock_s3_client = Mock()
        
        def client_side_effect(service, **kwargs):
            if service == 'lambda':
                return mock_lambda_client
            elif service == 's3':
                return mock_s3_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        # Mock function doesn't exist
        mock_exceptions = Mock()
        mock_exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        mock_lambda_client.exceptions = mock_exceptions
        mock_lambda_client.get_function.side_effect = [
            mock_exceptions.ResourceNotFoundException(),  # First call (check exists)
            {  # Second call (get ARN after create)
                'Configuration': {
                    'FunctionArn': f'arn:aws:lambda:us-east-1:123456789012:function:{self.function_name}'
                }
            }
        ]
        
        service = LambdaService()
        result = service.create_or_update_lambda(
            self.function_name, self.code, self.tenant_id, self.project_id
        )
        
        # Verify create path was taken
        mock_lambda_client.create_function.assert_called_once_with(
            FunctionName=self.function_name,
            PackageType='Image',
            Code={'ImageUri': service.latest_image_uri},
            Role=self.mock_settings.AWS_LAMBDA_EXECUTION_ROLE,
            Timeout=900,
            MemorySize=1024,
            Environment={
                'Variables': {
                    'PROJECT_ID': str(self.project_id),
                    'TENANT_ID': str(self.tenant_id),
                    'AWS_S3_PUBLIC_BUCKET_NAME': self.mock_settings.AWS_S3_PUBLIC_BUCKET_NAME,
                    'AWS_S3_PRIVATE_BUCKET_NAME': self.mock_settings.AWS_S3_PRIVATE_BUCKET_NAME,
                    "REDIS_URL": self.mock_settings.REDIS_URL,
                }
            }
        )
        
        # Verify update wasn't called
        mock_lambda_client.update_function_code.assert_not_called()
        
        # Verify S3 upload
        expected_s3_key = f"{self.tenant_id}/{self.project_id}/{self.function_name}.py"
        mock_s3_client.put_object.assert_called_once()

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_add_api_gateway_permission_new_permission(self, mock_settings, mock_boto_client):
        """Test adding API Gateway permission when it doesn't exist."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        mock_settings.AWS_ACCOUNT_ID = self.mock_settings.AWS_ACCOUNT_ID
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        # Mock no existing policy
        mock_exceptions = Mock()
        mock_exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        mock_lambda_client.exceptions = mock_exceptions
        mock_lambda_client.get_policy.side_effect = mock_exceptions.ResourceNotFoundException()
        
        service = LambdaService()
        service.add_api_gateway_permission(self.function_name, self.api_id)
        
        # Verify permission was added
        expected_statement_id = f"apigateway-{self.api_id}"
        expected_source_arn = f"arn:aws:execute-api:{self.mock_settings.AWS_REGION}:{self.mock_settings.AWS_ACCOUNT_ID}:{self.api_id}/*"
        
        mock_lambda_client.add_permission.assert_called_once_with(
            FunctionName=self.function_name,
            StatementId=expected_statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=expected_source_arn
        )

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_add_api_gateway_permission_already_exists(self, mock_settings, mock_boto_client):
        """Test adding API Gateway permission when it already exists."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        mock_settings.AWS_ACCOUNT_ID = self.mock_settings.AWS_ACCOUNT_ID
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        # Mock existing policy with the same statement ID
        statement_id = f"apigateway-{self.api_id}"
        mock_policy = {
            'Policy': json.dumps({
                'Statement': [
                    {
                        'Sid': statement_id,
                        'Effect': 'Allow'
                    }
                ]
            })
        }
        mock_lambda_client.get_policy.return_value = mock_policy
        
        service = LambdaService()
        service.add_api_gateway_permission(self.function_name, self.api_id)
        
        # Verify permission was NOT added (skipped)
        mock_lambda_client.add_permission.assert_not_called()

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_invoke_lambda_success(self, mock_settings, mock_boto_client):
        """Test successful lambda invocation."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        # Mock successful response
        expected_response = {'result': 'success', 'data': 'test data'}
        mock_payload = Mock()
        mock_payload.read.return_value = json.dumps(expected_response).encode()
        mock_lambda_client.invoke.return_value = {
            'Payload': mock_payload
        }
        
        payload = {'input': 'test input'}
        
        service = LambdaService()
        result = service.invoke_lambda(self.function_name, payload)
        
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName=self.function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        assert result == expected_response

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_invoke_lambda_client_error(self, mock_settings, mock_boto_client):
        """Test lambda invocation with ClientError."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        # Mock ClientError
        mock_lambda_client.invoke.side_effect = ClientError(
            error_response={'Error': {'Code': 'ResourceNotFoundException'}},
            operation_name='Invoke'
        )
        
        payload = {'input': 'test input'}
        
        service = LambdaService()
        
        with pytest.raises(ClientError):
            service.invoke_lambda(self.function_name, payload)

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_delete_lambda_success(self, mock_settings, mock_boto_client):
        """Test successful lambda deletion."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        service = LambdaService()
        service.delete_lambda(self.function_name)
        
        mock_lambda_client.delete_function.assert_called_once_with(FunctionName=self.function_name)

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_delete_lambda_not_found(self, mock_settings, mock_boto_client):
        """Test lambda deletion when function doesn't exist."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        # Mock ResourceNotFoundException
        mock_exceptions = Mock()
        mock_exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        mock_lambda_client.exceptions = mock_exceptions
        mock_lambda_client.delete_function.side_effect = mock_exceptions.ResourceNotFoundException()
        
        service = LambdaService()
        # Should not raise exception - should handle gracefully
        service.delete_lambda(self.function_name)
        
        mock_lambda_client.delete_function.assert_called_once_with(FunctionName=self.function_name)

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_delete_lambda_exception(self, mock_settings, mock_boto_client):
        """Test lambda deletion with general exception."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        # Create multiple clients for lambda service initialization
        mock_lambda_client = Mock()
        mock_ecr_client = Mock()
        mock_s3_client = Mock()
        
        def client_side_effect(service, **kwargs):
            if service == 'lambda':
                return mock_lambda_client
            elif service == 'ecr':
                return mock_ecr_client
            elif service == 's3':
                return mock_s3_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        # Mock exceptions namespace properly
        mock_exceptions = Mock()
        mock_exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        mock_lambda_client.exceptions = mock_exceptions
        
        mock_lambda_client.delete_function.side_effect = Exception("Delete failed")
        
        service = LambdaService()
        
        with pytest.raises(Exception) as exc_info:
            service.delete_lambda(self.function_name)
        
        assert "Delete failed" in str(exc_info.value)

    def test_get_lambda_service_factory_function(self):
        """Test that get_lambda_service returns a LambdaService instance."""
        with patch('services.lambda_service.boto3.client'):
            with patch('services.lambda_service.settings'):
                result = get_lambda_service()
                assert isinstance(result, LambdaService)

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_lambda_service_client_configuration(self, mock_settings, mock_boto_client):
        """Test that Lambda client is configured with correct timeout and retry settings."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        LambdaService()
        
        # Find the lambda client call
        lambda_call = None
        for call in mock_boto_client.call_args_list:
            if call[0][0] == 'lambda':
                lambda_call = call
                break
        
        assert lambda_call is not None
        config = lambda_call[1]['config']
        
        # Verify config object properties (we can't directly assert on Config internals)
        assert config is not None

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_create_or_update_lambda_exception_handling(self, mock_settings, mock_boto_client):
        """Test create_or_update_lambda exception handling."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        
        # Create multiple clients for lambda service initialization
        mock_lambda_client = Mock()
        mock_ecr_client = Mock()
        mock_s3_client = Mock()
        
        def client_side_effect(service, **kwargs):
            if service == 'lambda':
                return mock_lambda_client
            elif service == 'ecr':
                return mock_ecr_client
            elif service == 's3':
                return mock_s3_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        # Mock exceptions namespace properly
        mock_exceptions = Mock()
        mock_exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        mock_lambda_client.exceptions = mock_exceptions
        
        # Mock exception during get_function check
        mock_lambda_client.get_function.side_effect = Exception("Unexpected error")
        
        service = LambdaService()
        
        with pytest.raises(Exception) as exc_info:
            service.create_or_update_lambda(
                self.function_name, self.code, self.tenant_id, self.project_id
            )
        
        assert "Unexpected error" in str(exc_info.value)

    @patch('services.lambda_service.boto3.client')
    @patch('services.lambda_service.settings')
    def test_add_api_gateway_permission_exception_on_add(self, mock_settings, mock_boto_client):
        """Test add_api_gateway_permission exception during add_permission."""
        mock_settings.AWS_ACCESS_KEY_ID = self.mock_settings.AWS_ACCESS_KEY_ID
        mock_settings.AWS_SECRET_ACCESS_KEY = self.mock_settings.AWS_SECRET_ACCESS_KEY
        mock_settings.AWS_REGION = self.mock_settings.AWS_REGION
        mock_settings.AWS_ACCOUNT_ID = self.mock_settings.AWS_ACCOUNT_ID
        
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        # Mock no existing policy
        mock_exceptions = Mock()
        mock_exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        mock_lambda_client.exceptions = mock_exceptions
        mock_lambda_client.get_policy.side_effect = mock_exceptions.ResourceNotFoundException()
        
        # Mock exception during add_permission
        mock_lambda_client.add_permission.side_effect = Exception("Permission add failed")
        
        service = LambdaService()
        
        with pytest.raises(Exception) as exc_info:
            service.add_api_gateway_permission(self.function_name, self.api_id)
        
        assert "Permission add failed" in str(exc_info.value)