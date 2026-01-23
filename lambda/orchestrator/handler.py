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
from router import route_request, handle_welcome_request
from sms_formatter import format_for_sms

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
        pf_user_name = body.get('pf_user_name', '')  # User's display name for personalization
        channel = body.get('channel', 'chat')  # 'voice' or 'chat'
        caller_phone = body.get('caller_phone', '')  # For Vapi voice calls
        from_phone = body.get('from_phone', '')  # For voice cache lookup in scheduling-actions
        project_id = body.get('project_id', '')  # From GPT-4o smart prompt embedded state

        # Validate required parameters
        if not message:
            return create_error_response(400, "Missing required parameter: message")

        # VOICE/VAPI: If caller_phone is provided, look up credentials from DynamoDB
        if caller_phone and (not pf_client_id or not pf_user_id):
            phone_creds = get_phone_credentials(caller_phone)
            if phone_creds:
                pf_token = phone_creds.get('bearer_token', pf_token)
                pf_client_id = phone_creds.get('client_id', pf_client_id)
                pf_user_id = phone_creds.get('user_id', pf_user_id)
                pf_user_name = phone_creds.get('user_name', pf_user_name)
                logger.info(f"[VOICE_AUTH] Retrieved credentials for phone ***{caller_phone[-4:]}: user={pf_user_id}")
            else:
                logger.warning(f"[VOICE_AUTH] No credentials found for phone ***{caller_phone[-4:]}")

        # Phase 1+2 Architecture: pf_token is now optional (tokens come from Secrets Manager)
        # Only client_id and user_id are required
        if not pf_client_id or not pf_user_id:
            return create_error_response(400, "Missing authentication parameters: pf_client_id and pf_user_id required")

        logger.info(f"[REQUEST] session_id={session_id}, message='{message[:50]}...', channel={channel}, from_phone={'***'+from_phone[-4:] if from_phone else 'empty'}")

        # WELCOME FLOW: Detect __WELCOME__ signal from frontend after login
        logger.info(f"[DEBUG] message repr={repr(message)}, len={len(message)}, startswith='__'={message.startswith('__')}")
        if message == '__WELCOME__' or message.strip() == '__WELCOME__':
            logger.info(f"[WELCOME] Welcome request detected for user: {pf_user_name or pf_user_id}")
            result = handle_welcome_request(
                customer_id=pf_user_id,
                client_id=pf_client_id,
                pf_bearer_token=pf_token,
                user_name=pf_user_name,
                session_id=session_id
            )

            # FORMAT FOR SMS: Apply SMS-safe formatting for SMS channel
            if channel == 'sms':
                result['response'] = format_for_sms(result['response'])
                logger.info(f"[SMS] Welcome response formatted for SMS delivery")

            # IMPORTANT: Add welcome response to conversation history
            # So subsequent messages have context about which projects were shown
            conversation_manager = get_conversation_manager()
            conversation_manager.add_to_conversation_history(
                session_id,
                'assistant',
                result['response'],
                metadata={
                    'agent_name': 'Welcome',
                    'intent': 'welcome',
                    'action': 'welcome_with_projects',
                    'projects_shown': [p.get('id') for p in result.get('projects', [])]
                }
            )
            logger.info(f"[HISTORY] Added welcome response to conversation history")

            # Add status codes to the result
            result['pf_http_status_code'] = result.get('pf_http_status_code', 200)
            result['agenticscheduler_http_status_code'] = result.get('agenticscheduler_http_status_code', 200)
            logger.info(f"[WELCOME] Returning with status codes: pf={result['pf_http_status_code']}, agentic={result['agenticscheduler_http_status_code']}")
            return create_success_response(result)

        # Get conversation manager
        conversation_manager = get_conversation_manager()

        # Get conversation history for this session
        conversation_history = conversation_manager.get_conversation_history(session_id)
        logger.info(f"[SESSION] Session {session_id} has {len(conversation_history)} messages in history")

        # Add user message to history
        conversation_manager.add_to_conversation_history(session_id, 'user', message)

        # Route request (Direct Lambda or Bedrock Agent)
        result = route_request(
            message=message,
            session_id=session_id,
            customer_id=pf_user_id,
            client_id=pf_client_id,
            pf_bearer_token=pf_token,
            conversation_history=conversation_history,
            channel=channel,
            from_phone=from_phone,  # For voice cache lookup in scheduling-actions
            project_id=project_id  # From GPT-4o smart prompt embedded state
        )

        # Extract response components
        response_text = result['response']
        intent = result['intent']
        action = result.get('action')
        agent_name = result['agent_name']
        direct_call = result['direct_call']
        timing = result['timing']
        # Extract PF API status code if available from Lambda response
        pf_http_status_code = result.get('pf_http_status_code', 200)

        # FORMAT FOR SMS: Apply SMS-safe formatting for SMS channel
        # This strips emojis, markdown, and special unicode characters
        if channel == 'sms':
            response_text = format_for_sms(response_text)
            logger.info(f"[SMS] Response formatted for SMS delivery")

        logger.info(f"[OK] Response: agent={agent_name}, intent={intent}, direct={direct_call}, timing={timing.get('total', 0):.2f}s, pf_status={pf_http_status_code}")

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

        # Build response payload
        response_payload = {
            "response": response_text,
            "agent_name": agent_name,
            "intent": intent,
            "action": action,
            "session_id": session_id,
            "direct_call": direct_call,
            "performance": timing,
            "pf_http_status_code": pf_http_status_code,
            "agenticscheduler_http_status_code": 200
        }

        # Include confirmation fields if present (for chat scheduling confirmation flow)
        if result.get('confirmation_required'):
            response_payload['confirmation_required'] = True
            response_payload['pending_action'] = result.get('pending_action', {})

        # Return successful response with status codes
        return create_success_response(response_payload)

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


def create_error_response(status_code: int, error_message: str, pf_http_status_code: int = None) -> Dict[str, Any]:
    """
    Create API Gateway error response

    Args:
        status_code: HTTP status code
        error_message: Error message
        pf_http_status_code: ProjectForce API status code (optional)

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
            'error': error_message,
            'pf_http_status_code': pf_http_status_code,
            'agenticscheduler_http_status_code': status_code
        })
    }


def get_phone_credentials(phone_number: str) -> Dict[str, Any]:
    """
    Retrieve authenticated credentials from DynamoDB by phone number.
    Used when Vapi passes caller_phone to identify the authenticated user.

    Args:
        phone_number: Caller's phone number (e.g., "+15104137024" or "5104137024")

    Returns:
        Dict with bearer_token, client_id, user_id, user_name or None if not found
    """
    import boto3
    import time

    try:
        # Normalize phone number - strip to digits only
        phone_clean = ''.join(c for c in phone_number if c.isdigit())
        # Remove leading 1 for US numbers
        if len(phone_clean) == 11 and phone_clean.startswith('1'):
            phone_clean = phone_clean[1:]

        session_id = f"phone:{phone_clean}"

        # Get from DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        table = dynamodb.Table(os.environ.get('SESSIONS_TABLE', 'pf-syn-sessions-dev'))

        response = table.get_item(Key={'session_id': session_id})

        if 'Item' in response:
            item = response['Item']
            # Check TTL
            ttl = item.get('ttl', 0)
            if isinstance(ttl, str):
                ttl = int(ttl)
            if ttl > time.time():
                logger.info(f"[PHONE_AUTH] Found valid session for ***{phone_clean[-4:]}")
                return {
                    'bearer_token': item.get('bearer_token', ''),
                    'client_id': item.get('client_id', ''),
                    'user_id': item.get('user_id', ''),
                    'user_name': item.get('user_name', '')
                }
            else:
                logger.info(f"[PHONE_AUTH] Session expired for ***{phone_clean[-4:]}")
                return None
        else:
            logger.info(f"[PHONE_AUTH] No session found for ***{phone_clean[-4:]}")
            return None

    except Exception as e:
        logger.error(f"[PHONE_AUTH] Error looking up credentials: {e}")
        return None


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
