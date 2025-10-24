# B2B Multi-Client Integration Guide

**Version:** 1.0
**Last Updated:** 2025-10-17
**Status:** ✅ Complete - Ready for Portal Integration

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Business Model Support](#business-model-support)
3. [Portal Integration Requirements](#portal-integration-requirements)
4. [API Request Format](#api-request-format)
5. [Session Context Flow](#session-context-flow)
6. [Agent Behavior](#agent-behavior)
7. [Lambda Function Updates](#lambda-function-updates)
8. [Testing Scenarios](#testing-scenarios)
9. [Implementation Checklist](#implementation-checklist)

---

## Overview

The AWS Bedrock Multi-Agent Scheduling System now supports both **B2C (direct customers)** and **B2B (multi-client conglomerates)** business models with intelligent context-aware parameter handling.

### Key Principle

> **"Never ask for information you don't need or can infer from context"**

- **Project-centric operations** (scheduling, status, notes) only need `project_id`
- **Customer-centric operations** (listing projects) need `customer_id`
- **B2B filtering** uses optional `client_id` when customer wants specific location

---

## Business Model Support

### B2C (Business-to-Consumer)

**Scenario:** Direct customer relationship

```
Customer: CUST001 (John Smith)
  ├── PROJECT001 (Kitchen Remodel)
  ├── PROJECT002 (Bathroom Update)
  └── PROJECT003 (Deck Construction)
```

**Characteristics:**
- Customer = Client (single entity)
- No `client_id` needed in requests
- All projects belong to one customer
- Simpler parameter structure

### B2B (Business-to-Business)

**Scenario:** Multi-client conglomerate

```
Customer: CUST_BIGCORP (BigCorp Inc.)
  ├── Client: Tampa Office (09PF05VD) - 25 projects
  ├── Client: Miami Office (09PF05WE) - 18 projects
  ├── Client: Orlando Office (09PF05XF) - 32 projects
  └── Client: Jacksonville (09PF05YG) - 15 projects

Total: 90 projects across 4 locations
```

**Characteristics:**
- Customer has multiple client locations
- Each client has multiple projects
- Optional `client_id` for filtering by location
- User can view all locations or filter by one

---

## Portal Integration Requirements

### Step 1: Determine Customer Type

When user logs into ProjectsForce portal, determine if they're B2C or B2B:

```javascript
// Example logic in portal
async function getUserContext(customerId) {
  // Query your database
  const customer = await db.customers.findById(customerId);
  const clients = await db.clients.findByCustomer(customerId);

  if (clients.length > 1) {
    // B2B customer with multiple locations
    return {
      customerType: 'B2B',
      customer: customer,
      clients: clients,
      defaultClient: clients.find(c => c.isPrimary) || clients[0]
    };
  } else {
    // B2C customer (single entity)
    return {
      customerType: 'B2C',
      customer: customer,
      clients: null,
      defaultClient: null
    };
  }
}
```

### Step 2: Build Session Context

#### For B2C Customers

```javascript
const chatContext = {
  customer_id: "CUST001",
  client_id: null,                    // Not needed
  client_name: "John Smith",
  available_clients: null,            // Not needed
  customer_type: "B2C"
};
```

#### For B2B Customers (Approach 1: User selects location)

```html
<!-- Portal UI: Location selector -->
<select id="locationSelector" onchange="updateClientContext(this.value)">
  <option value="">All Locations (90 projects)</option>
  <option value="09PF05VD" selected>Tampa Office (25 projects)</option>
  <option value="09PF05WE">Miami Office (18 projects)</option>
  <option value="09PF05XF">Orlando Office (32 projects)</option>
  <option value="09PF05YG">Jacksonville (15 projects)</option>
</select>
```

```javascript
// User selects Tampa Office
const chatContext = {
  customer_id: "CUST_BIGCORP",
  client_id: "09PF05VD",                    // Tampa selected
  client_name: "Tampa Office",
  available_clients: [
    { client_id: "09PF05VD", client_name: "Tampa Office", is_primary: true },
    { client_id: "09PF05WE", client_name: "Miami Office", is_primary: false },
    { client_id: "09PF05XF", client_name: "Orlando Office", is_primary: false },
    { client_id: "09PF05YG", client_name: "Jacksonville", is_primary: false }
  ],
  customer_type: "B2B"
};
```

#### For B2B Customers (Approach 2: Natural language switching)

```javascript
// User has primary location as default, can switch via conversation
const chatContext = {
  customer_id: "CUST_BIGCORP",
  client_id: "09PF05VD",                    // Primary location
  client_name: "Tampa Office",
  available_clients: [
    { client_id: "09PF05VD", client_name: "Tampa Office", is_primary: true },
    { client_id: "09PF05WE", client_name: "Miami Office", is_primary: false },
    { client_id: "09PF05XF", client_name: "Orlando Office", is_primary: false },
    { client_id: "09PF05YG", client_name: "Jacksonville", is_primary: false }
  ],
  customer_type: "B2B"
};

// User can say: "Show me Miami projects"
// Agent intelligently switches to Miami client_id
```

---

## API Request Format

### Backend API Endpoint

```
POST /api/chat
```

### Request Schema (B2C)

```json
{
  "message": "Show me my projects",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "CUST001",
  "client_id": null,
  "client_name": "John Smith",
  "available_clients": null,
  "customer_type": "B2C"
}
```

### Request Schema (B2B)

```json
{
  "message": "Show me Tampa projects",
  "session_id": "550e8400-e29b-41d4-a716-446655440001",
  "customer_id": "CUST_BIGCORP",
  "client_id": "09PF05VD",
  "client_name": "Tampa Office",
  "available_clients": [
    {
      "client_id": "09PF05VD",
      "client_name": "Tampa Office",
      "is_primary": true
    },
    {
      "client_id": "09PF05WE",
      "client_name": "Miami Office",
      "is_primary": false
    },
    {
      "client_id": "09PF05XF",
      "client_name": "Orlando Office",
      "is_primary": false
    }
  ],
  "customer_type": "B2B"
}
```

---

## Session Context Flow

### How Context Flows Through the System

```
Portal (JavaScript)
  └─> Builds chat context (customer_id, client_id, available_clients)
      │
      ▼
Backend API (FastAPI)
  └─> Receives request, extracts context
      └─> Builds sessionAttributes for Bedrock
          │
          ▼
Bedrock Supervisor Agent
  └─> Receives sessionAttributes:
      - customer_id: "CUST_BIGCORP"
      - client_id: "09PF05VD"
      - customer_type: "B2B"
      - available_clients: JSON array
      - total_clients: "4"
      │
      └─> Routes to Specialist Agent (preserves context)
          │
          ▼
Specialist Agent (Scheduling/Information/Notes)
  └─> Has access to sessionAttributes
      └─> Decides which parameters needed for action
          └─> Invokes action with minimal parameters
              │
              ▼
Lambda Function
  └─> Receives parameters from action
      └─> Fallback to sessionAttributes if needed
          └─> Calls PF360 API
              └─> Returns results
```

### Session Attributes Structure

```json
{
  "sessionAttributes": {
    "customer_id": "CUST_BIGCORP",
    "client_id": "09PF05VD",
    "default_client_id": "09PF05VD",
    "customer_type": "B2B",
    "user_authenticated": "true",
    "total_clients": "4",
    "available_clients": "[{\"client_id\":\"09PF05VD\",\"client_name\":\"Tampa Office\",\"is_primary\":true}...]",
    "client_names": "Tampa Office, Miami Office, Orlando Office, Jacksonville"
  }
}
```

---

## Agent Behavior

### Supervisor Agent Instructions

```
You are a supervisor agent with access to customer context from authenticated sessions.

Session attributes available:
- customer_id: The authenticated customer's ID (B2C and B2B)
- client_id: Default client location (B2B only, optional)
- customer_type: "B2C" or "B2B"
- available_clients: JSON array of all client locations (B2B only)
- total_clients: Number of locations (B2B only)

Business Model Awareness:

B2C Customers:
- customer_type = "B2C"
- client_id is empty
- All operations use customer_id only

B2B Customers:
- customer_type = "B2B"
- client_id contains default/primary location
- User can filter by location or view all locations

Routing Principles:

1. When user says "show me my projects":
   - B2C: Use customer_id from sessionAttributes
   - B2B with client_id: Use both customer_id and client_id (filtered)
   - B2B without client_id: Use customer_id only (all locations)

2. When user says "show me Tampa projects":
   - Parse location name, map to client_id
   - Use customer_id + client_id for filtering

3. When user says "show me all projects":
   - Use customer_id only (no client_id filter)
   - Returns projects across all locations for B2B

4. When user says "schedule project PROJECT001":
   - Use project_id only
   - NO customer_id or client_id needed (inferred from project)

5. When user says "what are your business hours":
   - B2C: No parameters needed (default hours)
   - B2B: Can optionally use client_id for location-specific hours

Key Rules:
- Don't ask user for customer_id - you already have it in sessionAttributes
- For project-centric operations, only project_id needed
- For customer-centric operations (listing), use customer_id from session
- For B2B location filtering, use client_id when user specifies location
```

### Specialist Agent Instructions

#### Scheduling Agent

```
You are a scheduling specialist agent handling both B2C and B2B scenarios.

Session attributes available (from Supervisor):
- customer_id: Customer ID
- client_id: Optional client location (B2B)
- customer_type: "B2C" or "B2B"

Actions and Parameters:

1. list_projects:
   - Required: customer_id (from sessionAttributes)
   - Optional: client_id (for B2B location filtering)
   - Use case: "Show me my projects"

2. get_available_dates:
   - Required: project_id only
   - NO customer_id or client_id needed
   - Use case: "What dates are available for project PROJECT001?"

3. get_time_slots:
   - Required: project_id, date, request_id
   - NO customer_id or client_id needed
   - Use case: "Show me times for October 20th"

4. confirm_appointment:
   - Required: project_id, date, time, request_id
   - NO customer_id or client_id needed
   - Use case: "Book the 10 AM slot"

5. reschedule_appointment:
   - Required: project_id, new_date, new_time, request_id
   - NO customer_id or client_id needed

6. cancel_appointment:
   - Required: project_id only
   - NO customer_id or client_id needed

Key Principles:
- When user has project_id, don't ask for customer_id or client_id
- Project implies customer and client context
- Only ask for customer_id when listing projects
- client_id is optional for B2B filtering only
```

#### Information Agent

```
You are an information specialist agent handling both B2C and B2B scenarios.

Actions and Parameters:

1. get_project_details:
   - Required: project_id, customer_id
   - NO client_id needed

2. get_appointment_status:
   - Required: project_id only
   - NO customer_id or client_id needed

3. get_working_hours:
   - All parameters optional!
   - Optional: client_id (for B2B location-specific hours)
   - Default: Returns standard business hours

4. get_weather:
   - Required: location only
   - NO client_id needed

Key Principles:
- Most operations are project-centric (project_id sufficient)
- get_working_hours works without any parameters (sensible default)
- client_id only used when user asks for specific location hours
```

#### Notes Agent

```
You are a notes specialist agent handling both B2C and B2B scenarios.

Actions and Parameters:

1. add_note:
   - Required: project_id, note_text
   - Optional: author (defaults to 'Agent')
   - NO customer_id or client_id needed

2. list_notes:
   - Required: project_id only
   - NO customer_id or client_id needed

Key Principles:
- Notes are attached to projects
- Only project_id needed for all operations
- No customer or client context required
```

---

## Lambda Function Updates

### Parameter Extraction with Session Fallback

All Lambda functions have been updated to support session attribute fallback:

```python
def extract_parameters(event: Dict) -> Dict[str, Any]:
    """
    Extract parameters from Bedrock event with session fallback

    Priority:
    1. Explicit parameters from action invocation
    2. Session attributes (for customer_id, client_id)
    """

    # Get explicit parameters from action
    params = {}
    if 'requestBody' in event:
        content = event['requestBody'].get('content', {})
        app_json = content.get('application/json', {})

        # Check if properties array format (from action groups)
        if isinstance(app_json, dict) and 'properties' in app_json:
            params = {p['name']: p['value'] for p in app_json['properties']}
        # Check if JSON string format
        elif isinstance(app_json, str):
            params = json.loads(app_json)
        # Already a dict
        else:
            params = app_json

    # Fallback to session attributes if needed
    session_attrs = event.get('sessionAttributes', {})

    # Add customer_id from session if not in params
    if 'customer_id' not in params and 'customer_id' in session_attrs:
        params['customer_id'] = session_attrs['customer_id']
        logger.info(f"Using customer_id from session: {params['customer_id']}")

    # Add client_id from session if not in params (B2B only)
    if 'client_id' not in params and 'client_id' in session_attrs:
        client_id = session_attrs.get('client_id', '')
        if client_id:  # Only add if not empty
            params['client_id'] = client_id
            logger.info(f"Using client_id from session: {params['client_id']}")

    return params
```

### List Projects Handler (B2B Support)

```python
def handle_list_projects(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    List projects with B2B support

    Parameters:
    - customer_id: Required (from params or session)
    - client_id: Optional (for B2B location filtering)
    """

    customer_id = params.get('customer_id')
    client_id = params.get('client_id', '')  # Empty string if not provided

    if not customer_id:
        raise ValueError("customer_id is required")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching projects for customer {customer_id}, client {client_id or 'ALL'}")

        if client_id:
            # B2B: Filtered by location
            response = get_mock_projects_by_client(customer_id, client_id)
        else:
            # B2C or B2B: All projects
            response = get_mock_projects_all(customer_id)
    else:
        # Real API call
        url = f"{config['base_url']}/api/projects"
        params_dict = {"customer_id": customer_id}

        if client_id:
            params_dict["client_id"] = client_id

        res = requests.get(url, params=params_dict, headers=auth_headers, timeout=30)
        res.raise_for_status()
        response = res.json()

    # Format response
    projects = response.get("data", {}).get("projects", [])

    # Group by location for B2B if showing all
    if not client_id and len(projects) > 20:  # Likely B2B with multiple locations
        by_location = {}
        for project in projects:
            loc = project.get('client_name', 'Unknown')
            if loc not in by_location:
                by_location[loc] = []
            by_location[loc].append(project)

        return {
            "action": "list_projects",
            "customer_id": customer_id,
            "total_projects": len(projects),
            "locations": len(by_location),
            "projects_by_location": by_location,
            "message": f"Found {len(projects)} projects across {len(by_location)} locations"
        }
    else:
        # Single location or B2C
        return {
            "action": "list_projects",
            "customer_id": customer_id,
            "client_id": client_id,
            "total_projects": len(projects),
            "projects": projects,
            "mock_mode": USE_MOCK_API
        }
```

---

## Testing Scenarios

### Test 1: B2C Customer Flow

```
Portal: User logs in as CUST001 (B2C customer)

Request:
{
  "message": "Show me my projects",
  "customer_id": "CUST001",
  "client_id": null,
  "customer_type": "B2C"
}

Expected Flow:
1. Backend → Bedrock: sessionAttributes.customer_id = "CUST001"
2. Supervisor → Scheduling Agent: Recognizes customer context
3. Scheduling Agent → list_projects with customer_id from session
4. Lambda → PF360 API: GET /api/projects?customer_id=CUST001
5. Response: 3 projects (no location filtering)

User: "Schedule project PROJECT001"

Expected Flow:
1. Supervisor → Scheduling Agent
2. Scheduling Agent → get_available_dates with project_id=PROJECT001
3. NO customer_id or client_id needed
4. Lambda → PF360 API: GET /api/availability?project_id=PROJECT001
```

### Test 2: B2B Customer - All Locations

```
Portal: User logs in as CUST_BIGCORP (B2B customer with 4 locations)

Request:
{
  "message": "Show me all my projects",
  "customer_id": "CUST_BIGCORP",
  "client_id": null,  // View all locations
  "available_clients": [/* 4 locations */],
  "customer_type": "B2B"
}

Expected Flow:
1. Backend → Bedrock: sessionAttributes with B2B context
2. Supervisor → Scheduling Agent
3. Scheduling Agent → list_projects with customer_id only (no client_id filter)
4. Lambda → PF360 API: GET /api/projects?customer_id=CUST_BIGCORP
5. Response: 90 projects grouped by 4 locations
```

### Test 3: B2B Customer - Filtered by Location

```
Portal: User selects Tampa Office from dropdown

Request:
{
  "message": "Show me my projects",
  "customer_id": "CUST_BIGCORP",
  "client_id": "09PF05VD",  // Tampa selected
  "client_name": "Tampa Office",
  "available_clients": [/* 4 locations */],
  "customer_type": "B2B"
}

Expected Flow:
1. Backend → Bedrock: sessionAttributes.client_id = "09PF05VD"
2. Supervisor → Scheduling Agent
3. Scheduling Agent → list_projects with customer_id and client_id
4. Lambda → PF360 API: GET /api/projects?customer_id=CUST_BIGCORP&client_id=09PF05VD
5. Response: 25 Tampa projects only
```

### Test 4: B2B Customer - Natural Language Location Switch

```
Portal: User has Tampa as default, says "Show me Miami projects"

Request:
{
  "message": "Show me Miami projects",
  "customer_id": "CUST_BIGCORP",
  "client_id": "09PF05VD",  // Default Tampa
  "available_clients": [
    {"client_id": "09PF05VD", "client_name": "Tampa Office"},
    {"client_id": "09PF05WE", "client_name": "Miami Office"}
  ]
}

Expected Flow:
1. Supervisor understands "Miami" location reference
2. Maps "Miami" → client_id "09PF05WE" from available_clients
3. Supervisor → Scheduling Agent with client_id override
4. Lambda → PF360 API: GET /api/projects?customer_id=CUST_BIGCORP&client_id=09PF05WE
5. Response: 18 Miami projects
```

### Test 5: Working Hours - B2B Location-Specific

```
User: "What are Tampa office hours?"

Expected Flow:
1. Supervisor → Information Agent
2. Information Agent → get_working_hours with client_id="09PF05VD"
3. Lambda → PF360 API: GET /api/business-hours?client_id=09PF05VD
4. Response: Tampa-specific hours

User: "What are your business hours?" (general question)

Expected Flow:
1. Supervisor → Information Agent
2. Information Agent → get_working_hours with NO parameters
3. Lambda returns default business hours (no API call needed)
4. Response: Standard hours
```

---

## Implementation Checklist

### Backend Updates ✅ Complete

- [x] Updated `ChatRequest` schema with B2B fields
- [x] Added `ClientLocation` model
- [x] Updated `BedrockAgentClient.invoke()` with B2B parameters
- [x] Updated chat API to extract and pass B2B context
- [x] Session storage includes B2B context

### Lambda Updates ⏳ In Progress

- [x] Parameter extraction supports session fallback
- [ ] Deploy updated Lambda functions
  ```bash
  cd bedrock/scripts
  ./deploy_lambda_functions.sh
  ```

### Agent Instructions Updates ⏳ Pending

- [ ] Update Supervisor Agent instructions in AWS Console
- [ ] Update Scheduling Agent instructions
- [ ] Update Information Agent instructions
- [ ] Update Notes Agent instructions
- [ ] Test all agent instructions

### Portal Integration ⏳ Pending

- [ ] Implement customer type detection
- [ ] Add location selector UI for B2B customers
- [ ] Update chat API calls with B2B context
- [ ] Handle location switching in UI
- [ ] Test B2C flow
- [ ] Test B2B flow with single location
- [ ] Test B2B flow with multiple locations
- [ ] Test natural language location switching

### Testing ⏳ Pending

- [ ] Test B2C customer end-to-end
- [ ] Test B2B customer with all locations
- [ ] Test B2B customer with filtered location
- [ ] Test location switching via dropdown
- [ ] Test location switching via conversation
- [ ] Test working hours (default vs location-specific)
- [ ] Verify no redundant parameter requests

---

## Summary

The system is now fully designed to support both B2C and B2B business models with intelligent, context-aware parameter handling. The foundational work is complete in the backend API and Bedrock client.

**Next Steps:**
1. Deploy updated Lambda functions
2. Update agent instructions in AWS Console
3. Portal team implements frontend integration
4. End-to-end testing of all scenarios

**Key Benefits:**
- ✅ No redundant questions to users
- ✅ Context preserved throughout conversation
- ✅ Natural language location switching
- ✅ Flexible for both business models
- ✅ Project-centric operations don't need customer/client context

---

**Questions?** See related documentation:
- [BUSINESS_MODEL_ANALYSIS.md](./BUSINESS_MODEL_ANALYSIS.md)
- [SCHEMA_UPDATES_COMPLETE.md](./SCHEMA_UPDATES_COMPLETE.md)
- [AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md](./AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)
