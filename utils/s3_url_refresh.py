import re
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs
import logging

# Lazy imports to avoid six.moves issues at startup
def _get_boto3():
    try:
        import boto3
        return boto3
    except ImportError as e:
        raise ImportError(f"boto3 not available: {e}")

def _get_boto_exceptions():
    try:
        from botocore.exceptions import ClientError, NoCredentialsError
        return ClientError, NoCredentialsError
    except ImportError as e:
        raise ImportError(f"botocore not available: {e}")

logger = logging.getLogger(__name__)

# Regex pattern to match S3 URLs (both signed and unsigned)
# Matches S3 URLs including query parameters and file extensions
S3_URL_PATTERN = re.compile(
    r'https://[a-zA-Z0-9.-]+\.s3(?:\.[a-zA-Z0-9.-]+)?\.amazonaws\.com/[^\s)\]\},"\'<>]+(?:\?[^\s)\]\},"\'<>]*)?'
)

class S3UrlRefresher:
    """
    Utility class for detecting and refreshing expired S3 signed URLs.
    """
    
    def __init__(self):
        self.s3_client = None
        self._initialize_s3_client()
    
    def _initialize_s3_client(self):
        """Initialize S3 client with error handling for missing credentials."""
        try:
            import os
            boto3 = _get_boto3()
            ClientError, NoCredentialsError = _get_boto_exceptions()
            
            # Check if running in Lambda environment
            is_lambda = os.getenv("AWS_EXECUTION_ENV") is not None
            
            if is_lambda:
                # Lambda uses IAM roles
                self.s3_client = boto3.client(
                    "s3",
                    region_name=os.getenv("AWS_REGION", "eu-central-1"),
                )
            else:
                # Local development - try explicit credentials first, then fall back to default credential chain
                aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
                aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
                
                if aws_access_key_id and aws_secret_access_key:
                    # Use explicit credentials
                    self.s3_client = boto3.client(
                        "s3",
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key,
                        region_name=os.getenv("AWS_REGION", "eu-central-1"),
                    )
                else:
                    # Fall back to default credential chain (e.g., ~/.aws/credentials)
                    self.s3_client = boto3.client(
                        "s3",
                        region_name=os.getenv("AWS_REGION", "eu-central-1"),
                    )
            
            # Test credentials
            self.s3_client.list_buckets()
            logger.info("S3 client initialized successfully")
            print("DEBUG: S3 client initialized successfully")
        except (NoCredentialsError, ClientError) as e:
            logger.warning(f"S3 client initialization failed: {e}. URL refresh will be skipped.")
            self.s3_client = None
        except ImportError as e:
            logger.warning(f"boto3/botocore not available: {e}. URL refresh will be skipped.")
            print(f"DEBUG: boto3/botocore not available: {e}")
            self.s3_client = None
    
    def extract_s3_info_from_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Extract bucket name and object key from S3 URL (signed or unsigned).
        
        Args:
            url: S3 URL (with or without signature)
            
        Returns:
            Dict with 'bucket' and 'key' or None if parsing fails
        """
        try:
            from urllib.parse import unquote
            parsed = urlparse(url)
            
            # Extract bucket name from hostname
            # Format: bucket.s3.region.amazonaws.com or bucket.s3.amazonaws.com
            hostname_parts = parsed.hostname.split('.')
            if len(hostname_parts) >= 3 and 's3' in hostname_parts:
                bucket = hostname_parts[0]
            else:
                return None
            
            # Extract object key from path (remove leading slash)
            # For signed URLs, ignore query parameters
            # URL-decode the key to handle spaces and special characters
            key = unquote(parsed.path.lstrip('/'))
            if not key:
                return None
                
            return {'bucket': bucket, 'key': key}
            
        except Exception as e:
            logger.error(f"Failed to parse S3 URL {url}: {e}")
            return None
    
    def generate_presigned_url(self, bucket: str, key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a new presigned URL for S3 object.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            New presigned URL or None if generation fails
        """
        if not self.s3_client:
            return None
            
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for s3://{bucket}/{key}: {e}")
            return None
    
    def should_refresh_url(self, url: str) -> bool:
        """
        Determine if S3 URL should be refreshed with a presigned URL.
        
        Args:
            url: S3 URL to check
            
        Returns:
            True if we should refresh, False otherwise
        """
        if not self.s3_client:
            return False
            
        # Extract bucket and key to verify it's a valid S3 URL
        s3_info = self.extract_s3_info_from_url(url)
        if not s3_info:
            return False
            
        try:
            # Check if object exists
            self.s3_client.head_object(Bucket=s3_info['bucket'], Key=s3_info['key'])
            return True  # Object exists, we can generate presigned URL
        except Exception as e:
            try:
                ClientError, NoCredentialsError = _get_boto_exceptions()
                if isinstance(e, ClientError):
                    if e.response['Error']['Code'] in ['403', '404']:
                        logger.warning(f"S3 object not accessible: s3://{s3_info['bucket']}/{s3_info['key']}")
                        return False  # Don't refresh if object doesn't exist
            except ImportError:
                pass  # boto exceptions not available
            logger.error(f"Error checking S3 object {url}: {e}")
            return False
    
    def refresh_s3_urls_in_text(self, text: str, expiration: int = 3600) -> str:
        """
        Find and refresh all S3 URLs in the given text with presigned URLs.
        
        Args:
            text: Text content that may contain S3 URLs
            expiration: New URL expiration time in seconds
            
        Returns:
            Text with refreshed S3 URLs (converted to presigned)
        """
        if not self.s3_client or not text:
            print(f"DEBUG: S3 refresh skipped - client: {bool(self.s3_client)}, text: {bool(text)}")
            return text
        
        print(f"DEBUG: Looking for S3 URLs in text: {text[:200]}...")
        matches = S3_URL_PATTERN.findall(text)
        print(f"DEBUG: Found {len(matches)} S3 URLs")
        
        def replace_url(match):
            old_url = match.group(0)
            print(f"DEBUG: Processing S3 URL: {old_url}")
            
            # Extract S3 info
            s3_info = self.extract_s3_info_from_url(old_url)
            if not s3_info:
                print(f"DEBUG: Could not parse S3 URL: {old_url}")
                logger.warning(f"Could not parse S3 URL: {old_url}")
                return old_url
            
            print(f"DEBUG: Parsed S3 URL - bucket: {s3_info['bucket']}, key: {s3_info['key']}")
            
            # Check if we should refresh this URL
            if not self.should_refresh_url(old_url):
                print(f"DEBUG: Not refreshing URL (object not accessible): {old_url}")
                logger.debug(f"Not refreshing URL (object not accessible): {old_url}")
                return old_url
            
            print(f"DEBUG: Generating presigned URL for {s3_info['bucket']}/{s3_info['key']}")
            
            # Generate new presigned URL
            new_url = self.generate_presigned_url(
                s3_info['bucket'], 
                s3_info['key'], 
                expiration
            )
            
            if new_url:
                print(f"DEBUG: Successfully generated presigned URL")
                logger.info(f"Converted S3 URL to presigned: {s3_info['bucket']}/{s3_info['key']}")
                return new_url
            else:
                print(f"DEBUG: Failed to generate presigned URL")
                logger.error(f"Failed to generate presigned URL for: {old_url}")
                return old_url
        
        # Replace all S3 URLs in the text
        refreshed_text = S3_URL_PATTERN.sub(replace_url, text)
        print(f"DEBUG: Text refresh complete - changed: {refreshed_text != text}")
        return refreshed_text


# Global instance for reuse
_s3_refresher = None

def get_s3_url_refresher() -> S3UrlRefresher:
    """Get or create global S3UrlRefresher instance."""
    global _s3_refresher
    if _s3_refresher is None:
        _s3_refresher = S3UrlRefresher()
    return _s3_refresher

def refresh_s3_urls_in_text(text: str, expiration: int = 3600) -> str:
    """
    Convenience function to refresh S3 URLs in text.
    
    Args:
        text: Text content that may contain S3 URLs
        expiration: New URL expiration time in seconds (default 1 hour)
        
    Returns:
        Text with refreshed S3 URLs
    """
    refresher = get_s3_url_refresher()
    return refresher.refresh_s3_urls_in_text(text, expiration)