import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi import HTTPException

from services.blueprint_publish_service import BlueprintPublishService
from models import Blueprint, NodeSetup, NodeSetupVersion
from services.lambda_service import LambdaService
from services.sync_checker_service import SyncCheckerService


@pytest.mark.unit
class TestBlueprintPublishService:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.mock_db = Mock()
        self.mock_lambda_service = Mock(spec=LambdaService)
        self.mock_sync_checker = Mock(spec=SyncCheckerService)
        
        self.service = BlueprintPublishService(
            self.mock_db,
            self.mock_lambda_service,
            self.mock_sync_checker
        )
        
        # Test IDs
        self.blueprint_id = uuid4()
        self.project_id = uuid4()
        self.tenant_id = uuid4()
        self.node_setup_id = uuid4()
        self.version_id = uuid4()
        
        # Mock blueprint
        self.mock_blueprint = Mock(spec=Blueprint)
        self.mock_blueprint.id = self.blueprint_id
        self.mock_blueprint.tenant_id = self.tenant_id
        self.mock_blueprint.name = "Test Blueprint"
        
        # Mock node setup
        self.mock_node_setup = Mock(spec=NodeSetup)
        self.mock_node_setup.id = self.node_setup_id
        self.mock_node_setup.content_type = "blueprint"
        self.mock_node_setup.object_id = self.blueprint_id
        
        # Mock node setup version
        self.mock_version = Mock(spec=NodeSetupVersion)
        self.mock_version.id = self.version_id
        self.mock_version.executable = "print('test blueprint code')"
        self.mock_version.lambda_arn = None
        
        self.mock_node_setup.versions = [self.mock_version]

    def test_publish_success_new_lambda(self):
        """Test successful blueprint publish with new lambda creation."""
        # Mock validate method
        with patch.object(self.service, '_validate', return_value=self.mock_version):
            # Mock sync checker - lambda doesn't exist
            sync_status = {
                'lambda_exists': False,
                'needs_image_update': False,
                'needs_s3_update': False
            }
            self.mock_sync_checker.check_sync_needed.return_value = sync_status
            
            # Mock lambda service - create new lambda
            lambda_arn = f"arn:aws:lambda:us-east-1:123456789:function:node_setup_{self.version_id}_mock"
            self.mock_lambda_service.create_or_update_lambda.return_value = lambda_arn
            
            # Execute publish
            self.service.publish(self.mock_blueprint, self.project_id)
            
            # Verify sync checker was called
            self.mock_sync_checker.check_sync_needed.assert_called_once_with(
                self.mock_version,
                str(self.tenant_id),
                str(self.project_id),
                stage='mock'
            )
            
            # Verify lambda creation was called
            self.mock_lambda_service.create_or_update_lambda.assert_called_once_with(
                f"node_setup_{self.version_id}_mock",
                "print('test blueprint code')",
                str(self.tenant_id),
                str(self.project_id)
            )
            
            # Verify version was updated and committed
            assert self.mock_version.lambda_arn == lambda_arn
            self.mock_db.commit.assert_called_once()

    def test_publish_success_existing_lambda_image_update(self):
        """Test successful blueprint publish with existing lambda requiring image update."""
        with patch.object(self.service, '_validate', return_value=self.mock_version):
            # Mock sync checker - lambda exists but needs image update
            sync_status = {
                'lambda_exists': True,
                'needs_image_update': True,
                'needs_s3_update': False
            }
            self.mock_sync_checker.check_sync_needed.return_value = sync_status
            
            # Mock lambda service - update image
            lambda_arn = f"arn:aws:lambda:us-east-1:123456789:function:node_setup_{self.version_id}_mock"
            self.mock_lambda_service.update_function_image.return_value = lambda_arn
            
            self.service.publish(self.mock_blueprint, self.project_id)
            
            # Verify image update was called
            self.mock_lambda_service.update_function_image.assert_called_once_with(
                f"node_setup_{self.version_id}_mock",
                str(self.tenant_id),
                str(self.project_id)
            )
            
            # Verify create_or_update_lambda was NOT called
            self.mock_lambda_service.create_or_update_lambda.assert_not_called()
            
            assert self.mock_version.lambda_arn == lambda_arn
            self.mock_db.commit.assert_called_once()

    def test_publish_success_existing_lambda_s3_update(self):
        """Test successful blueprint publish with existing lambda requiring S3 update."""
        with patch.object(self.service, '_validate', return_value=self.mock_version):
            # Mock sync checker - lambda exists but needs S3 update
            sync_status = {
                'lambda_exists': True,
                'needs_image_update': False,
                'needs_s3_update': True,
                's3_key': f'lambda_code/{self.version_id}.zip'
            }
            self.mock_sync_checker.check_sync_needed.return_value = sync_status
            
            # Mock lambda service - get existing ARN
            lambda_arn = f"arn:aws:lambda:us-east-1:123456789:function:node_setup_{self.version_id}_mock"
            self.mock_lambda_service.get_function_arn.return_value = lambda_arn
            
            with patch('services.blueprint_publish_service.settings') as mock_settings:
                mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = 'test-lambda-bucket'
                
                self.service.publish(self.mock_blueprint, self.project_id)
            
            # Verify S3 upload was called
            self.mock_lambda_service.upload_code_to_s3.assert_called_once_with(
                'test-lambda-bucket',
                f'lambda_code/{self.version_id}.zip',
                "print('test blueprint code')"
            )
            
            # Verify existing function ARN was retrieved
            self.mock_lambda_service.get_function_arn.assert_called_once_with(
                f"node_setup_{self.version_id}_mock"
            )
            
            assert self.mock_version.lambda_arn == lambda_arn
            self.mock_db.commit.assert_called_once()

    def test_publish_success_existing_lambda_no_updates(self):
        """Test successful blueprint publish with existing lambda requiring no updates."""
        with patch.object(self.service, '_validate', return_value=self.mock_version):
            # Mock sync checker - lambda exists, no updates needed
            sync_status = {
                'lambda_exists': True,
                'needs_image_update': False,
                'needs_s3_update': False
            }
            self.mock_sync_checker.check_sync_needed.return_value = sync_status
            
            # Mock lambda service - get existing ARN
            lambda_arn = f"arn:aws:lambda:us-east-1:123456789:function:node_setup_{self.version_id}_mock"
            self.mock_lambda_service.get_function_arn.return_value = lambda_arn
            
            self.service.publish(self.mock_blueprint, self.project_id)
            
            # Verify no create/update operations were called
            self.mock_lambda_service.create_or_update_lambda.assert_not_called()
            self.mock_lambda_service.update_function_image.assert_not_called()
            self.mock_lambda_service.upload_code_to_s3.assert_not_called()
            
            # Verify existing function ARN was retrieved
            self.mock_lambda_service.get_function_arn.assert_called_once()
            
            assert self.mock_version.lambda_arn == lambda_arn
            self.mock_db.commit.assert_called_once()

    def test_publish_with_combined_updates(self):
        """Test blueprint publish with both image and S3 updates needed."""
        with patch.object(self.service, '_validate', return_value=self.mock_version):
            # Mock sync checker - lambda exists, needs both updates
            sync_status = {
                'lambda_exists': True,
                'needs_image_update': True,
                'needs_s3_update': True,
                's3_key': f'lambda_code/{self.version_id}.zip'
            }
            self.mock_sync_checker.check_sync_needed.return_value = sync_status
            
            # Mock lambda service
            lambda_arn = f"arn:aws:lambda:us-east-1:123456789:function:node_setup_{self.version_id}_mock"
            self.mock_lambda_service.update_function_image.return_value = lambda_arn
            
            with patch('services.blueprint_publish_service.settings') as mock_settings:
                mock_settings.AWS_S3_LAMBDA_BUCKET_NAME = 'test-lambda-bucket'
                
                self.service.publish(self.mock_blueprint, self.project_id)
            
            # Verify both image update and S3 upload were called
            self.mock_lambda_service.update_function_image.assert_called_once()
            self.mock_lambda_service.upload_code_to_s3.assert_called_once()
            
            # Verify get_function_arn was NOT called since update_function_image returned ARN
            self.mock_lambda_service.get_function_arn.assert_not_called()
            
            assert self.mock_version.lambda_arn == lambda_arn

    def test_validate_invalid_blueprint_type(self):
        """Test validation fails with non-Blueprint object."""
        invalid_object = Mock()  # Not a Blueprint
        
        with pytest.raises(HTTPException) as exc_info:
            self.service._validate(invalid_object)
        
        assert exc_info.value.status_code == 400
        assert "Only Blueprint publishing is supported" in exc_info.value.detail

    def test_validate_no_node_setup_found(self):
        """Test validation fails when no node setup is found."""
        # Mock database query returning None
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.service._validate(self.mock_blueprint)
        
        assert exc_info.value.status_code == 404
        assert "No published version found for this Blueprint" in exc_info.value.detail

    def test_validate_no_versions_available(self):
        """Test validation fails when node setup has no versions."""
        # Mock node setup with empty versions list
        mock_node_setup = Mock(spec=NodeSetup)
        mock_node_setup.versions = []
        
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_node_setup
        
        with pytest.raises(HTTPException) as exc_info:
            self.service._validate(self.mock_blueprint)
        
        assert exc_info.value.status_code == 404
        assert "No published version found for this Blueprint" in exc_info.value.detail

    def test_validate_success(self):
        """Test successful validation returns latest version."""
        # Mock database query
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = self.mock_node_setup
        
        result = self.service._validate(self.mock_blueprint)
        
        assert result == self.mock_version
        self.mock_db.query.assert_called_once_with(NodeSetup)

    def test_publish_lambda_service_exception(self):
        """Test publish handles lambda service exceptions."""
        with patch.object(self.service, '_validate', return_value=self.mock_version):
            # Mock sync checker
            sync_status = {'lambda_exists': False}
            self.mock_sync_checker.check_sync_needed.return_value = sync_status
            
            # Mock lambda service to raise exception
            self.mock_lambda_service.create_or_update_lambda.side_effect = Exception("Lambda error")
            
            with pytest.raises(Exception) as exc_info:
                self.service.publish(self.mock_blueprint, self.project_id)
            
            assert "Lambda error" in str(exc_info.value)
            # Verify commit was not called due to exception
            self.mock_db.commit.assert_not_called()

    def test_publish_sync_checker_exception(self):
        """Test publish handles sync checker exceptions."""
        with patch.object(self.service, '_validate', return_value=self.mock_version):
            # Mock sync checker to raise exception
            self.mock_sync_checker.check_sync_needed.side_effect = Exception("Sync check error")
            
            with pytest.raises(Exception) as exc_info:
                self.service.publish(self.mock_blueprint, self.project_id)
            
            assert "Sync check error" in str(exc_info.value)

    def test_get_blueprint_publish_service_dependency(self):
        """Test the dependency injection function."""
        from services.blueprint_publish_service import get_blueprint_publish_service
        
        mock_db = Mock()
        mock_lambda_service = Mock()
        mock_sync_checker = Mock()
        
        service = get_blueprint_publish_service(mock_db, mock_lambda_service, mock_sync_checker)
        
        assert isinstance(service, BlueprintPublishService)
        assert service.db == mock_db
        assert service.lambda_service == mock_lambda_service
        assert service.sync_checker == mock_sync_checker

    def test_publish_with_complex_executable_code(self):
        """Test publish with complex executable code."""
        complex_code = """
import json
import boto3

def handler(event, context):
    # Complex blueprint logic
    data = json.loads(event['body'])
    s3 = boto3.client('s3')
    
    result = process_data(data)
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }

def process_data(data):
    return {'processed': True, 'data': data}
"""
        
        # Update mock version with complex code
        self.mock_version.executable = complex_code
        
        with patch.object(self.service, '_validate', return_value=self.mock_version):
            sync_status = {'lambda_exists': False}
            self.mock_sync_checker.check_sync_needed.return_value = sync_status
            
            lambda_arn = f"arn:aws:lambda:us-east-1:123456789:function:node_setup_{self.version_id}_mock"
            self.mock_lambda_service.create_or_update_lambda.return_value = lambda_arn
            
            self.service.publish(self.mock_blueprint, self.project_id)
            
            # Verify complex code was passed to lambda service
            self.mock_lambda_service.create_or_update_lambda.assert_called_once_with(
                f"node_setup_{self.version_id}_mock",
                complex_code,
                str(self.tenant_id),
                str(self.project_id)
            )

    def test_publish_with_special_characters_in_code(self):
        """Test publish with executable code containing special characters."""
        special_code = """
# -*- coding: utf-8 -*-
def handler(event, context):
    message = "Hello, 世界! 🌍"
    return {'message': message, 'symbols': '!@#$%^&*()'}
"""
        
        self.mock_version.executable = special_code
        
        with patch.object(self.service, '_validate', return_value=self.mock_version):
            sync_status = {'lambda_exists': False}
            self.mock_sync_checker.check_sync_needed.return_value = sync_status
            
            lambda_arn = f"arn:aws:lambda:us-east-1:123456789:function:node_setup_{self.version_id}_mock"
            self.mock_lambda_service.create_or_update_lambda.return_value = lambda_arn
            
            self.service.publish(self.mock_blueprint, self.project_id)
            
            # Verify special characters are handled correctly
            self.mock_lambda_service.create_or_update_lambda.assert_called_once_with(
                f"node_setup_{self.version_id}_mock",
                special_code,
                str(self.tenant_id),
                str(self.project_id)
            )

    def test_publish_multiple_versions_uses_latest(self):
        """Test that publish uses the latest version when multiple versions exist."""
        # Create multiple versions
        older_version = Mock(spec=NodeSetupVersion)
        older_version.id = uuid4()
        older_version.executable = "print('old version')"
        
        latest_version = Mock(spec=NodeSetupVersion)
        latest_version.id = self.version_id
        latest_version.executable = "print('latest version')"
        latest_version.lambda_arn = None
        
        # Mock node setup with multiple versions (latest is last)
        self.mock_node_setup.versions = [older_version, latest_version]
        
        with patch.object(self.service, '_validate', return_value=latest_version):
            sync_status = {'lambda_exists': False}
            self.mock_sync_checker.check_sync_needed.return_value = sync_status
            
            lambda_arn = f"arn:aws:lambda:us-east-1:123456789:function:node_setup_{self.version_id}_mock"
            self.mock_lambda_service.create_or_update_lambda.return_value = lambda_arn
            
            self.service.publish(self.mock_blueprint, self.project_id)
            
            # Verify latest version's code was used
            self.mock_lambda_service.create_or_update_lambda.assert_called_once_with(
                f"node_setup_{self.version_id}_mock",
                "print('latest version')",
                str(self.tenant_id),
                str(self.project_id)
            )