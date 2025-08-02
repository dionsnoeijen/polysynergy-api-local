# Testing Guide

This directory contains comprehensive tests for the PolySynergy API.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── unit/                    # Unit tests (fast, isolated)
│   ├── services/           # Service layer tests
│   ├── api/               # API endpoint tests (mocked dependencies)
│   └── repositories/      # Repository tests
├── integration/            # Integration tests (slower, with database)
│   ├── api/               # Full API endpoint tests
│   └── services/          # Service tests with real dependencies
└── README.md              # This file
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Fast, isolated tests
- Mock external dependencies (AWS, database, etc.)
- Focus on testing business logic
- Run with: `poetry run pytest -m unit`

### Integration Tests (`@pytest.mark.integration`)
- Slower tests with real database connections
- Test full request/response cycles
- Verify component interactions
- Run with: `poetry run pytest -m integration`

## Fixtures

Key fixtures available in `conftest.py`:

- `db_session`: In-memory SQLite database session
- `client`: FastAPI test client with database override
- `sample_tenant`: Pre-created tenant for testing
- `sample_account`: Pre-created account for testing
- `sample_project`: Pre-created project for testing
- `mock_settings`: Mock application settings
- `mock_lambda_client`: Mocked AWS Lambda client
- `mock_s3_client`: Mocked AWS S3 client

## Writing Tests

### Service Tests
```python
@pytest.mark.unit
class TestMyService:
    def test_method_success(self, db_session, sample_account):
        # Test service method with mocked dependencies
        pass
```

### Endpoint Tests
```python
@pytest.mark.integration
class TestMyEndpoints:
    @patch('path.to.dependency')
    def test_endpoint_success(self, mock_dep, client):
        response = client.get("/api/v1/endpoint/")
        assert response.status_code == 200
```

## Best Practices

1. **Use appropriate markers**: Mark tests as `@pytest.mark.unit` or `@pytest.mark.integration`
2. **Mock external services**: Always mock AWS services, external APIs, email services
3. **Use fixtures**: Leverage shared fixtures for consistent test data
4. **Test error cases**: Include tests for validation errors, not found scenarios, etc.
5. **Keep tests isolated**: Each test should be independent and not rely on others
6. **Descriptive test names**: Use clear, descriptive test method names

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test categories
poetry run pytest -m unit
poetry run pytest -m integration

# Run specific test file
poetry run pytest tests/unit/services/test_account_service.py

# Run specific test method
poetry run pytest tests/unit/services/test_account_service.py::TestAccountService::test_get_by_cognito_id_found

# Run tests matching pattern
poetry run pytest -k "test_account"
```

## Coverage

Coverage reports are generated in `htmlcov/` directory. Open `htmlcov/index.html` to view detailed coverage information.