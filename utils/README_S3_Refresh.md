# S3 URL Refresh Utility

## Overview

The S3 URL refresh utility automatically detects and refreshes expired S3 signed URLs in chat responses. This ensures users always have access to files shared in conversations, even when the original signed URLs have expired.

## Implementation

### Core Components

1. **`utils/s3_url_refresh.py`**: Main utility module with `S3UrlRefresher` class
2. **`services/agno_chat_history_service.py`**: Integrated S3 URL refresh in `get_session_history()`

### How It Works

1. **Detection**: Uses regex pattern to identify S3 URLs (both signed and unsigned) in text content
2. **Validation**: Checks if S3 objects exist and are accessible via S3 head_object requests  
3. **Conversion**: Generates new presigned URLs with fresh expiration times for all S3 URLs
4. **Integration**: Automatically processes both user and agent messages during chat history retrieval

### Supported URL Formats

- **Signed URLs**: `https://bucket.s3.region.amazonaws.com/path/file?...X-Amz-Signature=...`
- **Unsigned URLs**: `https://bucket.s3.amazonaws.com/path/file` 
- **Regional buckets**: `https://bucket.s3.us-east-1.amazonaws.com/path/file`
- **Global buckets**: `https://bucket.s3.amazonaws.com/path/file`

All S3 URLs are converted to presigned URLs with fresh expiration times for secure access.

### Configuration

- **Default expiration**: 1 hour (3600 seconds)
- **AWS credentials**: Uses boto3 default credential chain
- **Error handling**: Gracefully handles missing credentials, expired URLs, and access errors

### Usage

The S3 URL refresh runs automatically when chat history is retrieved. No manual intervention required.

### Testing

Run the test suite to verify functionality:

```bash
cd /path/to/api-local
python utils/test_s3_refresh.py
```

### Requirements

- `boto3` (already included in pyproject.toml)
- Valid AWS credentials with S3 access for the relevant buckets
- Python 3.12+

### Error Handling

- **No credentials**: Logs warning, returns original URLs unchanged
- **Access denied**: Treats as expired, attempts refresh
- **Network errors**: Logs error, returns original URLs
- **Invalid URLs**: Skips processing, returns original text

### Performance Considerations

- Uses S3 head_object for efficient expiration checking (no file downloads)
- Caches S3 client instance for reuse
- Only refreshes URLs that are actually expired
- Regex matching is optimized for common S3 URL patterns