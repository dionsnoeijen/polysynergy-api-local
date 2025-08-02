import uuid
from datetime import datetime, timezone
from typing import Generator
import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from faker import Faker

from main import app
from models.base import Base
from models import Project, Account, Tenant
from db.session import get_db
from core.settings import Settings

fake = Faker()

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database session override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings(
        DATABASE_NAME="test_db",
        DATABASE_USER="test_user",
        DATABASE_PASSWORD="test_pass",
        DATABASE_HOST="localhost",
        DATABASE_PORT=5432,
        COGNITO_AWS_REGION="us-east-1",
        COGNITO_USER_POOL_ID="test_pool",
        COGNITO_APP_CLIENT_ID="test_client",
        AWS_REGION="us-east-1",
        AWS_ACCESS_KEY_ID="test_key",
        AWS_SECRET_ACCESS_KEY="test_secret",
        AWS_ACCOUNT_ID="123456789012",
        AWS_ACM_CERT_ARN="arn:aws:acm:us-east-1:123456789012:certificate/test",
        AWS_LAMBDA_EXECUTION_ROLE="arn:aws:iam::123456789012:role/test",
        AWS_LAMBDA_LAYER_ARN="arn:aws:lambda:us-east-1:123456789012:layer:test:1",
        EMAIL_HOST_USER="test@example.com",
        EMAIL_HOST_PASSWORD="test_pass",
        PORTAL_URL="http://localhost:3000",
        ROUTER_URL="http://localhost:8080",
        PUBNUB_PUBLISH_KEY="test_pub",
        PUBNUB_SUBSCRIBE_KEY="test_sub",
        PUBNUB_SECRET_KEY="test_secret",
        DYNAMODB_ENV_VARS_TABLE="test_table",
        OPENAI_API_KEY="test_openai_key"
    )


@pytest.fixture
def sample_tenant(db_session: Session) -> Tenant:
    """Create a sample tenant for testing."""
    tenant = Tenant(
        name=fake.company(),
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def sample_account(db_session: Session) -> Account:
    """Create a sample account for testing."""
    account = Account(
        cognito_id=fake.uuid4(),
        email=fake.email(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        active=True
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def sample_project(db_session: Session, sample_tenant: Tenant) -> Project:
    """Create a sample project for testing."""
    project = Project(
        name=fake.word(),
        tenant_id=sample_tenant.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 client for AWS services."""
    return Mock()


@pytest.fixture
def mock_lambda_client():
    """Mock Lambda client."""
    mock_client = Mock()
    mock_client.invoke.return_value = {
        'StatusCode': 200,
        'Payload': Mock(read=Mock(return_value=b'{"result": "success"}'))
    }
    return mock_client


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    mock_client = Mock()
    mock_client.put_object.return_value = {'ETag': 'test-etag'}
    mock_client.get_object.return_value = {
        'Body': Mock(read=Mock(return_value=b'test content'))
    }
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    return AsyncMock()