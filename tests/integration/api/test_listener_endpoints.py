import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from uuid import uuid4

from models import Account


@pytest.mark.integration
class TestListenerEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.version_id = str(uuid4())
        self.account_id = str(uuid4())
        
        # Mock account
        self.mock_account = Mock(spec=Account)
        self.mock_account.id = self.account_id
    
    def teardown_method(self):
        """Clean up after each test."""
        from main import app
        app.dependency_overrides.clear()
    
    def test_check_listener_active_when_active(self, client: TestClient):
        """Test checking if listener is active when it is active."""
        from utils.get_current_account import get_current_account
        from services.active_listeners_service import get_active_listeners_service
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock active listeners service
        mock_service = Mock()
        mock_service.has_listener.return_value = True
        app.dependency_overrides[get_active_listeners_service] = lambda: mock_service
        
        response = client.get(f"/api/v1/listeners/{self.version_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        
        mock_service.has_listener.assert_called_once_with(self.version_id, required_stage="mock")
    
    def test_check_listener_active_when_inactive(self, client: TestClient):
        """Test checking if listener is active when it is inactive."""
        from utils.get_current_account import get_current_account
        from services.active_listeners_service import get_active_listeners_service
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock active listeners service
        mock_service = Mock()
        mock_service.has_listener.return_value = False
        app.dependency_overrides[get_active_listeners_service] = lambda: mock_service
        
        response = client.get(f"/api/v1/listeners/{self.version_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        
        mock_service.has_listener.assert_called_once_with(self.version_id, required_stage="mock")
    
    def test_check_listener_active_service_error(self, client: TestClient):
        """Test checking listener status when service raises an error."""
        from utils.get_current_account import get_current_account
        from services.active_listeners_service import get_active_listeners_service
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock active listeners service to raise error
        mock_service = Mock()
        mock_service.has_listener.side_effect = Exception("DynamoDB connection failed")
        app.dependency_overrides[get_active_listeners_service] = lambda: mock_service
        
        # Since the endpoint doesn't handle exceptions, it will raise a 500 error
        with pytest.raises(Exception):
            response = client.get(f"/api/v1/listeners/{self.version_id}/")
    
    def test_activate_listener_success(self, client: TestClient):
        """Test successful listener activation."""
        from utils.get_current_account import get_current_account
        from services.active_listeners_service import get_active_listeners_service
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock active listeners service
        mock_service = Mock()
        mock_service.set_listener.return_value = None
        app.dependency_overrides[get_active_listeners_service] = lambda: mock_service
        
        response = client.post(f"/api/v1/listeners/{self.version_id}/activate/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Listener activated."
        
        mock_service.set_listener.assert_called_once_with(self.version_id)
    
    def test_activate_listener_service_error(self, client: TestClient):
        """Test listener activation when service raises an error."""
        from utils.get_current_account import get_current_account
        from services.active_listeners_service import get_active_listeners_service
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock active listeners service to raise error
        mock_service = Mock()
        mock_service.set_listener.side_effect = Exception("Failed to set listener in DynamoDB")
        app.dependency_overrides[get_active_listeners_service] = lambda: mock_service
        
        # Since the endpoint doesn't handle exceptions, it will raise a 500 error
        with pytest.raises(Exception):
            response = client.post(f"/api/v1/listeners/{self.version_id}/activate/")
    
    def test_deactivate_listener_success(self, client: TestClient):
        """Test successful listener deactivation."""
        from utils.get_current_account import get_current_account
        from services.active_listeners_service import get_active_listeners_service
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock active listeners service
        mock_service = Mock()
        mock_service.clear_listeners.return_value = None
        app.dependency_overrides[get_active_listeners_service] = lambda: mock_service
        
        response = client.post(f"/api/v1/listeners/{self.version_id}/deactivate/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Listener deactivated."
        
        mock_service.clear_listeners.assert_called_once_with(self.version_id)
    
    def test_deactivate_listener_service_error(self, client: TestClient):
        """Test listener deactivation when service raises an error."""
        from utils.get_current_account import get_current_account
        from services.active_listeners_service import get_active_listeners_service
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock active listeners service to raise error
        mock_service = Mock()
        mock_service.clear_listeners.side_effect = Exception("Failed to clear listener in DynamoDB")
        app.dependency_overrides[get_active_listeners_service] = lambda: mock_service
        
        # Since the endpoint doesn't handle exceptions, it will raise a 500 error
        with pytest.raises(Exception):
            response = client.post(f"/api/v1/listeners/{self.version_id}/deactivate/")
    
    def test_invalid_version_id_format(self, client: TestClient):
        """Test endpoints with invalid UUID format."""
        from utils.get_current_account import get_current_account
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        invalid_version_id = "not-a-uuid"
        
        # Check listener
        response = client.get(f"/api/v1/listeners/{invalid_version_id}/")
        assert response.status_code == 422
        
        # Activate listener
        response = client.post(f"/api/v1/listeners/{invalid_version_id}/activate/")
        assert response.status_code == 422
        
        # Deactivate listener
        response = client.post(f"/api/v1/listeners/{invalid_version_id}/deactivate/")
        assert response.status_code == 422
    
    def test_listener_endpoints_no_authentication(self, client: TestClient):
        """Test listener endpoints without authentication."""
        # Check listener
        response = client.get(f"/api/v1/listeners/{self.version_id}/")
        assert response.status_code == 401
        
        # Activate listener
        response = client.post(f"/api/v1/listeners/{self.version_id}/activate/")
        assert response.status_code == 401
        
        # Deactivate listener
        response = client.post(f"/api/v1/listeners/{self.version_id}/deactivate/")
        assert response.status_code == 401
    
    def test_activate_listener_idempotency(self, client: TestClient):
        """Test that activating a listener multiple times is idempotent."""
        from utils.get_current_account import get_current_account
        from services.active_listeners_service import get_active_listeners_service
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock active listeners service
        mock_service = Mock()
        mock_service.set_listener.return_value = None
        app.dependency_overrides[get_active_listeners_service] = lambda: mock_service
        
        # Activate listener multiple times
        for _ in range(3):
            response = client.post(f"/api/v1/listeners/{self.version_id}/activate/")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Listener activated."
        
        # Should be called 3 times (not idempotent at API level, service handles it)
        assert mock_service.set_listener.call_count == 3
    
    def test_deactivate_listener_idempotency(self, client: TestClient):
        """Test that deactivating a listener multiple times is idempotent."""
        from utils.get_current_account import get_current_account
        from services.active_listeners_service import get_active_listeners_service
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        
        # Mock active listeners service
        mock_service = Mock()
        mock_service.clear_listeners.return_value = None
        app.dependency_overrides[get_active_listeners_service] = lambda: mock_service
        
        # Deactivate listener multiple times
        for _ in range(3):
            response = client.post(f"/api/v1/listeners/{self.version_id}/deactivate/")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Listener deactivated."
        
        # Should be called 3 times (not idempotent at API level, service handles it)
        assert mock_service.clear_listeners.call_count == 3