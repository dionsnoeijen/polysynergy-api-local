import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi import HTTPException

from repositories.service_repository import ServiceRepository
from models import Service, NodeSetup, NodeSetupVersion, Project
from schemas.service import ServiceCreateIn, ServiceMetadata


@pytest.mark.unit
class TestServiceRepository:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.mock_db = Mock()
        self.repository = ServiceRepository(self.mock_db)
        
        self.project_id = uuid4()
        self.service_id = uuid4()
        self.node_setup_id = uuid4()
        self.version_id = uuid4()
        self.tenant_id = uuid4()
        
        # Mock project
        self.mock_project = Mock()
        self.mock_project.id = self.project_id
        self.mock_project.tenant_id = self.tenant_id
        
        # Mock service
        self.mock_service = Mock()
        self.mock_service.id = self.service_id
        self.mock_service.name = "Test Service"
        self.mock_service.meta = {"icon": "test-icon", "category": "test", "description": "Test service"}
        self.mock_service.tenant_id = self.tenant_id
        self.mock_service.created_at = datetime.now(timezone.utc)
        self.mock_service.updated_at = datetime.now(timezone.utc)
        self.mock_service.projects = [self.mock_project]
        
        # Mock node setup
        self.mock_node_setup = Mock()
        self.mock_node_setup.id = self.node_setup_id
        self.mock_node_setup.content_type = "service"
        self.mock_node_setup.object_id = self.service_id
        
        # Mock node setup version
        self.mock_version = Mock()
        self.mock_version.id = self.version_id
        self.mock_version.node_setup_id = self.node_setup_id
        self.mock_version.version_number = 1
        self.mock_version.content = {}
        self.mock_version.published = False
        self.mock_version.draft = True

    def test_get_all_by_project(self):
        """Test retrieval of all services by project."""
        services = [self.mock_service]
        self.mock_db.query.return_value.filter.return_value.all.return_value = services
        
        result = self.repository.get_all_by_project(self.mock_project)
        
        assert result == services
        self.mock_db.query.assert_called_once_with(Service)

    def test_get_one_with_versions_by_id_found(self):
        """Test successful retrieval of single service with versions."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_service
        
        # Mock the node setup query call
        mock_filter_by = Mock()
        mock_filter_by.first.return_value = self.mock_node_setup
        self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
        
        result = self.repository.get_one_with_versions_by_id(str(self.service_id), self.mock_project)
        
        assert result == self.mock_service
        assert result.node_setup == self.mock_node_setup

    def test_get_one_with_versions_by_id_not_found(self):
        """Test service not found raises 404."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.get_one_with_versions_by_id(str(self.service_id), self.mock_project)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Service not found"

    def test_get_one_with_versions_no_node_setup(self):
        """Test retrieval when no node setup exists."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_service
        
        # Mock no node setup found
        mock_filter_by = Mock()
        mock_filter_by.first.return_value = None
        self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
        
        result = self.repository.get_one_with_versions_by_id(str(self.service_id), self.mock_project)
        
        assert result == self.mock_service
        assert result.node_setup is None

    def test_create_success(self):
        """Test successful service creation."""
        metadata = ServiceMetadata(
            icon="test-icon",
            category="database",
            description="Test database service"
        )
        service_data = ServiceCreateIn(
            name="Test Service",
            meta=metadata,
            node_setup_content={"test": "content"}
        )
        
        # Mock successful creation
        with patch('repositories.service_repository.Service') as mock_service_class, \
             patch('repositories.service_repository.NodeSetup') as mock_node_setup_class, \
             patch('repositories.service_repository.NodeSetupVersion') as mock_version_class:
            
            mock_service_class.return_value = self.mock_service
            mock_node_setup_class.return_value = self.mock_node_setup
            mock_version_class.return_value = self.mock_version
            
            result = self.repository.create(service_data, self.mock_project)
            
            assert result == self.mock_service
            assert result.node_setup == self.mock_node_setup
            self.mock_db.add.assert_called()
            self.mock_db.flush.assert_called()
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(self.mock_service)

    def test_create_without_node_setup_content(self):
        """Test service creation without node setup content."""
        metadata = ServiceMetadata(
            icon="test-icon",
            category="api",
            description="Test API service"
        )
        service_data = ServiceCreateIn(
            name="Simple Service",
            meta=metadata
        )
        
        with patch('repositories.service_repository.Service') as mock_service_class, \
             patch('repositories.service_repository.NodeSetup') as mock_node_setup_class, \
             patch('repositories.service_repository.NodeSetupVersion') as mock_version_class:
            
            mock_service_class.return_value = self.mock_service
            mock_node_setup_class.return_value = self.mock_node_setup
            mock_version_class.return_value = self.mock_version
            
            result = self.repository.create(service_data, self.mock_project)
            
            assert result == self.mock_service
            self.mock_db.commit.assert_called_once()

    def test_create_with_empty_metadata(self):
        """Test service creation with empty metadata."""
        metadata = ServiceMetadata()  # Empty metadata
        service_data = ServiceCreateIn(
            name="Minimal Service",
            meta=metadata
        )
        
        with patch('repositories.service_repository.Service') as mock_service_class, \
             patch('repositories.service_repository.NodeSetup') as mock_node_setup_class, \
             patch('repositories.service_repository.NodeSetupVersion') as mock_version_class:
            
            mock_service_class.return_value = self.mock_service
            mock_node_setup_class.return_value = self.mock_node_setup
            mock_version_class.return_value = self.mock_version
            
            result = self.repository.create(service_data, self.mock_project)
            
            assert result == self.mock_service
            self.mock_db.commit.assert_called_once()

    def test_update_success(self):
        """Test successful service update."""
        metadata = ServiceMetadata(
            icon="updated-icon",
            category="updated-category",
            description="Updated service description"
        )
        service_data = ServiceCreateIn(
            name="Updated Service",
            meta=metadata,
            node_setup_content={"updated": "content"}
        )
        
        # Mock get_one_with_versions_by_id to return service
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_service):
            # Mock version query for node setup content update
            mock_version_query = Mock()
            mock_version_query.join.return_value.filter.return_value.first.return_value = self.mock_version
            self.mock_db.query.return_value = mock_version_query
            
            result = self.repository.update(str(self.service_id), service_data, self.mock_project)
            
            assert result == self.mock_service
            assert self.mock_service.name == "Updated Service"
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(self.mock_service)

    def test_update_without_node_setup_content(self):
        """Test service update without node setup content."""
        metadata = ServiceMetadata(
            icon="updated-icon",
            category="web",
            description="Updated web service"
        )
        service_data = ServiceCreateIn(
            name="Updated Service",
            meta=metadata
        )
        
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_service):
            result = self.repository.update(str(self.service_id), service_data, self.mock_project)
            
            assert result == self.mock_service
            self.mock_db.commit.assert_called_once()

    def test_update_with_node_setup_content_no_version(self):
        """Test service update with node setup content but no existing version."""
        metadata = ServiceMetadata(icon="test-icon")
        service_data = ServiceCreateIn(
            name="Updated Service",
            meta=metadata,
            node_setup_content={"new": "content"}
        )
        
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_service):
            # Mock version query returning None
            mock_version_query = Mock()
            mock_version_query.join.return_value.filter.return_value.first.return_value = None
            self.mock_db.query.return_value = mock_version_query
            
            result = self.repository.update(str(self.service_id), service_data, self.mock_project)
            
            assert result == self.mock_service
            self.mock_db.commit.assert_called_once()

    def test_update_service_not_found(self):
        """Test update fails when service not found."""
        metadata = ServiceMetadata(icon="test-icon")
        service_data = ServiceCreateIn(name="Updated Service", meta=metadata)
        
        with patch.object(self.repository, 'get_one_with_versions_by_id') as mock_get:
            mock_get.side_effect = HTTPException(status_code=404, detail="Service not found")
            
            with pytest.raises(HTTPException) as exc_info:
                self.repository.update(str(self.service_id), service_data, self.mock_project)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Service not found"

    def test_delete_success(self):
        """Test successful service deletion."""
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_service):
            # Mock node setup query
            mock_filter_by = Mock()
            mock_filter_by.first.return_value = self.mock_node_setup
            self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
            
            self.repository.delete(str(self.service_id), self.mock_project)
            
            # Verify both node setup and service were deleted
            assert self.mock_db.delete.call_count == 2
            self.mock_db.commit.assert_called_once()

    def test_delete_without_node_setup(self):
        """Test service deletion when no node setup exists."""
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_service):
            # Mock no node setup found
            mock_filter_by = Mock()
            mock_filter_by.first.return_value = None
            self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
            
            self.repository.delete(str(self.service_id), self.mock_project)
            
            # Verify only service was deleted
            self.mock_db.delete.assert_called_once_with(self.mock_service)
            self.mock_db.commit.assert_called_once()

    def test_delete_service_not_found(self):
        """Test delete fails when service not found."""
        with patch.object(self.repository, 'get_one_with_versions_by_id') as mock_get:
            mock_get.side_effect = HTTPException(status_code=404, detail="Service not found")
            
            with pytest.raises(HTTPException) as exc_info:
                self.repository.delete(str(self.service_id), self.mock_project)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Service not found"

    def test_create_with_complex_metadata(self):
        """Test service creation with comprehensive metadata."""
        metadata = ServiceMetadata(
            icon="database-icon",
            category="storage",
            description="Complex database service with full metadata"
        )
        service_data = ServiceCreateIn(
            name="Complex Service",
            meta=metadata,
            node_setup_content={
                "environment": {
                    "DATABASE_URL": "postgresql://localhost:5432/test",
                    "MAX_CONNECTIONS": 100
                },
                "ports": [5432, 8080],
                "volumes": ["/data", "/logs"]
            }
        )
        
        with patch('repositories.service_repository.Service') as mock_service_class, \
             patch('repositories.service_repository.NodeSetup') as mock_node_setup_class, \
             patch('repositories.service_repository.NodeSetupVersion') as mock_version_class:
            
            mock_service_class.return_value = self.mock_service
            mock_node_setup_class.return_value = self.mock_node_setup
            mock_version_class.return_value = self.mock_version
            
            result = self.repository.create(service_data, self.mock_project)
            
            assert result == self.mock_service
            self.mock_db.commit.assert_called_once()

    def test_update_with_complex_node_setup_content(self):
        """Test service update with complex node setup content."""
        metadata = ServiceMetadata(
            icon="api-icon",
            category="microservice",
            description="Updated microservice"
        )
        service_data = ServiceCreateIn(
            name="Updated Microservice",
            meta=metadata,
            node_setup_content={
                "replicas": 3,
                "resources": {
                    "cpu": "500m",
                    "memory": "512Mi"
                },
                "healthcheck": {
                    "path": "/health",
                    "interval": 30
                }
            }
        )
        
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_service):
            # Mock version query
            mock_version_query = Mock()
            mock_version_query.join.return_value.filter.return_value.first.return_value = self.mock_version
            self.mock_db.query.return_value = mock_version_query
            
            result = self.repository.update(str(self.service_id), service_data, self.mock_project)
            
            assert result == self.mock_service
            # Verify that the version content was updated
            assert self.mock_version.content == service_data.node_setup_content
            self.mock_db.commit.assert_called_once()