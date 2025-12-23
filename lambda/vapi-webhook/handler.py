"""
Lambda Function: VAPI Webhook Handler
Name: pf-syn-vapi-webhook-dev

Handles VAPI voice requests:
1. Authenticates caller via phone-call-login API (stores creds in Secrets Manager)
2. Routes messages to the orchestrator
3. Returns voice-formatted responses to VAPI

VAPI sends requests in this format:
{
    "message": {
        "type": "conversation-update" | "assistant-request" | "function-call" | etc,
        "call": {
            "id": "call-id",
            "customer": {"number": "+15104137024"},
            "phoneNumber": {"number": "+18338771422"}
        },
        "messages": [...]
    }
}

Environment Variables:
    ORCHESTRATOR_LAMBDA: Orchestrator Lambda function name (default: pf-syn-orchestrator-dev)
    ENVIRONMENT: Environment name (default: dev)
    AWS_REGION: AWS region (default: us-east-1)
    TWILIO_NUMBER: The Twilio number for this deployment (to_phone for auth)
"""

import json
import boto3
import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Import phone_auth module
try:
    from phone_auth import get_or_authenticate, AuthenticationError, normalize_phone
    PHONE_AUTH_AVAILABLE = True
except ImportError:
    PHONE_AUTH_AVAILABLE = False
    logger.warning("phone_auth module not available")

# Configuration
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
ORCHESTRATOR_LAMBDA = os.environ.get('ORCHESTRATOR_LAMBDA', f'pf-syn-orchestrator-{ENVIRONMENT}')
TWILIO_NUMBER = os.environ.get('TWILIO_NUMBER', '')  # Set in Lambda env vars

# AWS clients
lambda_client = boto3.client('lambda', region_name=AWS_REGION)

# Session cache (in-memory for Lambda warm starts)
_session_cache = {}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for VAPI webhook.

    Handles multiple VAPI message types:
    - assistant-request: User said something, needs response
    - function-call: VAPI wants to call a function
    - conversation-update: Status update (call started/ended)
    - end-of-call-report: Call summary
    """
    try:
        logger.info(f"[VAPI] Received event: {json.dumps(event)[:1000]}")

        # Handle Function URL format (body is JSON string)
        if 'body' in event:
            body = event['body']
            if isinstance(body, str):
                body = json.loads(body)
        else:
            body = event

        # Extract VAPI message
        message = body.get('message', body)
        message_type = message.get('type', 'unknown')

        logger.info(f"[VAPI] Message type: {message_type}")

        # Handle different message types
        if message_type == 'assistant-request':
            return handle_assistant_request(message)

        elif message_type == 'conversation-update':
            return handle_conversation_update(message)

        elif message_type == 'function-call':
            return handle_function_call(message)

        elif message_type == 'tool-calls':
            # VAPI sends tool-calls for OpenAI-style tool calling
            return handle_tool_calls(message)

        elif message_type == 'end-of-call-report':
            return handle_end_of_call(message)

        elif message_type == 'status-update':
            return handle_status_update(message)

        else:
            logger.warning(f"[VAPI] Unknown message type: {message_type}")
            return create_response(200, {"status": "ok"})

    except Exception as e:
        logger.error(f"[VAPI] Error: {e}", exc_info=True)
        return create_response(500, {"error": str(e)})


def handle_assistant_request(message: Dict) -> Dict:
    """
    Handle assistant-request: User spoke, generate response.

    This is the main conversation handler.
    """
    try:
        # Extract call info
        call = message.get('call', {})
        call_id = call.get('id', 'unknown')

        # Extract phone numbers
        customer = call.get('customer', {})
        phone_number = call.get('phoneNumber', {})

        from_phone = customer.get('number', '')
        to_phone = phone_number.get('number', '') or TWILIO_NUMBER

        logger.info(f"[VAPI] Call {call_id}: from={mask_phone(from_phone)}, to={mask_phone(to_phone)}")

        # Extract the latest user message
        messages = message.get('messages', [])
        user_message = extract_latest_user_message(messages)

        if not user_message:
            logger.warning("[VAPI] No user message found")
            return create_assistant_response("I didn't catch that. Could you please repeat?")

        logger.info(f"[VAPI] User message: {user_message[:100]}")

        # Authenticate user via phone
        credentials = authenticate_caller(from_phone, to_phone)

        if not credentials:
            logger.warning(f"[VAPI] Authentication failed for {mask_phone(from_phone)}")
            return create_assistant_response(
                "I couldn't verify your account. Please make sure you're calling from your registered phone number."
            )

        logger.info(f"[VAPI] Authenticated: user_id={credentials.get('user_id')}, name={credentials.get('user_name')}")

        # Call orchestrator
        response_text = call_orchestrator(
            message=user_message,
            call_id=call_id,
            credentials=credentials
        )

        return create_assistant_response(response_text)

    except Exception as e:
        logger.error(f"[VAPI] Error in assistant_request: {e}", exc_info=True)
        return create_assistant_response("I'm having trouble right now. Please try again.")


def handle_conversation_update(message: Dict) -> Dict:
    """
    Handle conversation-update: Call status changed.
    """
    call = message.get('call', {})
    call_id = call.get('id', 'unknown')
    status = call.get('status', 'unknown')

    logger.info(f"[VAPI] Conversation update: call={call_id}, status={status}")

    # Clear session cache on call end
    if status in ['ended', 'completed', 'failed']:
        if call_id in _session_cache:
            del _session_cache[call_id]
            logger.info(f"[VAPI] Cleared session cache for {call_id}")

    return create_response(200, {"status": "ok"})


def handle_function_call(message: Dict) -> Dict:
    """
    Handle function-call: VAPI wants to call a custom function.

    This is for VAPI's tool/function calling feature.
    The main function is 'projectforce_api' which routes to the orchestrator.
    """
    function_call = message.get('functionCall', {})
    function_name = function_call.get('name', 'unknown')
    parameters = function_call.get('parameters', {})

    # Extract call info for authentication
    call = message.get('call', {})
    call_id = call.get('id', 'unknown')
    customer = call.get('customer', {})
    phone_number = call.get('phoneNumber', {})
    from_phone = customer.get('number', '')
    to_phone = phone_number.get('number', '') or TWILIO_NUMBER

    logger.info(f"[VAPI] Function call: {function_name}, params={parameters}")
    logger.info(f"[VAPI] Call context: call_id={call_id}, from={mask_phone(from_phone)}")

    # Handle projectforce_api - the main tool for all project operations
    if function_name == 'projectforce_api':
        user_message = parameters.get('message', '')
        action = parameters.get('action', 'other')

        if not user_message:
            return create_function_response({
                "error": "No message provided",
                "response": "I didn't catch what you needed. Could you please repeat that?"
            })

        # Authenticate caller
        credentials = authenticate_caller(from_phone, to_phone)

        if not credentials:
            logger.warning(f"[VAPI] Authentication failed for {mask_phone(from_phone)}")
            return create_function_response({
                "error": "Authentication failed",
                "response": "I couldn't verify your account. Please make sure you're calling from your registered phone number."
            })

        logger.info(f"[VAPI] Authenticated: user_id={credentials.get('user_id')}, action={action}")

        # Call orchestrator with the user's message
        response_text = call_orchestrator(
            message=user_message,
            call_id=call_id,
            credentials=credentials
        )

        return create_function_response({
            "success": True,
            "response": response_text
        })

    # Handle legacy authenticate function
    elif function_name == 'authenticate':
        from_phone_param = parameters.get('from_phone', '') or from_phone
        to_phone_param = parameters.get('to_phone', TWILIO_NUMBER) or to_phone

        credentials = authenticate_caller(from_phone_param, to_phone_param)

        if credentials:
            return create_function_response({
                "success": True,
                "user_name": credentials.get('user_name', ''),
                "user_id": credentials.get('user_id', '')
            })
        else:
            return create_function_response({
                "success": False,
                "error": "Authentication failed"
            })

    # Default: unknown function
    logger.warning(f"[VAPI] Unknown function: {function_name}")
    return create_function_response({
        "error": f"Unknown function: {function_name}",
        "response": "I'm not sure how to help with that. Could you try rephrasing?"
    })


def handle_tool_calls(message: Dict) -> Dict:
    """
    Handle tool-calls: VAPI sends this for OpenAI-style tool calling.

    The toolCalls array contains the tool calls from the LLM.
    We process each and return results.
    """
    tool_calls = message.get('toolCalls', message.get('toolCallList', []))

    # Extract call info for authentication
    call = message.get('call', {})
    call_id = call.get('id', 'unknown')
    customer = call.get('customer', {})
    phone_number = call.get('phoneNumber', {})
    from_phone = customer.get('number', '')
    to_phone = phone_number.get('number', '') or TWILIO_NUMBER

    logger.info(f"[VAPI] Tool calls received: {len(tool_calls)} calls")
    logger.info(f"[VAPI] Call context: call_id={call_id}, from={mask_phone(from_phone)}")

    results = []

    for tool_call in tool_calls:
        tool_call_id = tool_call.get('id', '')
        function = tool_call.get('function', {})
        function_name = function.get('name', 'unknown')
        arguments_str = function.get('arguments', '{}')

        # Parse arguments
        try:
            arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
        except json.JSONDecodeError:
            arguments = {}

        logger.info(f"[VAPI] Tool call: {function_name}, args={arguments}")

        # Handle projectforce_api tool
        if function_name == 'projectforce_api':
            user_message = arguments.get('message', '')
            action = arguments.get('action', 'other')

            if not user_message:
                results.append({
                    "toolCallId": tool_call_id,
                    "result": json.dumps({
                        "error": "No message provided",
                        "response": "I didn't catch what you needed. Could you please repeat that?"
                    })
                })
                continue

            # Authenticate caller
            credentials = authenticate_caller(from_phone, to_phone)

            if not credentials:
                logger.warning(f"[VAPI] Authentication failed for {mask_phone(from_phone)}")
                results.append({
                    "toolCallId": tool_call_id,
                    "result": json.dumps({
                        "error": "Authentication failed",
                        "response": "I couldn't verify your account. Please make sure you're calling from your registered phone number."
                    })
                })
                continue

            logger.info(f"[VAPI] Authenticated: user_id={credentials.get('user_id')}, action={action}")

            # Call orchestrator
            response_text = call_orchestrator(
                message=user_message,
                call_id=call_id,
                credentials=credentials
            )

            results.append({
                "toolCallId": tool_call_id,
                "result": json.dumps({
                    "success": True,
                    "response": response_text
                })
            })

        else:
            logger.warning(f"[VAPI] Unknown tool: {function_name}")
            results.append({
                "toolCallId": tool_call_id,
                "result": json.dumps({
                    "error": f"Unknown tool: {function_name}",
                    "response": "I'm not sure how to help with that."
                })
            })

    # Return results in VAPI format
    return create_response(200, {"results": results})


def handle_end_of_call(message: Dict) -> Dict:
    """
    Handle end-of-call-report: Call ended, cleanup.
    """
    call = message.get('call', {})
    call_id = call.get('id', 'unknown')

    # Get call summary
    summary = message.get('summary', '')
    duration = message.get('durationSeconds', 0)

    logger.info(f"[VAPI] Call ended: {call_id}, duration={duration}s")

    # Clear cache
    if call_id in _session_cache:
        del _session_cache[call_id]

    return create_response(200, {"status": "ok"})


def handle_status_update(message: Dict) -> Dict:
    """Handle status-update messages."""
    status = message.get('status', {})
    logger.info(f"[VAPI] Status update: {status}")
    return create_response(200, {"status": "ok"})


def authenticate_caller(from_phone: str, to_phone: str) -> Optional[Dict]:
    """
    Authenticate caller using phone-call-login API.

    Stores credentials in Secrets Manager for future use.
    """
    if not PHONE_AUTH_AVAILABLE:
        logger.error("[VAPI] phone_auth module not available")
        return None

    if not from_phone:
        logger.error("[VAPI] Missing from_phone")
        return None

    # Use configured Twilio number if to_phone not provided
    if not to_phone:
        to_phone = TWILIO_NUMBER

    if not to_phone:
        logger.error("[VAPI] Missing to_phone and TWILIO_NUMBER not configured")
        return None

    try:
        credentials = get_or_authenticate(from_phone, to_phone)
        return credentials

    except AuthenticationError as e:
        logger.error(f"[VAPI] Authentication error: {e}")
        return None

    except Exception as e:
        logger.error(f"[VAPI] Unexpected auth error: {e}", exc_info=True)
        return None


def call_orchestrator(message: str, call_id: str, credentials: Dict) -> str:
    """
    Call the orchestrator Lambda with the user's message.
    """
    try:
        # Build orchestrator payload
        payload = {
            'body': json.dumps({
                'message': message,
                'session_id': f"vapi-{call_id}",
                'pf_token': credentials.get('bearer_token', ''),
                'pf_client_id': credentials.get('client_id', ''),
                'pf_user_id': credentials.get('user_id', ''),
                'pf_user_name': credentials.get('user_name', ''),
                'channel': 'voice'
            })
        }

        logger.info(f"[VAPI] Calling orchestrator: {ORCHESTRATOR_LAMBDA}")

        response = lambda_client.invoke(
            FunctionName=ORCHESTRATOR_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())
        logger.info(f"[VAPI] Orchestrator response: status={result.get('statusCode')}")

        if result.get('statusCode') == 200:
            body = result.get('body', '{}')
            if isinstance(body, str):
                body = json.loads(body)

            response_text = body.get('response', "I'm not sure how to help with that.")

            # Format for voice (remove markdown, etc.)
            response_text = format_for_voice(response_text)

            return response_text

        else:
            error = result.get('body', {})
            if isinstance(error, str):
                error = json.loads(error) if error.startswith('{') else {'error': error}

            error_msg = error.get('error', 'Unknown error')
            logger.error(f"[VAPI] Orchestrator error: {error_msg}")

            return "I'm having trouble processing that. Could you try again?"

    except Exception as e:
        logger.error(f"[VAPI] Error calling orchestrator: {e}", exc_info=True)
        return "I'm experiencing technical difficulties. Please try again in a moment."


def extract_latest_user_message(messages: list) -> Optional[str]:
    """
    Extract the latest user message from VAPI messages array.
    """
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            return msg.get('content', msg.get('message', ''))

    return None


def format_for_voice(text: str) -> str:
    """
    Format text for voice output.

    - Remove markdown
    - Clean up formatting
    - Keep it concise
    """
    import re

    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'`([^`]+)`', r'\1', text)        # `code`
    text = re.sub(r'#{1,6}\s*', '', text)           # # headers

    # Remove JSON/code blocks
    text = re.sub(r'```json.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

    # Clean up newlines
    text = text.replace('\n\n', '. ')
    text = text.replace('\n', ' ')

    # Clean up spacing
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\.+', '.', text)
    text = text.strip()

    # Limit length for voice
    MAX_LENGTH = 500
    if len(text) > MAX_LENGTH:
        truncated = text[:MAX_LENGTH]
        last_period = truncated.rfind('.')
        if last_period > MAX_LENGTH * 0.7:
            text = text[:last_period + 1]
        else:
            text = truncated + "..."

    return text


def mask_phone(phone: str) -> str:
    """Mask phone for logging."""
    if not phone:
        return 'unknown'
    if len(phone) > 4:
        return '*' * (len(phone) - 4) + phone[-4:]
    return '****'


def create_response(status_code: int, body: Dict) -> Dict:
    """Create HTTP response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }


def create_assistant_response(message: str) -> Dict:
    """
    Create VAPI assistant response format.

    VAPI expects:
    {
        "assistant": {
            "content": "response text"
        }
    }
    """
    return create_response(200, {
        "assistant": {
            "content": message
        }
    })


def create_function_response(result: Dict) -> Dict:
    """
    Create VAPI function call response format.

    VAPI expects:
    {
        "result": { ... }
    }
    """
    return create_response(200, {
        "result": result
    })
