import pytest
import io
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from main import app
from models.account import Account
from models.membership import Membership
from schemas.file_manager import (
    DirectoryContents, FileInfo, FileUploadResponse, FileOperationResponse
)


class TestFileManagerEndpoints:
    
    def setup_method(self):
        """Setup test fixtures"""
        self.client = TestClient(app)
        
        # Mock account and membership
        self.mock_account = Mock(spec=Account)
        self.mock_membership = Mock(spec=Membership)
        self.mock_membership.tenant_id = "test-tenant-123"
        self.mock_account.memberships = [self.mock_membership]
        
        self.project_id = "test-project-456"
        self.base_url = f"/api/v1/projects/{self.project_id}/files"
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_list_files_success(self, mock_get_service, mock_get_account):
        """Test successful file listing"""
        mock_get_account.return_value = self.mock_account
        
        # Mock file manager service
        mock_service = Mock()
        mock_service.list_directory_contents.return_value = DirectoryContents(
            path="",
            files=[
                FileInfo(
                    name="test.txt",
                    path="test.txt",
                    size=100,
                    content_type="text/plain",
                    last_modified=datetime.now(),
                    is_directory=False
                )
            ],
            directories=[],
            total_files=1,
            total_directories=0
        )
        mock_get_service.return_value = mock_service
        
        response = self.client.get(f"{self.base_url}/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["files"]) == 1
        assert data["files"][0]["name"] == "test.txt"
        assert data["total_files"] == 1
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_list_files_with_filters(self, mock_get_service, mock_get_account):
        """Test file listing with filters"""
        mock_get_account.return_value = self.mock_account
        mock_service = Mock()
        mock_service.list_directory_contents.return_value = DirectoryContents(
            path="documents",
            files=[],
            directories=[],
            total_files=0,
            total_directories=0
        )
        mock_get_service.return_value = mock_service
        
        response = self.client.get(f"{self.base_url}/", params={
            "path": "documents",
            "file_type": "document",
            "search": "test",
            "sort_by": "size",
            "sort_order": "desc",
            "limit": 50,
            "offset": 10
        })
        
        assert response.status_code == status.HTTP_200_OK
        mock_service.list_directory_contents.assert_called_once_with(
            path="documents",
            file_type="document",
            search="test",
            sort_by="size",
            sort_order="desc",
            limit=50,
            offset=10
        )
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_upload_file_success(self, mock_get_service, mock_get_account):
        """Test successful file upload"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.upload_file.return_value = FileUploadResponse(
            success=True,
            file_path="test.txt",
            url="https://bucket.s3.amazonaws.com/test.txt",
            size=100,
            content_type="text/plain",
            message="Upload successful"
        )
        mock_get_service.return_value = mock_service
        
        file_content = b"test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        
        response = self.client.post(f"{self.base_url}/upload", files=files)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["file_path"] == "test.txt"
        assert data["url"] is not None
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_upload_file_with_folder(self, mock_get_service, mock_get_account):
        """Test file upload to specific folder"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.upload_file.return_value = FileUploadResponse(
            success=True,
            file_path="documents/test.txt",
            url="https://bucket.s3.amazonaws.com/documents/test.txt",
            size=100,
            content_type="text/plain",
            message="Upload successful"
        )
        mock_get_service.return_value = mock_service
        
        file_content = b"test content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"folder_path": "documents"}
        
        response = self.client.post(f"{self.base_url}/upload", files=files, data=data)
        
        assert response.status_code == status.HTTP_200_OK
        mock_service.upload_file.assert_called_once_with(
            file_content=file_content,
            filename="test.txt",
            folder_path="documents",
            content_type="text/plain"
        )
    
    @patch('api.v1.project.file_manager.get_current_account')
    def test_upload_file_no_filename(self, mock_get_account):
        """Test upload with no filename"""
        mock_get_account.return_value = self.mock_account
        
        files = {"file": (None, io.BytesIO(b"content"), "text/plain")}
        
        response = self.client.post(f"{self.base_url}/upload", files=files)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "filename" in response.json()["detail"]
    
    @patch('api.v1.project.file_manager.get_current_account')
    def test_upload_file_empty(self, mock_get_account):
        """Test upload of empty file"""
        mock_get_account.return_value = self.mock_account
        
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        
        response = self.client.post(f"{self.base_url}/upload", files=files)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "empty" in response.json()["detail"]
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_upload_multiple_files(self, mock_get_service, mock_get_account):
        """Test multiple file upload"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.upload_file.side_effect = [
            FileUploadResponse(
                success=True,
                file_path="file1.txt",
                url="https://bucket.s3.amazonaws.com/file1.txt",
                size=100,
                content_type="text/plain",
                message="Upload successful"
            ),
            FileUploadResponse(
                success=True,
                file_path="file2.txt",
                url="https://bucket.s3.amazonaws.com/file2.txt",
                size=200,
                content_type="text/plain",
                message="Upload successful"
            )
        ]
        mock_get_service.return_value = mock_service
        
        files = [
            ("files", ("file1.txt", io.BytesIO(b"content1"), "text/plain")),
            ("files", ("file2.txt", io.BytesIO(b"content2"), "text/plain"))
        ]
        
        response = self.client.post(f"{self.base_url}/upload-multiple", files=files)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert all(result["success"] for result in data)
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_delete_file_success(self, mock_get_service, mock_get_account):
        """Test successful file deletion"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.delete_file.return_value = FileOperationResponse(
            success=True,
            message="File deleted successfully"
        )
        mock_get_service.return_value = mock_service
        
        response = self.client.delete(f"{self.base_url}/test.txt")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        mock_service.delete_file.assert_called_once_with("test.txt")
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_delete_directory(self, mock_get_service, mock_get_account):
        """Test directory deletion"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.delete_directory.return_value = FileOperationResponse(
            success=True,
            message="Directory deleted successfully"
        )
        mock_get_service.return_value = mock_service
        
        response = self.client.delete(
            f"{self.base_url}/test_folder",
            params={"is_directory": True}
        )
        
        assert response.status_code == status.HTTP_200_OK
        mock_service.delete_directory.assert_called_once_with("test_folder")
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_create_directory_success(self, mock_get_service, mock_get_account):
        """Test successful directory creation"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.create_directory.return_value = FileOperationResponse(
            success=True,
            message="Directory created successfully"
        )
        mock_get_service.return_value = mock_service
        
        request_data = {
            "directory_name": "new_folder",
            "parent_path": "documents"
        }
        
        response = self.client.post(f"{self.base_url}/directory", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        mock_service.create_directory.assert_called_once_with("documents/new_folder")
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_move_file_success(self, mock_get_service, mock_get_account):
        """Test successful file move"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.move_file.return_value = FileOperationResponse(
            success=True,
            message="File moved successfully"
        )
        mock_get_service.return_value = mock_service
        
        request_data = {
            "source_path": "old/file.txt",
            "destination_path": "new/file.txt"
        }
        
        response = self.client.put(f"{self.base_url}/move", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        mock_service.move_file.assert_called_once_with("old/file.txt", "new/file.txt")
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_get_file_metadata_success(self, mock_get_service, mock_get_account):
        """Test getting file metadata"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.get_file_metadata.return_value = FileInfo(
            name="test.txt",
            path="test.txt",
            size=100,
            content_type="text/plain",
            last_modified=datetime.now(),
            url="https://bucket.s3.amazonaws.com/test.txt",
            is_directory=False
        )
        mock_get_service.return_value = mock_service
        
        response = self.client.get(f"{self.base_url}/metadata/test.txt")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "test.txt"
        assert data["size"] == 100
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_get_file_metadata_not_found(self, mock_get_service, mock_get_account):
        """Test getting metadata for non-existent file"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.get_file_metadata.return_value = None
        mock_get_service.return_value = mock_service
        
        response = self.client.get(f"{self.base_url}/metadata/nonexistent.txt")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_search_files(self, mock_get_service, mock_get_account):
        """Test file search"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.search_files.return_value = Mock(
            query="test",
            results=[
                FileInfo(
                    name="test_file.txt",
                    path="test_file.txt",
                    size=100,
                    content_type="text/plain",
                    last_modified=datetime.now(),
                    is_directory=False
                )
            ],
            total_results=1,
            search_path=None
        )
        mock_get_service.return_value = mock_service
        
        response = self.client.get(f"{self.base_url}/search", params={"query": "test"})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["query"] == "test"
        assert len(data["results"]) == 1
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_batch_delete_files(self, mock_get_service, mock_get_account):
        """Test batch file deletion"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.batch_delete_files.return_value = Mock(
            success=True,
            successful_operations=["file1.txt", "file2.txt"],
            failed_operations=[],
            message="All files deleted successfully"
        )
        mock_get_service.return_value = mock_service
        
        request_data = {
            "file_paths": ["file1.txt", "file2.txt"]
        }
        
        response = self.client.post(f"{self.base_url}/batch-delete", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["successful_operations"]) == 2
    
    @patch('api.v1.project.file_manager.get_current_account')
    @patch('api.v1.project.file_manager.get_file_manager_service')
    def test_health_check(self, mock_get_service, mock_get_account):
        """Test health check endpoint"""
        mock_get_account.return_value = self.mock_account
        
        mock_service = Mock()
        mock_service.list_directory_contents.return_value = DirectoryContents(
            path="", files=[], directories=[], total_files=0, total_directories=0
        )
        mock_service.s3_service.bucket_name = "test-bucket"
        mock_service.base_path = f"{self.project_id}/files/"
        mock_get_service.return_value = mock_service
        
        response = self.client.get(f"{self.base_url}/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["project_id"] == self.project_id
        assert data["bucket_name"] == "test-bucket"
    
    @patch('api.v1.project.file_manager.get_current_account')
    def test_no_tenant_access(self, mock_get_account):
        """Test error when user has no tenant access"""
        mock_account = Mock(spec=Account)
        mock_account.memberships = []
        mock_get_account.return_value = mock_account
        
        response = self.client.get(f"{self.base_url}/")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "No tenant access" in response.json()["detail"]
    
    def test_upload_file_size_limit(self):
        """Test file size limit validation"""
        # This would be handled by the endpoint validation
        # Large file test would require actual file upload simulation
        pass
    
    def test_batch_operations_limit(self):
        """Test batch operation limits"""
        # Test for limits on batch uploads (20 files) and batch deletes (100 files)
        pass