# PolySynergy API

> FastAPI backend for the PolySynergy orchestrator system - A powerful automation and workflow management platform.

## 🚧 Development Status

**API Status**: ✅ **Production-ready** - The PolySynergy API is fully functional and stable.

**Orchestrator Integration**: 🚧 **Work in Progress** - I'm actively working on making the complete system easily available and runnable from the main orchestrator repository. Currently, some manual setup and AWS dependencies are required.

**What's Coming**: 
- 🎯 Complete local Docker setup without cloud dependencies
- 📦 One-command setup from the orchestrator repository
- 🔧 Optional AWS integration for advanced features

**For Contributors**: The API codebase is ready for contributions and feedback. The orchestrator integration improvements are ongoing.

---

## 🏗️ Architecture Overview

This is the **API component** of the larger PolySynergy ecosystem. It provides a RESTful API and WebSocket interface for managing projects, workflows, schedules, and node execution.

### 📁 Part of the PolySynergy Orchestrator

This repository is a **submodule** of the main [`polysynergy-orchestrator`](https://github.com/yourusername/polysynergy-orchestrator) repository, which contains:

```
polysynergy-orchestrator/
├── api-local/           # 👈 This repository - FastAPI backend
├── nodes/               # Node processing and execution logic  
├── node_runner/         # Node execution runtime
├── nodes_agno/          # Additional node implementations
└── docker-compose.yml   # Local development setup
```

### 🚀 Quick Start (Recommended)

**For the complete local development experience:**

1. Clone the main orchestrator repository with submodules:
   ```bash
   git clone --recursive https://github.com/dionsnoeijen/polysynergy-orchestrator.git
   cd polysynergy-orchestrator
   ```

2. Start the entire stack with Docker Compose:
   ```bash
   docker-compose up
   ```

This will start all services including the API, database, Redis, and supporting services.

## 🛠️ Local Development (API Only)

If you want to work on just the API component:

### Prerequisites

- Python 3.12+
- Poetry
- PostgreSQL
- Redis (optional, for caching)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/polysynergy-api.git
   cd polysynergy-api
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run database migrations:
   ```bash
   poetry run alembic upgrade head
   ```

5. Start the development server:
   ```bash
   poetry run uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/polysynergy

# Redis (optional)
REDIS_URL=redis://localhost:6379

# AWS (will be optional soon)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Authentication
JWT_SECRET_KEY=your_jwt_secret
COGNITO_USER_POOL_ID=your_pool_id

# Email Service
EMAIL_SERVICE_API_KEY=your_email_key
```

### AWS Dependencies

⚠️ **Note**: Currently requires AWS services (Lambda, S3, EventBridge) for full functionality. 

🎯 **Coming Soon**: AWS dependencies will be made optional for local development, allowing you to run the complete system locally without cloud dependencies.

## 🏃‍♂️ Usage

### API Endpoints

The API provides the following main endpoints:

- **Projects**: `/api/v1/projects/` - Manage automation projects
- **Nodes**: `/api/v1/nodes/` - Configure processing nodes  
- **Routes**: `/api/v1/routes/` - HTTP endpoint routing
- **Schedules**: `/api/v1/schedules/` - Cron-based scheduling
- **Execution**: `/api/v1/execution/` - Monitor and control workflow execution
- **Accounts**: `/api/v1/accounts/` - User and tenant management

### WebSocket

Real-time execution updates are available via WebSocket:
- **Execution Status**: `/ws/v1/execution` - Live execution monitoring

### API Documentation

Once running, visit:
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc` (Alternative docs)

## 🧪 Testing

### Run Tests

```bash
# All tests
poetry run pytest

# Unit tests only
poetry run pytest tests/unit/

# Integration tests only  
poetry run pytest tests/integration/

# With coverage report
poetry run pytest --cov

# Specific test
poetry run pytest tests/unit/services/test_account_service.py::TestAccountService::test_get_by_cognito_id_found
```

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test API endpoints and database interactions
- **Coverage**: Maintains high test coverage across all services

## 🗄️ Database

### Migrations

```bash
# Run migrations
poetry run alembic upgrade head

# Create new migration
poetry run alembic revision --autogenerate -m "description"
```

### Models

Key database models:
- **Project**: Container for automation workflows
- **NodeSetup**: Configuration for processing nodes
- **Route**: HTTP endpoint definitions
- **Schedule**: Cron-based scheduling rules
- **Execution**: Workflow execution tracking

## 📦 Docker

### Build Image

```bash
docker build -t polysynergy-api .
```

### Run Container

```bash
docker run -p 8000:8090 \
  -e DATABASE_URL=postgresql://... \
  polysynergy-api
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `poetry run pytest`
5. Submit a pull request

### Code Style

- Follow PEP 8 conventions
- Use type hints
- Write comprehensive tests
- Update documentation

## 📄 License

This project is licensed under the **Business Source License 1.1 (BSL 1.1)**.

- ✅ **Open source**: Code is publicly available and can be used freely
- 🚫 **Commercial restriction**: Cannot be offered as a commercial SaaS by third parties  
- 📅 **Change Date**: January 1, 2028 (becomes Apache 2.0 license)
- 📧 **Contact**: For commercial licensing inquiries, see LICENSE file

See the [LICENSE](LICENSE) file for full details.

## 🔗 Related Projects

- **[polysynergy-orchestrator](https://github.com/dionsnoeijen/polysynergy-orchestrator)** - Main repository with Docker Compose setup
- **[polysynergy-nodes](https://github.com/yourusername/polysynergy-nodes)** - Node processing library
- **[polysynergy-node-runner](https://github.com/yourusername/polysynergy-node-runner)** - Node execution runtime

## 📞 Support

- 📧 **Email**: dion@polysynergy.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/polysynergy-api/issues)
- 📖 **Documentation**: [docs.polysynergy.dev](https://docs.polysynergy.dev)
- 💬 **Community**: [Discord/Slack](https://discord.gg/polysynergy)

---

Made with ❤️ by the PolySynergy team