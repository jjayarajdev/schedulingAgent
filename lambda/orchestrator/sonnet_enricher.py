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
"""

import json
import logging
import boto3
from typing import Dict, Any, Optional, List
from botocore.config import Config as BotoConfig

logger = logging.getLogger()

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

Extract:
- project_id: If user mentions a specific project ID
- category: If user mentions a category (e.g., "dishwasher", "deck")
- location: If user mentions a location (e.g., "North Loop", "Chicago Ave")
- ordinal: If user uses position (e.g., "first", "2nd", "last")

Examples:
- "the dishwasher project" → {{"category": "Dishwasher"}}
- "project 7751743" → {{"project_id": "7751743"}}
- "the one at North Loop" → {{"location": "North Loop"}}
- "the first one" → {{"ordinal": 0}}
- "the second project" → {{"ordinal": 1}}
- "the last one" → {{"ordinal": -1}}

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

Examples:
- "show scheduled projects" → {{"status": "scheduled"}}
- "what can I schedule?" → {{"status": "schedulable"}}
- "kitchen projects" → {{"category": "Kitchen"}}
- "just the dishwasher" → {{"category": "Dishwasher"}}
- "projects at North Loop" → {{"location": "North Loop"}}

Return ONLY valid JSON. Only include fields that are explicitly mentioned.""",

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
    else:
        return _extract_generic(message, action, context)


def _extract_date_selection(message: str, context: Dict) -> Dict[str, Any]:
    """Extract date from user's selection"""
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
    """Extract project reference (ID, category, location, ordinal)"""
    workflow_state = context.get('workflow_state', {})
    project_mapping = workflow_state.get('context', {}).get('project_mapping', {})

    # Format project list
    project_lines = []
    for pid, info in project_mapping.items():
        cat = info.get('category', 'Unknown')
        addr = info.get('address', '')
        status = info.get('status', '')
        project_lines.append(f"- #{pid}: {cat} at {addr} ({status})")

    project_list = "\n".join(project_lines) if project_lines else "No projects in context"

    prompt = PROMPTS['resolve_project'].format(
        message=message,
        project_list=project_list
    )

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
        return not any(k in existing_entities for k in ['status', 'category', 'location'])

    elif action == 'get_time_slots':
        # Need date
        return 'date' not in existing_entities

    elif action == 'confirm_appointment':
        # Need slot_id or time
        return 'slot_id' not in existing_entities and 'time' not in existing_entities

    elif action in ['get_project_details', 'get_available_dates', 'cancel_appointment', 'reschedule_appointment']:
        # Need project_id or way to resolve it
        return 'project_id' not in existing_entities

    # Default: enrich to be safe
    return True
