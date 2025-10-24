# Backend Implementation Plan

**Architecture:** Multi-agent system with LangGraph + AWS Bedrock
**Research Complete:** ✅ See ARCHITECTURE.md for full design
**Estimated Time:** 6-8 hours for MVP, 12-16 hours for production-ready

---

## ✅ Research Complete - Key Findings

### AWS Bedrock Multi-Agent Collaboration (2025)
- Supervisor-based architecture with specialized agents
- Routing mode for simple requests, full orchestration for complex
- 55% increase in successful calls with proper intent classification
- 83% reduction in human agent escalation

### LangGraph Orchestration
- State machine for managing complex workflows
- Parallel agent execution where possible
- Built-in state persistence and recovery
- Human-in-the-loop capabilities

### UV Package Manager
- 10-100x faster than pip
- Deterministic builds with uv.lock
- Dependency groups for prod/dev/test separation
- Official FastAPI recommendation

---

## Implementation Phases

### Phase 1: Foundation (2 hours)
**Status:** Ready to start

**Tasks:**
1. Set up UV package management
   - Create pyproject.toml with all dependencies
   - Initialize uv.lock
   - Set Python version to 3.11

2. Create core infrastructure
   - Configuration management (app/core/config.py)
   - Database connection (app/core/database.py)
   - Redis connection (app/core/redis.py)
   - AWS Bedrock client (app/core/bedrock.py)
   - Structured logging (app/core/logging.py)

3. Define Pydantic schemas
   - Agent state schema
   - Chat request/response
   - Intent classification
   - Tool execution

---

### Phase 2: LangGraph State Machine (2-3 hours)
**Status:** Pending Phase 1

**Tasks:**
1. Define AgentState TypedDict
   - All shared state between agents
   - Input, classification, context, tools, response

2. Implement agent node functions
   - supervisor_agent() - Entry point and orchestration
   - intent_classifier_agent() - Classify with confidence
   - clarifier_agent() - Ask clarifying questions
   - tool_executor_agent() - Execute PF360 tools
   - response_generator_agent() - Generate final response

3. Define edge/routing functions
   - route_after_classification() - Route based on confidence
   - should_clarify() - Determine if clarification needed
   - should_execute_tools() - Determine if tools needed

4. Create scheduling graph
   - Build StateGraph with all nodes
   - Add conditional edges
   - Compile graph

---

### Phase 3: Agents Implementation (2-3 hours)
**Status:** Pending Phase 2

**Tasks:**
1. Intent Classifier Agent
   - Prompt engineering for classification
   - Confidence threshold logic (0.7)
   - Entity extraction
   - Few-shot examples from current system

2. Clarifier Agent
   - Generate clarifying questions
   - Template-based + LLM-generated
   - Context-aware question selection

3. Context Manager
   - Session state in Redis (TTL: 30 min)
   - Conversation history in PostgreSQL
   - Helper functions for state management

4. Tool Executor
   - Implement 11 tools from current system
   - PF360 API integration
   - Error handling and retries
   - Response transformation

5. Response Generator
   - Compile tool results
   - Generate natural language
   - Follow conversational guidelines
   - Format dates/times properly

---

### Phase 4: Database & Models (1-2 hours)
**Status:** Pending Phase 3

**Tasks:**
1. SQLAlchemy models
   - Base model with created_at, updated_at
   - Session model
   - Conversation model
   - Appointment model (optional)

2. Alembic migrations
   - Initial schema migration
   - Migration scripts

3. Database services
   - Session service
   - Conversation service
   - Query helpers

---

### Phase 5: API Layer (1 hour)
**Status:** Pending Phase 4

**Tasks:**
1. FastAPI application
   - main.py with app initialization
   - CORS middleware
   - Error handlers
   - Health check endpoint

2. Chat endpoint
   - POST /api/chat
   - Request validation
   - Graph invocation
   - Response formatting

3. Dependencies
   - Database session dependency
   - Redis client dependency
   - Authentication dependency (from headers)

---

### Phase 6: Testing (2-3 hours)
**Status:** Pending Phase 5

**Tasks:**
1. Unit tests
   - Test each agent function
   - Test utility functions
   - Test validators

2. Integration tests
   - Test graph state transitions
   - Test database operations
   - Test Redis operations

3. E2E tests
   - Test full conversation flows
   - Test multi-turn interactions
   - Test error scenarios

4. Coverage
   - Achieve 80%+ coverage
   - Generate coverage reports

---

## Detailed Implementation Steps

### Step 1: Set Up UV and Dependencies

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend/

# Initialize UV project (if not already done)
uv init

# Set Python version
echo "3.11" > .python-version

# Add dependencies (will create/update pyproject.toml)
uv add fastapi uvicorn[standard]
uv add "sqlalchemy[asyncio]" alembic asyncpg
uv add redis
uv add httpx tenacity
uv add "pydantic>=2.0" pydantic-settings
uv add langgraph langchain-aws boto3
uv add structlog python-json-logger

# Add dev dependencies
uv add --group dev pytest pytest-asyncio pytest-cov
uv add --group dev httpx-mock faker
uv add --group dev ruff mypy
uv add --group dev ipython

# Sync environment
uv sync
```

---

### Step 2: Create Core Configuration

**File: app/core/config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    # Environment
    environment: str = "dev"

    # Database
    database_url: str

    # Redis
    redis_url: str

    # AWS Bedrock
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    bedrock_agent_id: str | None = None

    # PF360 API
    customer_scheduler_api_url: str
    confirm_schedule_flag: int = 1
    cancel_schedule_flag: int = 1

    # Secrets
    jwt_secret_key: str

    # Agent Configuration
    intent_confidence_threshold: float = 0.7
    max_clarification_attempts: int = 3
    session_ttl_seconds: int = 1800  # 30 minutes

    # Logging
    log_level: str = "INFO"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

### Step 3: Create Database Connection

**File: app/core/database.py**

```python
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "dev",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base for models
Base = declarative_base()

# Dependency
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

---

### Step 4: Create Redis Connection

**File: app/core/redis.py**

```python
from redis.asyncio import Redis
from app.core.config import get_settings
import json
from typing import Any

settings = get_settings()

# Redis client
redis_client = Redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True
)

class RedisSessionManager:
    """Manage session state in Redis"""

    @staticmethod
    async def set_session(session_id: str, data: dict, ttl: int = None):
        ttl = ttl or settings.session_ttl_seconds
        await redis_client.setex(
            f"session:{session_id}",
            ttl,
            json.dumps(data)
        )

    @staticmethod
    async def get_session(session_id: str) -> dict | None:
        data = await redis_client.get(f"session:{session_id}")
        return json.loads(data) if data else None

    @staticmethod
    async def delete_session(session_id: str):
        await redis_client.delete(f"session:{session_id}")

    @staticmethod
    async def update_session(session_id: str, updates: dict):
        session = await RedisSessionManager.get_session(session_id)
        if session:
            session.update(updates)
            await RedisSessionManager.set_session(session_id, session)
```

---

### Step 5: Create AWS Bedrock Client

**File: app/core/bedrock.py**

```python
import boto3
import json
from app.core.config import get_settings

settings = get_settings()

# Bedrock runtime client
bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=settings.aws_region
)

async def invoke_claude(
    prompt: str,
    system_prompt: str | None = None,
    max_tokens: int = 2000,
    temperature: float = 0.0
) -> str:
    """Invoke Claude model via Bedrock"""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    if system_prompt:
        body["system"] = system_prompt

    response = bedrock_runtime.invoke_model(
        modelId=settings.bedrock_model_id,
        body=json.dumps(body)
    )

    response_body = json.loads(response["body"].read())
    return response_body["content"][0]["text"]
```

---

### Step 6: Define Agent State Schema

**File: app/graph/state.py**

```python
from typing import TypedDict, Annotated, List
import operator

class AgentState(TypedDict):
    """Shared state across all agents in the graph"""

    # Input
    session_id: str
    customer_id: str
    client_id: str
    client_name: str
    user_message: str

    # Classification
    intent: str | None
    confidence: float | None
    entities: dict

    # Clarification
    needs_clarification: bool
    clarifying_question: str | None
    clarification_count: int

    # Context
    session_context: dict
    conversation_history: Annotated[List[dict], operator.add]

    # Tool execution
    tools_to_execute: List[str]
    tool_results: dict

    # Response
    agent_response: str | None

    # Metadata
    current_agent: str
    error: str | None
    next_expected_intent: str | None
```

---

## Next Steps

**Choose implementation approach:**

**Option A: Incremental (Recommended)**
- Implement one phase at a time
- Test each phase before moving to next
- Can run and test incrementally
- Duration: 8-12 hours

**Option B: Full Build**
- Implement all phases in sequence
- Test at the end
- Faster but riskier
- Duration: 6-8 hours

**Option C: Parallel**
- Multiple developers work on different phases
- Requires coordination
- Duration: 4-6 hours

---

## What I'll Build

Based on your request, I will build:

1. ✅ **UV package management** - Modern, fast dependency management
2. ✅ **Multi-agent architecture** - Supervisor + 5 specialized agents
3. ✅ **LangGraph orchestration** - State machine for complex workflows
4. ✅ **Intent classifier** - >95% accuracy with confidence scoring
5. ✅ **Clarifier agent** - Asks questions when confidence < 0.7
6. ✅ **Context manager** - Redis + PostgreSQL for state
7. ✅ **Tool executor** - All 11 tools from current system
8. ✅ **Response generator** - Natural, conversational responses
9. ✅ **FastAPI endpoints** - /api/chat and /api/healthz
10. ✅ **SQLAlchemy models** - Session, Conversation, Appointment
11. ✅ **Alembic migrations** - Database schema management
12. ✅ **Comprehensive tests** - 80%+ coverage

---

## Files to Create (50+ files)

### Configuration & Setup (5 files)
- pyproject.toml
- .python-version
- .env.example
- README.md
- ARCHITECTURE.md ✅ (done)

### Core Infrastructure (5 files)
- app/core/config.py
- app/core/database.py
- app/core/redis.py
- app/core/bedrock.py
- app/core/logging.py

### LangGraph (5 files)
- app/graph/state.py
- app/graph/nodes.py
- app/graph/edges.py
- app/graph/scheduling_graph.py
- app/graph/__init__.py

### Agents (6 files)
- app/agents/supervisor.py
- app/agents/intent_classifier.py
- app/agents/clarifier.py
- app/agents/context_manager.py
- app/agents/tool_executor.py
- app/agents/response_generator.py

### Models (5 files)
- app/models/base.py
- app/models/session.py
- app/models/conversation.py
- app/models/appointment.py
- app/models/__init__.py

### Schemas (6 files)
- app/schemas/chat.py
- app/schemas/agent.py
- app/schemas/intent.py
- app/schemas/state.py
- app/schemas/pf360.py
- app/schemas/__init__.py

### Services (4 files)
- app/services/bedrock_service.py
- app/services/pf360_service.py
- app/services/session_service.py
- app/services/conversation_service.py

### API (4 files)
- app/api/routes.py
- app/api/deps.py
- app/api/middleware.py
- app/api/__init__.py

### Utils (2 files)
- app/utils/formatters.py
- app/utils/validators.py

### Tests (15+ files)
- tests/conftest.py
- tests/test_agents/*.py (6 files)
- tests/test_graph/*.py (2 files)
- tests/test_api/*.py (2 files)
- tests/test_services/*.py (4 files)
- tests/test_models/*.py (2 files)

### Migrations (2 files)
- alembic/env.py
- alembic/versions/001_initial_schema.py

### Scripts (2 files)
- scripts/seed_db.py
- scripts/test_bedrock_access.py

---

## Ready to Start?

I'm ready to implement the full multi-agent system with:
- Production-grade architecture
- Best practices from 2025 AWS Bedrock patterns
- LangGraph orchestration
- UV package management
- Comprehensive testing

**Shall I proceed with implementation?**

**Estimated time to MVP:** 6-8 hours
**Estimated time to production-ready:** 12-16 hours

**Let me know if you want me to:**
1. Start with Phase 1 (Foundation)
2. Create all files at once
3. Focus on specific components first
4. Any architecture adjustments

---

**Created:** October 12, 2025
**Status:** Research complete, architecture designed, ready to implement
