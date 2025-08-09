# Unified S3 Bucket Structure

This document describes the unified S3 bucket structure implemented across the PolySynergy Orchestrator system.

## Overview

The file manager and image generation nodes now use a unified bucket structure to allow users to manage all their files (uploaded and generated) in one interface.

## Bucket Naming

All buckets follow this naming pattern:
```
polysynergy-{tenant_hash}-{project_hash}-media
```

Where:
- `tenant_hash`: MD5 hash of tenant ID (first 8 characters) for UUIDs longer than 8 chars
- `project_hash`: MD5 hash of project ID (first 8 characters) for UUIDs longer than 8 chars
- For shorter IDs, the original ID is used

Examples:
- `polysynergy-51da7b43-bd58c895-media`
- `polysynergy-abc123-def456-media` (for shorter IDs)

## Folder Structure

```
Bucket: polysynergy-{tenant_hash}-{project_hash}-media
├── files/                    # User-managed files  
│   ├── uploads/             # Default upload folder
│   ├── documents/           # Document storage
│   └── {custom_folders}/    # User-created folders
└── generated/               # System-generated files
    ├── images/              # Generated images
    │   ├── {node_id}/
    │   │   └── {execution_id}/
    │   │       ├── generated_{params}_{timestamp}.png
    │   │       └── cached_{params}_{hash}.png
    ├── qr_codes/            # Generated QR codes
    │   ├── {node_id}/
    │   │   └── {execution_id}/
    │   │       └── qr_{timestamp}.png
    └── avatars/             # Generated avatars (future)
```

## File Manager Integration

### API Changes

All file manager endpoints now support a `folder_type` parameter:
- `folder_type=files` (default): Browse user-managed files
- `folder_type=generated`: Browse system-generated files

### UI Integration

The file manager UI shows both folder types:
- Users can navigate between `files/` and `generated/` folders
- Special navigation paths like `../generated` and `../files` allow switching
- Generated files are read-only for users but can be moved to user folders

## Image Node Changes

### S3 Key Generation

Image generation nodes now use the unified structure:

**Before:**
```
{tenant_id}/{project_id}/{node_id}/{execution_id}/generated_dalle2_1024x1024_20241201_143022.png
```

**After:**
```
generated/images/{node_id}/{execution_id}/generated_dalle2_1024x1024_20241201_143022.png
```

### QR Code Generation

QR code nodes use:
```
generated/qr_codes/{node_id}/{execution_id}/qr_20241201_143022.png
```

## Service Changes

### FileManagerService

- Constructor now requires `tenant_id` parameter
- Uses same bucket naming strategy as image nodes
- Supports `folder_type` parameter in all methods
- Automatically creates unified bucket structure

### S3ImageService

- Remains unchanged - already used the correct bucket naming
- Image nodes updated to use `generated/images/` prefix

## Migration Considerations

### Existing Files

- Old bucket structure files remain accessible
- New files use the unified structure
- Migration script needed to move existing files (optional)

### Backward Compatibility

- API maintains backward compatibility with optional `folder_type` parameter
- Default behavior lists `files/` folder
- Existing file paths continue to work

## Benefits

1. **Unified Management**: Users can manage all files in one interface
2. **Clear Organization**: Separate user files from generated content
3. **Scalability**: Hash-based bucket names prevent naming conflicts
4. **Flexibility**: Easy to add new generated content types
5. **Performance**: Consistent S3 policies and CORS settings

## Implementation Status

- ✅ FileManagerService updated with unified bucket naming
- ✅ File manager API endpoints support folder_type parameter
- ✅ Image generation nodes use generated/images/ structure
- ✅ QR code generation uses generated/qr_codes/ structure
- ⚠️ UI updates needed for folder navigation
- ⚠️ Migration scripts for existing files (optional)