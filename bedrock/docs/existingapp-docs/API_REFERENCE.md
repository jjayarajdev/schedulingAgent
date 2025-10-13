# API Reference

Documentation extracted from source code.

## FastAPI Endpoints

### Health Check

From `api/routes.py`, lines 11-13:
```python
@router.get("/healthz")
async def health_check():
    return {"status": "ok"}
```

**Endpoint**: `GET /api/healthz`
**Response**: `{"status": "ok"}`

---

### Chat Endpoint

From `api/routes.py`, lines 15-38:
```python
@router.post("/chat", response_model=ChatResponse)
async def chat(request_data: ChatRequest, request: Request):
    # Access headers
    authorization = request.headers.get("authorization")
    client_id = request.headers.get("client_id")

    # Optionally override request_data values from headers
    parsed = request_data.dict()
    parsed["authorization"] = authorization
    parsed["client_id"] = client_id

    set_parsed_json(parsed)

    prompt_with_session = (
        f"My session ID is {parsed['session_id']}. "
        f"Customer ID is {parsed['customer_id']}. "
        f"Message: {parsed['message']}"
    )

    result = agent.invoke({"input": prompt_with_session})
    return ChatResponse(response=result["output"])
```

**Endpoint**: `POST /api/chat`
**Headers**:
- `authorization`: Auth token
- `client_id`: Client ID

**Request Body** (from `models/schemas.py`, lines 3-11):
```python
class ChatRequest(BaseModel):
    session_id: int | str
    message: str
    customer_id: int | str
    client_name: str
```

**Response** (from `models/schemas.py`, lines 12-13):
```python
class ChatResponse(BaseModel):
    response: str
```

---

## Backend Scheduler API

URLs constructed in `core/tools.py`, `set_parsed_json()` function, lines 38-66:

```python
CUSTOMER_API_URL = f"{CUSTOMER_SCHEDULER_BASE_API_URL}/dashboard/get/{client_id}"
SCHEDULER_BASE_URL = f"{CUSTOMER_SCHEDULER_BASE_API_URL}/scheduler/client/{client_id}"
BASE_PROJECT_URL = f"https://{client_name}.cx-portal.{env_url}.projectsforce.com/details"
CUSTOMER_NOTE_URL = f"{CUSTOMER_SCHEDULER_BASE_API_URL}/project-notes/add/{client_id}"
```

Environment mapping (lines 48-58):
- `dev` → `"dev"`
- `qa` → `"qa"`
- `staging` → `"staging"`
- `prod` → `"apps"`
- default → `"dev"`

### Get Customer Projects

From `load_available_projects()`, line 156:
```python
url = f"{CUSTOMER_API_URL}/{customer_id}"
res = requests.get(url, headers=AUTH_HEADER)
```

**Endpoint**: `GET {CUSTOMER_API_URL}/{customer_id}`
**Method**: GET
**Headers**: AUTH_HEADER

---

### Get Business Hours

From `get_working_days()`, line 351:
```python
res = requests.get(f"{SCHEDULER_BASE_URL}/business-hours", headers=AUTH_HEADER)
```

**Endpoint**: `GET {SCHEDULER_BASE_URL}/business-hours`
**Method**: GET
**Response**: `{"data": {"workHours": [...]}}`

---

### Get Available Dates

From `get_available_dates()`, line 361:
```python
url = f"{SCHEDULER_BASE_URL}/project/{proj_id}/date/{today}/selected/{today}/get-rescheduler-slots"
res = requests.get(url, headers=AUTH_HEADER)
```

**Endpoint**: `GET {SCHEDULER_BASE_URL}/project/{proj_id}/date/{date}/selected/{date}/get-rescheduler-slots`
**Method**: GET
**Response**: `{"data": {"dates": [...], "request_id": "..."}}`

---

### Get Slots for Date

From `get_slots_for_date()`, lines 387-392:
```python
url = (
    f"{SCHEDULER_BASE_URL}/project/{proj_id}/"
    f"date/{date}/selected/{date}/get-rescheduler-slots?request_id={req_id}"
)
res = requests.get(url, headers=AUTH_HEADER)
```

**Endpoint**: `GET {SCHEDULER_BASE_URL}/project/{proj_id}/date/{date}/selected/{date}/get-rescheduler-slots?request_id={req_id}`
**Method**: GET
**Response**: `{"data": {"slots": [...]}}`

---

### Confirm Schedule

From `confirm_schedule()`, lines 429-445:
```python
payload = {
    "created_at": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%m-%d-%Y %H:%M:%S"),
    "date": date,
    "time": time,
    "request_id": session_context[session_id]["request_id"],
    "is_chatbot": "true",
}
if CONFIRM_SCHEDULE_FLAG == 1:
    url = f"{SCHEDULER_BASE_URL}/project/{proj_id}/schedule"
    res = requests.post(
        url,
        headers={**AUTH_HEADER, "content-type": "application/json"},
        json=payload
    )
```

**Endpoint**: `POST {SCHEDULER_BASE_URL}/project/{proj_id}/schedule`
**Method**: POST
**Executes only if**: `CONFIRM_SCHEDULE_FLAG == 1`
**Payload**:
```json
{
  "created_at": "MM-DD-YYYY HH:MM:SS",
  "date": "YYYY-MM-DD",
  "time": "HH:MM:SS",
  "request_id": "string",
  "is_chatbot": "true"
}
```

---

### Cancel Schedule

From `cancel_schedule()`, lines 404-410:
```python
if CANCEL_SCHEDULE_FLAG == 1:
    url = f"{SCHEDULER_BASE_URL}/project/{proj_id}/cancel-reschedule"
    response = requests.get(url, headers=AUTH_HEADER)
```

**Endpoint**: `GET {SCHEDULER_BASE_URL}/project/{proj_id}/cancel-reschedule`
**Method**: GET
**Executes only if**: `CANCEL_SCHEDULE_FLAG == 1`

---

### Add Project Note

From `add_project_note()`, lines 511-515:
```python
url = f"{CUSTOMER_NOTE_URL}/{proj_id}"
payload = {"note_text": note_text}
res = requests.post(url, headers=AUTH_HEADER, json=payload, timeout=20)
```

**Endpoint**: `POST {CUSTOMER_NOTE_URL}/{proj_id}`
**Method**: POST
**Payload**: `{"note_text": "string"}`
**Timeout**: 20 seconds

---

## Weather API

From `get_current_weather()`, lines 467-474:
```python
api_key = os.getenv("WEATHER_API_KEY", "02ffdcc1ea97431aa4c111400251408")
url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={city}"
response = requests.get(url)
```

**Provider**: WeatherAPI.com
**Endpoint**: `https://api.weatherapi.com/v1/current.json`
**Parameters**: `key`, `q` (city)
**Default API Key**: "02ffdcc1ea97431aa4c111400251408"

---

## Authentication Headers

From `set_parsed_json()`, lines 68-73:
```python
AUTH_HEADER = {
    "authorization": authorization,
    "client_id": client_id,
    "Content-Type": "application/json",
    "charset": "utf-8",
}
```

---

## CORS Configuration

From `main.py`, lines 14-21:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Router Prefix

From `main.py`, line 24:
```python
app.include_router(router, prefix="/api")
```

All routes are prefixed with `/api`.
