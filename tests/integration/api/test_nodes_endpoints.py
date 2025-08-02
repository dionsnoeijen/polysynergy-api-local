import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestNodesEndpoints:
    
    @patch('api.v1.nodes.nodes.discover_nodes')
    def test_list_nodes_success(self, mock_discover_nodes, client: TestClient):
        """Test successful node listing."""
        mock_nodes = [
            {
                "id": "text_input_node",
                "name": "Text Input",
                "description": "A node for text input",
                "category": "input",
                "inputs": [],
                "outputs": [{"name": "text", "type": "string"}],
                "version": "1.0.0"
            },
            {
                "id": "text_output_node", 
                "name": "Text Output",
                "description": "A node for text output",
                "category": "output",
                "inputs": [{"name": "text", "type": "string"}],
                "outputs": [],
                "version": "1.0.0"
            }
        ]
        mock_discover_nodes.return_value = mock_nodes
        
        response = client.get("/api/v1/nodes/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "text_input_node"
        assert data[0]["name"] == "Text Input"
        assert data[0]["category"] == "input"
        assert data[1]["id"] == "text_output_node"
        assert data[1]["category"] == "output"
        
        mock_discover_nodes.assert_called_once_with(["polysynergy_nodes", "polysynergy_nodes_agno"])
    
    @patch('api.v1.nodes.nodes.discover_nodes')
    def test_list_nodes_with_complex_node_structure(self, mock_discover_nodes, client: TestClient):
        """Test node listing with complex node structures."""
        mock_nodes = [
            {
                "id": "data_processor",
                "name": "Data Processor",
                "description": "Processes data with multiple inputs and outputs",
                "category": "processing",
                "inputs": [
                    {"name": "data", "type": "object", "required": True},
                    {"name": "config", "type": "object", "required": False}
                ],
                "outputs": [
                    {"name": "processed_data", "type": "object"},
                    {"name": "metadata", "type": "object"}
                ],
                "parameters": [
                    {"name": "operation", "type": "string", "default": "transform"},
                    {"name": "timeout", "type": "number", "default": 30}
                ],
                "version": "2.1.0",
                "author": "PolySynergy Team"
            }
        ]
        mock_discover_nodes.return_value = mock_nodes
        
        response = client.get("/api/v1/nodes/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        node = data[0]
        assert node["id"] == "data_processor"
        assert len(node["inputs"]) == 2
        assert len(node["outputs"]) == 2
        assert len(node["parameters"]) == 2
        assert node["version"] == "2.1.0"
    
    @patch('api.v1.nodes.nodes.discover_nodes')
    def test_list_nodes_empty(self, mock_discover_nodes, client: TestClient):
        """Test node listing when no nodes are found."""
        mock_discover_nodes.return_value = []
        
        response = client.get("/api/v1/nodes/")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    @patch('api.v1.nodes.nodes.discover_nodes')
    def test_list_nodes_exception(self, mock_discover_nodes, client: TestClient):
        """Test node listing when an exception occurs."""
        mock_discover_nodes.side_effect = Exception("Node discovery failed")
        
        response = client.get("/api/v1/nodes/")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Node discovery failed"
    
    @patch('api.v1.nodes.nodes.discover_nodes')
    def test_list_nodes_import_error(self, mock_discover_nodes, client: TestClient):
        """Test node listing when import error occurs."""
        mock_discover_nodes.side_effect = ImportError("Cannot import polysynergy_nodes")
        
        response = client.get("/api/v1/nodes/")
        
        assert response.status_code == 500
        data = response.json()
        assert "Cannot import polysynergy_nodes" in data["error"]
    
    @patch('api.v1.nodes.nodes.discover_nodes')
    def test_list_nodes_mixed_categories(self, mock_discover_nodes, client: TestClient):
        """Test node listing with nodes from different categories."""
        mock_nodes = [
            {
                "id": "http_request",
                "name": "HTTP Request",
                "category": "network",
                "version": "1.0.0"
            },
            {
                "id": "file_reader",
                "name": "File Reader", 
                "category": "io",
                "version": "1.2.0"
            },
            {
                "id": "math_add",
                "name": "Math Add",
                "category": "math",
                "version": "1.0.0"
            },
            {
                "id": "string_concat",
                "name": "String Concatenate",
                "category": "string",
                "version": "1.1.0"
            }
        ]
        mock_discover_nodes.return_value = mock_nodes
        
        response = client.get("/api/v1/nodes/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        
        categories = [node["category"] for node in data]
        assert "network" in categories
        assert "io" in categories
        assert "math" in categories
        assert "string" in categories