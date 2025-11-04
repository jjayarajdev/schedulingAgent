# ProjectForce CX Portal API - Project Selection & Details

**Analysis Date:** 2025-11-03
**Source:** HAR file analysis from projectsforce-validation.cx-portal.dev.projectsforce.com

---

## Overview

This document details the ProjectForce CX Portal APIs identified for:
1. **Listing all projects** for a customer
2. **Selecting and getting details** of a specific project
3. **Additional project-related data** (uploads, communications, etc.)

---

## Key API Endpoints

### 1. List All Projects (Dashboard)

**Purpose:** Get all projects for a specific customer

```
GET https://api-cx-portal.dev.projectsforce.com/dashboard/get/{CLIENT_ID}/{CUSTOMER_ID}
```

**Parameters:**
- `CLIENT_ID`: Client identifier (e.g., `09PF05VD`)
- `CUSTOMER_ID`: Customer identifier (e.g., `1646085`)

**Headers:**
```
Authorization: Bearer {TOKEN}
Content-Type: application/json
Client_Id: {CLIENT_ID}
```

**Response Structure:**
```json
{
  "message": "Dashboard data",
  "data": [
    {
      "project_project_id": 7751741,
      "project_client_id": "09PF05VD",
      "project_project_number": "21083_09PF05VD_1762166550719",
      "project_customer_id": 1646085,
      "project_status_id": 1,
      "project_project_category_id": 414,
      "project_project_type_id": 36,
      "project_date_scheduled_start": "2025-11-26T13:00:00.000Z",
      "project_date_scheduled_end": "2025-11-26T13:42:00.000Z",
      "project_category_category": "Decking",
      "project_type_project_type": "Call Back",
      "status_info_status": "New",
      "installation_address_address1": "401 Chicago Avenue",
      "installation_address_city": "Minneapolis",
      "installation_address_state": "MN",
      "installation_address_zipcode": "55415",
      "convertedProjectStartScheduledDate": "11-26-2025 08:00 AM",
      "convertedProjectEndScheduledDate": "11-26-2025 08:42 AM",
      ...
    }
  ]
}
```

**Key Fields:**
- `project_project_id`: Unique project identifier
- `project_project_number`: Human-readable project number
- `project_category_category`: Project category (e.g., "Decking", "Windows", "Kitchen Cabinets")
- `project_type_project_type`: Type of project (e.g., "Call Back", "Installation")
- `status_info_status`: Current status (e.g., "New", "Scheduled", "Completed")
- `project_date_scheduled_start/end`: Appointment dates
- `installation_address_*`: Installation location details

---

### 2. Get Specific Project Details (Find One Project)

**Purpose:** Get detailed information about a specific project

```
GET https://api-cx-portal.dev.projectsforce.com/dashboard/find-one-project/{CLIENT_ID}/{PROJECT_ID}
```

**Parameters:**
- `CLIENT_ID`: Client identifier (e.g., `09PF05VD`)
- `PROJECT_ID`: Project identifier (e.g., `7751741`)

**Headers:**
```
Authorization: Bearer {TOKEN}
Content-Type: application/json
Client_Id: {CLIENT_ID}
```

**Response Structure:**
```json
{
  "message": "Dashboard data",
  "data": {
    "project_id": 7751741,
    "client_id": "09PF05VD",
    "project_number": "21083_09PF05VD_1762166550719",
    "store_id": 21083,
    "customer_id": 1646085,
    "date_sold": "2025-11-03T10:41:46.000Z",
    "project_category_id": 414,
    "status_id": 1,
    "date_scheduled_start": "2025-11-26T13:00:00.000Z",
    "date_scheduled_end": "2025-11-26T13:42:00.000Z",
    "installation_address_id": 8430679,
    "project_category": {
      "project_category_id": 414,
      "category": "Decking"
    },
    "project_type": {
      "project_type_id": 36,
      "project_type": "Call Back"
    },
    "customer": {
      "customerId": 1646085,
      "firstName": "...",
      "lastName": "...",
      "email": "...",
      "phone": "..."
    },
    ...
  }
}
```

**Key Fields:**
- `project_id`: Unique project identifier
- `project_number`: Human-readable project/order number
- `project_category`: Nested object with category details
- `project_type`: Nested object with type details
- `customer`: Nested object with customer information
- All scheduling, status, and address information

---

### 3. Get Project Data (Additional Details)

**Purpose:** Get additional project data (appears to return null in some cases)

```
GET https://api-cx-portal.dev.projectsforce.com/dashboard/getdata/{CLIENT_ID}/{PROJECT_ID}
```

**Parameters:**
- `CLIENT_ID`: Client identifier (e.g., `09PF05VD`)
- `PROJECT_ID`: Project identifier (e.g., `7751741`)

**Headers:**
```
Authorization: Bearer {TOKEN}
Content-Type: application/json
Client_Id: {CLIENT_ID}
```

**Response:**
```json
{
  "message": "Dashboard data",
  "data": null
}
```

**Note:** May return additional project metadata when available.

---

### 4. Get Project Uploads

**Purpose:** Get files/documents uploaded for a project

```
GET https://api-cx-portal.dev.projectsforce.com/dashboard/getupload/{CLIENT_ID}/{PROJECT_ID}
```

**Parameters:**
- `CLIENT_ID`: Client identifier (e.g., `09PF05VD`)
- `PROJECT_ID`: Project identifier (e.g., `7751741`)

**Headers:**
```
Authorization: Bearer {TOKEN}
Content-Type: application/json
Client_Id: {CLIENT_ID}
```

**Response:**
```json
{
  "data": []
}
```

**Note:** Returns array of uploaded documents/images for the project.

---

### 5. Get Pending Documents

**Purpose:** Get pending documents for a customer

```
GET https://api-cx-portal.dev.projectsforce.com/document/get-pending-documents/{CLIENT_ID}/{CUSTOMER_ID}
```

**Parameters:**
- `CLIENT_ID`: Client identifier (e.g., `09PF05VD`)
- `CUSTOMER_ID`: Customer identifier (e.g., `1646085`)

**Headers:**
```
Authorization: Bearer {TOKEN}
Content-Type: application/json
Client_Id: {CLIENT_ID}
```

---

### 6. Get Project Communications

**Purpose:** Get communication sections/threads for a project

```
GET https://api-cx-portal.dev.projectsforce.com/communication/client/{CLIENT_ID}/project/{PROJECT_ID}/sections
```

**Query Parameters:**
- `limit`: Number of results (e.g., `10`)
- `page`: Page number (e.g., `1`)
- `sortBy`: Sort field (e.g., `section_id`)
- `sortOrder`: Sort direction (e.g., `DESC`)

**Example:**
```
GET https://api-cx-portal.dev.projectsforce.com/communication/client/09PF05VD/project/7751741/sections?limit=10&page=1&sortBy=section_id&sortOrder=DESC
```

**Headers:**
```
Authorization: Bearer {TOKEN}
Content-Type: application/json
Client_Id: {CLIENT_ID}
```

---

## Usage in Scheduling Agent

### Current Implementation

The scheduling Lambda functions currently use:
- **List Projects API:** `dashboard/get/{CLIENT_ID}/{CUSTOMER_ID}` (lines 215-250 in lambda/scheduling-actions/lambda_function.py)

### Recommended Enhancements

#### 1. Implement Project Switching
Users should be able to say:
- "Switch to my kitchen cabinets project"
- "Tell me about order number 21083_09PF05VD_1762166550719"

**Implementation:**
```python
def switch_project(client_id: str, customer_id: str, project_identifier: str):
    """
    Switch active project based on project number, category, or project ID

    Args:
        project_identifier: Project number, category name, or project ID
    """
    # 1. Get all projects
    projects = list_projects(client_id, customer_id)

    # 2. Find matching project by:
    #    - Project number (exact match)
    #    - Project category (fuzzy match)
    #    - Project ID (exact match)

    # 3. If found, call find-one-project API
    # 4. Return detailed project information
```

#### 2. Enhanced Project Details
When user asks for project details:
- "What are the details of my deck repair project?"
- "Tell me about order number ORD-2025-001"

**Implementation:**
```python
def get_project_details(client_id: str, project_id: str):
    """
    Get comprehensive project details
    """
    url = f"{API_BASE_URL}/dashboard/find-one-project/{client_id}/{project_id}"

    # Returns:
    # - Project info (number, category, type, status)
    # - Customer details
    # - Schedule dates
    # - Installation address
    # - Store information
```

#### 3. Project Context Management
Maintain active project context in session:
```python
session_attributes = {
    "activeProjectId": "7751741",
    "activeProjectNumber": "21083_09PF05VD_1762166550719",
    "activeProjectCategory": "Decking",
    "customerId": "1646085",
    "clientId": "09PF05VD"
}
```

---

## Test Query Alignment

The following test queries should use these APIs:

### Already Correct (✅)
1. "Show me all my projects" → `dashboard/get/{CLIENT_ID}/{CUSTOMER_ID}`
2. "What projects do I have scheduled?" → `dashboard/get/{CLIENT_ID}/{CUSTOMER_ID}` + filter by scheduled status

### Need API Integration (🔧)
3. "Tell me about order number ORD-2025-001" → Need to:
   - Parse project/order number from query
   - Call `dashboard/get` to find matching project
   - Call `dashboard/find-one-project/{CLIENT_ID}/{PROJECT_ID}` for details

4. "Switch to my flooring installation project" → Need to:
   - Parse category/type from query ("flooring installation")
   - Call `dashboard/get` to find matching project
   - Set active project in session
   - Call `dashboard/find-one-project` for confirmation

5. "What are the details of my kitchen cabinets project?" → Same as #3

---

## Implementation Priority

### High Priority
1. ✅ **List Projects API** - Already implemented
2. 🔧 **Find One Project API** - Add to scheduling-actions Lambda
3. 🔧 **Project Identification Logic** - Match user queries to project IDs

### Medium Priority
4. 🔧 **Session Context Management** - Track active project
5. 🔧 **Project Switching** - Allow users to change active project

### Low Priority
6. 📋 **Get Project Uploads API** - Show documents
7. 📋 **Get Project Communications API** - Show messages

---

## Example Implementation

```python
# lambda/scheduling-actions/lambda_function.py

def get_project_by_identifier(client_id: str, customer_id: str, identifier: str) -> dict:
    """
    Find project by number, category, or ID

    Args:
        identifier: Project number, category name, or project ID
    """
    # Get all projects
    projects_response = get_projects(client_id, customer_id)

    if not projects_response or 'data' not in projects_response:
        return None

    projects = projects_response['data']

    # Try exact match on project_number
    for project in projects:
        if project.get('project_project_number') == identifier:
            return get_project_details(client_id, project['project_project_id'])

    # Try fuzzy match on category
    identifier_lower = identifier.lower()
    for project in projects:
        category = project.get('project_category_category', '').lower()
        if identifier_lower in category or category in identifier_lower:
            return get_project_details(client_id, project['project_project_id'])

    # Try exact match on project_id
    try:
        project_id = int(identifier)
        return get_project_details(client_id, project_id)
    except ValueError:
        pass

    return None

def get_project_details(client_id: str, project_id: int) -> dict:
    """
    Get detailed project information
    """
    url = f"{API_BASE_URL}/dashboard/find-one-project/{client_id}/{project_id}"
    headers = get_auth_headers()

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()
```

---

## API Response Field Mapping

### List vs Find-One Project

| Field Purpose | List API (`dashboard/get`) | Find-One API (`dashboard/find-one-project`) |
|---------------|---------------------------|-------------------------------------------|
| Project ID | `project_project_id` | `project_id` |
| Client ID | `project_client_id` | `client_id` |
| Project Number | `project_project_number` | `project_number` |
| Category | `project_category_category` | `project_category.category` |
| Type | `project_type_project_type` | `project_type.project_type` |
| Status | `status_info_status` | Nested in status object |
| Start Date | `project_date_scheduled_start` | `date_scheduled_start` |
| End Date | `project_date_scheduled_end` | `date_scheduled_end` |
| Address | `installation_address_address1` | Nested in address object |

**Note:** List API uses prefixed field names (`project_*`, `status_info_*`), while Find-One API uses nested objects.

---

## Next Steps

1. Add `find-one-project` API integration to scheduling-actions Lambda
2. Implement project identifier matching logic
3. Add session attribute management for active project
4. Update test queries to verify project selection works
5. Add project switching capability to agent prompts

---

**Last Updated:** 2025-11-03
**Status:** 📋 Documentation Complete, Implementation Pending
