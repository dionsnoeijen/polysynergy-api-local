import pytest
from unittest.mock import Mock
from uuid import uuid4
from fastapi import HTTPException

from repositories.node_setup_repository import NodeSetupRepository, get_node_setup_repository
from models import NodeSetupVersion


@pytest.mark.unit
class TestNodeSetupRepository:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.mock_session = Mock()
        self.repository = NodeSetupRepository(self.mock_session)
        self.version_id = uuid4()
    
    def test_get_or_404_found(self):
        """Test get_or_404 when version is found."""
        # Mock NodeSetupVersion
        mock_version = Mock(spec=NodeSetupVersion)
        mock_version.id = self.version_id
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = mock_version
        
        # Call method
        result = self.repository.get_or_404(self.version_id)
        
        # Verify
        assert result == mock_version
        self.mock_session.query.assert_called_once_with(NodeSetupVersion)
        mock_query.filter_by.assert_called_once_with(id=self.version_id)
        mock_filter.first.assert_called_once()
    
    def test_get_or_404_not_found(self):
        """Test get_or_404 when version is not found."""
        # Mock query chain to return None
        mock_query = Mock()
        mock_filter = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = None
        
        # Call method and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self.repository.get_or_404(self.version_id)
        
        # Verify exception details
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "NodeSetupVersion not found"
        
        # Verify query was made
        self.mock_session.query.assert_called_once_with(NodeSetupVersion)
        mock_query.filter_by.assert_called_once_with(id=self.version_id)
        mock_filter.first.assert_called_once()
    
    def test_get_node_setup_repository(self):
        """Test get_node_setup_repository factory function."""
        mock_db = Mock()
        
        # Call factory function
        result = get_node_setup_repository(db=mock_db)
        
        # Verify instance creation
        assert isinstance(result, NodeSetupRepository)
        assert result.session == mock_db
    
    def test_get_or_404_with_different_uuid(self):
        """Test get_or_404 with different UUID."""
        different_uuid = uuid4()
        
        # Mock NodeSetupVersion
        mock_version = Mock(spec=NodeSetupVersion)
        mock_version.id = different_uuid
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = mock_version
        
        # Call method
        result = self.repository.get_or_404(different_uuid)
        
        # Verify correct UUID was used
        assert result == mock_version
        mock_query.filter_by.assert_called_once_with(id=different_uuid)
    
    def test_get_or_404_query_exception(self):
        """Test get_or_404 when database query raises exception."""
        # Mock query to raise exception
        self.mock_session.query.side_effect = Exception("Database connection error")
        
        # Call method and expect the exception to bubble up
        with pytest.raises(Exception, match="Database connection error"):
            self.repository.get_or_404(self.version_id)
        
        # Verify query was attempted
        self.mock_session.query.assert_called_once_with(NodeSetupVersion)