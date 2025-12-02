#!/usr/bin/env python3
"""Migrate data from AWS DynamoDB to DynamoDB Local.

This script:
1. Reads all items from AWS DynamoDB tables
2. Re-encrypts secrets with the LOCAL encryption key
3. Writes them to DynamoDB Local

Usage:
    # Dry run (preview changes)
    python scripts/migrate_aws_to_local_dynamodb.py --dry-run

    # Migrate only env vars
    python scripts/migrate_aws_to_local_dynamodb.py --env-vars-only

    # Migrate only secrets
    python scripts/migrate_aws_to_local_dynamodb.py --secrets-only

    # Full migration
    python scripts/migrate_aws_to_local_dynamodb.py
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "node_runner"))

import boto3
from polysynergy_node_runner.services.encryption_service import EncryptionService


class MigrationStats:
    def __init__(self):
        self.env_vars_total = 0
        self.env_vars_migrated = 0
        self.env_vars_failed = 0
        self.secrets_total = 0
        self.secrets_migrated = 0
        self.secrets_failed = 0

    def print_summary(self):
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Environment Variables:")
        print(f"  Total: {self.env_vars_total}")
        print(f"  Migrated: {self.env_vars_migrated}")
        print(f"  Failed: {self.env_vars_failed}")
        print(f"\nSecrets:")
        print(f"  Total: {self.secrets_total}")
        print(f"  Migrated: {self.secrets_migrated}")
        print(f"  Failed: {self.secrets_failed}")
        print("=" * 60)


def load_env_file():
    """Load .env file."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value


def get_aws_client(service: str):
    """Get AWS DynamoDB client."""
    return boto3.client(
        service,
        region_name=os.getenv("AWS_REGION", "eu-central-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )


def get_local_client(service: str):
    """Get DynamoDB Local client."""
    endpoint_url = os.getenv("DYNAMODB_LOCAL_ENDPOINT", "http://localhost:8001")
    return boto3.client(
        service,
        endpoint_url=endpoint_url,
        region_name='eu-central-1',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )


def migrate_env_vars(dry_run: bool, aws_encryption: EncryptionService, local_encryption: EncryptionService, stats: MigrationStats):
    """Migrate environment variables from AWS to Local."""
    table_name = os.getenv("DYNAMODB_ENV_VARS_TABLE", "polysynergy_env_vars")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating environment variables from AWS to Local...")

    # Get clients
    aws_client = get_aws_client("dynamodb")
    local_client = get_local_client("dynamodb")

    # Scan AWS table
    response = aws_client.scan(TableName=table_name)
    items = response.get("Items", [])
    stats.env_vars_total = len(items)

    print(f"Found {len(items)} environment variables in AWS DynamoDB")

    for item in items:
        pk = item["PK"]["S"]
        value = item["value"]["S"]
        is_encrypted = item.get("encrypted", {}).get("BOOL", False)

        try:
            # Decrypt with AWS key if encrypted
            if is_encrypted:
                value = aws_encryption.decrypt(value)
                print(f"  🔓 Decrypted {pk}")

            # Encrypt with LOCAL key
            encrypted_value = local_encryption.encrypt(value)
            print(f"  🔒 Re-encrypting {pk} with LOCAL key")

            if not dry_run:
                # Write to Local DynamoDB
                local_client.put_item(
                    TableName=table_name,
                    Item={
                        "PK": {"S": pk},
                        "value": {"S": encrypted_value},
                        "encrypted": {"BOOL": True}
                    }
                )

            stats.env_vars_migrated += 1

        except Exception as e:
            print(f"  ❌ Failed to migrate {pk}: {e}")
            stats.env_vars_failed += 1

    print(f"✅ Migrated {stats.env_vars_migrated}/{stats.env_vars_total} environment variables")


def migrate_secrets(dry_run: bool, aws_encryption: EncryptionService, local_encryption: EncryptionService, stats: MigrationStats):
    """Migrate secrets from AWS to Local."""
    table_name = os.getenv("SECRETS_TABLE_NAME", "project_secrets")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating secrets from AWS to Local...")

    # Get clients
    aws_client = get_aws_client("dynamodb")
    local_client = get_local_client("dynamodb")

    # Scan AWS table
    response = aws_client.scan(TableName=table_name)
    items = response.get("Items", [])
    stats.secrets_total = len(items)

    print(f"Found {len(items)} secrets in AWS DynamoDB")

    for item in items:
        secret_key = item["secret_key"]["S"]
        secret_value = item["secret_value"]["S"]
        is_encrypted = item.get("encrypted", {}).get("BOOL", False)

        # Get optional fields
        project_id = item.get("project_id", {}).get("S")
        stage = item.get("stage", {}).get("S")
        created_at = item.get("created_at", {}).get("S")
        migrated_at = item.get("migrated_at", {}).get("S")

        try:
            # Decrypt with AWS key if encrypted
            if is_encrypted:
                secret_value = aws_encryption.decrypt(secret_value)
                print(f"  🔓 Decrypted {secret_key}")

            # Encrypt with LOCAL key
            encrypted_value = local_encryption.encrypt(secret_value)
            print(f"  🔒 Re-encrypting {secret_key} with LOCAL key")

            if not dry_run:
                # Build item for Local DynamoDB
                local_item = {
                    "secret_key": {"S": secret_key},
                    "secret_value": {"S": encrypted_value},
                    "encrypted": {"BOOL": True}
                }

                # Add optional fields if they exist
                if project_id:
                    local_item["project_id"] = {"S": project_id}
                if stage:
                    local_item["stage"] = {"S": stage}
                if created_at:
                    local_item["created_at"] = {"S": created_at}
                if migrated_at:
                    local_item["migrated_at"] = {"S": migrated_at}

                # Write to Local DynamoDB
                local_client.put_item(
                    TableName=table_name,
                    Item=local_item
                )

            stats.secrets_migrated += 1

        except Exception as e:
            print(f"  ❌ Failed to migrate {secret_key}: {e}")
            stats.secrets_failed += 1

    print(f"✅ Migrated {stats.secrets_migrated}/{stats.secrets_total} secrets")


def main():
    parser = argparse.ArgumentParser(description="Migrate DynamoDB data from AWS to Local")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    parser.add_argument("--env-vars-only", action="store_true", help="Migrate only environment variables")
    parser.add_argument("--secrets-only", action="store_true", help="Migrate only secrets")

    args = parser.parse_args()

    print("=" * 60)
    print("DYNAMODB AWS → LOCAL MIGRATION")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 60)

    # Load .env file
    load_env_file()

    # Get encryption keys
    aws_encryption_key = os.getenv("AWS_ENCRYPTION_KEY")
    local_encryption_key = os.getenv("LOCAL_ENCRYPTION_KEY")

    if not aws_encryption_key:
        print("❌ ERROR: AWS_ENCRYPTION_KEY not found in environment!")
        sys.exit(1)

    if not local_encryption_key:
        print("❌ ERROR: LOCAL_ENCRYPTION_KEY not found in environment!")
        sys.exit(1)

    print(f"AWS encryption key: {aws_encryption_key[:10]}...{aws_encryption_key[-10:]}")
    print(f"LOCAL encryption key: {local_encryption_key[:10]}...{local_encryption_key[-10:]}")

    # Initialize encryption services
    aws_encryption = EncryptionService(encryption_key=aws_encryption_key)
    local_encryption = EncryptionService(encryption_key=local_encryption_key)

    if not args.dry_run:
        response = input("\n⚠️  This will modify data in DynamoDB Local. Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            return

    # Migration stats
    stats = MigrationStats()

    # Run migrations
    if not args.secrets_only:
        migrate_env_vars(args.dry_run, aws_encryption, local_encryption, stats)

    if not args.env_vars_only:
        migrate_secrets(args.dry_run, aws_encryption, local_encryption, stats)

    # Print summary
    stats.print_summary()

    if args.dry_run:
        print("\n💡 This was a dry run. Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
