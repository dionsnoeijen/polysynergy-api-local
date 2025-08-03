import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException

from repositories.blueprint_repository import BlueprintRepository
from models import Blueprint, Project, NodeSetup, NodeSetupVersion
from schemas.blueprint import BlueprintIn, BlueprintMetadata


@pytest.mark.unit
class TestBlueprintRepository:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.mock_db = Mock()
        self.repository = BlueprintRepository(self.mock_db)
        
        self.tenant_id = str(uuid4())
        self.project_id = str(uuid4())
        self.blueprint_id = str(uuid4())
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.tenant_id = self.tenant_id
        
        # Mock blueprint data
        self.mock_blueprint = Mock(spec=Blueprint)
        self.mock_blueprint.id = self.blueprint_id
        self.mock_blueprint.name = "Test Blueprint"
        self.mock_blueprint.meta = {
            "icon": "test-icon",
            "category": "utilities",
            "description": "Test description"
        }
        self.mock_blueprint.created_at = datetime.now(timezone.utc)
        self.mock_blueprint.updated_at = datetime.now(timezone.utc)
        self.mock_blueprint.tenant_id = self.tenant_id
    
    def test_get_all_by_project_success(self):
        """Test successful retrieval of all blueprints for a project."""
        # Mock query result
        mock_blueprints = [self.mock_blueprint, Mock(spec=Blueprint)]
        self.mock_db.query.return_value.filter.return_value.all.return_value = mock_blueprints
        
        result = self.repository.get_all_by_project(self.mock_project)
        
        assert result == mock_blueprints
        self.mock_db.query.assert_called_once_with(Blueprint)
        # Verify filter was called to check project association
        self.mock_db.query.return_value.filter.assert_called_once()
    
    def test_get_all_by_project_empty(self):
        """Test retrieval when no blueprints exist for project."""
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        result = self.repository.get_all_by_project(self.mock_project)
        
        assert result == []
    
    def test_get_one_with_versions_by_id_success(self):
        """Test successful retrieval of blueprint with versions."""
        # Mock blueprint query
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_blueprint
        
        # Mock node setup query
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = str(uuid4())
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_node_setup
        
        result = self.repository.get_one_with_versions_by_id(self.blueprint_id, self.mock_project)
        
        assert result == self.mock_blueprint
        assert result.node_setup == mock_node_setup
        
        # Verify blueprint query
        blueprint_query_calls = [call for call in self.mock_db.query.call_args_list if call[0][0] == Blueprint]
        assert len(blueprint_query_calls) == 1
        
        # Verify node setup query
        node_setup_query_calls = [call for call in self.mock_db.query.call_args_list if call[0][0] == NodeSetup]
        assert len(node_setup_query_calls) == 1
    
    def test_get_one_with_versions_by_id_not_found(self):
        """Test retrieval when blueprint doesn't exist."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Import the specific HTTPException used by the repository
        from starlette.exceptions import HTTPException as StarletteHTTPException
        
        with pytest.raises(StarletteHTTPException) as exc_info:
            self.repository.get_one_with_versions_by_id(self.blueprint_id, self.mock_project)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Blueprint not found"
    
    def test_get_one_with_versions_by_id_no_node_setup(self):
        """Test retrieval when blueprint exists but has no node setup."""
        # Mock blueprint query
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_blueprint
        
        # Mock node setup query returns None
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.repository.get_one_with_versions_by_id(self.blueprint_id, self.mock_project)
        
        assert result == self.mock_blueprint
        assert result.node_setup is None
    
    @patch('repositories.blueprint_repository.NodeSetupVersion')
    @patch('repositories.blueprint_repository.NodeSetup')
    @patch('repositories.blueprint_repository.Blueprint')
    @patch('repositories.blueprint_repository.uuid4')
    @patch('repositories.blueprint_repository.datetime')
    def test_create_success(self, mock_datetime, mock_uuid4, MockBlueprint, MockNodeSetup, MockNodeSetupVersion):
        """Test successful blueprint creation."""
        # Setup mocks
        fixed_time = datetime.now(timezone.utc)
        mock_datetime.now.return_value = fixed_time
        
        blueprint_uuid = uuid4()
        node_setup_uuid = uuid4()
        version_uuid = uuid4()
        mock_uuid4.side_effect = [blueprint_uuid, node_setup_uuid, version_uuid]
        
        # Create mock instances
        mock_blueprint = Mock()
        mock_node_setup = Mock()
        mock_version = Mock()
        
        MockBlueprint.return_value = mock_blueprint
        MockNodeSetup.return_value = mock_node_setup
        MockNodeSetupVersion.return_value = mock_version
        
        # Create test data
        blueprint_data = BlueprintIn(
            name="New Blueprint",
            meta=BlueprintMetadata(
                icon="new-icon",
                category="automation",
                description="New blueprint description"
            )
        )
        
        result = self.repository.create(blueprint_data, self.mock_project)
        
        # Verify database operations
        assert self.mock_db.add.call_count == 3  # Blueprint, NodeSetup, NodeSetupVersion
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_blueprint)
        
        # Verify Blueprint creation
        MockBlueprint.assert_called_once_with(
            id=blueprint_uuid,
            name="New Blueprint",
            meta={"icon": "new-icon", "category": "automation", "description": "New blueprint description"},
            created_at=fixed_time,
            updated_at=fixed_time,
            tenant_id=self.mock_project.tenant_id,
            projects=[self.mock_project]
        )
        
        # Verify NodeSetup creation
        MockNodeSetup.assert_called_once_with(
            id=node_setup_uuid,
            content_type="blueprint",
            object_id=blueprint_uuid,
            created_at=fixed_time,
            updated_at=fixed_time
        )
        
        # Verify NodeSetupVersion creation
        MockNodeSetupVersion.assert_called_once_with(
            id=version_uuid,
            node_setup_id=node_setup_uuid,
            version_number=1,
            content={},
            created_at=fixed_time,
            updated_at=fixed_time,
            draft=True
        )
        
        # Verify database calls
        assert self.mock_db.add.call_args_list[0][0][0] == mock_blueprint
        assert self.mock_db.add.call_args_list[1][0][0] == mock_node_setup
        assert self.mock_db.add.call_args_list[2][0][0] == mock_version
        
        # Verify the returned blueprint has the node_setup attached
        assert result == mock_blueprint
        assert result.node_setup == mock_node_setup
    
    @patch('repositories.blueprint_repository.datetime')
    def test_update_success(self, mock_datetime):
        """Test successful blueprint update."""
        fixed_time = datetime.now(timezone.utc)
        mock_datetime.now.return_value = fixed_time
        
        # Mock get_one_with_versions_by_id
        self.mock_blueprint.name = "Original Name"
        self.mock_blueprint.meta = {"icon": "old-icon"}
        
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_blueprint):
            update_data = BlueprintIn(
                name="Updated Blueprint",
                meta=BlueprintMetadata(
                    icon="updated-icon",
                    category="updated-category",
                    description="Updated description"
                )
            )
            
            result = self.repository.update(self.blueprint_id, update_data, self.mock_project)
            
            # Verify updates
            assert self.mock_blueprint.name == "Updated Blueprint"
            assert self.mock_blueprint.meta == update_data.meta.model_dump()
            assert self.mock_blueprint.updated_at == fixed_time
            
            # Verify database operations
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(self.mock_blueprint)
            
            assert result == self.mock_blueprint
    
    def test_update_blueprint_not_found(self):
        """Test update when blueprint doesn't exist."""
        from starlette.exceptions import HTTPException as StarletteHTTPException
        
        with patch.object(self.repository, 'get_one_with_versions_by_id', side_effect=StarletteHTTPException(status_code=404, detail="Blueprint not found")):
            update_data = BlueprintIn(
                name="Updated Blueprint",
                meta=BlueprintMetadata(icon="updated-icon")
            )
            
            with pytest.raises(StarletteHTTPException) as exc_info:
                self.repository.update(self.blueprint_id, update_data, self.mock_project)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Blueprint not found"
    
    def test_delete_success(self):
        """Test successful blueprint deletion."""
        # Mock node setup
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.id = str(uuid4())
        
        # Mock get_one_with_versions_by_id
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_blueprint):
            # Mock node setup query
            self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_node_setup
            
            self.repository.delete(self.blueprint_id, self.mock_project)
            
            # Verify deletions
            delete_calls = self.mock_db.delete.call_args_list
            assert len(delete_calls) == 2
            assert delete_calls[0][0][0] == mock_node_setup  # NodeSetup deleted first
            assert delete_calls[1][0][0] == self.mock_blueprint  # Blueprint deleted second
            
            self.mock_db.commit.assert_called_once()
    
    def test_delete_no_node_setup(self):
        """Test blueprint deletion when no associated node setup exists."""
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_blueprint):
            # Mock node setup query returns None
            self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
            
            self.repository.delete(self.blueprint_id, self.mock_project)
            
            # Verify only blueprint is deleted
            delete_calls = self.mock_db.delete.call_args_list
            assert len(delete_calls) == 1
            assert delete_calls[0][0][0] == self.mock_blueprint
            
            self.mock_db.commit.assert_called_once()
    
    def test_delete_blueprint_not_found(self):
        """Test deletion when blueprint doesn't exist."""
        from starlette.exceptions import HTTPException as StarletteHTTPException
        
        with patch.object(self.repository, 'get_one_with_versions_by_id', side_effect=StarletteHTTPException(status_code=404, detail="Blueprint not found")):
            with pytest.raises(StarletteHTTPException) as exc_info:
                self.repository.delete(self.blueprint_id, self.mock_project)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Blueprint not found"
            
            # Verify no delete operations were called
            self.mock_db.delete.assert_not_called()
            self.mock_db.commit.assert_not_called()
    
    def test_create_with_metadata_variations(self):
        """Test blueprint creation with various metadata configurations."""
        with patch('repositories.blueprint_repository.Blueprint') as MockBlueprint:
            with patch('repositories.blueprint_repository.NodeSetup') as MockNodeSetup:
                with patch('repositories.blueprint_repository.NodeSetupVersion') as MockNodeSetupVersion:
                    with patch('repositories.blueprint_repository.uuid4') as mock_uuid4:
                        with patch('repositories.blueprint_repository.datetime') as mock_datetime:
                            fixed_time = datetime.now(timezone.utc)
                            mock_datetime.now.return_value = fixed_time
                            mock_uuid4.side_effect = [uuid4(), uuid4(), uuid4()]
                            
                            # Create mock instances
                            mock_blueprint = Mock()
                            MockBlueprint.return_value = mock_blueprint
                            MockNodeSetup.return_value = Mock()
                            MockNodeSetupVersion.return_value = Mock()
                            
                            # Test with minimal metadata
                            minimal_data = BlueprintIn(
                                name="Minimal Blueprint",
                                meta=BlueprintMetadata()  # All defaults
                            )
                            
                            self.repository.create(minimal_data, self.mock_project)
                            
                            # Verify Blueprint was created with correct metadata
                            MockBlueprint.assert_called_once()
                            call_args = MockBlueprint.call_args[1]
                            assert call_args['name'] == "Minimal Blueprint"
                            assert call_args['meta'] == {"icon": "", "category": "", "description": ""}
    
    @patch('repositories.blueprint_repository.NodeSetupVersion')
    @patch('repositories.blueprint_repository.NodeSetup')
    @patch('repositories.blueprint_repository.Blueprint')
    @patch('repositories.blueprint_repository.uuid4')
    @patch('repositories.blueprint_repository.datetime')
    def test_create_database_error_handling(self, mock_datetime, mock_uuid4, MockBlueprint, MockNodeSetup, MockNodeSetupVersion):
        """Test blueprint creation when database operations fail."""
        fixed_time = datetime.now(timezone.utc)
        mock_datetime.now.return_value = fixed_time
        mock_uuid4.side_effect = [uuid4(), uuid4(), uuid4()]
        
        # Create mock instances
        MockBlueprint.return_value = Mock()
        MockNodeSetup.return_value = Mock()
        MockNodeSetupVersion.return_value = Mock()
        
        # Mock database commit to raise an exception
        self.mock_db.commit.side_effect = Exception("Database error")
        
        blueprint_data = BlueprintIn(
            name="Test Blueprint",
            meta=BlueprintMetadata(icon="test-icon", category="", description="")
        )
        
        with pytest.raises(Exception, match="Database error"):
            self.repository.create(blueprint_data, self.mock_project)
    
    def test_update_database_error_handling(self):
        """Test blueprint update when database operations fail."""
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_blueprint):
            # Mock database commit to raise an exception
            self.mock_db.commit.side_effect = Exception("Database commit failed")
            
            update_data = BlueprintIn(
                name="Updated Blueprint",
                meta=BlueprintMetadata(icon="updated-icon")
            )
            
            with pytest.raises(Exception, match="Database commit failed"):
                self.repository.update(self.blueprint_id, update_data, self.mock_project)
    
    def test_delete_database_error_handling(self):
        """Test blueprint deletion when database operations fail."""
        mock_node_setup = Mock(spec=NodeSetup)
        
        with patch.object(self.repository, 'get_one_with_versions_by_id', return_value=self.mock_blueprint):
            self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_node_setup
            
            # Mock database commit to raise an exception
            self.mock_db.commit.side_effect = Exception("Database deletion failed")
            
            with pytest.raises(Exception, match="Database deletion failed"):
                self.repository.delete(self.blueprint_id, self.mock_project)