import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from main import app


@pytest.mark.unit
class TestExecutionStorageModifications:
    """Test the new execution storage modifications for run history retention"""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    @patch('api.v1.execution.details.get_execution_storage_service')
    def test_get_available_runs_success(self, mock_get_storage):
        """Test successful retrieval of available runs"""
        mock_storage = Mock()
        mock_storage.get_available_runs.return_value = [
            {"run_id": "run123", "timestamp": "2024-01-01T10:00:00"},
            {"run_id": "run456", "timestamp": "2024-01-01T11:00:00"}
        ]
        mock_get_storage.return_value = mock_storage
        
        response = self.client.get("/api/v1/execution/flow123/runs/")
        
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert len(data["runs"]) == 2
        assert data["runs"][0]["run_id"] == "run123"
        assert data["runs"][1]["run_id"] == "run456"
        
        mock_storage.get_available_runs.assert_called_once_with("flow123")
    
    @patch('api.v1.execution.details.get_execution_storage_service')
    def test_get_available_runs_empty(self, mock_get_storage):
        """Test retrieval when no runs are available"""
        mock_storage = Mock()
        mock_storage.get_available_runs.return_value = []
        mock_get_storage.return_value = mock_storage
        
        response = self.client.get("/api/v1/execution/flow123/runs/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []
    
    @patch('api.v1.execution.details.get_execution_storage_service')
    def test_get_available_runs_service_error(self, mock_get_storage):
        """Test error handling when service throws exception"""
        mock_storage = Mock()
        mock_storage.get_available_runs.side_effect = Exception("DynamoDB error")
        mock_get_storage.return_value = mock_storage
        
        response = self.client.get("/api/v1/execution/flow123/runs/")
        
        assert response.status_code == 500
        assert "DynamoDB error" in response.json()["detail"]


@pytest.mark.unit 
class TestExecutionStorageServiceRetention:
    """Test the new retention logic in the execution storage service"""
    
    @patch('polysynergy_node_runner.services.execution_storage_service.boto3')
    def test_clear_previous_execution_retention(self, mock_boto3):
        """Test that the new clear_previous_execution preserves recent runs"""
        from polysynergy_node_runner.services.execution_storage_service import DynamoDbExecutionStorageService
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock existing runs - old runs should be deleted, recent ones kept
        mock_table.query.side_effect = [
            # First call - get all run_ids
            {
                "Items": [
                    {"SK": "run1#node1#1#mock#mock"},
                    {"SK": "run2#node1#1#mock#mock"},
                    {"SK": "run3#node1#1#mock#mock"},
                    {"SK": "run4#node1#1#mock#mock"},
                    {"SK": "run5#node1#1#mock#mock"},
                    {"SK": "run6#node1#1#mock#mock"},
                    {"SK": "run7#node1#1#mock#mock"},  # This should be deleted (oldest)
                    {"SK": "run1#connections"},
                    {"SK": "run2#connections"},
                ]
            },
            # Second call - get items for run7 (oldest) to delete
            {
                "Items": [
                    {"PK": "flow123", "SK": "run7#node1#1#mock#mock"},
                    {"PK": "flow123", "SK": "run7#connections"}
                ]
            }
        ]
        
        service = DynamoDbExecutionStorageService()
        
        # Test with max_runs_to_keep=5 and current_run_id="current_run"
        service.clear_previous_execution("flow123", "current_run", max_runs_to_keep=5)
        
        # Verify that the query was called to get runs
        assert mock_table.query.call_count >= 1
        
        # Verify that batch_writer was used for deletion
        mock_table.batch_writer.assert_called()
    
    def test_get_all_run_ids_parsing(self):
        """Test that run_ids are correctly extracted from SK values"""
        from polysynergy_node_runner.services.execution_storage_service import DynamoDbExecutionStorageService
        
        service = DynamoDbExecutionStorageService()
        
        # Mock the query response
        with patch.object(service, 'table') as mock_table:
            mock_table.query.return_value = {
                "Items": [
                    {"SK": "run123#node1#1#mock#mock"},
                    {"SK": "run123#connections"},
                    {"SK": "run456#node2#2#stage#substage"},
                    {"SK": "run789#node3#3#test#test"},
                ]
            }
            
            run_ids = service._get_all_run_ids("flow123")
            
            # Should extract unique run_ids
            assert set(run_ids) == {"run123", "run456", "run789"}
            assert len(run_ids) == 3