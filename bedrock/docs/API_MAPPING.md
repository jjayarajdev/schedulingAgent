# ProjectForce API Mapping for Test Queries

This document maps the test queries in test_ui.html to the ProjectForce APIs that should be called by the Bedrock agents.

## Test Queries and Required APIs

### Chitchat Category
| Test Query | Intent | Bedrock Agent | ProjectForce APIs Needed | Notes |
|------------|--------|---------------|-------------------------|-------|
| "Hey, how's it going?" | chitchat | Chitchat Agent | None | Conversational response only |
| "What do you think about the weather today?" | chitchat | Chitchat Agent | None | May use weather API (external) |
| "I'm feeling a bit stressed, just need to talk" | chitchat | Chitchat Agent | None | Emotional support response |
| "Tell me a joke!" | chitchat | Chitchat Agent | None | Conversational response |
| "Good morning! Ready for the weekend?" | chitchat | Chitchat Agent | None | Greeting response |
| "Thanks for all your help!" | chitchat | Chitchat Agent | None | Acknowledgment response |
| "How are you doing today?" | chitchat | Chitchat Agent | None | Greeting response |

---

### Scheduling Category
| Test Query | Intent | Bedrock Agent | ProjectForce APIs Needed | API Endpoint | Method |
|------------|--------|---------------|-------------------------|--------------|--------|
| "Show me all my projects" | scheduling | Scheduling Agent | **Get Customer Projects** | `/cx-scheduled/projects?customer_id={customer_id}` | GET |
| "What projects do I have scheduled?" | scheduling | Scheduling Agent | **Get Customer Projects** | `/cx-scheduled/projects?customer_id={customer_id}` | GET |
| "Tell me about order number ORD-2025-001" | scheduling | Scheduling Agent | **Get Customer Projects**<br>**Get Project Details** | `/cx-scheduled/projects?customer_id={customer_id}`<br>Filter by order_number | GET |
| "Switch to my flooring installation project" | scheduling | Scheduling Agent | **Get Customer Projects** | `/cx-scheduled/projects?customer_id={customer_id}`<br>Filter by category="Flooring" | GET |
| "What are the details of my kitchen cabinets project?" | scheduling | Scheduling Agent | **Get Customer Projects** | `/cx-scheduled/projects?customer_id={customer_id}`<br>Filter by category="Kitchen Cabinets" | GET |
| "When is my deck repair scheduled for?" | scheduling | Scheduling Agent | **Get Customer Projects** | `/cx-scheduled/projects?customer_id={customer_id}`<br>Filter by category="Deck Repair" | GET |
| "What dates are available for my windows installation?" | scheduling | Scheduling Agent | **Get Business Hours**<br>**Get Scheduler Info** | `/system/client-details`<br>`/admin-config/schedulerFilter/get-All-scheduler-info` | GET |
| "Show me time slots available for November 5th" | scheduling | Scheduling Agent | **Get Business Hours**<br>**Get Scheduler Info** | `/system/client-details`<br>`/admin-config/schedulerFilter/get-All-scheduler-info` | GET |
| "Schedule my bathroom remodel for November 8th at 2 PM" | scheduling | Scheduling Agent | **Update Project Schedule** | `/cx-scheduled/projects` (update endpoint) | POST/PUT |
| "Confirm appointment for project PRJ-78946 on November 10th at 9:00 AM" | scheduling | Scheduling Agent | **Confirm Schedule** | `/cx-scheduled/projects` (update endpoint) | POST/PUT |
| "Reschedule my flooring project to December 1st at 1 PM" | scheduling | Scheduling Agent | **Update Project Schedule** | `/cx-scheduled/projects` (update endpoint) | POST/PUT |
| "Cancel the appointment for project PRJ-78945" | scheduling | Scheduling Agent | **Cancel Schedule** | `/cx-scheduled/projects` (update endpoint) | POST/PUT |
| "What are your working days?" | scheduling | Scheduling Agent | **Get Client Details** | `/system/client-details` | GET |
| "What are your business hours?" | scheduling | Scheduling Agent | **Get Client Details** | `/system/client-details` | GET |

---

### Information Category
| Test Query | Intent | Bedrock Agent | ProjectForce APIs Needed | API Endpoint | Method |
|------------|--------|---------------|-------------------------|--------------|--------|
| "What's the weather in Tampa?" | information | Information Agent | None | External Weather API (not ProjectForce) | GET |
| "How's the weather in Clearwater Beach?" | information | Information Agent | None | External Weather API | GET |
| "What's the temperature in St Petersburg today?" | information | Information Agent | None | External Weather API | GET |
| "Is it going to rain in Tampa tomorrow?" | information | Information Agent | None | External Weather API | GET |
| "What's the weather forecast for this week?" | information | Information Agent | None | External Weather API | GET |
| "Check the weather for my installation address" | information | Information Agent | **Get Customer Projects** (for address)<br>Weather API | `/cx-scheduled/projects?customer_id={customer_id}` | GET |

---

### Notes Category
| Test Query | Intent | Bedrock Agent | ProjectForce APIs Needed | API Endpoint | Method |
|------------|--------|---------------|-------------------------|--------------|--------|
| "Add a note to project PRJ-78945: Customer prefers afternoon appointments" | notes | Notes Agent | **Add Project Note** | `/projects/notes` (or similar) | POST |
| "Save a note for my windows project: Gate code is 5678" | notes | Notes Agent | **Get Projects** (to find ID)<br>**Add Project Note** | `/cx-scheduled/projects`<br>`/projects/notes` | GET, POST |
| "Add a note: Need to confirm parking arrangements before installation" | notes | Notes Agent | **Add Note** | `/projects/notes` | POST |
| "Create a note for order ORD-2025-003: Customer has a dog, call ahead" | notes | Notes Agent | **Get Projects** (to find ID)<br>**Add Project Note** | `/cx-scheduled/projects`<br>`/projects/notes` | GET, POST |
| "Add reminder: Bring measuring tape for the bathroom remodel" | notes | Notes Agent | **Add Note** | `/projects/notes` | POST |
| "Note for kitchen project: Customer wants white cabinets only" | notes | Notes Agent | **Get Projects** (to find ID)<br>**Add Project Note** | `/cx-scheduled/projects`<br>`/projects/notes` | GET, POST |
| "Save note: Installation area needs to be cleared before arrival" | notes | Notes Agent | **Add Note** | `/projects/notes` | POST |

---

### Ambiguous Category
| Test Query | Intent | Bedrock Agent | ProjectForce APIs Needed | Notes |
|------------|--------|---------------|-------------------------|-------|
| "What's the status of my project?" | Ambiguous | Depends on context | **Get Customer Projects** | Needs clarification - which project? |
| "When is my appointment?" | Ambiguous | Depends on context | **Get Customer Projects** | Needs clarification - which appointment? |
| "I need to make a change" | Ambiguous | Depends on context | Various | Needs clarification - change to what? |
| "Can you help me with my order?" | Ambiguous | Depends on context | **Get Customer Projects** | Needs clarification - which order? |

---

## Available ProjectForce APIs (from HAR file)

### Core APIs Used by Agents

| API Endpoint | Method | Purpose | Agent Usage |
|--------------|--------|---------|-------------|
| `/cx-scheduled/projects` | GET | Get customer's scheduled projects | Scheduling, Information, Notes |
| `/system/client-details` | GET | Get client configuration and business hours | Scheduling |
| `/projects/master/project-category` | GET | Get list of project categories | Scheduling |
| `/projects/master/project-type` | GET | Get list of project types | Scheduling |
| `/system/status` | GET | Get project status options | Scheduling |
| `/customers` | GET | Get customers list | Scheduling |
| `/stores` | GET | Get store information | Scheduling |
| `/stores/all-stores` | GET | Get all stores | Scheduling |
| `/auth/user/profile` | GET | Get user profile information | All agents |
| `/admin-config/schedulerFilter/get-All-scheduler-info` | GET | Get scheduler configuration | Scheduling |

### Supporting APIs

| API Endpoint | Method | Purpose |
|--------------|--------|---------|
| `/stores/district` | GET | Get store districts |
| `/system/installer-work-type` | GET | Get installer work types |
| `/system/source-system` | GET | Get source systems |
| `/system/team` | GET | Get team information |
| `/system/user-types` | GET | Get user types |
| `/system/workroom/list` | GET | Get workroom list |
| `/tasks/get-notification-count/` | GET | Get notification count |
| `/dashboard/manage/list/my-dashboards` | GET | Get user dashboards |
| `/api/bulletin/active-bulletin/{type}/{date}` | GET | Get active bulletins |

---

## API Authentication

All ProjectForce API calls require:

```
Headers:
  Authorization: Bearer {pf_bearer_token}
  Content-Type: application/json
```

The token is available in Bedrock agent session attributes:
- `pf_bearer_token`: The ProjectForce access token
- `pf_api_base`: https://api.dev.projectsforce.com
- `client_id`: The ProjectForce client ID (e.g., 09PF05VD)
- `customer_id`: The customer/user ID

---

## Implementation Notes

1. **Session Attributes**: The backend passes these in `sessionAttributes`:
   ```json
   {
     "customer_id": "6f72bffa-c323-4058-a01c-9d495d696364",
     "client_id": "09PF05VD",
     "pf_bearer_token": "<token>",
     "pf_api_base": "https://api.dev.projectsforce.com"
   }
   ```

2. **Lambda Functions**: The action groups in Lambda need to:
   - Extract `pf_bearer_token` from session attributes
   - Use it to call ProjectForce APIs
   - Return real data instead of mock data

3. **Error Handling**:
   - If token is expired (401), agent should ask user to regenerate token
   - If project not found, agent should list available projects
   - If data is missing, agent should gracefully handle and ask for clarification

4. **Caching**: Consider caching frequently accessed data like:
   - Project categories
   - Project types
   - Business hours
   - Store information

---

## Next Steps

To make the agents use real ProjectForce data:

1. ✅ **Frontend**: Sends token to backend (DONE)
2. ✅ **Backend**: Passes token to Bedrock agents (DONE)
3. ⏳ **Lambda Functions**: Update to use `pf_bearer_token` and call real APIs
4. ⏳ **Testing**: Verify each test query returns real data

---

## Example Lambda Implementation

```python
import requests
import json

def lambda_handler(event, context):
    # Extract session attributes
    session_attributes = event.get('sessionAttributes', {})
    pf_token = session_attributes.get('pf_bearer_token')
    pf_api_base = session_attributes.get('pf_api_base')
    customer_id = session_attributes.get('customer_id')

    if not pf_token:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No ProjectForce token available'})
        }

    # Call ProjectForce API
    headers = {
        'Authorization': f'Bearer {pf_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(
        f'{pf_api_base}/cx-scheduled/projects?customer_id={customer_id}',
        headers=headers
    )

    if response.status_code == 200:
        projects = response.json()
        return {
            'statusCode': 200,
            'body': json.dumps(projects)
        }
    else:
        return {
            'statusCode': response.status_code,
            'body': json.dumps({'error': 'Failed to fetch projects'})
        }
```

---

Generated: 2025-11-03
