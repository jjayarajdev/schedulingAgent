"""
Orchestrator Lambda Handler
Main entry point for API Gateway requests
Routes to Direct Lambda or Bedrock Agents based on classification
"""
import json
import logging
import os
from typing import Dict, Any

from config import get_config
from conversation import get_conversation_manager
from router import route_request

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for API Gateway requests

    Expected Event Format (API Gateway Lambda Proxy Integration):
    {
        "body": "{\"message\": \"...\", \"session_id\": \"...\", ...}",
        "headers": {...},
        "requestContext": {...}
    }

    Request Body:
    {
        "message": "User message",
        "session_id": "session-id",
        "pf_token": "bearer-token",
        "pf_client_id": "client-id",
        "pf_user_id": "user-id"
    }

    Returns:
        API Gateway response with statusCode, headers, and body
    """
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        # Extract request parameters
        message = body.get('message', '')
        session_id = body.get('session_id', 'session-default')
        pf_token = body.get('pf_token', '')
        pf_client_id = body.get('pf_client_id', '')
        pf_user_id = str(body.get('pf_user_id', ''))

        # Validate required parameters
        if not message:
            return create_error_response(400, "Missing required parameter: message")

        if not pf_token or not pf_client_id or not pf_user_id:
            return create_error_response(400, "Missing authentication parameters")

        logger.info(f"🚀 Request: session_id={session_id}, message='{message[:50]}...'")

        # Get conversation manager
        conversation_manager = get_conversation_manager()

        # Get conversation history for this session
        conversation_history = conversation_manager.get_conversation_history(session_id)
        logger.info(f"📚 Session {session_id} has {len(conversation_history)} messages in history")

        # Add user message to history
        conversation_manager.add_to_conversation_history(session_id, 'user', message)

        # Route request (Direct Lambda or Bedrock Agent)
        result = route_request(
            message=message,
            session_id=session_id,
            customer_id=pf_user_id,
            client_id=pf_client_id,
            pf_bearer_token=pf_token,
            conversation_history=conversation_history
        )

        # Extract response components
        response_text = result['response']
        intent = result['intent']
        action = result.get('action')
        agent_name = result['agent_name']
        direct_call = result['direct_call']
        timing = result['timing']

        logger.info(f"✅ Response: agent={agent_name}, intent={intent}, direct={direct_call}, timing={timing.get('total', 0):.2f}s")

        # Add assistant response to conversation history
        conversation_manager.add_to_conversation_history(
            session_id,
            'assistant',
            response_text,
            metadata={
                'agent_name': agent_name,
                'intent': intent,
                'action': action,
                'direct_call': direct_call,
                'performance': timing
            }
        )

        # Return successful response
        return create_success_response({
            "response": response_text,
            "agent_name": agent_name,
            "intent": intent,
            "action": action,
            "session_id": session_id,
            "direct_call": direct_call,
            "performance": timing
        })

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return create_error_response(400, f"Invalid JSON: {str(e)}")

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return create_error_response(400, str(e))

    except Exception as e:
        logger.error(f"Orchestrator error: {e}", exc_info=True)
        return create_error_response(500, f"Internal server error: {str(e)}")


def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create API Gateway success response

    Args:
        data: Response data dictionary

    Returns:
        API Gateway response with statusCode 200
    """
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps(data)
    }


def create_error_response(status_code: int, error_message: str) -> Dict[str, Any]:
    """
    Create API Gateway error response

    Args:
        status_code: HTTP status code
        error_message: Error message

    Returns:
        API Gateway response with error status
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps({
            'error': error_message
        })
    }


def health_check_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Health check endpoint handler

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        Health check response
    """
    try:
        config = get_config()
        conversation_manager = get_conversation_manager()

        # Get session count
        active_sessions = conversation_manager.get_session_count()

        return create_success_response({
            "status": "ok",
            "service": "orchestrator-lambda",
            "active_sessions": active_sessions,
            "routing_method": config.routing_method,
            "features": {
                "direct_lambda": config.allow_direct_lambda,
                "supervisor": config.use_supervisor,
                "redis": bool(config.redis_endpoint)
            }
        })

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return create_error_response(500, f"Health check failed: {str(e)}")
