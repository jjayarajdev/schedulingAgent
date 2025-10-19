# Scheduling Agent - Project Documentation

## Overview

An AI-powered customer service scheduling agent built with FastAPI and LangChain that helps customers with scheduling, rescheduling, and cancellation of project appointments through conversational interactions.

## Project Structure

```
schedulingAgent-bb/
├── api/
│   └── routes.py              # API routes
├── core/
│   ├── context.py            # Session context (in-memory dict)
│   ├── langchain_agent.py    # Agent configuration with tools and prompt
│   ├── llm.py                # LLM configuration with rate limiting
│   ├── memory.py             # ConversationBufferMemory
│   └── tools.py              # Tool implementations
├── models/
│   └── schemas.py            # ChatRequest and ChatResponse models
├── archive/                  # Previous versions
├── main.py                   # FastAPI app with CORS
├── lambda_handler.py         # Mangum handler for AWS Lambda
├── streamlit_chat_ui.py      # Streamlit UI
├── requirements.txt          # Dependencies
├── log_conf.yaml            # Logging configuration
├── Dockerfile               # Python 3.13.5 container
└── bitbucket-pipelines.yml  # CI/CD for AWS EKS deployment
```

## Technology Stack

From `requirements.txt`:
- fastapi
- uvicorn
- langchain
- langchain-community
- openai
- pydantic
- tiktoken
- mangum
- requests
- pytz
- python-dotenv

## Environment Variables

From `core/tools.py`:
- `CUSTOMER_SCHEDULER_API_URL` - Base API URL
- `ENVIRONMENT` - dev, qa, staging, or prod
- `CONFIRM_SCHEDULE_FLAG` - int (0 or 1)
- `CANCEL_SCHEDULE_FLAG` - int (0 or 1)
- `WEATHER_API_KEY` - Optional (has default: "02ffdcc1ea97431aa4c111400251408")

## API Endpoints

From `api/routes.py`:

### GET /api/healthz
Returns: `{"status": "ok"}`

### POST /api/chat
Headers: `authorization`, `client_id`

Request Body (from `models/schemas.py`):
```python
class ChatRequest(BaseModel):
    session_id: int | str
    message: str
    customer_id: int | str
    client_name: str
```

Response:
```python
class ChatResponse(BaseModel):
    response: str
```

## LLM Configuration

From `core/llm.py`:
- Model: `gpt-4.1`
- Temperature: `0`
- Rate Limiter: `InMemoryRateLimiter`
  - `requests_per_second=0.8`
  - `check_every_n_seconds=0.1`
  - `max_bucket_size=5`
- `max_retries=3`
- `timeout=60`

## Memory

From `core/memory.py`:
```python
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
```

## Session Context

From `core/context.py`:
```python
session_context = {}  # In-memory dictionary
```

## Tools

From `core/langchain_agent.py`, 14 tools registered:

1. **ListProjects** - List all available projects
2. **SwitchProject** - Switch active project by text description
3. **ShowProjectDetails** - Return full details for one project
4. **GetWorkingDays** - Get working days for session
5. **GetAvailableDates** - Get available appointment dates
6. **GetSlotsForDate** - Get available time slots for a date
7. **UpdateDate** - Update selected appointment date
8. **ConfirmAppointment** - Confirm appointment (time in HH:MM:SS format)
9. **ShowSessionState** - View current session state
10. **CancelSchedule** - Cancel appointment for project ID
11. **LoadAvailableProjects** - Load all available project details
12. **GetCurrentWeather** - Get weather for a city
13. **AddProjectNote** - Add customer note to project

## Logging Configuration

From `main.py`:
```python
logging.getLogger("uvicorn.access").setLevel(logging.ERROR)
logging.getLogger("httpcore.http11").setLevel(logging.ERROR)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
```

From `log_conf.yaml`:
- Root level: DEBUG
- uvicorn.error: INFO
- uvicorn.access: DEBUG

## CORS Configuration

From `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Docker

From `Dockerfile`:
```dockerfile
FROM python:3.13.5
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-config=log_conf.yaml"]
```

## Deployment

From `bitbucket-pipelines.yml`:
- Deploys to AWS EKS (Kubernetes)
- Environments: dev, qa, staging, prod
- Uses AWS ECR for Docker images
- Branches: `release/dev`, `release/qa`, `release/staging`, `release/prod`

## Lambda Handler

From `lambda_handler.py`:
```python
from mangum import Mangum
from main import app

handler = Mangum(app)
```

## Streamlit UI

From `streamlit_chat_ui.py`:
- Available at configured `API_URL`
- Uses `uuid.uuid4()` for session IDs
- Sends POST requests to `/api/chat`
