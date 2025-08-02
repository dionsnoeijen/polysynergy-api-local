import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from services.api_key_service import ApiKeyService
from schemas.api_key import ApiKeyCreateIn, ApiKeyUpdateIn
from models import Project


@pytest.mark.unit
class TestApiKeyService:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.tenant_id = str(uuid4())
        self.project_id = str(uuid4())
        self.key_id = str(uuid4())
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.tenant_id = self.tenant_id
        
        # Mock DynamoDB responses
        self.mock_api_key_item = {
            "PK": f"apikey#{self.tenant_id}#{self.project_id}",
            "SK": self.key_id,
            "key_id": self.key_id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "label": "Test API Key",
            "key": "test-api-key-12345",
            "type": "api_key",
            "created_at": "2024-01-01T00:00:00"
        }
    
    @patch('services.api_key_service.boto3')
    def test_api_key_service_initialization(self, mock_boto3):
        """Test ApiKeyService initialization with proper AWS configuration."""
        mock_resource = Mock()
        mock_table = Mock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_resource
        
        with patch('services.api_key_service.settings') as mock_settings:
            mock_settings.AWS_REGION = "us-east-1"
            mock_settings.AWS_ACCESS_KEY_ID = "test-access-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
            
            service = ApiKeyService()
            
            # Verify DynamoDB resource was created with correct parameters
            mock_boto3.resource.assert_called_once_with(
                "dynamodb",
                region_name="us-east-1",
                aws_access_key_id="test-access-key",
                aws_secret_access_key="test-secret-key"
            )
            
            # Verify table was set correctly
            mock_resource.Table.assert_called_once_with("router_api_keys")
            assert service.table == mock_table
    
    @patch('services.api_key_service.boto3')
    def test_pk_generation(self, mock_boto3):
        """Test primary key generation for DynamoDB."""
        service = ApiKeyService()
        
        pk = service._pk(self.mock_project)
        
        expected_pk = f"apikey#{self.tenant_id}#{self.project_id}"
        assert pk == expected_pk
    
    @patch('services.api_key_service.boto3')
    def test_get_item_by_key_id_found(self, mock_boto3):
        """Test retrieving item by key_id when item exists."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock successful query response
        mock_table.query.return_value = {
            "Items": [self.mock_api_key_item]
        }
        
        service = ApiKeyService()
        result = service._get_item_by_key_id(self.key_id)
        
        assert result == self.mock_api_key_item
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == "gsi_keyid"
        assert call_kwargs["Limit"] == 1
    
    @patch('services.api_key_service.boto3')
    def test_get_item_by_key_id_not_found(self, mock_boto3):
        """Test retrieving item by key_id when item doesn't exist."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock empty query response
        mock_table.query.return_value = {"Items": []}
        
        service = ApiKeyService()
        result = service._get_item_by_key_id(self.key_id)
        
        assert result is None
    
    @patch('services.api_key_service.boto3')
    def test_list_keys_success(self, mock_boto3):
        """Test successful listing of API keys for a project."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock query response with multiple items
        mock_items = [
            {**self.mock_api_key_item, "key_id": str(uuid4()), "label": "Key 1"},
            {**self.mock_api_key_item, "key_id": str(uuid4()), "label": "Key 2"}
        ]
        mock_table.query.return_value = {"Items": mock_items}
        
        service = ApiKeyService()
        result = service.list_keys(self.mock_project)
        
        assert len(result) == 2
        assert result[0].label == "Key 1"
        assert result[1].label == "Key 2"
        
        mock_table.query.assert_called_once()
        call_args = mock_table.query.call_args
        assert call_args[1]["KeyConditionExpression"] is not None
    
    @patch('services.api_key_service.boto3')
    def test_list_keys_empty(self, mock_boto3):
        """Test listing API keys when no keys exist for project."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock empty query response
        mock_table.query.return_value = {"Items": []}
        
        service = ApiKeyService()
        result = service.list_keys(self.mock_project)
        
        assert result == []
    
    @patch('services.api_key_service.boto3')
    def test_get_one_success(self, mock_boto3):
        """Test successful retrieval of a single API key."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {"Items": [self.mock_api_key_item]}
        
        service = ApiKeyService()
        result = service.get_one(self.key_id, self.mock_project)
        
        assert result.key_id == self.key_id
        assert result.label == "Test API Key"
        assert result.project_id == self.project_id
    
    @patch('services.api_key_service.boto3')
    def test_get_one_not_found(self, mock_boto3):
        """Test get_one when API key doesn't exist."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {"Items": []}
        
        service = ApiKeyService()
        
        with pytest.raises(ValueError, match="API key not found or doesn't belong to this project"):
            service.get_one(self.key_id, self.mock_project)
    
    @patch('services.api_key_service.boto3')
    def test_get_one_wrong_project(self, mock_boto3):
        """Test get_one when API key belongs to different project."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock item with different project_id
        wrong_project_item = {**self.mock_api_key_item, "project_id": str(uuid4())}
        mock_table.query.return_value = {"Items": [wrong_project_item]}
        
        service = ApiKeyService()
        
        with pytest.raises(ValueError, match="API key not found or doesn't belong to this project"):
            service.get_one(self.key_id, self.mock_project)
    
    @patch('services.api_key_service.uuid.uuid4')
    @patch('services.api_key_service.datetime')
    @patch('services.api_key_service.boto3')
    def test_create_success(self, mock_boto3, mock_datetime, mock_uuid4):
        """Test successful API key creation."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock UUID and datetime
        mock_uuid4.return_value = Mock()
        mock_uuid4.return_value.__str__ = Mock(return_value=self.key_id)
        mock_datetime.utcnow.return_value.isoformat.return_value = "2024-01-01T00:00:00"
        
        service = ApiKeyService()
        create_data = ApiKeyCreateIn(label="New API Key", key="new-api-key-12345")
        
        result = service.create(create_data, self.mock_project)
        
        # Verify the result
        assert result.key_id == self.key_id
        assert result.label == "New API Key"
        assert result.key == "new-api-key-12345"
        assert result.project_id == self.project_id
        
        # Verify DynamoDB put_item was called
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args[1]["Item"]
        assert item["label"] == "New API Key"
        assert item["key"] == "new-api-key-12345"
        assert item["key_id"] == self.key_id
    
    @patch('services.api_key_service.boto3')
    def test_update_success(self, mock_boto3):
        """Test successful API key update."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock _get_item_by_key_id to return existing item
        mock_table.query.return_value = {"Items": [self.mock_api_key_item]}
        
        service = ApiKeyService()
        update_data = ApiKeyUpdateIn(label="Updated API Key")
        
        result = service.update(self.key_id, update_data, self.mock_project)
        
        # Verify the result
        assert result.key_id == self.key_id
        assert result.label == "Updated API Key"
        
        # Verify DynamoDB update_item was called
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args
        assert call_args[1]["UpdateExpression"] == "SET label = :label"
        assert call_args[1]["ExpressionAttributeValues"][":label"] == "Updated API Key"
    
    @patch('services.api_key_service.boto3')
    def test_update_not_found(self, mock_boto3):
        """Test update when API key doesn't exist."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {"Items": []}
        
        service = ApiKeyService()
        update_data = ApiKeyUpdateIn(label="Updated API Key")
        
        with pytest.raises(ValueError, match="API key not found or doesn't belong to this project"):
            service.update(self.key_id, update_data, self.mock_project)
    
    @patch('services.api_key_service.boto3')
    def test_delete_success(self, mock_boto3):
        """Test successful API key deletion."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock _get_item_by_key_id to return existing item
        mock_table.query.return_value = {"Items": [self.mock_api_key_item]}
        
        service = ApiKeyService()
        service.delete(self.key_id, self.mock_project)
        
        # Verify DynamoDB delete_item was called
        mock_table.delete_item.assert_called_once()
        call_args = mock_table.delete_item.call_args
        expected_key = {"PK": self.mock_api_key_item["PK"], "SK": self.mock_api_key_item["SK"]}
        assert call_args[1]["Key"] == expected_key
    
    @patch('services.api_key_service.boto3')
    def test_delete_not_found(self, mock_boto3):
        """Test delete when API key doesn't exist."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.query.return_value = {"Items": []}
        
        service = ApiKeyService()
        
        with pytest.raises(ValueError, match="API key not found or doesn't belong to this project"):
            service.delete(self.key_id, self.mock_project)
    
    @patch('services.api_key_service.boto3')
    def test_assign_keys_to_route(self, mock_boto3):
        """Test API key assignment to route (currently stub implementation)."""
        service = ApiKeyService()
        
        route_id = str(uuid4())
        api_key_refs = ["key1", "key2", "key3"]
        
        result = service.assign_keys_to_route(route_id, api_key_refs, self.mock_project)
        
        # Verify the stub implementation returns expected format
        assert result["route_id"] == route_id
        assert result["api_keys_assigned"] == api_key_refs
    
    @patch('services.api_key_service.boto3')
    def test_dynamo_query_error_handling(self, mock_boto3):
        """Test handling of DynamoDB query errors."""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock DynamoDB exception
        from botocore.exceptions import ClientError
        mock_table.query.side_effect = ClientError(
            error_response={'Error': {'Code': 'ResourceNotFoundException'}}, 
            operation_name='Query'
        )
        
        service = ApiKeyService()
        
        # The service should let the exception bubble up
        with pytest.raises(ClientError):
            service.list_keys(self.mock_project)