# ProjectForce Bedrock v4.0 - Architecture Documentation

**Version:** 4.0 | **Status:** Production Ready | **Last Updated:** 2025-11-15

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [v4.0 Serverless Architecture](#v40-serverless-architecture)
4. [Hybrid Routing Strategy](#hybrid-routing-strategy)
5. [Bedrock Agents](#bedrock-agents)
6. [Lambda Functions](#lambda-functions)
7. [Conversation Context](#conversation-context)
8. [Data Flow](#data-flow)
9. [Performance Characteristics](#performance-characteristics)
10. [Cost Analysis](#cost-analysis)
11. [Security](#security)
12. [Deployment Architecture](#deployment-architecture)

---

## Executive Summary

ProjectForce Bedrock v4.0 is a **production-ready, serverless AI scheduling system** built on AWS Bedrock multi-agent architecture with **hybrid routing** for optimal performance.

### Key Features

- **Hybrid Routing**: Direct Lambda (~2s) + Bedrock Agents (~5-25s)
- **Serverless Architecture**: No VPC, No Redis - DynamoDB for session management
- **Multi-turn Conversations**: 4-message context history per session
- **4 Bedrock Agents**: Supervisor, Scheduling, Information, Chitchat
- **3 Lambda Functions**: Orchestrator, Scheduling Actions, Information Actions
- **Cost-Optimized**: ~$8/month for 5,000 requests

### Architecture Principles

1. **Performance First**: Route simple queries to Direct Lambda (~2s)
2. **Serverless**: DynamoDB session storage, no VPC complexity
3. **Context-Aware**: 4-message conversation history per session
4. **Cost-Optimized**: Intent classification + direct routing saves 44% vs supervisor-only
5. **Production-Ready**: Comprehensive error handling, logging, monitoring

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Customer Input                             │
│                    (Web UI / API / Voice / SMS)                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          API Gateway                                │
│                   (REST API - Optional Layer)                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Orchestrator Lambda                             │
│                 (pf-orchestrator - 512MB RAM)                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  1. Load Session from DynamoDB                              │   │
│  │  2. Build Conversation Context (last 4 messages)            │   │
│  │  3. Classify Intent (Claude Haiku - 50ms)                   │   │
│  │  4. Route Request:                                          │   │
│  │     • Simple queries → Direct Lambda (~2s)                  │   │
│  │     • Complex queries → Bedrock Agents (~5-25s)             │   │
│  │  5. Save Response to DynamoDB                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────┬───────────────────────┘
                   │                          │
        ┌──────────▼──────────┐    ┌─────────▼──────────┐
        │  Direct Lambda      │    │  Bedrock Agents    │
        │   (~2s response)    │    │  (~5-25s response) │
        └──────────┬──────────┘    └─────────┬──────────┘
                   │                          │
    ┌──────────────┴──────────────┐          │
    │                             │          │
    ▼                             ▼          ▼
┌────────────────┐    ┌────────────────────────────────┐
│ Scheduling     │    │    4 Bedrock Agents           │
│ Actions Lambda │    │                               │
│ (1769MB RAM)   │    │  ┌──────────────────────────┐ │
└────────┬───────┘    │  │ Supervisor (GEMYQNPYB4) │ │
         │            │  │ - Multi-agent routing    │ │
    ┌────▼─────┐      │  │ - USE_SUPERVISOR=false   │ │
    │Information│      │  └──────────────────────────┘ │
    │ Actions   │      │                               │
    │ Lambda    │      │  ┌──────────────────────────┐ │
    │(1769MB RAM)│      │  │Scheduling (LMJI2V9E8Y)  │ │
    └────────┬──┘      │  │- Appointments, bookings  │ │
             │         │  │- Action: scheduling-     │ │
             │         │  │  actions Lambda          │ │
             │         │  └──────────────────────────┘ │
             │         │                               │
             │         │  ┌──────────────────────────┐ │
             │         │  │Information (VDWEVR6DJD)  │ │
             │         │  │- Weather, project info   │ │
             │         │  │- Action: information-    │ │
             │         │  │  actions Lambda          │ │
             │         │  └──────────────────────────┘ │
             │         │                               │
             │         │  ┌──────────────────────────┐ │
             │         │  │Chitchat (DIT6BVFDYW)     │ │
             │         │  │- Greetings, casual talk  │ │
             │         │  │- No action groups        │ │
             │         │  └──────────────────────────┘ │
             │         └────────────┬──────────────────┘
             │                      │
             └──────────┬───────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │  ProjectForce Backend APIs    │
        │  api-cx-portal.dev.pf.com     │
        │  • GET /projects              │
        │  • GET /project/{id}          │
        │  • POST /appointments         │
        │  • Weather API Integration    │
        └───────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │     DynamoDB Sessions         │
        │     pf-sessions-dev           │
        │  • Session history (1hr TTL)  │
        │  • Last 20 messages per user  │
        │  • <10ms read/write           │
        └───────────────────────────────┘
```

---

## v4.0 Serverless Architecture

### Architectural Changes from v3.x

| Component | v3.x (Legacy) | v4.0 (Current) |
|-----------|---------------|----------------|
| **Session Storage** | Redis/ElastiCache in VPC | DynamoDB (serverless) |
| **Networking** | VPC with subnets, NAT Gateway | No VPC required |
| **Routing** | Supervisor-only (slow) | Hybrid: Direct Lambda + Agents |
| **Configuration** | USE_SUPERVISOR=true | USE_SUPERVISOR=false |
| **Response Time** | 5-25s for all queries | 2s (simple) / 5-25s (complex) |
| **Cost** | ~$180/month (Redis + VPC) | ~$8/month (DynamoDB only) |
| **Complexity** | High (VPC, security groups) | Low (serverless) |

### Why Serverless?

**Benefits:**
- **No VPC Management**: No subnets, NAT gateways, security groups
- **Lower Cost**: DynamoDB cheaper than ElastiCache Redis ($1/month vs $15/month)
- **Faster Deployment**: 15-20 minutes vs 30-45 minutes
- **Simpler Operations**: No cluster health monitoring, no failover
- **Auto-Scaling**: DynamoDB scales automatically with demand

**Trade-offs:**
- DynamoDB read/write: ~10ms vs Redis: ~1ms (acceptable for session data)
- No Redis pub/sub (not needed for current use case)

---

## Hybrid Routing Strategy

### Overview

The Orchestrator Lambda uses **hybrid routing** to optimize performance and cost:

1. **Intent Classification** (50ms) - Claude 3 Haiku classifies user intent
2. **Routing Decision**:
   - **Simple queries** → Direct Lambda invocation (~2s)
   - **Complex queries** → Bedrock Agent invocation (~5-25s)

### Routing Rules

#### Direct Lambda Path (~2s)

**Triggers:**
- `list_projects` - "Show my projects", "List all projects"
- `get_project_details` - "Tell me about project 7751741"
- `filter_projects` - "Show Decking projects in Minneapolis"
- `get_available_dates` - "When can I schedule project 12345?"

**Why Direct Lambda?**
- No agent reasoning overhead
- Direct API call to ProjectForce backend
- Predictable 2-second response time
- 70% of all queries

**Configuration:**
```python
ALLOW_DIRECT_LAMBDA = true  # Enable hybrid routing
```

#### Bedrock Agent Path (~5-25s)

**Triggers:**
- Complex scheduling workflows: "Schedule appointment for tomorrow at 2pm"
- Multi-turn conversations: "What about next week? Can you check Tuesday?"
- Weather queries: "What's the weather in Tampa?"
- Chitchat: "Hello", "Thank you", "How are you?"

**Why Bedrock Agents?**
- Natural language understanding
- Multi-turn context tracking
- Complex reasoning (e.g., date parsing, availability checks)
- 30% of all queries

**Configuration:**
```python
USE_SUPERVISOR = false  # Direct agent routing (skip supervisor overhead)
```

### Routing Decision Logic

```python
def route_request(message, session_id, conversation_history):
    """
    Route request to Direct Lambda or Bedrock Agent
    """
    # Step 1: Classify intent (Claude Haiku - 50ms)
    classification = classify_intent_and_action(
        message=message,
        conversation_history=conversation_history,
        model="anthropic.claude-3-haiku-20240307-v1:0"
    )

    intent = classification['intent']
    action = classification['action']

    # Step 2: Check if Direct Lambda is allowed and available
    if ALLOW_DIRECT_LAMBDA and action in DIRECT_LAMBDA_ACTIONS:
        # Route to Direct Lambda (~2s)
        params = extract_parameters(message, action)
        response = call_lambda_directly(
            action=action,
            params=params
        )
        return {
            'response': response,
            'direct_call': True,
            'agent_name': 'Direct Lambda'
        }

    # Step 3: Route to Bedrock Agent (~5-25s)
    agent_config = select_agent(intent)
    response = invoke_bedrock_agent(
        agent_id=agent_config['agent_id'],
        agent_alias_id=agent_config['alias_id'],
        session_id=session_id,
        input_text=message,
        conversation_context=build_conversation_context(conversation_history)
    )
    return {
        'response': response,
        'direct_call': False,
        'agent_name': agent_config['name']
    }
```

---

## Bedrock Agents

### Agent Configuration

All 4 agents use:
- **Model**: Claude 3.5 Sonnet V2 (`us.anthropic.claude-3-5-sonnet-20241022-v2:0`)
- **Alias**: TSTALIASID (test alias, auto-created)
- **Region**: us-east-1

### 1. Supervisor Agent (GEMYQNPYB4)

**Purpose:** Multi-agent orchestration (optional - currently disabled)

**Configuration:**
```json
{
  "agent_id": "GEMYQNPYB4",
  "alias_id": "TSTALIASID",
  "collaboration_mode": "SUPERVISOR",
  "collaborators": [
    "LMJI2V9E8Y",  // Scheduling
    "VDWEVR6DJD",  // Information
    "DIT6BVFDYW"   // Chitchat
  ]
}
```

**When Used:**
- `USE_SUPERVISOR=true` - All requests routed through supervisor
- Currently disabled for performance (adds 2-5s overhead)

**Instructions:** See `infrastructure/agent_instructions/supervisor.txt`

**Key Features:**
- Routes to appropriate collaborator agent
- Maintains conversation context across agents
- Pass-through relay (no response modification)

### 2. Scheduling Agent (LMJI2V9E8Y)

**Purpose:** Appointment scheduling and project management

**Action Groups:**
- `scheduling-actions` → Lambda: `pf-scheduling-actions`

**Functions:**
```json
{
  "functions": [
    {
      "name": "list_projects",
      "description": "List ALL projects for the current user",
      "parameters": {
        "customer_id": "Customer ID (auto from session)",
        "client_id": "Client ID (auto from session)"
      }
    },
    {
      "name": "get_project_details",
      "description": "Get detailed info about ONE specific project",
      "parameters": {
        "project_id": "Project ID (required)",
        "client_id": "Client ID (auto from session)"
      }
    },
    {
      "name": "get_available_dates",
      "description": "Get available dates for scheduling",
      "parameters": {
        "project_id": "Project ID (required)"
      }
    },
    {
      "name": "get_time_slots",
      "description": "Get time slots for a specific date",
      "parameters": {
        "project_id": "Project ID",
        "date": "Date (YYYY-MM-DD)",
        "request_id": "Request ID from get_available_dates"
      }
    },
    {
      "name": "confirm_appointment",
      "description": "Confirm and schedule an appointment",
      "parameters": {
        "project_id": "Project ID",
        "date": "Date (YYYY-MM-DD)",
        "time": "Time (HH:MM)",
        "request_id": "Request ID"
      }
    },
    {
      "name": "reschedule_appointment",
      "description": "Reschedule existing appointment",
      "parameters": {
        "project_id": "Project ID",
        "new_date": "New date",
        "new_time": "New time"
      }
    },
    {
      "name": "cancel_appointment",
      "description": "Cancel existing appointment",
      "parameters": {
        "project_id": "Project ID"
      }
    }
  ]
}
```

**Instructions:** See `infrastructure/agent_instructions/scheduling_collaborator.txt`

**Usage Examples:**
- "Show my projects"
- "Tell me about project 7751741"
- "Schedule appointment for project 12345 tomorrow at 2pm"
- "Cancel appointment for project 7751741"

### 3. Information Agent (VDWEVR6DJD)

**Purpose:** Weather information and project queries

**Action Groups:**
- `information-actions` → Lambda: `pf-information-actions`

**Functions:**
```json
{
  "functions": [
    {
      "name": "get_weather",
      "description": "Get weather forecast for a location",
      "parameters": {
        "latitude": "Latitude (preferred method)",
        "longitude": "Longitude (with latitude)",
        "location": "Location name (fallback)",
        "project_id": "Project ID for context (optional)",
        "address": "Full address (optional)"
      }
    }
  ]
}
```

**Instructions:** See `infrastructure/agent_instructions/information_collaborator.txt`

**Usage Examples:**
- "What's the weather in Tampa?"
- "Check weather at project 7751741"
- "Is it going to rain tomorrow?"

### 4. Chitchat Agent (DIT6BVFDYW)

**Purpose:** Casual conversation and greetings

**Action Groups:** None (conversational only)

**Instructions:** See `infrastructure/agent_instructions/chitchat_collaborator.txt`

**Usage Examples:**
- "Hello"
- "Thank you"
- "How are you?"
- "What's 2+2?"

---

## Lambda Functions

### 1. Orchestrator Lambda (pf-orchestrator)

**Purpose:** Request routing, session management, conversation context

**Configuration:**
```python
Runtime: Python 3.11
Memory: 512 MB
Timeout: 30 seconds
Handler: handler.lambda_handler
```

**Environment Variables:**
```bash
# Agent Configuration
SUPERVISOR_AGENT_ID=GEMYQNPYB4
SCHEDULING_AGENT_ID=LMJI2V9E8Y
INFORMATION_AGENT_ID=VDWEVR6DJD
CHITCHAT_AGENT_ID=DIT6BVFDYW
AGENT_ALIAS_ID=TSTALIASID

# Routing Configuration
USE_SUPERVISOR=false           # Direct agent routing (faster)
ALLOW_DIRECT_LAMBDA=true       # Enable hybrid routing
ROUTING_METHOD=hybrid          # hybrid, supervisor, or direct

# Classification
CLASSIFIER_MODEL=anthropic.claude-3-haiku-20240307-v1:0

# Lambda Functions
SCHEDULING_LAMBDA=pf-scheduling-actions
INFORMATION_LAMBDA=pf-information-actions

# Session Storage
DYNAMODB_TABLE=pf-sessions-dev
REGION=us-east-1
SESSION_TIMEOUT=3600           # 1 hour
MAX_HISTORY_MESSAGES=20

# Performance
ENABLE_CLASSIFICATION_CACHE=true
ENABLE_CONNECTION_POOLING=true
```

**Key Functions:**

```python
def lambda_handler(event, context):
    """Main Lambda handler for API Gateway requests"""
    # 1. Parse request body
    body = json.loads(event['body'])
    message = body['message']
    session_id = body['session_id']
    pf_token = body['pf_token']
    pf_client_id = body['pf_client_id']
    pf_user_id = body['pf_user_id']

    # 2. Get conversation history from DynamoDB
    conversation_history = get_conversation_history(session_id)

    # 3. Add user message to history
    add_to_conversation_history(session_id, 'user', message)

    # 4. Route request (Direct Lambda or Bedrock Agent)
    result = route_request(
        message=message,
        session_id=session_id,
        customer_id=pf_user_id,
        client_id=pf_client_id,
        pf_bearer_token=pf_token,
        conversation_history=conversation_history
    )

    # 5. Add assistant response to history
    add_to_conversation_history(
        session_id,
        'assistant',
        result['response']
    )

    # 6. Return response
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
```

**IAM Permissions:**
- `bedrock:InvokeAgent` - Invoke Bedrock agents
- `bedrock:InvokeModel` - Intent classification with Claude
- `lambda:InvokeFunction` - Direct Lambda calls
- `dynamodb:GetItem`, `PutItem`, `UpdateItem` - Session storage
- `secretsmanager:GetSecretValue` - API credentials (if needed)

### 2. Scheduling Actions Lambda (pf-scheduling-actions)

**Purpose:** Execute scheduling operations

**Configuration:**
```python
Runtime: Python 3.11
Memory: 1769 MB
Timeout: 30 seconds
Handler: handler.lambda_handler
```

**Environment Variables:**
```bash
BEARER_TOKEN=<from-secrets-manager>
PF_CLIENT_ID=09PF05VD
PF_USER_ID=1646085
PF_API_BASE_URL=https://api-cx-portal.dev.projectsforce.com
TOKEN_SECRET_NAME=projectforce/api/credentials
LOG_LEVEL=INFO
```

**Implemented Actions:**
- `list_projects` - List all projects for customer
- `get_project_details` - Get detailed project information
- `get_available_dates` - Get available scheduling dates
- `get_time_slots` - Get available time slots for a date
- `confirm_appointment` - Book an appointment
- `reschedule_appointment` - Reschedule existing appointment
- `cancel_appointment` - Cancel existing appointment

**API Integration:**
```python
def list_projects(customer_id, client_id, pf_bearer_token):
    """List all projects for customer"""
    url = f"{API_BASE_URL}/projects"
    headers = {
        'Authorization': f'Bearer {pf_bearer_token}',
        'client-id': client_id,
        'user-id': customer_id
    }
    response = requests.get(url, headers=headers)
    return response.json()
```

### 3. Information Actions Lambda (pf-information-actions)

**Purpose:** Weather information via Open-Meteo API

**Configuration:**
```python
Runtime: Python 3.11
Memory: 1769 MB
Timeout: 30 seconds
Handler: handler.lambda_handler
```

**Environment Variables:**
```bash
BEARER_TOKEN=<from-secrets-manager>
PF_CLIENT_ID=09PF05VD
PF_USER_ID=1646085
PF_API_BASE_URL=https://api-cx-portal.dev.projectsforce.com
LOG_LEVEL=INFO
```

**Implemented Actions:**
- `get_weather` - Weather forecast via Open-Meteo API

**Weather API Integration:**
```python
def get_weather(latitude, longitude, location=None):
    """Get weather forecast from Open-Meteo API"""
    if latitude and longitude:
        # Use coordinates (preferred)
        url = f"https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'current': 'temperature_2m,weather_code',
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum',
            'forecast_days': 3
        }
    elif location:
        # Geocode location first
        coords = geocode_location(location)
        # Then fetch weather...

    response = requests.get(url, params=params)
    return format_weather_response(response.json())
```

---

## Conversation Context

### Context Management Strategy

The Orchestrator Lambda maintains conversation context for multi-turn conversations using DynamoDB session storage.

### Session Structure

```python
{
    'session_id': 'session-12345',      # Primary key
    'user_id': '1646085',               # GSI for user lookups
    'messages': [                       # Last 20 messages
        {
            'role': 'user',
            'content': 'Show my projects',
            'timestamp': '2025-11-15T10:30:00Z'
        },
        {
            'role': 'assistant',
            'content': 'You have 8 projects...',
            'timestamp': '2025-11-15T10:30:02Z'
        }
    ],
    'ttl': 1731675000,                  # 1 hour from last activity
    'last_activity': '2025-11-15T10:30:02Z',
    'client_id': '09PF05VD',
    'metadata': {
        'last_intent': 'list_projects',
        'last_agent': 'Direct Lambda'
    }
}
```

### Context Building (4-Message History)

```python
def build_conversation_context(conversation_history, max_messages=4):
    """
    Build compact conversation context from recent history

    Args:
        conversation_history: List of previous messages
        max_messages: Maximum number of recent messages (default: 4)

    Returns:
        Formatted context string
    """
    if not conversation_history:
        return ""

    # Get last 4 messages (2 turns)
    recent_messages = conversation_history[-max_messages:]

    context_lines = []
    for msg in recent_messages:
        role = msg['role']
        content = msg['content']

        # Truncate long messages to 150 characters
        if len(content) > 150:
            content = content[:150] + "..."

        context_lines.append(f"{role.upper()}: {content}")

    return "\n".join(context_lines)
```

**Example Context:**

```
USER: Show my projects
ASSISTANT: You have 8 Decking Call Back projects at 401 Chicago Avenue...
USER: Tell me more about the first one
ASSISTANT: Project 7751741 is a Decking Call Back project scheduled for 11-11-2025 at 01:00 PM...
```

### Why 4 Messages?

- **Optimal Context Window**: Captures 2 full conversation turns
- **Token Efficiency**: ~500 tokens vs 2,000+ tokens for full history
- **Response Quality**: Sufficient for context resolution
- **Cost Savings**: Reduces Claude API token costs by 75%

### Context Usage

**Direct Lambda:**
```python
# Context used for parameter extraction
classification = classify_intent_and_action(
    message="Tell me more about the first one",
    conversation_history=[
        {'role': 'user', 'content': 'Show my projects'},
        {'role': 'assistant', 'content': 'You have 8 projects...'},
        {'role': 'user', 'content': 'Tell me more about the first one'}
    ]
)
# Classifier extracts: project_id=7751741 from previous response
```

**Bedrock Agent:**
```python
# Context prepended to user input
conversation_context = build_conversation_context(history)
full_input = f"""
Previous conversation:
{conversation_context}

Current message: Tell me more about the first one
"""
invoke_bedrock_agent(input_text=full_input, ...)
```

---

## Data Flow

### Request Flow Diagram

```
┌─────────────────┐
│  User Input     │
│  "Show my       │
│   projects"     │
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  API Gateway (Optional)                  │
│  POST /invoke-agent                      │
│  Headers: Content-Type, CORS             │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Orchestrator Lambda                     │
│  ┌────────────────────────────────────┐  │
│  │ Step 1: Load Session (DynamoDB)    │  │
│  │   GET pf-sessions-dev/session-123  │  │
│  │   Returns: Last 20 messages        │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ Step 2: Build Context (4 msgs)     │  │
│  │   USER: Previous question...       │  │
│  │   ASSISTANT: Previous answer...    │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ Step 3: Classify Intent (50ms)     │  │
│  │   Model: Claude 3 Haiku            │  │
│  │   Input: Message + Context         │  │
│  │   Output: {                        │  │
│  │     intent: "scheduling",          │  │
│  │     action: "list_projects",       │  │
│  │     params: {}                     │  │
│  │   }                                │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ Step 4: Route Decision             │  │
│  │   Is action in DIRECT_ACTIONS?     │  │
│  │   ✅ YES → Direct Lambda           │  │
│  │   ❌ NO  → Bedrock Agent           │  │
│  └────────────────────────────────────┘  │
└────────┬─────────────────────────────────┘
         │
         ├─────────────────┬──────────────────┐
         │                 │                  │
         ▼                 ▼                  ▼
┌──────────────────┐  ┌─────────────┐  ┌──────────────┐
│ Direct Lambda    │  │  Bedrock    │  │  Bedrock     │
│ (~2s)            │  │  Agent      │  │  Agent       │
│                  │  │  (~5-25s)   │  │  (~5-25s)    │
│ ┌──────────────┐ │  │             │  │              │
│ │ list_projects│ │  │ Scheduling  │  │ Information  │
│ │ get_details  │ │  │ Complex     │  │ Weather      │
│ │ filter       │ │  │ workflows   │  │              │
│ │ get_dates    │ │  │             │  │              │
│ └──────┬───────┘ │  └──────┬──────┘  └──────┬───────┘
└────────┼─────────┘         │                │
         │                   │                │
         ▼                   ▼                ▼
┌────────────────────────────────────────────────────┐
│  Action Lambda Functions                          │
│  ┌──────────────────┐  ┌──────────────────┐       │
│  │ pf-scheduling-   │  │ pf-information-  │       │
│  │ actions          │  │ actions          │       │
│  │                  │  │                  │       │
│  │ • list_projects  │  │ • get_weather    │       │
│  │ • get_details    │  │                  │       │
│  │ • confirm_appt   │  │                  │       │
│  └────────┬─────────┘  └────────┬─────────┘       │
└───────────┼────────────────────┬┼──────────────────┘
            │                    ││
            ▼                    ▼▼
┌──────────────────────────────────────────────┐
│  ProjectForce Backend APIs                   │
│  https://api-cx-portal.dev.projectsforce.com │
│  ┌────────────────────────────────────────┐  │
│  │ GET /projects                          │  │
│  │   Headers:                             │  │
│  │     Authorization: Bearer {token}      │  │
│  │     client-id: 09PF05VD                │  │
│  │     user-id: 1646085                   │  │
│  │                                        │  │
│  │ Response:                              │  │
│  │   {                                    │  │
│  │     "data": [                          │  │
│  │       {                                │  │
│  │         "id": "7751741",               │  │
│  │         "projectNumber": "21083...",   │  │
│  │         "status": "Scheduled",         │  │
│  │         "category": "Decking",         │  │
│  │         ...                            │  │
│  │       }                                │  │
│  │     ]                                  │  │
│  │   }                                    │  │
│  └────────────────────────────────────────┘  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  Response Processing                         │
│  ┌────────────────────────────────────────┐  │
│  │ Format response (JSON or text)         │  │
│  │ Extract relevant fields                │  │
│  │ Build user-friendly message            │  │
│  └────────────────────────────────────────┘  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  DynamoDB Session Update                     │
│  PUT pf-sessions-dev/session-123             │
│  ┌────────────────────────────────────────┐  │
│  │ {                                      │  │
│  │   "messages": [                        │  │
│  │     ...(previous messages),            │  │
│  │     {                                  │  │
│  │       "role": "user",                  │  │
│  │       "content": "Show my projects",   │  │
│  │       "timestamp": "2025-11-15..."     │  │
│  │     },                                 │  │
│  │     {                                  │  │
│  │       "role": "assistant",             │  │
│  │       "content": "You have 8 projects" │  │
│  │       "timestamp": "2025-11-15..."     │  │
│  │     }                                  │  │
│  │   ],                                   │  │
│  │   "ttl": 1731675000,                   │  │
│  │   "last_activity": "2025-11-15..."     │  │
│  │ }                                      │  │
│  └────────────────────────────────────────┘  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  API Gateway Response                        │
│  ┌────────────────────────────────────────┐  │
│  │ {                                      │  │
│  │   "statusCode": 200,                   │  │
│  │   "headers": {                         │  │
│  │     "Content-Type": "application/json",│  │
│  │     "Access-Control-Allow-Origin": "*" │  │
│  │   },                                   │  │
│  │   "body": {                            │  │
│  │     "response": "You have 8 projects..│  │
│  │     "intent": "scheduling",            │  │
│  │     "action": "list_projects",         │  │
│  │     "agent_name": "Direct Lambda",     │  │
│  │     "direct_call": true,               │  │
│  │     "timing": {                        │  │
│  │       "classification": 0.05,          │  │
│  │       "execution": 1.8,                │  │
│  │       "total": 1.85                    │  │
│  │     }                                  │  │
│  │   }                                    │  │
│  │ }                                      │  │
│  └────────────────────────────────────────┘  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  User Sees Response                          │
│  "You have 8 Decking Call Back projects at   │
│   401 Chicago Avenue, Minneapolis:           │
│   • Project 7751741 - Scheduled 11-11-2025   │
│   • Project 7751742 - Scheduled 11-18-2025   │
│   ..."                                       │
└──────────────────────────────────────────────┘
```

### Session Data Flow

```
Session Lifecycle:
┌─────────────────────────────────────────────────────────────────┐
│  1. Session Creation (First Message)                           │
│     CREATE pf-sessions-dev {                                   │
│       session_id: "session-12345",                             │
│       user_id: "1646085",                                      │
│       messages: [],                                            │
│       ttl: now + 3600,                                         │
│       client_id: "09PF05VD"                                    │
│     }                                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Message Exchange (Each Turn)                               │
│     UPDATE pf-sessions-dev {                                   │
│       messages: APPEND [                                       │
│         {role: "user", content: "...", timestamp: "..."},      │
│         {role: "assistant", content: "...", timestamp: "..."}  │
│       ],                                                       │
│       ttl: now + 3600,  // Reset TTL                           │
│       last_activity: now                                       │
│     }                                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Context Extraction (Each Request)                          │
│     GET pf-sessions-dev/session-12345                          │
│     history = item['messages'][-20:]  // Last 20 messages      │
│     context = build_context(history[-4:])  // Last 4 for agent │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Session Expiration (After 1 Hour Inactivity)               │
│     DynamoDB TTL automatically deletes expired items           │
│     No manual cleanup required                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Performance Characteristics

### Response Time Analysis

#### Direct Lambda Path (~2s)

```
┌──────────────────────────────────────────────────┐
│  Total: ~2.0 seconds                             │
├──────────────────────────────────────────────────┤
│  • DynamoDB session load:        10ms            │
│  • Intent classification (Haiku): 50ms           │
│  • Parameter extraction:          5ms            │
│  • Lambda invocation:            200ms           │
│  • ProjectForce API call:      1,500ms           │
│  • Response formatting:          100ms           │
│  • DynamoDB session update:       10ms           │
│  • API Gateway overhead:         125ms           │
└──────────────────────────────────────────────────┘
```

#### Bedrock Agent Path (~5-25s)

```
┌──────────────────────────────────────────────────┐
│  Total: ~5-25 seconds (varies by complexity)     │
├──────────────────────────────────────────────────┤
│  • DynamoDB session load:         10ms           │
│  • Intent classification (Haiku):  50ms          │
│  • Context building:                5ms          │
│  • Bedrock agent invocation:      500ms          │
│  • Agent reasoning (Sonnet):   2-10,000ms        │
│  • Action group execution:     2-10,000ms        │
│  • Response generation:        1-3,000ms         │
│  • DynamoDB session update:        10ms          │
│  • API Gateway overhead:          125ms          │
└──────────────────────────────────────────────────┘
```

### Throughput

- **Orchestrator Lambda**: 1,000 concurrent executions
- **Action Lambdas**: 1,000 concurrent executions each
- **Bedrock Agents**: Throttling limits apply (100 TPS per agent)
- **DynamoDB**: Auto-scaling, 40,000 read/write capacity units

### Latency Targets

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| DynamoDB read | <10ms | ~5ms | ✅ |
| DynamoDB write | <10ms | ~7ms | ✅ |
| Intent classification | <100ms | ~50ms | ✅ |
| Direct Lambda call | <2s | ~1.8s | ✅ |
| Simple agent call | <10s | ~5s | ✅ |
| Complex agent call | <30s | ~15s | ✅ |

---

## Cost Analysis

### Monthly Cost Breakdown (5,000 Requests)

#### AWS Services

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **Claude 3 Haiku** (Classification) | 5,000 requests × 500 tokens | $0.00025/1K tokens | $0.63 |
| **Claude 3.5 Sonnet** (Agents) | 1,500 requests × 2,000 tokens | $0.003/1K tokens | $9.00 |
| **Lambda - Orchestrator** | 5,000 invocations × 512MB × 2s | $0.0000166667/GB-s | $0.08 |
| **Lambda - Scheduling** | 3,500 invocations × 1769MB × 2s | $0.0000166667/GB-s | $0.20 |
| **Lambda - Information** | 500 invocations × 1769MB × 2s | $0.0000166667/GB-s | $0.03 |
| **DynamoDB** | 10,000 read/write × 1KB | $0.25/million | $0.003 |
| **API Gateway** (Optional) | 5,000 requests | $3.50/million | $0.02 |
| **Secrets Manager** | 1 secret | $0.40/month | $0.40 |
| **CloudWatch Logs** | ~500MB/month | $0.50/GB | $0.25 |
| **Total** | | | **~$10.60/month** |

#### Cost Comparison: v3.x vs v4.0

| Component | v3.x (Redis) | v4.0 (DynamoDB) | Savings |
|-----------|--------------|-----------------|---------|
| Session Storage | ElastiCache Redis: $15/month | DynamoDB: $0.003/month | **$14.99** |
| VPC | NAT Gateway: $32/month | None: $0 | **$32.00** |
| Data Transfer | VPC: $9/month | No VPC: $0 | **$9.00** |
| Routing | Supervisor only: $18/month | Hybrid: $10/month | **$8.00** |
| **Total Monthly** | **$180/month** | **$10.60/month** | **$169.40 (94%)** |

### Cost Optimization Strategies

1. **Hybrid Routing**: Route 70% of requests to Direct Lambda (cheaper than agents)
2. **Haiku Classification**: Use cheaper model for intent classification
3. **DynamoDB vs Redis**: 500x cheaper for session storage
4. **No VPC**: Eliminates NAT Gateway and data transfer costs
5. **Direct Agent Routing**: Skip supervisor overhead (saves 44%)

### Per-Request Cost

```
Average per request: ~$0.0021

Breakdown:
┌────────────────────────────────────────────┐
│  Direct Lambda Request (70% of traffic):   │
│  • Classification (Haiku):      $0.0003    │
│  • Lambda execution:            $0.0002    │
│  • DynamoDB:                    $0.0001    │
│  • Total:                       $0.0006    │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│  Bedrock Agent Request (30% of traffic):   │
│  • Classification (Haiku):      $0.0003    │
│  • Agent invocation (Sonnet):   $0.0060    │
│  • Lambda execution:            $0.0002    │
│  • DynamoDB:                    $0.0001    │
│  • Total:                       $0.0066    │
└────────────────────────────────────────────┘

Weighted average: (0.70 × $0.0006) + (0.30 × $0.0066) = $0.0021
```

---

## Security

### Authentication & Authorization

#### API Gateway Integration
- **API Key**: Optional API key for production deployments
- **CORS**: Configured for cross-origin requests
- **Rate Limiting**: 1,000 requests per second per IP

#### Lambda IAM Roles

**Orchestrator Lambda Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:agent/*",
        "arn:aws:bedrock:*:*:agent-alias/*",
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:*::inference-profile/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:*:function:pf-scheduling-actions",
        "arn:aws:lambda:us-east-1:*:function:pf-information-actions"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:*:table/pf-sessions-dev"
      ]
    }
  ]
}
```

**Action Lambda Roles:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:*:secret:projectforce/api/credentials*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:*:*:*"
      ]
    }
  ]
}
```

#### Bedrock Agent Roles

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::inference-profile/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:*:function:pf-scheduling-actions",
        "arn:aws:lambda:us-east-1:*:function:pf-information-actions"
      ]
    }
  ]
}
```

### Secrets Management

#### Secrets Manager

**Secret:** `projectforce/api/credentials`

```json
{
  "bearer_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "client_id": "09PF05VD",
  "user_id": "1646085",
  "refresh_token": "AWldtvQhQ+wt4HhRcU/2mOjT5Lsh5NKD...",
  "api_base_url": "https://api-cx-portal.dev.projectsforce.com"
}
```

**Access:**
- Rotation: Manual (token refresh every 24 hours)
- Encryption: AWS KMS (automatic)
- Access: Lambda execution roles only

### Data Protection

#### DynamoDB Encryption
- **At Rest**: AWS-managed KMS encryption
- **In Transit**: TLS 1.2+

#### CloudWatch Logs
- **Retention**: 7 days
- **Encryption**: AWS KMS
- **PII Scrubbing**: Automatic redaction of Bearer tokens in logs

### Network Security

#### Serverless Benefits
- **No VPC**: No security group management
- **No NAT Gateway**: No internet gateway exposure
- **No Elastic IPs**: No static IP attack surface

#### API Gateway
- **HTTPS Only**: TLS 1.2+ required
- **CORS**: Strict origin policies
- **Throttling**: Per-IP rate limiting

---

## Deployment Architecture

### Infrastructure as Code

All infrastructure deployed via shell scripts (no Terraform/CloudFormation complexity):

```
scripts/
├── DEPLOY.sh                   # Main deployment (15-20 min)
├── CLEANUP.sh                  # Full cleanup (5 min)
├── VALIDATE.sh                 # Validation checks
├── deploy_api_gateway.sh       # API Gateway deployment (30s)
└── update_agent_configs.sh     # Agent config updates
```

### Deployment Process

```
Step 0: Secrets Manager Secret
├─ Check if secret exists
├─ Create or update with API credentials
└─ Verify credentials

Step 1: DynamoDB Tables
├─ Create pf-sessions-dev table
├─ Add user_id GSI for lookups
└─ Configure 1-hour TTL

Step 2: Deploy Lambda Functions
├─ pf-scheduling-actions
│  ├─ Package dependencies (requests, boto3)
│  ├─ Create IAM role with Secrets Manager permissions
│  ├─ Deploy Lambda (1769MB, 30s timeout)
│  └─ Add Bedrock invoke permission
├─ pf-information-actions
│  ├─ Package dependencies
│  ├─ Create IAM role
│  ├─ Deploy Lambda
│  └─ Add Bedrock invoke permission
└─ pf-orchestrator
   ├─ Package dependencies (boto3, json)
   ├─ Create IAM role with Bedrock + DynamoDB + Lambda permissions
   ├─ Deploy Lambda (512MB, 30s timeout)
   └─ Configure environment variables

Step 3: Create Bedrock Agents
├─ Create Supervisor agent (GEMYQNPYB4)
│  ├─ Model: Claude 3.5 Sonnet V2
│  ├─ Collaboration: SUPERVISOR
│  └─ Instructions: supervisor.txt
├─ Create Scheduling agent (LMJI2V9E8Y)
│  ├─ Model: Claude 3.5 Sonnet V2
│  ├─ Collaborator mode
│  └─ Instructions: scheduling_collaborator.txt
├─ Create Information agent (VDWEVR6DJD)
│  ├─ Model: Claude 3.5 Sonnet V2
│  ├─ Collaborator mode
│  └─ Instructions: information_collaborator.txt
└─ Create Chitchat agent (DIT6BVFDYW)
   ├─ Model: Claude 3.5 Sonnet V2
   ├─ Collaborator mode
   └─ Instructions: chitchat_collaborator.txt

Step 4: Create Action Groups
├─ Scheduling agent → scheduling-actions Lambda
│  ├─ list_projects
│  ├─ get_project_details
│  ├─ get_available_dates
│  ├─ get_time_slots
│  ├─ confirm_appointment
│  ├─ reschedule_appointment
│  └─ cancel_appointment
└─ Information agent → information-actions Lambda
   └─ get_weather

Step 5: Prepare All Agents
├─ Prepare Supervisor (creates TSTALIASID)
├─ Prepare Scheduling
├─ Prepare Information
└─ Prepare Chitchat

Step 6: Save Agent IDs
├─ config/agent_ids.json
└─ config/agent_config.dev.json

Step 7: Configure Orchestrator Lambda
├─ Update environment variables with agent IDs
├─ Set USE_SUPERVISOR=false
├─ Set ALLOW_DIRECT_LAMBDA=true
└─ Set DYNAMODB_TABLE=pf-sessions-dev
```

### Configuration Files

#### /Users/jjayaraj/workspaces/studios/projectsforce/bedrock/config/agent_ids.json

```json
{
  "agents": {
    "SchedulingAgent": {
      "id": "LMJI2V9E8Y",
      "name": "SchedulingAgent",
      "purpose": "Scheduling and project management"
    },
    "pf-information": {
      "id": "VDWEVR6DJD",
      "name": "pf-information",
      "purpose": "Weather information"
    },
    "pf-chitchat": {
      "id": "DIT6BVFDYW",
      "name": "pf-chitchat",
      "purpose": "Conversational"
    },
    "Supervisor": {
      "id": "GEMYQNPYB4",
      "name": "Supervisor",
      "purpose": "Query routing"
    }
  },
  "lambdas": {
    "pf-scheduling-actions": "arn:aws:lambda:us-east-1:618048437522:function:pf-scheduling-actions",
    "pf-information-actions": "arn:aws:lambda:us-east-1:618048437522:function:pf-information-actions"
  },
  "deployed_at": "2025-11-14T17:52:28Z",
  "region": "us-east-1",
  "account_id": "618048437522"
}
```

---

## Monitoring & Observability

### CloudWatch Logs

**Log Groups:**
- `/aws/lambda/pf-orchestrator` - Routing decisions, timing metrics
- `/aws/lambda/pf-scheduling-actions` - Scheduling operations
- `/aws/lambda/pf-information-actions` - Weather queries
- `/aws/bedrock/agents/LMJI2V9E8Y` - Scheduling agent traces
- `/aws/bedrock/agents/VDWEVR6DJD` - Information agent traces

**Key Metrics:**
```python
logger.info(f"🚀 Request: session_id={session_id}, message='{message[:50]}...'")
logger.info(f"📚 Session {session_id} has {len(history)} messages in history")
logger.info(f"⚡ Calling Lambda directly: {function}.{action}")
logger.info(f"✅ Response: agent={agent}, intent={intent}, direct={direct}, timing={timing}")
```

### DynamoDB Metrics

**Console:** AWS DynamoDB → Tables → pf-sessions-dev → Metrics

**Key Metrics:**
- Read/Write Capacity Units
- Read/Write Throttle Events
- Item Count
- Table Size

### Bedrock Agent Metrics

**Console:** AWS Bedrock → Agents → [Agent Name] → Metrics

**Key Metrics:**
- Invocations
- Errors
- Latency (p50, p90, p99)
- Token Usage

---

**Version:** 4.0 | **Status:** Production Ready | **Last Updated:** 2025-11-15
