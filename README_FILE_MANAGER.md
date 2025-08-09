# File Manager API

The File Manager API provides comprehensive file and directory management functionality for the PolySynergy Orchestrator platform. It allows users to manage files within their project workspaces using S3-compatible storage with proper tenant isolation.

## Features

- **File Operations**: Upload, download, delete, move, and rename files
- **Directory Management**: Create, list, and delete directories with nested structures
- **Batch Operations**: Multiple file uploads and batch deletions
- **File Search**: Search files by name across directory structures
- **Metadata Management**: Get detailed file information including size, type, and modification dates
- **Tenant Isolation**: Secure file separation between different tenants and projects
- **Access Control**: Integration with project-based authentication
- **File Type Filtering**: Filter files by type (images, documents, videos, etc.)
- **Sorting and Pagination**: Organized file listing with sorting and pagination support

## API Endpoints

### Base URL
All file manager endpoints are prefixed with `/api/v1/projects/{project_id}/files/`

### Directory Listing
```
GET /api/v1/projects/{project_id}/files/
```
Lists files and directories with optional filtering, searching, sorting, and pagination.

**Query Parameters:**
- `path`: Directory path to list (optional)
- `file_type`: Filter by file type (image, document, video, etc.)
- `search`: Search term for file names
- `sort_by`: Sort field (name, size, modified)
- `sort_order`: Sort order (asc, desc)
- `limit`: Maximum number of results (1-1000)
- `offset`: Results offset for pagination

### File Upload
```
POST /api/v1/projects/{project_id}/files/upload
```
Uploads a single file to the specified folder.

**Form Data:**
- `file`: File to upload (required)
- `folder_path`: Target folder path (optional)
- `public`: Make file publicly accessible (optional)

**Limits:**
- Maximum file size: 100MB
- Supported: All file types

### Multiple File Upload
```
POST /api/v1/projects/{project_id}/files/upload-multiple
```
Uploads multiple files simultaneously.

**Form Data:**
- `files`: Array of files to upload (required, max 20)
- `folder_path`: Target folder path (optional)
- `public`: Make files publicly accessible (optional)

### File/Directory Deletion
```
DELETE /api/v1/projects/{project_id}/files/{file_path}
```
Deletes a file or directory.

**Query Parameters:**
- `is_directory`: Whether the path is a directory (boolean)

### Batch File Deletion
```
POST /api/v1/projects/{project_id}/files/batch-delete
```
Deletes multiple files in a single operation.

**Request Body:**
```json
{
  "file_paths": ["path1/file1.txt", "path2/file2.jpg"]
}
```

**Limits:**
- Maximum 100 files per batch operation

### Directory Creation
```
POST /api/v1/projects/{project_id}/files/directory
```
Creates a new directory.

**Request Body:**
```json
{
  "directory_name": "new_folder",
  "parent_path": "documents" // optional
}
```

### File Move/Rename
```
PUT /api/v1/projects/{project_id}/files/move
```
Moves or renames a file.

**Request Body:**
```json
{
  "source_path": "old/path/file.txt",
  "destination_path": "new/path/file.txt"
}
```

### File Metadata
```
GET /api/v1/projects/{project_id}/files/metadata/{file_path}
```
Retrieves detailed metadata for a specific file.

### File Search
```
GET /api/v1/projects/{project_id}/files/search
```
Searches for files by name.

**Query Parameters:**
- `query`: Search query (required)
- `search_path`: Limit search to specific directory (optional)

### Health Check
```
GET /api/v1/projects/{project_id}/files/health
```
Checks the health of the file manager service for a project.

## File Organization

### Directory Structure
Files are organized with the following hierarchy:
```
{tenant_id}/{project_id}/files/{user_defined_path}
```

### Bucket Naming
- Private files: `ps-private-files-{tenant_id}`
- Public files: `ps-public-files-{tenant_id}`

### File Access
- **Private files**: Accessible via pre-signed URLs with 1-hour expiration
- **Public files**: Directly accessible via public S3 URLs

## File Type Categories

The API supports filtering by these file type categories:

- **image**: All image formats (JPEG, PNG, GIF, etc.)
- **video**: Video formats (MP4, AVI, MOV, etc.)
- **audio**: Audio formats (MP3, WAV, AAC, etc.)
- **document**: Documents (PDF, DOC, TXT, etc.)
- **archive**: Compressed files (ZIP, RAR, TAR, etc.)
- **text**: Text-based files

## Error Handling

The API provides comprehensive error handling with appropriate HTTP status codes:

- `400 Bad Request`: Invalid parameters or file data
- `403 Forbidden`: No tenant access
- `404 Not Found`: File or directory not found
- `413 Request Entity Too Large`: File size exceeds limits
- `500 Internal Server Error`: Server-side processing errors

## Authentication

All endpoints require valid project-level authentication. The current account must have membership in the tenant associated with the project.

## Usage Examples

### Upload a File
```bash
curl -X POST \
  "http://localhost:8090/api/v1/projects/{project_id}/files/upload" \
  -H "Authorization: Bearer {token}" \
  -F "file=@document.pdf" \
  -F "folder_path=documents" \
  -F "public=false"
```

### List Files
```bash
curl -X GET \
  "http://localhost:8090/api/v1/projects/{project_id}/files/?path=documents&file_type=document&limit=50" \
  -H "Authorization: Bearer {token}"
```

### Search Files
```bash
curl -X GET \
  "http://localhost:8090/api/v1/projects/{project_id}/files/search?query=report&search_path=documents" \
  -H "Authorization: Bearer {token}"
```

### Create Directory
```bash
curl -X POST \
  "http://localhost:8090/api/v1/projects/{project_id}/files/directory" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"directory_name": "reports", "parent_path": "documents"}'
```

### Move File
```bash
curl -X PUT \
  "http://localhost:8090/api/v1/projects/{project_id}/files/move" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"source_path": "temp/file.pdf", "destination_path": "documents/file.pdf"}'
```

## Implementation Details

### S3 Service Integration
The file manager uses the existing S3Service from the node_runner package, ensuring consistency with other S3 operations in the platform.

### Tenant Isolation
Files are isolated by tenant using bucket prefixes and separate bucket naming schemes, ensuring data security and privacy.

### Performance Optimization
- Efficient directory listing with S3 prefix-based queries
- Batch operations for multiple file management
- Optimized file metadata retrieval

### Scalability
The service is designed to handle large file structures and can scale with S3's inherent scalability features.

## Testing

Comprehensive test coverage is provided for:
- File manager service operations
- API endpoint functionality
- Error handling scenarios
- Edge cases and validation

Run tests with:
```bash
poetry run pytest tests/unit/test_file_manager_service.py -v
poetry run pytest tests/unit/test_file_manager_endpoints.py -v
```