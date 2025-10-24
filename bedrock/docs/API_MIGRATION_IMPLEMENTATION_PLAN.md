# API Migration Implementation Plan

**Date:** October 19, 2025
**Status:** Ready for Implementation
**Approach:** Phased migration with mock-to-real transition
**Reference:** `API_MIGRATION_PLAN.md`

---

## 📋 Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Implementation Strategy](#implementation-strategy)
3. [Detailed Task Breakdown](#detailed-task-breakdown)
4. [File Structure](#file-structure)
5. [Dependencies & Prerequisites](#dependencies--prerequisites)
6. [Testing Requirements](#testing-requirements)
7. [Rollout Plan](#rollout-plan)

---

## Current State Analysis

### Existing Infrastructure ✅

**Lambda Functions (3):**
```
lambda/scheduling-actions/
├── handler.py          # ✅ Already has mock mode support
├── config.py           # ✅ USE_MOCK_API flag exists
├── mock_data.py        # ✅ Mock responses already defined
└── requirements.txt

lambda/information-actions/
├── handler.py
├── config.py
├── mock_data.py
└── requirements.txt

lambda/notes-actions/
├── handler.py
├── config.py
├── mock_data.py (needs creation)
└── requirements.txt
```

**Configuration (Already exists):**
```python
# config.py - Already implemented ✅
USE_MOCK_API = os.getenv("USE_MOCK_API", "true").lower() == "true"
ENABLE_REAL_CONFIRM = os.getenv("ENABLE_REAL_CONFIRM", "false")
ENABLE_REAL_CANCEL = os.getenv("ENABLE_REAL_CANCEL", "false")
```

**Frontend:**
```
frontend/backend/app.py  # ✅ Flask backend ready
frontend/frontend/       # ✅ React UI ready
```

**Tests:**
```
tests/test_production.py  # ✅ Exists
tests/LoadTest/           # ✅ Load testing setup exists
```

### What's Missing / Needs Update

**Infrastructure:**
- [ ] DynamoDB table for session state
- [ ] Lambda IAM permissions for DynamoDB
- [ ] Shared Lambda layer for common code
- [ ] Terraform configs for infrastructure

**Lambda Code:**
- [ ] Real API integration code (currently mock only)
- [ ] Session management (DynamoDB read/write)
- [ ] Error handling and retries
- [ ] Request ID tracking for scheduling flow

**Frontend:**
- [ ] Authentication flow
- [ ] Session creation in Flask backend
- [ ] DynamoDB session storage

**Testing:**
- [ ] Unit tests for real API code
- [ ] Integration tests for multi-step flows
- [ ] Error scenario tests

---

## Implementation Strategy

### Three-Layer Architecture

**Layer 1: Mock Data (Current - Already Exists) ✅**
```python
# mock_data.py
def get_mock_projects(customer_id):
    return {"data": [...]}
```

**Layer 2: API Client (To Be Created)**
```python
# api_client.py - NEW
class PF360APIClient:
    def get_projects(self, customer_id):
        if USE_MOCK_API:
            return get_mock_projects(customer_id)
        else:
            return self._call_real_api(...)
```

**Layer 3: Handler (Update Existing)**
```python
# handler.py - UPDATE
def list_projects(event):
    api_client = PF360APIClient(session_data)
    return api_client.get_projects(customer_id)
```

### Transition Path

```
Phase 1: USE_MOCK_API=true (Current state - WORKS)
    ↓
Phase 2: Add real API code (USE_MOCK_API=true still)
    ↓
Phase 3: Test real API (USE_MOCK_API=false in dev only)
    ↓
Phase 4: Gradual rollout (USE_MOCK_API=false in prod)
```

**Key Principle:** At any point, setting `USE_MOCK_API=true` returns to working state

---

## Detailed Task Breakdown

### Phase 1: Infrastructure Setup (2-3 days)

#### Task 1.1: Create DynamoDB Table
**Priority:** HIGH
**Dependencies:** None
**Estimated Time:** 2 hours

**Files to Create:**
- `infrastructure/terraform/dynamodb.tf` (NEW)
- `scripts/create_dynamodb_table.sh` (NEW - for manual setup)

**DynamoDB Schema:**
```hcl
# dynamodb.tf
resource "aws_dynamodb_table" "bedrock_sessions" {
  name           = "bedrock-sessions-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Environment = var.environment
    Project     = "bedrock-agents"
  }
}
```

**Manual Creation Script:**
```bash
# scripts/create_dynamodb_table.sh
aws dynamodb create-table \
    --table-name bedrock-sessions-dev \
    --attribute-definitions AttributeName=session_id,AttributeType=S \
    --key-schema AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

**Test Plan:**
- Create table in dev
- Write test item
- Read test item
- Verify TTL (set 1-minute TTL, confirm auto-deletion)

**Acceptance Criteria:**
- [ ] Table created in dev environment
- [ ] Can write and read items
- [ ] TTL auto-deletion working
- [ ] Documented in README

---

#### Task 1.2: Update Lambda IAM Permissions
**Priority:** HIGH
**Dependencies:** Task 1.1 (DynamoDB table)
**Estimated Time:** 1 hour

**Files to Modify:**
- `infrastructure/terraform/iam.tf` (MODIFY)

**IAM Policy to Add:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/bedrock-sessions-*"
    }
  ]
}
```

**Test Plan:**
- Deploy updated IAM policy
- Test Lambda can read/write DynamoDB from Lambda console
- Verify in CloudWatch logs

**Acceptance Criteria:**
- [ ] Policy attached to Lambda execution role
- [ ] Lambda can write to DynamoDB
- [ ] Lambda can read from DynamoDB
- [ ] No permission errors in logs

---

#### Task 1.3: Create Shared Lambda Layer
**Priority:** HIGH
**Dependencies:** None
**Estimated Time:** 4 hours

**Files to Create:**
```
lambda/shared-layer/                    # NEW DIRECTORY
├── README.md                           # NEW
├── build.sh                            # NEW
├── python/
│   └── lib/
│       ├── __init__.py                 # NEW
│       ├── api_client.py               # NEW - Core API client
│       ├── session_manager.py          # NEW - DynamoDB session helper
│       ├── error_handler.py            # NEW - Error handling utilities
│       ├── validators.py               # NEW - Input validation
│       └── utils.py                    # NEW - Common utilities
└── requirements.txt                    # NEW
```

**Key Modules:**

**1. API Client (`api_client.py`):**
```python
"""
PF360 API Client with error handling and retry logic
"""
import requests
import os
import logging
from typing import Dict, Any, Optional
from .error_handler import APIError, handle_api_error
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

class PF360APIClient:
    """Client for PF360 Customer Scheduler API"""

    def __init__(self, session_data: Dict[str, Any]):
        self.base_url = os.getenv("CUSTOMER_SCHEDULER_BASE_API_URL")
        self.client_id = session_data.get("client_id")
        self.auth_token = session_data.get("auth_token")
        self.timeout = int(os.getenv("API_TIMEOUT", "20"))
        self.max_retries = int(os.getenv("API_MAX_RETRIES", "3"))

    def _headers(self) -> Dict[str, str]:
        """Generate request headers"""
        return {
            "authorization": self.auth_token,
            "client_id": self.client_id,
            "Content-Type": "application/json",
            "charset": "utf-8"
        }

    @handle_api_error
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make GET request with error handling and retries

        Args:
            endpoint: API endpoint (e.g., "/dashboard/get/client/customer")
            params: Query parameters

        Returns:
            {"success": True, "data": {...}} or {"success": False, "error": "..."}
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                logger.info(f"API GET {url} (attempt {attempt + 1}/{self.max_retries})")

                response = requests.get(
                    url,
                    headers=self._headers(),
                    params=params,
                    timeout=self.timeout
                )

                # Log response for debugging
                logger.info(f"API Response: {response.status_code}")

                response.raise_for_status()

                return {
                    "success": True,
                    "data": response.json(),
                    "status_code": response.status_code
                }

            except requests.Timeout:
                logger.warning(f"API timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return {
                        "success": False,
                        "error": "API request timed out. Please try again.",
                        "error_type": "timeout"
                    }

            except requests.HTTPError as e:
                status = e.response.status_code
                logger.error(f"HTTP {status} error: {e}")

                # Don't retry on 4xx errors (client errors)
                if 400 <= status < 500:
                    error_msg = self._parse_error_message(e.response)
                    return {
                        "success": False,
                        "error": error_msg,
                        "error_type": "client_error",
                        "status_code": status
                    }

                # Retry on 5xx errors (server errors)
                if attempt == self.max_retries - 1:
                    return {
                        "success": False,
                        "error": f"API server error ({status}). Please try again later.",
                        "error_type": "server_error",
                        "status_code": status
                    }

            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}", exc_info=True)
                if attempt == self.max_retries - 1:
                    return {
                        "success": False,
                        "error": "An unexpected error occurred. Please try again.",
                        "error_type": "unknown"
                    }

        return {"success": False, "error": "Maximum retries exceeded"}

    @handle_api_error
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request with error handling"""
        url = f"{self.base_url}{endpoint}"

        try:
            logger.info(f"API POST {url}")

            response = requests.post(
                url,
                headers=self._headers(),
                json=data,
                timeout=self.timeout
            )

            response.raise_for_status()

            return {
                "success": True,
                "data": response.json(),
                "status_code": response.status_code
            }

        except Exception as e:
            logger.error(f"POST error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": "post_error"
            }

    def _parse_error_message(self, response) -> str:
        """Extract user-friendly error message from API response"""
        try:
            error_data = response.json()
            return error_data.get("message", f"API error: {response.status_code}")
        except:
            return f"API error: {response.status_code}"
```

**2. Session Manager (`session_manager.py`):**
```python
"""
DynamoDB session management
"""
import boto3
import os
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SessionManager:
    """Manage user sessions in DynamoDB"""

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.getenv('DYNAMODB_SESSION_TABLE', 'bedrock-sessions-dev')
        self.table = self.dynamodb.Table(self.table_name)
        self.ttl_seconds = int(os.getenv('SESSION_TTL', '1800'))  # 30 minutes default

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data from DynamoDB

        Args:
            session_id: Unique session identifier

        Returns:
            Session data dict or None if not found/expired
        """
        try:
            response = self.table.get_item(Key={'session_id': session_id})
            item = response.get('Item')

            if item:
                # Check if session expired (TTL not yet processed)
                if item.get('ttl', 0) < time.time():
                    logger.warning(f"Session {session_id} expired")
                    return None

                logger.info(f"Retrieved session {session_id}")
                return item
            else:
                logger.warning(f"Session {session_id} not found")
                return None

        except Exception as e:
            logger.error(f"Error retrieving session: {str(e)}", exc_info=True)
            return None

    def create_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Create new session in DynamoDB

        Args:
            session_id: Unique session identifier
            data: Session data (customer_id, client_id, auth_token, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            item = {
                'session_id': session_id,
                'ttl': int(time.time()) + self.ttl_seconds,
                **data
            }

            self.table.put_item(Item=item)
            logger.info(f"Created session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating session: {str(e)}", exc_info=True)
            return False

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update existing session data

        Args:
            session_id: Session to update
            updates: Fields to update

        Returns:
            True if successful
        """
        try:
            # Build update expression
            update_expr = "SET "
            expr_values = {}
            expr_names = {}

            for i, (key, value) in enumerate(updates.items()):
                attr_name = f"#attr{i}"
                attr_value = f":val{i}"
                update_expr += f"{attr_name} = {attr_value}, "
                expr_names[attr_name] = key
                expr_values[attr_value] = value

            # Add TTL update
            update_expr += "#ttl = :ttl"
            expr_names["#ttl"] = "ttl"
            expr_values[":ttl"] = int(time.time()) + self.ttl_seconds

            self.table.update_item(
                Key={'session_id': session_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values
            )

            logger.info(f"Updated session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating session: {str(e)}", exc_info=True)
            return False

    def set_request_id(self, session_id: str, request_id: str) -> bool:
        """Store request_id for scheduling flow"""
        return self.update_session(session_id, {'request_id': request_id})

    def get_request_id(self, session_id: str) -> Optional[str]:
        """Retrieve request_id for scheduling flow"""
        session = self.get_session(session_id)
        return session.get('request_id') if session else None

    def delete_session(self, session_id: str) -> bool:
        """Delete session (manual cleanup, usually TTL handles this)"""
        try:
            self.table.delete_item(Key={'session_id': session_id})
            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}", exc_info=True)
            return False
```

**3. Error Handler (`error_handler.py`):**
```python
"""
Error handling utilities
"""
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base exception for API errors"""
    pass

class ValidationError(Exception):
    """Input validation error"""
    pass

def handle_api_error(func: Callable) -> Callable:
    """
    Decorator for API error handling

    Usage:
        @handle_api_error
        def some_api_call():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": "An unexpected error occurred",
                "error_type": "unknown",
                "details": str(e)
            }
    return wrapper

def validate_response(response: dict, required_fields: list) -> bool:
    """
    Validate API response has required fields

    Args:
        response: API response dict
        required_fields: List of required field names

    Returns:
        True if valid

    Raises:
        ValidationError if invalid
    """
    if not response.get("success"):
        return True  # Error responses don't need field validation

    data = response.get("data", {})
    missing = [field for field in required_fields if field not in data]

    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")

    return True
```

**4. Validators (`validators.py`):**
```python
"""
Input validation utilities
"""
import re
from typing import Any, Optional
from datetime import datetime

def validate_customer_id(customer_id: str) -> bool:
    """Validate customer_id format"""
    if not customer_id or not isinstance(customer_id, str):
        raise ValueError("customer_id must be a non-empty string")
    # Add specific format validation if needed
    return True

def validate_project_id(project_id: str) -> bool:
    """Validate project_id format"""
    if not project_id or not isinstance(project_id, str):
        raise ValueError("project_id must be a non-empty string")
    return True

def validate_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

def validate_time(time_str: str) -> bool:
    """Validate time format (HH:MM)"""
    pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    if not re.match(pattern, time_str):
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM")
    return True

def validate_session_id(session_id: str) -> bool:
    """Validate session_id format"""
    if not session_id or not isinstance(session_id, str):
        raise ValueError("session_id must be a non-empty string")
    return True
```

**Build Script (`build.sh`):**
```bash
#!/bin/bash
# Build Lambda layer

set -e

echo "Building Lambda layer..."

# Create build directory
rm -rf build
mkdir -p build/python/lib

# Copy source files
cp -r python/lib/* build/python/lib/

# Install dependencies
if [ -f requirements.txt ]; then
    pip install -r requirements.txt -t build/python/
fi

# Create ZIP
cd build
zip -r ../lambda-layer.zip python/
cd ..

echo "Lambda layer built: lambda-layer.zip"
echo "Upload to AWS Lambda Layers"
```

**requirements.txt:**
```
requests==2.31.0
boto3==1.34.0
python-dateutil==2.8.2
```

**Test Plan:**
- Build layer locally
- Test imports work
- Deploy to AWS
- Attach to Lambda
- Test Lambda can use layer

**Acceptance Criteria:**
- [ ] Layer builds successfully
- [ ] All modules importable
- [ ] Deployed to AWS Lambda Layers
- [ ] Attached to all 3 Lambda functions
- [ ] Lambda can import and use modules

---

### Phase 2: Lambda Function Updates (3-5 days)

#### Task 2.1: Update `scheduling-actions` Lambda
**Priority:** HIGH
**Dependencies:** Task 1.3 (Lambda layer)
**Estimated Time:** 8 hours

**Files to Modify:**
- `lambda/scheduling-actions/handler.py` (MODIFY - major update)
- `lambda/scheduling-actions/mock_data.py` (MODIFY - update to match real API responses)
- `lambda/scheduling-actions/requirements.txt` (MODIFY - add layer dependency)

**Files to Create:**
- `lambda/scheduling-actions/api_integration.py` (NEW - real API calls)

**New File: `api_integration.py`:**
```python
"""
Real API integration for Scheduling Actions
"""
import os
from datetime import datetime
import pytz
from lib.api_client import PF360APIClient
from lib.session_manager import SessionManager
from lib.validators import *
from lib.error_handler import handle_api_error
from mock_data import get_mock_projects, get_mock_available_dates, ...

# Import configuration
from config import USE_MOCK_API, ENABLE_REAL_CONFIRM, ENABLE_REAL_CANCEL

class SchedulingAPIIntegration:
    """Handles real API calls for scheduling actions"""

    def __init__(self, session_id: str):
        self.session_mgr = SessionManager()
        self.session_id = session_id
        self.session = self.session_mgr.get_session(session_id)

        if not self.session:
            raise ValueError(f"Invalid session: {session_id}")

        # Initialize API client with session data
        self.api_client = PF360APIClient(self.session)
        self.use_mock = USE_MOCK_API

    @handle_api_error
    def get_projects(self, customer_id: str) -> dict:
        """
        Get customer projects

        Args:
            customer_id: Customer ID

        Returns:
            {"success": True, "data": {"projects": [...]}} or error dict
        """
        # Validation
        validate_customer_id(customer_id)

        # Mock mode
        if self.use_mock:
            mock_response = get_mock_projects(customer_id)
            projects = self._extract_projects(mock_response)
            return {"success": True, "data": {"projects": projects}}

        # Real API call
        client_id = self.session.get("client_id")
        endpoint = f"/dashboard/get/{client_id}/{customer_id}"

        result = self.api_client.get(endpoint)

        if not result["success"]:
            return result

        # Transform API response to clean format
        projects = self._extract_projects(result["data"])

        # Add project URLs
        env = self.session.get("environment", "dev")
        client_name = self.session.get("client_name")

        for project in projects:
            project["project_url"] = self._build_project_url(
                client_name, env, project["project_id"]
            )

        return {"success": True, "data": {"projects": projects}}

    def _extract_projects(self, raw_data: dict) -> list:
        """Transform flattened API response to clean project list"""
        projects = []
        data_list = raw_data.get("data", [])

        for i, item in enumerate(data_list):
            projects.append({
                "project_number": i + 1,
                "project_id": item.get("project_project_id"),
                "order_number": item.get("project_project_number"),
                "project_type": item.get("project_type_project_type"),
                "category": item.get("project_category_category"),
                "status": item.get("status_info_status"),
                "store": item.get("project_store_store_number"),
                "installation_addr": item.get("installation_address_full_address"),
                "address": {
                    "street": item.get("installation_address_address1"),
                    "street2": item.get("installation_address_address2"),
                    "city": item.get("installation_address_city"),
                    "state": item.get("installation_address_state"),
                    "zipcode": item.get("installation_address_zipcode")
                },
                "dates": {
                    "date_sold": item.get("project_date_sold"),
                    "scheduled_date": item.get("project_date_scheduled_date"),
                    "scheduled_start": item.get("convertedProjectStartScheduledDate"),
                    "scheduled_end": item.get("convertedProjectEndScheduledDate"),
                    "date_completed": item.get("project_date_completed_date")
                },
                "technician": {
                    "user_id": item.get("user_idata_user_id"),
                    "first_name": item.get("user_idata_first_name"),
                    "last_name": item.get("user_idata_last_name")
                },
                "service_time": {
                    "duration_value": item.get("service_time_duration_value"),
                    "duration_type": item.get("service_time_duration_type")
                }
            })

        return projects

    def _build_project_url(self, client_name: str, env: str, project_id: str) -> str:
        """Build clickable project URL"""
        env_map = {"dev": "dev", "qa": "qa", "staging": "staging", "prod": "apps"}
        domain = env_map.get(env, "dev")
        return f"https://{client_name}.cx-portal.{domain}.projectsforce.com/details/{project_id}"

    @handle_api_error
    def get_available_dates(self, customer_id: str, project_id: str) -> dict:
        """
        Get available dates for scheduling

        Returns:
            {
                "success": True,
                "data": {
                    "available_dates": ["2025-10-20", ...],
                    "request_id": "req_abc123"
                }
            }
        """
        # Validation
        validate_customer_id(customer_id)
        validate_project_id(project_id)

        # Mock mode
        if self.use_mock:
            mock_response = get_mock_available_dates(customer_id, project_id)
            return {"success": True, "data": mock_response}

        # Real API call
        client_id = self.session.get("client_id")
        today = datetime.now().strftime("%Y-%m-%d")

        endpoint = f"/scheduler/client/{client_id}/project/{project_id}/date/{today}/selected/{today}/get-rescheduler-slots"

        result = self.api_client.get(endpoint)

        if not result["success"]:
            return result

        # Extract dates and request_id
        data = result["data"].get("data", {})
        dates = data.get("dates", [])
        request_id = data.get("request_id")

        # CRITICAL: Store request_id for next steps
        if request_id:
            self.session_mgr.set_request_id(self.session_id, request_id)

        return {
            "success": True,
            "data": {
                "available_dates": dates,
                "request_id": request_id
            }
        }

    @handle_api_error
    def get_time_slots(self, customer_id: str, project_id: str, date: str) -> dict:
        """
        Get available time slots for a specific date

        Requires: request_id from previous get_available_dates call
        """
        # Validation
        validate_customer_id(customer_id)
        validate_project_id(project_id)
        validate_date(date)

        # Mock mode
        if self.use_mock:
            mock_response = get_mock_time_slots(customer_id, project_id, date)
            return {"success": True, "data": mock_response}

        # Get request_id from session
        request_id = self.session_mgr.get_request_id(self.session_id)

        if not request_id:
            return {
                "success": False,
                "error": "No active scheduling session. Please get available dates first.",
                "error_type": "missing_request_id"
            }

        # Real API call
        client_id = self.session.get("client_id")
        endpoint = f"/scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{date}/get-rescheduler-slots"

        result = self.api_client.get(endpoint, params={"request_id": request_id})

        if not result["success"]:
            return result

        # Extract slots
        data = result["data"].get("data", {})
        slots = data.get("slots", [])

        return {
            "success": True,
            "data": {
                "time_slots": slots,
                "date": date
            }
        }

    @handle_api_error
    def confirm_appointment(self, customer_id: str, project_id: str, date: str, time: str) -> dict:
        """
        Confirm/schedule appointment

        Requires: request_id from get_available_dates call
        """
        # Validation
        validate_customer_id(customer_id)
        validate_project_id(project_id)
        validate_date(date)
        validate_time(time)

        # Check feature flag
        if not ENABLE_REAL_CONFIRM:
            return {
                "success": True,
                "data": {
                    "message": "TEST MODE: Appointment would be confirmed",
                    "date": date,
                    "time": time,
                    "test_mode": True
                }
            }

        # Mock mode
        if self.use_mock:
            mock_response = get_mock_confirm_response(customer_id, project_id, date, time)
            return {"success": True, "data": mock_response}

        # Get request_id
        request_id = self.session_mgr.get_request_id(self.session_id)

        if not request_id:
            return {
                "success": False,
                "error": "No active scheduling session",
                "error_type": "missing_request_id"
            }

        # Build payload
        created_at = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%m-%d-%Y %H:%M:%S")

        payload = {
            "created_at": created_at,
            "date": date,
            "time": time,
            "request_id": request_id,
            "is_chatbot": "true"  # String, not boolean
        }

        # Real API call
        client_id = self.session.get("client_id")
        endpoint = f"/scheduler/client/{client_id}/project/{project_id}/schedule"

        result = self.api_client.post(endpoint, payload)

        if not result["success"]:
            return result

        # Clear request_id after successful booking
        self.session_mgr.update_session(self.session_id, {"request_id": None})

        return {
            "success": True,
            "data": {
                "message": result["data"].get("message", "Appointment confirmed"),
                "date": date,
                "time": time
            }
        }

    # Similar methods for:
    # - cancel_appointment()
    # - get_business_hours()
```

**Updated `handler.py`:**
```python
"""
Scheduling Actions Lambda Handler - Updated with real API integration
"""
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import integration layer
from api_integration import SchedulingAPIIntegration
from config import USE_MOCK_API

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Bedrock Agent actions

    Event structure from Bedrock:
    {
        "actionGroup": "scheduling-actions",
        "action": "list_projects",
        "parameters": [
            {"name": "session_id", "value": "sess_123"},
            {"name": "customer_id", "value": "CUST001"}
        ]
    }
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        action_group = event.get("actionGroup")
        action = event.get("action")
        parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}

        # Extract common parameters
        session_id = parameters.get("session_id")
        customer_id = parameters.get("customer_id")

        if not session_id:
            return error_response("session_id is required")

        # Initialize API integration
        api = SchedulingAPIIntegration(session_id)

        # Route to appropriate action
        if action == "list_projects":
            result = api.get_projects(customer_id)

        elif action == "get_available_dates":
            project_id = parameters.get("project_id")
            result = api.get_available_dates(customer_id, project_id)

        elif action == "get_time_slots":
            project_id = parameters.get("project_id")
            date = parameters.get("date")
            result = api.get_time_slots(customer_id, project_id, date)

        elif action == "confirm_appointment":
            project_id = parameters.get("project_id")
            date = parameters.get("date")
            time = parameters.get("time")
            result = api.confirm_appointment(customer_id, project_id, date, time)

        elif action == "cancel_appointment":
            project_id = parameters.get("project_id")
            result = api.cancel_appointment(customer_id, project_id)

        elif action == "get_business_hours":
            client_id = parameters.get("client_id")
            result = api.get_business_hours(client_id)

        else:
            return error_response(f"Unknown action: {action}")

        # Return result
        if result.get("success"):
            return success_response(result["data"])
        else:
            return error_response(result.get("error", "Unknown error"))

    except Exception as e:
        logger.error(f"Lambda error: {str(e)}", exc_info=True)
        return error_response(f"Lambda error: {str(e)}")

def success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Format success response for Bedrock"""
    return {
        "actionGroup": "scheduling-actions",
        "apiPath": "/",
        "httpMethod": "POST",
        "httpStatusCode": 200,
        "responseBody": {
            "application/json": {
                "body": json.dumps(data)
            }
        }
    }

def error_response(error_message: str) -> Dict[str, Any]:
    """Format error response for Bedrock"""
    return {
        "actionGroup": "scheduling-actions",
        "apiPath": "/",
        "httpMethod": "POST",
        "httpStatusCode": 400,
        "responseBody": {
            "application/json": {
                "body": json.dumps({"error": error_message})
            }
        }
    }
```

**Test Plan:**
- [ ] Test with `USE_MOCK_API=true` (should work as before)
- [ ] Test with `USE_MOCK_API=false` in dev
- [ ] Test each action independently
- [ ] Test full scheduling flow (dates → slots → confirm)
- [ ] Test error scenarios (invalid session, timeout, etc.)
- [ ] Test request_id tracking

**Acceptance Criteria:**
- [ ] All 6 actions working in mock mode
- [ ] All 6 actions working with real API in dev
- [ ] Request ID properly stored and retrieved
- [ ] Error handling working
- [ ] Logging comprehensive
- [ ] No regression (mock mode still works)

---

#### Task 2.2 & 2.3: Update Other Lambda Functions
**Priority:** MEDIUM
**Dependencies:** Task 2.1 completed
**Estimated Time:** 4 hours each

Apply same pattern to:
- `information-actions` (4 actions)
- `notes-actions` (2 actions)

**Same files to create/modify in each Lambda**

---

### Phase 3: Frontend Updates (2-3 days)

#### Task 3.1: Add Session Management to Flask Backend
**Priority:** HIGH
**Dependencies:** Task 1.1 (DynamoDB table)
**Estimated Time:** 4 hours

**Files to Modify:**
- `frontend/backend/app.py` (MODIFY - major update)

**Files to Create:**
- `frontend/backend/session_manager.py` (NEW - same as Lambda layer)
- `frontend/backend/requirements.txt` (MODIFY - add boto3)

**Updated `app.py`:**
```python
"""
Flask Backend with Session Management
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
import json
import time
import os
import uuid

from session_manager import SessionManager

app = Flask(__name__)
CORS(app)

# Initialize session manager
session_mgr = SessionManager()

# Bedrock client
bedrock_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

SUPERVISOR_ID = os.getenv('BEDROCK_SUPERVISOR_ID', 'DWDXA5LC4V')
SUPERVISOR_ALIAS = os.getenv('BEDROCK_SUPERVISOR_ALIAS', 'NJLOOCOFAX')

@app.route('/api/chat/simple', methods=['POST'])
def chat_simple():
    """
    Chat endpoint with session management

    Request:
    {
        "message": "Show me my projects",
        "customer_id": "CUST001",      # From auth token
        "client_id": "acme-corp",      # From auth token
        "client_name": "acme-corp",    # From auth token
        "authorization": "Bearer xxx"  # Auth token
    }
    """
    data = request.json
    message = data.get('message')
    customer_id = data.get('customer_id')
    client_id = data.get('client_id')
    client_name = data.get('client_name')
    auth_token = data.get('authorization') or request.headers.get('Authorization')

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    # TODO: Validate auth token (JWT decode, check expiry, etc.)

    # Generate or retrieve session ID
    session_id = data.get('session_id')
    if not session_id:
        session_id = f"sess_{customer_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    # Store session in DynamoDB
    session_mgr.create_session(session_id, {
        'customer_id': customer_id,
        'client_id': client_id,
        'client_name': client_name,
        'auth_token': auth_token,
        'environment': os.getenv('ENVIRONMENT', 'dev')
    })

    # Augment prompt with session context
    augmented_prompt = f"""Session Context:
- Session ID: {session_id}
- Customer ID: {customer_id}
- Client ID: {client_id}

User Request: {message}

Please help the customer with their request."""

    # Call Bedrock
    response = bedrock_client.invoke_agent(
        agentId=SUPERVISOR_ID,
        agentAliasId=SUPERVISOR_ALIAS,
        sessionId=session_id,
        inputText=augmented_prompt
    )

    # Collect response
    full_response = ""
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                full_response += chunk['bytes'].decode('utf-8')

    return jsonify({
        'response': full_response,
        'session_id': session_id,
        'timestamp': time.time()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
```

**Test Plan:**
- [ ] Test session creation in DynamoDB
- [ ] Test session retrieval
- [ ] Test session TTL
- [ ] Test end-to-end conversation with session

**Acceptance Criteria:**
- [ ] Sessions created in DynamoDB
- [ ] Session ID returned to frontend
- [ ] Lambda can retrieve session
- [ ] TTL working (30 min expiry)

---

### Phase 4: Testing (3-5 days)

#### Task 4.1: Unit Tests
**Priority:** HIGH
**Dependencies:** All implementation complete
**Estimated Time:** 6 hours

**Files to Create:**
```
tests/unit/
├── test_api_client.py           # NEW
├── test_session_manager.py      # NEW
├── test_validators.py           # NEW
├── test_scheduling_lambda.py    # NEW
├── test_information_lambda.py   # NEW
└── test_notes_lambda.py         # NEW
```

**Example Test (`test_api_client.py`):**
```python
"""
Unit tests for PF360APIClient
"""
import pytest
import responses
from lib.api_client import PF360APIClient

class TestPF360APIClient:

    @pytest.fixture
    def api_client(self):
        session_data = {
            "client_id": "test-client",
            "auth_token": "Bearer test_token"
        }
        return PF360APIClient(session_data)

    @responses.activate
    def test_get_success(self, api_client):
        """Test successful GET request"""
        responses.add(
            responses.GET,
            "https://api.projectsforce.com/test",
            json={"data": "test"},
            status=200
        )

        result = api_client.get("/test")

        assert result["success"] is True
        assert result["data"] == {"data": "test"}

    @responses.activate
    def test_get_timeout(self, api_client):
        """Test timeout handling"""
        responses.add(
            responses.GET,
            "https://api.projectsforce.com/test",
            body=requests.Timeout("Connection timeout")
        )

        result = api_client.get("/test")

        assert result["success"] is False
        assert result["error_type"] == "timeout"

    @responses.activate
    def test_get_401_error(self, api_client):
        """Test 401 authentication error"""
        responses.add(
            responses.GET,
            "https://api.projectsforce.com/test",
            json={"message": "Unauthorized"},
            status=401
        )

        result = api_client.get("/test")

        assert result["success"] is False
        assert result["error_type"] == "client_error"
        assert result["status_code"] == 401
```

**Run Command:**
```bash
pytest tests/unit/ -v --cov=lambda --cov-report=html
```

**Acceptance Criteria:**
- [ ] 80%+ code coverage
- [ ] All tests passing
- [ ] Edge cases covered
- [ ] Error scenarios tested

---

#### Task 4.2: Integration Tests
**Priority:** HIGH
**Dependencies:** Task 4.1
**Estimated Time:** 8 hours

**Files to Create:**
```
tests/integration/
├── test_scheduling_flow.py      # NEW - Full scheduling workflow
├── test_information_flow.py     # NEW
├── test_notes_flow.py           # NEW
└── test_error_scenarios.py      # NEW
```

**Example Test (`test_scheduling_flow.py`):**
```python
"""
Integration test for complete scheduling workflow
"""
import pytest
import boto3
import json

class TestSchedulingFlow:

    @pytest.fixture(scope="class")
    def setup_session(self):
        """Create test session in DynamoDB"""
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('bedrock-sessions-dev')

        session_data = {
            'session_id': 'test_sess_integration',
            'customer_id': 'CUST001',
            'client_id': 'test-client',
            'client_name': 'test-client',
            'auth_token': 'Bearer test_token',
            'environment': 'dev',
            'ttl': int(time.time()) + 1800
        }

        table.put_item(Item=session_data)

        yield session_data

        # Cleanup
        table.delete_item(Key={'session_id': 'test_sess_integration'})

    def test_full_scheduling_workflow(self, setup_session):
        """
        Test complete scheduling flow:
        1. List projects
        2. Get available dates (returns request_id)
        3. Get time slots (uses request_id)
        4. Confirm appointment (uses request_id)
        """
        lambda_client = boto3.client('lambda')

        # Step 1: List projects
        response = lambda_client.invoke(
            FunctionName='scheduling-actions',
            Payload=json.dumps({
                'actionGroup': 'scheduling-actions',
                'action': 'list_projects',
                'parameters': [
                    {'name': 'session_id', 'value': 'test_sess_integration'},
                    {'name': 'customer_id', 'value': 'CUST001'}
                ]
            })
        )

        result = json.loads(response['Payload'].read())
        assert result['httpStatusCode'] == 200

        # Step 2: Get available dates
        response = lambda_client.invoke(
            FunctionName='scheduling-actions',
            Payload=json.dumps({
                'actionGroup': 'scheduling-actions',
                'action': 'get_available_dates',
                'parameters': [
                    {'name': 'session_id', 'value': 'test_sess_integration'},
                    {'name': 'customer_id', 'value': 'CUST001'},
                    {'name': 'project_id', 'value': '12345'}
                ]
            })
        )

        result = json.loads(response['Payload'].read())
        assert result['httpStatusCode'] == 200

        # Verify request_id stored in DynamoDB
        session_mgr = SessionManager()
        request_id = session_mgr.get_request_id('test_sess_integration')
        assert request_id is not None

        # Step 3: Get time slots (should use stored request_id)
        # Step 4: Confirm appointment (should use stored request_id)
        # ... (similar pattern)
```

**Acceptance Criteria:**
- [ ] Full workflows tested
- [ ] Multi-step flows working
- [ ] State properly maintained
- [ ] Error recovery tested

---

## Testing Requirements Summary

### Test Coverage Goals

**Unit Tests (80%+ coverage):**
- [ ] API client (all methods)
- [ ] Session manager (all methods)
- [ ] Validators (all validation rules)
- [ ] Error handlers (all error types)
- [ ] Each Lambda action handler

**Integration Tests:**
- [ ] Complete scheduling flow
- [ ] Information retrieval flow
- [ ] Notes addition flow
- [ ] Session lifecycle
- [ ] Request ID tracking
- [ ] Error scenarios

**Load Tests (Existing in `tests/LoadTest/`):**
- [ ] 10 concurrent users
- [ ] 50 concurrent users
- [ ] 100 concurrent users
- [ ] Sustained load (30 min)

**Test Environments:**
- [ ] Local (mock mode)
- [ ] Dev (real API)
- [ ] QA (real API)
- [ ] Staging (real API)

---

## Rollout Plan

### Week 1: Infrastructure + Shared Layer
- [ ] Day 1-2: DynamoDB setup (Task 1.1, 1.2)
- [ ] Day 3-5: Lambda layer development and testing (Task 1.3)

### Week 2: Lambda Updates
- [ ] Day 1-3: Update scheduling-actions (Task 2.1)
- [ ] Day 4: Update information-actions (Task 2.2)
- [ ] Day 5: Update notes-actions (Task 2.3)

### Week 3: Frontend + Testing
- [ ] Day 1-2: Frontend session management (Task 3.1)
- [ ] Day 3-4: Unit tests (Task 4.1)
- [ ] Day 5: Integration tests (Task 4.2)

### Week 4: QA + Production Rollout
- [ ] Day 1-2: QA testing
- [ ] Day 3: Deploy to staging
- [ ] Day 4: Gradual prod rollout (10% → 50% → 100%)
- [ ] Day 5: Monitor, optimize, document

---

## Success Criteria

### Phase Completion Checklist

**Phase 1 (Infrastructure):**
- [ ] DynamoDB table created in all environments
- [ ] Lambda IAM permissions working
- [ ] Lambda layer deployed and attached
- [ ] All modules importable and working

**Phase 2 (Lambda Updates):**
- [ ] All actions work in mock mode (no regression)
- [ ] All actions work with real API in dev
- [ ] Error handling comprehensive
- [ ] Logging sufficient for debugging
- [ ] Request ID tracking working

**Phase 3 (Frontend):**
- [ ] Session creation working
- [ ] Session storage in DynamoDB
- [ ] Session retrieval in Lambda
- [ ] End-to-end flow working

**Phase 4 (Testing):**
- [ ] 80%+ unit test coverage
- [ ] All integration tests passing
- [ ] Load tests meet performance targets
- [ ] No errors in CloudWatch

**Production Readiness:**
- [ ] Deployed to QA
- [ ] QA team approval
- [ ] Performance acceptable (P95 < 3s)
- [ ] Error rate < 1%
- [ ] Monitoring dashboards set up
- [ ] Rollback tested

---

## Open Questions / Decisions Needed

1. **API Credentials:**
   - Do we have dev environment API access?
   - Test auth tokens available?
   - Customer IDs for testing?

2. **Timeline:**
   - Target production date?
   - QA testing window?
   - Acceptable rollout schedule?

3. **Feature Flags:**
   - Start with all flags OFF (mock mode)?
   - Gradual enable per action or all at once?
   - Rollback threshold (error rate)?

4. **Monitoring:**
   - CloudWatch dashboards needed?
   - Alert thresholds?
   - On-call rotation?

---

## Next Steps

**Immediate (Today):**
1. Review this implementation plan
2. Get answers to open questions
3. Set up dev environment access
4. Create JIRA tickets / task tracking

**This Week:**
1. Start Phase 1 (Infrastructure)
2. Set up DynamoDB table
3. Begin Lambda layer development

**Ready to Start?**
Please approve this plan and provide answers to open questions, then I'll begin implementation with Phase 1!

---

**Document Version:** 1.0
**Last Updated:** October 19, 2025
**Status:** Awaiting Approval
**Estimated Total Time:** 12-19 days (2.5-4 weeks)
