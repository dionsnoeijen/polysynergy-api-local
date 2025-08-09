import pytest
import io
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from services.file_manager_service import FileManagerService
from schemas.file_manager import FileInfo, DirectoryInfo


class TestFileManagerService:
    
    @patch.dict('os.environ', {'AWS_ACCESS_KEY_ID': 'test', 'AWS_SECRET_ACCESS_KEY': 'test'})
    @patch('services.file_manager_service.boto3')
    def setup_method(self, mock_boto3):
        """Setup test fixtures"""
        self.mock_s3_service = Mock()
        self.mock_s3_service.bucket_name = "test-bucket"
        self.mock_s3_service.region = "us-east-1"
        self.mock_s3_service.public = True
        self.mock_s3_service.s3_client = Mock()
        
        # Mock boto3 client
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        mock_s3_client.head_bucket.return_value = {}
        
        self.project_id = "test-project-123"
        self.tenant_id = "test-tenant-456"
        self.file_manager = FileManagerService(
            s3_service=self.mock_s3_service,
            project_id=self.project_id,
            tenant_id=self.tenant_id
        )
    
    def test_normalize_path(self):
        """Test path normalization"""
        assert self.file_manager._normalize_path(None) == ""
        assert self.file_manager._normalize_path("") == ""
        assert self.file_manager._normalize_path("/path/to/file") == "path/to/file"
        assert self.file_manager._normalize_path("path/to/file/") == "path/to/file"
        assert self.file_manager._normalize_path("//path//to//file//") == "path/to/file"
    
    def test_get_full_s3_key(self):
        """Test S3 key generation"""
        expected_base = f"{self.project_id}/files/"
        
        assert self.file_manager._get_full_s3_key("") == expected_base.rstrip("/")
        assert self.file_manager._get_full_s3_key("folder/file.txt") == f"{expected_base}folder/file.txt"
        assert self.file_manager._get_full_s3_key("/folder/file.txt") == f"{expected_base}folder/file.txt"
    
    def test_extract_file_info_from_s3_object(self):
        """Test file info extraction from S3 object"""
        s3_object = {
            "Key": f"{self.project_id}/files/documents/test.pdf",
            "Size": 1024,
            "LastModified": datetime(2023, 1, 1, 12, 0, 0)
        }
        
        file_info = self.file_manager._extract_file_info_from_s3_object(s3_object)
        
        assert file_info.name == "test.pdf"
        assert file_info.path == "documents/test.pdf"
        assert file_info.size == 1024
        assert file_info.content_type == "application/pdf"
        assert not file_info.is_directory
        assert file_info.url is not None
    
    def test_list_directory_contents_empty(self):
        """Test listing empty directory"""
        self.mock_s3_service.s3_client.list_objects_v2.return_value = {
            "Contents": [],
            "CommonPrefixes": []
        }
        
        result = self.file_manager.list_directory_contents()
        
        assert result.path == ""
        assert len(result.files) == 0
        assert len(result.directories) == 0
        assert result.total_files == 0
        assert result.total_directories == 0
    
    def test_list_directory_contents_with_files_and_dirs(self):
        """Test listing directory with files and subdirectories"""
        base_path = f"{self.project_id}/files/"
        
        self.mock_s3_service.s3_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": f"{base_path}file1.txt",
                    "Size": 100,
                    "LastModified": datetime.now()
                },
                {
                    "Key": f"{base_path}file2.jpg",
                    "Size": 2048,
                    "LastModified": datetime.now()
                }
            ],
            "CommonPrefixes": [
                {"Prefix": f"{base_path}documents/"},
                {"Prefix": f"{base_path}images/"}
            ]
        }
        
        result = self.file_manager.list_directory_contents()
        
        assert len(result.files) == 2
        assert len(result.directories) == 2
        assert result.files[0].name == "file1.txt"
        assert result.files[1].name == "file2.jpg"
        assert result.directories[0].name == "documents"
        assert result.directories[1].name == "images"
    
    def test_upload_file_success(self):
        """Test successful file upload"""
        file_content = b"test file content"
        filename = "test.txt"
        
        with patch.object(self.file_manager.s3_service.s3_client, 'upload_fileobj') as mock_upload:
            mock_upload.return_value = None
            
            result = self.file_manager.upload_file(
                file_content=file_content,
                filename=filename
            )
            
            assert result.success is True
            assert result.file_path == filename
            assert result.size == len(file_content)
            assert result.content_type == "text/plain"
            mock_upload.assert_called_once()
    
    def test_upload_file_with_folder_path(self):
        """Test file upload to specific folder"""
        file_content = b"test content"
        filename = "test.txt"
        folder_path = "documents/subfolder"
        
        with patch.object(self.file_manager.s3_service.s3_client, 'upload_fileobj') as mock_upload:
            mock_upload.return_value = None
            
            result = self.file_manager.upload_file(
                file_content=file_content,
                filename=filename,
                folder_path=folder_path
            )
            
            expected_path = f"{folder_path}/{filename}"
            assert result.file_path == expected_path
    
    def test_delete_file_success(self):
        """Test successful file deletion"""
        file_path = "test/file.txt"
        
        self.mock_s3_service.s3_client.delete_object.return_value = {}
        
        result = self.file_manager.delete_file(file_path)
        
        assert result.success is True
        assert "deleted successfully" in result.message
        self.mock_s3_service.s3_client.delete_object.assert_called_once()
    
    def test_delete_file_not_found(self):
        """Test deleting non-existent file"""
        file_path = "nonexistent.txt"
        
        error = ClientError(
            error_response={'Error': {'Code': 'NoSuchKey'}},
            operation_name='delete_object'
        )
        self.mock_s3_service.s3_client.delete_object.side_effect = error
        
        result = self.file_manager.delete_file(file_path)
        
        assert result.success is False
        assert "not found" in result.message
    
    def test_create_directory_success(self):
        """Test successful directory creation"""
        directory_path = "new_folder"
        
        self.mock_s3_service.s3_client.put_object.return_value = {}
        
        result = self.file_manager.create_directory(directory_path)
        
        assert result.success is True
        assert "created successfully" in result.message
        self.mock_s3_service.s3_client.put_object.assert_called_once()
    
    def test_move_file_success(self):
        """Test successful file move"""
        source_path = "old/file.txt"
        dest_path = "new/file.txt"
        
        self.mock_s3_service.s3_client.copy_object.return_value = {}
        self.mock_s3_service.s3_client.delete_object.return_value = {}
        
        result = self.file_manager.move_file(source_path, dest_path)
        
        assert result.success is True
        assert "moved" in result.message.lower()
        self.mock_s3_service.s3_client.copy_object.assert_called_once()
        self.mock_s3_service.s3_client.delete_object.assert_called_once()
    
    def test_get_file_metadata_success(self):
        """Test getting file metadata"""
        file_path = "test/file.txt"
        
        self.mock_s3_service.s3_client.head_object.return_value = {
            "ContentLength": 1024,
            "LastModified": datetime.now(),
            "ContentType": "text/plain"
        }
        
        result = self.file_manager.get_file_metadata(file_path)
        
        assert result is not None
        assert result.name == "file.txt"
        assert result.path == file_path
        assert result.size == 1024
    
    def test_get_file_metadata_not_found(self):
        """Test getting metadata for non-existent file"""
        file_path = "nonexistent.txt"
        
        error = ClientError(
            error_response={'Error': {'Code': 'NoSuchKey'}},
            operation_name='head_object'
        )
        self.mock_s3_service.s3_client.head_object.side_effect = error
        
        result = self.file_manager.get_file_metadata(file_path)
        
        assert result is None
    
    def test_search_files(self):
        """Test file search functionality"""
        query = "test"
        
        self.mock_s3_service.s3_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": f"{self.project_id}/files/test_file.txt",
                    "Size": 100,
                    "LastModified": datetime.now()
                },
                {
                    "Key": f"{self.project_id}/files/another_test.doc",
                    "Size": 200,
                    "LastModified": datetime.now()
                },
                {
                    "Key": f"{self.project_id}/files/no_match.jpg",
                    "Size": 300,
                    "LastModified": datetime.now()
                }
            ]
        }
        
        result = self.file_manager.search_files(query)
        
        assert result.query == query
        assert len(result.results) == 2  # Only files containing "test"
        assert result.total_results == 2
        assert all("test" in file.name.lower() for file in result.results)
    
    def test_batch_delete_files(self):
        """Test batch file deletion"""
        file_paths = ["file1.txt", "file2.txt", "nonexistent.txt"]
        
        def mock_delete_file(path):
            if path == "nonexistent.txt":
                from schemas.file_manager import FileOperationResponse
                return FileOperationResponse(success=False, message="File not found")
            else:
                from schemas.file_manager import FileOperationResponse
                return FileOperationResponse(success=True, message="Deleted successfully")
        
        with patch.object(self.file_manager, 'delete_file', side_effect=mock_delete_file):
            result = self.file_manager.batch_delete_files(file_paths)
            
            assert len(result.successful_operations) == 2
            assert len(result.failed_operations) == 1
            assert result.failed_operations[0]["path"] == "nonexistent.txt"
    
    def test_matches_file_type(self):
        """Test file type matching"""
        assert self.file_manager._matches_file_type("image/jpeg", "image")
        assert self.file_manager._matches_file_type("image/png", "image")
        assert not self.file_manager._matches_file_type("text/plain", "image")
        assert self.file_manager._matches_file_type("application/pdf", "document")
        assert self.file_manager._matches_file_type("text/html", "text")
    
    def test_delete_directory_success(self):
        """Test successful directory deletion"""
        directory_path = "test_folder"
        
        # Mock list_objects_v2 to return some files in the directory
        self.mock_s3_service.s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": f"{self.project_id}/files/{directory_path}/file1.txt"},
                {"Key": f"{self.project_id}/files/{directory_path}/file2.txt"}
            ]
        }
        
        # Mock delete_objects
        self.mock_s3_service.s3_client.delete_objects.return_value = {}
        
        result = self.file_manager.delete_directory(directory_path)
        
        assert result.success is True
        assert "deleted successfully" in result.message
        assert result.details["deleted_files"] == 2
        self.mock_s3_service.s3_client.delete_objects.assert_called_once()
    
    def test_delete_directory_empty(self):
        """Test deleting empty or non-existent directory"""
        directory_path = "empty_folder"
        
        self.mock_s3_service.s3_client.list_objects_v2.return_value = {
            "Contents": []
        }
        
        result = self.file_manager.delete_directory(directory_path)
        
        assert result.success is False
        assert "not found or already empty" in result.message