"""
Scheduling Actions Lambda Handler
Handles 6 scheduling-related actions for Bedrock Agent

Actions:
1. list_projects - Show available projects for customer
2. get_available_dates - Get available dates for scheduling
3. get_time_slots - Get available time slots for a date
4. confirm_appointment - Confirm/schedule an appointment
5. reschedule_appointment - Reschedule an existing appointment
6. cancel_appointment - Cancel an appointment

Supports both MOCK and REAL API modes via USE_MOCK_API environment variable
"""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# Import configuration and mock data
from config import (
    USE_MOCK_API,
    get_api_config,
    get_auth_headers,
    ENABLE_REAL_CONFIRM,
    ENABLE_REAL_CANCEL
)
from mock_data import (
    get_mock_projects,
    get_mock_available_dates,
    get_mock_time_slots,
    get_mock_confirm_appointment,
    get_mock_cancel_appointment,
    get_mock_business_hours
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ============================================================================
# Helper Functions
# ============================================================================

def extract_parameters(event: Dict) -> Dict[str, Any]:
    """
    Extract parameters from Bedrock Agent event
    Handles both actionGroup and requestBody formats
    """
    try:
        # Bedrock Agent passes parameters in different ways
        if 'parameters' in event and event['parameters']:
            params = {p['name']: p['value'] for p in event['parameters']}
        elif 'requestBody' in event:
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
        else:
            # Fallback: try to parse body
            body = event.get('body', '{}')
            if isinstance(body, str):
                params = json.loads(body)
            else:
                params = body

        logger.info(f"Extracted parameters: {params}")
        return params

    except Exception as e:
        logger.error(f"Error extracting parameters: {str(e)}")
        return {}

def format_success_response(event: Dict, action: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Format successful response for Bedrock Agent"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'scheduling'),
            'apiPath': event.get('apiPath', f'/{action}'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(result)
                }
            }
        }
    }

def format_error_response(event: Dict, action: str, error_message: str, status_code: int = 500) -> Dict[str, Any]:
    """Format error response for Bedrock Agent"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'scheduling'),
            'apiPath': event.get('apiPath', f'/{action}'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': status_code,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({
                        'error': error_message,
                        'action': action
                    })
                }
            }
        }
    }

# ============================================================================
# Action Handlers
# ============================================================================

def handle_list_projects(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: list_projects
    Returns list of projects for the customer
    """
    customer_id = params.get('customer_id')

    if not customer_id:
        raise ValueError("Missing required parameter: customer_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching projects for customer {customer_id}")
        response = get_mock_projects(customer_id)
    else:
        logger.info(f"[REAL] Fetching projects for customer {customer_id}")
        url = f"{config['dashboard_url']}/{customer_id}"
        res = requests.get(url, headers=auth_headers, timeout=30)
        res.raise_for_status()
        response = res.json()

    # Extract and simplify project data
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

    return {
        "action": "list_projects",
        "customer_id": customer_id,
        "project_count": len(projects),
        "projects": projects,
        "mock_mode": USE_MOCK_API
    }

def handle_get_available_dates(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_available_dates
    Returns available dates for scheduling a project
    """
    project_id = params.get('project_id')

    if not project_id:
        raise ValueError("Missing required parameter: project_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching available dates for project {project_id}")
        response = get_mock_available_dates(project_id)
    else:
        logger.info(f"[REAL] Fetching available dates for project {project_id}")
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"{config['scheduler_base_url']}/project/{project_id}/date/{today}/selected/{today}/get-rescheduler-slots"
        res = requests.get(url, headers=auth_headers, timeout=30)
        res.raise_for_status()
        response = res.json()

    data = response.get("data", {})
    return {
        "action": "get_available_dates",
        "project_id": project_id,
        "available_dates": data.get("dates", []),
        "request_id": data.get("request_id"),
        "mock_mode": USE_MOCK_API
    }

def handle_get_time_slots(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_time_slots
    Returns available time slots for a specific date
    """
    project_id = params.get('project_id')
    date = params.get('date')
    request_id = params.get('request_id')

    if not all([project_id, date, request_id]):
        raise ValueError("Missing required parameters: project_id, date, request_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching time slots for project {project_id} on {date}")
        response = get_mock_time_slots(project_id, date, request_id)
    else:
        logger.info(f"[REAL] Fetching time slots for project {project_id} on {date}")
        url = f"{config['scheduler_base_url']}/project/{project_id}/date/{date}/selected/{date}/get-rescheduler-slots?request_id={request_id}"
        res = requests.get(url, headers=auth_headers, timeout=30)
        res.raise_for_status()
        response = res.json()

    data = response.get("data", {})
    return {
        "action": "get_time_slots",
        "project_id": project_id,
        "date": date,
        "available_slots": data.get("slots", []),
        "mock_mode": USE_MOCK_API
    }

def handle_confirm_appointment(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: confirm_appointment
    Confirms/schedules an appointment for a project
    """
    project_id = params.get('project_id')
    date = params.get('date')
    time = params.get('time')
    request_id = params.get('request_id')

    if not all([project_id, date, time, request_id]):
        raise ValueError("Missing required parameters: project_id, date, time, request_id")

    # Use mock if global flag is set OR if real confirm is not enabled
    use_mock = USE_MOCK_API or not ENABLE_REAL_CONFIRM

    if use_mock:
        logger.info(f"[MOCK] Confirming appointment for project {project_id} on {date} at {time}")
        response = get_mock_confirm_appointment(project_id, date, time, request_id)
    else:
        logger.info(f"[REAL] Confirming appointment for project {project_id} on {date} at {time}")
        url = f"{config['scheduler_base_url']}/project/{project_id}/schedule"

        payload = {
            "created_at": datetime.now().strftime("%m-%d-%Y %H:%M:%S"),
            "date": date,
            "time": time,
            "request_id": request_id,
            "is_chatbot": "true"
        }

        res = requests.post(url, headers=auth_headers, json=payload, timeout=30)
        res.raise_for_status()
        response = res.json()

    return {
        "action": "confirm_appointment",
        "project_id": project_id,
        "scheduled_date": date,
        "scheduled_time": time,
        "message": response.get("message", "Appointment confirmed"),
        "confirmation_data": response.get("data", {}),
        "mock_mode": use_mock
    }

def handle_reschedule_appointment(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: reschedule_appointment
    Reschedules an existing appointment (cancel + confirm)
    """
    project_id = params.get('project_id')
    new_date = params.get('new_date')
    new_time = params.get('new_time')
    request_id = params.get('request_id')

    if not all([project_id, new_date, new_time, request_id]):
        raise ValueError("Missing required parameters: project_id, new_date, new_time, request_id")

    logger.info(f"Rescheduling appointment for project {project_id}")

    # Step 1: Cancel existing appointment
    try:
        cancel_result = handle_cancel_appointment(
            {'project_id': project_id},
            config,
            auth_headers
        )
    except Exception as e:
        logger.warning(f"Cancel failed (might not have existing appointment): {str(e)}")
        cancel_result = {"status": "skipped"}

    # Step 2: Confirm new appointment
    confirm_result = handle_confirm_appointment(
        {
            'project_id': project_id,
            'date': new_date,
            'time': new_time,
            'request_id': request_id
        },
        config,
        auth_headers
    )

    return {
        "action": "reschedule_appointment",
        "project_id": project_id,
        "new_date": new_date,
        "new_time": new_time,
        "cancel_result": cancel_result,
        "confirm_result": confirm_result,
        "message": f"Appointment rescheduled to {new_date} at {new_time}",
        "mock_mode": USE_MOCK_API
    }

def handle_cancel_appointment(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: cancel_appointment
    Cancels an existing appointment
    """
    project_id = params.get('project_id')

    if not project_id:
        raise ValueError("Missing required parameter: project_id")

    # Use mock if global flag is set OR if real cancel is not enabled
    use_mock = USE_MOCK_API or not ENABLE_REAL_CANCEL

    if use_mock:
        logger.info(f"[MOCK] Cancelling appointment for project {project_id}")
        response = get_mock_cancel_appointment(project_id)
    else:
        logger.info(f"[REAL] Cancelling appointment for project {project_id}")
        url = f"{config['scheduler_base_url']}/project/{project_id}/cancel-reschedule"
        res = requests.get(url, headers=auth_headers, timeout=30)
        res.raise_for_status()
        response = res.json()

    return {
        "action": "cancel_appointment",
        "project_id": project_id,
        "message": response.get("message", "Appointment cancelled"),
        "cancellation_data": response.get("data", {}),
        "mock_mode": use_mock
    }

# ============================================================================
# Lambda Handler
# ============================================================================

def lambda_handler(event, context):
    """
    Main Lambda handler for scheduling actions
    Routes to appropriate action handler based on apiPath
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract action from event
        action = event.get('apiPath', '').lstrip('/')
        if not action:
            # Fallback: check for action in parameters
            params = extract_parameters(event)
            action = params.get('action', '')

        # Normalize action name: convert underscores to hyphens for handler matching
        action = action.replace('_', '-')

        if not action:
            return format_error_response(
                event,
                'unknown',
                'No action specified in event',
                400
            )

        logger.info(f"Processing action: {action}")

        # Extract parameters
        params = extract_parameters(event)

        # Get configuration
        client_id = params.get('client_id', 'default')
        config = get_api_config(client_id)

        # Get auth headers (if not using mock)
        auth_headers = {}
        if not USE_MOCK_API:
            authorization = params.get('authorization', event.get('authorization', ''))
            auth_headers = get_auth_headers(authorization, client_id)

        # Route to appropriate handler
        handlers = {
            'list-projects': handle_list_projects,
            'get-available-dates': handle_get_available_dates,
            'get-time-slots': handle_get_time_slots,
            'confirm-appointment': handle_confirm_appointment,
            'reschedule-appointment': handle_reschedule_appointment,
            'cancel-appointment': handle_cancel_appointment
        }

        handler = handlers.get(action)
        if not handler:
            return format_error_response(
                event,
                action,
                f'Unknown action: {action}',
                400
            )

        # Execute handler
        result = handler(params, config, auth_headers)

        # Return formatted response
        return format_success_response(event, action, result)

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return format_error_response(
            event,
            action if 'action' in locals() else 'unknown',
            f'Validation error: {str(e)}',
            400
        )

    except requests.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return format_error_response(
            event,
            action if 'action' in locals() else 'unknown',
            f'API request failed: {str(e)}',
            502
        )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return format_error_response(
            event,
            action if 'action' in locals() else 'unknown',
            f'Internal error: {str(e)}',
            500
        )

# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "apiPath": "/list-projects",
        "httpMethod": "POST",
        "parameters": [
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }

    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))
