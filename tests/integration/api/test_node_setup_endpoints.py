import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from uuid import uuid4

from models import Project, Account, NodeSetup, NodeSetupVersion
from schemas.node_setup_version import NodeSetupVersionOut


@pytest.mark.integration
class TestNodeSetupEndpoints:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.project_id = str(uuid4())
        self.account_id = str(uuid4())
        self.setup_id = str(uuid4())
        self.version_id = str(uuid4())
        self.type = "blueprint"
        
        # Mock account
        self.mock_account = Mock(spec=Account)
        self.mock_account.id = self.account_id
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        
        # Mock node setup
        self.mock_node_setup = Mock(spec=NodeSetup)
        self.mock_node_setup.id = uuid4()
        self.mock_node_setup.content_type = self.type
        self.mock_node_setup.object_id = self.setup_id
        
        # Mock version
        self.mock_version = Mock(spec=NodeSetupVersion)
        self.mock_version.id = self.version_id
        self.mock_version.node_setup_id = self.mock_node_setup.id
        self.mock_version.draft = True
        self.mock_version.content = {"test": "content"}
        self.mock_version.version_number = 1
        
        # Sample update data
        self.update_data = {
            "content": {
                "nodes": [],
                "connections": [],
                "metadata": {"version": "1.0"}
            }
        }
    
    def teardown_method(self):
        """Clean up after each test."""
        from main import app
        app.dependency_overrides.clear()
    
    @patch('api.v1.project.node_setup.generate_code_from_json')
    def test_update_node_setup_version_success(self, mock_generate_code, client: TestClient):
        """Test successful node setup version update."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.mock_sync_service import get_mock_sync_service
        from db.session import get_db
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock database session
        mock_db = Mock()
        app.dependency_overrides[get_db] = lambda: mock_db
        
        # Mock sync service
        mock_sync_service = Mock()
        app.dependency_overrides[get_mock_sync_service] = lambda: mock_sync_service
        
        # Mock database queries
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_node_setup,  # First query for NodeSetup
            self.mock_version       # Second query for NodeSetupVersion
        ]
        
        # Mock code generation
        generated_code = "def lambda_handler(event, context): return {'statusCode': 200}"
        mock_generate_code.return_value = generated_code
        
        response = client.put(
            f"/api/v1/node-setup/{self.type}/{self.setup_id}/version/{self.version_id}/",
            json=self.update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify the version was updated
        assert self.mock_version.content == self.update_data["content"]
        assert self.mock_version.executable == generated_code
        
        # Verify database operations
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(self.mock_version)
        
        # Verify sync service was called
        mock_sync_service.sync_if_needed.assert_called_once_with(self.mock_version, self.mock_project)
        
        # Verify code generation was called
        mock_generate_code.assert_called_once_with(self.update_data["content"], self.version_id)
    
    def test_update_node_setup_version_node_setup_not_found(self, client: TestClient):
        """Test update when NodeSetup is not found."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from db.session import get_db
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock database session
        mock_db = Mock()
        app.dependency_overrides[get_db] = lambda: mock_db
        
        # Mock query to return None for NodeSetup
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        response = client.put(
            f"/api/v1/node-setup/{self.type}/{self.setup_id}/version/{self.version_id}/",
            json=self.update_data
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "NodeSetup not found"
    
    def test_update_node_setup_version_version_not_found(self, client: TestClient):
        """Test update when NodeSetupVersion is not found."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from db.session import get_db
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock database session
        mock_db = Mock()
        app.dependency_overrides[get_db] = lambda: mock_db
        
        # Mock queries - first returns NodeSetup, second returns None for version
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_node_setup,  # NodeSetup found
            None                   # NodeSetupVersion not found
        ]
        
        response = client.put(
            f"/api/v1/node-setup/{self.type}/{self.setup_id}/version/{self.version_id}/",
            json=self.update_data
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "NodeSetupVersion not found"
    
    def test_update_node_setup_version_not_draft(self, client: TestClient):
        """Test update when version is not a draft."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from db.session import get_db
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock database session
        mock_db = Mock()
        app.dependency_overrides[get_db] = lambda: mock_db
        
        # Set version as not draft
        self.mock_version.draft = False
        
        # Mock database queries
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_node_setup,
            self.mock_version
        ]
        
        response = client.put(
            f"/api/v1/node-setup/{self.type}/{self.setup_id}/version/{self.version_id}/",
            json=self.update_data
        )
        
        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["error"] == "This version is not editable."
        assert data["detail"]["requires_duplication"] is True
        assert data["detail"]["version_id"] == self.mock_version.id
    
    @patch('api.v1.project.node_setup.generate_code_from_json')
    def test_update_node_setup_version_code_generation_error(self, mock_generate_code, client: TestClient):
        """Test update when code generation fails."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.mock_sync_service import get_mock_sync_service
        from db.session import get_db
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock database session
        mock_db = Mock()
        app.dependency_overrides[get_db] = lambda: mock_db
        
        # Mock sync service
        mock_sync_service = Mock()
        app.dependency_overrides[get_mock_sync_service] = lambda: mock_sync_service
        
        # Mock database queries
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_node_setup,
            self.mock_version
        ]
        
        # Mock code generation to fail
        mock_generate_code.side_effect = Exception("Code generation failed")
        
        response = client.put(
            f"/api/v1/node-setup/{self.type}/{self.setup_id}/version/{self.version_id}/",
            json=self.update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["detail"]["message"] == "Did not update version"
        assert "Code generation failed" in data["detail"]["details"]
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()
    
    @patch('api.v1.project.node_setup.generate_code_from_json')
    def test_update_node_setup_version_sync_service_error(self, mock_generate_code, client: TestClient):
        """Test update when sync service fails (should not affect the update)."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.mock_sync_service import get_mock_sync_service
        from db.session import get_db
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock database session
        mock_db = Mock()
        app.dependency_overrides[get_db] = lambda: mock_db
        
        # Mock sync service to fail
        mock_sync_service = Mock()
        mock_sync_service.sync_if_needed.side_effect = Exception("Sync failed")
        app.dependency_overrides[get_mock_sync_service] = lambda: mock_sync_service
        
        # Mock database queries
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_node_setup,
            self.mock_version
        ]
        
        # Mock code generation
        generated_code = "def lambda_handler(event, context): return {'statusCode': 200}"
        mock_generate_code.return_value = generated_code
        
        response = client.put(
            f"/api/v1/node-setup/{self.type}/{self.setup_id}/version/{self.version_id}/",
            json=self.update_data
        )
        
        # Should still succeed despite sync failure
        assert response.status_code == 200
        
        # Verify the version was still updated
        assert self.mock_version.content == self.update_data["content"]
        assert self.mock_version.executable == generated_code
        
        # Verify database operations still happened
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(self.mock_version)
    
    def test_update_node_setup_version_invalid_json(self, client: TestClient):
        """Test update with invalid JSON payload."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Send invalid JSON
        response = client.put(
            f"/api/v1/node-setup/{self.type}/{self.setup_id}/version/{self.version_id}/",
            json={"invalid": "missing content field"}
        )
        
        assert response.status_code == 422
    
    def test_update_node_setup_version_no_authentication(self, client: TestClient):
        """Test update without authentication."""
        response = client.put(
            f"/api/v1/node-setup/{self.type}/{self.setup_id}/version/{self.version_id}/",
            json=self.update_data
        )
        
        assert response.status_code == 401
    
    @patch('api.v1.project.node_setup.generate_code_from_json')
    def test_update_node_setup_version_empty_content(self, mock_generate_code, client: TestClient):
        """Test update with empty content."""
        from utils.get_current_account import get_current_account, get_project_or_403
        from services.mock_sync_service import get_mock_sync_service
        from db.session import get_db
        from main import app
        
        app.dependency_overrides[get_current_account] = lambda: self.mock_account
        app.dependency_overrides[get_project_or_403] = lambda: self.mock_project
        
        # Mock database session
        mock_db = Mock()
        app.dependency_overrides[get_db] = lambda: mock_db
        
        # Mock sync service
        mock_sync_service = Mock()
        app.dependency_overrides[get_mock_sync_service] = lambda: mock_sync_service
        
        # Mock database queries
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_node_setup,
            self.mock_version
        ]
        
        # Mock code generation
        generated_code = ""
        mock_generate_code.return_value = generated_code
        
        empty_content_data = {"content": {}}
        
        response = client.put(
            f"/api/v1/node-setup/{self.type}/{self.setup_id}/version/{self.version_id}/",
            json=empty_content_data
        )
        
        assert response.status_code == 200
        
        # Verify empty content was set
        assert self.mock_version.content == {}
        assert self.mock_version.executable == generated_code