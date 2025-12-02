#!/usr/bin/env python3
"""Migration script to encrypt existing secrets and environment variables in DynamoDB.

This script:
1. Reads all items from polysynergy_env_vars and project_secrets tables
2. Encrypts values using the appropriate encryption key (PROD or LOCAL)
3. Adds 'encrypted' and 'saas_mode' fields
4. Updates items in DynamoDB

Usage:
    # Dry run (preview changes without applying)
    python scripts/migrate_encrypt_secrets.py --dry-run

    # Apply migration
    python scripts/migrate_encrypt_secrets.py

    # Migrate only env vars
    python scripts/migrate_encrypt_secrets.py --env-vars-only

    # Migrate only secrets
    python scripts/migrate_encrypt_secrets.py --secrets-only
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import from node_runner
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


def load_encryption_key():
    """Load encryption key from environment."""
    # Load .env file
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    encryption_key = os.getenv("ENCRYPTION_KEY")

    if not encryption_key:
        print("ERROR: Encryption key not found in environment!")
        print("Please set ENCRYPTION_KEY in .env file")
        sys.exit(1)

    return encryption_key


def migrate_env_vars(dry_run: bool, encryption_key: str, stats: MigrationStats):
    """Migrate environment variables table."""
    table_name = os.getenv("DYNAMODB_ENV_VARS_TABLE", "polysynergy_env_vars")
    region = os.getenv("AWS_REGION", "eu-central-1")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating environment variables from {table_name}...")

    # Initialize encryption service
    encryption = EncryptionService(encryption_key=encryption_key)

    # Initialize DynamoDB client
    dynamodb = boto3.client("dynamodb", region_name=region)

    # Scan table
    response = dynamodb.scan(TableName=table_name)
    items = response.get("Items", [])
    stats.env_vars_total = len(items)

    print(f"Found {len(items)} environment variables")

    for item in items:
        pk = item["PK"]["S"]
        value = item["value"]["S"]
        is_encrypted = item.get("encrypted", {}).get("BOOL", False)

        # Skip if already encrypted
        if is_encrypted:
            print(f"  ⏭️  Skipping {pk} (already encrypted)")
            continue

        try:
            # Encrypt value
            encrypted_value = encryption.encrypt(value)

            print(f"  🔒 Encrypting {pk}")

            if not dry_run:
                # Update item
                dynamodb.update_item(
                    TableName=table_name,
                    Key={"PK": {"S": pk}},
                    UpdateExpression="SET #val = :val, encrypted = :enc",
                    ExpressionAttributeNames={"#val": "value"},
                    ExpressionAttributeValues={
                        ":val": {"S": encrypted_value},
                        ":enc": {"BOOL": True}
                    }
                )

            stats.env_vars_migrated += 1

        except Exception as e:
            print(f"  ❌ Failed to encrypt {pk}: {e}")
            stats.env_vars_failed += 1

    print(f"✅ Migrated {stats.env_vars_migrated}/{stats.env_vars_total} environment variables")


def migrate_secrets(dry_run: bool, encryption_key: str, stats: MigrationStats):
    """Migrate secrets table."""
    table_name = os.getenv("SECRETS_TABLE_NAME", "project_secrets")
    region = os.getenv("AWS_REGION", "eu-central-1")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating secrets from {table_name}...")

    # Initialize encryption service
    encryption = EncryptionService(encryption_key=encryption_key)

    # Initialize DynamoDB client
    dynamodb = boto3.client("dynamodb", region_name=region)

    # Scan table
    response = dynamodb.scan(TableName=table_name)
    items = response.get("Items", [])
    stats.secrets_total = len(items)

    print(f"Found {len(items)} secrets")

    for item in items:
        secret_key = item["secret_key"]["S"]
        secret_value = item["secret_value"]["S"]
        is_encrypted = item.get("encrypted", {}).get("BOOL", False)

        # Skip if already encrypted
        if is_encrypted:
            print(f"  ⏭️  Skipping {secret_key} (already encrypted)")
            continue

        try:
            # Encrypt value
            encrypted_value = encryption.encrypt(secret_value)

            print(f"  🔒 Encrypting {secret_key}")

            if not dry_run:
                # Update item
                dynamodb.update_item(
                    TableName=table_name,
                    Key={"secret_key": {"S": secret_key}},
                    UpdateExpression="SET secret_value = :val, encrypted = :enc",
                    ExpressionAttributeValues={
                        ":val": {"S": encrypted_value},
                        ":enc": {"BOOL": True}
                    }
                )

            stats.secrets_migrated += 1

        except Exception as e:
            print(f"  ❌ Failed to encrypt {secret_key}: {e}")
            stats.secrets_failed += 1

    print(f"✅ Migrated {stats.secrets_migrated}/{stats.secrets_total} secrets")


def main():
    parser = argparse.ArgumentParser(description="Migrate and encrypt DynamoDB secrets")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    parser.add_argument("--env-vars-only", action="store_true", help="Migrate only environment variables")
    parser.add_argument("--secrets-only", action="store_true", help="Migrate only secrets")

    args = parser.parse_args()

    print("=" * 60)
    print("DYNAMODB SECRETS ENCRYPTION MIGRATION")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 60)

    if not args.dry_run:
        response = input("\n⚠️  This will modify data in DynamoDB. Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            return

    # Load encryption key
    encryption_key = load_encryption_key()
    print(f"Using encryption key: {encryption_key[:10]}...{encryption_key[-10:]}")

    # Migration stats
    stats = MigrationStats()

    # Run migrations
    if not args.secrets_only:
        migrate_env_vars(args.dry_run, encryption_key, stats)

    if not args.env_vars_only:
        migrate_secrets(args.dry_run, encryption_key, stats)

    # Print summary
    stats.print_summary()

    if args.dry_run:
        print("\n💡 This was a dry run. Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
