# Scheduling Agent Backend - Multi-Agent System

**Architecture:** Multi-agent system with supervisor orchestration
**Framework:** LangGraph + AWS Bedrock Claude 3.5 Sonnet
**Package Manager:** UV (10-100x faster than pip)
**Python Version:** 3.11+

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- UV package manager ([install instructions](https://docs.astral.sh/uv/getting-started/installation/))
- PostgreSQL 15+ (or Aurora Serverless v2)
- Redis 7.1+ (or ElastiCache)
- AWS credentials configured

### Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv

# Verify installation
uv --version
```

### Setup

```bash
# Navigate to backend directory
cd bedrock/backend

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Copy environment file
cp .env.example .env

# Edit .env with your actual values
nano .env
```

---

## Project Structure

```
backend/
├── app/
│   ├── agents/              # Multi-agent system
│   │   ├── supervisor.py    # Supervisor/Orchestrator agent
│   │   ├── intent_classifier.py  # Intent classification
│   │   ├── clarifier.py     # Clarification agent
│   │   ├── context_manager.py    # Context/memory management
│   │   ├── tool_executor.py      # Tool execution
│   │   └── response_generator.py # Response generation
│   │
│   ├── graph/               # LangGraph state machine
│   │   ├── state.py         # Agent state schema
│   │   ├── nodes.py         # Node functions
│   │   ├── edges.py         # Edge/routing functions
│   │   └── scheduling_graph.py   # Main graph definition
│   │
│   ├── core/                # Core infrastructure
│   │   ├── config.py        # Configuration management
│   │   ├── database.py      # Database connection (async)
│   │   ├── redis.py         # Redis connection
│   │   ├── bedrock.py       # AWS Bedrock client
│   │   └── logging.py       # Structured logging
│   │
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic services
│   ├── api/                 # API routes
│   └── utils/               # Utilities
│
├── tests/                   # Test suite (80%+ coverage target)
├── alembic/                 # Database migrations
├── scripts/                 # Utility scripts
├── pyproject.toml           # UV configuration & dependencies
├── uv.lock                  # Deterministic dependency lock
├── .python-version          # Python version (3.11)
├── .env.example             # Environment variables template
└── README.md                # This file
```

---

## UV Package Manager Commands

### Basic Commands

```bash
# Install all dependencies (creates/updates .venv)
uv sync

# Add a new dependency
uv add package-name

# Add a development dependency
uv add --group dev package-name

# Remove a dependency
uv remove package-name

# Update all dependencies
uv sync --upgrade

# Update specific package
uv add package-name --upgrade

# Run a command in the virtual environment
uv run python script.py
uv run uvicorn app.main:app --reload

# Show installed packages
uv pip list

# Show dependency tree
uv tree
```

### Development Workflow

```bash
# Install dependencies including dev group
uv sync --group dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Run linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Run type checker
uv run mypy app/

# Format code
uv run ruff format .
```

---

## Running the Application

### Development Server

```bash
# With UV
uv run uvicorn app.main:app --reload --port 8000

# Or activate venv first
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Database Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Show migration history
uv run alembic history
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_agents/test_supervisor.py

# Run with coverage report
uv run pytest --cov --cov-report=html

# Run and open coverage report
uv run pytest --cov --cov-report=html && open htmlcov/index.html
```

---

## Multi-Agent System Architecture

### Agent Flow

```
User Message
     ↓
Supervisor Agent (Orchestrator)
     ↓
Intent Classifier (confidence ≥ 0.7?)
     ├─ Yes → Tool Executor → Response Generator
     └─ No → Clarifier → Intent Classifier (retry)
```

### Agents

1. **Supervisor Agent** - Orchestrates all agents via LangGraph state machine
2. **Intent Classifier** - Classifies user intent with confidence scoring (>95% accuracy)
3. **Clarifier** - Asks clarifying questions when confidence < 0.7
4. **Context Manager** - Manages session state (Redis) and conversation history (PostgreSQL)
5. **Tool Executor** - Executes scheduling tools via PF360 API
6. **Response Generator** - Generates natural language responses

### State Management

- **Short-term memory:** Redis (TTL: 30 min)
- **Long-term memory:** PostgreSQL (conversation history)
- **LangGraph state:** Shared across all agents

---

## API Endpoints

### Health Check

```bash
GET /api/healthz

Response:
{
  "status": "ok",
  "timestamp": "2025-10-12T20:00:00Z"
}
```

### Chat

```bash
POST /api/chat

Request:
{
  "message": "I want to schedule an appointment",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "1645975",
  "client_name": "projectsforce-validation"
}

Response:
{
  "response": "I'd be happy to help you schedule an appointment! Let me show you your available projects...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "intent": "list_projects",
  "confidence": 0.95,
  "metadata": {
    "tools_executed": ["list_projects"],
    "clarification_needed": false,
    "next_expected_intent": "select_project"
  }
}
```

---

## Configuration

All configuration is done via environment variables in `.env` file.

### Required Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Redis
REDIS_URL=redis://host:6379/0

# AWS Bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0

# PF360 API
CUSTOMER_SCHEDULER_API_URL=https://api.example.com

# Security
JWT_SECRET_KEY=your-secret-key
```

See `.env.example` for all available configuration options.

---

## Testing

### Test Structure

```
tests/
├── conftest.py              # Pytest fixtures
├── test_agents/             # Agent tests
├── test_graph/              # LangGraph tests
├── test_api/                # API endpoint tests
├── test_services/           # Service tests
└── test_models/             # Model tests
```

### Writing Tests

```python
# tests/test_agents/test_intent_classifier.py
import pytest
from app.agents.intent_classifier import classify_intent

@pytest.mark.asyncio
async def test_classify_scheduling_intent():
    message = "I want to schedule an appointment"
    result = await classify_intent(message)

    assert result.intent == "list_projects"
    assert result.confidence >= 0.7
```

### Coverage Target

**Goal:** 80%+ code coverage

```bash
# Generate coverage report
uv run pytest --cov --cov-report=term-missing

# View detailed HTML report
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

---

## Development Tools

### Code Quality

```bash
# Linting with Ruff
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Type checking with mypy
uv run mypy app/
```

### Interactive Shell

```bash
# Python REPL with all imports
uv run ipython

# Import app modules
>>> from app.agents.supervisor import SupervisorAgent
>>> from app.core.config import get_settings
```

---

## Deployment

### Docker

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache --no-dev

# Copy application
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini ./

# Run migrations and start server
CMD uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Build and Run

```bash
# Build image
docker build -t scheduling-agent:latest .

# Run container
docker run -p 8000:8000 --env-file .env scheduling-agent:latest
```

---

## Troubleshooting

### UV Installation Issues

```bash
# Check UV version
uv --version

# Reinstall UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Check Python version
python --version  # Should be 3.11+
```

### Dependency Issues

```bash
# Clear UV cache
uv cache clean

# Remove virtual environment and reinstall
rm -rf .venv
uv sync

# Update all dependencies
uv sync --upgrade
```

### Database Connection Issues

```bash
# Test database connection
uv run python -c "from app.core.database import engine; import asyncio; asyncio.run(engine.connect())"

# Check environment variable
echo $DATABASE_URL
```

### Redis Connection Issues

```bash
# Test Redis connection
uv run python -c "from app.core.redis import redis_client; import asyncio; asyncio.run(redis_client.ping())"

# Check environment variable
echo $REDIS_URL
```

---

## Performance

### Targets

- **P50 latency:** <1s (simple requests)
- **P95 latency:** <3s (complex requests)
- **P99 latency:** <5s
- **Intent classification accuracy:** >95%
- **Tool execution success rate:** >99%

### Monitoring

```bash
# View application logs
tail -f logs/app.log

# View structured logs
cat logs/app.log | jq '.'

# Monitor Redis
redis-cli monitor

# Monitor PostgreSQL
psql -c "SELECT * FROM pg_stat_activity;"
```

---

## Resources

- **UV Documentation:** https://docs.astral.sh/uv/
- **LangGraph Documentation:** https://langchain-ai.github.io/langgraph/
- **AWS Bedrock Agents:** https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **Architecture:** See `ARCHITECTURE.md`
- **Implementation Plan:** See `IMPLEMENTATION_PLAN.md`

---

## License

Proprietary - ProjectsForce Team

---

**Last Updated:** October 12, 2025
**Python Version:** 3.11+
**Package Manager:** UV 0.5+
