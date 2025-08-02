import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime
from fastapi import HTTPException

from services.route_publish_service import RoutePublishService, get_route_publish_service
from models import Route, NodeSetup, NodeSetupVersion, NodeSetupVersionStage, Stage, Project, Tenant
from services.lambda_service import LambdaService
from services.router_service import RouterService
from services.sync_checker_service import SyncCheckerService


@pytest.mark.unit
class TestRoutePublishService:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.route_id = uuid4()
        self.project_id = uuid4()
        self.tenant_id = uuid4()
        self.node_setup_id = uuid4()
        self.version_id = uuid4()
        self.stage_id = uuid4()
        
        # Mock tenant
        self.mock_tenant = Mock(spec=Tenant)
        self.mock_tenant.id = self.tenant_id
        
        # Mock project
        self.mock_project = Mock(spec=Project)
        self.mock_project.id = self.project_id
        self.mock_project.tenant = self.mock_tenant
        
        # Mock route
        self.mock_route = Mock(spec=Route)
        self.mock_route.id = self.route_id
        self.mock_route.project = self.mock_project
        
        # Mock node setup
        self.mock_node_setup = Mock(spec=NodeSetup)
        self.mock_node_setup.id = self.node_setup_id
        
        # Mock node setup version
        self.mock_version = Mock(spec=NodeSetupVersion)
        self.mock_version.id = self.version_id
        self.mock_version.executable = "print('Hello World')"
        self.mock_version.executable_hash = "hash123"
        self.mock_version.created_at = datetime.now()
        self.mock_version.node_setup = self.mock_node_setup
        
        # Mock stage
        self.mock_stage = Mock(spec=Stage)
        self.mock_stage.id = self.stage_id
        self.mock_stage.name = "production"
        
        # Mock dependencies
        self.mock_db = Mock()
        self.mock_lambda_service = Mock(spec=LambdaService)
        self.mock_router_service = Mock(spec=RouterService)
        self.mock_sync_checker = Mock(spec=SyncCheckerService)
        
        # Create service instance
        self.service = RoutePublishService(
            db=self.mock_db,
            lambda_service=self.mock_lambda_service,
            router_service=self.mock_router_service,
            sync_checker=self.mock_sync_checker
        )

    def test_route_publish_service_initialization(self):
        """Test that RoutePublishService initializes correctly with dependencies."""
        assert self.service.db == self.mock_db
        assert self.service.lambda_service == self.mock_lambda_service
        assert self.service.router_service == self.mock_router_service
        assert self.service.sync_checker == self.mock_sync_checker

    def test_validate_success(self):
        """Test successful validation of route."""
        # Mock node setup query
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        
        # Mock versions
        self.mock_node_setup.versions = [self.mock_version]
        
        result = self.service._validate(self.mock_route)
        
        assert result == self.mock_version
        self.mock_db.query.assert_called_with(NodeSetup)

    def test_validate_non_route_object(self):
        """Test validation failure with non-Route object."""
        not_a_route = Mock()
        not_a_route.__class__ = Mock()
        not_a_route.__class__.__name__ = "NotRoute"
        
        with pytest.raises(HTTPException) as exc_info:
            self.service._validate(not_a_route)
        
        assert exc_info.value.status_code == 400
        assert "Only Route publishing is supported" in exc_info.value.detail

    def test_validate_no_node_setup(self):
        """Test validation failure when NodeSetup doesn't exist."""
        # Mock node setup query returning None
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.service._validate(self.mock_route)
        
        assert exc_info.value.status_code == 404
        assert "NodeSetup not found" in exc_info.value.detail

    def test_validate_no_versions(self):
        """Test validation failure when no versions exist."""
        # Mock node setup query
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        
        # Mock empty versions
        self.mock_node_setup.versions = []
        
        with pytest.raises(HTTPException) as exc_info:
            self.service._validate(self.mock_route)
        
        assert exc_info.value.status_code == 404
        assert "No version found for this route" in exc_info.value.detail

    def test_validate_no_executable(self):
        """Test validation failure when version has no executable."""
        # Mock node setup query
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        
        # Mock version without executable
        version_without_executable = Mock(spec=NodeSetupVersion)
        version_without_executable.executable = None
        version_without_executable.created_at = datetime.now()
        self.mock_node_setup.versions = [version_without_executable]
        
        with pytest.raises(HTTPException) as exc_info:
            self.service._validate(self.mock_route)
        
        assert exc_info.value.status_code == 400
        assert "No executable defined" in exc_info.value.detail

    def test_validate_multiple_versions_selects_latest(self):
        """Test validation selects the latest version when multiple exist."""
        # Mock node setup query
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        
        # Create multiple versions with different timestamps
        older_version = Mock(spec=NodeSetupVersion)
        older_version.created_at = datetime(2023, 1, 1)
        older_version.executable = "old code"
        
        newer_version = Mock(spec=NodeSetupVersion)
        newer_version.created_at = datetime(2023, 12, 1)
        newer_version.executable = "new code"
        
        self.mock_node_setup.versions = [older_version, newer_version]
        
        result = self.service._validate(self.mock_route)
        
        assert result == newer_version

    @patch('services.route_publish_service.settings')
    def test_sync_lambda_lambda_not_exists(self, mock_settings):
        """Test sync_lambda when lambda doesn't exist."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-bucket"
        
        # Mock validation
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        self.mock_node_setup.versions = [self.mock_version]
        
        # Mock sync checker - lambda doesn't exist
        sync_status = {
            'lambda_exists': False,
            'needs_image_update': False,
            'needs_s3_update': False,
            's3_key': 'test-key'
        }
        self.mock_sync_checker.check_sync_needed.return_value = sync_status
        
        self.service.sync_lambda(self.mock_route, 'production')
        
        # Verify lambda creation was called
        self.mock_lambda_service.create_or_update_lambda.assert_called_once_with(
            f"node_setup_{self.version_id}_production",
            self.mock_version.executable,
            str(self.tenant_id),
            str(self.project_id)
        )
        
        # Verify sync checker was called
        self.mock_sync_checker.check_sync_needed.assert_called_once_with(
            self.mock_version,
            str(self.tenant_id),
            str(self.project_id),
            'production'
        )

    @patch('services.route_publish_service.settings')
    def test_sync_lambda_lambda_exists_needs_image_update(self, mock_settings):
        """Test sync_lambda when lambda exists but needs image update."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-bucket"
        
        # Mock validation
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        self.mock_node_setup.versions = [self.mock_version]
        
        # Mock sync checker - lambda exists, needs image update
        sync_status = {
            'lambda_exists': True,
            'needs_image_update': True,
            'needs_s3_update': False,
            's3_key': 'test-key'
        }
        self.mock_sync_checker.check_sync_needed.return_value = sync_status
        
        self.service.sync_lambda(self.mock_route, 'staging')
        
        # Verify image update was called
        self.mock_lambda_service.update_function_image.assert_called_once_with(
            f"node_setup_{self.version_id}_staging",
            str(self.tenant_id),
            str(self.project_id)
        )
        
        # Verify create wasn't called
        self.mock_lambda_service.create_or_update_lambda.assert_not_called()

    @patch('services.route_publish_service.settings')
    def test_sync_lambda_lambda_exists_needs_s3_update(self, mock_settings):
        """Test sync_lambda when lambda exists but needs S3 update."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-lambda-bucket"
        
        # Mock validation
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        self.mock_node_setup.versions = [self.mock_version]
        
        # Mock sync checker - lambda exists, needs S3 update
        sync_status = {
            'lambda_exists': True,
            'needs_image_update': False,
            'needs_s3_update': True,
            's3_key': f'{self.tenant_id}/{self.project_id}/test-key.py'
        }
        self.mock_sync_checker.check_sync_needed.return_value = sync_status
        
        self.service.sync_lambda(self.mock_route, 'development')
        
        # Verify S3 upload was called
        self.mock_lambda_service.upload_code_to_s3.assert_called_once_with(
            "test-lambda-bucket",
            sync_status['s3_key'],
            self.mock_version.executable
        )
        
        # Verify other methods weren't called
        self.mock_lambda_service.create_or_update_lambda.assert_not_called()
        self.mock_lambda_service.update_function_image.assert_not_called()

    @patch('services.route_publish_service.settings')
    def test_sync_lambda_lambda_exists_needs_both_updates(self, mock_settings):
        """Test sync_lambda when lambda exists but needs both image and S3 updates."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-bucket"
        
        # Mock validation
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        self.mock_node_setup.versions = [self.mock_version]
        
        # Mock sync checker - lambda exists, needs both updates
        sync_status = {
            'lambda_exists': True,
            'needs_image_update': True,
            'needs_s3_update': True,
            's3_key': 'both-updates-key.py'
        }
        self.mock_sync_checker.check_sync_needed.return_value = sync_status
        
        self.service.sync_lambda(self.mock_route, 'production')
        
        # Verify both image and S3 updates were called
        self.mock_lambda_service.update_function_image.assert_called_once()
        self.mock_lambda_service.upload_code_to_s3.assert_called_once()
        
        # Verify create wasn't called
        self.mock_lambda_service.create_or_update_lambda.assert_not_called()

    @patch('services.route_publish_service.settings')
    def test_sync_lambda_lambda_exists_no_updates_needed(self, mock_settings):
        """Test sync_lambda when lambda exists and is up to date."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-bucket"
        
        # Mock validation
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        self.mock_node_setup.versions = [self.mock_version]
        
        # Mock sync checker - lambda exists, no updates needed
        sync_status = {
            'lambda_exists': True,
            'needs_image_update': False,
            'needs_s3_update': False,
            's3_key': 'no-updates-key.py'
        }
        self.mock_sync_checker.check_sync_needed.return_value = sync_status
        
        self.service.sync_lambda(self.mock_route, 'production')
        
        # Verify no lambda service methods were called
        self.mock_lambda_service.create_or_update_lambda.assert_not_called()
        self.mock_lambda_service.update_function_image.assert_not_called()
        self.mock_lambda_service.upload_code_to_s3.assert_not_called()

    def test_update_route_success(self):
        """Test successful route update."""
        # Mock successful router response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'route_id': str(self.route_id)}
        self.mock_router_service.update_route.return_value = mock_response
        
        result = self.service.update_route(self.mock_route, self.mock_version, 'production')
        
        # Verify router service was called
        self.mock_router_service.update_route.assert_called_once_with(
            self.mock_route, self.mock_version, 'production'
        )
        
        # Verify response
        assert result == {'success': True, 'route_id': str(self.route_id)}

    def test_update_route_failure(self):
        """Test route update failure."""
        # Mock failed router response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        self.mock_router_service.update_route.return_value = mock_response
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.update_route(self.mock_route, self.mock_version, 'production')
        
        assert exc_info.value.status_code == 500
        assert "Router update failed" in exc_info.value.detail

    def test_update_route_non_200_status(self):
        """Test route update with non-200 status codes."""
        # Test various non-200 status codes
        for status_code in [400, 404, 422, 500, 503]:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.text = f"Error {status_code}"
            self.mock_router_service.update_route.return_value = mock_response
            
            with pytest.raises(HTTPException) as exc_info:
                self.service.update_route(self.mock_route, self.mock_version, 'production')
            
            assert exc_info.value.status_code == 500
            assert "Router update failed" in exc_info.value.detail

    @patch('services.route_publish_service.settings')
    def test_publish_success(self, mock_settings):
        """Test successful route publishing."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-bucket"
        
        # Mock validation
        self.mock_node_setup.versions = [self.mock_version]
        
        # Mock db.query to return different results for different queries
        def mock_query_side_effect(model):
            mock_query_result = Mock()
            if model == NodeSetup:
                mock_query_result.filter_by.return_value.first.return_value = self.mock_node_setup
            elif model == Stage:
                mock_query_result.filter_by.return_value.one.return_value = self.mock_stage
            return mock_query_result
        
        self.mock_db.query.side_effect = mock_query_side_effect
        
        # Mock sync checker
        sync_status = {
            'lambda_exists': False,
            'needs_image_update': False,
            'needs_s3_update': False,
            's3_key': 'test-key'
        }
        self.mock_sync_checker.check_sync_needed.return_value = sync_status
        
        # Mock router response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        self.mock_router_service.update_route.return_value = mock_response
        
        self.service.publish(self.mock_route, 'production')
        
        # Verify lambda was created
        self.mock_lambda_service.create_or_update_lambda.assert_called_once()
        
        # Verify router was updated
        self.mock_router_service.update_route.assert_called_once()
        
        # Verify stage link was created
        self.mock_db.merge.assert_called_once()
        self.mock_db.commit.assert_called_once()

    @patch('services.route_publish_service.settings')
    def test_publish_default_stage(self, mock_settings):
        """Test publishing with default stage."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-bucket"
        
        # Mock validation
        self.mock_node_setup.versions = [self.mock_version]
        
        # Mock db.query to return different results for different queries
        def mock_query_side_effect(model):
            mock_query_result = Mock()
            if model == NodeSetup:
                mock_query_result.filter_by.return_value.first.return_value = self.mock_node_setup
            elif model == Stage:
                mock_query_result.filter_by.return_value.one.return_value = self.mock_stage
            return mock_query_result
        
        self.mock_db.query.side_effect = mock_query_side_effect
        
        # Mock sync checker
        sync_status = {
            'lambda_exists': True,
            'needs_image_update': False,
            'needs_s3_update': False,
            's3_key': 'test-key'
        }
        self.mock_sync_checker.check_sync_needed.return_value = sync_status
        
        # Mock router response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        self.mock_router_service.update_route.return_value = mock_response
        
        # Test with default stage (should be 'prod')
        self.service.publish(self.mock_route)
        
        # Verify sync_lambda was called with default 'prod' stage
        self.mock_sync_checker.check_sync_needed.assert_called_with(
            self.mock_version,
            str(self.tenant_id),
            str(self.project_id),
            'prod'
        )

    @patch('services.route_publish_service.settings')
    def test_publish_validation_failure(self, mock_settings):
        """Test publishing fails when validation fails."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-bucket"
        
        # Mock validation failure (no node setup)
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.publish(self.mock_route, 'production')
        
        assert exc_info.value.status_code == 404
        
        # Verify no services were called
        self.mock_lambda_service.create_or_update_lambda.assert_not_called()
        self.mock_router_service.update_route.assert_not_called()
        self.mock_db.merge.assert_not_called()
        self.mock_db.commit.assert_not_called()

    @patch('services.route_publish_service.settings')
    def test_publish_router_failure(self, mock_settings):
        """Test publishing fails when router update fails."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-bucket"
        
        # Mock validation
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        self.mock_node_setup.versions = [self.mock_version]
        
        # Mock sync checker
        sync_status = {
            'lambda_exists': True,
            'needs_image_update': False,
            'needs_s3_update': False,
            's3_key': 'test-key'
        }
        self.mock_sync_checker.check_sync_needed.return_value = sync_status
        
        # Mock router failure
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Router error"
        self.mock_router_service.update_route.return_value = mock_response
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.publish(self.mock_route, 'production')
        
        assert exc_info.value.status_code == 500
        assert "Router update failed" in exc_info.value.detail
        
        # Verify database operations weren't performed
        self.mock_db.merge.assert_not_called()
        self.mock_db.commit.assert_not_called()

    def test_publish_creates_stage_link(self):
        """Test that publish creates the correct NodeSetupVersionStage link."""
        # Mock validation
        self.mock_node_setup.versions = [self.mock_version]
        
        # Mock db.query to return different results for different queries
        def mock_query_side_effect(model):
            mock_query_result = Mock()
            if model == NodeSetup:
                mock_query_result.filter_by.return_value.first.return_value = self.mock_node_setup
            elif model == Stage:
                mock_query_result.filter_by.return_value.one.return_value = self.mock_stage
            return mock_query_result
        
        self.mock_db.query.side_effect = mock_query_side_effect
        
        # Mock sync checker
        sync_status = {
            'lambda_exists': True,
            'needs_image_update': False,
            'needs_s3_update': False,
            's3_key': 'test-key'
        }
        self.mock_sync_checker.check_sync_needed.return_value = sync_status
        
        # Mock router response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        self.mock_router_service.update_route.return_value = mock_response
        
        self.service.publish(self.mock_route, 'production')
        
        # Verify merge was called
        merge_call = self.mock_db.merge.call_args[0][0]
        assert isinstance(merge_call, NodeSetupVersionStage)
        assert merge_call.stage_id == self.stage_id
        assert merge_call.node_setup_id == self.node_setup_id
        assert merge_call.version_id == self.version_id
        assert merge_call.executable_hash == self.mock_version.executable_hash

    def test_get_route_publish_service_factory_function(self):
        """Test that get_route_publish_service creates a RoutePublishService instance."""
        mock_db = Mock()
        mock_lambda_service = Mock()
        mock_router_service = Mock()
        mock_sync_checker = Mock()
        
        result = get_route_publish_service(
            db=mock_db,
            lambda_service=mock_lambda_service,
            router_service=mock_router_service,
            sync_checker=mock_sync_checker
        )
        
        assert isinstance(result, RoutePublishService)
        assert result.db == mock_db
        assert result.lambda_service == mock_lambda_service
        assert result.router_service == mock_router_service
        assert result.sync_checker == mock_sync_checker

    def test_validate_with_empty_executable_string(self):
        """Test validation failure when version has empty executable string."""
        # Mock node setup query
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        
        # Mock version with empty executable
        version_with_empty_executable = Mock(spec=NodeSetupVersion)
        version_with_empty_executable.executable = ""
        version_with_empty_executable.created_at = datetime.now()
        self.mock_node_setup.versions = [version_with_empty_executable]
        
        with pytest.raises(HTTPException) as exc_info:
            self.service._validate(self.mock_route)
        
        assert exc_info.value.status_code == 400
        assert "No executable defined" in exc_info.value.detail

    @patch('services.route_publish_service.settings')
    def test_sync_lambda_with_different_stages(self, mock_settings):
        """Test sync_lambda with different stage names."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-bucket"
        
        # Mock validation
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        self.mock_node_setup.versions = [self.mock_version]
        
        # Test different stages
        stages = ['dev', 'test', 'staging', 'prod', 'production']
        
        for stage in stages:
            # Mock sync checker
            sync_status = {
                'lambda_exists': False,
                'needs_image_update': False,
                'needs_s3_update': False,
                's3_key': f'test-key-{stage}'
            }
            self.mock_sync_checker.check_sync_needed.return_value = sync_status
            
            self.service.sync_lambda(self.mock_route, stage)
            
            # Verify correct function name was used
            expected_function_name = f"node_setup_{self.version_id}_{stage}"
            self.mock_lambda_service.create_or_update_lambda.assert_called_with(
                expected_function_name,
                self.mock_version.executable,
                str(self.tenant_id),
                str(self.project_id)
            )
            
            # Reset mock for next iteration
            self.mock_lambda_service.reset_mock()

    def test_validate_error_message_consistency(self):
        """Test that validation error message mentions 'schedule' instead of 'route' (bug in original code)."""
        # Mock node setup query returning None
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.service._validate(self.mock_route)
        
        # Note: The original code has a bug - it says "schedule" instead of "route"
        assert exc_info.value.status_code == 404
        assert "NodeSetup not found for this schedule" in exc_info.value.detail

    @patch('services.route_publish_service.settings')
    def test_publish_stage_query_parameters(self, mock_settings):
        """Test that publish uses correct parameters when querying for stage."""
        mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = "test-bucket"
        
        # Mock validation
        self.mock_node_setup.versions = [self.mock_version]
        
        # Mock stage query - create a separate mock to verify call parameters
        mock_stage_query_result = Mock()
        mock_stage_query_result.filter_by.return_value.one.return_value = self.mock_stage
        
        # Mock db.query to return different results for different queries
        def mock_query_side_effect(model):
            mock_query_result = Mock()
            if model == NodeSetup:
                mock_query_result.filter_by.return_value.first.return_value = self.mock_node_setup
            elif model == Stage:
                return mock_stage_query_result
            return mock_query_result
        
        self.mock_db.query.side_effect = mock_query_side_effect
        
        # Mock sync checker
        sync_status = {
            'lambda_exists': True,
            'needs_image_update': False,
            'needs_s3_update': False,
            's3_key': 'test-key'
        }
        self.mock_sync_checker.check_sync_needed.return_value = sync_status
        
        # Mock router response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        self.mock_router_service.update_route.return_value = mock_response
        
        stage_name = 'custom-stage'
        self.service.publish(self.mock_route, stage_name)
        
        # Verify stage query was called with correct parameters
        mock_stage_query_result.filter_by.assert_called_with(
            project=self.mock_project,
            name=stage_name
        )