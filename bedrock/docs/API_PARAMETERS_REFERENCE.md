# API Parameters Reference

Complete reference for all API actions in the ProjectForce Scheduling Agent system.

**Last Updated:** January 9, 2025

---

## 📋 Table of Contents

- [Scheduling Actions (7 actions)](#scheduling-actions)
- [Information Actions (1 action)](#information-actions)
- [Parameter Types](#parameter-types)
- [Session Attributes](#session-attributes)
- [Common Patterns](#common-patterns)

---

## Scheduling Actions

The **SchedulingAgent** handles 7 scheduling-related actions via the `pf-scheduling-actions` Lambda function.

### 1. `list_projects`

**Purpose:** Get all projects for a customer

**Parameters:**

| Parameter | Type | Required | Source | Description |
|-----------|------|----------|--------|-------------|
| `customer_id` | string | ✅ Yes | Session | Unique identifier for the customer |
| `client_id` | string | ❌ No | Session | Client identifier (defaults to "default") |

**Example Request:**
```json
{
  "customer_id": "1645869",
  "client_id": "09PF05VD"
}
```

**Example Response:**
```json
{
  "action": "list_projects",
  "customer_id": "1645869",
  "projectCount": 25,
  "projects": [
    {
      "id": 7751741,
      "projectNumber": "21083_09PF05VD_1762166550719",
      "status": "Scheduled",
      "category": "Decking",
      "projectType": "Call Back",
      "scheduledDate": "2025-11-11",
      "address": "401 Chicago Avenue Minneapolis MN 55415",
      "store": "1",
      "dateSold": "2025-11-03"
    }
  ],
  "mockMode": false
}
```

**API Endpoint:**
```
GET /dashboard/get/{client_id}/{customer_id}
```

---

### 2. `get_project_details`

**Purpose:** Get detailed information about a specific project

**Parameters:**

| Parameter | Type | Required | Source | Description |
|-----------|------|----------|--------|-------------|
| `project_id` | string/int | ✅ Yes | User input | Unique identifier for the project |
| `client_id` | string | ❌ No | Session | Client identifier (defaults to "default") |

**Example Request:**
```json
{
  "project_id": "7751741",
  "client_id": "09PF05VD"
}
```

**Example Response:**
```json
{
  "action": "get_project_details",
  "project": {
    "id": "7751741",
    "projectNumber": "21083_09PF05VD_1762166550719",
    "status": "Scheduled",
    "category": "Decking",
    "address": {
      "address1": "401 Chicago Avenue",
      "city": "Minneapolis",
      "state": "MN",
      "fullAddress": "401 Chicago Avenue Minneapolis MN 55415"
    },
    "store": {
      "storeName": "12",
      "storeNumber": "1"
    },
    "technician": {
      "technician_id": "7603",
      "name": "Christopher XXXX",
      "email": "754aecf3c9d04dbab@testuser.com",
      "phone": "1231922321"
    }
  },
  "summary": "Project #21083_09PF05VD_1762166550719 - Decking (Call Back)\nStatus: Scheduled...",
  "full_data": { /* complete API response */ }
}
```

**API Endpoint:**
```
GET /dashboard/getdata/{client_id}/{project_id}
```

---

### 3. `get_available_dates`

**Purpose:** Get available appointment dates for a project

**Parameters:**

| Parameter | Type | Required | Source | Description |
|-----------|------|----------|--------|-------------|
| `project_id` | string/int | ✅ Yes | User input | Unique identifier for the project |
| `customer_id` | string | ❌ No | Session | Customer ID (auto-provided) |
| `start_date` | string | ❌ No | User input | Start date for availability search (YYYY-MM-DD) |
| `end_date` | string | ❌ No | User input | End date for availability search (YYYY-MM-DD) |

**Example Request:**
```json
{
  "project_id": "7751741",
  "customer_id": "1645869",
  "start_date": "2025-11-15",
  "end_date": "2025-12-15"
}
```

**Example Response:**
```json
{
  "action": "get_available_dates",
  "project_id": "7751741",
  "availableDates": [
    {
      "date": "2025-11-15",
      "dayOfWeek": "Friday",
      "formattedDate": "Friday, November 15, 2025",
      "isAvailable": true
    },
    {
      "date": "2025-11-18",
      "dayOfWeek": "Monday",
      "formattedDate": "Monday, November 18, 2025",
      "isAvailable": true
    }
  ],
  "totalDates": 15,
  "dateRange": {
    "start": "2025-11-15",
    "end": "2025-12-15"
  }
}
```

**API Endpoint:**
```
POST /scheduler/get-available-dates
Body: {
  "clientId": "09PF05VD",
  "projectId": "7751741",
  "startDate": "2025-11-15",
  "endDate": "2025-12-15"
}
```

---

### 4. `get_time_slots`

**Purpose:** Get available time slots for a specific date

**Parameters:**

| Parameter | Type | Required | Source | Description |
|-----------|------|----------|--------|-------------|
| `project_id` | string/int | ✅ Yes | User input | Unique identifier for the project |
| `date` | string | ✅ Yes | User input | Date to check (YYYY-MM-DD format) |
| `customer_id` | string | ❌ No | Session | Customer ID (auto-provided) |

**Example Request:**
```json
{
  "project_id": "7751741",
  "date": "2025-11-15",
  "customer_id": "1645869"
}
```

**Example Response:**
```json
{
  "action": "get_time_slots",
  "project_id": "7751741",
  "date": "2025-11-15",
  "formattedDate": "Friday, November 15, 2025",
  "timeSlots": {
    "morning": [
      {
        "slotId": "slot_20251115_0800",
        "startTime": "08:00",
        "endTime": "12:00",
        "formatted": "8:00 AM - 12:00 PM",
        "duration": "4 hours",
        "isAvailable": true
      }
    ],
    "afternoon": [
      {
        "slotId": "slot_20251115_1200",
        "startTime": "12:00",
        "endTime": "16:00",
        "formatted": "12:00 PM - 4:00 PM",
        "duration": "4 hours",
        "isAvailable": true
      }
    ],
    "evening": []
  },
  "totalSlots": 4
}
```

**API Endpoint:**
```
POST /scheduler/get-time-slots
Body: {
  "clientId": "09PF05VD",
  "projectId": "7751741",
  "date": "2025-11-15"
}
```

---

### 5. `confirm_appointment`

**Purpose:** Book/confirm an appointment

**Parameters:**

| Parameter | Type | Required | Source | Description |
|-----------|------|----------|--------|-------------|
| `project_id` | string/int | ✅ Yes | User input | Unique identifier for the project |
| `date` | string | ✅ Yes | User input | Appointment date (YYYY-MM-DD) |
| `time_slot_id` | string | ✅ Yes | User input | Selected time slot ID |
| `start_time` | string | ✅ Yes | User input | Start time (HH:MM format) |
| `end_time` | string | ✅ Yes | User input | End time (HH:MM format) |
| `customer_id` | string | ❌ No | Session | Customer ID (auto-provided) |
| `notes` | string | ❌ No | User input | Optional appointment notes |

**Example Request:**
```json
{
  "project_id": "7751741",
  "date": "2025-11-15",
  "time_slot_id": "slot_20251115_0800",
  "start_time": "08:00",
  "end_time": "12:00",
  "customer_id": "1645869",
  "notes": "Please call when arriving"
}
```

**Example Response:**
```json
{
  "action": "confirm_appointment",
  "status": "success",
  "appointment": {
    "appointmentId": "APT_7751741_20251115",
    "projectId": "7751741",
    "date": "2025-11-15",
    "formattedDate": "Friday, November 15, 2025",
    "startTime": "08:00",
    "endTime": "12:00",
    "formattedTime": "8:00 AM - 12:00 PM"
  },
  "message": "Your appointment has been confirmed for Friday, November 15, 2025 from 8:00 AM to 12:00 PM"
}
```

**API Endpoint:**
```
POST /scheduler/book-appointment
Body: {
  "clientId": "09PF05VD",
  "projectId": "7751741",
  "customerId": "1645869",
  "scheduledDate": "2025-11-15",
  "startTime": "08:00",
  "endTime": "12:00",
  "notes": "Please call when arriving"
}
```

---

### 6. `reschedule_appointment`

**Purpose:** Reschedule an existing appointment to a new date/time

**Parameters:**

| Parameter | Type | Required | Source | Description |
|-----------|------|----------|--------|-------------|
| `appointment_id` | string | ✅ Yes | User input | Unique identifier for the appointment (or project_id) |
| `new_date` | string | ✅ Yes | User input | New appointment date (YYYY-MM-DD) |
| `new_time_slot_id` | string | ✅ Yes | User input | New time slot ID |
| `new_start_time` | string | ✅ Yes | User input | New start time (HH:MM) |
| `new_end_time` | string | ✅ Yes | User input | New end time (HH:MM) |
| `customer_id` | string | ❌ No | Session | Customer ID (auto-provided) |

**Example Request:**
```json
{
  "appointment_id": "7751741",
  "new_date": "2025-11-18",
  "new_time_slot_id": "slot_20251118_1200",
  "new_start_time": "12:00",
  "new_end_time": "16:00",
  "customer_id": "1645869"
}
```

**Example Response:**
```json
{
  "action": "reschedule_appointment",
  "status": "success",
  "appointment": {
    "appointmentId": "7751741",
    "projectId": "7751741",
    "newDate": "2025-11-18",
    "formattedDate": "Monday, November 18, 2025",
    "newStartTime": "12:00",
    "newEndTime": "16:00",
    "formattedTime": "12:00 PM - 4:00 PM"
  },
  "message": "Your appointment has been rescheduled to Monday, November 18, 2025 from 12:00 PM to 4:00 PM"
}
```

**API Endpoint:**
```
PUT /scheduler/reschedule-appointment
Body: {
  "clientId": "09PF05VD",
  "projectId": "7751741",
  "customerId": "1645869",
  "newScheduledDate": "2025-11-18",
  "newStartTime": "12:00",
  "newEndTime": "16:00"
}
```

---

### 7. `cancel_appointment`

**Purpose:** Cancel an existing appointment

**Status:** ⚠️ **Currently DISABLED** (returns error message)

**Parameters:**

| Parameter | Type | Required | Source | Description |
|-----------|------|----------|--------|-------------|
| `appointment_id` | string | ✅ Yes | User input | Unique identifier for the appointment (or project_id) |
| `customer_id` | string | ❌ No | Session | Customer ID (auto-provided) |
| `cancellation_reason` | string | ❌ No | User input | Optional reason for cancellation |

**Example Request:**
```json
{
  "appointment_id": "7751741",
  "customer_id": "1645869",
  "cancellation_reason": "Need to reschedule due to conflict"
}
```

**Current Response:**
```json
{
  "action": "cancel_appointment",
  "status": "disabled",
  "message": "Cancel appointment feature is temporarily disabled. Please contact customer service to cancel your appointment."
}
```

**Note:** The cancel implementation is commented out in the handler (lines 969-1022). When enabled, it will call:

```
DELETE /scheduler/cancel-appointment
Body: {
  "clientId": "09PF05VD",
  "projectId": "7751741",
  "customerId": "1645869",
  "reason": "Need to reschedule due to conflict"
}
```

---

## Information Actions

The **pf-information** agent handles 1 action via the `pf-information-actions` Lambda function.

### 1. `get_weather`

**Purpose:** Get weather forecast for a location

**Parameters:**

| Parameter | Type | Required | Source | Description |
|-----------|------|----------|--------|-------------|
| `location` | string | ✅ Yes | User input | City name, zip code, or "City, State" format |

**Example Request:**
```json
{
  "location": "Tampa, FL"
}
```

**Example Response:**
```json
{
  "action": "get_weather",
  "location": "Tampa, FL",
  "weather": {
    "location": {
      "area": "Tampa",
      "region": "Florida",
      "country": "United States of America"
    },
    "current": {
      "temp_f": "75",
      "temp_c": "24",
      "condition": "Partly cloudy",
      "humidity": "65",
      "wind_mph": "10",
      "wind_dir": "NE",
      "feels_like_f": "77",
      "uv_index": "5"
    },
    "forecast": [
      {
        "date": "2025-11-10",
        "max_temp_f": "78",
        "min_temp_f": "68",
        "avg_temp_f": "73",
        "uv_index": "6",
        "sun_hours": "8.5"
      },
      {
        "date": "2025-11-11",
        "max_temp_f": "77",
        "min_temp_f": "69",
        "avg_temp_f": "74",
        "uv_index": "5",
        "sun_hours": "7.8"
      },
      {
        "date": "2025-11-12",
        "max_temp_f": "76",
        "min_temp_f": "70",
        "avg_temp_f": "73",
        "uv_index": "6",
        "sun_hours": "8.2"
      }
    ]
  },
  "mock_mode": false
}
```

**API Endpoint:**
```
GET https://wttr.in/{location}?format=j1
```

**Note:** This is an external API (wttr.in) and does not require ProjectForce authentication.

---

## Parameter Types

### String Formats

| Format | Pattern | Example | Description |
|--------|---------|---------|-------------|
| `date` | YYYY-MM-DD | "2025-11-15" | ISO 8601 date format |
| `time` | HH:MM | "14:30" | 24-hour time format |
| `datetime` | YYYY-MM-DDTHH:MM:SS | "2025-11-15T14:30:00" | ISO 8601 datetime |

### Common Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text value | "Tampa, FL" |
| `integer` | Whole number | 7751741 |
| `boolean` | True/false | true |
| `array` | List of values | ["slot1", "slot2"] |
| `object` | Key-value pairs | {"id": "123", "name": "Project"} |

---

## Session Attributes

These parameters are automatically provided from the user's session:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `customer_id` | string | Authenticated customer's ID | "1645869" |
| `client_id` | string | Client organization ID | "09PF05VD" |
| `pf_bearer_token` | string | ProjectForce API auth token | "eyJhbGc..." |
| `pf_api_base` | string | API base URL | "https://api-cx-portal.dev.projectsforce.com" |

### How Session Attributes Work

Session attributes are passed in the Bedrock Agent event:

```json
{
  "sessionAttributes": {
    "customer_id": "1645869",
    "client_id": "09PF05VD",
    "pf_bearer_token": "eyJhbGc...",
    "pf_api_base": "https://api-cx-portal.dev.projectsforce.com"
  }
}
```

The handler automatically resolves references like:
- `$customer_id` → "1645869"
- `session.customer_id` → "1645869"
- `{{session.customer_id}}` → "1645869"

---

## Common Patterns

### 1. Project Selection Flow

```
User: "Show me my projects"
→ list_projects(customer_id)
→ Returns 25 projects

User: "Tell me about project 7751741"
→ get_project_details(project_id: 7751741)
→ Returns detailed project info
```

### 2. Appointment Booking Flow

```
User: "I want to schedule project 7751741"
→ get_available_dates(project_id: 7751741)
→ Returns available dates

User: "What times are available on November 15?"
→ get_time_slots(project_id: 7751741, date: "2025-11-15")
→ Returns available time slots

User: "Book the 8 AM slot"
→ confirm_appointment(
    project_id: 7751741,
    date: "2025-11-15",
    time_slot_id: "slot_20251115_0800",
    start_time: "08:00",
    end_time: "12:00"
  )
→ Appointment confirmed
```

### 3. Rescheduling Flow

```
User: "I need to reschedule my appointment"
→ list_projects(customer_id)
→ Returns projects with scheduled appointments

User: "Reschedule project 7751741 to November 18"
→ get_time_slots(project_id: 7751741, date: "2025-11-18")
→ Returns available time slots

User: "Book the 12 PM slot"
→ reschedule_appointment(
    appointment_id: 7751741,
    new_date: "2025-11-18",
    new_time_slot_id: "slot_20251118_1200",
    new_start_time: "12:00",
    new_end_time: "16:00"
  )
→ Appointment rescheduled
```

### 4. Weather Check Flow

```
User: "What's the weather in Tampa?"
→ get_weather(location: "Tampa")
→ Returns current conditions + 3-day forecast

User: "Will it rain on my installation day?"
→ First get project details for location
→ Then get_weather(location: project.address.city)
→ Returns weather forecast for that location
```

---

## Error Handling

### Common Error Responses

**Missing Required Parameter:**
```json
{
  "error": "Missing required parameter: project_id",
  "action": "get_project_details"
}
```

**Invalid Parameter Format:**
```json
{
  "error": "Invalid date format. Expected YYYY-MM-DD, got '11/15/2025'",
  "action": "get_available_dates"
}
```

**API Request Failed:**
```json
{
  "error": "API request failed: 401 Unauthorized",
  "action": "list_projects"
}
```

**Action Not Found:**
```json
{
  "error": "Unknown action: invalid_action",
  "action": "invalid_action"
}
```

---

## Mock vs Real API Mode

### Mock Mode (USE_MOCK_API=true)

Returns static mock data for testing:
- No external API calls made
- Predictable responses
- Faster execution
- Good for development/testing

### Real Mode (USE_MOCK_API=false)

Calls actual ProjectForce APIs:
- Requires valid authentication
- Returns live data
- Subject to API rate limits
- Production behavior

**Set via environment variable:**
```bash
export USE_MOCK_API=false  # Real API
export USE_MOCK_API=true   # Mock API
```

---

## Rate Limits & Timeouts

| Setting | Value | Description |
|---------|-------|-------------|
| Request timeout | 30 seconds | Max time for API call |
| Lambda timeout | 30 seconds | Max Lambda execution time |
| Lambda memory | 1769 MB | Allocated memory |

---

## Authentication

### ProjectForce API

**Authentication Method:** Bearer Token

**Headers:**
```json
{
  "Authorization": "Bearer <token>",
  "Accept": "application/json, text/plain, */*",
  "Content-Type": "application/json",
  "client_id": "09PF05VD"
}
```

**Token Source:**
1. Session attributes (`pf_bearer_token`)
2. AWS Secrets Manager (`projectforce-api-token`)
3. Environment variable (`BEARER_TOKEN`) - deprecated

### Weather API (wttr.in)

**Authentication:** None required (public API)

---

## Related Documentation

- [FINAL_AGENT_ARCHITECTURE.md](FINAL_AGENT_ARCHITECTURE.md) - Overall architecture
- [INFORMATION_AGENT_CONSOLIDATION.md](INFORMATION_AGENT_CONSOLIDATION.md) - Recent changes
- [Scheduling Handler README](../lambda/scheduling-actions/README.md) - Implementation details
- [Information Handler README](../lambda/information-actions/README.md) - Weather implementation

---

**Last Updated:** January 9, 2025
**Version:** 2.0.0 (Post-consolidation)
