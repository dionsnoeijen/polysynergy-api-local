import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi import HTTPException

from repositories.route_repository import RouteRepository
from models import Route, RouteSegment, NodeSetup, NodeSetupVersion, Project
from models.route import Method
from schemas.route import RouteCreateIn, RouteSegmentIn
from models.route_segment import RouteSegmentType, VariableType


@pytest.mark.unit
class TestRouteRepository:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.mock_db = Mock()
        self.repository = RouteRepository(self.mock_db)
        
        self.project_id = str(uuid4())
        self.route_id = str(uuid4())
        self.segment_id = str(uuid4())
        self.node_setup_id = str(uuid4())
        self.version_id = str(uuid4())
        
        # Mock project
        self.mock_project = Mock()
        self.mock_project.id = self.project_id
        
        # Mock route
        self.mock_route = Mock()
        self.mock_route.id = self.route_id
        self.mock_route.project_id = self.project_id
        self.mock_route.description = "Test Route"
        self.mock_route.method = Method.GET
        self.mock_route.created_at = datetime.now(timezone.utc)
        self.mock_route.updated_at = datetime.now(timezone.utc)
        
        # Mock route segment
        self.mock_segment = Mock()
        self.mock_segment.id = self.segment_id
        self.mock_segment.route_id = self.route_id
        self.mock_segment.segment_order = 1
        self.mock_segment.type = RouteSegmentType.STATIC
        self.mock_segment.name = "api"
        self.mock_segment.default_value = None
        self.mock_segment.variable_type = None
        
        # Mock node setup
        self.mock_node_setup = Mock()
        self.mock_node_setup.id = self.node_setup_id
        self.mock_node_setup.content_type = "route"
        self.mock_node_setup.object_id = self.route_id
        
        # Mock node setup version
        self.mock_version = Mock()
        self.mock_version.id = self.version_id
        self.mock_version.node_setup_id = self.node_setup_id
        self.mock_version.version_number = 1
        self.mock_version.content = {}

    def test_get_all_by_project(self):
        """Test retrieval of all routes by project."""
        routes = [self.mock_route]
        self.mock_db.query.return_value.filter.return_value.all.return_value = routes
        
        result = self.repository.get_all_by_project(self.mock_project)
        
        assert result == routes
        self.mock_db.query.assert_called_once_with(Route)

    def test_get_by_id_found(self):
        """Test successful retrieval of route by ID."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_route
        
        result = self.repository.get_by_id(self.route_id, self.mock_project)
        
        assert result == self.mock_route
        self.mock_db.query.assert_called_once_with(Route)

    def test_get_by_id_not_found(self):
        """Test route not found by ID."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = self.repository.get_by_id(self.route_id, self.mock_project)
        
        assert result is None

    def test_get_all_with_versions_by_project(self):
        """Test retrieval of all routes with their versions."""
        routes = [self.mock_route]
        self.mock_db.query.return_value.filter.return_value.all.return_value = routes
        
        # Mock the node setup query call
        mock_filter_by = Mock()
        mock_filter_by.first.return_value = self.mock_node_setup
        self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
        
        result = self.repository.get_all_with_versions_by_project(self.mock_project)
        
        assert result == routes
        assert routes[0].node_setup == self.mock_node_setup
        assert self.mock_db.query.call_count == 2  # Once for routes, once for node_setup

    def test_get_all_with_versions_by_project_no_node_setup(self):
        """Test retrieval of routes when no node setup exists."""
        routes = [self.mock_route]
        self.mock_db.query.return_value.filter.return_value.all.return_value = routes
        
        # Mock no node setup found
        mock_filter_by = Mock()
        mock_filter_by.first.return_value = None
        self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
        
        result = self.repository.get_all_with_versions_by_project(self.mock_project)
        
        assert result == routes
        assert routes[0].node_setup == []

    def test_get_one_with_versions_by_id_found(self):
        """Test successful retrieval of single route with versions."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_route
        
        # Mock the node setup query call
        mock_filter_by = Mock()
        mock_filter_by.first.return_value = self.mock_node_setup
        self.mock_db.query.return_value.filter_by = Mock(return_value=mock_filter_by)
        
        result = self.repository.get_one_with_versions_by_id(self.route_id, self.mock_project)
        
        assert result == self.mock_route
        assert result.node_setup == self.mock_node_setup

    def test_get_one_with_versions_by_id_not_found(self):
        """Test route not found raises 404."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.get_one_with_versions_by_id(self.route_id, self.mock_project)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Route not found"

    def test_exists_with_pattern_found(self):
        """Test pattern exists returns True."""
        # Mock route with segments
        mock_segment = Mock()
        mock_segment.type = "static"
        mock_segment.name = "api"
        
        route_with_segments = Mock()
        route_with_segments.segments = [mock_segment]
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [route_with_segments]
        
        result = self.repository.exists_with_pattern("GET", self.mock_project, ["api"])
        
        assert result is True

    def test_exists_with_pattern_not_found(self):
        """Test pattern doesn't exist returns False."""
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        result = self.repository.exists_with_pattern("GET", self.mock_project, ["different"])
        
        assert result is False

    def test_exists_with_pattern_variable_segment(self):
        """Test pattern matching with variable segments."""
        # Mock route with variable segment
        mock_segment = Mock()
        mock_segment.type = "variable"
        mock_segment.name = "id"
        
        route_with_segments = Mock()
        route_with_segments.segments = [mock_segment]
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [route_with_segments]
        
        result = self.repository.exists_with_pattern("GET", self.mock_project, ["{var}"])
        
        assert result is True

    def test_create_success(self):
        """Test successful route creation."""
        route_data = RouteCreateIn(
            description="Test Route",
            method="GET",
            segments=[
                RouteSegmentIn(
                    segment_order=1,
                    type=RouteSegmentType.STATIC,
                    name="api",
                    default_value=None,
                    variable_type=None
                )
            ]
        )
        
        # Mock successful creation
        with patch('repositories.route_repository.Route') as mock_route_class, \
             patch('repositories.route_repository.RouteSegment') as mock_segment_class, \
             patch('repositories.route_repository.NodeSetup') as mock_node_setup_class, \
             patch('repositories.route_repository.NodeSetupVersion') as mock_version_class:
            
            mock_route_class.return_value = self.mock_route
            mock_segment_class.return_value = self.mock_segment
            mock_node_setup_class.return_value = self.mock_node_setup
            mock_version_class.return_value = self.mock_version
            
            # Mock no existing routes
            self.mock_db.query.return_value.filter.return_value.all.return_value = []
            
            result = self.repository.create(route_data, self.mock_project)
            
            assert result == self.mock_route
            self.mock_db.add.assert_called()
            self.mock_db.flush.assert_called()
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(self.mock_route)

    def test_create_duplicate_route(self):
        """Test creation fails when duplicate route exists."""
        route_data = RouteCreateIn(
            description="Test Route",
            method="GET",
            segments=[
                RouteSegmentIn(
                    segment_order=1,
                    type=RouteSegmentType.STATIC,
                    name="api"
                )
            ]
        )
        
        # Mock existing route with same pattern
        existing_route = Mock()
        existing_segment = Mock()
        existing_segment.type = "static"
        existing_segment.name = "api"
        existing_route.segments = [existing_segment]
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [existing_route]
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.create(route_data, self.mock_project)
        
        assert exc_info.value.status_code == 400
        assert "Duplicate route" in exc_info.value.detail

    def test_update_success(self):
        """Test successful route update."""
        route_data = RouteCreateIn(
            description="Updated Route",
            method="POST",
            segments=[]
        )
        
        # Mock get_by_id_or_404 to return route
        with patch.object(self.repository, 'get_by_id_or_404', return_value=self.mock_route):
            # Mock version query
            self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_version
            
            result = self.repository.update(self.route_id, self.version_id, route_data)
            
            assert result == self.mock_route
            assert self.mock_route.description == "Updated Route"
            assert self.mock_route.method == "POST"
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(self.mock_route)

    def test_update_version_not_found(self):
        """Test update fails when version not found."""
        route_data = RouteCreateIn(
            description="Updated Route",
            method="POST",
            segments=[]
        )
        
        # Mock get_by_id_or_404 to return route
        with patch.object(self.repository, 'get_by_id_or_404', return_value=self.mock_route):
            # Mock version not found
            self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                self.repository.update(self.route_id, self.version_id, route_data)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "NodeSetupVersion not found"

    def test_delete_success(self):
        """Test successful route deletion."""
        with patch.object(self.repository, 'get_by_id_or_404', return_value=self.mock_route):
            self.repository.delete(self.route_id, self.mock_project)
            
            self.mock_db.delete.assert_called_once_with(self.mock_route)
            self.mock_db.commit.assert_called_once()

    def test_get_node_setup_found(self):
        """Test successful node setup retrieval."""
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        
        result = self.repository.get_node_setup(self.route_id)
        
        assert result == self.mock_node_setup

    def test_get_node_setup_not_found(self):
        """Test node setup not found returns None."""
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.repository.get_node_setup(self.route_id)
        
        assert result is None

    def test_get_by_id_or_404_found(self):
        """Test successful get_by_id_or_404."""
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_route
        
        result = self.repository.get_by_id_or_404(self.route_id)
        
        assert result == self.mock_route

    def test_get_by_id_or_404_not_found(self):
        """Test get_by_id_or_404 raises 404 when not found."""
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.repository.get_by_id_or_404(self.route_id)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Route not found"

    def test_create_with_variable_segments(self):
        """Test creation with variable segments."""
        route_data = RouteCreateIn(
            description="Variable Route",
            method="GET",
            segments=[
                RouteSegmentIn(
                    segment_order=1,
                    type=RouteSegmentType.STATIC,
                    name="api"
                ),
                RouteSegmentIn(
                    segment_order=2,
                    type=RouteSegmentType.VARIABLE,
                    name="id",
                    default_value="1",
                    variable_type=VariableType.NUMBER
                )
            ]
        )
        
        with patch('repositories.route_repository.Route') as mock_route_class, \
             patch('repositories.route_repository.RouteSegment') as mock_segment_class, \
             patch('repositories.route_repository.NodeSetup') as mock_node_setup_class, \
             patch('repositories.route_repository.NodeSetupVersion') as mock_version_class:
            
            mock_route_class.return_value = self.mock_route
            mock_segment_class.return_value = self.mock_segment
            mock_node_setup_class.return_value = self.mock_node_setup
            mock_version_class.return_value = self.mock_version
            
            # Mock no existing routes
            self.mock_db.query.return_value.filter.return_value.all.return_value = []
            
            result = self.repository.create(route_data, self.mock_project)
            
            assert result == self.mock_route
            # Verify both segments were processed
            assert self.mock_db.add.call_count >= 4  # Route, 2 segments, NodeSetup, Version

    def test_create_empty_segments(self):
        """Test creation with empty segments list."""
        route_data = RouteCreateIn(
            description="Empty Route",
            method="GET",
            segments=[]
        )
        
        with patch('repositories.route_repository.Route') as mock_route_class, \
             patch('repositories.route_repository.NodeSetup') as mock_node_setup_class, \
             patch('repositories.route_repository.NodeSetupVersion') as mock_version_class:
            
            mock_route_class.return_value = self.mock_route
            mock_node_setup_class.return_value = self.mock_node_setup
            mock_version_class.return_value = self.mock_version
            
            # Mock no existing routes
            self.mock_db.query.return_value.filter.return_value.all.return_value = []
            
            result = self.repository.create(route_data, self.mock_project)
            
            assert result == self.mock_route