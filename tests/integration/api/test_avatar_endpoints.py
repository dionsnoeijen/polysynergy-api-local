import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from uuid import uuid4

from models import Account, Membership


@pytest.mark.integration
class TestAvatarEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.node_id = str(uuid4())
        self.tenant_id = str(uuid4())
        self.account_id = str(uuid4())
        
        # Mock membership
        self.mock_membership = Mock(spec=Membership)
        self.mock_membership.tenant_id = self.tenant_id
        
        # Mock account with membership
        self.mock_account = Mock(spec=Account)
        self.mock_account.id = self.account_id
        self.mock_account.memberships = [self.mock_membership]
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.s3_service.get_s3_service')
    @patch('services.avatar_service.AvatarService.generate_and_upload')
    def test_generate_avatar_success(self, mock_generate_upload, mock_get_s3_service, mock_get_account, client: TestClient):
        """Test successful avatar generation."""
        # Mock authentication
        mock_get_account.return_value = self.mock_account
        
        # Mock S3 service
        mock_s3_service = Mock()
        mock_get_s3_service.return_value = mock_s3_service
        
        # Mock avatar generation
        expected_url = f"https://s3.amazonaws.com/bucket/avatars/{self.node_id}.png"
        mock_generate_upload.return_value = expected_url
        
        payload = {
            "name": "TestBot",
            "instructions": "A helpful AI assistant for testing"
        }
        
        response = client.post(f"/api/v1/avatars/{self.node_id}/", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == expected_url
        
        # Verify service calls
        mock_get_s3_service.assert_called_once_with(tenant_id=self.tenant_id, public=True)
        mock_generate_upload.assert_called_once_with(
            node_id=self.node_id,
            name="TestBot",
            instructions="A helpful AI assistant for testing",
            account=self.mock_account,
            s3_service=mock_s3_service
        )
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.s3_service.get_s3_service')
    @patch('services.avatar_service.AvatarService.generate_and_upload')
    def test_generate_avatar_minimal_payload(self, mock_generate_upload, mock_get_s3_service, mock_get_account, client: TestClient):
        """Test avatar generation with minimal request data."""
        mock_get_account.return_value = self.mock_account
        mock_s3_service = Mock()
        mock_get_s3_service.return_value = mock_s3_service
        
        expected_url = f"https://s3.amazonaws.com/bucket/avatars/{self.node_id}.png"
        mock_generate_upload.return_value = expected_url
        
        # Empty payload (name and instructions are optional)
        payload = {}
        
        response = client.post(f"/api/v1/avatars/{self.node_id}/", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == expected_url
        
        mock_generate_upload.assert_called_once_with(
            node_id=self.node_id,
            name=None,
            instructions=None,
            account=self.mock_account,
            s3_service=mock_s3_service
        )
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.s3_service.get_s3_service')
    @patch('services.avatar_service.AvatarService.generate_and_upload')
    def test_generate_avatar_only_name(self, mock_generate_upload, mock_get_s3_service, mock_get_account, client: TestClient):
        """Test avatar generation with only name provided."""
        mock_get_account.return_value = self.mock_account
        mock_s3_service = Mock()
        mock_get_s3_service.return_value = mock_s3_service
        
        expected_url = f"https://s3.amazonaws.com/bucket/avatars/{self.node_id}.png"
        mock_generate_upload.return_value = expected_url
        
        payload = {
            "name": "DataAnalyzer"
        }
        
        response = client.post(f"/api/v1/avatars/{self.node_id}/", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == expected_url
        
        mock_generate_upload.assert_called_once_with(
            node_id=self.node_id,
            name="DataAnalyzer",
            instructions=None,
            account=self.mock_account,
            s3_service=mock_s3_service
        )
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.s3_service.get_s3_service')
    @patch('services.avatar_service.AvatarService.generate_and_upload')
    def test_generate_avatar_only_instructions(self, mock_generate_upload, mock_get_s3_service, mock_get_account, client: TestClient):
        """Test avatar generation with only instructions provided."""
        mock_get_account.return_value = self.mock_account
        mock_s3_service = Mock()
        mock_get_s3_service.return_value = mock_s3_service
        
        expected_url = f"https://s3.amazonaws.com/bucket/avatars/{self.node_id}.png"
        mock_generate_upload.return_value = expected_url
        
        payload = {
            "instructions": "Specializes in financial data analysis and reporting"
        }
        
        response = client.post(f"/api/v1/avatars/{self.node_id}/", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == expected_url
        
        mock_generate_upload.assert_called_once_with(
            node_id=self.node_id,
            name=None,
            instructions="Specializes in financial data analysis and reporting",
            account=self.mock_account,
            s3_service=mock_s3_service
        )
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.s3_service.get_s3_service')
    @patch('services.avatar_service.AvatarService.generate_and_upload')
    def test_generate_avatar_value_error(self, mock_generate_upload, mock_get_s3_service, mock_get_account, client: TestClient):
        """Test avatar generation when service raises ValueError."""
        mock_get_account.return_value = self.mock_account
        mock_s3_service = Mock()
        mock_get_s3_service.return_value = mock_s3_service
        
        # Mock service to raise ValueError
        mock_generate_upload.side_effect = ValueError("No tenants available for this user")
        
        payload = {
            "name": "TestBot",
            "instructions": "Test instructions"
        }
        
        response = client.post(f"/api/v1/avatars/{self.node_id}/", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "No tenants available for this user"
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.s3_service.get_s3_service')
    @patch('services.avatar_service.AvatarService.generate_and_upload')
    def test_generate_avatar_generic_error(self, mock_generate_upload, mock_get_s3_service, mock_get_account, client: TestClient):
        """Test avatar generation when service raises generic exception."""
        mock_get_account.return_value = self.mock_account
        mock_s3_service = Mock()
        mock_get_s3_service.return_value = mock_s3_service
        
        # Mock service to raise generic exception
        mock_generate_upload.side_effect = Exception("OpenAI API error")
        
        payload = {
            "name": "TestBot",
            "instructions": "Test instructions"
        }
        
        response = client.post(f"/api/v1/avatars/{self.node_id}/", json=payload)
        
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "OpenAI API error"
    
    @patch('utils.get_current_account.get_current_account')
    def test_generate_avatar_invalid_node_id(self, mock_get_account, client: TestClient):
        """Test avatar generation with invalid node_id format."""
        mock_get_account.return_value = self.mock_account
        
        # Invalid UUID format
        invalid_node_id = "not-a-valid-uuid"
        
        payload = {
            "name": "TestBot",
            "instructions": "Test instructions"
        }
        
        response = client.post(f"/api/v1/avatars/{invalid_node_id}/", json=payload)
        
        # FastAPI will return 422 for invalid UUID format
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.s3_service.get_s3_service')
    @patch('services.avatar_service.AvatarService.generate_and_upload')
    def test_generate_avatar_long_strings(self, mock_generate_upload, mock_get_s3_service, mock_get_account, client: TestClient):
        """Test avatar generation with long name and instructions."""
        mock_get_account.return_value = self.mock_account
        mock_s3_service = Mock()
        mock_get_s3_service.return_value = mock_s3_service
        
        expected_url = f"https://s3.amazonaws.com/bucket/avatars/{self.node_id}.png"
        mock_generate_upload.return_value = expected_url
        
        # Long strings to test handling
        long_name = "A" * 500
        long_instructions = "This is a very detailed instruction set " * 50
        
        payload = {
            "name": long_name,
            "instructions": long_instructions
        }
        
        response = client.post(f"/api/v1/avatars/{self.node_id}/", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == expected_url
        
        mock_generate_upload.assert_called_once_with(
            node_id=self.node_id,
            name=long_name,
            instructions=long_instructions,
            account=self.mock_account,
            s3_service=mock_s3_service
        )
    
    def test_generate_avatar_no_authentication(self, client: TestClient):
        """Test avatar generation without authentication."""
        payload = {
            "name": "TestBot",
            "instructions": "Test instructions"
        }
        
        response = client.post(f"/api/v1/avatars/{self.node_id}/", json=payload)
        
        # Should return 401 unauthorized without proper authentication
        assert response.status_code == 401