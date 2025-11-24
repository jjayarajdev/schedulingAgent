"""
Notes Actions Lambda Handler
Handles 2 notes-related actions for Bedrock Agent

Actions:
1. add_note - Add a note to a project
2. list_notes - List all notes for a project

Supports both MOCK and REAL API modes via USE_MOCK_API environment variable
Note: list_notes API may not exist in PF360, using DynamoDB as fallback
"""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError

# Import configuration and mock data
from config import (
    USE_MOCK_API,
    get_api_config,
    get_auth_headers
)
from mock_data import (
    get_mock_add_note,
    get_mock_list_notes
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB client
dynamodb = boto3.resource('dynamodb')

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
                properties = app_json['properties']
                if isinstance(properties, list):
                    params = {p['name']: p['value'] for p in properties}
                else:
                    params = properties
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
        logger.error(f"Error extracting parameters: {str(e)}", exc_info=True)
        return {}

def format_success_response(event: Dict, action: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Format successful response for Bedrock Agent"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'notes'),
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
            'actionGroup': event.get('actionGroup', 'notes'),
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
# DynamoDB Helper Functions
# ============================================================================

def store_note_in_dynamodb(table_name: str, project_id: str, note_text: str, author: str) -> Dict[str, Any]:
    """Store note in DynamoDB"""
    table = dynamodb.Table(table_name)

    note = {
        'project_id': project_id,
        'timestamp': datetime.now().isoformat(),
        'note_text': note_text,
        'author': author,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    table.put_item(Item=note)
    return note

def get_notes_from_dynamodb(table_name: str, project_id: str) -> List[Dict[str, Any]]:
    """Retrieve notes from DynamoDB"""
    table = dynamodb.Table(table_name)

    try:
        response = table.query(
            KeyConditionExpression='project_id = :pid',
            ExpressionAttributeValues={
                ':pid': project_id
            },
            ScanIndexForward=False  # Sort by timestamp descending
        )
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"DynamoDB query failed: {str(e)}")
        return []

# ============================================================================
# Action Handlers
# ============================================================================

def handle_add_note(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: add_note
    Add a note to a project
    """
    project_id = params.get('project_id')
    note_text = params.get('note_text')
    author = params.get('author', 'Agent')

    if not all([project_id, note_text]):
        raise ValueError("Missing required parameters: project_id, note_text")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Adding note to project {project_id}")
        response = get_mock_add_note(project_id, note_text, author)
    else:
        logger.info(f"[REAL] Adding note to project {project_id}")
        url = config['add_note_url']

        payload = {
            "project_id": project_id,
            "note": note_text,
            "author": author,
            "created_at": datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        }

        try:
            res = requests.post(url, headers=auth_headers, json=payload, timeout=30)
            res.raise_for_status()
            response = res.json()
        except requests.RequestException as e:
            # If API fails, fallback to DynamoDB
            logger.warning(f"Add note API failed, using DynamoDB fallback: {str(e)}")
            note = store_note_in_dynamodb(config['dynamodb_table'], project_id, note_text, author)
            response = {
                "status": "success",
                "message": "Note added (stored in DynamoDB)",
                "data": note
            }

    return {
        "action": "add_note",
        "project_id": project_id,
        "note_text": note_text,
        "author": author,
        "message": response.get("message", "Note added successfully"),
        "note_data": response.get("data", {}),
        "mock_mode": USE_MOCK_API
    }

def handle_list_notes(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: list_notes
    List all notes for a project
    Note: PF360 API for listing notes may not exist, using DynamoDB fallback
    """
    project_id = params.get('project_id')

    if not project_id:
        raise ValueError("Missing required parameter: project_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Listing notes for project {project_id}")
        response = get_mock_list_notes(project_id)
    else:
        logger.info(f"[REAL] Listing notes for project {project_id}")

        # Try PF360 API first
        try:
            url = f"{config['list_notes_url']}?project_id={project_id}"
            res = requests.get(url, headers=auth_headers, timeout=30)
            res.raise_for_status()
            response = res.json()
        except requests.RequestException as e:
            # If API doesn't exist or fails, use DynamoDB
            logger.warning(f"List notes API not available, using DynamoDB: {str(e)}")
            notes = get_notes_from_dynamodb(config['dynamodb_table'], project_id)
            response = {
                "status": "success",
                "data": {
                    "project_id": project_id,
                    "notes": notes,
                    "total_count": len(notes),
                    "source": "dynamodb"
                }
            }

    data = response.get("data", {})
    return {
        "action": "list_notes",
        "project_id": project_id,
        "notes": data.get("notes", []),
        "total_count": data.get("total_count", 0),
        "source": data.get("source", "api"),
        "mock_mode": USE_MOCK_API
    }

# ============================================================================
# Lambda Handler
# ============================================================================

def lambda_handler(event, context):
    """
    Main Lambda handler for notes actions
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
            'add-note': handle_add_note,
            'list-notes': handle_list_notes
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
        "apiPath": "/add-note",
        "httpMethod": "POST",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "note_text", "value": "Test note from Lambda handler"},
            {"name": "author", "value": "Test Agent"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }

    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))
