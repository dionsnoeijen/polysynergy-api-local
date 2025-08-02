import pytest
from unittest.mock import patch, Mock

from services.s3_service import get_s3_service


@pytest.mark.unit
class TestS3Service:
    
    @patch('services.s3_service.S3Service')
    def test_get_s3_service_public(self, mock_s3_service_class, mock_settings):
        """Test getting S3 service for public bucket."""
        mock_s3_instance = Mock()
        mock_s3_service_class.return_value = mock_s3_instance
        
        with patch('services.s3_service.settings', mock_settings):
            result = get_s3_service("tenant-123", public=True)
        
        mock_s3_service_class.assert_called_once_with(
            tenant_id="tenant-123",
            public=True,
            access_key=mock_settings.AWS_ACCESS_KEY_ID,
            secret_key=mock_settings.AWS_SECRET_ACCESS_KEY,
            region=mock_settings.AWS_REGION
        )
        assert result == mock_s3_instance
    
    @patch('services.s3_service.S3Service')
    def test_get_s3_service_private(self, mock_s3_service_class, mock_settings):
        """Test getting S3 service for private bucket."""
        mock_s3_instance = Mock()
        mock_s3_service_class.return_value = mock_s3_instance
        
        with patch('services.s3_service.settings', mock_settings):
            result = get_s3_service("tenant-456", public=False)
        
        mock_s3_service_class.assert_called_once_with(
            tenant_id="tenant-456",
            public=False,
            access_key=mock_settings.AWS_ACCESS_KEY_ID,
            secret_key=mock_settings.AWS_SECRET_ACCESS_KEY,
            region=mock_settings.AWS_REGION
        )
        assert result == mock_s3_instance