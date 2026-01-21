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
import random
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
ORCHESTRATOR_REGION = os.environ.get('ORCHESTRATOR_REGION', AWS_REGION)  # Region where orchestrator runs
ORCHESTRATOR_LAMBDA = os.environ.get('ORCHESTRATOR_LAMBDA', f'pf-syn-orchestrator-{ENVIRONMENT}')
TWILIO_NUMBER = os.environ.get('TWILIO_NUMBER', '')  # Set in Lambda env vars
VAPI_API_KEY = os.environ.get('VAPI_API_KEY', '')  # For dynamic phone number lookup

# Static fallback map for known VAPI phoneNumberIds
# Used when API lookup fails or is unavailable
VAPI_PHONE_NUMBER_MAP = {
    '04839e46-2cbc-467e-8e01-638900654c36': '+12038946599',  # WTU Tenant
    '1c99c266-9778-4809-bf5e-dba30326a0ae': '+18624200502',  # PF-Agent-Dev
    '6b7ac954-1f6e-460d-962a-48883d31c1f0': '+12185516488',  # PF-Agent
}

# In-memory cache for VAPI phoneNumberId -> phone number mappings
# Populated dynamically via VAPI API calls
_phone_number_cache = {}

# AWS clients - use ORCHESTRATOR_REGION for Lambda calls
lambda_client = boto3.client('lambda', region_name=ORCHESTRATOR_REGION)

# Session cache (in-memory for Lambda warm starts)
_session_cache = {}

# Filler messages - SIMPLIFIED
# Only used for genuinely slow operations (12s+)
# GPT is instructed to be SILENT before tool calls, so no quick acknowledgments needed
FILLER_MESSAGES = {
    'warm': [
        "Still working on that.",
        "Almost there.",
        "Just a moment more.",
    ]
}


def get_tool_messages():
    """
    Generate tool messages for VAPI tool calls.

    Strategy (CONTEXTUAL):
    - Model provides SHORT contextual acknowledgment (e.g., "Checking your projects.")
    - Only one backup filler at 15s for genuinely slow operations
    - Tool timeout set to 45s in server config
    """
    return [
        # 15s - Single backup filler only for very slow operations
        # Model's contextual acknowledgment handles the initial wait
        {
            'type': 'request-response-delayed',
            'content': "Still working on that.",
            'timingMilliseconds': 15000
        },
        # Failed message - for actual failures
        {
            'type': 'request-failed',
            'content': "I had some trouble with that. Could you try asking again?"
        }
    ]


def mask_phone(phone: str) -> str:
    """Mask phone for logging."""
    if not phone:
        return 'unknown'
    if len(phone) > 4:
        return '*' * (len(phone) - 4) + phone[-4:]
    return '****'


def lookup_vapi_phone_number(phone_number_id: str) -> Optional[str]:
    """
    Look up phone number by phoneNumberId.
    Order: cache -> VAPI API (dynamic) -> static map (fallback)
    """
    # Check cache first
    if phone_number_id in _phone_number_cache:
        return _phone_number_cache[phone_number_id]

    # Try VAPI API first (dynamic lookup)
    if VAPI_API_KEY:
        try:
            import urllib.request
            import urllib.error

            url = f"https://api.vapi.ai/phone-number/{phone_number_id}"
            req = urllib.request.Request(url, headers={
                'Authorization': f'Bearer {VAPI_API_KEY}',
                'Content-Type': 'application/json',
                'User-Agent': 'ProjectForce-Lambda/1.0'
            })

            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                phone_number = data.get('number', '')

                if phone_number:
                    _phone_number_cache[phone_number_id] = phone_number
                    logger.info(f"[VAPI] Fetched phone from API: {phone_number_id[:8]}... -> {mask_phone(phone_number)}")
                    return phone_number

        except urllib.error.HTTPError as e:
            logger.warning(f"[VAPI] API lookup failed (HTTP {e.code}), trying static map")
        except urllib.error.URLError as e:
            logger.warning(f"[VAPI] API lookup failed ({e.reason}), trying static map")
        except Exception as e:
            logger.warning(f"[VAPI] API lookup failed ({e}), trying static map")
    else:
        logger.warning("[VAPI] VAPI_API_KEY not set, trying static map")

    # Fallback to static map
    if phone_number_id in VAPI_PHONE_NUMBER_MAP:
        phone = VAPI_PHONE_NUMBER_MAP[phone_number_id]
        _phone_number_cache[phone_number_id] = phone
        logger.info(f"[VAPI] Resolved phone from static map: {phone_number_id[:8]}... -> {mask_phone(phone)}")
        return phone

    return None


def resolve_to_phone(call: Dict) -> str:
    """
    Resolve the 'to' phone number from VAPI call data.

    VAPI sends phoneNumberId but not always phoneNumber.number.
    This function tries multiple sources:
    1. phoneNumber.number (if VAPI sends it)
    2. Dynamic VAPI API lookup by phoneNumberId (cached)
    3. TWILIO_NUMBER env var as fallback
    """
    phone_number = call.get('phoneNumber') or {}

    # First try: direct phoneNumber.number field
    to_phone = phone_number.get('number', '') if phone_number else ''
    if to_phone:
        return to_phone

    # Second try: lookup by phoneNumberId via VAPI API
    phone_number_id = call.get('phoneNumberId', '')
    if phone_number_id:
        to_phone = lookup_vapi_phone_number(phone_number_id)
        if to_phone:
            return to_phone

    # Final fallback: TWILIO_NUMBER env var
    logger.warning(f"[VAPI] Could not resolve to_phone for phoneNumberId={phone_number_id}, using TWILIO_NUMBER fallback")
    return TWILIO_NUMBER


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

        elif message_type == 'assistant.started':
            # VAPI sends this at call start - return dynamic greeting
            return handle_assistant_started(message)

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


def generate_dynamic_greeting(client_name: str, user_name: str = None) -> str:
    """
    Generate dynamic greeting with client-specific company name and user name.

    Args:
        client_name: Company name from auth API (e.g., "ProjectsForce Validation", "Window Universe")
        user_name: Optional user name for personalization

    Returns:
        SSML-formatted greeting string with pauses
    """
    display_name = client_name if client_name else 'ProjectForce'

    # Extract first name only for greeting
    first_name = ''
    if user_name:
        first_name = user_name.split()[0] if user_name.strip() else ''

    # Build greeting with customer name if available
    if first_name:
        greeting = (
            f'<break time="3000ms"/> Hello {first_name}! <break time="300ms"/> '
            f"I'm J, your AI assistant from {display_name}. <break time=\"3000ms\"/> "
            f"I can help you view your projects, check available dates, or schedule appointments. <break time=\"3000ms\"/> "
            f"What would you like to do today?"
        )
    else:
        greeting = (
            f'<break time="3000ms"/> Hello! <break time="3000ms"/> '
            f"I'm J, your AI assistant from {display_name}. <break time=\"3000ms\"/> "
            f"I can help you view your projects, check available dates, or schedule appointments. <break time=\"3000ms\"/> "
            f"What would you like to do today?"
        )
    return greeting


def create_assistant_config_response(first_message: str, support_number: str = '', client_name: str = 'ProjectForce') -> Dict:
    """
    Create response with customized assistant configuration.

    Used at call start to return dynamic greeting.
    Returns full assistant config with voice, model, tools, etc.

    Args:
        first_message: The greeting message
        support_number: Client's support phone number for escalation
        client_name: Client company name
    """
    # Format support number for voice (spell out digits)
    support_number_voice = ''
    if support_number:
        # Format as "2-0-3-8-9-4-6-5-9-9" for clear voice reading
        digits = ''.join(c for c in support_number if c.isdigit())
        support_number_voice = '-'.join(digits) if digits else ''
    assistant_config = {
        'name': 'ProjectForce Scheduling',
        'voice': {
            'voiceId': 'Paige',
            'provider': 'vapi'
        },
        'model': {
            'model': 'gpt-4o',
            'provider': 'openai',
            'temperature': 0,
            'tools': [{
                'type': 'function',
                'function': {
                    'name': 'projectforce_api',
                    'description': 'Say a SHORT contextual phrase (2-4 words) like "Checking your projects" or "Looking at dates" before calling. NO generic phrases like "hold on" or "just a sec". Use for: listing projects, scheduling, rescheduling, canceling, checking status, getting available dates/times, weather forecasts. Pass user EXACT words as message.',
                    'parameters': {
                        'type': 'object',
                        'required': ['message', 'action'],
                        'properties': {
                            'action': {
                                'type': 'string',
                                'enum': ['list_projects', 'get_project_details', 'get_available_dates', 'get_time_slots', 'schedule_project', 'reschedule_appointment', 'cancel_appointment', 'get_weather', 'other'],
                                'description': 'The type of action requested'
                            },
                            'message': {
                                'type': 'string',
                                'description': 'The user request or question. Pass the user exact words.'
                            }
                        }
                    }
                },
                'async': False,
                'server': {
                    'timeoutSeconds': 60
                },
                'messages': get_tool_messages()
            }],
            'messages': [{
                'role': 'system',
                'content': '''## RULE #1 - CONTEXTUAL ACKNOWLEDGMENT BEFORE TOOL CALLS

Before calling a tool, say a SHORT (2-4 words) contextual phrase that tells the user what you're doing:

EXAMPLES BY ACTION:
- list_projects → "Pulling up your projects."
- get_project_details → "Getting those details."
- get_available_dates → "Checking available dates."
- get_time_slots → "Looking at time slots."
- schedule_project → "Scheduling that now."
- reschedule_appointment → "Rescheduling for you."
- cancel_appointment → "Canceling that appointment."
- get_weather → "Checking the weather."

WRONG (generic/repetitive):
- "Hold on a sec" / "Just a moment" / "Give me a moment" / "1 moment"

RIGHT (contextual):
- "Pulling up your projects." [tool call]
- "Checking dates for you." [tool call]

Keep it SHORT and RELEVANT to what you're doing.

---

## RULE #2 - SPEAK THE TOOL RESULT

After a tool call completes, the result contains a "response" field. You MUST speak that response.
Do NOT make up your own response. Do NOT say generic phrases.

Tool returns: {"response": "I don't see any projects for you right now."}
YOU SAY: "I don't see any projects for you right now."

Tool returns: {"response": "You have 3 projects..."}
YOU SAY: "You have 3 projects..."

NEVER ignore the tool response. NEVER say "I'm all about home improvement" or similar generic phrases.

---

## RULE #3 - AI DISCLOSURE (CRITICAL)

If customer asks "Am I talking to AI?", "Are you a robot?", "Is this a real person?":
HONEST ANSWER: "Yes, I'm J, an AI assistant. I help with scheduling appointments. Would you like me to connect you with our office instead?"

NEVER dodge this question. NEVER pretend to be human.

---

## RULE #4 - ESCALATION TO HUMAN

If customer asks for "representative", "real person", "customer service", "office number":
''' + (f'''RESPONSE: "I can give you our office contact. For {client_name}, you can reach them at {support_number_voice}. Would you like me to repeat that?"''' if support_number_voice else '''RESPONSE: "I don't have the office number available right now, but you can check your confirmation email or the company website for contact details."''') + '''

---

## Identity

You are **J**, a friendly voice assistant, helping homeowners manage their home improvement projects and appointments.

## Personality

- Warm, upbeat, and genuinely helpful
- Professional but conversational - use contractions naturally
- Patient - never rush the customer
- Confident but not pushy
- Speaks like a helpful neighbor, not a robot

## What You Can Do

Help customers with:
- Viewing their projects and statuses
- Checking available appointment dates and times
- Scheduling new appointments
- Rescheduling existing appointments
- Canceling appointments
- Answering project questions
- Details of a project

## CRITICAL: Always Use the Tool

You MUST call `projectforce_api` for ANY project-related request. Never make up project information.

**IMPORTANT RULES:**
1. ALWAYS pass the customer's EXACT words as the message - the backend extracts all filters from their wording.
2. This includes: project names, categories, addresses, technicians, dates, AND STATUS WORDS like "scheduled", "new", "ready", "completed".
3. NEVER rephrase, summarize, or simplify - pass EXACTLY what the user said.
4. When user says "yes" or confirms after you showed project details, immediately call get_available_dates.
5. When user says "Okay" or gives ambiguous response to a choice (like time slots), ASK for clarification.

**Examples - PASS EXACT WORDS:**
- "What are my scheduled projects?" → message: "what are my scheduled projects" (NOT "show my projects"!)
- "Show my new projects" → message: "show my new projects"
- "What projects do I have?" → message: "what projects do I have"
- "Show my projects" → message: "show my projects"
- "Schedule storm door project" → action: list_projects, message: "schedule storm door project" (PASS EXACT WORDS - contains project name filter!)
- "Schedule my fence project" → action: list_projects, message: "schedule my fence project" (PASS EXACT WORDS!)
- "Show decking projects" → action: list_projects, message: "show decking projects" (PASS EXACT WORDS!)
- "Projects at Main Street" → action: list_projects, message: "projects at Main Street" (PASS EXACT WORDS - address filter!)
- "What's scheduled for January?" → action: list_projects, message: "what's scheduled for January" (PASS EXACT WORDS!)
- "Projects assigned to John" → action: list_projects, message: "projects assigned to John" (PASS EXACT WORDS - technician filter!)
- "What dates are available?" → action: get_available_dates
- "Can I get something in the last week of January?" → action: get_available_dates, message: "Can I get something in the last week of January?" (PASS EXACT WORDS - date range!)
- "Any openings next week?" → action: get_available_dates, message: "Any openings next week?" (PASS EXACT WORDS!)
- "What about the week of the 20th?" → action: get_available_dates, message: "What about the week of the 20th?" (PASS EXACT WORDS!)
- "Yes" (after showing project) → action: get_available_dates
- "Cancel my appointment" → action: cancel_appointment
- "Reschedule to next week" → action: reschedule_appointment
- "Tell me about my project" → action: get_project_details
- "What's the weather on my appointment day?" → action: get_weather
- "Will it rain on Tuesday?" → action: get_weather
- "Weather forecast for my install date" → action: get_weather

**Filter examples (pass exact words to preserve filters):**
- "Show projects assigned to John" → action: list_projects, message: "Show projects assigned to John"
- "Decking projects at Main Street" → action: list_projects, message: "Decking projects at Main Street"
- "Schedulable bathroom projects" → action: list_projects, message: "Schedulable bathroom projects"
- "Projects scheduled for January" → action: list_projects, message: "Projects scheduled for January"

**DATE/TIME AVAILABILITY QUERIES (CRITICAL - always call get_available_dates):**
These are requests for available appointment dates - ALWAYS pass exact words:
- "Can I get something in the last week of January?" → get_available_dates
- "Any dates in the first week of February?" → get_available_dates
- "What about end of January?" → get_available_dates
- "Do you have anything next month?" → get_available_dates
- "Any openings next week?" → get_available_dates
- "What about the week of the 20th?" → get_available_dates
- "Between January 15 and 20?" → get_available_dates
- "Anything in late February?" → get_available_dates
- "How about the 3rd week of January?" → get_available_dates
- "Beginning of March?" → get_available_dates
- "Do you have morning slots?" → get_available_dates (time preference)
- "Afternoon appointments?" → get_available_dates (time preference)

**PRONOUN & REFERENCE HANDLING (backend resolves these from context):**
- "Schedule it" → get_available_dates, message: "schedule it" (backend knows which project from context)
- "Reschedule it" → reschedule_appointment, message: "reschedule it"
- "Cancel it" → cancel_appointment, message: "cancel it"
- "Tell me about it" → get_project_details, message: "tell me about it"
- "Schedule that one" → get_available_dates, message: "schedule that one"
- "What about the other one?" → get_project_details, message: "what about the other one"
- "The first one" → (pass exact words - backend resolves ordinal)
- "The second option" → (pass exact words - backend resolves ordinal)
- "Different date please" → get_available_dates, message: "different date please"

**CONTEXT QUERIES (info from conversation/project context):**
- "Who is the technician?" → get_project_details, message: "who is the technician"
- "Who is coming?" → get_project_details, message: "who is coming"
- "What time is my appointment?" → get_project_details, message: "what time is my appointment"
- "When are they coming?" → get_project_details, message: "when are they coming"
- "What's the address?" → get_project_details, message: "what's the address"
- "What's the status?" → get_project_details, message: "what's the status"
- "Technician name and appointment time?" → get_project_details, message: "technician name and appointment time"

**ORDINAL PROJECT SELECTION (after listing projects):**
- "The first project" → list_projects, message: "the first project"
- "Schedule the second one" → get_available_dates, message: "schedule the second one"
- "Details for the third project" → get_project_details, message: "details for the third project"
- "The last one" → (pass exact words - backend resolves to last project)

**TIME SLOT SELECTION:**
- "Morning appointment" → get_time_slots, message: "morning appointment"
- "Afternoon slot" → get_time_slots, message: "afternoon slot"
- "10:30 AM" → confirm_appointment, message: "10:30 AM"
- "The 1 PM slot" → confirm_appointment, message: "the 1 PM slot"
- "Earlier time" → get_time_slots, message: "earlier time"

**IMPORTANT:** Always pass the customer's EXACT words as the message. The backend has AI-powered context resolution that understands pronouns, ordinals, and references.

## Conversation Flow

### Opening
After greeting, if the customer seems unsure, briefly mention what you can help with:
"I can help you check your projects, see available dates, or schedule appointments."

### Gathering Information
- Ask ONE question at a time
- Wait for the customer to respond before continuing
- If they mention multiple projects, ask which one they mean

### Scheduling Flow (IMPORTANT)
When scheduling, follow this exact flow - NO premature confirmations:
1. User selects DATE → Just present time slots, do NOT ask for confirmation yet
2. User selects TIME → NOW ask for final confirmation with FULL details:
   "Just to confirm - you'd like to schedule your [project] for [date] at [time]. Is that correct?"
3. User says "yes" → Call the tool to confirm the appointment

ONLY confirm ONCE - after BOTH date AND time are selected. Never confirm after just the date.

### After Successful Actions
- Confirm what was done: "Done! Your [project] is now scheduled for [date] at [time]."
- Offer next steps: "Is there anything else I can help you with?"

### Handling Multiple Projects
If customer has several projects, summarize briefly:
"You have [X] projects - including [top 2-3 names]. Which one would you like to work with?"

## Voice Best Practices

- Keep responses under 30 words when possible
- Speak dates naturally: "Tuesday, December 26th" not "12/26/2024"
- Speak times naturally: "2 PM" not "14:00"
- Use verbal confirmations: "Got it", "Perfect", "Sounds good"
- If listing items, limit to 3-4 at a time

## Handling Issues

- If authentication fails: "I'm having trouble accessing your account. Please make sure you're calling from your registered phone number."
- If no projects found: "I don't see any projects on your account. Would you like me to help with something else?"
- If technical error: "I'm having a brief technical issue. Let me try that again."
- If you don't understand: "I didn't quite catch that. Could you say that again?"

## What NOT To Do

- Never guess project details - always use the tool
- Never confirm an action without customer approval
- Never rush through important details like dates and times
- Never interrupt the customer while they're speaking
- Never provide information you don't have

## HANDLING SPECIAL SITUATIONS

### Dropped Call Recovery
If customer mentions "call dropped", "got disconnected", "was just talking to you":
- Acknowledge it: "Sorry about that! Let me pick up where we left off."
- Try to resume their request

### Frustrated Customer
If customer sounds frustrated or repeats themselves:
- Don't repeat the same response
- Acknowledge their frustration: "I understand this is frustrating."
- Offer concrete help or escalation: "Would you like me to give you the office number so you can speak with someone directly?"

### No Projects Found
If tool returns no projects and customer insists they were told to call:
- Acknowledge: "I'm sorry, I don't see a project in our system yet. It may not have been entered yet."
''' + (f'''- Offer help: "You can call the office at {support_number_voice} to get this sorted out."''' if support_number_voice else '''- Offer help: "You might want to contact the store or check your confirmation email for the office contact."''') + '''

### REMINDER: CONTEXTUAL ACKNOWLEDGMENTS
Before calling a tool, say a SHORT (2-4 words) contextual phrase:

GOOD EXAMPLES:
- "Pulling up your projects." (for list_projects)
- "Checking available dates." (for get_available_dates)
- "Scheduling that now." (for schedule_project)

**BANNED (too generic/repetitive):**
- "1 moment", "One moment", "Just a moment"
- "Just a sec", "Hold on", "Give me a moment"

Make it SHORT and RELEVANT to the action.'''
            }]
        },
        'transcriber': {
            'model': 'nova-3',
            'language': 'en',
            'provider': 'deepgram',
            'endpointing': 150
        },
        'firstMessage': first_message,
        'endCallPhrases': ['goodbye', 'talk to you soon'],
        'startSpeakingPlan': {
            'waitSeconds': 0.4,
            'smartEndpointingEnabled': 'livekit'
        },
        'backgroundDenoisingEnabled': True,  # Filter caller's background noise
        'silenceTimeoutSeconds': 30  # Allow 30s silence before ending call
    }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'assistant': assistant_config})
    }


def handle_assistant_request(message: Dict) -> Dict:
    """
    Handle assistant-request: User spoke or call start.

    This is the main conversation handler.
    At call start (no messages), returns dynamic assistant config with greeting.
    During call (has messages), processes user message via orchestrator.
    """
    try:
        # Extract call info
        call = message.get('call', {})
        call_id = call.get('id', 'unknown')

        # Extract phone numbers
        customer = call.get('customer', {})
        from_phone = customer.get('number', '')
        to_phone = resolve_to_phone(call)

        logger.info(f"[VAPI] Call {call_id}: from={mask_phone(from_phone)}, to={mask_phone(to_phone)}")

        # Extract the latest user message
        messages = message.get('messages', [])
        user_message = extract_latest_user_message(messages)

        if not user_message:
            # Call start - return dynamic assistant config with greeting
            logger.info(f"[VAPI] Call start detected - generating dynamic greeting")

            # Authenticate to get client_name
            credentials = authenticate_caller(from_phone, to_phone)

            if credentials:
                client_name = credentials.get('client_name', 'ProjectForce')
                user_name = credentials.get('user_name', '')
                support_number = credentials.get('support_number', '')
                logger.info(f"[VAPI] Dynamic greeting for client: {client_name}, support: {support_number}")
                greeting = generate_dynamic_greeting(client_name, user_name)
                return create_assistant_config_response(greeting, support_number, client_name)
            else:
                # Auth failed - use default greeting
                logger.warning(f"[VAPI] Auth failed at call start, using default greeting")
                greeting = generate_dynamic_greeting('ProjectForce')
                return create_assistant_config_response(greeting, '', 'ProjectForce')

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


def handle_assistant_started(message: Dict) -> Dict:
    """
    Handle assistant.started: VAPI notifies that assistant has started.

    This is sent at call start. We use it to return dynamic greeting
    with personalized client name and customer name.
    """
    try:
        # Extract call info
        call = message.get('call', {})
        call_id = call.get('id', 'unknown')

        # Extract phone numbers
        customer = call.get('customer', {})
        from_phone = customer.get('number', '')
        to_phone = resolve_to_phone(call)

        logger.info(f"[VAPI] assistant.started - Call {call_id}: from={mask_phone(from_phone)}, to={mask_phone(to_phone)}")

        # Authenticate to get client_name and user_name
        credentials = authenticate_caller(from_phone, to_phone)

        if credentials:
            client_name = credentials.get('client_name', 'ProjectForce')
            user_name = credentials.get('user_name', '')
            support_number = credentials.get('support_number', '')
            logger.info(f"[VAPI] Dynamic greeting for: {user_name} @ {client_name}, support: {support_number}")
            greeting = generate_dynamic_greeting(client_name, user_name)
            return create_assistant_config_response(greeting, support_number, client_name)
        else:
            # Auth failed - use default greeting
            logger.warning(f"[VAPI] Auth failed at assistant.started, using default greeting")
            greeting = generate_dynamic_greeting('ProjectForce')
            return create_assistant_config_response(greeting, '', 'ProjectForce')

    except Exception as e:
        logger.error(f"[VAPI] Error in assistant.started: {e}", exc_info=True)
        # Return default greeting on error
        greeting = generate_dynamic_greeting('ProjectForce')
        return create_assistant_config_response(greeting, '', 'ProjectForce')


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
    from_phone = customer.get('number', '')
    to_phone = resolve_to_phone(call)

    logger.info(f"[VAPI] Function call: {function_name}, params={parameters}")
    logger.info(f"[VAPI] Call context: call_id={call_id}, from={mask_phone(from_phone)}, to={mask_phone(to_phone)}")

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
    from_phone = customer.get('number', '')
    to_phone = resolve_to_phone(call)

    logger.info(f"[VAPI] Tool calls received: {len(tool_calls)} calls")
    logger.info(f"[VAPI] Call context: call_id={call_id}, from={mask_phone(from_phone)}, to={mask_phone(to_phone)}")
    logger.info(f"[VAPI] phoneNumberId: {call.get('phoneNumberId', 'N/A')}")

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
