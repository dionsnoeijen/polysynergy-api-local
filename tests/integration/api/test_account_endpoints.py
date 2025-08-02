import uuid
import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import Account, Membership, Tenant


@pytest.mark.integration
class TestAccountEndpoints:
    
    @patch('services.account_service.AccountService._update_cognito_user')
    @patch('services.account_service.AccountService._cognito_client')
    def test_create_account_success(self, mock_cognito_client, mock_update_cognito, client: TestClient):
        """Test successful account creation."""
        payload = {
            "tenant_name": "Test Company",
            "cognito_id": "test-cognito-id",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com"
        }
        
        response = client.post("/api/v1/account/", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["email"] == "john@example.com"
        assert data["active"] is True
    
    def test_get_account_found(self, client: TestClient, sample_account: Account):
        """Test getting account by cognito ID when account exists."""
        response = client.get(f"/api/v1/account/{sample_account.cognito_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_account.id)
        assert data["email"] == sample_account.email
    
    def test_get_account_not_found(self, client: TestClient):
        """Test getting account by cognito ID when account doesn't exist."""
        response = client.get("/api/v1/account/nonexistent-cognito-id/")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Account not found"
    
    @patch('services.account_service.AccountService._update_cognito_user')
    def test_activate_account_success(self, mock_update_cognito, client: TestClient, db_session: Session):
        """Test successful account activation."""
        # Create inactive account
        account = Account(
            cognito_id="test-cognito-id",
            email="test@example.com",
            first_name="",
            last_name="",
            active=False
        )
        db_session.add(account)
        db_session.commit()
        
        payload = {
            "first_name": "John",
            "last_name": "Doe"
        }
        
        response = client.post(f"/api/v1/account/activate/{account.cognito_id}/", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["active"] is True
    
    def test_activate_account_not_found(self, client: TestClient):
        """Test activating account that doesn't exist."""
        payload = {
            "first_name": "John",
            "last_name": "Doe"
        }
        
        response = client.post("/api/v1/account/activate/nonexistent-id/", json=payload)
        
        assert response.status_code == 400
        assert "Account not found" in response.json()["detail"]
    
    def test_activate_account_already_active(self, client: TestClient, sample_account: Account, db_session: Session):
        """Test activating account that's already active."""
        sample_account.active = True
        db_session.commit()
        
        payload = {
            "first_name": "John",
            "last_name": "Doe"
        }
        
        response = client.post(f"/api/v1/account/activate/{sample_account.cognito_id}/", json=payload)
        
        assert response.status_code == 400
        assert "Account already active" in response.json()["detail"]
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.account_service.EmailService.send_invitation_email')
    @patch('services.account_service.AccountService._cognito_client')
    @patch('services.account_service.generate_temporary_password')
    def test_invite_account_success(self, mock_gen_password, mock_cognito_client, mock_email_service, 
                                   mock_get_current_account, client: TestClient, db_session: Session, 
                                   sample_account: Account, sample_tenant: Tenant):
        """Test successful account invitation."""
        # Setup existing membership for inviter
        membership = Membership(account_id=sample_account.id, tenant_id=sample_tenant.id)
        db_session.add(membership)
        db_session.commit()
        db_session.refresh(sample_account)
        
        mock_get_current_account.return_value = sample_account
        mock_gen_password.return_value = "temp123"
        mock_cognito = Mock()
        mock_cognito.admin_create_user.return_value = {
            "User": {"Username": "invited-user-id"}
        }
        mock_cognito_client.return_value = mock_cognito
        
        payload = {
            "email": "newuser@example.com"
        }
        
        response = client.post("/api/v1/account/invite/", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["cognito_id"] == "invited-user-id"
        assert data["email"] == "newuser@example.com"
    
    @patch('utils.get_current_account.get_current_account')
    def test_list_tenant_users(self, mock_get_current_account, client: TestClient, db_session: Session,
                              sample_account: Account, sample_tenant: Tenant):
        """Test listing tenant users."""
        # Create membership for the account
        membership = Membership(account_id=sample_account.id, tenant_id=sample_tenant.id)
        db_session.add(membership)
        db_session.commit()
        
        mock_get_current_account.return_value = sample_account
        
        response = client.get("/api/v1/account/tenant/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(sample_account.id)
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.account_service.EmailService.send_invitation_email')
    @patch('services.account_service.AccountService._cognito_client')
    @patch('services.account_service.generate_temporary_password')
    def test_resend_invite_success(self, mock_gen_password, mock_cognito_client, mock_email_service,
                                  mock_get_current_account, client: TestClient, sample_account: Account):
        """Test resending invitation."""
        mock_get_current_account.return_value = sample_account
        mock_gen_password.return_value = "newtemp123"
        mock_cognito = Mock()
        mock_cognito_client.return_value = mock_cognito
        
        response = client.post(f"/api/v1/account/resend-invitation/{sample_account.id}/")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Invitation email successfully resent"
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.account_service.AccountService._cognito_client')
    def test_delete_account_success(self, mock_cognito_client, mock_get_current_account, 
                                   client: TestClient, sample_account: Account):
        """Test successful account deletion."""
        mock_get_current_account.return_value = sample_account
        mock_cognito = Mock()
        mock_cognito_client.return_value = mock_cognito
        
        response = client.delete(f"/api/v1/account/{sample_account.id}/")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Account successfully deleted"
    
    @patch('utils.get_current_account.get_current_account')
    def test_delete_account_not_found(self, mock_get_current_account, client: TestClient, sample_account: Account):
        """Test deleting nonexistent account."""
        mock_get_current_account.return_value = sample_account
        nonexistent_id = uuid.uuid4()
        
        response = client.delete(f"/api/v1/account/{nonexistent_id}/")
        
        assert response.status_code == 500  # Internal server error due to ValueError