import logging
from typing import List, Optional
from fastapi import (
    APIRouter, HTTPException, Depends, UploadFile, File, 
    Query, Path, Form, status
)
from fastapi.responses import JSONResponse

from models import Account
from schemas.file_manager import (
    DirectoryContents, FileUploadResponse, FileOperationResponse,
    FileBatchOperationResponse, FileSearchResponse, FileInfo,
    DirectoryCreateRequest, FileOperationRequest, FileBatchDeleteRequest,
    FileListParams, FileMetadataUpdateRequest
)
from services.file_manager_service import FileManagerService
from services.s3_service import get_s3_service
from utils.get_current_account import get_current_account

logger = logging.getLogger(__name__)
router = APIRouter()


def get_file_manager_service(
    project_id: str,
    current_account: Account = Depends(get_current_account)
) -> FileManagerService:
    """Get file manager service instance"""
    if not current_account.memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant access available"
        )
    
    tenant_id = current_account.memberships[0].tenant_id
    s3_service = get_s3_service(tenant_id=str(tenant_id), project_id=str(project_id))

    return FileManagerService(s3_service=s3_service, project_id=project_id, tenant_id=tenant_id)


@router.get(
    "/{project_id}/files/",
    response_model=DirectoryContents,
    summary="List directory contents",
    description="Browse files and directories in the project's file storage"
)
async def list_files(
    project_id: str = Path(..., description="Project ID"),
    path: Optional[str] = Query(None, description="Directory path to list"),
    file_type: Optional[str] = Query(None, description="Filter by file type (image, document, video, etc.)"),
    search: Optional[str] = Query(None, description="Search term for file names"),
    sort_by: str = Query("name", description="Sort field: name, size, modified"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Results offset for pagination"),
    current_account: Account = Depends(get_current_account)
):
    """List contents of a directory with filtering, sorting, and pagination"""
    try:
        file_manager = get_file_manager_service(project_id, current_account)
        
        result = file_manager.list_directory_contents(
            path=path,
            file_type=file_type,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing files for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list directory contents"
        )


@router.post(
    "/{project_id}/files/upload",
    response_model=FileUploadResponse,
    summary="Upload file",
    description="Upload a single file to the project's file storage"
)
async def upload_file(
    project_id: str = Path(..., description="Project ID"),
    file: UploadFile = File(..., description="File to upload"),
    folder_path: Optional[str] = Form(None, description="Target folder path"),
    public: bool = Form(False, description="Make file publicly accessible"),
    current_account: Account = Depends(get_current_account)
):
    """Upload a single file to the specified folder"""
    try:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must have a filename"
            )
        
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File cannot be empty"
            )
        
        # Check file size (limit to 100MB)
        if len(file_content) > 100 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 100MB limit"
            )
        
        file_manager = get_file_manager_service(project_id, current_account, public=public)
        
        result = file_manager.upload_file(
            file_content=file_content,
            filename=file.filename,
            folder_path=folder_path,
            content_type=file.content_type
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )


@router.post(
    "/{project_id}/files/upload-multiple",
    response_model=List[FileUploadResponse],
    summary="Upload multiple files",
    description="Upload multiple files to the project's file storage"
)
async def upload_multiple_files(
    project_id: str = Path(..., description="Project ID"),
    files: List[UploadFile] = File(..., description="Files to upload"),
    folder_path: Optional[str] = Form(None, description="Target folder path"),
    public: bool = Form(False, description="Make files publicly accessible"),
    current_account: Account = Depends(get_current_account)
):
    """Upload multiple files to the specified folder"""
    if len(files) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 files allowed per upload"
        )
    
    file_manager = get_file_manager_service(project_id, current_account, public=public)
    results = []
    
    for file in files:
        try:
            if not file.filename:
                results.append(FileUploadResponse(
                    success=False,
                    file_path="",
                    size=0,
                    content_type="",
                    message="File must have a filename"
                ))
                continue
            
            file_content = await file.read()
            
            if len(file_content) == 0:
                results.append(FileUploadResponse(
                    success=False,
                    file_path=file.filename,
                    size=0,
                    content_type=file.content_type or "",
                    message="File cannot be empty"
                ))
                continue
            
            # Check individual file size
            if len(file_content) > 100 * 1024 * 1024:
                results.append(FileUploadResponse(
                    success=False,
                    file_path=file.filename,
                    size=len(file_content),
                    content_type=file.content_type or "",
                    message="File size exceeds 100MB limit"
                ))
                continue
            
            result = file_manager.upload_file(
                file_content=file_content,
                filename=file.filename,
                folder_path=folder_path,
                content_type=file.content_type
            )
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {e}")
            results.append(FileUploadResponse(
                success=False,
                file_path=file.filename,
                size=0,
                content_type="",
                message=f"Upload failed: {str(e)}"
            ))
    
    return results


@router.delete(
    "/{project_id}/files/{file_path:path}",
    response_model=FileOperationResponse,
    summary="Delete file or directory",
    description="Delete a file or directory (with all contents)"
)
async def delete_file_or_directory(
    project_id: str = Path(..., description="Project ID"),
    file_path: str = Path(..., description="File or directory path to delete"),
    is_directory: bool = Query(False, description="Whether the path is a directory"),
    current_account: Account = Depends(get_current_account)
):
    """Delete a file or directory"""
    try:
        file_manager = get_file_manager_service(project_id, current_account)
        
        if is_directory:
            result = file_manager.delete_directory(file_path)
        else:
            result = file_manager.delete_file(file_path)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND if "not found" in result.message.lower() 
                else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting {file_path} for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file or directory"
        )


@router.post(
    "/{project_id}/files/batch-delete",
    response_model=FileBatchOperationResponse,
    summary="Delete multiple files",
    description="Delete multiple files in a batch operation"
)
async def batch_delete_files(
    project_id: str = Path(..., description="Project ID"),
    request: FileBatchDeleteRequest = ...,
    current_account: Account = Depends(get_current_account)
):
    """Delete multiple files in batch"""
    try:
        if len(request.file_paths) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 files allowed per batch delete"
            )
        
        file_manager = get_file_manager_service(project_id, current_account)
        result = file_manager.batch_delete_files(request.file_paths)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch deleting files for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete files"
        )


@router.post(
    "/{project_id}/files/directory",
    response_model=FileOperationResponse,
    summary="Create directory",
    description="Create a new directory in the project's file storage"
)
async def create_directory(
    project_id: str = Path(..., description="Project ID"),
    request: DirectoryCreateRequest = ...,
    current_account: Account = Depends(get_current_account)
):
    """Create a new directory"""
    try:
        file_manager = get_file_manager_service(project_id, current_account)
        
        # Construct directory path
        if request.parent_path:
            directory_path = f"{request.parent_path.rstrip('/')}/{request.directory_name}"
        else:
            directory_path = request.directory_name
        
        result = file_manager.create_directory(directory_path)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating directory for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create directory"
        )


@router.put(
    "/{project_id}/files/move",
    response_model=FileOperationResponse,
    summary="Move or rename file/directory",
    description="Move or rename a file or directory"
)
async def move_file(
    project_id: str = Path(..., description="Project ID"),
    request: FileOperationRequest = ...,
    current_account: Account = Depends(get_current_account)
):
    """Move or rename a file"""
    try:
        file_manager = get_file_manager_service(project_id, current_account)
        
        result = file_manager.move_file(
            source_path=request.source_path,
            destination_path=request.destination_path
        )
        
        if not result.success:
            status_code = status.HTTP_404_NOT_FOUND if "not found" in result.message.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(
                status_code=status_code,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving file for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to move file"
        )


@router.get(
    "/{project_id}/files/metadata/{file_path:path}",
    response_model=FileInfo,
    summary="Get file metadata",
    description="Get detailed metadata for a specific file"
)
async def get_file_metadata(
    project_id: str = Path(..., description="Project ID"),
    file_path: str = Path(..., description="File path"),
    current_account: Account = Depends(get_current_account)
):
    """Get metadata for a specific file"""
    try:
        file_manager = get_file_manager_service(project_id, current_account)
        
        file_info = file_manager.get_file_metadata(file_path)
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return file_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file metadata for {file_path} in project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file metadata"
        )


@router.put(
    "/{project_id}/files/metadata/{file_path:path}",
    response_model=FileOperationResponse,
    summary="Update file metadata",
    description="Update custom metadata for a specific file"
)
async def update_file_metadata(
    project_id: str = Path(..., description="Project ID"),
    file_path: str = Path(..., description="File path"),
    request: FileMetadataUpdateRequest = ...,
    current_account: Account = Depends(get_current_account)
):
    """Update custom metadata for a specific file"""
    try:
        file_manager = get_file_manager_service(project_id, current_account)
        
        # Update the file metadata
        success = file_manager.update_file_metadata(file_path, request.metadata)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or metadata update failed"
            )
        
        return FileOperationResponse(
            success=True,
            message="File metadata updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating file metadata for {file_path} in project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file metadata"
        )


@router.get(
    "/{project_id}/files/search",
    response_model=FileSearchResponse,
    summary="Search files",
    description="Search for files by name within the project's file storage"
)
async def search_files(
    project_id: str = Path(..., description="Project ID"),
    query: str = Query(..., min_length=1, description="Search query"),
    search_path: Optional[str] = Query(None, description="Limit search to specific directory"),
    current_account: Account = Depends(get_current_account)
):
    """Search for files by name"""
    try:
        file_manager = get_file_manager_service(project_id, current_account)
        
        result = file_manager.search_files(
            query=query,
            search_path=search_path
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error searching files for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search files"
        )


# Health check endpoint for the file manager
@router.get(
    "/{project_id}/files/health",
    response_model=dict,
    summary="File manager health check",
    description="Check the health of file manager service for a project"
)
async def health_check(
    project_id: str = Path(..., description="Project ID"),
    current_account: Account = Depends(get_current_account)
):
    """Health check for the file manager service"""
    try:
        file_manager = get_file_manager_service(project_id, current_account)
        
        # Test basic functionality by listing root directory
        result = file_manager.list_directory_contents(limit=1)
        
        return {
            "status": "healthy",
            "project_id": project_id,
            "tenant_id": current_account.memberships[0].tenant_id,
            "bucket_name": file_manager.bucket_name
        }
        
    except Exception as e:
        logger.error(f"Health check failed for project {project_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "project_id": project_id,
                "error": str(e)
            }
        )