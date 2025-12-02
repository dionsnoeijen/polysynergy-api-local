#!/usr/bin/env python3
"""Initialize MinIO with required buckets for local development.

This script creates the necessary S3-compatible buckets in MinIO Local.
Run this after starting the MinIO container.

Usage:
    python scripts/init_minio.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("❌ Error: boto3 not installed. Run: poetry install")
    sys.exit(1)


def create_bucket(s3_client, bucket_name: str, public: bool = False):
    """Create a bucket in MinIO."""
    try:
        # Create bucket
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"✅ Created bucket: {bucket_name}")

        # Set public access if needed
        if public:
            # Set bucket policy for public read access
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                    }
                ]
            }
            import json
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            print(f"  🌍 Set public read access")

        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou':
            print(f"⏭️  Bucket {bucket_name} already exists")
            return False
        else:
            print(f"❌ Failed to create bucket {bucket_name}: {e}")
            return False
    except Exception as e:
        print(f"❌ Failed to create bucket {bucket_name}: {e}")
        return False


def main():
    print("=" * 60)
    print("MINIO LOCAL INITIALIZATION")
    print("=" * 60)

    # MinIO endpoint
    endpoint_url = os.getenv("S3_LOCAL_ENDPOINT", "http://localhost:9000")
    access_key = os.getenv("S3_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("S3_SECRET_KEY", "minioadmin")

    # Bucket names (only public and private, no lambdas for local)
    public_bucket = os.getenv("AWS_S3_PUBLIC_BUCKET_NAME", "polysynergy-public-dev")
    private_bucket = os.getenv("AWS_S3_PRIVATE_BUCKET_NAME", "polysynergy-private-dev")

    print(f"Endpoint: {endpoint_url}")
    print(f"Access Key: {access_key}")
    print(f"Public bucket: {public_bucket}")
    print(f"Private bucket: {private_bucket}")
    print("=" * 60)

    # Initialize S3 client for MinIO
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='eu-central-1'
    )

    # Test connection
    try:
        s3_client.list_buckets()
        print("✅ Successfully connected to MinIO")
    except Exception as e:
        print(f"❌ Failed to connect to MinIO: {e}")
        print("\n💡 Make sure MinIO is running:")
        print("   docker-compose up -d minio")
        sys.exit(1)

    # Create buckets
    print("\nCreating buckets...")
    create_bucket(s3_client, public_bucket, public=True)
    create_bucket(s3_client, private_bucket, public=False)

    # List buckets to verify
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    response = s3_client.list_buckets()
    buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
    print(f"Buckets in MinIO: {buckets}")

    if public_bucket in buckets and private_bucket in buckets:
        print("\n✅ All buckets created successfully!")
        print(f"\n🌐 MinIO Console: http://localhost:9001")
        print(f"   Username: {access_key}")
        print(f"   Password: {secret_key}")
    else:
        print("\n⚠️  Some buckets may be missing. Check the output above.")


if __name__ == "__main__":
    main()
