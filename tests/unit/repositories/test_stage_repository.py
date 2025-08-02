import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi import HTTPException

from repositories.stage_repository import StageRepository
from models import Stage, Project
from schemas.stage import StageCreate, StageUpdate, ReorderStagesIn


@pytest.mark.unit
class TestStageRepository:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.mock_db = Mock()
        self.repository = StageRepository(self.mock_db)
        
        self.project_id = uuid4()
        self.stage_id = uuid4()
        self.tenant_id = uuid4()
        
        # Mock project
        self.mock_project = Mock()
        self.mock_project.id = self.project_id
        self.mock_project.tenant_id = self.tenant_id
        
        # Mock stage
        self.mock_stage = Mock()
        self.mock_stage.id = str(self.stage_id)
        self.mock_stage.name = "development"
        self.mock_stage.is_production = False
        self.mock_stage.order = 1
        self.mock_stage.project_id = self.project_id
        self.mock_stage.created_at = datetime.now(timezone.utc)
        self.mock_stage.updated_at = datetime.now(timezone.utc)

    def test_get_all_by_project(self):
        """Test retrieval of all stages by project."""
        stages = [self.mock_stage]
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = stages
        
        result = self.repository.get_all_by_project(self.mock_project)
        
        assert result == stages
        self.mock_db.query.assert_called_once_with(Stage)

    def test_get_by_id_found(self):
        """Test successful retrieval of stage by ID."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_stage
        
        result = self.repository.get_by_id(str(self.stage_id), self.mock_project)
        
        assert result == self.mock_stage
        self.mock_db.query.assert_called_once_with(Stage)

    def test_get_by_id_not_found(self):
        """Test stage not found raises 404."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.get_by_id(str(self.stage_id), self.mock_project)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Stage not found"

    def test_create_success(self):
        """Test successful stage creation."""
        stage_data = StageCreate(
            name="Testing",
            is_production=False
        )
        
        # Mock no existing stage
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        # Mock max order query
        self.mock_db.query.return_value.filter.return_value.scalar.return_value = 2
        
        with patch('repositories.stage_repository.Stage') as mock_stage_class:
            mock_stage_class.return_value = self.mock_stage
            
            result = self.repository.create(stage_data, self.mock_project)
            
            assert result == self.mock_stage
            self.mock_db.add.assert_called_once_with(self.mock_stage)
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(self.mock_stage)

    def test_create_reserved_name_mock(self):
        """Test creation fails with reserved name 'mock'."""
        stage_data = StageCreate(name="mock", is_production=False)
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.create(stage_data, self.mock_project)
        
        assert exc_info.value.status_code == 400
        assert "'mock' is a reserved stage name" in exc_info.value.detail

    def test_create_duplicate_name(self):
        """Test creation fails with duplicate name in project."""
        stage_data = StageCreate(name="Development", is_production=False)
        
        # Mock existing stage with same name
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_stage
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.create(stage_data, self.mock_project)
        
        assert exc_info.value.status_code == 400
        assert "Stage with this name already exists" in exc_info.value.detail

    def test_create_production_stage(self):
        """Test creating a production stage removes production flag from others."""
        stage_data = StageCreate(name="Production", is_production=True)
        
        # Mock no existing stage with same name
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        # Mock max order query
        self.mock_db.query.return_value.filter.return_value.scalar.return_value = 1
        
        with patch('repositories.stage_repository.Stage') as mock_stage_class:
            mock_stage_class.return_value = self.mock_stage
            
            result = self.repository.create(stage_data, self.mock_project)
            
            # Verify production flag was removed from other stages
            self.mock_db.query.return_value.filter.return_value.update.assert_called()
            assert result == self.mock_stage

    def test_create_with_empty_max_order(self):
        """Test stage creation when no stages exist (max_order is None)."""
        stage_data = StageCreate(name="First", is_production=False)
        
        # Mock no existing stage
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        # Mock empty max order query
        self.mock_db.query.return_value.filter.return_value.scalar.return_value = None
        
        with patch('repositories.stage_repository.Stage') as mock_stage_class:
            mock_stage_class.return_value = self.mock_stage
            
            result = self.repository.create(stage_data, self.mock_project)
            
            assert result == self.mock_stage

    def test_update_success(self):
        """Test successful stage update."""
        stage_data = StageUpdate(name="Updated Stage", is_production=False)
        
        with patch.object(self.repository, 'get_by_id', return_value=self.mock_stage):
            # Mock no existing stage with same name
            self.mock_db.query.return_value.filter.return_value.first.return_value = None
            
            result = self.repository.update(str(self.stage_id), stage_data, self.mock_project)
            
            assert result == self.mock_stage
            assert self.mock_stage.name == "updated stage"  # lowercase
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(self.mock_stage)

    def test_update_reserved_name(self):
        """Test update fails with reserved name 'mock'."""
        stage_data = StageUpdate(name="Mock")
        
        with patch.object(self.repository, 'get_by_id', return_value=self.mock_stage):
            with pytest.raises(HTTPException) as exc_info:
                self.repository.update(str(self.stage_id), stage_data, self.mock_project)
            
            assert exc_info.value.status_code == 400
            assert "'mock' is a reserved name" in exc_info.value.detail

    def test_update_duplicate_name(self):
        """Test update fails with duplicate name in project."""
        stage_data = StageUpdate(name="Existing")
        
        with patch.object(self.repository, 'get_by_id', return_value=self.mock_stage):
            # Mock existing stage with same name
            existing_stage = Mock()
            self.mock_db.query.return_value.filter.return_value.first.return_value = existing_stage
            
            with pytest.raises(HTTPException) as exc_info:
                self.repository.update(str(self.stage_id), stage_data, self.mock_project)
            
            assert exc_info.value.status_code == 400
            assert "Another stage with this name already exists" in exc_info.value.detail

    def test_update_set_production_true(self):
        """Test setting stage as production removes flag from others."""
        stage_data = StageUpdate(is_production=True)
        
        with patch.object(self.repository, 'get_by_id', return_value=self.mock_stage):
            result = self.repository.update(str(self.stage_id), stage_data, self.mock_project)
            
            # Verify production flag was removed from other stages
            self.mock_db.query.return_value.filter.return_value.update.assert_called()
            assert self.mock_stage.is_production is True
            assert result == self.mock_stage

    def test_update_set_production_false(self):
        """Test setting stage as non-production."""
        stage_data = StageUpdate(is_production=False)
        
        with patch.object(self.repository, 'get_by_id', return_value=self.mock_stage):
            result = self.repository.update(str(self.stage_id), stage_data, self.mock_project)
            
            assert self.mock_stage.is_production is False
            assert result == self.mock_stage

    def test_update_partial_data(self):
        """Test stage update with only some fields."""
        stage_data = StageUpdate(name="New Name")  # Only name, no is_production
        
        with patch.object(self.repository, 'get_by_id', return_value=self.mock_stage):
            # Mock no existing stage with same name
            self.mock_db.query.return_value.filter.return_value.first.return_value = None
            
            result = self.repository.update(str(self.stage_id), stage_data, self.mock_project)
            
            assert result == self.mock_stage
            assert self.mock_stage.name == "new name"

    def test_update_stage_not_found(self):
        """Test update fails when stage not found."""
        stage_data = StageUpdate(name="New Name")
        
        with patch.object(self.repository, 'get_by_id') as mock_get:
            mock_get.side_effect = HTTPException(status_code=404, detail="Stage not found")
            
            with pytest.raises(HTTPException) as exc_info:
                self.repository.update(str(self.stage_id), stage_data, self.mock_project)
            
            assert exc_info.value.status_code == 404

    def test_delete_success(self):
        """Test successful stage deletion."""
        with patch.object(self.repository, 'get_by_id', return_value=self.mock_stage):
            self.repository.delete(str(self.stage_id), self.mock_project)
            
            self.mock_db.delete.assert_called_once_with(self.mock_stage)
            self.mock_db.commit.assert_called_once()

    def test_delete_reserved_stage_mock(self):
        """Test deletion fails for reserved 'mock' stage."""
        mock_stage = Mock()
        mock_stage.name = "mock"
        
        with patch.object(self.repository, 'get_by_id', return_value=mock_stage):
            with pytest.raises(HTTPException) as exc_info:
                self.repository.delete(str(self.stage_id), self.mock_project)
            
            assert exc_info.value.status_code == 400
            assert "Cannot delete reserved stage 'mock'" in exc_info.value.detail

    def test_delete_stage_not_found(self):
        """Test delete fails when stage not found."""
        with patch.object(self.repository, 'get_by_id') as mock_get:
            mock_get.side_effect = HTTPException(status_code=404, detail="Stage not found")
            
            with pytest.raises(HTTPException) as exc_info:
                self.repository.delete(str(self.stage_id), self.mock_project)
            
            assert exc_info.value.status_code == 404

    def test_reorder_success(self):
        """Test successful stage reordering."""
        stage1_id = str(uuid4())
        stage2_id = str(uuid4())
        stage3_id = str(uuid4())
        
        mock_stage1 = Mock()
        mock_stage1.id = stage1_id
        mock_stage2 = Mock()
        mock_stage2.id = stage2_id
        mock_stage3 = Mock()
        mock_stage3.id = stage3_id
        
        stages = [mock_stage1, mock_stage2, mock_stage3]
        self.mock_db.query.return_value.filter.return_value.all.return_value = stages
        
        reorder_data = ReorderStagesIn(stage_ids=[stage3_id, stage1_id, stage2_id])
        
        self.repository.reorder(reorder_data, self.mock_project)
        
        # Verify orders were set correctly
        assert mock_stage3.order == 0  # First in new order
        assert mock_stage1.order == 1  # Second in new order
        assert mock_stage2.order == 2  # Third in new order
        self.mock_db.commit.assert_called_once()

    def test_reorder_with_invalid_stage_ids(self):
        """Test reordering with some invalid stage IDs."""
        stage1_id = str(uuid4())
        invalid_id = str(uuid4())
        
        mock_stage1 = Mock()
        mock_stage1.id = stage1_id
        
        stages = [mock_stage1]
        self.mock_db.query.return_value.filter.return_value.all.return_value = stages
        
        reorder_data = ReorderStagesIn(stage_ids=[stage1_id, invalid_id])
        
        self.repository.reorder(reorder_data, self.mock_project)
        
        # Only valid stage should be reordered
        assert mock_stage1.order == 0
        self.mock_db.commit.assert_called_once()

    def test_reorder_empty_list(self):
        """Test reordering with empty stage IDs list."""
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        reorder_data = ReorderStagesIn(stage_ids=[])
        
        self.repository.reorder(reorder_data, self.mock_project)
        
        self.mock_db.commit.assert_called_once()