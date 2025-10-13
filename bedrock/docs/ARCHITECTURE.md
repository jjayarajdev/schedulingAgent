# Backend Architecture - Multi-Agent System

**Based on:** AWS Bedrock multi-agent collaboration patterns (2025)
**Framework:** LangGraph + AWS Bedrock
**Package Manager:** UV (10-100x faster than pip)

---

## Research Summary

### Key Findings from 2025 Best Practices

**AWS Bedrock Multi-Agent Collaboration (GA: March 10, 2025):**
- Supervisor-based architecture with specialized agents
- Automatic plan creation and execution across collaborator agents
- Routing mode for simple requests, full orchestration for complex queries
- Hierarchical organization (soft limit: 3 layers)
- Parallel communication for efficient task completion

**LangGraph Integration:**
- State management across all components
- Parallel processing and stateful workflows
- Human-in-the-loop capabilities
- Graph-based orchestration for complex workflows

**Intent Classification Best Practices:**
- Confidence threshold: 0.7 for fallback triggers
- Hierarchical classification (domain → specific intent)
- AI-powered systems achieve >95% accuracy
- 55% increase in successful calls, 83% reduction in human escalation

**UV Package Manager Benefits:**
- 10-100x faster than pip
- Deterministic builds with uv.lock
- Dependency groups (prod, dev, test)
- Single pyproject.toml for all dependencies

---

## Architecture Overview

### Multi-Agent System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Supervisor Agent                         │
│  (Orchestrator - Coordinates all agents via LangGraph)     │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Intent     │  │  Clarifier   │  │   Tool       │
│ Classifier   │  │    Agent     │  │  Executor    │
│              │  │              │  │              │
│ Confidence:  │  │ Asks for     │  │ Executes     │
│  High→Route  │  │ clarification│  │ PF360 API    │
│  Low→Clarify │  │ when unclear │  │ calls        │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
              ┌───────────────────────┐
              │   Context Manager     │
              │  (Redis + Database)   │
              │                       │
              │  - Session state      │
              │  - Conversation hist  │
              │  - User context       │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Response Generator   │
              │  (AWS Bedrock Claude) │
              └───────────────────────┘
```

---

## Agent Descriptions

### 1. Supervisor Agent (Orchestrator)

**Role:** Master coordinator using LangGraph state machine

**Responsibilities:**
- Receive initial user message
- Determine routing strategy (simple vs complex)
- Coordinate specialized agents in parallel when possible
- Manage conversation state across turns
- Compile final response from agent outputs
- Handle error recovery and fallbacks

**Technology:**
- LangGraph for state graph definition
- AWS Bedrock Claude 3.5 Sonnet for reasoning
- Redis for state persistence

**State Machine:**
```python
States:
- START: Initial state, receive user message
- CLASSIFY_INTENT: Route to Intent Classifier
- CLARIFY: Route to Clarifier if confidence < 0.7
- EXECUTE_TOOLS: Route to Tool Executor
- GENERATE_RESPONSE: Compile and generate final response
- END: Return response to user

Transitions:
START → CLASSIFY_INTENT
CLASSIFY_INTENT → CLARIFY (if confidence < 0.7)
CLASSIFY_INTENT → EXECUTE_TOOLS (if confidence >= 0.7)
CLARIFY → CLASSIFY_INTENT (after clarification)
EXECUTE_TOOLS → GENERATE_RESPONSE
GENERATE_RESPONSE → END
```

---

### 2. Intent Classifier Agent

**Role:** Hierarchical intent classification with confidence scoring

**Responsibilities:**
- Classify user message into intent hierarchy
- Calculate confidence score (0.0 - 1.0)
- Extract entities from message
- Detect multi-intent requests
- Return structured classification result

**Intent Hierarchy:**
```
scheduling
├── list_projects
├── select_project
├── get_available_dates
├── select_date
├── get_time_slots
├── select_time_slot
├── confirm_appointment
├── reschedule
└── cancel

information
├── project_details
├── appointment_status
├── working_hours
└── weather

notes
├── add_note
└── view_notes

chitchat
├── greeting
├── thanks
└── goodbye
```

**Confidence Thresholds:**
- ≥ 0.7: High confidence → Execute
- 0.4 - 0.69: Medium confidence → Clarify
- < 0.4: Low confidence → Ask for clarification

**Technology:**
- AWS Bedrock Claude 3.5 Sonnet for classification
- Few-shot prompting with examples from current system
- Structured output (Pydantic schema)

---

### 3. Clarifier Agent

**Role:** Ask clarifying questions when intent is unclear

**Responsibilities:**
- Trigger when intent confidence < 0.7
- Analyze what information is missing
- Generate specific clarifying questions
- Collect additional user responses
- Re-route to Intent Classifier with enhanced context

**Clarification Strategies:**
```python
Missing Information Types:
1. Ambiguous intent
   Q: "Would you like to schedule, reschedule, or check an appointment?"

2. Missing project selection
   Q: "Which project would you like to work with? Here are your options: ..."

3. Unclear date/time
   Q: "Could you specify the date you prefer? For example: tomorrow, next Monday, or a specific date."

4. Multiple possible intents
   Q: "I can help you with X or Y. Which would you prefer?"

5. Incomplete request
   Q: "To complete your request, I need to know [missing info]. Can you provide that?"
```

**Technology:**
- AWS Bedrock Claude 3.5 Sonnet for question generation
- Template-based + LLM-generated questions
- Context-aware question selection

---

### 4. Context Manager

**Role:** Manage session state and conversation history

**Responsibilities:**
- Store and retrieve session data (Redis)
- Maintain conversation history (Database)
- Track selected project, date, time across turns
- Implement short-term and long-term memory
- Provide context to all agents

**Data Structures:**
```python
Session State (Redis - TTL: 30 min):
{
  "session_id": "uuid",
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "current_state": "selecting_date",
  "selected_project_id": 123,
  "selected_date": "2025-10-15",
  "selected_time": null,
  "conversation_turns": 5,
  "last_intent": "get_available_dates",
  "clarification_count": 0,
  "context": {
    "projects": [...],
    "working_days": [...],
    "available_dates": [...],
    "request_id": "abc123"
  }
}

Conversation History (PostgreSQL):
- session_id, turn_number
- user_message, agent_response
- intent, confidence
- tools_used, execution_result
- timestamp
```

**Technology:**
- Redis for fast session state access
- PostgreSQL for persistent conversation history
- SQLAlchemy async for database operations

---

### 5. Tool Executor Agent

**Role:** Execute scheduling operations via PF360 API

**Responsibilities:**
- Execute tools based on classified intent
- Call PF360 API endpoints (via Lambda or direct)
- Handle API errors and retries
- Transform API responses for agent consumption
- Update session context with results

**Tools (from current system core/tools.py):**
```python
1. list_projects(session_id) → List[Project]
2. switch_project(session_id, project_text) → Project
3. show_project_details(session_id) → ProjectDetails
4. get_working_days(session_id) → List[str]
5. get_available_dates(session_id) → List[str]
6. get_slots_for_date(session_id, date) → List[str]
7. update_date(session_id, date) → bool
8. confirm_appointment(session_id, time) → Appointment
9. cancel_schedule(session_id) → bool
10. add_project_note(session_id, note) → bool
11. get_current_weather(city) → WeatherInfo
```

**Error Handling:**
- Retry logic (exponential backoff)
- Fallback responses
- User-friendly error messages
- Automatic context preservation on errors

**Technology:**
- httpx for async HTTP requests
- Tenacity for retries
- Pydantic for response validation

---

### 6. Response Generator Agent

**Role:** Generate natural, conversational responses

**Responsibilities:**
- Compile information from tool executions
- Generate natural language response
- Follow conversational guidelines from current system
- Format dates/times properly (12-hour AM/PM)
- Hide technical IDs from users
- Maintain friendly, professional tone

**Response Guidelines (from current system):**
- Always greet users warmly
- Show only first 3 consecutive available dates
- Display times in AM/PM format (not 24-hour)
- Never expose session_id, project_id, request_id
- Always confirm before booking
- Offer to add notes after operations
- Be conversational and natural

**Technology:**
- AWS Bedrock Claude 3.5 Sonnet for generation
- Template-based responses for common scenarios
- LLM-generated responses for complex scenarios

---

## LangGraph State Machine Definition

```python
from langgraph.graph import StateGraph
from typing import TypedDict, Annotated, List
import operator

class AgentState(TypedDict):
    """Shared state across all agents"""
    # Input
    session_id: str
    customer_id: str
    user_message: str

    # Classification
    intent: str
    confidence: float
    entities: dict

    # Clarification
    needs_clarification: bool
    clarifying_question: str
    clarification_response: str

    # Context
    session_context: dict
    conversation_history: List[dict]

    # Tool execution
    tools_to_execute: List[str]
    tool_results: dict

    # Response
    agent_response: str

    # Metadata
    current_agent: str
    error: str | None

# Define graph
def create_scheduling_graph():
    graph = StateGraph(AgentState)

    # Add nodes (agents)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("intent_classifier", intent_classifier_agent)
    graph.add_node("clarifier", clarifier_agent)
    graph.add_node("tool_executor", tool_executor_agent)
    graph.add_node("response_generator", response_generator_agent)

    # Define edges (transitions)
    graph.set_entry_point("supervisor")

    graph.add_edge("supervisor", "intent_classifier")

    graph.add_conditional_edges(
        "intent_classifier",
        route_after_classification,
        {
            "clarify": "clarifier",
            "execute": "tool_executor",
            "end": "response_generator"
        }
    )

    graph.add_edge("clarifier", "intent_classifier")
    graph.add_edge("tool_executor", "response_generator")
    graph.set_finish_point("response_generator")

    return graph.compile()
```

---

## Technology Stack

### Core

- **Python:** 3.11+
- **Package Manager:** UV (uv 0.5+)
- **Web Framework:** FastAPI 0.115+
- **ASGI Server:** Uvicorn
- **Orchestration:** LangGraph 0.3+

### AI/ML

- **LLM Provider:** AWS Bedrock
- **Model:** Claude 3.5 Sonnet (anthropic.claude-3-5-sonnet-20240620-v1:0)
- **Agent Framework:** LangGraph
- **Prompt Management:** LangChain

### Database

- **Primary DB:** PostgreSQL 15 (Aurora Serverless v2)
- **ORM:** SQLAlchemy 2.0+ (async)
- **Migrations:** Alembic
- **Cache/State:** Redis 7.1 (ElastiCache)

### API Integration

- **HTTP Client:** httpx (async)
- **Retry Logic:** tenacity
- **Validation:** Pydantic v2

### Testing

- **Framework:** pytest + pytest-asyncio
- **HTTP Mocking:** httpx-mock
- **Coverage:** pytest-cov (target: 80%+)

### Observability

- **Logging:** structlog
- **Tracing:** AWS X-Ray
- **Metrics:** CloudWatch

---

## Project Structure (UV + FastAPI Module-Functionality)

```
backend/
├── pyproject.toml           # UV configuration, all dependencies
├── uv.lock                  # Deterministic dependency lock
├── .python-version          # Python version (3.11)
├── README.md
├── ARCHITECTURE.md          # This file
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry
│   │
│   ├── agents/              # Multi-agent system
│   │   ├── __init__.py
│   │   ├── supervisor.py    # Supervisor/Orchestrator agent
│   │   ├── intent_classifier.py  # Intent classification
│   │   ├── clarifier.py     # Clarification agent
│   │   ├── context_manager.py    # Context/memory management
│   │   ├── tool_executor.py      # Tool execution
│   │   └── response_generator.py # Response generation
│   │
│   ├── graph/               # LangGraph definitions
│   │   ├── __init__.py
│   │   ├── state.py         # State schema
│   │   ├── nodes.py         # Node functions
│   │   ├── edges.py         # Edge/routing functions
│   │   └── scheduling_graph.py   # Main graph definition
│   │
│   ├── core/                # Core infrastructure
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration management
│   │   ├── database.py      # Database connection (async)
│   │   ├── redis.py         # Redis connection
│   │   ├── bedrock.py       # AWS Bedrock client
│   │   └── logging.py       # Structured logging
│   │
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py          # Base model class
│   │   ├── session.py       # Session model
│   │   ├── conversation.py  # Conversation history
│   │   ├── appointment.py   # Appointments
│   │   └── user.py          # User/customer
│   │
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── chat.py          # Chat request/response
│   │   ├── agent.py         # Agent schemas
│   │   ├── intent.py        # Intent classification
│   │   ├── state.py         # State schemas
│   │   └── pf360.py         # PF360 API schemas
│   │
│   ├── services/            # Business logic services
│   │   ├── __init__.py
│   │   ├── bedrock_service.py    # Bedrock interactions
│   │   ├── pf360_service.py      # PF360 API client
│   │   ├── session_service.py    # Session management
│   │   └── conversation_service.py  # Conversation handling
│   │
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependencies
│   │   ├── routes.py        # Main routes
│   │   └── middleware.py    # Custom middleware
│   │
│   └── utils/               # Utilities
│       ├── __init__.py
│       ├── formatters.py    # Response formatters
│       └── validators.py    # Custom validators
│
├── alembic/                 # Database migrations
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
│
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_agents/
│   │   ├── test_supervisor.py
│   │   ├── test_intent_classifier.py
│   │   ├── test_clarifier.py
│   │   └── test_tool_executor.py
│   ├── test_graph/
│   │   └── test_scheduling_graph.py
│   ├── test_api/
│   │   └── test_routes.py
│   ├── test_services/
│   │   ├── test_bedrock_service.py
│   │   └── test_pf360_service.py
│   └── test_models/
│       └── test_session.py
│
└── scripts/                 # Utility scripts
    ├── seed_db.py
    └── test_bedrock_access.py
```

---

## Dependency Groups (UV)

**pyproject.toml structure:**

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "langgraph>=0.3.0",
    "langchain-aws>=0.2.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.14.0",
    "asyncpg>=0.30.0",
    "redis>=5.2.0",
    "httpx>=0.28.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "tenacity>=9.0.0",
    "structlog>=24.4.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx-mock>=0.17.0",
    "faker>=33.1.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

test = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx-mock>=0.17.0",
]
```

---

## API Endpoints

### Chat API

**POST /api/chat**

Request:
```json
{
  "message": "I want to schedule an appointment",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "1645975",
  "client_name": "projectsforce-validation"
}
```

Response:
```json
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

## Observability

### Logging

```python
import structlog

log = structlog.get_logger()

log.info(
    "intent_classified",
    session_id=session_id,
    intent=intent,
    confidence=confidence,
    user_message=user_message,
)
```

### Metrics (CloudWatch)

- Intent classification latency
- Agent execution time
- Tool execution success rate
- Clarification rate
- End-to-end request latency

### Tracing (AWS X-Ray)

- Trace full request through all agents
- Identify bottlenecks
- Debug complex multi-agent interactions

---

## Deployment

### Development

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Production (Docker)

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache
COPY ./app ./app
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Testing Strategy

### Unit Tests (70%)
- Individual agent functions
- Utility functions
- Validators, formatters

### Integration Tests (20%)
- LangGraph state transitions
- Database operations
- Redis operations
- API endpoint flows

### E2E Tests (10%)
- Full conversation flows
- Multi-turn interactions
- Error scenarios

**Target Coverage:** 80%+

---

## Migration Path from Current System

### Reusable from Current System (40%)

**From `core/tools.py` (527 lines):**
- PF360 API endpoint URLs
- PF360 API call patterns
- Tool function signatures
- Error handling patterns
- Environment variable configuration

**From `core/langchain_agent.py`:**
- System prompt instructions
- Tool descriptions
- Agent guidelines

**From `api/routes.py`:**
- Chat endpoint structure
- Request/response schemas
- Header extraction

### New Implementation (60%)

- Multi-agent architecture (LangGraph)
- Intent classification system
- Clarification logic
- Context management (Redis + DB)
- State machine orchestration
- Async database operations
- Observability and logging

---

## Performance Targets

- **P50 latency:** <1s (simple requests)
- **P95 latency:** <3s (complex requests)
- **P99 latency:** <5s
- **Intent classification accuracy:** >95%
- **Clarification rate:** <15%
- **Tool execution success rate:** >99%

---

## Security

- JWT authentication from current system
- Secret management via AWS Secrets Manager
- SQL injection prevention (SQLAlchemy parameterization)
- Input validation (Pydantic)
- Rate limiting (API Gateway)
- Audit logging (all tool executions)

---

**Architecture Version:** 1.0
**Last Updated:** October 12, 2025
**Status:** Design complete, ready for implementation
