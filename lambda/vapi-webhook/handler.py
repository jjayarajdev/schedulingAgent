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

# Import voice session cache for project preloading
try:
    from voice_session_cache import preload_projects_for_voice, get_cached_projects
    VOICE_CACHE_AVAILABLE = True
except ImportError:
    VOICE_CACHE_AVAILABLE = False
    logger.warning("voice_session_cache module not available")

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
        "Almost there.",
        "Just a moment more.",
    ]
}


def build_smart_project_context(projects_data: Optional[Dict]) -> str:
    """
    Build a smart project context string for the system prompt.

    Embeds project state directly so GPT-4o can respond without tool calls
    for common queries like "show my projects" or "schedule appointment".

    Args:
        projects_data: Dict from get_cached_projects with 'projects' and 'project_mapping'

    Returns:
        String to embed in system prompt, or empty string if no projects
    """
    if not projects_data:
        return ""

    projects = projects_data.get('projects', [])
    project_mapping = projects_data.get('project_mapping', {})

    if not projects:
        return """

## YOUR CUSTOMER'S PROJECTS (EMBEDDED STATE)

This customer has NO projects in the system.

**When they ask about projects:**
- Say: "I don't see any projects for you right now. Is there something else I can help with?"
- Do NOT call the tool for list_projects - you already know the answer.
"""

    # Categorize projects
    scheduled_projects = []
    schedulable_projects = []
    other_projects = []

    # Statuses to exclude from listing (not actionable by voice assistant)
    excluded_statuses = ['closed', 'cancelled', 'completed', 'work complete', 'done', 'archived',
                         'completed-archived', 'cancelled/surge', 'ready to cancel']

    for p in projects:
        status = (p.get('status') or '').lower()
        category = p.get('category', 'Unknown')
        project_type = p.get('projectType', '')
        project_id = p.get('project_id') or p.get('id', '')
        scheduled_date = p.get('scheduled_date', '')

        # Skip closed/cancelled/completed projects - not actionable
        if status in excluded_statuses:
            logger.info(f"[SMART-PROMPT] Project {project_id} ({category}) status='{status}' → EXCLUDED (not actionable)")
            continue

        project_number = p.get('projectNumber', '')
        project_info = {
            'category': category,
            'project_type': project_type,
            'project_id': project_id,
            'project_number': project_number,  # Customer-facing order number
            'status': status,
            'scheduled_date': scheduled_date,
            'address': p.get('address', ''),
            'date_sold': p.get('dateSold', ''),
        }

        # Determine bucket
        # Include tentatively scheduled as scheduled (has a date, awaiting confirmation)
        if status in ['scheduled', 'customer scheduled', 'tentatively scheduled']:
            scheduled_projects.append(project_info)
            logger.info(f"[SMART-PROMPT] Project {project_id} ({category}) status='{status}' → SCHEDULED bucket")
        elif status in ['ready to schedule', 'new', 'ready']:
            schedulable_projects.append(project_info)
            logger.info(f"[SMART-PROMPT] Project {project_id} ({category}) status='{status}' → SCHEDULABLE bucket")
        else:
            other_projects.append(project_info)
            logger.info(f"[SMART-PROMPT] Project {project_id} ({category}) status='{status}' → OTHER bucket")

    # Log summary for debugging
    logger.info(f"[SMART-PROMPT] Categorization: scheduled={len(scheduled_projects)}, schedulable={len(schedulable_projects)}, other={len(other_projects)}")

    # Build context string
    context_parts = ["\n\n## YOUR CUSTOMER'S PROJECTS (EMBEDDED STATE - RESPOND WITHOUT TOOL CALL)\n"]
    context_parts.append(f"Total projects: {len(projects)}\n")

    # Helper to format type naturally
    def format_type(ptype):
        if ptype:
            return f" (it's {'an' if ptype[0].lower() in 'aeiou' else 'a'} {ptype})"
        return ""

    # Helper to format project display (voice-friendly - no internal IDs)
    def format_project_display(p, show_date=False, show_status=False):
        """
        Format project for display - VOICE OPTIMIZED.

        CRITICAL: Do NOT include:
        - Order numbers (e.g., "21076-19PF6W-xxx") - read as "2 1 0 7 6 p f" by TTS
        - HTML comments (e.g., "<!-- project_id=xxx -->") - also read aloud by TTS

        Only show: category, type, date/status
        GPT-4o uses the project mapping in the system prompt to resolve category/type to project_id.
        """
        parts = [p['category']]
        if p['project_type']:
            parts.append(f"({p['project_type']})")
        if show_date and p.get('scheduled_date'):
            parts.append(f"- scheduled {p['scheduled_date']}")
        elif show_status:
            parts.append(f"- {p['status']}")
        # NO order numbers or hidden project_id references - TTS reads them aloud!
        return " ".join(parts)

    # Scheduled projects
    if scheduled_projects:
        context_parts.append(f"\n**ALREADY SCHEDULED ({len(scheduled_projects)}):**")
        for i, p in enumerate(scheduled_projects, 1):
            context_parts.append(f"  {i}. {format_project_display(p, show_date=True)}")

    # Schedulable projects
    if schedulable_projects:
        context_parts.append(f"\n**READY TO SCHEDULE ({len(schedulable_projects)}):**")
        for i, p in enumerate(schedulable_projects, 1):
            context_parts.append(f"  {i}. {format_project_display(p, show_status=True)}")

    # Other projects
    if other_projects:
        context_parts.append(f"\n**OTHER ({len(other_projects)}):**")
        for i, p in enumerate(other_projects, 1):
            context_parts.append(f"  {i}. {format_project_display(p, show_status=True)}")

    # Add response guidance
    context_parts.append("\n\n**SMART RESPONSES (NO TOOL CALL NEEDED):**")

    # Guide for "show my projects" / "what are my projects"
    if len(projects) == 1:
        p = projects[0]
        status = (p.get('status') or '').lower()
        ptype = p.get('projectType', '')
        type_phrase = f", it's {'an' if ptype and ptype[0].lower() in 'aeiou' else 'a'} {ptype}" if ptype else ""
        # Include tentatively scheduled as scheduled
        if status in ['scheduled', 'customer scheduled', 'tentatively scheduled']:
            date = p.get('scheduled_date', '') or 'an upcoming date'
            context_parts.append(f'''
- "Show my projects" / "What projects do I have?" →
  Say: "You have one project - {p.get('category')}{type_phrase}. It's already scheduled for {date}. Would you like to reschedule, or check the appointment details?"
  (No tool call needed - you have the info!)''')
        else:
            context_parts.append(f'''
- "Show my projects" / "What projects do I have?" →
  Say: "You have one project - {p.get('category')}{type_phrase}. It's ready to schedule. Would you like me to check available dates?"
  (No tool call needed!)''')
    else:
        # Multiple projects
        sched_count = len(scheduled_projects)
        ready_count = len(schedulable_projects)
        if sched_count > 0 and ready_count > 0:
            context_parts.append(f'''
- "Show my projects" →
  Say: "You have {len(projects)} projects. {sched_count} already scheduled, and {ready_count} ready to schedule. Which would you like to know more about?"''')
        elif sched_count > 0:
            context_parts.append(f'''
- "Show my projects" →
  Say: "You have {sched_count} project{'s' if sched_count > 1 else ''}, all already scheduled. Would you like to check the details or reschedule?"''')
        elif ready_count > 0:
            context_parts.append(f'''
- "Show my projects" →
  Say: "You have {ready_count} project{'s' if ready_count > 1 else ''} ready to schedule. Would you like to pick one?"''')

    # Guide for "schedule appointment" / "schedule a project"
    if len(schedulable_projects) == 0 and len(scheduled_projects) > 0:
        p = scheduled_projects[0]
        ptype = p.get('project_type', '')
        type_phrase = f", it's {'an' if ptype and ptype[0].lower() in 'aeiou' else 'a'} {ptype}" if ptype else ""
        # Handle empty scheduled_date - say "an upcoming date" if date is missing
        date_display = p['scheduled_date'] if p.get('scheduled_date') else "an upcoming date"
        logger.info(f"[SMART-PROMPT] Scheduling guidance: ALREADY_SCHEDULED - '{p['category']}' scheduled for {date_display}")
        context_parts.append(f'''
- "Schedule appointment" / "I want to schedule" / "Reschedule" →
  Say: "Your {p['category']} project{type_phrase} is already scheduled for {date_display}. Would you like to reschedule, or check the details?"
  If they say YES/RESCHEDULE → call tool: action=reschedule_appointment, project_id={p['project_id']}, message: "user's words"
  (IMPORTANT: Use reschedule_appointment for already-scheduled projects, NOT get_available_dates!)''')
    elif len(schedulable_projects) == 1:
        p = schedulable_projects[0]
        ptype = p.get('project_type', '')
        type_phrase = f", it's {'an' if ptype and ptype[0].lower() in 'aeiou' else 'a'} {ptype}" if ptype else ""
        logger.info(f"[SMART-PROMPT] Scheduling guidance: READY_TO_SCHEDULE - '{p['category']}' (ID: {p['project_id']})")
        context_parts.append(f'''
- "Schedule appointment" / "Schedule a project" →
  You can offer: "I see your {p['category']} project{type_phrase} is ready. Would you like me to check available dates?"
  If they say YES → call tool: action=get_available_dates, project_id={p['project_id']}''')
    elif len(schedulable_projects) > 1:
        # Differentiate projects: Type → Type+Address → Type+Store → Type+DateSold → Ordinals
        # Only use ordinals for actual duplicates, not ALL projects
        cat_types = []
        seen_names = set()

        for i, p in enumerate(schedulable_projects[:5]):
            cat = p['category']
            ptype = p.get('project_type', '')
            addr = p.get('address', '')
            store_name = ''
            date_sold = p.get('date_sold', '')

            # Extract address string
            if isinstance(addr, dict):
                addr_str = addr.get('address1', '') or addr.get('city', '')
            elif addr:
                addr_str = str(addr).split(',')[0][:20]
            else:
                addr_str = ''

            # Build name with best available differentiator
            if ptype:
                name = f"{cat} {ptype}"
            elif addr_str:
                name = f"{cat} at {addr_str}"
            else:
                name = cat

            # If duplicate, try adding more context
            if name in seen_names:
                if addr_str and ptype:
                    name = f"{cat} {ptype} at {addr_str}"
                if name in seen_names and date_sold:
                    try:
                        from datetime import datetime as dt_cls
                        ds = dt_cls.fromisoformat(date_sold.replace('Z', '+00:00'))
                        name = f"{cat} {ptype} sold {ds.strftime('%B %Y')}" if ptype else f"{cat} sold {ds.strftime('%B %Y')}"
                    except:
                        pass
                # Final fallback: ordinal (only for THIS duplicate, not all)
                if name in seen_names:
                    ordinal = ["first", "second", "third", "fourth", "fifth"][i]
                    name = f"the {ordinal} {cat} {ptype}" if ptype else f"the {ordinal} {cat}"

            seen_names.add(name)
            cat_types.append(name)

        logger.info(f"[SMART-PROMPT] Scheduling names: {cat_types}")
        context_parts.append(f'''
- "Schedule appointment" →
  Say: "I see {len(schedulable_projects)} projects ready to schedule: {', '.join(cat_types)}. Which one?"
  (No tool call needed to list them!)''')

    # Build project ID lookup mapping (GPT-4o can use category/type/address to find project_id)
    # CRITICAL: Put SCHEDULABLE projects FIRST so ordinals match voice guidance
    # Voice says "first Blinds, second Blinds" referring to SCHEDULABLE projects
    # So "first" in the mapping must also point to the first SCHEDULABLE project
    all_projects = schedulable_projects + scheduled_projects + other_projects
    mapping_lines = []
    for i, p in enumerate(all_projects, 1):
        cat = p['category']
        ptype = p.get('project_type', '')
        addr = p.get('address', '')
        addr_str = str(addr) if addr else ''
        addr_short = addr_str.split(',')[0] if ',' in addr_str else addr_str[:20] if addr_str else ''

        if ptype:
            mapping_lines.append(f"  - {cat} ({ptype}): project_id={p['project_id']}")
        elif addr_short:
            # Include address for projects without type (helps match "Blinds at Main Street")
            mapping_lines.append(f"  - {cat} at {addr_short}: project_id={p['project_id']}")
        else:
            # Fallback: use ordinal position
            ordinal = ["first", "second", "third", "fourth", "fifth"][i-1] if i <= 5 else f"#{i}"
            mapping_lines.append(f"  - {ordinal} {cat}: project_id={p['project_id']}")

    context_parts.append(f'''
**PROJECT ID LOOKUP (for tool calls only - NEVER read these aloud):**
{chr(10).join(mapping_lines)}

**WHEN TO USE THE TOOL:**
- get_available_dates: For projects NOT yet scheduled (status: Ready To Schedule, New)
- reschedule_appointment: For projects ALREADY scheduled (status: Scheduled, Customer Scheduled)
  IMPORTANT: If user says "reschedule" or wants new dates for an ALREADY SCHEDULED project,
  use action=reschedule_appointment (NOT get_available_dates!)
- get_time_slots: When user picks a date and needs time slots
- schedule_project: When user confirms date AND time
- get_project_details: When user asks for details you don't have (technician, exact time, etc.)
- ALWAYS include project_id from the lookup table above when calling tools

**CRITICAL - PROJECT IDENTIFICATION:**
- When speaking: Refer to projects by CATEGORY (e.g., "your Blinds project", "your Decking project")
- When speaking: If there are multiple projects of the same category, use TYPE (e.g., "Blinds Installation", "Blinds Measurement")
- NEVER read out project IDs, order numbers, or any alphanumeric codes - they sound terrible when spoken
- When calling tools: Look up the project_id from the table above using category (and type if needed)
''')

    return '\n'.join(context_parts)


def get_tool_messages():
    """
    Generate tool messages for VAPI tool calls.

    Strategy:
    - Filler at start: "Sure, let me check."
    - Failure message for errors
    - No delayed filler - responses should be fast enough now
    """
    return [
        {
            'type': 'request-start',
            'content': "Sure, let me check."
        },
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


def send_support_sms(from_phone: str, to_phone: str, client_id: str, bearer_token: str, support_number: str, call_id: str = '', user_id: str = '') -> Dict[str, Any]:
    """
    Send support contact info via SMS to the customer.

    Calls the ProjectForce support-sms API to send the customer a text message
    with the office phone number they can call.

    Args:
        from_phone: Customer's phone number (recipient of SMS)
        to_phone: Our VAPI/Twilio number (sender)
        client_id: Client identifier
        bearer_token: Auth token for the API
        support_number: The support phone number to include
        call_id: VAPI call ID for audit trail
        user_id: Customer user ID for audit trail

    Returns:
        Dict with success status and voice-formatted support number
    """
    import urllib.request
    import urllib.error

    # Determine environment from Lambda function name or use dev
    environment = os.environ.get('ENVIRONMENT', 'dev')
    if environment == 'prod':
        api_base = 'https://api-cx-portal.apps.projectsforce.com'
    else:
        api_base = 'https://api-cx-portal.dev.projectsforce.com'

    url = f'{api_base}/authentication/support-sms'

    # Build request payload
    # API expects: from_phone = customer (recipient), to_phone = VAPI/Twilio (sender)
    payload = json.dumps({
        'client_id': client_id,
        'from_phone': from_phone,  # Customer receives the SMS
        'to_phone': to_phone       # VAPI/Twilio number sends it
    }).encode('utf-8')

    # Audit context for logging
    audit_ctx = f"call_id={call_id}, user_id={user_id}, client_id={client_id}, to={mask_phone(from_phone)}"

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {bearer_token}'
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            logger.info(f"[SUPPORT_SMS] SUCCESS - {audit_ctx}, support_number={support_number}")

            return {
                'success': True,
                'sms_sent': True,
                'support_number': support_number,
                'message': result.get('message', 'SMS sent')
            }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ''
        logger.error(f"[SUPPORT_SMS] FAILED - {audit_ctx}, http_code={e.code}, error={error_body}")
        return {
            'success': False,
            'sms_sent': False,
            'support_number': support_number,
            'error': f'HTTP {e.code}'
        }
    except Exception as e:
        logger.error(f"[SUPPORT_SMS] FAILED - {audit_ctx}, error={str(e)}")
        return {
            'success': False,
            'sms_sent': False,
            'support_number': support_number,
            'error': str(e)
        }


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


def generate_dynamic_greeting(client_name: str, user_name: str = None, projects_data: Optional[Dict] = None) -> str:
    """
    Generate dynamic greeting with client-specific company name, user name, and project context.

    Args:
        client_name: Company name from auth API (e.g., "ProjectsForce Validation", "Window Universe")
        user_name: Optional user name for personalization
        projects_data: Optional dict with 'projects' list for context-aware greeting

    Returns:
        SSML-formatted greeting string with pauses
    """
    display_name = client_name if client_name else 'ProjectForce'

    # Extract first name only for greeting
    first_name = ''
    if user_name:
        first_name = user_name.split()[0] if user_name.strip() else ''

    # Analyze projects for smart greeting
    schedulable_projects = []
    scheduled_projects = []

    if projects_data and projects_data.get('projects'):
        for p in projects_data['projects']:
            status = (p.get('status_info_status') or p.get('status') or '').lower()
            category = p.get('project_category') or p.get('category') or 'project'

            if status in ['new', 'ready to schedule']:
                schedulable_projects.append(category)
            elif status in ['scheduled', 'customer scheduled', 'tentatively scheduled']:
                scheduled_projects.append(category)

    # Build context-aware greeting
    name_part = f"Hello {first_name}!" if first_name else "Hello!"
    intro = f"I'm J, your AI assistant from {display_name}."

    # Generate project-aware guidance
    if schedulable_projects and scheduled_projects:
        # Both types of projects
        sched_count = len(schedulable_projects)
        already_count = len(scheduled_projects)
        sched_names = ', '.join(set(schedulable_projects[:2]))  # First 2 unique categories
        guidance = (
            f"I see you have {sched_count} project{'s' if sched_count > 1 else ''} ready to schedule, "
            f"like your {sched_names}, and {already_count} already scheduled. "
            f"Would you like to schedule a new appointment, or check on your existing ones?"
        )
    elif schedulable_projects:
        # Only schedulable projects
        sched_count = len(schedulable_projects)
        sched_names = ', '.join(set(schedulable_projects[:2]))
        guidance = (
            f"I see you have {sched_count} project{'s' if sched_count > 1 else ''} ready to schedule, "
            f"including your {sched_names}. Would you like to check available dates?"
        )
    elif scheduled_projects:
        # Only scheduled projects
        already_count = len(scheduled_projects)
        guidance = (
            f"I see you have {already_count} appointment{'s' if already_count > 1 else ''} already scheduled. "
            f"Would you like to check on them, or reschedule?"
        )
    else:
        # No projects or unknown
        guidance = (
            "I can help you view your projects, check available dates, or schedule appointments. "
            "What would you like to do today?"
        )

    greeting = (
        f'<break time="3000ms"/> {name_part} <break time="300ms"/> '
        f'{intro} <break time="500ms"/> '
        f'{guidance}'
    )
    return greeting


def create_assistant_config_response(first_message: str, support_number: str = '', client_name: str = 'ProjectForce', projects_data: Optional[Dict] = None) -> Dict:
    """
    Create response with customized assistant configuration.

    Used at call start to return dynamic greeting.
    Returns full assistant config with voice, model, tools, etc.

    Args:
        first_message: The greeting message
        support_number: Client's support phone number for escalation
        client_name: Client company name
        projects_data: Optional cached projects data for smart system prompt
    """
    # Format support number for voice - use WORDS for slower, clearer speech
    # Words naturally slow down TTS compared to digits
    digit_words = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
    }
    support_number_voice = ''
    if support_number:
        digits = ''.join(c for c in support_number if c.isdigit())
        if len(digits) == 10:
            # Format: "eight, six, zero... two, six, nine... nine, zero, four, zero"
            part1 = ', '.join(digit_words[d] for d in digits[0:3])
            part2 = ', '.join(digit_words[d] for d in digits[3:6])
            part3 = ', '.join(digit_words[d] for d in digits[6:10])
            support_number_voice = f"{part1}... {part2}... {part3}"
        elif len(digits) == 11 and digits[0] == '1':
            part1 = ', '.join(digit_words[d] for d in digits[1:4])
            part2 = ', '.join(digit_words[d] for d in digits[4:7])
            part3 = ', '.join(digit_words[d] for d in digits[7:11])
            support_number_voice = f"one... {part1}... {part2}... {part3}"
        else:
            # Fallback: words for all digits
            support_number_voice = ', '.join(digit_words.get(d, d) for d in digits)
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
                    'description': 'Say ONE brief phrase like "Sure, let me check." then call SILENTLY. NO multiple fillers. Pass user EXACT words as message. Include project_id when you know which project.',
                    'parameters': {
                        'type': 'object',
                        'required': ['message', 'action'],
                        'properties': {
                            'action': {
                                'type': 'string',
                                'enum': ['list_projects', 'get_project_details', 'get_available_dates', 'get_time_slots', 'schedule_project', 'confirm_appointment', 'reschedule_appointment', 'get_weather', 'calendar_info', 'send_support_sms', 'other'],
                                'description': 'The type of action requested. Use calendar_info for "what day is X date" questions. Use send_support_sms when user asks for office number or you need to escalate - this sends them an SMS AND returns the number to read. CRITICAL: Use confirm_appointment ONLY after user has selected BOTH a DATE and a TIME SLOT.'
                            },
                            'message': {
                                'type': 'string',
                                'description': 'The user request or question. Pass the user exact words.'
                            },
                            'project_id': {
                                'type': 'string',
                                'description': 'The project ID from embedded state. Include when you know which project (from YOUR CUSTOMER\'S PROJECTS section).'
                            },
                            'project_status': {
                                'type': 'string',
                                'description': 'The project status from embedded state (e.g., "scheduled", "ready to schedule"). Include along with project_id.'
                            },
                            'confirmed': {
                                'type': 'boolean',
                                'description': 'Set to true ONLY after user explicitly confirms the appointment preview. Required for Step 2 of booking.'
                            },
                            'date': {
                                'type': 'string',
                                'description': 'Selected date in YYYY-MM-DD format. Extract from user speech (e.g., "January 31st" → "2026-01-31", "tomorrow" → calculate date). ALWAYS include when user mentions a date.'
                            },
                            'time': {
                                'type': 'string',
                                'description': 'Selected time in HH:MM format (24-hour). Extract from user speech (e.g., "8 AM" → "08:00", "2:30 PM" → "14:30"). ALWAYS include when user mentions a time.'
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
                'content': '''## RULE #1 - TOOL CALL BEHAVIOR

The system will automatically say filler phrases during tool calls.
**AFTER tool call completes:** Immediately speak the result from the "response" field.

IMPORTANT: When you receive a tool result, your VERY NEXT words must be the content from the "response" field. Do not add any preamble or filler - just speak the response directly.
- "This will just take a sec" - BANNED

## RULE #1b - PHONE NUMBER READOUT (SPEAK SLOWLY)

When reading phone numbers, SPEAK SLOWLY and clearly. Use the WORD form of each digit.
Output exactly as formatted in this prompt - the words create natural slower pacing.
Example output: "eight, six, zero... two, six, nine... nine, zero, four, zero"

CRITICAL: Speak each digit as a WORD (eight, not 8). The ellipsis creates pauses between groups. Do NOT rush.

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

If customer asks or implies ANY of these:
- "Am I talking to AI?" / "Is this AI?" / "Is this artificial intelligence?"
- "Are you a robot?" / "Are you a computer?" / "Are you a bot?"
- "Is this a real person?" / "Am I talking to a real person?"
- "Are you a girl?" / "Are you human?" / "Are you a person?"
- "You're not a real person, right?" / "This is a computer, isn't it?"
- "Are you one of those AI things?"

HONEST ANSWER: "Yes, I'm J, an AI assistant. I help with scheduling appointments. Would you like me to give you our office number to speak with someone directly?"

If customer STATES to someone else "This is an AI" or "This isn't a real person":
RESPONSE: "That's right, I'm an AI assistant. I'm happy to help with scheduling, or I can give you the office number if you'd prefer to speak with someone."

NEVER dodge this question. NEVER pretend to be human. NEVER deflect with unrelated topics like "I'm all about home improvement".

---

## RULE #4 - ESCALATION TO HUMAN

If customer asks for "representative", "real person", "customer service", "office number", OR you need to give them the office number:
**CALL the tool** with action='send_support_sms' - this returns the office number for you to read.

After the tool returns, read the response directly - it contains the formatted office number.

''' + (f'''If tool unavailable, fallback: "You can reach {client_name} at {support_number_voice}."''' if support_number_voice else '''If no number available: "You can check your confirmation email or the company website for contact details."''') + '''

---

## Identity

You are **J**, a friendly voice assistant, helping homeowners manage their home improvement projects and appointments.

**Today's date: ''' + datetime.now().strftime("%A, %B %d, %Y") + '''**

**CALENDAR QUESTIONS (CRITICAL - DO NOT GUESS):**
When customer asks "what day is [date]" or "which day does [date] fall on":
1. Say "Sure, let me check." and call the tool with action="calendar_info"
2. WAIT for the tool response - do NOT say any day name (Monday, Tuesday, etc.) until you receive the result
3. Speak ONLY the tool response - it will say "[Date] is a [Day]."

⚠️ NEVER guess or calculate days yourself - your math WILL be wrong. Just wait for the tool.

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
- Answering project questions
- Details of a project

## What You CANNOT Do (redirect to office - USE send_support_sms)

**CRITICAL - These features do NOT exist. When you need to give the office number, CALL the tool with action='send_support_sms':**

1. **CANCEL appointments**: "I'm not able to cancel appointments directly. Let me give you our office number." → CALL send_support_sms

2. **Change ADDRESS**: "I can't update addresses in the system. Would you like the office number?" → CALL send_support_sms

3. **Pricing/cost questions**: "I don't have pricing information. Let me give you the office number." → CALL send_support_sms

4. **Product questions** (not about their project): "For product questions, our office would be the best resource." → CALL send_support_sms

5. **Complaints about service**: "I'm sorry to hear that. Let me give you the office number so you can speak with someone." → CALL send_support_sms

6. **Technical/installation questions**: "That's a great question for the installer. I can tell you when they're scheduled, or give you the office number."

NEVER say "I'm having trouble" or "I couldn't complete that" for cancel/address - these imply temporary failure. Be honest that the feature doesn't exist.

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
- "Cancel my appointment" → action: send_support_sms. Say: "I'm not able to cancel appointments directly. Let me give you our office number."
- "Reschedule to next week" → action: reschedule_appointment
- "Tell me about my project" → action: get_project_details
- "What's the weather on my appointment day?" → action: get_weather
- "Will it rain on Tuesday?" → action: get_weather
- "Weather forecast for my install date" → action: get_weather

**GENERIC SCHEDULING REQUESTS (MANDATORY - YOU MUST CALL list_projects):**
⚠️ CRITICAL: When user says ANY of these, you MUST immediately call list_projects. NO EXCEPTIONS. NO CHITCHAT. NO QUESTIONS.
- "Schedule appointment" → CALL TOOL: action: list_projects, message: "schedule appointment"
- "Schedule a project" → CALL TOOL: action: list_projects, message: "schedule a project"
- "I want to schedule" → CALL TOOL: action: list_projects, message: "I want to schedule"
- "Book an appointment" → CALL TOOL: action: list_projects, message: "book an appointment"
- "Make an appointment" → CALL TOOL: action: list_projects, message: "make an appointment"
- "Help me schedule" → CALL TOOL: action: list_projects, message: "help me schedule"
- "Can I schedule something?" → CALL TOOL: action: list_projects, message: "can I schedule something"
- "Today, help me schedule" → CALL TOOL: action: list_projects, message: "help me schedule"
- ANY variation with "schedule" or "appointment" → CALL TOOL: action: list_projects

⚠️ COMMON TRANSCRIPTION ERRORS (these sound like "schedule" - treat as scheduling requests):
- "Scale" / "Scale up" / "Scale a" → CALL TOOL: action: list_projects (misheard "schedule")
- "Settle" / "Settle up" → CALL TOOL: action: list_projects (misheard "schedule")
- "Scaling" → CALL TOOL: action: list_projects (misheard "scheduling")
- "Set up" / "Setting up" → CALL TOOL: action: list_projects (misheard "scheduling")
- If user says something that sounds SIMILAR to "schedule" or "appointment", treat it as a scheduling request.

❌ WRONG: Responding "Want to see your projects or schedule something new?" (this is chitchat - NEVER do this)
✅ RIGHT: Immediately call list_projects tool with the user's message

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
- "Cancel it" → DO NOT call tool. Say: "I can't cancel appointments, but our office can help with that right away."
- "Tell me about it" → get_project_details, message: "tell me about it"
- "Schedule that one" → get_available_dates, message: "schedule that one"
- "What about the other one?" → get_project_details, message: "what about the other one"
- "The first one" → (pass exact words - backend resolves ordinal)
- "The second option" → (pass exact words - backend resolves ordinal)
- "Different date please" → get_available_dates, message: "different date please"

**APPOINTMENT STATUS QUERIES (when NO project context exists yet):**
⚠️ If user asks about appointments but you haven't discussed a specific project yet, call list_projects FIRST:
- "Is someone coming today?" → list_projects, message: "is someone coming today"
- "When is my appointment?" → list_projects, message: "when is my appointment"
- "Is the technician coming?" → list_projects, message: "is the technician coming"
- "Are they coming to measure?" → list_projects, message: "are they coming to measure"
- "Do I have an appointment today?" → list_projects, message: "do I have an appointment today"
- "What time is someone coming?" → list_projects, message: "what time is someone coming"
- "Is anyone coming this week?" → list_projects, message: "is anyone coming this week"
The backend will find scheduled projects and return the relevant appointment info.

**CONTEXT QUERIES (when project context ALREADY exists from prior conversation):**
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

**TIME SLOT SELECTION (CRITICAL FLOW):**
⚠️ YOU MUST GET TIME SLOTS BEFORE CONFIRMING! Follow this exact sequence:
1. User picks a DATE → call get_time_slots to show available times for that date
2. User picks a TIME → THEN call confirm_appointment

NEVER skip step 1! Even if user says "book it" or "confirm" after picking just a date, you MUST first call get_time_slots.

Examples:
- "Morning appointment" → get_time_slots, message: "morning appointment"
- "Afternoon slot" → get_time_slots, message: "afternoon slot"
- "10:30 AM" → confirm_appointment, message: "10:30 AM" (ONLY after time slots were shown!)
- "The 1 PM slot" → confirm_appointment, message: "the 1 PM slot" (ONLY after time slots were shown!)
- "Earlier time" → get_time_slots, message: "earlier time"
- User selected date, then says "book it" → get_time_slots FIRST (they haven't picked a time yet!)

**IMPORTANT:** Always pass the customer's EXACT words as the message. The backend has AI-powered context resolution that understands pronouns, ordinals, and references.

**PARAMETER ACCUMULATION (CRITICAL FOR SPEED):**
When calling tools, ALWAYS include accumulated context from the conversation:

1. **DATE EXTRACTION** - When user mentions ANY date:
   - "January 31st" / "the 31st" → date: "2026-01-31"
   - "tomorrow" → calculate and pass as YYYY-MM-DD
   - "next Friday" → calculate and pass as YYYY-MM-DD
   - "the 30th" → date: "2026-01-30" (assume current/next month)

2. **TIME EXTRACTION** - When user mentions ANY time:
   - "8 AM" / "8 o'clock" → time: "08:00"
   - "2:30 PM" → time: "14:30"
   - "morning" → time: "08:00" (or earliest shown)
   - "the first slot" → time: use the first time you showed them

3. **ALWAYS PASS WHAT YOU KNOW:**
   - If you know project_id → include it
   - If user selected a date → include date parameter
   - If user selected a time → include time parameter
   - If confirming → include confirmed: true

Example flow:
- Turn 1: User says "Blinds" → action: get_available_dates, project_id: "8175908"
- Turn 2: User says "January 31st" → action: get_time_slots, project_id: "8175908", date: "2026-01-31"
- Turn 3: User says "8 AM" → action: confirm_appointment, project_id: "8175908", date: "2026-01-31", time: "08:00", confirmed: true

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

### TWO-STEP APPOINTMENT CONFIRMATION (CRITICAL)
⚠️ MANDATORY: The appointment booking requires TWO tool calls to complete!

**STEP 1 - Preview:** When user selects a time and you call the tool, you will receive a PREVIEW response with `status: awaiting_confirmation`. This is NOT the final booking. Speak the preview to the user.

**STEP 2 - Finalize:** When the user says "yes", "confirm", "book it", "sounds good", or any affirmative response:
- You MUST call the `projectforce_api` tool AGAIN with:
  - action: "schedule_project"
  - message: "confirm appointment" or "yes confirm"
  - The backend will finalize the booking with `confirmed=true`

❌ WRONG: User says "yes" → You say "Great, you're all set!" (WITHOUT calling tool)
✅ RIGHT: User says "yes" → Call tool with message="confirm appointment" → THEN say "Great, you're all set!"

**The appointment is NOT booked until you receive a SUCCESS response after the user confirms.**
Never assume the appointment is booked after Step 1. Always make the second tool call.

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
- **NEVER respond with chitchat when customer wants to schedule** - if they say "schedule", "help me schedule", "book an appointment", "make an appointment", or ANY scheduling-related request, you MUST call the list_projects tool. Do NOT ask clarifying questions. Do NOT make conversation. CALL THE TOOL.
- **NEVER ask "which project do you want to schedule?"** - the backend will show available projects when you call list_projects

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

### CRITICAL REMINDER: SILENCE DURING TOOL CALLS
1. Say ONE contextual filler (e.g., "Checking your projects." for list_projects)
2. STOP SPEAKING. Say NOTHING while waiting.
3. Next words = the actual answer.

NEVER say: "Hold on", "Just a sec", "Still working", "Give me a moment"

### REPETITION DETECTION (CRITICAL - AVOID LOOPS)
If you notice you're giving the SAME response multiple times in a conversation (e.g., "no dates available" twice):
- DO NOT repeat the same response a third time
- Instead, escalate: "It looks like our schedule is quite full right now. Let me give you our office number - they may have more options available. Would that help?"
- If customer keeps trying: "I understand you'd like to schedule soon. Unfortunately, I'm not finding any openings right now. The office team has direct access to the installer schedules and may be able to help. Would you like that number?"

**Examples of loops to break:**
- "No dates available" → "No dates available" → STOP, offer office number
- "I don't see any projects" → "I don't see any projects" → STOP, suggest calling back later
- Same error message twice → STOP, acknowledge the issue and offer alternative

The goal is NEVER to frustrate the customer with repetitive responses. When stuck, always offer a human alternative.''' + build_smart_project_context(projects_data)
            }]
        },
        'transcriber': {
            'model': 'nova-3',
            'language': 'en',
            'provider': 'deepgram',
            'endpointing': 150
        },
        'firstMessage': first_message,
        'endCallPhrases': ['goodbye', 'talk to you soon', 'have a great day', 'have a good day', 'bye bye', 'bye now'],
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

                # PRELOAD PROJECTS at call start for faster voice responses
                # Then get the cached data for smart system prompt
                projects_data = None
                if VOICE_CACHE_AVAILABLE:
                    try:
                        from phone_auth import normalize_phone
                        normalized_phone = normalize_phone(from_phone)
                        preload_result = preload_projects_for_voice(
                            phone_number=normalized_phone,
                            client_id=credentials.get('client_id', ''),
                            customer_id=credentials.get('user_id', ''),
                            bearer_token=credentials.get('bearer_token', '')
                        )
                        logger.info(f"[VAPI] Preload result: {preload_result.get('project_count', 0)} projects cached")

                        # Get cached projects for smart system prompt
                        projects_data = get_cached_projects(normalized_phone)
                        if projects_data:
                            logger.info(f"[VAPI] Smart prompt: {len(projects_data.get('projects', []))} projects embedded in system prompt")
                    except Exception as e:
                        logger.warning(f"[VAPI] Preload failed (non-blocking): {e}")

                greeting = generate_dynamic_greeting(client_name, user_name, projects_data)
                return create_assistant_config_response(greeting, support_number, client_name, projects_data)
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

        # Call orchestrator (include from_phone for voice cache lookup)
        response_text = call_orchestrator(
            message=user_message,
            call_id=call_id,
            credentials=credentials,
            from_phone=from_phone
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
        project_id = parameters.get('project_id', '')  # From smart prompt embedded state
        project_status = parameters.get('project_status', '')  # From smart prompt embedded state
        gpt_date = parameters.get('date', '')  # From GPT-4o: selected date YYYY-MM-DD
        gpt_time = parameters.get('time', '')  # From GPT-4o: selected time HH:MM
        confirmed = parameters.get('confirmed', False)  # From GPT-4o: user confirmed appointment

        if project_id:
            logger.info(f"[VAPI] GPT-4o passed project_id from embedded state: {project_id}, status: {project_status}")
        if gpt_date or gpt_time:
            logger.info(f"[VAPI] GPT-4o passed date={gpt_date}, time={gpt_time}")

        # FALLBACK: If message is empty but action is provided, synthesize message from action
        # This handles cases where GPT-4o knows the intent (action) but doesn't provide message
        if not user_message and action and action != 'other':
            user_message = action.replace('_', ' ')  # e.g., "get_available_dates" -> "get available dates"
            logger.info(f"[VAPI] Synthesized message from action: '{user_message}' (original message was empty)")

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

        # Handle send_support_sms action - send SMS + return number for voice
        if action == 'send_support_sms':
            support_number = credentials.get('support_number', '')
            client_id = credentials.get('client_id', '')
            bearer_token = credentials.get('bearer_token', '')

            # Format number for voice (words)
            digit_words = {
                '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
                '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
            }
            digits = ''.join(c for c in support_number if c.isdigit())
            if len(digits) == 10:
                part1 = ', '.join(digit_words[d] for d in digits[0:3])
                part2 = ', '.join(digit_words[d] for d in digits[3:6])
                part3 = ', '.join(digit_words[d] for d in digits[6:10])
                support_number_voice = f"{part1}... {part2}... {part3}"
            else:
                support_number_voice = ', '.join(digit_words.get(d, d) for d in digits)

            # Send the SMS silently (don't mention it to user)
            user_id = credentials.get('user_id', '')
            sms_result = send_support_sms(
                from_phone=from_phone,  # Customer's phone (recipient)
                to_phone=to_phone,      # Our number (sender)
                client_id=client_id,
                bearer_token=bearer_token,
                support_number=support_number,
                call_id=call_id,        # For audit trail
                user_id=user_id         # For audit trail
            )

            if not sms_result.get('sms_sent'):
                logger.warning(f"[VAPI] SMS send failed: {sms_result.get('error')}")

            # Just return the number - AI reads it out, SMS is silent
            client_name = credentials.get('client_name', 'our office')
            response_text = f"You can reach {client_name} at {support_number_voice}. Would you like me to repeat that?"

            return create_function_response({
                "success": True,
                "response": response_text,
                "sms_sent": sms_result.get('sms_sent', False),
                "support_number": support_number
            })

        # Call orchestrator with the user's message
        # CRITICAL: Pass GPT-4o's action - the orchestrator should TRUST it!
        # GPT-4o has full context via smart prompt and knows what action to take
        response_text = call_orchestrator(
            message=user_message,
            call_id=call_id,
            credentials=credentials,
            from_phone=from_phone,
            project_id=project_id,
            project_status=project_status,
            confirmed=confirmed,
            gpt_action=action,  # TRUST GPT-4o's decision!
            gpt_date=gpt_date,
            gpt_time=gpt_time
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
            project_id = arguments.get('project_id', '')  # From smart prompt embedded state
            project_status = arguments.get('project_status', '')  # From smart prompt embedded state
            confirmed = arguments.get('confirmed', False)  # For two-step appointment confirmation
            gpt_date = arguments.get('date', '')  # From GPT-4o: selected date YYYY-MM-DD
            gpt_time = arguments.get('time', '')  # From GPT-4o: selected time HH:MM

            # FALLBACK: If message is empty but action is provided, synthesize message from action
            # This handles cases where user says "Yes" and GPT-4o knows the intent but doesn't provide message
            if not user_message and action and action != 'other':
                user_message = action.replace('_', ' ')  # e.g., "get_available_dates" -> "get available dates"
                logger.info(f"[VAPI] Synthesized message from action: '{user_message}' (original message was empty)")

            if project_id:
                logger.info(f"[VAPI] GPT-4o passed project_id from embedded state: {project_id}, status: {project_status}")
            if gpt_date or gpt_time:
                logger.info(f"[VAPI] GPT-4o passed date={gpt_date}, time={gpt_time}")
            if confirmed:
                logger.info(f"[VAPI] GPT-4o passed confirmed=True for final appointment booking")

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

            # Handle send_support_sms action directly - send SMS + return number for voice
            if action == 'send_support_sms':
                support_number = credentials.get('support_number', '')
                client_id = credentials.get('client_id', '')
                bearer_token = credentials.get('bearer_token', '')

                # Format number for voice (words)
                digit_words = {
                    '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
                    '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
                }
                digits = ''.join(c for c in support_number if c.isdigit())
                if len(digits) == 10:
                    part1 = ', '.join(digit_words[d] for d in digits[0:3])
                    part2 = ', '.join(digit_words[d] for d in digits[3:6])
                    part3 = ', '.join(digit_words[d] for d in digits[6:10])
                    support_number_voice = f"{part1}... {part2}... {part3}"
                else:
                    support_number_voice = ', '.join(digit_words.get(d, d) for d in digits)

                # Send the SMS silently (don't mention it to user)
                user_id = credentials.get('user_id', '')
                sms_result = send_support_sms(
                    from_phone=from_phone,
                    to_phone=to_phone,
                    client_id=client_id,
                    bearer_token=bearer_token,
                    support_number=support_number,
                    call_id=call_id,
                    user_id=user_id
                )

                if not sms_result.get('sms_sent'):
                    logger.warning(f"[VAPI] SMS send failed: {sms_result.get('error')}")

                # Return the number - AI reads it out, SMS is silent
                client_name = credentials.get('client_name', 'our office')
                response_text = f"You can reach {client_name} at {support_number_voice}. Would you like me to repeat that?"

                results.append({
                    "toolCallId": tool_call_id,
                    "result": json.dumps({
                        "success": True,
                        "response": response_text,
                        "sms_sent": sms_result.get('sms_sent', False),
                        "support_number": support_number
                    })
                })
                continue

            # Call orchestrator with GPT-4o's action - TRUST IT!
            # GPT-4o has full context via smart prompt and knows what to do
            response_text = call_orchestrator(
                message=user_message,
                call_id=call_id,
                credentials=credentials,
                from_phone=from_phone,
                project_id=project_id,
                project_status=project_status,
                confirmed=confirmed,
                gpt_action=action,  # TRUST GPT-4o's decision!
                gpt_date=gpt_date,
                gpt_time=gpt_time
            )

            logger.info(f"[VAPI] Tool call result: {response_text[:200] if response_text else 'empty'}")
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


def call_orchestrator(message: str, call_id: str, credentials: Dict, from_phone: str = '', project_id: str = '', project_status: str = '', confirmed: bool = False, gpt_action: str = '', gpt_date: str = '', gpt_time: str = '') -> str:
    """
    Call the orchestrator Lambda with the user's message.

    Args:
        message: The user's message
        call_id: VAPI call ID
        credentials: Auth credentials from phone_auth
        from_phone: Caller's phone number for voice cache lookup
        project_id: Optional project ID from GPT-4o's embedded state (smart prompt)
        project_status: Optional project status from GPT-4o's embedded state (smart prompt)
        confirmed: True when user explicitly confirms appointment (Step 2 of two-step booking)
        gpt_action: Action specified by GPT-4o (e.g., 'get_available_dates', 'list_projects') - TRUST THIS!
        gpt_date: Selected date from GPT-4o in YYYY-MM-DD format
        gpt_time: Selected time from GPT-4o in HH:MM format
    """
    try:
        # Build orchestrator payload
        body_data = {
            'message': message,
            'session_id': f"vapi-{call_id}",
            'pf_token': credentials.get('bearer_token', ''),
            'pf_client_id': credentials.get('client_id', ''),
            'pf_user_id': credentials.get('user_id', ''),
            'pf_user_name': credentials.get('user_name', ''),
            'channel': 'voice',
            'from_phone': from_phone  # For voice cache lookup in scheduling-actions
        }

        # Include project_id and project_status if provided by GPT-4o from embedded state
        if project_id:
            body_data['project_id'] = project_id
            logger.info(f"[VAPI] Including project_id from smart prompt: {project_id}")
        if project_status:
            body_data['project_status'] = project_status
            logger.info(f"[VAPI] Including project_status from smart prompt: {project_status}")
        if confirmed:
            body_data['confirmed'] = True
            logger.info(f"[VAPI] Including confirmed=True for Step 2 appointment booking")

        # CRITICAL: Pass GPT-4o's action - orchestrator should TRUST this!
        # GPT-4o has full context (smart prompt with all projects) and knows what action to take
        if gpt_action and gpt_action != 'other':
            body_data['gpt_action'] = gpt_action
            logger.info(f"[VAPI] Including gpt_action={gpt_action} - ORCHESTRATOR SHOULD TRUST THIS!")

        # Pass date and time from GPT-4o if provided
        if gpt_date:
            body_data['date'] = gpt_date
            logger.info(f"[VAPI] Including date from GPT-4o: {gpt_date}")
        if gpt_time:
            body_data['time'] = gpt_time
            logger.info(f"[VAPI] Including time from GPT-4o: {gpt_time}")

        payload = {
            'body': json.dumps(body_data)
        }

        logger.info(f"[VAPI] Calling orchestrator: {ORCHESTRATOR_LAMBDA}, from_phone={'***'+from_phone[-4:] if from_phone else 'empty'}")

        response = lambda_client.invoke(
            FunctionName=ORCHESTRATOR_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())
        logger.info(f"[VAPI] Orchestrator response: status={result.get('statusCode')}")
        logger.info(f"[VAPI] Orchestrator result body: {str(result.get('body', ''))[:500]}")

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

    - Strip ALL SSML tags (Claude and some TTS don't handle them well)
    - Remove markdown
    - Clean up formatting
    - Keep it concise
    """
    import re

    # Strip ALL SSML tags - Claude and many TTS providers don't handle them well
    # This makes the response clean text that any LLM/TTS can handle
    text = re.sub(r'<amazon:domain[^>]*>', '', text)
    text = re.sub(r'</amazon:domain>', '', text)
    text = re.sub(r'<speak>', '', text)
    text = re.sub(r'</speak>', '', text)
    text = re.sub(r'<prosody[^>]*>', '', text)
    text = re.sub(r'</prosody>', '', text)
    text = re.sub(r'<break[^>]*/>', '', text)
    text = re.sub(r'<break[^>]*>', '', text)

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
