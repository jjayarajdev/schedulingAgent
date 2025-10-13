"""
Information Actions Lambda Handler
Handles 4 information-related actions for Bedrock Agent

Actions:
1. get_project_details - Show detailed project information
2. get_appointment_status - Check appointment status
3. get_working_hours - Get business hours
4. get_weather - Get weather forecast

Supports both MOCK and REAL API modes via USE_MOCK_API environment variable
"""

import json
import logging
import requests
from typing import Dict, Any, Optional

# Import configuration and mock data
from config import (
    USE_MOCK_API,
    get_api_config,
    get_auth_headers
)
from mock_data import (
    get_mock_project_details,
    get_mock_appointment_status,
    get_mock_business_hours,
    get_mock_weather
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
        if 'parameters' in event:
            params = {p['name']: p['value'] for p in event['parameters']}
        elif 'requestBody' in event:
            content = event['requestBody'].get('content', {})
            params = json.loads(content.get('application/json', '{}'))
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
            'actionGroup': event.get('actionGroup', 'information'),
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
            'actionGroup': event.get('actionGroup', 'information'),
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

def handle_get_project_details(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_project_details
    Returns detailed information about a specific project
    """
    project_id = params.get('project_id')
    customer_id = params.get('customer_id')

    if not all([project_id, customer_id]):
        raise ValueError("Missing required parameters: project_id, customer_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching details for project {project_id}")
        response = get_mock_project_details(project_id, customer_id)
    else:
        logger.info(f"[REAL] Fetching details for project {project_id}")
        url = f"{config['dashboard_url']}/{customer_id}"
        res = requests.get(url, headers=auth_headers, timeout=30)
        res.raise_for_status()
        response = res.json()

    # Extract project data
    data = response.get("data", [])
    project = None
    for item in data:
        if item.get("project_project_id") == project_id:
            project = item
            break

    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Format project details
    project_details = {
        "project_id": project.get("project_project_id"),
        "order_number": project.get("project_project_number"),
        "project_type": project.get("project_type_project_type"),
        "category": project.get("project_category_category"),
        "status": project.get("status_info_status"),
        "store": project.get("project_store_store_number"),
        "address": {
            "full_address": project.get("installation_address_full_address"),
            "address1": project.get("installation_address_address1"),
            "address2": project.get("installation_address_address2"),
            "city": project.get("installation_address_city"),
            "state": project.get("installation_address_state"),
            "zipcode": project.get("installation_address_zipcode")
        },
        "dates": {
            "sold": project.get("project_date_sold"),
            "scheduled": project.get("project_date_scheduled_date"),
            "scheduled_start": project.get("convertedProjectStartScheduledDate"),
            "scheduled_end": project.get("convertedProjectEndScheduledDate"),
            "completed": project.get("project_date_completed_date")
        },
        "technician": {
            "user_id": project.get("user_idata_user_id"),
            "first_name": project.get("user_idata_first_name"),
            "last_name": project.get("user_idata_last_name")
        },
        "service_time": {
            "duration": project.get("service_time_duration_value"),
            "duration_type": project.get("service_time_duration_type")
        },
        "customer": {
            "customer_id": project.get("customer_customer_id"),
            "first_name": project.get("customer_first_name"),
            "last_name": project.get("customer_last_name"),
            "email": project.get("customer_email"),
            "phone": project.get("customer_phone")
        }
    }

    return {
        "action": "get_project_details",
        "project_id": project_id,
        "project_details": project_details,
        "mock_mode": USE_MOCK_API
    }

def handle_get_appointment_status(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_appointment_status
    Returns the current status of an appointment
    Note: No dedicated API found, derived from Dashboard API data
    """
    project_id = params.get('project_id')

    if not project_id:
        raise ValueError("Missing required parameter: project_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching appointment status for project {project_id}")
        response = get_mock_appointment_status(project_id)
    else:
        logger.info(f"[REAL] Fetching appointment status for project {project_id}")
        # Note: Using Dashboard API to derive status since no dedicated endpoint found
        customer_id = params.get('customer_id')
        if not customer_id:
            raise ValueError("Missing required parameter: customer_id (needed for real API)")

        url = f"{config['dashboard_url']}/{customer_id}"
        res = requests.get(url, headers=auth_headers, timeout=30)
        res.raise_for_status()
        dashboard_response = res.json()

        # Find the project and extract status
        project = None
        for item in dashboard_response.get("data", []):
            if item.get("project_project_id") == project_id:
                project = item
                break

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Derive status from project data
        status_info = {
            "project_id": project_id,
            "status": project.get("status_info_status"),
            "scheduled_date": project.get("project_date_scheduled_date"),
            "scheduled_time": project.get("convertedProjectStartScheduledDate"),
            "scheduled_end_time": project.get("convertedProjectEndScheduledDate"),
            "duration": f"{project.get('service_time_duration_value')} {project.get('service_time_duration_type')}",
            "technician": f"{project.get('user_idata_first_name')} {project.get('user_idata_last_name')}" if project.get('user_idata_first_name') else None,
            "can_reschedule": project.get("status_info_status") == "Scheduled",
            "can_cancel": project.get("status_info_status") == "Scheduled"
        }

        response = {
            "status": "success",
            "data": status_info
        }

    data = response.get("data", {})
    return {
        "action": "get_appointment_status",
        "project_id": project_id,
        "appointment_status": data,
        "mock_mode": USE_MOCK_API
    }

def handle_get_working_hours(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_working_hours
    Returns business hours for scheduling
    """
    client_id = params.get('client_id')

    if not client_id:
        raise ValueError("Missing required parameter: client_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching business hours for client {client_id}")
        response = get_mock_business_hours(client_id)
    else:
        logger.info(f"[REAL] Fetching business hours for client {client_id}")
        url = config['business_hours_url']
        res = requests.get(url, headers=auth_headers, timeout=30)
        res.raise_for_status()
        response = res.json()

    data = response.get("data", {})
    return {
        "action": "get_working_hours",
        "client_id": client_id,
        "business_hours": data.get("workHours", []),
        "timezone": data.get("timezone"),
        "mock_mode": USE_MOCK_API
    }

def handle_get_weather(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_weather
    Returns weather forecast for project location
    Note: Uses external wttr.in API (no authentication needed)
    """
    location = params.get('location')

    if not location:
        raise ValueError("Missing required parameter: location")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching weather for {location}")
        response = get_mock_weather(location)
    else:
        logger.info(f"[REAL] Fetching weather for {location}")
        # Weather API doesn't need authentication
        url = f"{config['weather_url']}/{location}?format=j1"
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        response = res.json()

    # Extract and format weather data
    current = response.get("current_condition", [{}])[0]
    forecast = response.get("weather", [])
    area = response.get("nearest_area", [{}])[0]

    weather_info = {
        "location": {
            "area": area.get("areaName", [{}])[0].get("value"),
            "region": area.get("region", [{}])[0].get("value"),
            "country": area.get("country", [{}])[0].get("value")
        },
        "current": {
            "temp_f": current.get("temp_F"),
            "temp_c": current.get("temp_C"),
            "condition": current.get("weatherDesc", [{}])[0].get("value"),
            "humidity": current.get("humidity"),
            "wind_mph": current.get("windspeedMiles"),
            "wind_dir": current.get("winddir16Point"),
            "feels_like_f": current.get("FeelsLikeF"),
            "uv_index": current.get("uvIndex")
        },
        "forecast": [
            {
                "date": day.get("date"),
                "max_temp_f": day.get("maxtempF"),
                "min_temp_f": day.get("mintempF"),
                "avg_temp_f": day.get("avgtempF"),
                "uv_index": day.get("uvIndex"),
                "sun_hours": day.get("sunHour")
            }
            for day in forecast[:3]  # Next 3 days
        ]
    }

    return {
        "action": "get_weather",
        "location": location,
        "weather": weather_info,
        "mock_mode": USE_MOCK_API
    }

# ============================================================================
# Lambda Handler
# ============================================================================

def lambda_handler(event, context):
    """
    Main Lambda handler for information actions
    Routes to appropriate action handler based on apiPath
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract action from event
        action = event.get('apiPath', '').lstrip('/')
        if not action:
            # Fallback: check for action in parameters
            params = extract_parameters(event)
            action = params.get('action', '').replace('_', '-')

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
            'get-project-details': handle_get_project_details,
            'get-appointment-status': handle_get_appointment_status,
            'get-working-hours': handle_get_working_hours,
            'get-weather': handle_get_weather
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
        "apiPath": "/get-project-details",
        "httpMethod": "POST",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }

    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))
