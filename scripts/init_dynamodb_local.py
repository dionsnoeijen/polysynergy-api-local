#!/usr/bin/env python3
"""Initialize DynamoDB Local with required tables.

This script creates the necessary DynamoDB tables in DynamoDB Local.
Run this after starting the DynamoDB Local container.

Usage:
    python scripts/init_dynamodb_local.py
"""

import boto3
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_env_vars_table(dynamodb_client, table_name: str):
    """Create the polysynergy_env_vars table."""
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'PK',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Created table: {table_name}")
        return True
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"⏭️  Table {table_name} already exists")
        return False
    except Exception as e:
        print(f"❌ Failed to create table {table_name}: {e}")
        return False


def create_secrets_table(dynamodb_client, table_name: str):
    """Create the project_secrets table."""
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'secret_key',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'secret_key',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Created table: {table_name}")
        return True
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"⏭️  Table {table_name} already exists")
        return False
    except Exception as e:
        print(f"❌ Failed to create table {table_name}: {e}")
        return False


def create_routes_table(dynamodb_client, table_name: str):
    """Create the routes table for router service."""
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'  # Partition key: routing#{project_id}
                },
                {
                    'AttributeName': 'SK',
                    'KeyType': 'RANGE'  # Sort key: route#{route_id}
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'PK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'SK',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Created table: {table_name}")
        return True
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"⏭️  Table {table_name} already exists")
        return False
    except Exception as e:
        print(f"❌ Failed to create table {table_name}: {e}")
        return False


def create_listeners_table(dynamodb_client, table_name: str):
    """Create the flow_listeners table for active listeners service."""
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'  # Partition key: node_setup_version_id
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'PK',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Created table: {table_name}")
        return True
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"⏭️  Table {table_name} already exists")
        return False
    except Exception as e:
        print(f"❌ Failed to create table {table_name}: {e}")
        return False


def create_api_keys_table(dynamodb_client, table_name: str):
    """Create the router_api_keys table for API key management."""
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'  # Partition key: apikey#{tenant_id}#{project_id}
                },
                {
                    'AttributeName': 'SK',
                    'KeyType': 'RANGE'  # Sort key: key_id
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'PK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'SK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'key_id',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'gsi_keyid',
                    'KeySchema': [
                        {
                            'AttributeName': 'key_id',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Created table: {table_name}")
        return True
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"⏭️  Table {table_name} already exists")
        return False
    except Exception as e:
        print(f"❌ Failed to create table {table_name}: {e}")
        return False


def create_execution_storage_table(dynamodb_client, table_name: str):
    """Create the execution_storage table for execution data."""
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'  # Partition key: flow_id
                },
                {
                    'AttributeName': 'SK',
                    'KeyType': 'RANGE'  # Sort key: various keys for execution data
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'PK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'SK',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Created table: {table_name}")
        return True
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"⏭️  Table {table_name} already exists")
        return False
    except Exception as e:
        print(f"❌ Failed to create table {table_name}: {e}")
        return False


def main():
    print("=" * 60)
    print("DYNAMODB LOCAL INITIALIZATION")
    print("=" * 60)

    # DynamoDB Local endpoint
    endpoint_url = os.getenv("DYNAMODB_LOCAL_ENDPOINT", "http://localhost:8001")

    # Table names
    env_vars_table = os.getenv("DYNAMODB_ENV_VARS_TABLE", "polysynergy_env_vars")
    secrets_table = os.getenv("SECRETS_TABLE_NAME", "project_secrets")
    routes_table = os.getenv("ROUTES_TABLE_NAME", "polysynergy_routes")
    listeners_table = "flow_listeners"
    api_keys_table = "router_api_keys"
    execution_storage_table = "execution_storage"

    print(f"Endpoint: {endpoint_url}")
    print(f"Env vars table: {env_vars_table}")
    print(f"Secrets table: {secrets_table}")
    print(f"Routes table: {routes_table}")
    print(f"Listeners table: {listeners_table}")
    print(f"API keys table: {api_keys_table}")
    print(f"Execution storage table: {execution_storage_table}")
    print("=" * 60)

    # Initialize DynamoDB client for local
    dynamodb_client = boto3.client(
        'dynamodb',
        endpoint_url=endpoint_url,
        region_name='eu-central-1',
        aws_access_key_id='dummy',  # DynamoDB Local doesn't validate credentials
        aws_secret_access_key='dummy'
    )

    # Create tables
    print("\nCreating tables...")
    create_env_vars_table(dynamodb_client, env_vars_table)
    create_secrets_table(dynamodb_client, secrets_table)
    create_routes_table(dynamodb_client, routes_table)
    create_listeners_table(dynamodb_client, listeners_table)
    create_api_keys_table(dynamodb_client, api_keys_table)
    create_execution_storage_table(dynamodb_client, execution_storage_table)

    # List tables to verify
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    response = dynamodb_client.list_tables()
    tables = response.get('TableNames', [])
    print(f"Tables in DynamoDB Local: {tables}")

    required_tables = [env_vars_table, secrets_table, routes_table, listeners_table, api_keys_table, execution_storage_table]
    if all(table in tables for table in required_tables):
        print("\n✅ All tables created successfully!")
    else:
        missing = [t for t in required_tables if t not in tables]
        print(f"\n⚠️  Missing tables: {missing}. Check the output above.")


if __name__ == "__main__":
    main()
