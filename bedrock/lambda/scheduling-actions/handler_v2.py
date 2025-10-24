"""
Scheduling Actions Lambda Handler (Updated with Shared Layer)
Handles 6 scheduling-related actions for Bedrock Agent

Actions:
1. list_projects - Show available projects for customer
2. get_available_dates - Get available dates for scheduling
3. get_time_slots - Get available time slots for a date
4. confirm_appointment - Confirm/schedule an appointment
5. reschedule_appointment - Reschedule an existing appointment
6. cancel_appointment - Cancel an appointment

Uses shared Lambda layer for API client, session management, error handling, and validation
Supports both MOCK and REAL API modes via USE_MOCK_API environment variable
"""

import json
import logging
import os
from typing import Dict, Any

# Import from shared layer
from lib.api_client import PF360APIClient
from lib.session_manager import SessionManager
from lib.error_handler import (
    handle_errors,
    format_bedrock_response,
    log_request,
    log_response
)
from lib.validators import (
    validate_bedrock_event,
    extract_bedrock_parameters,
    extract_session_id,
    validate_customer_id,
    validate_project_id,
    validate_date,
    validate_time
)

# Import configuration
from config import USE_MOCK_API

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize session manager
session_manager = SessionManager()

# ============================================================================
# Helper Functions
# ============================================================================

def get_or_create_session(session_id: str, params: Dict[str, str]) -> Dict[str, Any]:
    """
    Get existing session or create new one from parameters

    Args:
        session_id: Bedrock session ID
        params: Parameters from event (should contain customer_id, client_id, client_name)

    Returns:
        Session data dict
    """
    # Try to get existing session
    session_data = session_manager.get_session(session_id)

    if session_data:
        logger.info(f"Retrieved existing session: {session_id}")
        return session_data

    # Create new session from parameters
    logger.info(f"Creating new session: {session_id}")

    # Extract required fields from params or use defaults
    default_session_data = {
        "customer_id": params.get("customer_id", "CUST001"),
        "client_id": params.get("client_id", "CLIENT001"),
        "client_name": params.get("client_name", "testclient"),
        "auth_token": params.get("authorization", "")
    }

    return session_manager.create_session(session_id, default_session_data)


def extract_and_simplify_projects(response: Dict[str, Any]) -> list:
    """
    Extract and simplify project data from API response

    Args:
        response: Raw API response

    Returns:
        List of simplified project dicts
    """
    projects = []
    for i, item in enumerate(response.get("data", [])):
        projects.append({
            "project_number": i + 1,
            "project_id": item.get("project_project_id"),
            "order_number": item.get("project_project_number"),
            "project_type": item.get("project_type_project_type"),
            "category": item.get("project_category_category"),
            "status": item.get("status_info_status"),
            "store": item.get("project_store_store_number"),
            "address": item.get("installation_address_full_address"),
            "scheduled_date": item.get("project_date_scheduled_date")
        })
    return projects


# ============================================================================
# Action Handlers
# ============================================================================

@handle_errors
def handle_list_projects(event: Dict, session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Action: list_projects
    Returns list of projects for the customer
    """
    params = extract_bedrock_parameters(event)

    # Validate customer_id
    customer_id = validate_customer_id(params.get("customer_id"))

    # Initialize API client with session data
    api_client = PF360APIClient(session_data)

    # Fetch projects
    logger.info(f"Fetching projects for customer {customer_id}")
    response = api_client.get_projects()

    # Extract and simplify
    projects = extract_and_simplify_projects(response)

    result = {
        "action": "list_projects",
        "customer_id": customer_id,
        "project_count": len(projects),
        "projects": projects,
        "mock_mode": USE_MOCK_API
    }

    return format_bedrock_response(
        action_group=event.get("actionGroup", "scheduling"),
        api_path=event.get("apiPath", "/list-projects"),
        http_method=event.get("httpMethod", "POST"),
        response_body=result,
        http_status_code=200
    )


@handle_errors
def handle_get_available_dates(event: Dict, session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Action: get_available_dates
    Returns available dates for scheduling a project
    """
    params = extract_bedrock_parameters(event)

    # Validate parameters
    project_id = validate_project_id(params.get("project_id"))

    # Initialize API client
    api_client = PF360APIClient(session_data)

    # Fetch available dates
    logger.info(f"Fetching available dates for project {project_id}")
    response = api_client.get_available_dates(project_id)

    # Extract data
    data = response.get("data", {})
    request_id = data.get("request_id")

    # Store request_id in session for subsequent calls
    if request_id:
        session_id = extract_session_id(event)
        session_manager.update_request_id(session_id, request_id)
        logger.info(f"Stored request_id in session: {request_id}")

    result = {
        "action": "get_available_dates",
        "project_id": project_id,
        "available_dates": data.get("dates", []),
        "request_id": request_id,
        "mock_mode": USE_MOCK_API
    }

    return format_bedrock_response(
        action_group=event.get("actionGroup", "scheduling"),
        api_path=event.get("apiPath", "/get-available-dates"),
        http_method=event.get("httpMethod", "POST"),
        response_body=result,
        http_status_code=200
    )


@handle_errors
def handle_get_time_slots(event: Dict, session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Action: get_time_slots
    Returns available time slots for a specific date
    """
    params = extract_bedrock_parameters(event)

    # Validate parameters
    project_id = validate_project_id(params.get("project_id"))
    date = validate_date(params.get("date"))

    # Get request_id from session or parameters
    request_id = params.get("request_id") or session_data.get("request_id")

    if not request_id:
        raise ValueError(
            "request_id is required. Please call get_available_dates first."
        )

    # Initialize API client with request_id from session
    api_client = PF360APIClient(session_data)

    # Fetch time slots
    logger.info(f"Fetching time slots for project {project_id} on {date}")
    response = api_client.get_time_slots(project_id, date, request_id)

    # Extract data
    data = response.get("data", {})

    result = {
        "action": "get_time_slots",
        "project_id": project_id,
        "date": date,
        "available_slots": data.get("slots", []),
        "mock_mode": USE_MOCK_API
    }

    return format_bedrock_response(
        action_group=event.get("actionGroup", "scheduling"),
        api_path=event.get("apiPath", "/get-time-slots"),
        http_method=event.get("httpMethod", "POST"),
        response_body=result,
        http_status_code=200
    )


@handle_errors
def handle_confirm_appointment(event: Dict, session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Action: confirm_appointment
    Confirms/schedules an appointment for a project
    """
    params = extract_bedrock_parameters(event)

    # Validate parameters
    project_id = validate_project_id(params.get("project_id"))
    date = validate_date(params.get("date"))
    time = validate_time(params.get("time"))

    # Get request_id from session or parameters
    request_id = params.get("request_id") or session_data.get("request_id")

    if not request_id:
        raise ValueError(
            "request_id is required. Please call get_available_dates first."
        )

    # Initialize API client
    api_client = PF360APIClient(session_data)

    # Confirm appointment
    logger.info(f"Confirming appointment for project {project_id} on {date} at {time}")
    response = api_client.confirm_appointment(project_id, date, time, request_id)

    result = {
        "action": "confirm_appointment",
        "project_id": project_id,
        "scheduled_date": date,
        "scheduled_time": time,
        "message": response.get("message", "Appointment confirmed"),
        "confirmation_data": response.get("data", {}),
        "mock_mode": USE_MOCK_API or not os.getenv("ENABLE_REAL_CONFIRM", "false").lower() == "true"
    }

    return format_bedrock_response(
        action_group=event.get("actionGroup", "scheduling"),
        api_path=event.get("apiPath", "/confirm-appointment"),
        http_method=event.get("httpMethod", "POST"),
        response_body=result,
        http_status_code=200
    )


@handle_errors
def handle_reschedule_appointment(event: Dict, session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Action: reschedule_appointment
    Reschedules an existing appointment (cancel + confirm)
    """
    params = extract_bedrock_parameters(event)

    # Validate parameters
    project_id = validate_project_id(params.get("project_id"))
    new_date = validate_date(params.get("new_date"))
    new_time = validate_time(params.get("new_time"))

    # Get request_id from session or parameters
    request_id = params.get("request_id") or session_data.get("request_id")

    if not request_id:
        raise ValueError(
            "request_id is required. Please call get_available_dates first."
        )

    # Initialize API client
    api_client = PF360APIClient(session_data)

    logger.info(f"Rescheduling appointment for project {project_id}")

    # Step 1: Cancel existing appointment
    cancel_result = {"status": "skipped"}
    try:
        cancel_response = api_client.cancel_appointment(project_id, request_id)
        cancel_result = {
            "status": "success",
            "message": cancel_response.get("message", "Cancelled")
        }
    except Exception as e:
        logger.warning(f"Cancel failed (might not have existing appointment): {str(e)}")
        cancel_result = {"status": "skipped", "reason": str(e)}

    # Step 2: Confirm new appointment
    confirm_response = api_client.confirm_appointment(project_id, new_date, new_time, request_id)

    result = {
        "action": "reschedule_appointment",
        "project_id": project_id,
        "new_date": new_date,
        "new_time": new_time,
        "cancel_result": cancel_result,
        "confirm_result": {
            "message": confirm_response.get("message", "Confirmed"),
            "data": confirm_response.get("data", {})
        },
        "message": f"Appointment rescheduled to {new_date} at {new_time}",
        "mock_mode": USE_MOCK_API
    }

    return format_bedrock_response(
        action_group=event.get("actionGroup", "scheduling"),
        api_path=event.get("apiPath", "/reschedule-appointment"),
        http_method=event.get("httpMethod", "POST"),
        response_body=result,
        http_status_code=200
    )


@handle_errors
def handle_cancel_appointment(event: Dict, session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Action: cancel_appointment
    Cancels an existing appointment
    """
    params = extract_bedrock_parameters(event)

    # Validate parameters
    project_id = validate_project_id(params.get("project_id"))

    # Get request_id from session (optional for cancel)
    request_id = params.get("request_id") or session_data.get("request_id")

    # Initialize API client
    api_client = PF360APIClient(session_data)

    # Cancel appointment
    logger.info(f"Cancelling appointment for project {project_id}")
    response = api_client.cancel_appointment(project_id, request_id)

    result = {
        "action": "cancel_appointment",
        "project_id": project_id,
        "message": response.get("message", "Appointment cancelled"),
        "cancellation_data": response.get("data", {}),
        "mock_mode": USE_MOCK_API or not os.getenv("ENABLE_REAL_CANCEL", "false").lower() == "true"
    }

    return format_bedrock_response(
        action_group=event.get("actionGroup", "scheduling"),
        api_path=event.get("apiPath", "/cancel-appointment"),
        http_method=event.get("httpMethod", "POST"),
        response_body=result,
        http_status_code=200
    )


# ============================================================================
# Lambda Handler
# ============================================================================

def lambda_handler(event, context):
    """
    Main Lambda handler for scheduling actions
    Routes to appropriate action handler based on apiPath
    """
    # Log incoming request
    log_request(event, context)

    try:
        # Validate event structure
        validate_bedrock_event(event)

        # Extract session ID
        session_id = extract_session_id(event)

        # Extract parameters
        params = extract_bedrock_parameters(event)

        # Get or create session
        session_data = get_or_create_session(session_id, params)

        # Extract action from event
        action = event.get("apiPath", "").lstrip("/")

        if not action:
            raise ValueError("No action specified in event")

        logger.info(f"Processing action: {action}")

        # Route to appropriate handler
        handlers = {
            "list-projects": handle_list_projects,
            "get-available-dates": handle_get_available_dates,
            "get-time-slots": handle_get_time_slots,
            "confirm-appointment": handle_confirm_appointment,
            "reschedule-appointment": handle_reschedule_appointment,
            "cancel-appointment": handle_cancel_appointment
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")

        # Execute handler (error handling is done by @handle_errors decorator)
        response = handler(event, session_data)

        # Log response
        log_response(response)

        return response

    except Exception as e:
        # This catches any errors not handled by @handle_errors decorator
        logger.error(f"Unhandled error in lambda_handler: {str(e)}", exc_info=True)

        error_response = format_bedrock_response(
            action_group=event.get("actionGroup", "scheduling"),
            api_path=event.get("apiPath", "/error"),
            http_method=event.get("httpMethod", "POST"),
            response_body={
                "error": str(e),
                "type": "InternalError"
            },
            http_status_code=500
        )

        log_response(error_response)
        return error_response


# For local testing
if __name__ == "__main__":
    # Set mock mode for local testing
    os.environ["USE_MOCK_API"] = "true"

    # Test event
    test_event = {
        "messageVersion": "1.0",
        "agent": {"name": "test-agent", "id": "TEST123", "alias": "v1"},
        "actionGroup": "scheduling",
        "apiPath": "/list-projects",
        "httpMethod": "POST",
        "sessionId": "test-session-123",
        "requestBody": {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "customer_id", "value": "CUST001"},
                        {"name": "client_id", "value": "CLIENT001"},
                        {"name": "client_name", "value": "testclient"}
                    ]
                }
            }
        }
    }

    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))
