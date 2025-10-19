# Business Model Analysis & Schema Design

**Date:** 2025-10-17
**Purpose:** Design schemas that intelligently handle both B2C and B2B scenarios

---

## 📊 Business Models

### Model 1: B2C (Direct Business)
```
Customer (CUST001)
  └── Projects (PROJECT001, PROJECT002, PROJECT003)
```

**Characteristics:**
- Customer = Client (same entity)
- Direct relationship between ProjectsForce and Customer
- No intermediate client layer
- `client_id` is implicit/derived from `customer_id`

### Model 2: B2B (Conglomerate/Multi-Client)
```
Customer (CUST001 - Large Corporation)
  ├── Client A (09PF05VD)
  │     └── Projects (PROJECT001, PROJECT002)
  ├── Client B (09PF05WE)
  │     └── Projects (PROJECT003, PROJECT004)
  └── Client C (09PF05XF)
        └── Projects (PROJECT005)
```

**Characteristics:**
- Customer has multiple Clients (subsidiaries, branches, etc.)
- Each Client has their own projects
- `client_id` is important for distinguishing which subsidiary

---

## 🎯 Design Principle

**The agent should NEVER ask for information it doesn't need or can infer.**

### When `client_id` is needed:
- ❌ **NOT needed:** When dealing with a specific project (project already belongs to a client)
- ❌ **NOT needed:** When dealing with a specific customer in B2C model
- ✅ **NEEDED:** When listing projects for a customer in B2B model (to filter by client)
- ✅ **NEEDED:** When getting business hours specific to a client location

### When `customer_id` is needed:
- ✅ **NEEDED:** When listing all projects for a customer
- ❌ **NOT needed:** When dealing with a specific project_id (can look up customer from project)
- ✅ **NEEDED:** For real API calls that require authentication/context

---

## 📋 Recommended Schema Changes

### Scheduling Actions

#### 1. `list-projects`
**Current:** Requires `customer_id`, optional `client_id`
**Recommended:**
```json
{
  "customer_id": {
    "type": "string",
    "description": "Customer ID. Required to list all projects for a customer."
  },
  "client_id": {
    "type": "string",
    "description": "Optional. Filter projects by specific client (for B2B scenarios with multiple clients)."
  }
}
"required": ["customer_id"]
```
**Rationale:** Need customer to start with. Client is optional filter for B2B.

#### 2. `get-available-dates`
**Current:** Requires `project_id`, optional `client_id`
**Recommended:**
```json
{
  "project_id": {
    "type": "string",
    "description": "Project ID to check availability for"
  }
}
"required": ["project_id"]
```
**Rationale:** Project ID is sufficient. Client is implicit in the project.

#### 3. `get-time-slots`
**Current:** Requires `project_id`, `date`, `request_id`, optional `client_id`
**Recommended:**
```json
{
  "project_id": {
    "type": "string",
    "description": "Project ID"
  },
  "date": {
    "type": "string",
    "description": "Date to check time slots for (YYYY-MM-DD)"
  },
  "request_id": {
    "type": "string",
    "description": "Request ID from get-available-dates call"
  }
}
"required": ["project_id", "date", "request_id"]
```
**Rationale:** All context is in project and request_id.

#### 4. `confirm-appointment`
**Current:** Requires `project_id`, `date`, `time`, `request_id`, optional `client_id`
**Recommended:**
```json
{
  "project_id": {
    "type": "string",
    "description": "Project ID"
  },
  "date": {
    "type": "string",
    "description": "Appointment date (YYYY-MM-DD)"
  },
  "time": {
    "type": "string",
    "description": "Appointment time (HH:MM format)"
  },
  "request_id": {
    "type": "string",
    "description": "Request ID from get-available-dates call"
  }
}
"required": ["project_id", "date", "time", "request_id"]
```
**Rationale:** Project has all client context.

#### 5. `reschedule-appointment`
**Current:** Requires `project_id`, `new_date`, `new_time`, `request_id`, optional `client_id`
**Recommended:**
```json
{
  "project_id": {
    "type": "string",
    "description": "Project ID"
  },
  "new_date": {
    "type": "string",
    "description": "New appointment date (YYYY-MM-DD)"
  },
  "new_time": {
    "type": "string",
    "description": "New appointment time (HH:MM format)"
  },
  "request_id": {
    "type": "string",
    "description": "Request ID from get-available-dates call"
  }
}
"required": ["project_id", "new_date", "new_time", "request_id"]
```
**Rationale:** Project has all client context.

#### 6. `cancel-appointment`
**Current:** Requires `project_id`, optional `client_id`
**Recommended:**
```json
{
  "project_id": {
    "type": "string",
    "description": "Project ID"
  }
}
"required": ["project_id"]
```
**Rationale:** Project ID is sufficient.

---

### Information Actions

#### 1. `get-project-details`
**Current:** Requires `project_id`, `customer_id`, optional `client_id`
**Recommended:**
```json
{
  "project_id": {
    "type": "string",
    "description": "Project ID"
  },
  "customer_id": {
    "type": "string",
    "description": "Customer ID. Required for real API authentication."
  }
}
"required": ["project_id", "customer_id"]
```
**Rationale:** Need both for real API. Client is implicit in project.

#### 2. `get-appointment-status`
**Current:** Requires `project_id`, optional `customer_id`, `client_id`
**Recommended:**
```json
{
  "project_id": {
    "type": "string",
    "description": "Project ID"
  }
}
"required": ["project_id"]
```
**Rationale:** ✅ Already updated. Project ID is sufficient in mock mode.

#### 3. `get-working-hours`
**Current:** Optional `client_id`
**Recommended:**
```json
{
  "client_id": {
    "type": "string",
    "description": "Optional. Get working hours for specific client location (B2B). Defaults to standard business hours."
  }
}
"required": []
```
**Rationale:** ✅ Already updated. Returns default hours if not specified.

#### 4. `get-weather`
**Current:** Requires `location`, optional `client_id`
**Recommended:**
```json
{
  "location": {
    "type": "string",
    "description": "Location (city, zipcode, or address)"
  }
}
"required": ["location"]
```
**Rationale:** ✅ Already updated. Weather is location-based only.

---

### Notes Actions

#### 1. `add-note`
**Current:** Requires `project_id`, `note_text`, optional `author`, `client_id`
**Recommended:**
```json
{
  "project_id": {
    "type": "string",
    "description": "Project ID"
  },
  "note_text": {
    "type": "string",
    "description": "The note content to add"
  },
  "author": {
    "type": "string",
    "description": "Optional. Author of the note (defaults to 'Agent')"
  }
}
"required": ["project_id", "note_text"]
```
**Rationale:** Project has client context. Author optional.

#### 2. `list-notes`
**Current:** Requires `project_id`, optional `client_id`
**Recommended:**
```json
{
  "project_id": {
    "type": "string",
    "description": "Project ID"
  }
}
"required": ["project_id"]
```
**Rationale:** Project ID is sufficient.

---

## 🔧 Implementation Plan

### Phase 1: Remove Unnecessary `client_id` ✅ DONE (Information)

**Status:**
- ✅ Information Actions: Updated (schema + Lambda)
- ⏳ Scheduling Actions: Needs update
- ⏳ Notes Actions: Needs update

### Phase 2: Update Remaining Schemas

1. **Scheduling Actions Schema**
   - Remove `client_id` from: get-available-dates, get-time-slots, confirm-appointment, reschedule-appointment, cancel-appointment
   - Keep `client_id` as optional in: list-projects (for B2B filtering)

2. **Notes Actions Schema**
   - Remove `client_id` from: add-note, list-notes

### Phase 3: Update Agent Instructions

Update agent instructions to understand the business models:

**Supervisor Agent:**
```
You coordinate scheduling for both B2C (direct customers) and B2B (customers with multiple client locations) scenarios.

- When a customer has multiple clients, they may specify which client location
- When dealing with a specific project, you don't need to ask for client_id (it's already part of the project)
- Only ask for customer_id when listing projects
- Only ask for project_id when working with appointments
```

**Scheduling Agent:**
```
You handle scheduling for both B2C and B2B scenarios.

Key principles:
- When customer mentions a project_id, don't ask for customer_id or client_id
- When customer says "my projects", ask for customer_id only
- client_id is only useful when filtering projects for large customers with multiple locations
- Never ask for both customer_id and client_id when you already have project_id
```

**Information Agent:**
```
You provide information for both B2C and B2B scenarios.

Key principles:
- When providing project details, only project_id is needed
- For working hours, provide default hours unless customer specifies a client location
- Don't ask for client_id when you already have project_id
```

**Notes Agent:**
```
You manage notes for both B2C and B2B scenarios.

Key principles:
- Notes are attached to projects
- Only project_id is needed to add or list notes
- Don't ask for client_id or customer_id when you have project_id
```

---

## 📝 Conversation Examples

### Example 1: B2C Direct Customer

**User:** Show me my projects for customer CUST001
**Agent:** [Calls list-projects with customer_id=CUST001]
**Result:** Shows 3 projects

**User:** Schedule project PROJECT001
**Agent:** [Calls get-available-dates with project_id=PROJECT001]
**Result:** Shows available dates (NO asking for customer_id or client_id)

### Example 2: B2B Multi-Client Customer

**User:** Show me all projects for customer BIGCORP001
**Agent:** [Calls list-projects with customer_id=BIGCORP001]
**Result:** Shows 50 projects across multiple client locations

**User:** Show me only projects for our Tampa location
**Agent:** [Calls list-projects with customer_id=BIGCORP001, client_id=09PF05VD]
**Result:** Shows 10 projects for Tampa client only

**User:** Schedule project PROJECT042
**Agent:** [Calls get-available-dates with project_id=PROJECT042]
**Result:** Shows available dates (NO asking for client_id - already knows from project)

---

## 🎯 Key Takeaways

1. **Project-centric operations** (schedule, reschedule, cancel, get-details, add-note) → Only need `project_id`

2. **Customer-centric operations** (list-projects) → Need `customer_id`, optionally `client_id` for B2B filtering

3. **Generic operations** (working-hours, weather) → Should work with defaults, optional parameters for specificity

4. **Never ask for redundant information** → If you have project_id, you can look up customer and client

---

**Next Steps:**
1. Update Scheduling Actions schema (remove client_id from 5 actions)
2. Update Notes Actions schema (remove client_id from 2 actions)
3. Update all 3 Lambda handlers (if needed)
4. Update agent instructions to understand business models
5. Test both B2C and B2B scenarios
