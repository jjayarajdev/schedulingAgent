#!/usr/bin/env python3
"""
Simple CORS proxy for ProjectForce API
Allows the HTML page to make API calls without CORS issues
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging
import json
import os
import time
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment-based configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

API_BASE_URLS = {
    "dev": "https://api-cx-portal.dev.projectsforce.com",
    "staging": "https://api-cx-portal.staging.projectsforce.com",
    "prod": "https://api-cx-portal.apps.projectsforce.com"
}
PF_API_BASE = API_BASE_URLS.get(ENVIRONMENT, API_BASE_URLS["dev"])
logger.info(f"🌍 Environment: {ENVIRONMENT} | Region: {AWS_REGION} | API Base: {PF_API_BASE}")

# ============================================================================
# Conversation History Management
# ============================================================================

# In-memory conversation storage (session_id -> conversation history)
# Format: {session_id: {'messages': [...], 'last_activity': timestamp}}
conversation_store = {}

# Configuration
MAX_HISTORY_MESSAGES = 20  # Keep last 20 messages per session
SESSION_TIMEOUT = 3600  # 1 hour timeout for inactive sessions

# ============================================================================
# Token Storage (in-memory, survives for lifetime of proxy server)
# ============================================================================
# This allows the UI to work without sending token every request
# Token is set via /api/set-token endpoint or read from Secrets Manager on startup
STORED_TOKEN = None

def get_stored_token():
    """Get stored token (from memory or Secrets Manager)"""
    global STORED_TOKEN
    if STORED_TOKEN and len(STORED_TOKEN) > 50:
        return STORED_TOKEN

    # Try to load from Secrets Manager on first call
    try:
        import boto3
        secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)
        response = secrets_client.get_secret_value(SecretId='projectforce/api/credentials')
        secret = json.loads(response['SecretString'])
        token = secret.get('pf_token', '') or secret.get('bearer_token', '')
        if token and len(token) > 50:
            STORED_TOKEN = token
            logger.info(f"Loaded token from Secrets Manager (length: {len(token)})")
            return STORED_TOKEN
    except Exception as e:
        logger.warning(f"Could not load token from Secrets Manager: {e}")

    return None

def set_stored_token(token):
    """Set stored token in memory"""
    global STORED_TOKEN
    if token and len(token) > 50:
        STORED_TOKEN = token
        logger.info(f"Token stored in memory (length: {len(token)})")
        return True
    return False

def get_conversation_history(session_id):
    """Get conversation history for a session"""
    if session_id not in conversation_store:
        conversation_store[session_id] = {
            'messages': [],
            'last_activity': time.time()
        }
    return conversation_store[session_id]['messages']

def add_to_conversation_history(session_id, role, content, metadata=None):
    """Add a message to conversation history"""
    if session_id not in conversation_store:
        conversation_store[session_id] = {
            'messages': [],
            'last_activity': time.time()
        }

    message = {
        'role': role,  # 'user' or 'assistant'
        'content': content,
        'timestamp': time.time(),
        'metadata': metadata or {}
    }

    conversation_store[session_id]['messages'].append(message)
    conversation_store[session_id]['last_activity'] = time.time()

    # Trim history if too long
    if len(conversation_store[session_id]['messages']) > MAX_HISTORY_MESSAGES:
        conversation_store[session_id]['messages'] = conversation_store[session_id]['messages'][-MAX_HISTORY_MESSAGES:]

    logger.debug(f"Added to history for {session_id}: {role} - {content[:100]}...")

def cleanup_old_sessions():
    """Remove sessions that have been inactive for too long"""
    current_time = time.time()
    sessions_to_remove = []

    for session_id, session_data in conversation_store.items():
        if current_time - session_data['last_activity'] > SESSION_TIMEOUT:
            sessions_to_remove.append(session_id)

    for session_id in sessions_to_remove:
        del conversation_store[session_id]
        logger.info(f"Cleaned up inactive session: {session_id}")

    return len(sessions_to_remove)

def extract_location_from_history(conversation_history):
    """
    Extract location from conversation history by looking for addresses in project data
    Returns: city name or None
    """
    import re

    if not conversation_history:
        logger.debug("No conversation history available")
        return None

    logger.debug(f"Scanning {len(conversation_history)} messages for location...")

    # Look through recent assistant messages for project addresses
    for msg in reversed(conversation_history):
        if msg['role'] != 'assistant':
            continue

        content = msg['content']

        # Try to parse JSON responses that might contain project addresses
        try:
            # Extract JSON from markdown block or direct JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                logger.debug("Found JSON in markdown block")
            elif content.strip().startswith('{'):
                data = json.loads(content)
                logger.debug("Found direct JSON")
            else:
                continue

            # Check for project details with address
            if 'project' in data and 'address' in data['project']:
                addr = data['project']['address']
                if isinstance(addr, dict) and 'city' in addr:
                    return addr['city']
                elif isinstance(addr, str):
                    # Parse address string format: "401 Chicago Avenue, MN, Minneapolis-55415"
                    parts = addr.split(',')
                    if len(parts) >= 3:
                        # City is usually before the zip code
                        city_part = parts[-1].strip()
                        city_match = re.search(r'^([A-Za-z\s]+)-\d+', city_part)
                        if city_match:
                            return city_match.group(1).strip()

            # Check for project list with addresses
            if 'projects' in data and isinstance(data['projects'], list) and len(data['projects']) > 0:
                logger.debug(f"Found projects list with {len(data['projects'])} projects")
                first_project = data['projects'][0]
                if 'address' in first_project:
                    addr = first_project['address']
                    logger.debug(f"Address type: {type(addr)}, keys: {addr.keys() if isinstance(addr, dict) else 'N/A'}")
                    if isinstance(addr, dict) and 'city' in addr:
                        city = addr['city']
                        logger.info(f"✅ Extracted city from project address: {city}")
                        return city
                    elif isinstance(addr, str):
                        parts = addr.split(',')
                        if len(parts) >= 3:
                            city_part = parts[-1].strip()
                            city_match = re.search(r'^([A-Za-z\s]+)-\d+', city_part)
                            if city_match:
                                city = city_match.group(1).strip()
                                logger.info(f"✅ Extracted city from address string: {city}")
                                return city

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.debug(f"JSON parse error: {e}")
            continue

    logger.debug("No location found in conversation history")
    return None

# Load agent configuration dynamically
def load_agent_config():
    """Load agent configuration from config/agent_config.dev.json"""
    # Try multiple possible paths (from testing/ui to bedrock/config)
    possible_paths = [
        Path(__file__).parent / "../../config/agent_config.dev.json",               # bedrock/testing/ui -> bedrock/config
        Path(__file__).resolve().parent.parent.parent / "config" / "agent_config.dev.json",  # Absolute path
        Path(__file__).parent.parent / "config" / "agent_config.dev.json",          # Alternative
    ]

    for config_path in possible_paths:
        try:
            resolved_path = config_path.resolve()
            if resolved_path.exists():
                logger.info(f"✅ Loading agent config from: {resolved_path}")
                with open(resolved_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Could not load from {config_path}: {e}")
            continue

    # Fallback to hardcoded values if config not found
    logger.warning("⚠️  Could not find agent_config.dev.json, using hardcoded values")
    logger.warning(f"⚠️  Tried paths: {[str(p) for p in possible_paths]}")
    return {
        "supervisor_id": "76VIQYAT6R",
        "supervisor_alias": "TSTALIASID"
    }

# Load configuration at startup
AGENT_CONFIG = load_agent_config()
logger.info(f"📋 Loaded Supervisor Agent: {AGENT_CONFIG.get('supervisor_id')}")
logger.info(f"📋 Loaded Supervisor Alias: {AGENT_CONFIG.get('supervisor_alias')}")


def format_lambda_response(action: str, response_body: dict) -> str:
    """
    Format Lambda response as human-readable text instead of raw JSON

    Args:
        action: The action that was performed (list_projects, get_project_details, etc.)
        response_body: The Lambda response body (parsed JSON)

    Returns:
        Formatted human-readable text
    """
    try:
        if action == 'list_projects':
            projects = response_body.get('projects', [])
            if not projects:
                return response_body.get('message', "You have no projects matching your criteria.")

            lines = [f"Found {len(projects)} project(s):\n"]
            for i, project in enumerate(projects, 1):
                status = project.get('status', 'Unknown')
                category = project.get('category', 'Not specified')
                project_type = project.get('projectType', 'Not specified')
                scheduled_date = project.get('scheduledDate', 'Not scheduled')
                address = project.get('address', {})
                city = address.get('city', '')
                state = address.get('state', '')
                location = f"{city}, {state}" if city and state else "No address"

                lines.append(f"{i}. Project {project.get('id', 'Unknown')}")
                lines.append(f"   Status: {status}")
                lines.append(f"   Category: {category}")
                lines.append(f"   Type: {project_type}")
                lines.append(f"   Scheduled: {scheduled_date}")
                lines.append(f"   Location: {location}")

                tech = project.get('technician', {})
                if tech and tech.get('name'):
                    lines.append(f"   Technician: {tech.get('name')} (#{tech.get('id', 'N/A')})")
                lines.append("")  # Empty line between projects

            return "\n".join(lines)

        elif action == 'get_project_details':
            project = response_body.get('project', {})
            if not project:
                return "Project details not found."

            lines = [f"Details for Project {project.get('id', 'Unknown')}:\n"]
            lines.append(f"Status: {project.get('status', 'Unknown')}")
            lines.append(f"Category: {project.get('category', 'Not specified')}")
            lines.append(f"Project Type: {project.get('projectType', 'Not specified')}")

            scheduled = project.get('scheduledDate', 'Not scheduled')
            lines.append(f"Scheduled Date: {scheduled}")

            address = project.get('address', {})
            if address:
                addr_parts = [
                    address.get('address1', ''),
                    address.get('city', ''),
                    address.get('state', ''),
                    address.get('zipcode', '')
                ]
                full_addr = ', '.join(filter(None, addr_parts))
                lines.append(f"Address: {full_addr}")

            tech = project.get('technician', {})
            if tech and tech.get('name'):
                lines.append(f"Technician: {tech.get('name')} (#{tech.get('id', 'N/A')})")

            return "\n".join(lines)

        elif action == 'get_available_dates':
            dates = response_body.get('available_dates', [])
            if not dates:
                return "No available dates found."

            lines = ["Available dates:\n"]
            for date in dates[:10]:  # Show first 10
                lines.append(f"  • {date}")

            if len(dates) > 10:
                lines.append(f"\n...and {len(dates) - 10} more dates")

            return "\n".join(lines)

        elif action == 'get_time_slots':
            slots = response_body.get('slots', [])
            if not slots:
                return "No available time slots found."

            lines = ["Available time slots:\n"]
            for slot in slots:
                start = slot.get('start', '')
                end = slot.get('end', '')
                lines.append(f"  • {start} - {end}")

            return "\n".join(lines)

        else:
            # For unknown actions, return JSON
            return json.dumps(response_body, indent=2)

    except Exception as e:
        logger.error(f"Response formatting error: {e}")
        # Fallback to JSON if formatting fails
        return json.dumps(response_body, indent=2)


def classify_intent_and_action(message, conversation_history=None):
    """
    Enhanced intent and action classification using Claude Sonnet with conversation context
    Returns: {'intent': 'scheduling', 'action': 'list_projects', 'can_call_direct': True}
    """
    import boto3

    # Build context from conversation history
    import re
    context_str = ""
    if conversation_history and len(conversation_history) > 0:
        context_str = "\n\nConversation history (most recent last):\n"
        # Include last 3 messages for context (enough for list + question)
        recent_history = conversation_history[-3:]
        for msg in recent_history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            content = msg['content']
            # For assistant messages with JSON, extract just the project IDs for efficiency
            if role == "Assistant" and '"projects"' in content and len(content) > 1000:
                # Parse JSON properly to extract only project-level IDs
                try:
                    # Try to extract JSON from markdown code block if present
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # Try direct JSON parse
                        json_str = content

                    data = json.loads(json_str)
                    project_ids = [str(p['id']) for p in data.get('projects', [])]
                    if project_ids:
                        content = f"[Project list with IDs: {', '.join(project_ids[:10])}]"  # First 10 IDs
                except Exception as e:
                    # Fallback to regex if JSON parsing fails
                    logger.warning(f"JSON parsing failed, using regex fallback: {e}")
                    # More specific regex that looks for id at the beginning of object definitions
                    project_ids = re.findall(r'"projects"\s*:\s*\[(?:[^]]*?"id"\s*:\s*"(\d+)"[^]]*?)+\]', content)
                    if project_ids:
                        content = f"[Project list with IDs: {', '.join(project_ids[:10])}]"
            else:
                content = content[:500]  # Allow more context for non-project-list messages
            context_str += f"{role}: {content}\n"

    prompt = f"""You are an intent classifier for a property management scheduling system.

Classify the user message and determine if we can call Lambda directly or need an agent.
{context_str}
Current user message: "{message}"

Respond in JSON format with FOUR fields:
1. intent: scheduling/information/chitchat
2. action: specific action name (or null if needs agent conversation)
3. can_call_direct: true/false
4. params: object with extracted parameters (or null if none)

⚠️ INTENT CATEGORIES ⚠️

**SCHEDULING intent:**
- Anything related to projects, appointments, dates, times, booking
- Examples: "show my projects", "schedule project 123", "available dates"

**INFORMATION intent:**
- Weather queries
- Project information lookups
- External data queries
- Examples: "what's the weather", "weather in Tampa", "forecast for tomorrow"

**CHITCHAT intent:**
- Greetings, thanks, casual conversation
- Examples: "hello", "thank you", "how are you"

⚠️ CRITICAL RULE: UNDERSTAND SEMANTIC INTENT ⚠️

Think about what the user is TRYING TO DO, not just the words they use:

**QUERY Intent (can_call_direct=TRUE):**
- User wants to SEE/VIEW/GET information
- User is ASKING ABOUT something
- User wants to KNOW/CHECK/DISPLAY data
- Examples of query intent:
  * "show my projects" (wants to VIEW)
  * "what projects do I have" (wants to KNOW)
  * "details for project 123" (wants to SEE)
  * "available dates for project 456" (wants to CHECK)
  * "what times are free on Nov 14" (wants to KNOW)

**ACTION Intent (can_call_direct=FALSE):**
- User wants to DO something / MAKE A CHANGE
- User wants to CREATE/MODIFY/DELETE an appointment
- User is requesting an operation that changes state
- User needs confirmation before proceeding
- Examples of action intent:
  * "schedule project 123" (wants to CREATE appointment)
  * "book the last project" (wants to CREATE appointment)
  * "I want to set up an appointment" (wants to CREATE)
  * "reschedule my meeting" (wants to MODIFY)
  * "cancel my appointment" (wants to DELETE)
  * "let's go with Nov 14" (implicit booking confirmation)
  * "yes, book it" (confirmation of action)

**How to decide:**
1. Ask yourself: "Is the user asking for information, or asking to do something?"
2. If ASKING FOR INFO → can_call_direct=true
3. If REQUESTING AN ACTION → can_call_direct=false

Even if the message doesn't contain explicit action verbs, use semantic understanding:
- "I'll take project 123 for tomorrow" → ACTION (implied booking)
- "Can you tell me about project 123" → QUERY (asking for info)
- "Let's go with 2pm on Friday" → ACTION (implicit confirmation)
- "What times work for Friday" → QUERY (asking for info)

DIRECT Lambda actions (QUERIES ONLY - simple data retrieval):

list_projects:
- Examples: "show my projects", "list projects", "what projects do I have", "display projects"
- MUST be pure queries (show/list/get/display)
- NO action verbs allowed
- IMPORTANT: Extract filter parameters if mentioned:
  * status: "scheduled", "new", "completed", "pending", etc.
    Examples: "show scheduled projects", "list new projects", "my completed projects"
  * category: "Decking", "Flooring", "Kitchen", "Bathroom", etc.
    Examples: "show decking projects", "my flooring jobs"
  * projectType: "Call Back", "Installation", "Repair", etc.
    Examples: "list call back projects", "show installation jobs"
- Response: intent=scheduling, action=list_projects, can_call_direct=true, params={{status/category/projectType if found, otherwise null}}

get_project_details:
- Examples: "show details for 7751742", "details for project 123", "show me project 7751742"
- MUST be pure queries
- CRITICAL FOR POSITION REFERENCES: "2nd project", "3rd one", "first project", "details for 2"
- When user uses ordinal/position reference (1st, 2nd, 3rd, first, second, etc):
  * Look in conversation history for project IDs
  * Extract the Nth project ID from that list
  * DO NOT use the number as project_id - extract the actual ID!
  * Example: History has [7751741, 7751742, 7751743], user says "2nd project" → use "7751742"
- If you CANNOT find project IDs in history for a position reference:
  * Set can_call_direct=false (needs agent to handle ambiguity)
- Response: intent=scheduling, action=get_project_details, can_call_direct=true, params with ACTUAL project_id

get_available_dates:
- Examples: "show dates for project 123", "available dates", "when can I schedule project 456", "what dates are available"
- MUST be pure queries asking ABOUT availability (not BOOKING)
- Extract project_id if mentioned
- Response: intent=scheduling, action=get_available_dates, can_call_direct=true, params with project_id if found

get_time_slots:
- Examples: "show times for Nov 14", "available slots for Nov 14", "what times on November 14"
- ONLY when user is ASKING about time slots, NOT booking
- Extract date from message
- CRITICAL: If conversation history shows available dates for a project, extract that project_id too
- Response: intent=scheduling, action=get_time_slots, can_call_direct=true, params with date AND project_id if found in context

NEEDS AGENT (requires conversation/confirmation/actions):
- ❌ ANY message with "schedule", "book", "reserve" → can_call_direct=FALSE
  Examples: "schedule the last project", "book project 123", "I want to schedule"
- ❌ ANY message with "reschedule", "change appointment", "move" → can_call_direct=FALSE
- ❌ ANY message with "cancel", "delete appointment" → can_call_direct=FALSE
- ❌ Confirmations: "yes", "confirm", "go ahead" → can_call_direct=FALSE
- ❌ Chitchat: conversational → can_call_direct=FALSE
- ❌ Information queries: weather, etc. → can_call_direct=FALSE

Example JSON responses (respond with VALID JSON only):

Example 1 - Query intent (Direct Lambda):
For "show details for 7751742":
{{"intent":"scheduling","action":"get_project_details","can_call_direct":true,"params":{{"project_id":"7751742"}}}}
Reasoning: User wants to VIEW information → QUERY

Example 2 - Query with position reference (Direct Lambda):
History shows: projects with ids ["7751741", "7751742", "7751743", ...]
For "show me the 3rd project":
{{"intent":"scheduling","action":"get_project_details","can_call_direct":true,"params":{{"project_id":"7751743"}}}}
Reasoning: User wants to SEE info → QUERY. "3rd project" = id at index 2 = "7751743"

Example 3 - Action intent with verb (Agent):
For "schedule the last project for Nov 13":
{{"intent":"scheduling","action":null,"can_call_direct":false,"params":null}}
Reasoning: User wants to CREATE appointment → ACTION (needs confirmation, multi-step)

Example 4 - Action intent without explicit verb (Agent):
For "I'll take the 2pm slot on Friday":
{{"intent":"scheduling","action":null,"can_call_direct":false,"params":null}}
Reasoning: User is COMMITTING to booking → ACTION (even without "book" or "schedule" verb)

Example 5 - Query about availability (Direct Lambda):
For "what dates are free for project 123":
{{"intent":"scheduling","action":"get_available_dates","can_call_direct":true,"params":{{"project_id":"123"}}}}
Reasoning: User wants to CHECK availability → QUERY (asking, not booking)

Example 6 - Confirmation intent (Agent):
For "yes, that works":
{{"intent":"scheduling","action":null,"can_call_direct":false,"params":null}}
Reasoning: Confirmation of previous action → needs agent context

Example 7 - Query with conversational phrasing (Direct Lambda):
For "can you tell me what projects I have":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":null}}
Reasoning: Polite phrasing but semantic intent is VIEW/GET info → QUERY

Example 8 - Information intent (Agent):
For "what's the weather in Tampa":
{{"intent":"information","action":null,"can_call_direct":false,"params":null}}
Reasoning: Weather query → INFORMATION intent (will route to Information Agent)

Example 9 - Chitchat (Agent):
For "hello":
{{"intent":"chitchat","action":null,"can_call_direct":false,"params":null}}

Example 10 - Query with status filter (Direct Lambda):
For "show the scheduled projects":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":{{"status":"Scheduled"}}}}
Reasoning: User wants to VIEW filtered list → QUERY with filter

Example 11 - Query with category filter (Direct Lambda):
For "list my decking projects":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":{{"category":"Decking"}}}}
Reasoning: User wants to VIEW category-specific projects → QUERY with filter

Example 12 - Query with multiple filters (Direct Lambda):
For "show scheduled decking projects":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":{{"status":"Scheduled","category":"Decking"}}}}
Reasoning: User wants to VIEW with multiple filters → QUERY with multiple params

Remember: Focus on WHAT THE USER WANTS TO ACCOMPLISH, not the exact words they use.
Weather queries ALWAYS go to "information" intent, NOT "chitchat".
For filters: Match natural language to field values (e.g., "scheduled" → "Scheduled", "call back" → "Call Back").

Respond ONLY with the JSON object, nothing else."""

    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        response = bedrock_runtime.invoke_model(
            modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,  # Increased to allow context reasoning and JSON response
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        classification_text = response_body['content'][0]['text'].strip()

        # Debug: log what the model returned
        logger.info(f"Raw classification response: {classification_text}")

        # Parse JSON response
        classification = json.loads(classification_text)

        logger.info(f"Classification: {classification} for message: '{message[:50]}...'")
        return classification

    except Exception as e:
        logger.error(f"Classification error: {e}")
        logger.error(f"Failed to parse classification text: {classification_text if 'classification_text' in locals() else 'N/A'}")
        # Fallback: return chitchat with no direct call
        return {'intent': 'chitchat', 'action': None, 'can_call_direct': False}


def classify_intent_simple(message):
    """
    Simple intent classification (legacy compatibility)
    Returns: 'scheduling', 'information', or 'chitchat'
    """
    classification = classify_intent_and_action(message)
    return classification['intent']


def call_lambda_directly(action, params):
    """
    Call Lambda function directly for simple actions
    Returns: Lambda response payload
    """
    import boto3

    lambda_client = boto3.client('lambda', region_name=AWS_REGION)

    # Map action to Lambda function
    lambda_functions = {
        'list_projects': 'pf-scheduling-actions',
        'get_project_details': 'pf-scheduling-actions',
        'get_available_dates': 'pf-scheduling-actions',
        'get_time_slots': 'pf-scheduling-actions'
    }

    function_name = lambda_functions.get(action)
    if not function_name:
        raise ValueError(f"Unknown action: {action}")

    # Construct Lambda event (Bedrock agent format)
    # Note: Lambda expects 'function' to be the action name
    event = {
        'actionGroup': 'scheduling-actions',
        'function': action,  # This is what Lambda uses to route
        'parameters': [
            {'name': key, 'value': str(value)}
            for key, value in params.items()
            if key not in ['customer_id', 'client_id', 'pf_bearer_token']
        ],
        'sessionAttributes': {
            'customer_id': params.get('customer_id', ''),
            'client_id': params.get('client_id', ''),
            'pf_bearer_token': params.get('pf_bearer_token', '')
        }
    }

    logger.debug(f"Lambda event: {json.dumps(event, indent=2)}")

    logger.info(f"⚡ Calling Lambda directly: {function_name}.{action}")

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        payload = json.loads(response['Payload'].read())
        logger.info(f"✅ Lambda direct call successful")
        return payload

    except Exception as e:
        logger.error(f"Lambda direct call error: {e}")
        raise


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "pf-proxy",
        "active_sessions": len(conversation_store),
        "features": {
            "direct_lambda": True,
            "conversation_history": True
        }
    })


@app.route('/api/conversation-history/<session_id>', methods=['GET'])
def get_session_history(session_id):
    """Get conversation history for a session (debugging endpoint)"""
    history = get_conversation_history(session_id)
    return jsonify({
        "session_id": session_id,
        "message_count": len(history),
        "messages": history
    })


@app.route('/api/login', methods=['POST'])
def login():
    """
    Proxy for login endpoint with token validation and refresh

    SINGLE SOURCE OF TRUTH: Secrets Manager
    1. Load bearer_token from Secrets Manager
    2. Validate the token (check if it works)
    3. If expired, perform fresh login with password
    4. Save fresh token back to Secrets Manager
    5. Return valid token to UI
    """
    try:
        import boto3
        import time

        data = request.json
        email = data.get('email', '')
        password = data.get('password', '')
        logger.info(f"Login request for: {email}")

        secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)

        # Step 1: Try to load existing token from Secrets Manager
        try:
            secret_response = secrets_client.get_secret_value(SecretId='projectforce/api/credentials')
            credentials = json.loads(secret_response['SecretString'])

            client_id = credentials.get('client_id', '09PF05VD')
            user_id = credentials.get('user_id', '1646085')
            bearer_token = credentials.get('bearer_token', '')

            logger.info(f"✓ Loaded credentials from Secrets Manager: client_id={client_id}, user_id={user_id}")
            logger.info(f"✓ Bearer token loaded (length: {len(bearer_token)})")

            # Step 2: Validate the token - try to use it against the DASHBOARD API
            # (not auth endpoint, which returns 200 for stale tokens)
            if bearer_token and len(bearer_token) > 100:
                logger.info("⏳ Validating existing token against dashboard API...")
                validation_response = requests.get(
                    f"{PF_API_BASE}/dashboard/get/{client_id}/{user_id}",
                    headers={
                        "Authorization": f"Bearer {bearer_token}",
                        "Content-Type": "application/json",
                        "client_id": client_id
                    },
                    timeout=5
                )

                if validation_response.status_code == 200:
                    logger.info("✓ Token is valid, returning existing token")
                    result = {
                        "accesstoken": bearer_token,  # UI expects "accesstoken" not "token"
                        "user": {
                            "customer_id": str(user_id),
                            "client_id": client_id
                        },
                        "email": email,
                        "success": True
                    }
                    return jsonify(result), 200
                else:
                    logger.warning(f"⚠️  Token validation failed (status: {validation_response.status_code}), need to refresh")

        except Exception as load_err:
            logger.warning(f"Could not load/validate existing token: {load_err}")

        # Step 3: Token expired or not found - perform fresh login
        logger.info("🔄 Performing fresh login with password...")

        # Try actual PF360 login API
        login_response = requests.post(
            f"{PF_API_BASE}/authentication/login",
            params={"identifier": "projectsforce-validation"},
            json={
                "email": email,
                "password": password
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        logger.info(f"Login response status: {login_response.status_code}")
        logger.info(f"Login response Content-Type: {login_response.headers.get('Content-Type', 'unknown')}")

        # Check if we got JSON back (not HTML)
        content_type = login_response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            logger.error(f"PF360 login API returned non-JSON: {content_type}")
            return jsonify({
                "error": "Login API returned invalid response",
                "details": "PF360 API is not returning JSON. Please contact support."
            }), 500

        if login_response.status_code == 200:
            login_data = login_response.json()

            # Check if OTP verification is required
            if login_data.get('isOtpVerified') == False and login_data.get('otp_token'):
                logger.info("🔐 OTP verification required, fetching OTP from Mailinator...")
                otp_token = login_data.get('otp_token')

                # Extract username from email (e.g., "jay@mailinator.com" -> "jay")
                mailinator_inbox = email.split('@')[0] if '@' in email else 'jay'
                otp_code = None

                # Fetch OTP from Mailinator
                try:
                    # Wait a moment for email to arrive
                    import time as time_module
                    time_module.sleep(2)

                    # Get latest messages from Mailinator inbox
                    mailinator_url = f"https://www.mailinator.com/api/v2/domains/public/inboxes/{mailinator_inbox}"
                    mail_response = requests.get(mailinator_url, timeout=10)

                    if mail_response.status_code == 200:
                        mail_data = mail_response.json()
                        messages = mail_data.get('msgs', [])

                        if messages:
                            # Get the most recent message
                            latest_msg = messages[0]
                            msg_id = latest_msg.get('id')

                            # Fetch message content
                            msg_url = f"https://www.mailinator.com/api/v2/domains/public/inboxes/{mailinator_inbox}/messages/{msg_id}"
                            msg_response = requests.get(msg_url, timeout=10)

                            if msg_response.status_code == 200:
                                msg_data = msg_response.json()
                                # Look for OTP in message body - typically 6 digits
                                import re
                                body = str(msg_data.get('parts', [{}])[0].get('body', ''))
                                # Find 6-digit OTP code
                                otp_match = re.search(r'\b(\d{6})\b', body)
                                if otp_match:
                                    otp_code = otp_match.group(1)
                                    logger.info(f"✓ Found OTP code from Mailinator: {otp_code}")
                except Exception as mail_err:
                    logger.warning(f"Could not fetch OTP from Mailinator: {mail_err}")

                # Try OTP codes - first from Mailinator, then fallback to common test codes
                codes_to_try = [otp_code] if otp_code else []
                codes_to_try.extend(['123456', '000000', '111111'])

                verified = False
                for code in codes_to_try:
                    if not code:
                        continue
                    try:
                        otp_response = requests.post(
                            f"{PF_API_BASE}/authentication/verify-otp",
                            params={"identifier": "projectsforce-validation"},
                            json={
                                "otp": code,
                                "otp_token": otp_token
                            },
                            headers={"Content-Type": "application/json"},
                            timeout=10
                        )

                        if otp_response.status_code == 200:
                            otp_data = otp_response.json()
                            fresh_token = otp_data.get('accesstoken', otp_data.get('access_token', ''))
                            if fresh_token and len(fresh_token) > 100:
                                logger.info(f"✓ OTP verification successful with code {code}")
                                login_data = otp_data  # Use OTP response data
                                verified = True
                                break
                    except Exception as otp_err:
                        logger.warning(f"OTP verification with {code} failed: {otp_err}")
                        continue

                if not verified:
                    # None of the OTP codes worked - return error asking user to handle manually
                    logger.error("OTP verification required but auto-verify failed")
                    return jsonify({
                        "error": "OTP verification required",
                        "otp_token": otp_token,
                        "details": "Please verify OTP manually or disable OTP for test account"
                    }), 401

            # API returns 'accesstoken' (no underscore) - check all variants
            fresh_token = login_data.get('accesstoken', login_data.get('access_token', login_data.get('token', '')))

            if not fresh_token or len(fresh_token) < 100:
                logger.error(f"Login successful but no valid token in response: {login_data}")
                return jsonify({
                    "error": "Login succeeded but no valid token received",
                    "details": str(login_data)
                }), 500

            logger.info(f"✓ Fresh login successful (token length: {len(fresh_token)})")

            # Step 4: Save fresh token to Secrets Manager
            try:
                # Get client_id and user_id from login response (inside 'user' object)
                user_data = login_data.get('user', {})
                response_client_id = user_data.get('client_id', credentials.get('client_id', '09PF05VD'))
                response_user_id = user_data.get('customer_id', user_data.get('user_id', credentials.get('user_id', '1646085')))

                secret_value = {
                    "bearer_token": fresh_token,
                    "client_id": response_client_id,
                    "user_id": str(response_user_id),
                    "api_base_url": PF_API_BASE,
                    "REFRESH_TOKEN": "true",
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "updated_by": "pf_proxy.py login"
                }

                # Try put first, create if doesn't exist
                try:
                    secrets_client.put_secret_value(
                        SecretId='projectforce/api/credentials',
                        SecretString=json.dumps(secret_value)
                    )
                except secrets_client.exceptions.ResourceNotFoundException:
                    secrets_client.create_secret(
                        Name='projectforce/api/credentials',
                        Description='ProjectForce API credentials for scheduling agent',
                        SecretString=json.dumps(secret_value)
                    )
                    logger.info("Created new secret: projectforce/api/credentials")
                logger.info("Fresh token saved to Secrets Manager")
            except Exception as save_err:
                logger.error(f"Failed to save token to Secrets Manager: {save_err}")
                # Continue anyway - UI can still use the token

            # Step 5: Return fresh token to UI (match UI field names!)
            result = {
                "accesstoken": fresh_token,  # UI expects "accesstoken" not "token"
                "user": {
                    "customer_id": str(response_user_id),
                    "client_id": response_client_id
                },
                "email": email,
                "success": True
            }
            logger.info("✓ Login successful, returning fresh token to UI")
            return jsonify(result), 200
        else:
            logger.error(f"Login failed: {login_response.status_code}")
            logger.error(f"Response: {login_response.text[:500]}")
            return jsonify({
                "error": "Login failed",
                "status_code": login_response.status_code,
                "details": login_response.text[:200]
            }), login_response.status_code

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/set-token', methods=['POST'])
def api_set_token():
    """Set token in memory AND update AWS Secrets Manager (for voice/Lambda)"""
    try:
        data = request.json or {}
        token = data.get('token', data.get('access_token', data.get('bearer_token', '')))
        update_secrets = data.get('update_secrets', True)  # Default: also update Secrets Manager

        if not token or len(token) < 50:
            return jsonify({"error": "Invalid token (must be > 50 chars)"}), 400

        # Store in memory
        memory_success = set_stored_token(token)

        # Also update Secrets Manager (for voice/Lambda calls)
        secrets_success = False
        secrets_error = None
        if update_secrets:
            try:
                import boto3
                secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)

                # Get existing secret to preserve other fields
                try:
                    existing = secrets_client.get_secret_value(SecretId='projectforce/api/credentials')
                    secret_data = json.loads(existing['SecretString'])
                except:
                    secret_data = {}

                # Update bearer_token while preserving other fields
                secret_data['bearer_token'] = token
                secret_data['client_id'] = secret_data.get('client_id', '09PF05VD')
                secret_data['REFRESH_TOKEN'] = secret_data.get('REFRESH_TOKEN', 'true')
                secret_data['environment'] = secret_data.get('environment', 'dev')

                # Try update first, create if doesn't exist
                try:
                    secrets_client.update_secret(
                        SecretId='projectforce/api/credentials',
                        SecretString=json.dumps(secret_data)
                    )
                    logger.info("Token updated in AWS Secrets Manager")
                except secrets_client.exceptions.ResourceNotFoundException:
                    # Secret doesn't exist, create it
                    secrets_client.create_secret(
                        Name='projectforce/api/credentials',
                        Description='ProjectForce API credentials for scheduling agent',
                        SecretString=json.dumps(secret_data)
                    )
                    logger.info("Token saved to NEW Secrets Manager secret")
                secrets_success = True
            except Exception as e:
                secrets_error = str(e)
                logger.error(f"Failed to update Secrets Manager: {e}")

        if memory_success:
            return jsonify({
                "success": True,
                "message": "Token stored",
                "token_length": len(token),
                "memory": True,
                "secrets_manager": secrets_success,
                "secrets_error": secrets_error
            }), 200
        else:
            return jsonify({"error": "Failed to store token"}), 500

    except Exception as e:
        logger.error(f"Set token error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/get-token-status', methods=['GET'])
def api_get_token_status():
    """Check if a valid token is stored"""
    token = get_stored_token()
    if token:
        return jsonify({
            "has_token": True,
            "token_length": len(token),
            "token_preview": f"{token[:20]}...{token[-20:]}"
        }), 200
    else:
        return jsonify({"has_token": False}), 200


@app.route('/api/regenerate-token', methods=['POST'])
def regenerate_token():
    """Regenerate token using client_id and user_id"""
    try:
        data = request.json or {}
        user_id = data.get('user_id', '1646085')
        client_id = data.get('client_id', '09PF05VD')

        logger.info(f"Regenerating token for user: {user_id}, client: {client_id}")

        response = requests.post(
            "https://auth.dev.projectsforce.com/regenerate-token",
            json={
                "client_id": client_id,
                "user_id": user_id,
                "login_via_password": False,
                "client_secret": "devappssecret",
                "device_type": "web",
                "grant_type": "authorization_code",
                "secret_client_id": "devapps"
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        logger.info(f"Regenerate response status: {response.status_code}")

        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            logger.error(f"Failed to regenerate token: {response.text[:200]}")
            return jsonify({"error": "Failed to regenerate token"}), response.status_code

    except Exception as e:
        logger.error(f"Regenerate token error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/save-token-to-secrets', methods=['POST'])
def save_token_to_secrets():
    """Save current token to AWS Secrets Manager"""
    try:
        data = request.json or {}
        access_token = data.get('access_token', '')
        client_id = data.get('client_id', '09PF05VD')
        customer_id = data.get('customer_id', '1646085')

        if not access_token or len(access_token) < 100:
            return jsonify({"error": "Invalid token"}), 400

        # ALSO set token in memory (same as /api/set-token)
        set_stored_token(access_token)
        logger.info(f"Saving token to Secrets Manager AND memory (length: {len(access_token)})")

        import boto3
        import time

        secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)
        # Use environment-aware URL
        api_url = PF_API_BASE
        logger.info(f"📝 Using API URL for {ENVIRONMENT}: {api_url}")

        # Helper function to create or update secret
        def save_secret(secret_id, secret_name, secret_data, description):
            try:
                secrets_client.put_secret_value(
                    SecretId=secret_id,
                    SecretString=json.dumps(secret_data)
                )
            except secrets_client.exceptions.ResourceNotFoundException:
                # Secret doesn't exist, create it
                secrets_client.create_secret(
                    Name=secret_name,
                    Description=description,
                    SecretString=json.dumps(secret_data)
                )
                logger.info(f"Created new secret: {secret_name}")

        # Update target secret
        secret_value = {
            "pf_token": access_token,
            "client_id": client_id,
            "customer_id": customer_id,
            "api_url": api_url,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "updated_by": "pf_proxy.py",
            "notes": "Saved from UI login"
        }

        save_secret(
            'scheduling-agent/pf360/api-credentials',
            'scheduling-agent/pf360/api-credentials',
            secret_value,
            'ProjectForce API credentials (target)'
        )

        # Also update source secret
        source_secret = {
            "bearer_token": access_token,
            "client_id": client_id,
            "user_id": customer_id,
            "api_base_url": api_url
        }

        save_secret(
            'projectforce/api/credentials',
            'projectforce/api/credentials',
            source_secret,
            'ProjectForce API credentials for scheduling agent'
        )

        logger.info("Token saved to both secrets")

        return jsonify({"status": "success", "message": "Token saved to AWS Secrets Manager"}), 200

    except Exception as e:
        logger.error(f"Save token error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/validate-token', methods=['GET'])
def validate_token():
    """Proxy for token validation endpoint"""
    try:
        user_id = request.args.get('user_id', '1646085')
        identifier = request.args.get('identifier', 'projectsforce-validation')
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        logger.info(f"Validating token for user: {user_id}")

        response = requests.get(
            f"{PF_API_BASE}/authentication/token/{user_id}",
            params={"identifier": identifier},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )

        logger.info(f"Validation response status: {response.status_code}")

        return jsonify(response.json()), response.status_code

    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    """Proxy for dashboard/projects endpoint"""
    try:
        client_id = request.args.get('client_id', '09PF05VD')
        user_id = request.args.get('user_id', '1646085')
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        logger.info(f"Fetching dashboard for client: {client_id}, user: {user_id}")

        response = requests.get(
            f"{PF_API_BASE}/dashboard/get/{client_id}/{user_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )

        logger.info(f"Dashboard response status: {response.status_code}")

        return jsonify(response.json()), response.status_code

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/invoke-agent', methods=['POST'])
def invoke_agent():
    """Proxy for invoking AWS Bedrock agent with streaming support"""
    try:
        import boto3

        # START PERFORMANCE TRACKING
        request_start = time.time()
        timing = {}

        data = request.json
        message = data.get('message', '')
        session_id = data.get('session_id', 'session-default')
        pf_token = data.get('pf_token', '')
        pf_client_id = data.get('pf_client_id', '09PF05VD')
        pf_user_id = data.get('pf_user_id', '1646085')
        stream = data.get('stream', False)  # Support both streaming and non-streaming

        # Use stored token if not provided in request
        if not pf_token or len(pf_token) < 50:
            stored = get_stored_token()
            if stored:
                pf_token = stored
                logger.info(f"Using stored token (length: {len(pf_token)})")
            else:
                logger.warning("No token provided and no stored token available")

        logger.info(f"Invoking Bedrock agent with message: {message[:50]}... (stream={stream})")

        # Cleanup old sessions periodically
        cleanup_old_sessions()

        # Get conversation history for this session
        conversation_history = get_conversation_history(session_id)
        logger.info(f"📚 Session {session_id} has {len(conversation_history)} messages in history")

        # Add user message to history
        add_to_conversation_history(session_id, 'user', message)

        # Initialize Bedrock client
        init_start = time.time()
        bedrock_client = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
        timing['boto3_init'] = time.time() - init_start

        # Determine routing based on config
        routing_config = AGENT_CONFIG.get('routing', {})
        use_supervisor = routing_config.get('use_supervisor', False)
        allow_direct_lambda = routing_config.get('allow_direct_lambda', True)  # NEW: enable direct Lambda calls

        # ALWAYS route through orchestrator (no direct Lambda calls from proxy)
        # Orchestrator handles: Direct Lambda optimization + context resolution + formatting
        logger.info(f"🎯 Routing ALL requests to LAMBDA ORCHESTRATOR: pf-orchestrator")

        try:
            lambda_start = time.time()
            lambda_client = boto3.client('lambda', region_name=AWS_REGION)

            # Prepare orchestrator event (API Gateway format)
            request_body = {
                'message': message,
                'session_id': session_id,
                'pf_token': pf_token,
                'pf_client_id': pf_client_id,
                'pf_user_id': str(pf_user_id)
            }

            orchestrator_event = {
                'body': json.dumps(request_body),  # API Gateway wraps body as JSON string
                'headers': {
                    'Content-Type': 'application/json'
                }
            }

            logger.info(f"📤 Invoking pf-orchestrator for message: '{message[:50]}...'")

            # Invoke Lambda orchestrator (use function name without version qualifier)
            orchestrator_function = AGENT_CONFIG.get('orchestrator_function', 'pf-orchestrator')
            response = lambda_client.invoke(
                FunctionName=orchestrator_function,
                InvocationType='RequestResponse',
                Payload=json.dumps(orchestrator_event)
            )

            payload = json.loads(response['Payload'].read())
            timing['orchestrator_lambda'] = time.time() - lambda_start
            timing['total_request'] = time.time() - request_start

            logger.info(f"⏱️  PERFORMANCE: Total={timing['total_request']:.2f}s | Orchestrator={timing['orchestrator_lambda']:.2f}s")

            # Extract response from orchestrator (API Gateway format)
            # Orchestrator returns: {statusCode: 200, body: "{\"response\": \"...\"}", ...}
            status_code = payload.get('statusCode', 200)

            if status_code != 200:
                # Error response
                error_body = payload.get('body', '{}')
                if isinstance(error_body, str):
                    error_body = json.loads(error_body)
                error_msg = error_body.get('error', 'Unknown error from orchestrator')
                raise Exception(f"Orchestrator error ({status_code}): {error_msg}")

            # Parse the body (it's a JSON string)
            body_str = payload.get('body', '{}')
            if isinstance(body_str, str):
                body = json.loads(body_str)
            else:
                body = body_str

            # Extract the response text
            response_text = body.get('response', str(body))
            agent_name_from_orch = body.get('agent_name', 'Orchestrator')
            action = body.get('action')
            intent = body.get('intent', 'unknown')

            logger.info(f"📝 Orchestrator response: {str(response_text)[:100]}...")

            # Add orchestrator response to conversation history
            add_to_conversation_history(
                session_id,
                'assistant',
                str(response_text),
                metadata={
                    'agent_name': agent_name_from_orch,
                    'intent': intent,
                    'action': action,
                    'performance': timing
                }
            )

            # Include projects array if returned by orchestrator (for welcome/list_projects)
            projects = body.get('projects', [])
            if projects:
                logger.info(f"📋 Returning {len(projects)} projects to UI")

            return jsonify({
                "response": str(response_text),
                "agent_name": agent_name_from_orch,
                "intent": intent,
                "action": action,
                "session_id": session_id,
                "performance": timing,
                "orchestrator": True,
                "projects": projects  # Pass through projects for UI rendering
            })

        except Exception as e:
            logger.error(f"Lambda Orchestrator error: {e}")
            # Return error response (no Bedrock fallback)
            return jsonify({
                "error": f"Orchestrator error: {str(e)}",
                "session_id": session_id
            }), 500

    except Exception as e:
        logger.error(f"Error in invoke-agent endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("=" * 80)
    print("🚀 ProjectForce API Proxy Server")
    print("=" * 80)
    print()
    print("Server running on: http://localhost:5003")
    print()
    print("Endpoints:")
    print("  POST   /api/login           - Login and get token")
    print("  GET    /api/validate-token  - Validate token")
    print("  GET    /api/dashboard       - Get dashboard/projects")
    print("  POST   /api/invoke-agent    - Invoke AWS Bedrock agent")
    print("  GET    /health              - Health check")
    print()
    print("=" * 80)
    print()

    app.run(host='0.0.0.0', port=5003, debug=True)
