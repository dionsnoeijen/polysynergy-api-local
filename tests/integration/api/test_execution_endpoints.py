import uuid
import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import Project, Account, NodeSetupVersion


@pytest.mark.integration
class TestExecutionDetailsEndpoints:
    
    @patch('api.v1.execution.details.get_execution_storage_service')
    def test_get_node_result_success(self, mock_get_storage, client: TestClient):
        """Test successful node result retrieval."""
        mock_storage = Mock()
        mock_storage.get_node_result.return_value = {
            "node_id": "test-node",
            "result": {"status": "success", "data": "test_data"}
        }
        mock_get_storage.return_value = mock_storage
        
        response = client.get("/api/v1/execution/flow123/run456/node789/1?stage=mock&sub_stage=mock")
        
        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == "test-node"
        assert data["result"]["status"] == "success"
        
        mock_storage.get_node_result.assert_called_once_with(
            "flow123", "run456", "node789", 1, "mock", "mock"
        )
    
    @patch('api.v1.execution.details.get_execution_storage_service')
    def test_get_node_result_not_found(self, mock_get_storage, client: TestClient):
        """Test node result retrieval when result not found."""
        mock_storage = Mock()
        mock_storage.get_node_result.return_value = None
        mock_get_storage.return_value = mock_storage
        
        response = client.get("/api/v1/execution/flow123/run456/node789/1")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "No result found"
    
    @patch('api.v1.execution.details.get_execution_storage_service')
    def test_get_node_result_service_error(self, mock_get_storage, client: TestClient):
        """Test node result retrieval when service throws error."""
        mock_storage = Mock()
        mock_storage.get_node_result.side_effect = Exception("Service error")
        mock_get_storage.return_value = mock_storage
        
        response = client.get("/api/v1/execution/flow123/run456/node789/1")
        
        assert response.status_code == 500
        assert response.json()["detail"] == "Service error"
    
    @patch('api.v1.execution.details.get_execution_storage_service')
    def test_get_connection_result_success(self, mock_get_storage, client: TestClient):
        """Test successful connection result retrieval."""
        mock_storage = Mock()
        mock_storage.get_connections_result.return_value = {
            "connections": [
                {"from": "node1", "to": "node2", "data": "test"}
            ]
        }
        mock_get_storage.return_value = mock_storage
        
        response = client.get("/api/v1/execution/flow123/run456/connections/")
        
        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
        assert len(data["connections"]) == 1
        
        mock_storage.get_connections_result.assert_called_once_with("flow123", "run456")
    
    @patch('api.v1.execution.details.get_execution_storage_service')
    def test_get_connection_result_not_found(self, mock_get_storage, client: TestClient):
        """Test connection result retrieval when result not found."""
        mock_storage = Mock()
        mock_storage.get_connections_result.return_value = None
        mock_get_storage.return_value = mock_storage
        
        response = client.get("/api/v1/execution/flow123/run456/connections/")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "No result found"


@pytest.mark.integration
class TestExecutionLogsEndpoints:
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.lambda_log_service.LambdaLogService.get_lambda_logs')
    def test_get_lambda_logs_success(self, mock_get_logs, mock_get_account, 
                                   client: TestClient, sample_account: Account):
        """Test successful lambda logs retrieval."""
        mock_get_account.return_value = sample_account
        mock_logs = [
            {"timestamp": 1640995200000, "message": "Log entry 1"},
            {"timestamp": 1640995210000, "message": "Log entry 2"}
        ]
        mock_get_logs.return_value = mock_logs
        
        version_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/execution/{version_id}/logs/")
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) == 2
        assert data["logs"][0]["message"] == "Log entry 1"
        
        mock_get_logs.assert_called_once_with(version_id, None)
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.lambda_log_service.LambdaLogService.get_lambda_logs')
    def test_get_lambda_logs_with_after_param(self, mock_get_logs, mock_get_account,
                                            client: TestClient, sample_account: Account):
        """Test lambda logs retrieval with after parameter."""
        mock_get_account.return_value = sample_account
        mock_logs = [{"timestamp": 1640995220000, "message": "Recent log"}]
        mock_get_logs.return_value = mock_logs
        
        version_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/execution/{version_id}/logs/?after=1640995200")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1
        
        mock_get_logs.assert_called_once_with(version_id, 1640995200)
    
    @patch('utils.get_current_account.get_current_account')
    @patch('services.lambda_log_service.LambdaLogService.get_lambda_logs')
    def test_get_lambda_logs_empty(self, mock_get_logs, mock_get_account,
                                 client: TestClient, sample_account: Account):
        """Test lambda logs retrieval when no logs found."""
        mock_get_account.return_value = sample_account
        mock_get_logs.return_value = []
        
        version_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/execution/{version_id}/logs/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []


@pytest.mark.integration
class TestExecutionMockEndpoints:
    
    @patch('utils.get_current_account.get_project_or_403')
    @patch('api.v1.execution.mock.get_active_listeners_service')
    @patch('api.v1.execution.mock.get_lambda_service')
    @patch('api.v1.execution.mock.get_node_setup_repository')
    @patch('api.v1.execution.mock.get_mock_sync_service')
    @patch('core.settings.settings')
    def test_mock_play_lambda_success(self, mock_settings, mock_get_sync, mock_get_repo, 
                                    mock_get_lambda, mock_get_listeners, mock_get_project,
                                    client: TestClient, sample_project: Project):
        """Test successful mock execution via Lambda."""
        # Setup mocks
        mock_settings.EXECUTE_NODE_SETUP_LOCAL = False
        mock_get_project.return_value = sample_project
        
        mock_listener_service = Mock()
        mock_get_listeners.return_value = mock_listener_service
        
        mock_lambda_service = Mock()
        mock_lambda_service.invoke_lambda.return_value = {"result": "success"}
        mock_get_lambda.return_value = mock_lambda_service
        
        mock_version = Mock()
        mock_version.id = uuid.uuid4()
        mock_repo = Mock()
        mock_repo.get_or_404.return_value = mock_version
        mock_get_repo.return_value = mock_repo
        
        mock_sync_service = Mock()
        mock_get_sync.return_value = mock_sync_service
        
        version_id = str(uuid.uuid4())
        mock_node_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/execution/{version_id}/{mock_node_id}/?sub_stage=test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "mock executed"
        assert data["result"]["result"] == "success"
        
        mock_listener_service.set_listener.assert_called_once_with(version_id)
        mock_repo.get_or_404.assert_called_once()
        mock_sync_service.sync_if_needed.assert_called_once_with(mock_version, sample_project)
    
    @patch('utils.get_current_account.get_project_or_403')
    @patch('api.v1.execution.mock.get_active_listeners_service')
    @patch('api.v1.execution.mock.get_lambda_service')
    @patch('api.v1.execution.mock.get_node_setup_repository')
    @patch('api.v1.execution.mock.get_mock_sync_service')
    @patch('core.settings.settings')
    def test_mock_play_lambda_pending_retry(self, mock_settings, mock_get_sync, mock_get_repo,
                                          mock_get_lambda, mock_get_listeners, mock_get_project,
                                          client: TestClient, sample_project: Project):
        """Test mock execution with Lambda pending retry."""
        mock_settings.EXECUTE_NODE_SETUP_LOCAL = False
        mock_get_project.return_value = sample_project
        
        mock_listener_service = Mock()
        mock_get_listeners.return_value = mock_listener_service
        
        # Mock lambda service to fail first, then succeed
        mock_lambda_service = Mock()
        mock_lambda_service.invoke_lambda.side_effect = [
            Exception("ResourceConflictException: Function is in Pending state"),
            {"result": "success"}
        ]
        mock_get_lambda.return_value = mock_lambda_service
        
        mock_version = Mock()
        mock_version.id = uuid.uuid4()
        mock_repo = Mock()
        mock_repo.get_or_404.return_value = mock_version
        mock_get_repo.return_value = mock_repo
        
        mock_sync_service = Mock()
        mock_get_sync.return_value = mock_sync_service
        
        version_id = str(uuid.uuid4())
        mock_node_id = str(uuid.uuid4())
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            response = client.get(f"/api/v1/execution/{version_id}/{mock_node_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "mock executed"
        assert mock_lambda_service.invoke_lambda.call_count == 2
    
    @patch('utils.get_current_account.get_project_or_403')
    @patch('api.v1.execution.mock.get_active_listeners_service')
    @patch('api.v1.execution.mock.get_lambda_service')
    @patch('api.v1.execution.mock.get_node_setup_repository')
    @patch('api.v1.execution.mock.get_mock_sync_service')
    @patch('core.settings.settings')
    def test_mock_play_lambda_error(self, mock_settings, mock_get_sync, mock_get_repo,
                                  mock_get_lambda, mock_get_listeners, mock_get_project,
                                  client: TestClient, sample_project: Project):
        """Test mock execution with Lambda error."""
        mock_settings.EXECUTE_NODE_SETUP_LOCAL = False
        mock_get_project.return_value = sample_project
        
        mock_listener_service = Mock()
        mock_get_listeners.return_value = mock_listener_service
        
        mock_lambda_service = Mock()
        mock_lambda_service.invoke_lambda.side_effect = Exception("Lambda execution failed")
        mock_get_lambda.return_value = mock_lambda_service
        
        mock_version = Mock()
        mock_version.id = uuid.uuid4()
        mock_repo = Mock()
        mock_repo.get_or_404.return_value = mock_version
        mock_get_repo.return_value = mock_repo
        
        mock_sync_service = Mock()
        mock_get_sync.return_value = mock_sync_service
        
        version_id = str(uuid.uuid4())
        mock_node_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/execution/{version_id}/{mock_node_id}/")
        
        assert response.status_code == 500
        assert "Lambda error" in response.json()["detail"]["error"]
    
    @patch('utils.get_current_account.get_project_or_403')
    @patch('api.v1.execution.mock.get_active_listeners_service')
    @patch('api.v1.execution.mock.get_node_setup_repository')
    @patch('api.v1.execution.mock.execute_local')
    @patch('core.settings.settings')
    def test_mock_play_local_execution_success(self, mock_settings, mock_execute_local,
                                             mock_get_repo, mock_get_listeners, mock_get_project,
                                             client: TestClient, sample_project: Project):
        """Test successful local mock execution."""
        mock_settings.EXECUTE_NODE_SETUP_LOCAL = True
        mock_get_project.return_value = sample_project
        
        mock_listener_service = Mock()
        mock_get_listeners.return_value = mock_listener_service
        
        mock_version = Mock()
        mock_version.id = uuid.uuid4()
        mock_repo = Mock()
        mock_repo.get_or_404.return_value = mock_version
        mock_get_repo.return_value = mock_repo
        
        mock_execute_local.return_value = {"status": "mock executed", "result": {"local": True}}
        
        version_id = str(uuid.uuid4())
        mock_node_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/execution/{version_id}/{mock_node_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "mock executed"
        assert data["result"]["local"] is True
        
        mock_execute_local.assert_called_once()