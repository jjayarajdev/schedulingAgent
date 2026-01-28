"""
Sonnet Entity Enricher

Sonnet's ONLY job is to extract entities from user messages.
It CANNOT change the action - that's already determined by NLU + Guards.

This keeps Sonnet focused on what it's good at:
- Understanding natural language dates ("tomorrow", "next Tuesday")
- Extracting times ("2pm", "morning", "afternoon")
- Understanding slot selections ("the first one", "slot 3")
- Detecting confirmations ("yes", "sounds good", "let's do it")
- Extracting complex references ("the project at North Loop")

Enhanced with DSPy-learned examples for:
- Date interpretation (natural language to YYYY-MM-DD)
- Context resolution (pronouns, references)
- Response styling (voice/sms/chat adaptation)
- Slot ranking (preference + weather aware)
"""

import json
import logging
import boto3
from typing import Dict, Any, Optional, List
from botocore.config import Config as BotoConfig

logger = logging.getLogger()

# DSPy integration for enhanced prompts
try:
    from dspy_integration import (
        get_date_interpreter_few_shots,
        get_context_resolver_few_shots,
        get_slot_ranker_few_shots,
        get_response_style_few_shots
    )
    DSPY_ENRICHER_AVAILABLE = True
except ImportError:
    DSPY_ENRICHER_AVAILABLE = False
    def get_date_interpreter_few_shots(): return ""
    def get_context_resolver_few_shots(): return ""
    def get_slot_ranker_few_shots(): return ""
    def get_response_style_few_shots(channel="chat"): return ""

# Bedrock client (lazy init)
_bedrock_client = None


def get_bedrock_client():
    """Get or create Bedrock client"""
    global _bedrock_client
    if _bedrock_client is None:
        boto_config = BotoConfig(
            region_name='us-east-1',
            retries={"max_attempts": 3, "mode": "adaptive"}
        )
        _bedrock_client = boto3.client("bedrock-runtime", config=boto_config)
    return _bedrock_client


def call_sonnet(prompt: str, max_tokens: int = 500) -> str:
    """Call Sonnet 3.5 v2 for entity extraction"""
    bedrock = get_bedrock_client()

    try:
        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": 0,  # Deterministic for entity extraction
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]

    except Exception as e:
        logger.error(f"Sonnet enricher call failed: {e}")
        return "{}"


# ═══════════════════════════════════════════════════════════════════════════════
# ENTITY EXTRACTION PROMPTS - One per action type
# ═══════════════════════════════════════════════════════════════════════════════

PROMPTS = {
    # For date selection (after showing available dates)
    'get_time_slots': """Extract the DATE the user selected.

User message: "{message}"

Available dates shown to user:
{available_dates}

Extract:
- date: The date in YYYY-MM-DD format

Examples:
- "December 28" → {{"date": "2025-12-28"}}
- "the 28th" → {{"date": "2025-12-28"}}
- "tomorrow" → {{"date": "{tomorrow}"}}
- "the first one" → {{"date": "{first_available}"}}
- "next Tuesday" → {{"date": "2025-12-24"}}

Return ONLY valid JSON. If no date found, return {{"date": null}}""",

    # For time/slot selection (after showing time slots)
    'confirm_appointment': """Extract the TIME SLOT the user selected.

User message: "{message}"

Available slots shown to user:
{available_slots}

Extract:
- slot_id: The slot ID if user selected by number/position
- time: The time if user mentioned specific time

Examples:
- "2pm" → {{"time": "14:00"}}
- "the first one" → {{"slot_id": "1"}}
- "slot 3" → {{"slot_id": "3"}}
- "morning slot" → {{"time": "morning"}}
- "the 10am one" → {{"time": "10:00"}}

Return ONLY valid JSON. If unclear, return {{"slot_id": null, "time": null}}""",

    # For project reference resolution
    'resolve_project': """Identify which project the user is referring to.

User message: "{message}"

Known projects:
{project_list}

Currently discussed project (for pronoun resolution): {current_project_id}

Extract:
- project_id: If user mentions a specific project ID OR uses a pronoun referring to current project
- category: If user mentions a category (e.g., "dishwasher", "deck")
- location: If user mentions a location (e.g., "North Loop", "Chicago Ave")
- ordinal: If user uses position (e.g., "first", "2nd", "last")

IMPORTANT: Pronouns like "it", "that", "that one", "this one", "this project" refer to the CURRENTLY DISCUSSED project.

Examples:
- "the dishwasher project" → {{"category": "Dishwasher"}}
- "project 7751743" → {{"project_id": "7751743"}}
- "the one at North Loop" → {{"location": "North Loop"}}
- "the first one" → {{"ordinal": 0}}
- "the second project" → {{"ordinal": 1}}
- "the last one" → {{"ordinal": -1}}
- "reschedule it" (current=8503762) → {{"project_id": "8503762"}}
- "schedule that one" (current=8503762) → {{"project_id": "8503762"}}
- "cancel this project" (current=1234567) → {{"project_id": "1234567"}}
- "what about it" (current=8175908) → {{"project_id": "8175908"}}

Return ONLY valid JSON.""",

    # For confirmation detection
    'detect_confirmation': """Detect if the user is confirming or declining.

User message: "{message}"

Context: {context}

Extract:
- confirmed: true if user confirms, false if user declines, null if unclear

Confirmations: yes, yeah, yep, sure, ok, okay, confirm, do it, go ahead, sounds good, let's do it, book it
Declines: no, nope, nah, cancel, never mind, stop, don't, wait, hold on

Return ONLY valid JSON: {{"confirmed": true/false/null}}""",

    # For filter extraction (list_projects)
    'extract_filters': """Extract filter criteria from the user's request.

User message: "{message}"

Extract any of:
- status: "schedulable" (New, Ready To Schedule) or "scheduled" (Scheduled, Tentatively Scheduled)
- category: Kitchen, Decking, Windows, Flooring, Doors, etc.
- location: Any address or area mentioned
- technician_name: Name of assigned technician/installer
- scheduled_month: Month name if user asks for appointments in a specific month (e.g., "January", "February")

Examples:
- "show scheduled projects" → {{"status": "scheduled"}}
- "what can I schedule?" → {{"status": "schedulable"}}
- "kitchen projects" → {{"category": "Kitchen"}}
- "just the dishwasher" → {{"category": "Dishwasher"}}
- "projects at North Loop" → {{"location": "North Loop"}}
- "projects assigned to John" → {{"technician_name": "John"}}
- "Mildred's projects" → {{"technician_name": "Mildred"}}
- "scheduled for January" → {{"status": "scheduled", "scheduled_month": "January"}}
- "appointments in February" → {{"status": "scheduled", "scheduled_month": "February"}}
- "what's coming up in March" → {{"status": "scheduled", "scheduled_month": "March"}}

Return ONLY valid JSON. Only include fields that are explicitly mentioned.""",

    # Weather query - extract location AND date from context
    'get_weather': """Extract location and date for weather query.

User message: "{message}"
Conversation context: {context}
Today's date: {today}

IMPORTANT: Extract BOTH location AND date if mentioned.

LOCATION:
- If user mentions a city/state: use that location
- If user references a project (by ID, category, or "the project"): extract the project's ADDRESS from context
- Project IDs (like "21083_09PF05VD_...") are NOT locations - look up the project's address instead

DATE:
- If user mentions a specific date: extract it in YYYY-MM-DD format
- Handle relative dates: "tomorrow", "next Tuesday", "January 15th", "the 7th", etc.
- If no date mentioned, return null for date

Examples:
- "weather in Minneapolis" → {{"location": "Minneapolis"}}
- "weather for January 15th" → {{"date": "2026-01-15"}}
- "what's the weather for next Tuesday" → {{"date": "[calculated date]"}}
- "how's the weather for the 7th" → {{"date": "2026-01-07"}}
- "weather in Chicago on Friday" → {{"location": "Chicago", "date": "[Friday's date]"}}
- "how's the weather" (with project in context) → {{"location": "[project address from context]"}}

Return ONLY valid JSON: {{"location": "...", "date": "YYYY-MM-DD"}} with available fields.""",

    # Generic entity extraction fallback
    'generic': """Extract any relevant entities from this message.

User message: "{message}"
Action being performed: {action}
Conversation context: {context}

Extract any of:
- date: Any date mentioned (format: YYYY-MM-DD)
- time: Any time mentioned (format: HH:MM or descriptive like "morning")
- project_id: Any project ID (7-digit number)
- category: Any project category
- location: Any location/address
- confirmed: true/false if this is a confirmation

Return ONLY valid JSON with found entities. Empty object {{}} if none found."""
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENRICHER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def enrich_entities(
    message: str,
    action: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract entities from user message based on the action.

    Args:
        message: User's message
        action: The action already determined by NLU + Guards
        context: Dict with workflow_state, available_dates, available_slots, etc.

    Returns:
        Dict of extracted entities
    """
    logger.info(f"[ENRICHER] Extracting entities for action: {action}")

    # Select appropriate prompt based on action
    if action == 'get_time_slots':
        return _extract_date_selection(message, context)
    elif action == 'confirm_appointment':
        return _extract_slot_selection(message, context)
    elif action == 'list_projects':
        return _extract_filters(message, context)
    elif action in ['get_project_details', 'get_available_dates', 'cancel_appointment', 'reschedule_appointment']:
        return _extract_project_reference(message, context)
    elif action in ['confirm_appointment', 'cancel_appointment']:
        return _extract_confirmation(message, context)
    elif action == 'get_weather':
        return _extract_weather_location(message, context)
    else:
        return _extract_generic(message, action, context)


def _extract_date_selection(message: str, context: Dict) -> Dict[str, Any]:
    """Extract date from user's selection - enhanced with DSPy few-shots"""
    from datetime import datetime, timedelta

    # Get available dates from context
    available_dates = context.get('available_dates', [])
    dates_str = "\n".join([f"- {d}" for d in available_dates]) if available_dates else "No dates available"

    # Calculate tomorrow's date
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    first_available = available_dates[0] if available_dates else tomorrow

    prompt = PROMPTS['get_time_slots'].format(
        message=message,
        available_dates=dates_str,
        tomorrow=tomorrow,
        first_available=first_available
    )

    # Enhance with DSPy-learned date interpretation examples
    if DSPY_ENRICHER_AVAILABLE:
        dspy_examples = get_date_interpreter_few_shots()
        if dspy_examples:
            prompt = dspy_examples + "\n\n" + prompt

    response = call_sonnet(prompt, max_tokens=100)
    return _parse_json_response(response)


def _extract_slot_selection(message: str, context: Dict) -> Dict[str, Any]:
    """Extract time slot from user's selection"""
    available_slots = context.get('available_slots', [])
    slots_str = "\n".join([f"- Slot {i+1}: {s}" for i, s in enumerate(available_slots)]) if available_slots else "No slots available"

    prompt = PROMPTS['confirm_appointment'].format(
        message=message,
        available_slots=slots_str
    )

    response = call_sonnet(prompt, max_tokens=100)
    return _parse_json_response(response)


def _extract_project_reference(message: str, context: Dict) -> Dict[str, Any]:
    """Extract project reference (ID, category, location, ordinal) - enhanced with DSPy"""
    workflow_state = context.get('workflow_state', {})
    workflow_context = workflow_state.get('context', {})
    project_mapping = workflow_context.get('project_mapping', {})

    # Get current project_id for pronoun resolution ("it", "that one", etc.)
    current_project_id = workflow_context.get('project_id', '')
    if current_project_id:
        logger.info(f"[ENRICHER] Current project for pronoun resolution: {current_project_id}")

    # Format project list
    project_lines = []
    for pid, info in project_mapping.items():
        cat = info.get('category', 'Unknown')
        addr = info.get('address', '')
        status = info.get('status', '')
        # Mark current project in the list
        marker = " (CURRENT)" if str(pid) == str(current_project_id) else ""
        project_lines.append(f"- #{pid}: {cat} at {addr} ({status}){marker}")

    project_list = "\n".join(project_lines) if project_lines else "No projects in context"

    prompt = PROMPTS['resolve_project'].format(
        message=message,
        project_list=project_list,
        current_project_id=current_project_id or "None"
    )

    # Enhance with DSPy-learned context resolution examples
    if DSPY_ENRICHER_AVAILABLE:
        dspy_examples = get_context_resolver_few_shots()
        if dspy_examples:
            prompt = dspy_examples + "\n\n" + prompt

    response = call_sonnet(prompt, max_tokens=150)
    return _parse_json_response(response)


def _extract_filters(message: str, context: Dict) -> Dict[str, Any]:
    """Extract filter criteria for list_projects"""
    prompt = PROMPTS['extract_filters'].format(message=message)
    response = call_sonnet(prompt, max_tokens=100)
    return _parse_json_response(response)


def _extract_confirmation(message: str, context: Dict) -> Dict[str, Any]:
    """Detect if user is confirming or declining"""
    context_str = json.dumps(context.get('workflow_state', {}).get('context', {}), indent=2)

    prompt = PROMPTS['detect_confirmation'].format(
        message=message,
        context=context_str
    )

    response = call_sonnet(prompt, max_tokens=50)
    return _parse_json_response(response)


def _extract_weather_location(message: str, context: Dict) -> Dict[str, Any]:
    """Extract geographic location AND date for weather query from message or project context"""
    from datetime import datetime

    # Build context string with project info for Sonnet to reference
    workflow_state = context.get('workflow_state', {})
    workflow_context = workflow_state.get('context', {})
    # Check both context-level AND top-level project_mapping (context switch preserves at top level)
    project_mapping = workflow_context.get('project_mapping', {}) or workflow_state.get('project_mapping', {})

    # Include project addresses in context
    context_info = {
        'current_project_id': workflow_context.get('project_id'),
        'projects': {pid: {'address': info.get('address'), 'category': info.get('category')}
                     for pid, info in project_mapping.items()} if project_mapping else {}
    }
    context_str = json.dumps(context_info, indent=2)[:1000]

    # Get today's date for relative date calculations
    today = datetime.now().strftime('%Y-%m-%d')

    prompt = PROMPTS['get_weather'].format(
        message=message,
        context=context_str,
        today=today
    )

    response = call_sonnet(prompt, max_tokens=100)
    return _parse_json_response(response)


def _extract_generic(message: str, action: str, context: Dict) -> Dict[str, Any]:
    """Generic entity extraction fallback"""
    context_str = json.dumps(context.get('workflow_state', {}).get('context', {}), indent=2)[:500]

    prompt = PROMPTS['generic'].format(
        message=message,
        action=action,
        context=context_str
    )

    response = call_sonnet(prompt, max_tokens=150)
    return _parse_json_response(response)


def _parse_json_response(response: str) -> Dict[str, Any]:
    """Parse JSON from Sonnet response, handling edge cases"""
    try:
        # Try direct parse
        return json.loads(response.strip())
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{[^}]+\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        logger.warning(f"[ENRICHER] Failed to parse JSON: {response[:100]}")
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY: Check if enrichment is needed
# ═══════════════════════════════════════════════════════════════════════════════

def needs_enrichment(action: str, existing_entities: Dict) -> bool:
    """
    Determine if we need to call Sonnet for entity enrichment.

    Skip Sonnet call if we already have all needed entities.
    """
    if action == 'list_projects':
        # Only enrich if no filters already extracted
        return not any(k in existing_entities for k in ['status', 'category', 'location', 'technician_name'])

    elif action == 'get_time_slots':
        # Need date
        return 'date' not in existing_entities

    elif action == 'confirm_appointment':
        # Need slot_id or time
        return 'slot_id' not in existing_entities and 'time' not in existing_entities

    elif action in ['get_project_details', 'get_available_dates', 'cancel_appointment', 'reschedule_appointment']:
        # Need project_id or way to resolve it - check key exists AND has a value
        return 'project_id' not in existing_entities or existing_entities.get('project_id') is None

    # Default: enrich to be safe
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE STYLING - Adapt responses for voice/sms/chat channels
# ═══════════════════════════════════════════════════════════════════════════════

def style_response_for_channel(
    raw_response: str,
    channel: str,
    action_context: str = ""
) -> str:
    """
    Style a response for the appropriate channel using DSPy-learned patterns.

    Args:
        raw_response: The raw response content to style
        channel: "voice", "sms", or "chat"
        action_context: What action was being performed

    Returns:
        Styled response appropriate for the channel
    """
    if not raw_response:
        return raw_response

    # Get DSPy-learned styling examples for this channel
    dspy_examples = ""
    if DSPY_ENRICHER_AVAILABLE:
        dspy_examples = get_response_style_few_shots(channel)

    prompt = f"""Adapt this response for {channel.upper()} channel.

{dspy_examples}

Raw response: "{raw_response}"
Context: {action_context}
Channel: {channel}

Guidelines:
- voice: Conversational, natural flow, no markdown, under 200 chars
- sms: Ultra-concise, abbreviations OK, under 160 chars
- chat: Balanced, markdown formatting OK, bullet points for lists

Return ONLY the styled response, nothing else."""

    styled = call_sonnet(prompt, max_tokens=300)

    # Fallback to raw if styling fails
    if not styled or len(styled) < 5:
        return raw_response

    return styled.strip()


def rank_time_slots(
    available_slots: List[str],
    user_preference: str = "",
    weather_info: str = "",
    project_type: str = ""
) -> Dict[str, Any]:
    """
    Rank time slots based on user preferences, weather, and project type.

    Uses DSPy-learned ranking patterns for intelligent recommendations.

    Args:
        available_slots: List of available time slots
        user_preference: User's preference (morning, afternoon, earliest, latest)
        weather_info: Weather conditions for the date
        project_type: Indoor or outdoor project type

    Returns:
        Dict with ranked_slots list and recommendation
    """
    if not available_slots:
        return {"ranked_slots": [], "recommendation": None, "reason": "No slots available"}

    # Get DSPy-learned slot ranking examples
    dspy_examples = ""
    if DSPY_ENRICHER_AVAILABLE:
        dspy_examples = get_slot_ranker_few_shots()

    slots_json = json.dumps(available_slots)

    prompt = f"""Rank these time slots for optimal scheduling.

{dspy_examples}

Available slots: {slots_json}
User preference: {user_preference or "none specified"}
Weather: {weather_info or "not available"}
Project type: {project_type or "unknown"}

Return JSON with:
- ranked_slots: Array of slots in recommended order
- recommendation: Best slot
- reason: Brief explanation

Return ONLY valid JSON."""

    response = call_sonnet(prompt, max_tokens=200)
    result = _parse_json_response(response)

    # Fallback if parsing fails
    if not result.get('ranked_slots'):
        return {
            "ranked_slots": available_slots,
            "recommendation": available_slots[0] if available_slots else None,
            "reason": "Default ordering"
        }

    return result
