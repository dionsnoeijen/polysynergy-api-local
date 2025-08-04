# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## License

PolySynergy API is licensed under the Business Source License 1.1 (BSL 1.1). See the LICENSE file for details.

- **Open source**: Code is publicly available and can be used freely
- **Commercial restriction**: Cannot be offered as a commercial SaaS by third parties
- **Change Date**: January 1, 2028 (becomes Apache 2.0 license)
- **Contact**: For commercial licensing inquiries, see LICENSE file

## Commands

### Development
- `poetry install` - Install dependencies
- `poetry run uvicorn main:app --reload` - Start development server
- `poetry run python cli.py run-local-mock --version-id <id> --node-id <id> --project-id <id> --tenant-id <id>` - Run local mock execution

### Testing
- `poetry run pytest` - Run all tests
- `poetry run pytest tests/unit/` - Run unit tests only
- `poetry run pytest tests/integration/` - Run integration tests only
- `poetry run pytest -m unit` - Run tests marked as unit tests
- `poetry run pytest -m integration` - Run tests marked as integration tests
- `poetry run pytest --cov` - Run tests with coverage report
- `poetry run pytest -v` - Run tests with verbose output
- `poetry run pytest tests/unit/services/test_account_service.py::TestAccountService::test_get_by_cognito_id_found` - Run specific test

### Database
- `poetry run alembic upgrade head` - Run database migrations
- `poetry run alembic revision --autogenerate -m "description"` - Create new migration

## Architecture

This is a FastAPI-based backend for the PolySynergy orchestrator system that manages node execution, projects, and AWS Lambda deployments.

### Core Structure
- **FastAPI Application**: `main.py` - Main application with CORS middleware and router registration
- **CLI Interface**: `cli.py` - Typer-based CLI for local mock execution
- **Database**: PostgreSQL with SQLAlchemy 2.0 and Alembic migrations
- **Redis**: Optional caching layer (configured via REDIS_URL)

### Key Components

#### API Structure (`api/v1/`)
- `account/` - Account management endpoints
- `execution/` - Node execution endpoints including mock execution and logs
- `nodes/` - Node setup and management
- `project/` - Project resources (blueprints, routes, schedules, services, etc.)

#### WebSocket (`ws/v1/`)
- `execution.py` - Real-time execution status updates

#### Models (`models/`)
- `base.py` - Base model with UUID primary keys and timestamps
- Domain models: Project, Blueprint, NodeSetup, Route, Schedule, Service, etc.
- `associative_tables.py` - Many-to-many relationship tables

#### Services (`services/`)
- **AWS Integration**: `lambda_service.py`, `s3_service.py`, `scheduled_lambda_service.py`
- **Publishing**: `blueprint_publish_service.py`, `route_publish_service.py`, `schedule_publish_service.py`
- **Execution**: `execution_storage_service.py`, `mock_sync_service.py`
- **External Services**: Email service, secrets manager, environment variable manager

#### Repositories (`repositories/`)
Repository pattern implementation for data access layer with get_or_404 methods.

### Dependencies
- **Local Packages**: Depends on `polysynergy_nodes`, `polysynergy_node_runner`, and `polysynergy_nodes_agno` from parent directories
- **AWS Services**: Boto3 for Lambda, S3, ECR, Cognito integration
- **Database**: PostgreSQL with psycopg2-binary driver
- **Cache**: Redis for performance optimization

### Environment Configuration
Settings in `core/settings.py` require:
- Database connection parameters
- AWS credentials and resource ARNs
- Cognito user pool configuration
- Email service credentials
- PubNub keys for real-time communication
- OpenAI API key for node processing

### Key Patterns
- **Dependency Injection**: FastAPI's Depends() for repositories and services
- **Repository Pattern**: Data access abstraction layer
- **Service Layer**: Business logic separation
- **Database Context**: `db_context()` for transaction management
- **UUID Primary Keys**: All entities use UUID4 for distributed system compatibility

### Architecture Principles

#### Separation of Concerns
Follow strict layered architecture with clear responsibilities:

- **Controllers** (`api/v1/`): Handle HTTP requests and orchestrate calls to services/repositories
- **Services** (`services/`): Business logic and external system communication (AWS, router, email, etc.)
- **Repositories** (`repositories/`): Pure database operations only - no business logic or external calls
- **Models** (`models/`): Data structures and database entities

#### Communication Patterns
- **Controller → Service**: For business logic and external system interactions
- **Controller → Repository**: For direct database operations
- **Service → Repository**: When services need data access
- **Service → Service**: For composed operations

**Anti-patterns to avoid:**
- Repositories calling services or external systems
- Controllers containing business logic
- Direct database access from controllers (bypass repositories)

#### Microservice Integration
When integrating with other microservices (like the router service):

1. **Create dedicated service classes** for external communication
2. **Keep payloads DRY** - use private methods for payload construction
3. **Handle both single and batch operations** efficiently
4. **Maintain backwards compatibility** when extending service methods
5. **Use proper error handling** - don't fail operations if external updates fail

#### Data Consistency
- **Database updates first** - ensure local state is correct
- **External system updates second** - sync with microservices after local updates
- **Graceful degradation** - log warnings but don't fail operations if external syncs fail
- **Consider eventual consistency** - some operations may succeed locally but fail externally