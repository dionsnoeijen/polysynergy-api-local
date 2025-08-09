from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Request Models
class FileUploadRequest(BaseModel):
    """Request model for file upload"""
    filename: str = Field(..., description="Name of the file")
    content_type: Optional[str] = Field(None, description="MIME type of the file")
    folder_path: Optional[str] = Field(None, description="Folder path to upload to")


class DirectoryCreateRequest(BaseModel):
    """Request model for directory creation"""
    directory_name: str = Field(..., description="Name of the directory to create")
    parent_path: Optional[str] = Field(None, description="Parent directory path")


class FileOperationRequest(BaseModel):
    """Request model for file operations like move/rename"""
    source_path: str = Field(..., description="Source file/directory path")
    destination_path: str = Field(..., description="Destination file/directory path")


class FileBatchDeleteRequest(BaseModel):
    """Request model for batch file deletion"""
    file_paths: List[str] = Field(..., description="List of file paths to delete")


# Response Models
class FileInfo(BaseModel):
    """File information model"""
    name: str = Field(..., description="File name")
    path: str = Field(..., description="Full file path")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type")
    last_modified: datetime = Field(..., description="Last modification date")
    url: Optional[str] = Field(None, description="Public URL if available")
    is_directory: bool = Field(False, description="Whether this is a directory")


class DirectoryInfo(BaseModel):
    """Directory information model"""
    name: str = Field(..., description="Directory name")
    path: str = Field(..., description="Full directory path")
    last_modified: datetime = Field(..., description="Last modification date")
    is_directory: bool = Field(True, description="Always true for directories")
    file_count: Optional[int] = Field(None, description="Number of files in directory")


class DirectoryContents(BaseModel):
    """Directory contents response model"""
    path: str = Field(..., description="Current directory path")
    files: List[FileInfo] = Field(default_factory=list, description="Files in directory")
    directories: List[DirectoryInfo] = Field(default_factory=list, description="Subdirectories")
    total_files: int = Field(0, description="Total number of files")
    total_directories: int = Field(0, description="Total number of directories")


class FileUploadResponse(BaseModel):
    """File upload response model"""
    success: bool = Field(..., description="Upload success status")
    file_path: str = Field(..., description="Uploaded file path")
    url: Optional[str] = Field(None, description="Public URL if available")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="File MIME type")
    message: str = Field(..., description="Status message")


class FileOperationResponse(BaseModel):
    """Generic file operation response model"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    details: Optional[dict] = Field(None, description="Additional operation details")


class FileBatchOperationResponse(BaseModel):
    """Batch file operation response model"""
    success: bool = Field(..., description="Overall operation success status")
    successful_operations: List[str] = Field(default_factory=list, description="Successfully processed items")
    failed_operations: List[dict] = Field(default_factory=list, description="Failed operations with errors")
    message: str = Field(..., description="Overall operation summary")


class FileSearchResponse(BaseModel):
    """File search response model"""
    query: str = Field(..., description="Search query used")
    results: List[FileInfo] = Field(default_factory=list, description="Matching files")
    total_results: int = Field(0, description="Total number of results")
    search_path: Optional[str] = Field(None, description="Path searched within")


# Query parameter models for endpoints
class FileListParams(BaseModel):
    """Query parameters for file listing"""
    path: Optional[str] = Field(None, description="Directory path to list")
    file_type: Optional[str] = Field(None, description="Filter by file type (e.g., 'image', 'document')")
    search: Optional[str] = Field(None, description="Search term for file names")
    sort_by: Optional[str] = Field("name", description="Sort field: 'name', 'size', 'modified'")
    sort_order: Optional[str] = Field("asc", description="Sort order: 'asc' or 'desc'")
    limit: Optional[int] = Field(100, description="Maximum number of results")
    offset: Optional[int] = Field(0, description="Results offset for pagination")