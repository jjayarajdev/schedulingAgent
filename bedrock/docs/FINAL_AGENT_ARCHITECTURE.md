# Final Agent Architecture - 4 Agents

**Date:** 2025-11-03
**Decision:** Keep 4 specialized agents with clear separation of concerns

---

## Final Architecture Overview

### Agents (4 Total) ✅

| Agent Name | Agent ID | Purpose | Lambda Functions |
|------------|----------|---------|------------------|
| **SchedulingAgent** | TIGRBGSXCS | Core scheduling, projects, notes | pf-scheduling-actions |
| **pf-information** | JEK4SDJOOU | Weather information (external API) | pf-information-actions |
| **pf-chitchat** | GXVZEOBQ64 | Generic conversational responses | None |
| **Supervisor** | WF1S95L7X1 | Agent orchestration and routing | pf-query-router |

---

## Agent Responsibilities

### 1. SchedulingAgent (Primary Agent) 🎯

**Purpose:** Handle all scheduling, project management, and notes operations

**Capabilities:**

#### Scheduling Operations
- ✅ List projects for customer
- ✅ Get available appointment dates
- ✅ Get time slots for specific dates
- ✅ Confirm/schedule appointments
- ✅ Reschedule appointments
- ✅ Cancel appointments
- ✅ Get appointment status

#### Project Management (NEW)
- 🆕 Get project details by identifier (order number, project number, category)
- 🆕 Switch active project context
- 🆕 Get project by category or type
- ✅ List all projects

#### Supporting Information
- 🆕 Get business hours
- 🆕 Get working days

#### Notes Management
- 🆕 Add notes to projects
- 🆕 List notes for projects
- 🆕 Add reminders

**Lambda Function:** `pf-scheduling-actions`

**Total Functions:** 14 functions

---

### 2. pf-information (Weather Specialist) 🌤️

**Purpose:** Handle external weather API calls

**Rationale for Separation:**
- ✅ External API dependency (separate from ProjectForce API)
- ✅ Different error handling (external service may be down)
- ✅ Different caching strategy (weather data has different TTL)
- ✅ Independent scaling (weather queries may spike)
- ✅ Cleaner separation of concerns

**Capabilities:**
- ✅ Get weather by location
- ✅ Get weather forecast
- ✅ Get temperature
- ✅ Check rain forecast
- ✅ Get weather for installation address (uses project context from session)

**Lambda Function:** `pf-information-actions`

**Total Functions:** 1 function (weather-related)

---

### 3. pf-chitchat (Conversational Fallback) 💬

**Purpose:** Handle generic conversational queries that don't require action

**Capabilities:**
- ✅ Greetings ("Hello", "Hi", "Good morning")
- ✅ Thank you responses
- ✅ General questions about capabilities
- ✅ Small talk
- ✅ Unclear/ambiguous queries (friendly clarification)

**Lambda Function:** None (uses Bedrock's conversational abilities)

**Fallback Behavior:** When Supervisor can't route to a specific agent

---

### 4. Supervisor (Orchestrator) 🎛️

**Purpose:** Route queries to appropriate specialized agents

**Routing Logic:**
```python
def route_query(query: str, session: Dict) -> str:
    """
    Route query to appropriate agent based on intent
    """
    intent = classify_intent(query)

    # Scheduling and project queries → SchedulingAgent
    if intent in ['scheduling', 'project_info', 'notes', 'appointment_status']:
        return 'SchedulingAgent'

    # Weather queries → pf-information
    elif intent == 'weather':
        return 'pf-information'

    # Conversational queries → pf-chitchat
    elif intent in ['greeting', 'thankyou', 'chitchat', 'unclear']:
        return 'pf-chitchat'

    # Default fallback
    else:
        return 'pf-chitchat'
```

**Lambda Function:** `pf-query-router`

---

## Query Distribution (27 Test Queries)

### SchedulingAgent: 19 queries (70%)

**Scheduling (12 queries)**
1. "Show me all my projects"
2. "What projects do I have scheduled?"
3. "Tell me about order number ORD-2025-001"
4. "Switch to my flooring installation project"
5. "What are the details of my kitchen cabinets project?"
6. "When is my deck repair scheduled for?"
7. "What dates are available for my windows installation?"
8. "Show me time slots available for November 5th"
9. "Schedule my bathroom remodel for November 8th at 2 PM"
10. "Confirm appointment for project PRJ-78946 on November 10th at 9:00 AM"
11. "Reschedule my flooring project to December 1st at 1 PM"
12. "Cancel the appointment for project PRJ-78945"

**Notes (7 queries)**
13. "Add a note to project PRJ-78945: Customer prefers afternoon appointments"
14. "Save a note for my windows project: Gate code is 5678"
15. "Add a note: Need to confirm parking arrangements before installation"
16. "Create a note for order ORD-2025-003: Customer has a dog, call ahead"
17. "Add reminder: Bring measuring tape for the bathroom remodel"
18. "Note for kitchen project: Customer wants white cabinets only"
19. "Save note: Installation area needs to be cleared before arrival"

### pf-information: 8 queries (30%)

**Weather (6 queries)**
20. "What's the weather in Tampa?"
21. "How's the weather in Clearwater Beach?"
22. "What's the temperature in St Petersburg today?"
23. "Is it going to rain in Tampa tomorrow?"
24. "What's the weather forecast for this week?"
25. "Check the weather for my installation address"

**Business Hours (2 queries)** - MOVE TO SchedulingAgent
26. "What are your working days?"
27. "What are your business hours?"

---

## Consolidation Changes

### From Current → Final Architecture

#### SchedulingAgent (Expand) ⬆️

**Add from pf-information:**
- ✅ `handle_get_project_details` → Already covered by new functions
- ✅ `handle_get_appointment_status` → Move to SchedulingAgent
- ✅ `handle_get_working_hours` → Move to SchedulingAgent

**Add from pf-notes:**
- ✅ `handle_add_note` → Move to SchedulingAgent
- ✅ `handle_list_notes` → Move to SchedulingAgent

**New Functions:**
- 🆕 `handle_get_project_by_identifier` - Project identification
- 🆕 `handle_switch_project` - Project context switching

**Final Count:** 6 existing + 5 migrated + 2 new = **13 functions**

#### pf-information (Reduce) ⬇️

**Keep:**
- ✅ `handle_get_weather` - External weather API

**Remove (migrate to SchedulingAgent):**
- ❌ `handle_get_projects` - Duplicate of SchedulingAgent's list_projects
- ❌ `handle_get_project_details` - Covered by new project functions
- ❌ `handle_get_appointment_status` - Scheduling-related
- ❌ `handle_get_working_hours` - Business info belongs with scheduling

**Final Count:** **1 function (weather only)**

#### pf-notes (Deprecate) 🗑️

**Action:** Delete agent, migrate functions to SchedulingAgent

**Migrate:**
- ✅ `handle_add_note` → SchedulingAgent
- ✅ `handle_list_notes` → SchedulingAgent

**Rationale:** Notes are tightly coupled with projects, which are managed by SchedulingAgent

---

## Updated Test Query Mapping

### SchedulingAgent (21 queries - 78%) ✅

**Scheduling Operations (12)**
- Queries #1-12 from test_queries.json

**Notes Operations (7)**
- Queries #21-27 from test_queries.json

**Business Information (2)**
- Query #26: "What are your working days?"
- Query #27: "What are your business hours?"

### pf-information (6 queries - 22%) ✅

**Weather Only (6)**
- Queries #13-18 from test_queries.json (weather-related)

### pf-chitchat (Conversational - as needed) ✅

**Examples:**
- "Hello"
- "Thanks"
- "What can you do?"
- Unclear/ambiguous queries

---

## Implementation Plan

### Phase 1: Enhance SchedulingAgent (Week 1-2) 🔥

**Step 1.1: Add Project Identification Functions**

Create in `lambda/scheduling-actions/handler.py`:

```python
def handle_get_project_by_identifier(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Find project by order number, project number, category, or ID

    Examples:
    - "Tell me about order ORD-2025-001"
    - "Switch to my kitchen cabinets project"
    """
    client_id = params.get('clientId', config['DEFAULT_CLIENT_ID'])
    customer_id = params['customerId']
    identifier = params['identifier']

    # Get all projects
    projects_response = handle_list_projects(params, config, auth_headers)
    projects = projects_response.get('projects', [])

    # Try exact match on project_number
    for project in projects:
        if project.get('project_project_number') == identifier:
            return get_project_details_api(
                client_id,
                project['project_project_id'],
                auth_headers,
                config
            )

    # Try fuzzy match on category
    identifier_lower = identifier.lower()
    for project in projects:
        category = project.get('project_category_category', '').lower()
        if identifier_lower in category or category in identifier_lower:
            return get_project_details_api(
                client_id,
                project['project_project_id'],
                auth_headers,
                config
            )

    # Try exact match on project_id
    try:
        project_id = int(identifier)
        return get_project_details_api(client_id, project_id, auth_headers, config)
    except ValueError:
        pass

    raise ValueError(f"No project found matching: {identifier}")


def get_project_details_api(client_id: str, project_id: int, auth_headers: Dict, config: Dict) -> Dict:
    """
    Call ProjectForce find-one-project API
    """
    url = f"{config['API_BASE_URL']}/dashboard/find-one-project/{client_id}/{project_id}"

    response = requests.get(url, headers=auth_headers)
    response.raise_for_status()

    data = response.json()
    return {
        'project': data.get('data'),
        'message': data.get('message', 'Project details retrieved successfully')
    }


def handle_switch_project(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Switch active project in session context
    """
    project_result = handle_get_project_by_identifier(params, config, auth_headers)
    project = project_result['project']

    # Return with session attributes for context management
    return {
        'project': project,
        'message': f"Switched to project: {project.get('project_category', {}).get('category')}",
        'sessionAttributes': {
            'activeProjectId': str(project.get('project_id')),
            'activeProjectNumber': project.get('project_number'),
            'activeProjectCategory': project.get('project_category', {}).get('category'),
            'customerId': str(project.get('customer_id')),
            'clientId': project.get('client_id')
        }
    }
```

**Step 1.2: Migrate Business Hours Function**

Copy from `lambda/information-actions/handler.py` to `lambda/scheduling-actions/handler.py`:

```python
def handle_get_working_hours(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Get business working hours and days
    """
    # Return standard business hours (can be made configurable)
    return {
        'workingHours': {
            'monday': '8:00 AM - 6:00 PM',
            'tuesday': '8:00 AM - 6:00 PM',
            'wednesday': '8:00 AM - 6:00 PM',
            'thursday': '8:00 AM - 6:00 PM',
            'friday': '8:00 AM - 6:00 PM',
            'saturday': '9:00 AM - 3:00 PM',
            'sunday': 'Closed'
        },
        'workingDays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
        'timezone': 'US/Eastern'
    }
```

**Step 1.3: Migrate Notes Functions**

Copy from `lambda/notes-actions/handler.py` to `lambda/scheduling-actions/handler.py`:

```python
# Both handle_add_note and handle_list_notes
# Keep DynamoDB integration
```

**Step 1.4: Update Lambda Handler**

Add routing for new functions in `lambda_handler`:

```python
def lambda_handler(event, context):
    """Main Lambda handler with routing"""

    action = event.get('actionGroup', '')
    api_path = event.get('apiPath', '')

    action_handlers = {
        # Existing
        'listProjects': handle_list_projects,
        'getAvailableDates': handle_get_available_dates,
        'getTimeSlots': handle_get_time_slots,
        'confirmAppointment': handle_confirm_appointment,
        'rescheduleAppointment': handle_reschedule_appointment,
        'cancelAppointment': handle_cancel_appointment,

        # New - Project Management
        'getProjectByIdentifier': handle_get_project_by_identifier,
        'switchProject': handle_switch_project,
        'getAppointmentStatus': handle_get_appointment_status,  # Migrated

        # New - Business Info
        'getWorkingHours': handle_get_working_hours,  # Migrated

        # New - Notes
        'addNote': handle_add_note,  # Migrated
        'listNotes': handle_list_notes  # Migrated
    }

    # ... rest of handler logic
```

### Phase 2: Update Agent Schemas (Week 2) 📋

**Step 2.1: Update SchedulingAgent Action Group**

Update the action group JSON schema:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Scheduling Actions API",
    "version": "1.0.0"
  },
  "paths": {
    "/listProjects": { /* existing */ },
    "/getAvailableDates": { /* existing */ },
    "/getTimeSlots": { /* existing */ },
    "/confirmAppointment": { /* existing */ },
    "/rescheduleAppointment": { /* existing */ },
    "/cancelAppointment": { /* existing */ },

    "/getProjectByIdentifier": {
      "post": {
        "summary": "Find project by order number, project number, category, or ID",
        "operationId": "getProjectByIdentifier",
        "parameters": [
          {
            "name": "customerId",
            "in": "query",
            "required": true,
            "schema": { "type": "string" }
          },
          {
            "name": "identifier",
            "in": "query",
            "required": true,
            "schema": { "type": "string" },
            "description": "Order number, project number, category name, or project ID"
          }
        ]
      }
    },

    "/switchProject": {
      "post": {
        "summary": "Switch to a different project context",
        "operationId": "switchProject",
        "parameters": [
          {
            "name": "customerId",
            "in": "query",
            "required": true,
            "schema": { "type": "string" }
          },
          {
            "name": "identifier",
            "in": "query",
            "required": true,
            "schema": { "type": "string" }
          }
        ]
      }
    },

    "/getAppointmentStatus": { /* migrated from information */ },
    "/getWorkingHours": { /* migrated from information */ },
    "/addNote": { /* migrated from notes */ },
    "/listNotes": { /* migrated from notes */ }
  }
}
```

**Step 2.2: Update SchedulingAgent Instructions**

Update agent prompt to include new capabilities:

```markdown
You are the SchedulingAgent for ProjectForce, handling scheduling, project management, and notes.

## Core Capabilities

### 1. Scheduling Operations
- List customer projects
- Check available appointment dates
- View time slots for specific dates
- Schedule/confirm appointments
- Reschedule appointments
- Cancel appointments
- Check appointment status

### 2. Project Management
- Find projects by order number, project number, or category
- Switch between projects in conversation
- Provide detailed project information
- Maintain project context throughout conversation

### 3. Notes Management
- Add notes to projects
- List notes for projects
- Add reminders and special instructions

### 4. Business Information
- Provide working hours and days

## Key Instructions

### Project Identification
When user mentions:
- "order number" or "order ORD-XXX" → Use getProjectByIdentifier
- "project number" or "PRJ-XXX" → Use getProjectByIdentifier
- Project category like "kitchen cabinets", "flooring" → Use getProjectByIdentifier

### Project Context
- Track activeProjectId in session attributes
- When user says "my project", use active project from session
- When user switches projects, update session context

### Weather-Related Queries
- For weather questions, tell user: "Let me check the weather for you..."
- The Supervisor will route weather queries to the information specialist
- Do not attempt to answer weather questions directly

### Note: Weather queries are handled by a specialized agent
```

**Step 2.3: Update pf-information Agent**

Simplify to weather-only:

```markdown
You are the Weather Information Specialist for ProjectForce.

## Capabilities
- Provide current weather conditions
- Provide weather forecasts
- Check temperature
- Check rain forecast
- Get weather for installation addresses (use project context from session)

## Instructions
- Focus only on weather-related queries
- Use external weather API for accurate data
- Consider weather impact on installation scheduling
- When weather may affect scheduling, mention it proactively
```

### Phase 3: Update Supervisor Routing (Week 2) 🎛️

Update `lambda/query-router/handler.py`:

```python
def classify_intent(query: str) -> str:
    """
    Classify user query intent for routing
    """
    query_lower = query.lower()

    # Weather keywords → pf-information
    weather_keywords = ['weather', 'temperature', 'rain', 'forecast', 'sunny', 'cloudy']
    if any(keyword in query_lower for keyword in weather_keywords):
        return 'weather'

    # Scheduling keywords → SchedulingAgent
    scheduling_keywords = [
        'schedule', 'appointment', 'book', 'reschedule', 'cancel',
        'available', 'time slot', 'date', 'when',
        'project', 'order', 'note', 'reminder',
        'working hours', 'business hours', 'working days'
    ]
    if any(keyword in query_lower for keyword in scheduling_keywords):
        return 'scheduling'

    # Conversational → chitchat
    conversational_keywords = ['hello', 'hi', 'thanks', 'thank you', 'bye']
    if any(keyword in query_lower for keyword in conversational_keywords):
        return 'chitchat'

    # Default to scheduling (most queries are scheduling-related)
    return 'scheduling'


def route_to_agent(intent: str) -> str:
    """
    Map intent to agent ID
    """
    routing_map = {
        'scheduling': 'TIGRBGSXCS',  # SchedulingAgent
        'weather': 'JEK4SDJOOU',     # pf-information
        'chitchat': 'GXVZEOBQ64'     # pf-chitchat
    }

    return routing_map.get(intent, 'TIGRBGSXCS')  # Default to SchedulingAgent
```

### Phase 4: Deploy and Test (Week 3) ✅

**Step 4.1: Deploy Lambda Updates**

```bash
# Deploy updated scheduling-actions Lambda
cd lambda/scheduling-actions
zip -r function.zip .
aws lambda update-function-code \
  --function-name pf-scheduling-actions \
  --zip-file fileb://function.zip \
  --region us-east-1

# Update information-actions (simplified to weather only)
cd ../information-actions
# Remove migrated functions, keep only weather
zip -r function.zip .
aws lambda update-function-code \
  --function-name pf-information-actions \
  --zip-file fileb://function.zip \
  --region us-east-1
```

**Step 4.2: Update Agent Schemas**

```bash
# Update SchedulingAgent with new action group schema
aws bedrock-agent update-agent-action-group \
  --agent-id TIGRBGSXCS \
  --agent-version DRAFT \
  --action-group-name scheduling-actions \
  --api-schema file://schemas/scheduling-actions-enhanced.json \
  --region us-east-1

# Prepare agents
aws bedrock-agent prepare-agent --agent-id TIGRBGSXCS --region us-east-1
aws bedrock-agent prepare-agent --agent-id JEK4SDJOOU --region us-east-1
```

**Step 4.3: Test All 27 Queries**

```bash
# Use test_queries.json with testing UI or backend API
python3 test_all_queries.py
```

### Phase 5: Deprecate pf-notes Agent (Week 3) 🗑️

```bash
# Delete pf-notes agent
aws bedrock-agent delete-agent \
  --agent-id CF0IPHCFFY \
  --region us-east-1 \
  --skip-resource-in-use-check

# Delete pf-notes-actions Lambda (after verifying no usage)
aws lambda delete-function \
  --function-name pf-notes-actions \
  --region us-east-1
```

---

## Cost Impact

### Current (5 agents)
```
Average query: Supervisor → Target Agent
Cost per query: $0.0060
Monthly (100K queries): $600
```

### Final (4 agents)
```
Average query: Supervisor → Target Agent (same)
But 78% go to SchedulingAgent (consolidated)
Cost per query: $0.0045 (estimated)
Monthly (100K queries): $450
```

**Savings: $150/month (25% reduction)** ✅

### Additional Benefits
- ⚡ Slightly faster (fewer functions per agent)
- 🎯 Better accuracy (clear agent boundaries)
- 🔧 Easier maintenance (logical grouping)
- 📊 Cleaner architecture

---

## Final Agent Boundaries

### SchedulingAgent
- **Focus:** ProjectForce internal operations
- **API:** ProjectForce CX Portal API
- **Data:** Projects, appointments, schedules, notes
- **Ownership:** 78% of queries

### pf-information
- **Focus:** External weather data
- **API:** External weather API
- **Data:** Weather conditions, forecasts
- **Ownership:** 22% of queries

### pf-chitchat
- **Focus:** Generic conversation
- **API:** None (conversational AI)
- **Data:** None
- **Ownership:** Fallback only

### Supervisor
- **Focus:** Intelligent routing
- **API:** None (orchestration)
- **Data:** Query classification
- **Ownership:** 100% of queries (router)

---

## Success Criteria

### Functional
- ✅ All 27 test queries work correctly
- ✅ Project identification accuracy > 95%
- ✅ Session context maintained
- ✅ Weather queries routed correctly

### Performance
- ✅ Response time < 2s (95th percentile)
- ✅ Error rate < 0.1%
- ✅ Cold start < 5s

### Business
- ✅ Cost reduction ≥ 20%
- ✅ User satisfaction maintained
- ✅ Simpler maintenance

---

## Rollback Plan

If issues arise:

1. **Revert Lambda functions** (keep old versions for 2 weeks)
2. **Recreate pf-notes agent** (from backup)
3. **Revert action group schemas** (versioned in git)
4. **Update Supervisor routing** (to old agent IDs)

---

## Timeline

| Week | Phase | Tasks |
|------|-------|-------|
| Week 1 | Phase 1 | Add new functions to SchedulingAgent Lambda |
| Week 2 | Phase 2-3 | Update agent schemas, update Supervisor routing |
| Week 3 | Phase 4 | Deploy, test all 27 queries |
| Week 3 | Phase 5 | Deprecate pf-notes agent and Lambda |
| Week 4 | Monitor | Verify stability, performance, cost savings |

---

## Recommendation

**✅ APPROVED: 4-Agent Architecture**

**Rationale:**
1. ✅ Clear separation of concerns (internal vs external APIs)
2. ✅ Weather isolation makes sense (external dependency)
3. ✅ 25% cost reduction
4. ✅ Maintains modularity
5. ✅ Easier to test and maintain

**Next Action:** Start Phase 1 implementation

---

**Last Updated:** 2025-11-03
**Status:** ✅ Architecture Approved, Ready for Implementation
**Confidence Level:** ⭐⭐⭐⭐⭐ (Very High)
