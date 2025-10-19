# Tools Documentation

All tools are defined in `core/tools.py` and registered in `core/langchain_agent.py`.

## Tool Registration

From `core/langchain_agent.py`:
```python
tools = [
    StructuredTool.from_function(
        func=function,
        name="ToolName",
        description="...",
        args_schema=InputSchema
    ),
    ...
]
```

## Project Management Tools

### 1. ListProjects

**Name**: `ListProjects`
**Function**: `list_projects`
**Description**: "List all available projects by order_number, project_number, type, category and status so the user can choose one."

**Input Schema**:
```python
class ListProjectsInput(BaseModel):
    session_id: int | str
```

**Returns**: String with projects list including project_number, order_number, project_id, type, category, status, and project_url

---

### 2. SwitchProject

**Name**: `SwitchProject`
**Function**: `switch_project_by_text`
**Description**: "Switch the active project by giving the user's raw description (handles order_number, project_number, type, category, status, etc.)."

**Input Schema**:
```python
class ProjectSwitchByTextInput(BaseModel):
    session_id: int | str
    user_input: str = Field(..., description="The user's description to select the project")
```

**Implementation**: Uses LLM to match user description to projects, returns JSON with project_id

---

### 3. ShowProjectDetails

**Name**: `ShowProjectDetails`
**Function**: `show_project_details`
**Description**: "Return full details for one project. You can specify order_number, project_id, project_number, project_type, or category."

**Input Schema**:
```python
class ProjectDetailsInput(BaseModel):
    session_id: int | str
    project_id: int = Field(None, description="Exact project_id")
    project_number: str = Field(None, description="Exact project_number")
    order_number: str = Field(None, description="Exact order_number")
    project_type: str = Field(None, description="Fuzzy project type")
    category: str = Field(None, description="Fuzzy project category")
```

**Details Returned**: order_number, project_id, type, category, status, project_url, store, installation_addr, dates, technician, service_time

**Matching**: Exact match on id/number/order_number, fuzzy match on type/category using `difflib.get_close_matches` (cutoff=0.6)

---

### 4. LoadAvailableProjects

**Name**: `LoadAvailableProjects`
**Function**: `load_available_projects`
**Description**: "Load all the available project details for the customer."

**Input Schema**:
```python
class LoadAvailableProjectsInput(BaseModel):
    session_id: int | str
    customer_id: int | str
```

**API Call**: `GET {CUSTOMER_API_URL}/{customer_id}`
**Data Transform**: `extract_projects()` converts API response to simplified project list

---

## Scheduling Tools

### 5. GetWorkingDays

**Name**: `GetWorkingDays`
**Function**: `get_working_days`
**Description**: "Get the working days for a session."

**Input Schema**:
```python
class SessionInput(BaseModel):
    session_id: int | str
```

**API Call**: `GET {SCHEDULER_BASE_URL}/business-hours`
**Storage**: Stores in `session_context[session_id]["working_days"]`

---

### 6. GetAvailableDates

**Name**: `GetAvailableDates`
**Function**: `get_available_dates`
**Description**: "Get available appointment dates for the active project."

**Input Schema**:
```python
class SessionInput(BaseModel):
    session_id: int | str
```

**API Call**: `GET {SCHEDULER_BASE_URL}/project/{proj_id}/date/{today}/selected/{today}/get-rescheduler-slots`
**Storage**: Stores `available_dates` and `request_id` in session context

---

### 7. GetSlotsForDate

**Name**: `GetSlotsForDate`
**Function**: `get_slots_for_date`
**Description**: "Get available time slots for a given date."

**Input Schema**:
```python
class SlotsInput(BaseModel):
    date: str
    session_id: int | str
```

**API Call**: `GET {SCHEDULER_BASE_URL}/project/{proj_id}/date/{date}/selected/{date}/get-rescheduler-slots?request_id={req_id}`
**Storage**: Stores `date` and `slots` in session context

---

### 8. UpdateDate

**Name**: `UpdateDate`
**Function**: `update_date`
**Description**: "Update the selected appointment date in-session."

**Input Schema**:
```python
class UpdateDateInput(BaseModel):
    new_date: str
    session_id: int | str
```

**Action**: Updates `session_context[session_id]["date"]`

---

### 9. ConfirmAppointment

**Name**: `ConfirmAppointment`
**Function**: `confirm_schedule`
**Description**: "Confirm an appointment for a specific date and time. Time should always be in HH:MM:SS format as input to function."

**Input Schema**:
```python
class ConfirmInput(BaseModel):
    date: str
    time: str
    session_id: int | str
```

**API Call** (if `CONFIRM_SCHEDULE_FLAG == 1`):
```python
POST {SCHEDULER_BASE_URL}/project/{proj_id}/schedule
```

**Payload**:
```python
{
    "created_at": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%m-%d-%Y %H:%M:%S"),
    "date": date,
    "time": time,
    "request_id": session_context[session_id]["request_id"],
    "is_chatbot": "true"
}
```

---

### 10. CancelSchedule

**Name**: `CancelSchedule`
**Function**: `cancel_schedule`
**Description**: "Cancel the current appointment for a given project ID"

**Input Schema**:
```python
class CancelScheduleInput(BaseModel):
    session_id: int | str
```

**API Call** (if `CANCEL_SCHEDULE_FLAG == 1`):
```python
GET {SCHEDULER_BASE_URL}/project/{proj_id}/cancel-reschedule
```

---

## Utility Tools

### 11. GetCurrentWeather

**Name**: `GetCurrentWeather`
**Function**: `get_current_weather`
**Description**: "Get the current weather for a given city. Returns temperature, condition, humidity, and wind."

**Input Schema**:
```python
class WeatherToolInput(BaseModel):
    city: str = Field(..., description="City name to get the weather for.")
```

**API**: WeatherAPI.com
**Endpoint**: `https://api.weatherapi.com/v1/current.json?key={api_key}&q={city}`
**Default API Key**: "02ffdcc1ea97431aa4c111400251408"

---

### 12. AddProjectNote

**Name**: `AddProjectNote`
**Function**: `add_project_note`
**Description**: "Add a customer note to the currently selected project (or a given project_id). Use when user says they want to add a note during scheduling/rescheduling or to any project/job."

**Input Schema**:
```python
class AddNoteInput(BaseModel):
    session_id: int | str
    note_text: str = Field(..., description="Note text to add for the project.")
```

**API Call**:
```python
POST {CUSTOMER_NOTE_URL}/{proj_id}
```

**Payload**:
```python
{"note_text": note_text}
```

**Storage**: Also stores in `session_context[session_id]["notes"][proj_id]`

---

### 13. ShowSessionState

**Name**: `ShowSessionState`
**Function**: `show_session_state`
**Description**: "Debug: view the current session state."

**Input Schema**:
```python
class SessionStatusInput(BaseModel):
    session_id: int | str
```

**Returns**: `str(session_context.get(session_id, {}))`

---

## Session Context Structure

From `core/tools.py`:

```python
session_context[session_id] = {
    "session_id": str,
    "customer_id": int | str,
    "client_id": str,
    "client_name": str,
    "project_id": int,              # Currently selected
    "projects": list[dict],         # All available projects
    "working_days": list[str],
    "available_dates": list[str],
    "request_id": str,
    "date": str,
    "slots": list[str],
    "time": str,
    "notes": dict
}
```

## Project Structure

From `extract_projects()` in `core/tools.py`:

```python
{
    "project_number": i+1,
    "project_id": item.get("project_project_id"),
    "project_url": f'[View Project]({BASE_PROJECT_URL}/{item.get("project_project_id")})',
    "order_number": item.get("project_project_number"),
    "project_type": item.get("project_type_project_type"),
    "category": item.get("project_category_category"),
    "status": item.get("status_info_status"),
    "store": item.get("project_store_store_number"),
    "installation_addr": item.get("installation_address_full_address"),
    "address": {...},
    "dates": {...},
    "technician": {...},
    "service_time": {...}
}
```

## API URLs

From `set_parsed_json()` in `core/tools.py`:

```python
CUSTOMER_API_URL = f"{CUSTOMER_SCHEDULER_BASE_API_URL}/dashboard/get/{client_id}"
SCHEDULER_BASE_URL = f"{CUSTOMER_SCHEDULER_BASE_API_URL}/scheduler/client/{client_id}"
BASE_PROJECT_URL = f"https://{client_name}.cx-portal.{env_url}.projectsforce.com/details"
CUSTOMER_NOTE_URL = f"{CUSTOMER_SCHEDULER_BASE_API_URL}/project-notes/add/{client_id}"
```

Environment URL mapping:
- `dev` → `dev`
- `qa` → `qa`
- `staging` → `staging`
- `prod` → `apps`
- default → `dev`

## Authentication Headers

From `set_parsed_json()` in `core/tools.py`:

```python
AUTH_HEADER = {
    "authorization": authorization,
    "client_id": client_id,
    "Content-Type": "application/json",
    "charset": "utf-8",
}
```
