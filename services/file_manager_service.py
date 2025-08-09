import os
import hashlib
import logging
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from urllib.parse import unquote
import mimetypes
import io
from botocore.exceptions import ClientError, NoCredentialsError
import boto3

from polysynergy_node_runner.services.s3_service import S3Service
from schemas.file_manager import (
    FileInfo, DirectoryInfo, DirectoryContents, 
    FileUploadResponse, FileOperationResponse,
    FileBatchOperationResponse, FileSearchResponse
)

logger = logging.getLogger(__name__)


class FileManagerService:
    """Service for managing files in S3 storage with unified bucket structure"""
    
    def __init__(self, s3_service: S3Service, project_id: str, tenant_id: str):
        self.s3_service = s3_service
        self.project_id = project_id
        self.tenant_id = tenant_id
        
        # Create unified S3 client
        self.s3_client = self._create_s3_client()
        self.region = os.getenv("AWS_REGION", "eu-central-1")
        
        # Get unified bucket name
        self.bucket_name = self._get_unified_bucket_name()
        
        # Ensure bucket exists with proper configuration
        self._ensure_bucket_exists()
    
    def _create_s3_client(self):
        """Create S3 client with appropriate credentials"""
        is_lambda = os.getenv("AWS_EXECUTION_ENV") is not None
        
        if is_lambda:
            # In Lambda, use IAM role
            return boto3.client(
                's3',
                region_name=os.getenv("AWS_REGION", "eu-central-1")
            )
        else:
            # Local development
            return boto3.client(
                's3',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "eu-central-1")
            )
    
    def _get_unified_bucket_name(self) -> str:
        """Get unified bucket name using same strategy as image nodes"""
        # Use same logic as S3ImageService
        tenant_id = str(self.tenant_id) if self.tenant_id else 'default'
        project_id = str(self.project_id) if self.project_id else 'default'
        
        # For long tenant/project IDs (UUIDs), create shortened versions using hash
        # This ensures bucket names stay within S3 limits (63 chars) and remain unique
        if len(tenant_id) > 8:
            tenant_short = hashlib.md5(tenant_id.encode()).hexdigest()[:8]
        else:
            tenant_short = tenant_id
            
        if len(project_id) > 8:
            project_short = hashlib.md5(project_id.encode()).hexdigest()[:8]
        else:
            project_short = project_id
        
        # Bucket naming pattern: polysynergy-{tenant_hash}-{project_hash}-media
        # This keeps bucket names under 63 characters while maintaining uniqueness
        bucket_name = f"polysynergy-{tenant_short}-{project_short}-media".lower()
        
        # Ensure bucket name is valid (lowercase, no underscores)
        bucket_name = bucket_name.replace('_', '-')
        
        # Final safety check - should never exceed 63 chars with our hash approach
        if len(bucket_name) > 63:
            # Emergency fallback: use shorter hashes
            tenant_short = hashlib.md5(tenant_id.encode()).hexdigest()[:6]
            project_short = hashlib.md5(project_id.encode()).hexdigest()[:6]
            bucket_name = f"poly-{tenant_short}-{project_short}-media".lower()
        
        return bucket_name
    
    def _ensure_bucket_exists(self) -> bool:
        """Ensure the bucket exists with proper configuration"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            # Bucket exists, ensure it has proper configuration
            self._set_bucket_cors(self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    
                    # Set bucket configuration
                    self._set_bucket_cors(self.bucket_name)
                    return True
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket {self.bucket_name}: {create_error}")
                    return False
            else:
                logger.error(f"Error checking bucket {self.bucket_name}: {e}")
                return False
    
    def _set_bucket_cors(self, bucket_name: str):
        """Set CORS configuration for the bucket"""
        cors_configuration = {
            'CORSRules': [{
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'HEAD', 'POST', 'PUT'],
                'AllowedOrigins': ['*'],
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3000
            }]
        }
        
        try:
            self.s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_configuration
            )
        except ClientError as e:
            logger.warning(f"Failed to set CORS for bucket {bucket_name}: {e}")
    
    def _normalize_path(self, path: Optional[str]) -> str:
        """Normalize and sanitize file paths"""
        if not path:
            return ""
        
        # Remove leading/trailing slashes and normalize
        path = path.strip("/")
        # URL decode path
        path = unquote(path)
        # Remove any double slashes
        path = "/".join(part for part in path.split("/") if part)
        return path
    
    def _get_full_s3_key(self, path: str) -> str:
        """Get full S3 key using the path directly"""
        normalized_path = self._normalize_path(path)
        
        if normalized_path:
            return normalized_path
        return ""
    
    def _extract_file_info_from_s3_object(self, s3_object: Dict[str, Any]) -> FileInfo:
        """Extract file info from S3 object metadata"""
        key = s3_object["Key"]
        # Use key as the relative path directly
        relative_path = key
        
        name = os.path.basename(relative_path) if relative_path else ""
        size = s3_object.get("Size", 0)
        last_modified = s3_object.get("LastModified", datetime.now())
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(name)
        content_type = content_type or "application/octet-stream"
        
        # Generate URL (use signed URL for private access)
        try:
            # Generate pre-signed URL for private bucket access (24 hours)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=86400  # 24 hours
            )
        except Exception:
            # Fallback to direct URL if signing fails
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
        
        return FileInfo(
            name=name,
            path=relative_path,
            size=size,
            content_type=content_type,
            last_modified=last_modified,
            url=url,
            is_directory=False
        )
    
    def _get_directory_structure(self, prefix: str) -> Tuple[List[FileInfo], List[DirectoryInfo]]:
        """Get directory structure from S3 listing"""
        try:
            full_prefix = self._get_full_s3_key(prefix)
            if not full_prefix.endswith("/") and full_prefix:
                full_prefix += "/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=full_prefix,
                Delimiter="/"
            )
            
            files = []
            directories = []
            
            # Process files
            for obj in response.get("Contents", []):
                # Skip the directory marker itself
                if obj["Key"] == full_prefix:
                    continue
                    
                # Only include direct children, not nested files
                relative_key = obj["Key"][len(full_prefix):]
                if "/" not in relative_key:
                    files.append(self._extract_file_info_from_s3_object(obj))
            
            # Process directories (common prefixes)
            for common_prefix in response.get("CommonPrefixes", []):
                dir_prefix = common_prefix["Prefix"]
                # Use prefix directly as relative path, remove trailing slash
                relative_dir = dir_prefix.rstrip("/")
                
                # Only include direct child directories
                if prefix:
                    relative_to_current = relative_dir[len(prefix.rstrip("/") + "/"):]
                else:
                    relative_to_current = relative_dir
                
                if "/" not in relative_to_current:
                    dir_name = relative_to_current
                    directories.append(DirectoryInfo(
                        name=dir_name,
                        path=relative_dir,
                        last_modified=datetime.now(),
                        is_directory=True
                    ))
            
            return files, directories
            
        except Exception as e:
            logger.error(f"Error getting directory structure for {prefix}: {e}")
            return [], []
    
    def list_directory_contents(
        self, 
        path: Optional[str] = None,
        file_type: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        limit: int = 100,
        offset: int = 0
    ) -> DirectoryContents:
        """List contents of a directory with filtering and sorting"""
        try:
            normalized_path = self._normalize_path(path)
            files, directories = self._get_directory_structure(normalized_path)
            
            # Filter by file type
            if file_type:
                filtered_files = []
                for file in files:
                    if self._matches_file_type(file.content_type, file_type):
                        filtered_files.append(file)
                files = filtered_files
            
            # Filter by search term
            if search:
                search_lower = search.lower()
                files = [f for f in files if search_lower in f.name.lower()]
                directories = [d for d in directories if search_lower in d.name.lower()]
            
            # Sort results
            reverse = sort_order.lower() == "desc"
            if sort_by == "name":
                files.sort(key=lambda x: x.name.lower(), reverse=reverse)
                directories.sort(key=lambda x: x.name.lower(), reverse=reverse)
            elif sort_by == "size":
                files.sort(key=lambda x: x.size, reverse=reverse)
            elif sort_by == "modified":
                files.sort(key=lambda x: x.last_modified, reverse=reverse)
                directories.sort(key=lambda x: x.last_modified, reverse=reverse)
            
            # Apply pagination
            total_files = len(files)
            total_directories = len(directories)
            
            files = files[offset:offset + limit]
            directories = directories[offset:offset + limit] if offset < total_directories else []
            
            return DirectoryContents(
                path=normalized_path,
                files=files,
                directories=directories,
                total_files=total_files,
                total_directories=total_directories
            )
            
        except Exception as e:
            logger.error(f"Error listing directory contents: {e}")
            return DirectoryContents(
                path=normalized_path if 'normalized_path' in locals() else "",
                files=[],
                directories=[],
                total_files=0,
                total_directories=0
            )
    
    def _matches_file_type(self, content_type: str, file_type: str) -> bool:
        """Check if content type matches the requested file type filter"""
        type_mappings = {
            "image": ["image/"],
            "video": ["video/"],
            "audio": ["audio/"],
            "document": ["application/pdf", "application/msword", "text/"],
            "archive": ["application/zip", "application/x-rar", "application/x-tar"],
            "text": ["text/"]
        }
        
        if file_type.lower() in type_mappings:
            return any(content_type.startswith(prefix) for prefix in type_mappings[file_type.lower()])
        
        return file_type.lower() in content_type.lower()
    
    def upload_file(
        self, 
        file_content: bytes, 
        filename: str, 
        folder_path: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> FileUploadResponse:
        """Upload a file to S3"""
        try:
            # Normalize paths
            folder_path = self._normalize_path(folder_path)
            
            # Construct full file path
            if folder_path:
                file_path = f"{folder_path}/{filename}"
            else:
                file_path = filename
            
            s3_key = self._get_full_s3_key(file_path)
            
            # Guess content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                content_type = content_type or "application/octet-stream"
            
            # Upload using S3Service's upload_file method
            # We need to temporarily override the method to use our content type
            original_upload = self.s3_service.upload_file
            
            def custom_upload(file_obj, file_key):
                try:
                    self.s3_client.upload_fileobj(
                        io.BytesIO(file_obj),
                        self.bucket_name,
                        file_key,
                        ExtraArgs={'ContentType': content_type}
                    )
                    logger.info(f"Uploaded: {file_key}")
                    return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"
                except Exception as e:
                    logger.error(f"Upload error: {e}")
                    return None
            
            url = custom_upload(file_content, s3_key)
            
            if not url:
                return FileUploadResponse(
                    success=False,
                    file_path=file_path,
                    size=len(file_content),
                    content_type=content_type,
                    message="Failed to upload file to S3"
                )
            
            return FileUploadResponse(
                success=True,
                file_path=file_path,
                url=url,
                size=len(file_content),
                content_type=content_type,
                message="File uploaded successfully"
            )
            
        except Exception as e:
            logger.error(f"Error uploading file {filename}: {e}")
            return FileUploadResponse(
                success=False,
                file_path=filename,
                size=len(file_content),
                content_type=content_type or "application/octet-stream",
                message=f"Upload failed: {str(e)}"
            )
    
    def delete_file(self, file_path: str) -> FileOperationResponse:
        """Delete a single file"""
        try:
            s3_key = self._get_full_s3_key(file_path)
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Deleted file: {s3_key}")
            return FileOperationResponse(
                success=True,
                message=f"File '{file_path}' deleted successfully"
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return FileOperationResponse(
                    success=False,
                    message=f"File '{file_path}' not found"
                )
            else:
                logger.error(f"Error deleting file {file_path}: {e}")
                return FileOperationResponse(
                    success=False,
                    message=f"Failed to delete file: {str(e)}"
                )
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return FileOperationResponse(
                success=False,
                message=f"Failed to delete file: {str(e)}"
            )
    
    def delete_directory(self, directory_path: str) -> FileOperationResponse:
        """Delete a directory and all its contents"""
        try:
            s3_prefix = self._get_full_s3_key(directory_path)
            if not s3_prefix.endswith("/"):
                s3_prefix += "/"
            
            # List all objects with the prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=s3_prefix
            )
            
            objects_to_delete = response.get("Contents", [])
            
            if not objects_to_delete:
                return FileOperationResponse(
                    success=False,
                    message=f"Directory '{directory_path}' not found or already empty"
                )
            
            # Delete objects in batches
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                delete_keys = [{"Key": obj["Key"]} for obj in batch]
                
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={"Objects": delete_keys}
                )
            
            logger.info(f"Deleted directory: {s3_prefix}")
            return FileOperationResponse(
                success=True,
                message=f"Directory '{directory_path}' and {len(objects_to_delete)} files deleted successfully",
                details={"deleted_files": len(objects_to_delete)}
            )
            
        except Exception as e:
            logger.error(f"Error deleting directory {directory_path}: {e}")
            return FileOperationResponse(
                success=False,
                message=f"Failed to delete directory: {str(e)}"
            )
    
    def create_directory(self, directory_path: str) -> FileOperationResponse:
        """Create a directory (folder marker in S3)"""
        try:
            # Normalize path and ensure it ends with /
            normalized_path = self._normalize_path(directory_path)
            if not normalized_path.endswith("/"):
                normalized_path += "/"
            
            s3_key = self._get_full_s3_key(normalized_path)
            
            # Create an empty object to act as directory marker
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=b"",
                ContentType="application/x-directory"
            )
            
            logger.info(f"Created directory: {s3_key}")
            return FileOperationResponse(
                success=True,
                message=f"Directory '{directory_path}' created successfully"
            )
            
        except Exception as e:
            logger.error(f"Error creating directory {directory_path}: {e}")
            return FileOperationResponse(
                success=False,
                message=f"Failed to create directory: {str(e)}"
            )
    
    def move_file(self, source_path: str, destination_path: str) -> FileOperationResponse:
        """Move/rename a file"""
        try:
            source_key = self._get_full_s3_key(source_path)
            dest_key = self._get_full_s3_key(destination_path)
            
            # Copy file to new location
            copy_source = {"Bucket": self.bucket_name, "Key": source_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_key
            )
            
            # Delete original file
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=source_key
            )
            
            logger.info(f"Moved file from {source_key} to {dest_key}")
            return FileOperationResponse(
                success=True,
                message=f"File moved from '{source_path}' to '{destination_path}' successfully"
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return FileOperationResponse(
                    success=False,
                    message=f"Source file '{source_path}' not found"
                )
            else:
                logger.error(f"Error moving file: {e}")
                return FileOperationResponse(
                    success=False,
                    message=f"Failed to move file: {str(e)}"
                )
        except Exception as e:
            logger.error(f"Error moving file from {source_path} to {destination_path}: {e}")
            return FileOperationResponse(
                success=False,
                message=f"Failed to move file: {str(e)}"
            )
    
    def get_file_metadata(self, file_path: str) -> Optional[FileInfo]:
        """Get metadata for a specific file"""
        try:
            s3_key = self._get_full_s3_key(file_path)
            
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Create S3 object-like structure for consistency
            s3_object = {
                "Key": s3_key,
                "Size": response.get("ContentLength", 0),
                "LastModified": response.get("LastModified", datetime.now())
            }
            
            return self._extract_file_info_from_s3_object(s3_object)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['NoSuchKey', '404']:
                return None
            else:
                logger.error(f"Error getting file metadata for {file_path}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error getting file metadata for {file_path}: {e}")
            return None
    
    def batch_delete_files(self, file_paths: List[str]) -> FileBatchOperationResponse:
        """Delete multiple files in batch"""
        successful_operations = []
        failed_operations = []
        
        for file_path in file_paths:
            result = self.delete_file(file_path)
            if result.success:
                successful_operations.append(file_path)
            else:
                failed_operations.append({
                    "path": file_path,
                    "error": result.message
                })
        
        success_count = len(successful_operations)
        failure_count = len(failed_operations)
        
        return FileBatchOperationResponse(
            success=failure_count == 0,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            message=f"Batch delete completed: {success_count} succeeded, {failure_count} failed"
        )
    
    def search_files(self, query: str, search_path: Optional[str] = None) -> FileSearchResponse:
        """Search for files by name"""
        try:
            if search_path:
                search_prefix = self._get_full_s3_key(search_path)
            else:
                search_prefix = ""
            
            if not search_prefix.endswith("/") and search_prefix:
                search_prefix += "/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=search_prefix
            )
            
            matching_files = []
            query_lower = query.lower()
            
            for obj in response.get("Contents", []):
                # Extract filename from key
                relative_key = obj["Key"]
                filename = os.path.basename(relative_key)
                
                if query_lower in filename.lower():
                    matching_files.append(self._extract_file_info_from_s3_object(obj))
            
            return FileSearchResponse(
                query=query,
                results=matching_files,
                total_results=len(matching_files),
                search_path=search_path
            )
            
        except Exception as e:
            logger.error(f"Error searching files with query '{query}': {e}")
            return FileSearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_path=search_path
            )