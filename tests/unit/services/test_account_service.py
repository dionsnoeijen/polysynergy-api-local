import uuid
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks

from services.account_service import AccountService
from models import Account, Membership, Tenant


@pytest.mark.unit
class TestAccountService:
    
    def test_get_by_cognito_id_found(self, db_session: Session, sample_account: Account):
        """Test getting account by cognito ID when account exists."""
        result = AccountService.get_by_cognito_id(db_session, sample_account.cognito_id)
        
        assert result is not None
        assert result.id == sample_account.id
        assert result.cognito_id == sample_account.cognito_id
    
    def test_get_by_cognito_id_not_found(self, db_session: Session):
        """Test getting account by cognito ID when account doesn't exist."""
        result = AccountService.get_by_cognito_id(db_session, "nonexistent-cognito-id")
        
        assert result is None
    
    def test_get_users_for_tenant_success(self, db_session: Session, sample_account: Account, sample_tenant: Tenant):
        """Test getting users for tenant when membership exists."""
        # Create membership for the account
        membership = Membership(account_id=sample_account.id, tenant_id=sample_tenant.id)
        db_session.add(membership)
        db_session.commit()
        
        # Create another account in the same tenant
        other_account = Account(
            id=uuid.uuid4(),
            cognito_id="other-cognito-id",
            email="other@example.com",
            first_name="Other",
            last_name="User"
        )
        db_session.add(other_account)
        other_membership = Membership(account_id=other_account.id, tenant_id=sample_tenant.id)
        db_session.add(other_membership)
        db_session.commit()
        
        result = AccountService.get_users_for_tenant(db_session, sample_account)
        
        assert len(result) == 2
        account_ids = [acc.id for acc in result]
        assert sample_account.id in account_ids
        assert other_account.id in account_ids
    
    def test_get_users_for_tenant_no_membership(self, db_session: Session, sample_account: Account):
        """Test getting users for tenant when current account has no membership."""
        with pytest.raises(ValueError, match="Access denied: account has no tenant membership"):
            AccountService.get_users_for_tenant(db_session, sample_account)
    
    @patch('services.account_service.AccountService._update_cognito_user')
    @patch('services.account_service.AccountService._cognito_client')
    def test_create_account_with_tenant(self, mock_cognito_client, mock_update_cognito, db_session: Session):
        """Test creating account with tenant."""
        data = {
            "tenant_name": "Test Company",
            "cognito_id": "test-cognito-id",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com"
        }
        
        result = AccountService.create_account_with_tenant(db_session, data)
        
        assert result.cognito_id == "test-cognito-id"
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.email == "john@example.com"
        assert result.active is True
        
        # Verify tenant was created
        assert len(result.memberships) == 1
        assert result.memberships[0].tenant.name == "Test Company"
        
        # Verify Cognito update was called
        mock_update_cognito.assert_called_once()
    
    @patch('services.account_service.settings')
    @patch('services.account_service.EmailService.send_invitation_email')
    @patch('services.account_service.AccountService._cognito_client')
    @patch('services.account_service.generate_temporary_password')
    def test_invite_to_tenant(self, mock_gen_password, mock_cognito_client, mock_email_service, mock_settings,
                             db_session: Session, sample_account: Account, sample_tenant: Tenant):
        """Test inviting user to tenant."""
        # Setup settings
        mock_settings.COGNITO_USER_POOL_ID = "test_pool"
        mock_settings.PORTAL_URL = "http://test.com"
        
        # Setup existing membership for inviter
        membership = Membership(account_id=sample_account.id, tenant_id=sample_tenant.id)
        db_session.add(membership)
        db_session.commit()
        db_session.refresh(sample_account)
        
        mock_gen_password.return_value = "temp123"
        mock_cognito = Mock()
        mock_cognito.admin_create_user.return_value = {
            "User": {"Username": "invited-user-id"}
        }
        mock_cognito_client.return_value = mock_cognito
        
        background_tasks = BackgroundTasks()
        result = AccountService.invite_to_tenant(db_session, sample_account, "newuser@example.com", background_tasks)
        
        assert result.cognito_id == "invited-user-id"
        assert result.email == "newuser@example.com"
        assert len(result.memberships) == 1
        assert result.memberships[0].tenant_id == sample_tenant.id
        
        mock_cognito.admin_create_user.assert_called_once()
        mock_email_service.assert_called_once()
    
    @patch('services.account_service.AccountService._update_cognito_user')
    def test_activate_account_success(self, mock_update_cognito, db_session: Session):
        """Test activating an inactive account."""
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
        
        result = AccountService.activate_account(db_session, "test-cognito-id", "John", "Doe")
        
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.active is True
        mock_update_cognito.assert_called_once()
    
    def test_activate_account_not_found(self, db_session: Session):
        """Test activating account that doesn't exist."""
        with pytest.raises(ValueError, match="Account not found"):
            AccountService.activate_account(db_session, "nonexistent-id", "John", "Doe")
    
    def test_activate_account_already_active(self, db_session: Session, sample_account: Account):
        """Test activating account that's already active."""
        sample_account.active = True
        db_session.commit()
        
        with pytest.raises(ValueError, match="Account already active"):
            AccountService.activate_account(db_session, sample_account.cognito_id, "John", "Doe")
    
    @patch('services.account_service.settings')
    @patch('services.account_service.EmailService.send_invitation_email')
    @patch('services.account_service.AccountService._cognito_client')
    @patch('services.account_service.generate_temporary_password')
    def test_resend_invite(self, mock_gen_password, mock_cognito_client, mock_email_service, mock_settings,
                          db_session: Session, sample_account: Account):
        """Test resending invitation to user."""
        # Setup settings
        mock_settings.COGNITO_USER_POOL_ID = "test_pool"
        mock_settings.PORTAL_URL = "http://test.com"
        
        mock_gen_password.return_value = "newtemp123"
        mock_cognito = Mock()
        mock_cognito_client.return_value = mock_cognito
        background_tasks = Mock()
        
        AccountService.resend_invite(db_session, str(sample_account.id), background_tasks)
        
        mock_cognito.admin_set_user_password.assert_called_once_with(
            UserPoolId="test_pool",
            Username=sample_account.email,
            Password="newtemp123",
            Permanent=False
        )
        mock_email_service.assert_called_once()
    
    @patch('services.account_service.settings')
    def test_resend_invite_account_not_found(self, mock_settings, db_session: Session):
        """Test resending invite for nonexistent account."""
        background_tasks = Mock()
        
        with pytest.raises(ValueError, match="Account not found"):
            AccountService.resend_invite(db_session, str(uuid.uuid4()), background_tasks)
    
    @patch('services.account_service.settings')
    @patch('services.account_service.AccountService._cognito_client')
    def test_delete_account(self, mock_cognito_client, mock_settings, db_session: Session, sample_account: Account):
        """Test deleting account."""
        # Setup settings
        mock_settings.COGNITO_USER_POOL_ID = "test_pool"
        
        mock_cognito = Mock()
        mock_cognito_client.return_value = mock_cognito
        account_id = str(sample_account.id)
        
        AccountService.delete_account(db_session, account_id)
        
        # Verify account was deleted from database
        deleted_account = db_session.get(Account, sample_account.id)
        assert deleted_account is None
        
        # Verify Cognito deletion was called
        mock_cognito.admin_delete_user.assert_called_once_with(
            UserPoolId="test_pool",
            Username=sample_account.email
        )
    
    @patch('services.account_service.settings')
    def test_delete_account_not_found(self, mock_settings, db_session: Session):
        """Test deleting nonexistent account."""
        with pytest.raises(ValueError, match="Account not found"):
            AccountService.delete_account(db_session, str(uuid.uuid4()))