"""
Intelligent Workflow Orchestrator

Architecture: Hybrid LLM + Deterministic
- Sonnet 3.7 handles: intent classification, context-aware decisions, response generation
- Deterministic helpers handle: cheap extraction (dates, ordinals, times), guardrails, post-filtering

Key design decisions:
1. Upstream ProjectForce API does NOT support filtering - we fetch all and post-filter
2. Post-filters (status, category, projectType, address, technician_name) are applied via apply_project_filters()
3. Category buckets map user terms ("kitchen") to actual categories ("Dishwasher", "Ovens")
4. Workflow state tracks: project_ids, project_mapping, viewed_projects for ordinal resolution

Note: This module has its own intelligent_classify() which may duplicate classifier.py.
Consider unifying to a single classification source of truth.
"""
import json
import logging
import re
import time
import boto3
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from botocore.config import Config as BotoConfig

from config import get_config
from workflow_state import get_state_manager
from router import call_lambda_directly, format_lambda_response
from classifier import apply_project_filters, extract_first_json_object, heuristic_intent_fallback, CATEGORY_BUCKETS, SCHEDULED_STATUSES, classify_intent_and_action
from voice_formatter import _format_project_details_for_voice, _add_voice_followup
from action_guards import apply_guards, log_classification_decision
from sonnet_enricher import enrich_entities, needs_enrichment
from weather_aware_scheduling import (
    is_outdoor_project,
    find_forecast_for_date,
    analyze_weather_suitability,
    extract_location_from_context,
    find_better_weather_dates,
    add_weather_indicators_to_dates
)
from response_context import (
    build_voice_context,
    save_action_to_context,
    cache_upcoming_appointments,
    get_filler_for_action,
    ConversationState
)

logger = logging.getLogger()

# Bedrock runtime client singleton
_bedrock_runtime = None


def get_category_bucket(category: str) -> Optional[str]:
    """
    Determine which bucket a category belongs to.
    Returns bucket name ("kitchen", "windows", etc.) or None if no match.
    """
    if not category:
        return None
    cat_lower = category.lower().strip()
    for bucket_name, bucket_categories in CATEGORY_BUCKETS.items():
        if cat_lower in bucket_categories:
            return bucket_name
    return None


def handle_calendar_info(date_param: str, message: str) -> Dict[str, Any]:
    """
    Handle calendar/day-of-week questions using Python datetime.
    Called after LLM classifies intent as Calendar_Info_Request.

    Args:
        date_param: Date string (YYYY-MM-DD format from LLM, or natural language)
        message: Original user message (for fallback parsing)

    Returns:
        Response dict with the day of week
    """
    # Month name mapping for natural language parsing
    months = {
        'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
        'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
        'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
    }

    target_date = None
    current_date = datetime.now()

    # Try YYYY-MM-DD format first (from LLM)
    if date_param:
        try:
            target_date = datetime.strptime(date_param, "%Y-%m-%d")
            logger.info(f"[CALENDAR-INFO] Parsed YYYY-MM-DD format: {date_param}")
        except ValueError:
            pass

    # Fallback: parse natural language from message
    if not target_date:
        msg_lower = message.lower()
        # Look for "month day" pattern
        date_match = re.search(r'(\w+)\s+(\d+)(?:st|nd|rd|th)?', msg_lower)
        if date_match:
            month_str = date_match.group(1).lower()
            day = int(date_match.group(2))
            month = months.get(month_str)
            if month:
                year = current_date.year
                try:
                    target_date = datetime(year, month, day)
                    # If date has passed this year, use next year
                    if target_date < current_date:
                        year += 1
                        target_date = datetime(year, month, day)
                    logger.info(f"[CALENDAR-INFO] Parsed natural language: {month_str} {day} -> {target_date}")
                except ValueError:
                    pass

    if target_date:
        day_name = target_date.strftime("%A")
        formatted_date = target_date.strftime("%B %d, %Y")
        logger.info(f"[CALENDAR-INFO] {formatted_date} is a {day_name}")

        return {
            'response': f"{formatted_date} is a {day_name}.",
            'intent': 'information',
            'action': 'calendar_info',
            'agent_name': 'Intelligent Orchestrator (Calendar)',
            'direct_call': True
        }

    # Could not parse date
    logger.warning(f"[CALENDAR-INFO] Could not parse date from: {date_param}, {message}")
    return {
        'response': "I couldn't understand that date. Could you please say it again, like 'September 14th'?",
        'intent': 'information',
        'action': 'calendar_info_error',
        'agent_name': 'Intelligent Orchestrator (Calendar)'
    }


def find_project_by_partial_id(search_id: str, project_mapping: Dict[str, Any]) -> Optional[str]:
    """
    Find a project ID using partial matching.

    Handles cases where user provides:
    - Order Number (projectNumber) like "21083_09PF05VD_1762166550719_1"
    - Internal Project ID like "9000497"
    - Partial ID

    Args:
        search_id: The ID the user provided (may be Order Number or partial)
        project_mapping: Dict of project_id/projectNumber -> project_info

    Returns:
        Internal project_id (for API calls) if found, None otherwise
    """
    if not search_id or not project_mapping:
        return None

    search_id_str = str(search_id).strip()
    search_id_lower = search_id_str.lower()

    # 1. Exact match - check if it's an Order Number with project_id mapping
    if search_id_str in project_mapping:
        info = project_mapping[search_id_str]
        # If this entry has a project_id field, it's an Order Number -> return the internal ID
        if info.get('project_id'):
            logger.info(f"[RESOLVE] Order Number '{search_id_str}' -> Project ID '{info['project_id']}'")
            return info['project_id']
        # Otherwise it's already an internal project ID
        return search_id_str

    # 2. Case-insensitive exact match
    for pid in project_mapping.keys():
        if pid.lower() == search_id_lower:
            info = project_mapping[pid]
            if info.get('project_id'):
                logger.info(f"[RESOLVE] Order Number '{pid}' -> Project ID '{info['project_id']}'")
                return info['project_id']
            return pid

    # 3. Suffix match - search_id is at the end of the full ID
    # e.g., "9000407_1" matches "21083_09PF05VD_9000407_1"
    for pid in project_mapping.keys():
        if pid.lower().endswith(search_id_lower):
            info = project_mapping[pid]
            resolved = info.get('project_id', pid)
            logger.info(f"[PARTIAL-MATCH] Suffix match: '{search_id}' -> '{pid}' -> project_id '{resolved}'")
            return resolved

    # 4. Contains match - search_id is contained in full ID
    for pid in project_mapping.keys():
        if search_id_lower in pid.lower():
            info = project_mapping[pid]
            resolved = info.get('project_id', pid)
            logger.info(f"[PARTIAL-MATCH] Contains match: '{search_id}' -> '{pid}' -> project_id '{resolved}'")
            return resolved

    # 5. Numeric EXACT match - extract numeric part and match exactly
    # Avoid partial matches like "100000" matching "100002"
    search_digits = re.sub(r'[^0-9_]', '', search_id_str)
    if search_digits:
        for pid in project_mapping.keys():
            pid_digits = re.sub(r'[^0-9_]', '', pid)
            if search_digits == pid_digits:
                info = project_mapping[pid]
                resolved = info.get('project_id', pid)
                logger.info(f"[PARTIAL-MATCH] Numeric exact match: '{search_id}' -> '{pid}' -> project_id '{resolved}'")
                return resolved

    return None


def find_project_reference_in_message(message: str, project_mapping: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """
    Find any project reference in the message by matching against known project IDs/numbers.

    This is format-agnostic - works with ANY project ID format (AI-PRO-XXXXXX,
    numeric IDs, alphanumeric codes, etc.) by using the project_mapping as source of truth.

    Args:
        message: User's message
        project_mapping: Dict of project_id/projectNumber -> project_info

    Returns:
        Tuple of (matched_reference, resolved_project_id) or None if no match
    """
    if not message or not project_mapping:
        return None

    # Tokenize message - extract potential ID-like tokens (alphanumeric with hyphens/underscores)
    # This captures: "AI-PRO-1000010", "90000087", "21083_09PF05VD_123", etc.
    tokens = re.findall(r'[A-Za-z0-9][\w-]*[A-Za-z0-9]|[A-Za-z0-9]+', message)

    # Filter to tokens that look like IDs (at least 3 chars, contains digit)
    potential_ids = [t for t in tokens if len(t) >= 3 and any(c.isdigit() for c in t)]

    logger.debug(f"[PROJECT-REF] Potential ID tokens from message: {potential_ids}")

    for token in potential_ids:
        token_lower = token.lower()

        # 1. Exact match (case-insensitive) against project_mapping keys
        for known_id in project_mapping.keys():
            if token_lower == known_id.lower():
                info = project_mapping[known_id]
                resolved_id = info.get('project_id', known_id)
                logger.info(f"[PROJECT-REF] Exact match: '{token}' -> '{known_id}' -> project_id '{resolved_id}'")
                return (known_id, resolved_id)

        # 2. Token is contained in a known ID (e.g., "1000010" in "AI-PRO-1000010")
        for known_id in project_mapping.keys():
            if token_lower in known_id.lower():
                info = project_mapping[known_id]
                resolved_id = info.get('project_id', known_id)
                logger.info(f"[PROJECT-REF] Contains match: '{token}' in '{known_id}' -> project_id '{resolved_id}'")
                return (known_id, resolved_id)

        # 3. Known ID is contained in token (e.g., "AI-PRO-1000010" contains "1000010")
        for known_id in project_mapping.keys():
            if known_id.lower() in token_lower:
                info = project_mapping[known_id]
                resolved_id = info.get('project_id', known_id)
                logger.info(f"[PROJECT-REF] Reverse contains: '{known_id}' in '{token}' -> project_id '{resolved_id}'")
                return (known_id, resolved_id)

    # 4. Numeric EXACT match only - no partial matching to avoid false positives
    # e.g., "100002" should NOT match "100000" just because they share digits
    for token in potential_ids:
        token_digits = re.sub(r'[^0-9]', '', token)
        if len(token_digits) >= 5:  # Need at least 5 digits for meaningful match
            for known_id in project_mapping.keys():
                known_digits = re.sub(r'[^0-9]', '', known_id)
                # Only match if digits are exactly equal
                if token_digits == known_digits:
                    info = project_mapping[known_id]
                    resolved_id = info.get('project_id', known_id)
                    logger.info(f"[PROJECT-REF] Numeric exact match: '{token}' ({token_digits}) == '{known_id}' ({known_digits}) -> project_id '{resolved_id}'")
                    return (known_id, resolved_id)

    return None


# ============================================================================
# STAGE-DRIVEN WORKFLOW CONTINUATION
# These functions check if user is providing what we're waiting for,
# bypassing context_resolver and classification to avoid "5th Dec" being
# interpreted as "5th project".
# ============================================================================

def extract_date_from_message(message: str) -> Optional[str]:
    """
    Extract date from message without LLM - simple patterns only.
    Returns date in YYYY-MM-DD format or None if no date found.
    """
    from datetime import datetime, timedelta

    msg = message.lower().strip()

    # Pattern 0: Relative dates - "today", "tomorrow"
    if 'today' in msg:
        return datetime.now().strftime('%Y-%m-%d')
    if 'tomorrow' in msg:
        return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    # Month name patterns (3-letter abbreviations)
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    # Pattern 1: "5th Dec", "5 Dec", "5th of December"
    pattern1 = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?([a-z]+)', msg)
    if pattern1:
        day_str, month_str = pattern1.groups()
        for m_name, m_num in months.items():
            if month_str.startswith(m_name):
                year = datetime.now().year
                # Handle year rollover (if date is in past, assume next year)
                proposed_date = datetime(year, m_num, int(day_str))
                if proposed_date < datetime.now():
                    year += 1
                return f"{year}-{m_num:02d}-{int(day_str):02d}"

    # Pattern 2: "Dec 5", "December 5th"
    pattern2 = re.search(r'([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?', msg)
    if pattern2:
        month_str, day_str = pattern2.groups()
        for m_name, m_num in months.items():
            if month_str.startswith(m_name):
                year = datetime.now().year
                proposed_date = datetime(year, m_num, int(day_str))
                if proposed_date < datetime.now():
                    year += 1
                return f"{year}-{m_num:02d}-{int(day_str):02d}"

    # Pattern 3: YYYY-MM-DD (already formatted)
    pattern3 = re.search(r'(\d{4})-(\d{2})-(\d{2})', msg)
    if pattern3:
        return pattern3.group(0)

    # Pattern 4: MM/DD/YYYY or MM-DD-YYYY
    pattern4 = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', msg)
    if pattern4:
        month, day, year = pattern4.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # Pattern 5: MM/DD or MM-DD (without year) - assume current/next year
    # Match MM/DD but NOT MM/DD/YYYY (already handled above)
    pattern5 = re.search(r'(?<!\d)(\d{1,2})[/-](\d{1,2})(?![/-]\d)', msg)
    if pattern5:
        month, day = pattern5.groups()
        month_int = int(month)
        day_int = int(day)
        # Validate month/day
        if 1 <= month_int <= 12 and 1 <= day_int <= 31:
            year = datetime.now().year
            try:
                proposed_date = datetime(year, month_int, day_int)
                if proposed_date < datetime.now():
                    year += 1
                return f"{year}-{month_int:02d}-{day_int:02d}"
            except ValueError:
                pass  # Invalid date (e.g., Feb 30)

    return None


def extract_month_reference(message: str) -> Optional[str]:
    """
    Extract month-only reference from message (e.g., "February", "March").
    Returns the month name as-is for the scheduler LLM interpreter to handle.
    """
    msg = message.lower().strip()

    # Full month names
    months = ['january', 'february', 'march', 'april', 'may', 'june',
              'july', 'august', 'september', 'october', 'november', 'december']

    for month in months:
        # Check for full month name or 3-letter abbreviation as standalone word
        if month in msg or re.search(rf'\b{month[:3]}\b', msg):
            return month

    return None


def extract_ordinal_project_reference(message: str) -> Optional[int]:
    """
    Extract ordinal project reference from message.
    Returns project_index (0-based, supports negative) or None if no ordinal reference found.

    Examples:
        "first project" -> 0
        "1st project" -> 0
        "second project" -> 1
        "2nd project" -> 1
        "last project" -> -1
        "details for the last one" -> -1
    """
    msg = message.lower().strip()

    # Check if message is about project (details, info, or scheduling actions)
    project_keywords = ['project', 'one', 'details', 'show', 'info', 'about', 'schedule', 'book', 'reschedule', 'cancel']
    has_project_context = any(kw in msg for kw in project_keywords)

    if not has_project_context:
        return None

    # Pattern for "last project", "the last one", "last"
    if re.search(r'\blast\b', msg):
        logger.info(f"[ORDINAL] Detected 'last' reference in: {msg}")
        return -1

    # Pattern for "first project", "the first one", "1st"
    if re.search(r'\b(first|1st)\b', msg):
        logger.info(f"[ORDINAL] Detected 'first' reference in: {msg}")
        return 0

    # Pattern for "second", "2nd"
    if re.search(r'\b(second|2nd)\b', msg):
        logger.info(f"[ORDINAL] Detected 'second' reference in: {msg}")
        return 1

    # Pattern for "third", "3rd"
    if re.search(r'\b(third|3rd)\b', msg):
        logger.info(f"[ORDINAL] Detected 'third' reference in: {msg}")
        return 2

    # Pattern for numeric ordinals: "4th project", "5th one", etc.
    # IMPORTANT: Only match if followed by project-related word to avoid "5th Dec"
    numeric_match = re.search(r'\b(\d+)(?:st|nd|rd|th)\s+(?:project|one)\b', msg)
    if numeric_match:
        index = int(numeric_match.group(1)) - 1  # Convert to 0-based
        logger.info(f"[ORDINAL] Detected numeric ordinal {numeric_match.group(1)} -> index {index}")
        return index

    return None


def extract_partial_id_reference(message: str) -> Optional[str]:
    """
    Extract partial project ID reference from message.
    Returns the partial ID digits or None if no partial reference found.

    Examples:
        "project ending in 717" -> "717"
        "ending 717" -> "717"
        "the one ending with 60000" -> "60000"
        "project starting with 775" -> "775"
    """
    msg = message.lower().strip()

    # Pattern 1: "ending in/with 717", "ends in 717", "ending 717"
    ending_match = re.search(r'(?:ending|ends)\s*(?:in|with)?\s*(\d{3,})', msg)
    if ending_match:
        partial = ending_match.group(1)
        logger.info(f"[PARTIAL_ID] Detected 'ending' pattern: {partial}")
        return partial

    # Pattern 2: "starting with 775", "starts with 775", "beginning with 775"
    starting_match = re.search(r'(?:starting|starts|beginning|begins)\s*(?:with)?\s*(\d{3,})', msg)
    if starting_match:
        partial = starting_match.group(1)
        logger.info(f"[PARTIAL_ID] Detected 'starting' pattern: {partial}")
        return partial

    # Pattern 3: "last 3 digits 717", "last digits 717"
    last_digits_match = re.search(r'last\s*(?:\d+\s*)?digits?\s*(\d{3,})', msg)
    if last_digits_match:
        partial = last_digits_match.group(1)
        logger.info(f"[PARTIAL_ID] Detected 'last digits' pattern: {partial}")
        return partial

    return None


def extract_time_from_message(message: str) -> Optional[str]:
    """
    Extract time from message without LLM - simple patterns only.
    Returns time in HH:MM format (24-hour) or None if no time found.
    """
    msg = message.lower().strip()

    # Pattern 1: "2pm", "2 pm", "2:00pm", "2:00 pm"
    pattern1 = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)', msg)
    if pattern1:
        hour = int(pattern1.group(1))
        minute = int(pattern1.group(2) or 0)
        ampm = pattern1.group(3)

        if ampm == 'pm' and hour < 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    # Pattern 2: "2 o'clock", "2 oclock"
    pattern2 = re.search(r'(\d{1,2})\s*o\'?clock', msg)
    if pattern2:
        hour = int(pattern2.group(1))
        # Assume PM for business hours (1-6 o'clock)
        if 1 <= hour <= 6:
            hour += 12
        return f"{hour:02d}:00"

    # Pattern 3: 24-hour format "14:00", "14:30"
    pattern3 = re.search(r'\b(\d{2}):(\d{2})\b', msg)
    if pattern3:
        hour, minute = int(pattern3.group(1)), int(pattern3.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"

    return None


def format_time_12hr(time_str: str) -> str:
    """
    Convert 24-hour time format (HH:MM) to 12-hour format with AM/PM.
    E.g., "13:00" -> "1:00 PM", "08:30" -> "8:30 AM"

    If time_str is already in 12-hour format or invalid, returns as-is.
    """
    if not time_str:
        return time_str

    # Check if already has AM/PM
    if 'am' in time_str.lower() or 'pm' in time_str.lower():
        return time_str

    try:
        # Parse HH:MM format
        parts = time_str.split(':')
        if len(parts) != 2:
            return time_str

        hour = int(parts[0])
        minute = int(parts[1])

        # Determine AM/PM
        if hour == 0:
            display_hour = 12
            period = 'AM'
        elif hour < 12:
            display_hour = hour
            period = 'AM'
        elif hour == 12:
            display_hour = 12
            period = 'PM'
        else:
            display_hour = hour - 12
            period = 'PM'

        # Format with minutes
        if minute == 0:
            return f"{display_hour}:00 {period}"
        else:
            return f"{display_hour}:{minute:02d} {period}"

    except (ValueError, IndexError):
        return time_str


def check_workflow_continuation(message: str, workflow_state: Dict, channel: str = 'chat') -> Optional[Dict]:
    """
    Check if user is providing what we're waiting for (date or time selection).
    If yes, return the next action directly (skip classification).
    If no, return None to proceed with normal classification.

    This prevents "5th Dec" from being interpreted as "5th project" when
    we're awaiting date selection.

    Args:
        message: User's message
        workflow_state: Current workflow state
        channel: 'chat' or 'voice' - for channel-specific handling
    """
    if not workflow_state:
        return None

    # Defensive check: ensure workflow_state is a dict, not a string
    if not isinstance(workflow_state, dict):
        logger.warning(f"[CONTINUATION] workflow_state is {type(workflow_state).__name__}, expected dict. Skipping continuation.")
        return None

    current_stage = workflow_state.get('current_stage')
    context = workflow_state.get('context', {})
    workflow_type = workflow_state.get('workflow_type', '')

    logger.info(f"[CONTINUATION] Checking continuation: stage={current_stage}, workflow_type={workflow_type}")

    # ========================================================================
    # CONTEXT SWITCH DETECTION: Check if user mentions a DIFFERENT project
    # If so, skip continuation and process the new request fresh
    # This prevents workflow state contamination when user switches context
    # Detects context switch by: project_id, category, status, or type
    # ========================================================================
    context_project_id = context.get('project_id')
    context_category = context.get('category', '').lower()
    # Check both top-level (after context switch) AND inside context (normal flow)
    project_mapping = workflow_state.get('project_mapping', {}) or context.get('project_mapping', {})

    if context_project_id:
        message_lower = message.lower()
        message_project_id = None
        message_project_ref = None  # The raw reference from the message (e.g., "AI-PRO-100002")

        # 0. FIRST: Extract any project-ID-like pattern directly from message
        # This catches cases where user asks about a NEW project not in mapping yet
        # Patterns: "AI-PRO-100002", "21083_09PF05VD_...", "9000489", etc.
        # EXCLUDE: Date patterns like "2026-01-06" which could be mistaken for project IDs
        id_patterns = re.findall(r'[A-Za-z0-9][\w-]*[A-Za-z0-9]|[A-Za-z0-9]+', message)
        # Filter: length >= 5, has digit, and NOT a date pattern (YYYY-MM-DD)
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        potential_refs = [t for t in id_patterns if len(t) >= 5 and any(c.isdigit() for c in t) and not date_pattern.match(t)]
        if potential_refs:
            message_project_ref = potential_refs[0]  # Take first project-like reference
            logger.info(f"[CONTINUATION] Extracted potential project reference: '{message_project_ref}'")

        # 1. Use intelligent project reference matching (format-agnostic)
        # This works with ANY format: AI-PRO-XXXXXX, numeric IDs, alphanumeric codes, etc.
        if project_mapping:
            ref_match = find_project_reference_in_message(message, project_mapping)
            if ref_match:
                matched_ref, message_project_id = ref_match
                logger.info(f"[CONTINUATION] Found project reference '{matched_ref}' -> project_id '{message_project_id}'")

        # 2. Fallback: Check for PARTIAL ID references like "ending in 717", "ending 717"
        if not message_project_id:
            partial_id = extract_partial_id_reference(message)
            if partial_id:
                # Try to resolve partial ID using workflow state
                state_manager = get_state_manager()
                session_id = workflow_state.get('session_id')
                if session_id:
                    matched_project = state_manager.find_project_by_partial_id(session_id, partial_id)
                    if matched_project:
                        message_project_id = matched_project.get('project_id')
                        logger.info(f"[CONTINUATION] Resolved partial ID '{partial_id}' to project {message_project_id}")

        # If user mentioned a different project ID, signal context switch
        if message_project_id and str(message_project_id) != str(context_project_id):
            logger.info(f"[CONTINUATION] CONTEXT SWITCH DETECTED (by ID): User mentioned project {message_project_id}, but workflow has project {context_project_id}. Clearing workflow state.")
            return {'context_switch': True, 'clear_state': True}

        # 2b. NEW: If user mentioned a project reference NOT in mapping, and it's different from context projectNumber
        # This catches cases like: context has AI-PRO-100000, user asks for AI-PRO-100002 (not in mapping)
        context_project_number = context.get('projectNumber', context.get('project_number', ''))
        if not message_project_id and message_project_ref:
            # Check if the reference is different from context's projectNumber or project_id
            ref_lower = message_project_ref.lower()
            context_pn_lower = str(context_project_number).lower() if context_project_number else ''
            context_pid_lower = str(context_project_id).lower() if context_project_id else ''

            # If message reference doesn't match context's projectNumber or project_id, it's a new project
            if ref_lower != context_pn_lower and ref_lower != context_pid_lower:
                # Also check if it's not a substring match (to avoid false positives from partial typing)
                if context_pn_lower and ref_lower not in context_pn_lower and context_pn_lower not in ref_lower:
                    logger.info(f"[CONTINUATION] CONTEXT SWITCH DETECTED (new project): User asked for '{message_project_ref}', context has projectNumber='{context_project_number}', project_id='{context_project_id}'. Clearing workflow state.")
                    return {'context_switch': True, 'clear_state': True}
                elif not context_pn_lower:
                    # No projectNumber in context, just compare with project_id
                    logger.info(f"[CONTINUATION] CONTEXT SWITCH DETECTED (new project): User asked for '{message_project_ref}', context has project_id='{context_project_id}'. Clearing workflow state.")
                    return {'context_switch': True, 'clear_state': True}

        # 3. Check for category-based context switch (e.g., "show the dishwasher project")
        # Only check if user didn't mention a specific project_id
        if not message_project_id and context_category and project_mapping:
            # Common project categories to detect
            category_keywords = [
                'decking', 'storm door', 'storm', 'dishwasher', 'sink', 'kitchen sink',
                'oven', 'ovens', 'washer dryer', 'washer', 'dryer', 'cooktop', 'electric cooktop',
                'exterior door', 'exterior doors', 'exterior', 'windows', 'doors', 'electric'
            ]

            # Check if message contains a category different from current project
            for category_kw in category_keywords:
                if category_kw in message_lower:
                    # Find project with this category in project_mapping
                    for pid, proj_info in project_mapping.items():
                        proj_category = (proj_info.get('category', '') or '').lower()
                        if category_kw in proj_category and str(pid) != str(context_project_id):
                            logger.info(f"[CONTINUATION] CONTEXT SWITCH DETECTED (by category): User mentioned '{category_kw}', found project {pid}, but workflow has project {context_project_id}. Clearing workflow state.")
                            return {'context_switch': True, 'clear_state': True}

                    # Also check if mentioned category differs from current project's category
                    if category_kw not in context_category:
                        logger.info(f"[CONTINUATION] CONTEXT SWITCH DETECTED (category mismatch): User mentioned '{category_kw}', but current project category is '{context_category}'. Clearing workflow state.")
                        return {'context_switch': True, 'clear_state': True}

        # 3. Check for status-based context switch (e.g., "show the scheduled project")
        if not message_project_id and project_mapping:
            status_keywords = {
                'scheduled': ['scheduled', 'tentatively scheduled'],
                'ready to schedule': ['ready to schedule', 'ready'],
                'completed': ['completed', 'done', 'finished'],
                'cancelled': ['cancelled', 'canceled']
            }

            for status_term, status_variants in status_keywords.items():
                if any(sv in message_lower for sv in status_variants):
                    # Find project with this status in project_mapping
                    for pid, proj_info in project_mapping.items():
                        proj_status = (proj_info.get('status', '') or '').lower()
                        if any(sv in proj_status for sv in status_variants) and str(pid) != str(context_project_id):
                            logger.info(f"[CONTINUATION] CONTEXT SWITCH DETECTED (by status): User mentioned '{status_term}', found project {pid}, but workflow has project {context_project_id}. Clearing workflow state.")
                            return {'context_switch': True, 'clear_state': True}

    # ========================================================================
    # ABORT HANDLING: Check if user wants to go back / cancel / never mind
    # This should be checked FIRST before any continuation logic
    # ========================================================================
    message_lower = message.lower().strip()

    # Check if "cancel" or "reschedule" is part of a cancel/reschedule_appointment action (not an abort)
    # e.g., "cancel the storm door", "cancel my appointment", "cancel the 2nd project"
    # e.g., "reschedule the decking", "reschedule my appointment"
    appointment_action_indicators = [
        # Generic terms
        'appointment', 'project', 'booking', 'installation',
        # Project categories (from actual data)
        'storm', 'door', 'decking', 'dishwasher', 'sink', 'oven', 'washer', 'dryer',
        'cooktop', 'exterior', 'electric', 'kitchen', 'windows', 'doors',
        # Ordinals (1st through 10th, plus 'last')
        '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th',
        'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'last',
        # Demonstratives and possessives
        'the', 'my', 'this', 'that', 'one', 'it'
    ]
    is_cancel_appointment_request = ('cancel' in message_lower and
                                      any(ind in message_lower for ind in appointment_action_indicators))
    is_reschedule_request = ('reschedule' in message_lower and
                              any(ind in message_lower for ind in appointment_action_indicators))

    # Only use 'cancel' as abort when it's standalone, not part of cancel/reschedule_appointment action
    abort_phrases = ['never mind', 'nevermind', 'forget it', 'go back',
                     'start over', 'actually no', 'no thanks', 'nope', 'stop',
                     'dont want', "don't want", 'changed my mind', 'forget about it',
                     'let me think', 'hold on', 'wait', 'not now']

    # Add 'cancel' only if it's not a cancel_appointment request
    if not is_cancel_appointment_request:
        abort_phrases.append('cancel')

    # If this is a cancel/reschedule appointment request, don't treat it as abort
    # even if the message contains abort-like phrases
    is_abort = any(phrase in message_lower for phrase in abort_phrases)
    if is_cancel_appointment_request or is_reschedule_request:
        is_abort = False
        logger.info(f"[CONTINUATION] Detected appointment action request (cancel={is_cancel_appointment_request}, reschedule={is_reschedule_request}) - bypassing abort")

    if is_abort and current_stage not in ['start', 'complete', None]:
        logger.info(f"[CONTINUATION] User wants to abort workflow at stage '{current_stage}'")
        return {
            'continue_workflow': True,
            'action': 'abort_workflow',
            'params': {},
            'next_stage': 'aborted',
            'preserve_context': {},
            'workflow_type': workflow_type,
            'abort_message': "No problem. What else can I help with?"
        }

    # ========================================================================
    # Stage: AWAITING SCHEDULE CONFIRM - Single project, user confirms "yes"
    # Voice fast path sets this stage when there's exactly 1 schedulable project
    # ========================================================================
    if current_stage == 'awaiting_schedule_confirm' and workflow_type == 'guided_selection':
        project_ids = context.get('project_ids', [])
        project_mapping = context.get('project_mapping', {})

        # Check for confirmation phrases
        confirm_phrases = ['yes', 'yeah', 'sure', 'ok', 'okay', 'yep', 'yup', 'please', 'go ahead',
                          'show me', 'let me see', 'sounds good', 'do it', 'proceed', 'right', 'correct']
        is_confirm = any(phrase in message_lower for phrase in confirm_phrases)

        if is_confirm and project_ids:
            # User confirmed - proceed to get_available_dates for the single project
            selected_project_id = project_ids[0]
            project_info = project_mapping.get(selected_project_id, {})
            project_status = project_info.get('status', '').lower()

            # Check if project is already scheduled - use rescheduler API
            scheduled_statuses = ['scheduled', 'customer scheduled', 'tentatively scheduled']
            is_reschedule = project_status in scheduled_statuses

            logger.info(f"[CONTINUATION] SCHEDULE CONFIRM: User confirmed single project {selected_project_id} (status={project_status}, is_reschedule={is_reschedule}) - going to get_available_dates")
            return {
                'continue_workflow': True,
                'action': 'get_available_dates',
                'params': {
                    'project_id': str(selected_project_id),
                    'is_reschedule': is_reschedule  # Use rescheduler API if already scheduled
                },
                'next_stage': 'awaiting_date_selection',
                'preserve_context': {
                    'project_id': str(selected_project_id),
                    'project_ids': project_ids,
                    'project_mapping': project_mapping,
                    'category': project_info.get('category', ''),
                    'address': project_info.get('address', ''),
                    'is_reschedule': is_reschedule
                },
                'workflow_type': 'reschedule_appointment' if is_reschedule else 'schedule_appointment'
            }

    # ========================================================================
    # Stage: AWAITING RESCHEDULE CONFIRM - User asked to schedule but project is already scheduled
    # Voice fast path sets this stage when user says "schedule" but project is already scheduled
    # User can say "yes", "reschedule", or "check details"
    # ========================================================================
    if current_stage == 'awaiting_reschedule_confirm' and workflow_type == 'reschedule_offer':
        project_ids = context.get('project_ids', [])
        project_mapping = context.get('project_mapping', {})
        selected_project_id = context.get('selected_project_id', project_ids[0] if project_ids else None)

        # Check for reschedule confirmation
        reschedule_phrases = ['yes', 'yeah', 'sure', 'ok', 'okay', 'yep', 'yup', 'please', 'reschedule',
                              'change', 'different date', 'another date', 'move it', 'new date',
                              'go ahead', 'do it', 'proceed', 'let me reschedule', 'i want to reschedule']
        is_reschedule = any(phrase in message_lower for phrase in reschedule_phrases)

        # Check for details request
        details_phrases = ['details', 'check', 'appointment', 'when is', 'what time', 'what date', 'info']
        is_details = any(phrase in message_lower for phrase in details_phrases)

        if is_reschedule and selected_project_id:
            project_info = project_mapping.get(str(selected_project_id), {})
            logger.info(f"[CONTINUATION] RESCHEDULE CONFIRM: User confirmed reschedule for project {selected_project_id} - calling reschedule_appointment with confirmed=True")
            return {
                'continue_workflow': True,
                'action': 'reschedule_appointment',  # Call directly with confirmed=True (user already consented)
                'params': {
                    'project_id': str(selected_project_id),
                    'confirmed': True  # User consent obtained - cancel existing and fetch dates
                },
                'next_stage': 'awaiting_date_selection',
                'preserve_context': {
                    'project_id': str(selected_project_id),
                    'project_ids': project_ids,
                    'project_mapping': project_mapping,
                    'category': project_info.get('category', ''),
                    'address': project_info.get('address', ''),
                    'is_reschedule': True
                },
                'workflow_type': 'reschedule_appointment'
            }

        if is_details and selected_project_id:
            project_info = project_mapping.get(str(selected_project_id), {})
            logger.info(f"[CONTINUATION] RESCHEDULE -> DETAILS: User wants to check appointment details for {selected_project_id}")
            return {
                'continue_workflow': True,
                'action': 'get_project_details',
                'params': {
                    'project_id': str(selected_project_id)
                },
                'next_stage': 'showing_details',
                'preserve_context': {
                    'project_id': str(selected_project_id),
                    'project_ids': project_ids,
                    'project_mapping': project_mapping,
                    'category': project_info.get('category', '')
                },
                'workflow_type': 'view_appointment'
            }

    # ========================================================================
    # SMART PROMPT CONTEXT HANDLER (Voice channel)
    # GPT-4o may respond using embedded project state WITHOUT calling a tool.
    # Example: "Your blinds project is already scheduled. Would you like to reschedule?"
    # When user says "yes" or "reschedule", this handler routes to reschedule_appointment
    # using the project_id from the smart prompt context.
    #
    # This handler is triggered when:
    # 1. workflow_type is 'smart_prompt_context' (created when project_id is passed from voice)
    # 2. OR workflow_type is 'project_list' (from welcome) and project_id is in context
    # 3. AND current_stage is 'initial' or 'projects_displayed' (haven't started a workflow yet)
    # ========================================================================
    is_smart_prompt_eligible = (
        workflow_type in ['smart_prompt_context', 'project_list'] and
        current_stage in ['initial', 'projects_displayed'] and
        context.get('project_id')  # project_id was injected from smart prompt
    )

    if is_smart_prompt_eligible:
        project_id_from_context = context.get('project_id')

        # Check for reschedule confirmation
        reschedule_phrases = ['yes', 'yeah', 'sure', 'ok', 'okay', 'yep', 'yup', 'please', 'reschedule',
                              'change', 'different date', 'another date', 'move it', 'new date',
                              'go ahead', 'do it', 'proceed', 'i want to reschedule', 'i\'d like to reschedule',
                              'like to reschedule', 'want to reschedule']
        is_reschedule = any(phrase in message_lower for phrase in reschedule_phrases)

        # Check for schedule confirmation (not just reschedule)
        schedule_phrases = ['schedule', 'book', 'available dates', 'when can']
        is_schedule = any(phrase in message_lower for phrase in schedule_phrases)

        if is_reschedule or is_schedule:
            # Determine if this is a reschedule or new schedule based on project status
            project_status = context.get('project_status', '').lower()
            project_mapping = context.get('project_mapping', {})

            # Try to get status from project_mapping if not in context
            if not project_status and project_mapping:
                project_info = project_mapping.get(str(project_id_from_context), {})
                project_status = project_info.get('status', '').lower()

            scheduled_statuses = ['scheduled', 'customer scheduled', 'tentatively scheduled']
            is_already_scheduled = project_status in scheduled_statuses

            if is_already_scheduled:
                # Project is scheduled - use reschedule_appointment
                logger.info(f"[CONTINUATION] SMART-PROMPT RESCHEDULE: Project {project_id_from_context} is scheduled (status={project_status}) - calling reschedule_appointment")
                return {
                    'continue_workflow': True,
                    'action': 'reschedule_appointment',
                    'params': {
                        'project_id': str(project_id_from_context),
                        'confirmed': True  # User consent already obtained via GPT-4o conversation
                    },
                    'next_stage': 'awaiting_date_selection',
                    'preserve_context': {
                        'project_id': str(project_id_from_context),
                        'project_ids': context.get('project_ids', [project_id_from_context]),
                        'is_reschedule': True
                    },
                    'workflow_type': 'reschedule_appointment'
                }
            else:
                # Project status unknown or not scheduled
                # If user said "reschedule", use rescheduler API even if status is unknown
                # (rescheduler API works for both new scheduling and reschedule)
                use_reschedule_api = is_reschedule or not project_status  # Unknown status + reschedule intent

                if is_reschedule:
                    logger.info(f"[CONTINUATION] SMART-PROMPT: User said 'reschedule' but status unknown ('{project_status}') - using rescheduler API")
                else:
                    logger.info(f"[CONTINUATION] SMART-PROMPT SCHEDULE: Project {project_id_from_context} is not scheduled (status={project_status}) - calling get_available_dates")

                return {
                    'continue_workflow': True,
                    'action': 'get_available_dates',
                    'params': {
                        'project_id': str(project_id_from_context),
                        'is_reschedule': use_reschedule_api  # Use rescheduler API if user said "reschedule"
                    },
                    'next_stage': 'awaiting_date_selection',
                    'preserve_context': {
                        'project_id': str(project_id_from_context),
                        'project_ids': context.get('project_ids', [project_id_from_context]),
                        'is_reschedule': use_reschedule_api
                    },
                    'workflow_type': 'reschedule_appointment' if use_reschedule_api else 'schedule_appointment'
                }

        # Check for details request
        details_phrases = ['details', 'check', 'appointment', 'when is', 'what time', 'what date', 'info', 'tell me about']
        is_details = any(phrase in message_lower for phrase in details_phrases)

        if is_details:
            logger.info(f"[CONTINUATION] SMART-PROMPT DETAILS: User wants details for project {project_id_from_context} (workflow_type={workflow_type})")
            return {
                'continue_workflow': True,
                'action': 'get_project_details',
                'params': {
                    'project_id': str(project_id_from_context)
                },
                'next_stage': 'showing_details',
                'preserve_context': {
                    'project_id': str(project_id_from_context),
                    'project_ids': context.get('project_ids', [project_id_from_context])
                },
                'workflow_type': 'view_project'
            }

    # ========================================================================
    # Stage: SHOWING SCHEDULABLE PROJECTS - User selects a project to schedule
    # When user names a project by category, ordinal, or project number after
    # seeing schedulable projects, go directly to get_available_dates
    # Handles multiple stage names: showing_schedulable_projects, project_selection, awaiting_project_selection
    # Also handles guided_selection workflow when user initiated with "schedule a project"
    # ========================================================================
    # Check if this is a scheduling-related guided selection
    pending_action = context.get('pending_action', '')
    is_scheduling_guided = (workflow_type == 'guided_selection' and
                            any(kw in str(pending_action).lower() for kw in ['schedule', 'book', 'available dates']))

    # Also handle project switch during awaiting_date_selection (user picks different project after one failed/was already scheduled)
    is_project_selection_stage = current_stage in ['showing_schedulable_projects', 'project_selection', 'awaiting_project_selection']
    is_switching_project_during_dates = (current_stage == 'awaiting_date_selection' and
                                         workflow_type == 'schedule_appointment' and
                                         not extract_date_from_message(message))  # Not providing a date

    # Also allow smart_prompt_context, category_resolved, project_listing - any state where user has seen projects
    is_valid_workflow = workflow_type in ['schedule_appointment', 'smart_prompt_context', 'category_resolved', 'project_listing'] or is_scheduling_guided

    if (is_project_selection_stage or is_switching_project_during_dates) and is_valid_workflow:
        # Get project_ids and project_mapping from context (these ARE saved)
        project_ids = context.get('project_ids', [])
        project_mapping = context.get('project_mapping', {})

        logger.info(f"[CONTINUATION] {current_stage}: {len(project_ids)} projects available, mapping keys: {list(project_mapping.keys())[:5]}")

        # Try to match user's reference to a project
        selected_project_id = None

        # Check for ordinal references: "the first one", "second project", "1st", "2nd", etc.
        ordinal_map = {
            'first': 1, '1st': 1, 'one': 1,
            'second': 2, '2nd': 2, 'two': 2,
            'third': 3, '3rd': 3, 'three': 3,
            'fourth': 4, '4th': 4, 'four': 4,
            'fifth': 5, '5th': 5, 'five': 5,
            'sixth': 6, '6th': 6, 'six': 6,
            'seventh': 7, '7th': 7, 'seven': 7,
            'eighth': 8, '8th': 8, 'eight': 8,
            'ninth': 9, '9th': 9, 'nine': 9,
            'tenth': 10, '10th': 10, 'ten': 10,
            'last': -1
        }

        for word, ordinal in ordinal_map.items():
            if word in message_lower:
                if ordinal == -1 and project_ids:
                    selected_project_id = project_ids[-1]
                    logger.info(f"[CONTINUATION] Ordinal 'last' matched project {selected_project_id}")
                elif 0 < ordinal <= len(project_ids):
                    selected_project_id = project_ids[ordinal - 1]
                    logger.info(f"[CONTINUATION] Ordinal '{word}' matched project {selected_project_id}")
                break

        # Check for project number: user says "45345" or "order 21076"
        # Customers know their ORDER/PROJECT NUMBER, not internal IDs
        if not selected_project_id:
            # Extract numeric strings from message (re is imported globally at top of file)
            numbers_in_message = re.findall(r'\b(\d{4,10})\b', message)  # 4-10 digit numbers
            for num in numbers_in_message:
                # Check project_number (customer-facing order number) - this is what customers know
                for pid, pinfo in project_mapping.items():
                    proj_num = str(pinfo.get('project_number', '') or pinfo.get('projectNumber', ''))
                    if num in proj_num:
                        selected_project_id = pid
                        logger.info(f"[CONTINUATION] Project number '{num}' matched in '{proj_num}' → project {pid}")
                        break
                if selected_project_id:
                    break

        # Check for category match: "washer dryer", "storm door", "decking", etc.
        # EXPANDED: Added blinds, installation, measurement, and more common categories
        if not selected_project_id:
            category_keywords = [
                # Window treatments
                'blinds', 'shutters', 'shades', 'curtains', 'window treatment',
                # Project types
                'installation', 'measurement', 'repair', 'replacement', 'service',
                # Appliances
                'storm door', 'decking', 'dishwasher', 'sink', 'oven',
                'washer dryer', 'washer', 'dryer', 'cooktop', 'exterior',
                'electric', 'kitchen', 'windows', 'doors', 'faucet',
                'refrigerator', 'fridge', 'microwave', 'range', 'garbage disposal',
                # HVAC & Plumbing
                'plumbing', 'hvac', 'heating', 'cooling', 'air conditioning', 'ac unit',
                # Outdoor
                'fence', 'fencing', 'roofing', 'roof', 'siding', 'gutter', 'patio', 'balcony',
                # Solar
                'solar', 'panel', 'battery',
                # Flooring
                'flooring', 'carpet', 'tile', 'hardwood', 'laminate', 'vinyl'
            ]

            # First, try to match type-specific keywords (e.g., "installation" vs "measurement")
            # to filter down when there are multiple projects of same category
            type_keywords = {'installation', 'measurement', 'repair', 'replacement', 'service'}
            requested_type = None
            for tk in type_keywords:
                if tk in message_lower:
                    requested_type = tk
                    logger.info(f"[CONTINUATION] User specified project type: '{requested_type}'")
                    break

            for kw in category_keywords:
                if kw in message_lower:
                    # Find matching project by category using project_mapping
                    # Prefer projects that also match the requested type (if specified)
                    best_match = None
                    best_match_has_type = False
                    schedulable_statuses = ['new', 'ready to schedule']

                    for pid, pinfo in project_mapping.items():
                        proj_category = (pinfo.get('category') or '').lower()
                        proj_type = (pinfo.get('project_type') or '').lower()
                        proj_status = (pinfo.get('status') or '').lower()
                        category_bucket = (pinfo.get('category_bucket') or '').lower()

                        if kw in proj_category or kw in proj_type or kw in category_bucket:
                            type_matches = requested_type and requested_type in proj_type
                            is_schedulable = proj_status in schedulable_statuses

                            # Prefer: schedulable + type match > schedulable > type match > any
                            if type_matches and is_schedulable:
                                best_match = pid
                                best_match_has_type = True
                                logger.info(f"[CONTINUATION] Perfect match: category '{kw}' + type '{requested_type}' + schedulable → {pid}")
                                break  # Found perfect match
                            elif is_schedulable and not best_match_has_type:
                                best_match = pid
                                logger.info(f"[CONTINUATION] Schedulable match: category '{kw}' → {pid} (status={proj_status})")
                            elif not best_match:
                                best_match = pid
                                logger.info(f"[CONTINUATION] Fallback match: category '{kw}' → {pid}")

                    if best_match:
                        selected_project_id = best_match
                        break

        # If we found a project, go directly to get_available_dates
        if selected_project_id:
            # Get project info for context preservation
            matched_project_info = project_mapping.get(str(selected_project_id), {})
            matched_category = matched_project_info.get('category', '')
            matched_type = matched_project_info.get('project_type', '')
            matched_status = matched_project_info.get('status', '').lower()

            # Check if this is a reschedule scenario
            scheduled_statuses = ['scheduled', 'customer scheduled', 'tentatively scheduled']
            is_project_scheduled = matched_status in scheduled_statuses
            is_reschedule_context = 'reschedule' in message_lower or is_project_scheduled

            logger.info(f"[CONTINUATION] SCHEDULE PROJECT SELECTION: User selected project {selected_project_id} ({matched_category} {matched_type}, status={matched_status}) - is_reschedule={is_reschedule_context}")
            return {
                'continue_workflow': True,
                'action': 'get_available_dates',
                'params': {
                    'project_id': str(selected_project_id),
                    'is_reschedule': is_reschedule_context  # Use rescheduler API if already scheduled
                },
                'next_stage': 'awaiting_date_selection',
                'preserve_context': {
                    'project_id': str(selected_project_id),
                    'category': matched_category,
                    'project_type': matched_type,
                    'project_ids': project_ids,
                    'project_mapping': project_mapping,
                    'is_reschedule': is_reschedule_context
                },
                'workflow_type': 'reschedule_appointment' if is_reschedule_context else 'schedule_appointment'
            }

    # Stage: Awaiting cancel confirmation (two-step cancel flow)
    if current_stage == 'awaiting_cancel_confirmation':
        # Check for confirmation or denial
        confirm_patterns = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'confirm', 'proceed', 'go ahead', 'do it']
        deny_patterns = ['no', 'nope', 'keep it', 'keep', 'dont cancel', "don't cancel", 'never mind', 'cancel that']

        is_confirm = any(pattern in message_lower for pattern in confirm_patterns)
        is_deny = any(pattern in message_lower for pattern in deny_patterns)

        if is_confirm:
            logger.info(f"[CONTINUATION] User confirmed cancel at stage '{current_stage}', workflow_type={workflow_type}")

            # Check if this is a reschedule workflow - if so, continue to date selection
            is_reschedule = workflow_type == 'reschedule_appointment'

            if is_reschedule:
                logger.info(f"[CONTINUATION] Reschedule workflow - will fetch dates after cancel")
                return {
                    'continue_workflow': True,
                    'action': 'cancel_appointment_execute',
                    'params': {
                        'project_id': context.get('project_id'),
                        'confirmed': True,
                        'is_reschedule': True  # Signal to fetch dates after cancel
                    },
                    'next_stage': 'cancelled_awaiting_dates',
                    'preserve_context': {
                        'project_id': context.get('project_id'),
                        'category': context.get('category'),
                        'project_type': context.get('project_type'),
                        'city': context.get('city'),
                        'state': context.get('state')
                    },
                    'workflow_type': workflow_type
                }
            else:
                # Regular cancel - complete the workflow
                return {
                    'continue_workflow': True,
                    'action': 'cancel_appointment_execute',
                    'params': {
                        'project_id': context.get('project_id'),
                        'confirmed': True
                    },
                    'next_stage': 'complete',
                    'preserve_context': {},
                    'workflow_type': workflow_type
                }
        elif is_deny:
            logger.info(f"[CONTINUATION] User denied cancel at stage '{current_stage}'")
            return {
                'continue_workflow': True,
                'action': 'abort_workflow',
                'params': {},
                'next_stage': 'aborted',
                'preserve_context': {},
                'workflow_type': workflow_type,
                'abort_message': "Okay, I'll keep your appointment. Anything else I can help with?"
            }

    # Stage: Waiting for user to CONFIRM they want to reschedule (appointment NOT cancelled yet)
    if current_stage == 'awaiting_reschedule_confirm' and workflow_type == 'reschedule_appointment':
        confirm_patterns = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'reschedule', 'change', 'proceed', 'go ahead']
        deny_patterns = ['no', 'nope', 'never', 'cancel', 'stop', 'don\'t', 'dont', 'keep']
        message_lower = message.lower().strip()
        is_confirmation = any(pattern in message_lower for pattern in confirm_patterns)
        is_deny = any(pattern in message_lower for pattern in deny_patterns) and not is_confirmation

        if is_confirmation:
            logger.info(f"[CONTINUATION] User CONFIRMED reschedule at stage '{current_stage}' - now cancelling and fetching dates")
            return {
                'continue_workflow': True,
                'action': 'reschedule_appointment',
                'params': {
                    'project_id': context.get('project_id'),
                    'confirmed': True  # User consent obtained - now cancel and fetch dates
                },
                'next_stage': 'awaiting_date_selection',
                'preserve_context': {
                    'project_id': context.get('project_id'),
                    'category': context.get('category'),
                    'project_type': context.get('project_type'),
                    'city': context.get('city'),
                    'state': context.get('state')
                },
                'workflow_type': workflow_type
            }
        elif is_deny:
            logger.info(f"[CONTINUATION] User DECLINED reschedule at stage '{current_stage}' - keeping existing appointment")
            return {
                'continue_workflow': True,
                'action': 'abort_workflow',
                'params': {},
                'next_stage': 'aborted',
                'preserve_context': {},
                'workflow_type': workflow_type,
                'abort_message': "No problem, I'll keep your existing appointment. Is there anything else I can help you with?"
            }

    # Stage: AWAITING APPOINTMENT CONFIRM - User selected date/time, must confirm before finalizing
    if current_stage == 'awaiting_appointment_confirm':
        confirm_patterns = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'confirm', 'book', 'schedule', 'proceed', 'go ahead', 'sounds good', 'perfect', 'that works']
        deny_patterns = ['no', 'nope', 'never', 'cancel', 'stop', 'don\'t', 'dont', 'wait', 'hold on', 'change', 'different']
        message_lower = message.lower().strip()
        is_confirmation = any(pattern in message_lower for pattern in confirm_patterns)
        is_deny = any(pattern in message_lower for pattern in deny_patterns) and not is_confirmation

        if is_confirmation:
            logger.info(f"[CONTINUATION] User CONFIRMED appointment at stage '{current_stage}' - finalizing booking")
            return {
                'continue_workflow': True,
                'action': 'confirm_appointment',
                'params': {
                    'project_id': context.get('project_id'),
                    'date': context.get('date'),
                    'time': context.get('time'),
                    'request_id': context.get('request_id'),
                    'category': context.get('category'),
                    'confirmed': True  # User consent obtained - finalize the appointment
                },
                'next_stage': 'complete',
                'preserve_context': {
                    'project_id': context.get('project_id'),
                    'category': context.get('category'),
                    'date': context.get('date'),
                    'time': context.get('time')
                },
                'workflow_type': workflow_type
            }
        elif is_deny:
            logger.info(f"[CONTINUATION] User DECLINED appointment confirmation at stage '{current_stage}'")
            return {
                'continue_workflow': True,
                'action': 'abort_workflow',
                'params': {},
                'next_stage': 'aborted',
                'preserve_context': {
                    'project_id': context.get('project_id'),
                    'category': context.get('category')
                },
                'workflow_type': workflow_type,
                'abort_message': "No problem. Would you like to pick a different date or time?"
            }

    # Stage: Cancelled, waiting for user to confirm fetching dates (legacy two-step reschedule)
    # NOTE: This is kept for backward compatibility - new flow uses awaiting_reschedule_confirm
    if current_stage == 'cancelled_awaiting_dates':
        # Check if user confirms with yes/show dates/continue etc.
        confirm_patterns = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'show', 'dates', 'continue', 'proceed', 'go ahead']
        message_lower = message.lower().strip()
        is_confirmation = any(pattern in message_lower for pattern in confirm_patterns)

        if is_confirmation:
            logger.info(f"[CONTINUATION] User confirmed to fetch dates at stage '{current_stage}' - fetching available dates")
            return {
                'continue_workflow': True,
                'action': 'reschedule_appointment',
                'params': {
                    'project_id': context.get('project_id'),
                    'confirmed': True  # Appointment already cancelled, just fetch dates
                },
                'next_stage': 'awaiting_date_selection',
                'preserve_context': {
                    'project_id': context.get('project_id'),
                    'category': context.get('category'),
                    'project_type': context.get('project_type'),
                    'city': context.get('city'),
                    'state': context.get('state')
                },
                'workflow_type': workflow_type
            }

    # Stage: Waiting for date selection
    if current_stage == 'awaiting_date_selection':
        # IMPORTANT: Don't treat as date selection if user is asking for a DATE RANGE
        # Patterns like "show me dates between X and Y", "dates from X to Y" are range requests
        date_range_patterns = [
            'show me dates', 'show dates', 'dates between', 'dates from',
            'between .* and', 'between .* to', 'from .* to', 'different dates',
            'other dates', 'more dates', 'next week', 'upcoming week'
        ]
        is_date_range_request = any(
            (pattern in message_lower if '.*' not in pattern else re.search(pattern, message_lower))
            for pattern in date_range_patterns
        )

        if is_date_range_request:
            logger.info(f"[CONTINUATION] Date range request detected at stage '{current_stage}' - proceeding with classification")
            # Fall through to classification to handle date range properly
        else:
            date = extract_date_from_message(message)
            if date:
                is_reschedule = context.get('is_reschedule', False) or workflow_type == 'reschedule_appointment'
                logger.info(f"[CONTINUATION] User provided date '{date}' at stage '{current_stage}' (is_reschedule={is_reschedule}) - bypassing classification")
                return {
                    'continue_workflow': True,
                    'action': 'get_time_slots',
                    'params': {
                        'project_id': context.get('project_id'),
                        'date': date,
                        'request_id': context.get('request_id'),
                        'is_reschedule': is_reschedule  # Use rescheduler API if in reschedule workflow
                    },
                    'next_stage': 'awaiting_time_selection',
                    'preserve_context': {
                        'project_id': context.get('project_id'),
                        'date': date,
                        'request_id': context.get('request_id'),
                        'category': context.get('category'),
                        'project_type': context.get('project_type'),
                        'city': context.get('city'),
                        'state': context.get('state'),
                        'is_reschedule': is_reschedule,  # Preserve for subsequent calls
                        # Preserve batch mode context if present
                        'batch_mode': context.get('batch_mode'),
                        'project_ids': context.get('project_ids'),
                        'current_index': context.get('current_index'),
                        'total_projects': context.get('total_projects'),
                        'completed_projects': context.get('completed_projects')
                    },
                    'workflow_type': workflow_type
                }

            # Handle "Yes" confirmation when only 1 date was offered
            # User says "Yes" → auto-select the single available date
            available_dates = context.get('available_dates', [])
            confirm_patterns = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'that works', 'sounds good', 'perfect', 'go ahead']
            first_patterns = ['the first', 'first one', 'first date', 'first option']
            is_confirmation = any(pattern in message_lower for pattern in confirm_patterns)
            is_first_selection = any(pattern in message_lower for pattern in first_patterns)

            # Auto-select first date if user says "the first one" (any number of dates)
            # OR if user says "yes" and only 1 date available
            if (is_first_selection and available_dates) or (is_confirmation and len(available_dates) == 1):
                single_date = available_dates[0] if isinstance(available_dates[0], str) else available_dates[0].get('date')
                is_reschedule = context.get('is_reschedule', False) or workflow_type == 'reschedule_appointment'
                logger.info(f"[CONTINUATION] User said 'Yes' with 1 available date - auto-selecting {single_date} (is_reschedule={is_reschedule})")
                return {
                    'continue_workflow': True,
                    'action': 'get_time_slots',
                    'params': {
                        'project_id': context.get('project_id'),
                        'date': single_date,
                        'request_id': context.get('request_id'),
                        'is_reschedule': is_reschedule  # Use rescheduler API if in reschedule workflow
                    },
                    'next_stage': 'awaiting_time_selection',
                    'preserve_context': {
                        'project_id': context.get('project_id'),
                        'date': single_date,
                        'request_id': context.get('request_id'),
                        'category': context.get('category'),
                        'project_type': context.get('project_type'),
                        'city': context.get('city'),
                        'state': context.get('state'),
                        'is_reschedule': is_reschedule,  # Preserve for subsequent calls
                        'batch_mode': context.get('batch_mode'),
                        'project_ids': context.get('project_ids'),
                        'current_index': context.get('current_index'),
                        'total_projects': context.get('total_projects'),
                        'completed_projects': context.get('completed_projects')
                    },
                    'workflow_type': workflow_type
                }

            # Check for month-only reference (e.g., "February", "March", "how about feb")
            # This calls get_available_dates with the month name for the LLM interpreter
            # BUT FIRST: Check if user provided BOTH date AND time (e.g., "11 AM January 30th")
            # In that case, skip straight to confirm_appointment
            time_val = extract_time_from_message(message)
            if time_val:
                # User provided time at date selection stage - they're giving us both date and time
                # Extract the date and go straight to confirmation
                date_val = extract_date_from_message(message)
                if date_val:
                    logger.info(f"[CONTINUATION] User provided BOTH date '{date_val}' AND time '{time_val}' at stage '{current_stage}' - confirming directly")
                    confirm_params = {
                        'project_id': context.get('project_id'),
                        'date': date_val,
                        'time': time_val,
                        'request_id': context.get('request_id')
                    }
                    if channel == 'voice':
                        confirm_params['confirmed'] = True
                        logger.info(f"[CONTINUATION] Voice channel - booking immediately with date+time")
                    return {
                        'continue_workflow': True,
                        'action': 'confirm_appointment',
                        'params': confirm_params,
                        'next_stage': 'complete',
                        'preserve_context': context,
                        'workflow_type': workflow_type
                    }

            month_ref = extract_month_reference(message)
            if month_ref:
                # Preserve is_reschedule from context (set during initial project selection)
                is_reschedule = context.get('is_reschedule', False) or workflow_type == 'reschedule_appointment'
                logger.info(f"[CONTINUATION] User provided month reference '{month_ref}' at stage '{current_stage}' (is_reschedule={is_reschedule}) - calling get_available_dates")
                return {
                    'continue_workflow': True,
                    'action': 'get_available_dates',
                    'params': {
                        'project_id': context.get('project_id'),
                        'date': month_ref,  # Pass month name as-is for LLM interpreter
                        'request_id': context.get('request_id'),  # Preserve for rebooking
                        'is_reschedule': is_reschedule  # Use rescheduler API if in reschedule workflow
                    },
                    'next_stage': 'awaiting_date_selection',  # Stay in date selection
                    'preserve_context': {
                        'project_id': context.get('project_id'),
                        'request_id': context.get('request_id'),  # CRITICAL: Preserve request_id!
                        'available_dates': context.get('available_dates'),  # Preserve cached dates
                        'category': context.get('category'),
                        'project_type': context.get('project_type'),
                        'city': context.get('city'),
                        'state': context.get('state'),
                        'is_reschedule': is_reschedule
                    },
                    'workflow_type': workflow_type
                }

    # Stage: Waiting for time selection
    if current_stage == 'awaiting_time_selection':
        time_val = extract_time_from_message(message)
        if time_val:
            logger.info(f"[CONTINUATION] User provided time '{time_val}' at stage '{current_stage}' - bypassing classification")
            # For voice channel, book immediately (confirmed=True) since GPT-4o manages the conversation
            # For chat/SMS, use two-step confirmation flow
            confirm_params = {
                'project_id': context.get('project_id'),
                'date': context.get('date'),
                'time': time_val,
                'request_id': context.get('request_id')
            }
            if channel == 'voice':
                confirm_params['confirmed'] = True  # Voice: book immediately, GPT-4o handles conversation
                logger.info(f"[CONTINUATION] Voice channel - booking immediately with confirmed=True")
            return {
                'continue_workflow': True,
                'action': 'confirm_appointment',
                'params': confirm_params,
                'next_stage': 'complete',
                'preserve_context': context,
                'workflow_type': workflow_type
            }

        # CHAD FEEDBACK FIX: Handle "Yes" or "That works" after time slots are offered
        # Auto-select the FIRST time slot when user confirms generically
        available_times = context.get('time_slots', [])
        confirm_patterns = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'that works', 'sounds good', 'perfect', 'the first', 'first one']
        is_confirmation = any(pattern in message_lower for pattern in confirm_patterns)

        if is_confirmation and available_times:
            first_time = available_times[0] if isinstance(available_times[0], str) else available_times[0].get('time', available_times[0].get('slot'))
            logger.info(f"[CONTINUATION] User said 'Yes' with time slots available - auto-selecting first time: {first_time}")
            confirm_params = {
                'project_id': context.get('project_id'),
                'date': context.get('date'),
                'time': first_time,
                'request_id': context.get('request_id')
            }
            if channel == 'voice':
                confirm_params['confirmed'] = True
                logger.info(f"[CONTINUATION] Voice channel - booking immediately with first time slot")
            return {
                'continue_workflow': True,
                'action': 'confirm_appointment',
                'params': confirm_params,
                'next_stage': 'complete',
                'preserve_context': context,
                'workflow_type': workflow_type
            }

    # ========================================================================
    # IMPLICIT SCHEDULING: Handle "schedule it", "book it", "schedule this"
    # when we have a project in context (after viewing project details)
    # This ensures "schedule it" uses the currently viewed project
    # ========================================================================
    context_project_id = context.get('project_id')
    if context_project_id:
        # IMPORTANT: Don't match implicit schedule if user says "reschedule"
        # "reschedule this" contains "schedule this" but is a different intent
        if 'reschedule' not in message_lower:
            implicit_schedule_patterns = [
                'schedule it', 'schedule this', 'book it', 'book this',
                'schedule that', 'book that', "let's schedule", "lets schedule",
                'want to schedule', 'like to schedule', 'schedule the project',
                'schedule my', 'book my', 'i want to schedule', 'can you schedule'
            ]
            if any(pattern in message_lower for pattern in implicit_schedule_patterns):
                logger.info(f"[CONTINUATION] IMPLICIT SCHEDULE: Detected scheduling request with context project {context_project_id}")

                # Priority 1: Check if user provided a date in their message (e.g., "schedule the project for 01/27")
                message_date = extract_date_from_message(message)
                if message_date:
                    is_reschedule = context.get('is_reschedule', False) or context.get('status', '').lower() in ['scheduled', 'customer scheduled', 'tentatively scheduled']
                    logger.info(f"[CONTINUATION] Using date from user's message: {message_date} (is_reschedule={is_reschedule})")
                    return {
                        'continue_workflow': True,
                        'action': 'get_time_slots',
                        'params': {
                            'project_id': context_project_id,
                            'date': message_date,
                            'request_id': context.get('request_id'),
                            'is_reschedule': is_reschedule  # Use rescheduler API if project is scheduled
                        },
                        'next_stage': 'awaiting_time_selection',
                        'preserve_context': {
                            'project_id': context_project_id,
                            'date': message_date,
                            'request_id': context.get('request_id'),
                            'category': context.get('category'),
                            'project_type': context.get('project_type'),
                            'city': context.get('city'),
                            'state': context.get('state'),
                            'is_reschedule': is_reschedule
                        },
                        'workflow_type': 'reschedule_appointment' if is_reschedule else 'schedule_appointment'
                    }

                # Priority 2: Check if user has a calendar date in context (from "what day is X" query)
                last_calendar_date = context.get('last_calendar_date')
                last_calendar_display = context.get('last_calendar_date_display')
                if last_calendar_date:
                    is_reschedule = context.get('is_reschedule', False) or context.get('status', '').lower() in ['scheduled', 'customer scheduled', 'tentatively scheduled']
                    logger.info(f"[CONTINUATION] Using last_calendar_date from context: {last_calendar_date} ({last_calendar_display}) (is_reschedule={is_reschedule})")
                    return {
                        'continue_workflow': True,
                        'action': 'get_time_slots',
                        'params': {
                            'project_id': context_project_id,
                            'date': last_calendar_date,
                            'request_id': context.get('request_id'),
                            'is_reschedule': is_reschedule  # Use rescheduler API if project is scheduled
                        },
                        'next_stage': 'awaiting_time_selection',
                        'preserve_context': {
                            'project_id': context_project_id,
                            'date': last_calendar_date,
                            'request_id': context.get('request_id'),
                            'category': context.get('category'),
                            'project_type': context.get('project_type'),
                            'city': context.get('city'),
                            'state': context.get('state'),
                            'is_reschedule': is_reschedule
                        },
                        'workflow_type': 'reschedule_appointment' if is_reschedule else 'schedule_appointment'
                    }

                # Priority 3: No date provided - show available dates
                # Check if project is already scheduled - use rescheduler API
                project_status = context.get('status', '').lower()
                scheduled_statuses = ['scheduled', 'customer scheduled', 'tentatively scheduled']
                is_reschedule = project_status in scheduled_statuses or context.get('is_reschedule', False)

                return {
                    'continue_workflow': True,
                    'action': 'get_available_dates',
                    'params': {
                        'project_id': context_project_id,
                        'is_reschedule': is_reschedule  # Use rescheduler API if already scheduled
                    },
                    'next_stage': 'awaiting_date_selection',
                    'preserve_context': {
                        'project_id': context_project_id,
                        'category': context.get('category'),
                        'project_type': context.get('project_type'),
                        'city': context.get('city'),
                        'state': context.get('state'),
                        'address': context.get('address'),
                        'is_reschedule': is_reschedule
                    },
                    'workflow_type': 'reschedule_appointment' if is_reschedule else 'schedule_appointment'
                }

    # Not a continuation - proceed with normal classification
    logger.info(f"[CONTINUATION] No continuation match for stage '{current_stage}' - proceeding with classification")
    return None


def format_date_natural(date_str: str) -> str:
    """
    Convert date from "MM-DD-YYYY HH:MM AM/PM" format to natural language.
    Examples:
    - "11-29-2025 08:00 AM" -> "November 29, 2025 at 8:00 AM"
    - "11-29-2025 08:00 AM - 11-29-2025 09:00 AM" -> "November 29, 2025 at 8:00 AM - 9:00 AM"
    """
    if not date_str:
        return date_str

    month_names = {
        '01': 'January', '02': 'February', '03': 'March', '04': 'April',
        '05': 'May', '06': 'June', '07': 'July', '08': 'August',
        '09': 'September', '10': 'October', '11': 'November', '12': 'December'
    }

    try:
        # Check if it's a date range (contains " - " with dates on both sides)
        if ' - ' in date_str:
            parts = date_str.split(' - ')
            if len(parts) == 2:
                # Parse start: "MM-DD-YYYY HH:MM AM"
                start_match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}:\d{2}\s*(?:AM|PM))', parts[0].strip(), re.IGNORECASE)
                # Parse end: "MM-DD-YYYY HH:MM AM"
                end_match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}:\d{2}\s*(?:AM|PM))', parts[1].strip(), re.IGNORECASE)

                if start_match and end_match:
                    start_month = month_names.get(start_match.group(1).zfill(2), start_match.group(1))
                    start_day = str(int(start_match.group(2)))  # Remove leading zero
                    start_year = start_match.group(3)
                    start_time = start_match.group(4)
                    end_time = end_match.group(4)

                    # Same date range: "November 29, 2025 at 8:00 AM - 9:00 AM"
                    return f"{start_month} {start_day}, {start_year} at {start_time} - {end_time}"

        # Single date/time: "MM-DD-YYYY HH:MM AM"
        single_match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}:\d{2}\s*(?:AM|PM))', date_str.strip(), re.IGNORECASE)
        if single_match:
            month = month_names.get(single_match.group(1).zfill(2), single_match.group(1))
            day = str(int(single_match.group(2)))  # Remove leading zero
            year = single_match.group(3)
            time = single_match.group(4)
            return f"{month} {day}, {year} at {time}"

        # Date only: "MM-DD-YYYY"
        date_only_match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})$', date_str.strip())
        if date_only_match:
            month = month_names.get(date_only_match.group(1).zfill(2), date_only_match.group(1))
            day = str(int(date_only_match.group(2)))
            year = date_only_match.group(3)
            return f"{month} {day}, {year}"

        # Return original if no pattern matched
        return date_str
    except Exception as e:
        logger.warning(f"Date formatting failed for '{date_str}': {e}")
        return date_str


def extract_project_data_from_history(conversation_history: List[Dict], classification: Dict = None) -> Optional[Dict]:
    """
    Extract project data from conversation history for context queries.
    Looks for project details, scheduled dates, technician info, etc.

    Args:
        conversation_history: List of conversation messages
        classification: Optional classification result with entities (project_id, project_index)
    """
    project_data = {}

    # Get project reference from classification if available
    target_project_id = None
    target_project_index = None
    if classification and classification.get('entities'):
        entities = classification['entities']
        target_project_id = entities.get('project_id')
        target_project_index = entities.get('project_index')
        logger.info(f"[CONTEXT] Looking for project_id={target_project_id}, project_index={target_project_index}")

    logger.info(f"[CONTEXT] Extracting from {len(conversation_history)} messages in history")

    for msg in reversed(conversation_history):
        content = msg.get('content', '')
        role = msg.get('role', '')

        if role != 'assistant':
            continue

        # Look for technician/installer info - multiple patterns
        logger.info(f"[CONTEXT] Scanning message for technician info, length={len(content)}")

        if 'installer' in content.lower() or 'technician' in content.lower() or 'scheduled with' in content.lower():
            logger.info(f"[CONTEXT] Found technician/installer keyword in content")

            # Pattern 1: "scheduled with Jay Installer1 on" (conversational text)
            scheduled_with_match = re.search(r'scheduled with\s+([A-Za-z][A-Za-z0-9\s]+?)\s+on\s', content, re.IGNORECASE)
            if scheduled_with_match and 'technician_name' not in project_data:
                project_data['technician_name'] = scheduled_with_match.group(1).strip()
                logger.info(f"[CONTEXT] Pattern 1 matched: {project_data['technician_name']}")

            # Pattern 1b: "technician, Name, will" or "technician Name will"
            tech_will_match = re.search(r'technician[,\s]+([A-Za-z][A-Za-z0-9\s]+?)[,\s]+will', content, re.IGNORECASE)
            if tech_will_match and 'technician_name' not in project_data:
                project_data['technician_name'] = tech_will_match.group(1).strip()
                logger.info(f"[CONTEXT] Pattern 1b matched: {project_data['technician_name']}")

            # Pattern 2: "Assigned Technician\nJay Installer1 (ID: 8203)" (formatted output)
            assigned_match = re.search(r'Assigned Technician\s*[\n\r]+\s*([A-Za-z][A-Za-z0-9\s]+?)\s*\(ID:\s*(\d+)\)', content, re.IGNORECASE)
            if assigned_match and 'technician_name' not in project_data:
                project_data['technician_name'] = assigned_match.group(1).strip()
                project_data['technician_id'] = assigned_match.group(2)

            # Pattern 3: "Technician: Jay Installer1" or "Installer: Jay Installer1"
            colon_match = re.search(r'(?:installer|technician)[:\s]+([A-Za-z][A-Za-z0-9\s]+?)(?:\s*\(|,|\.|$)', content, re.IGNORECASE)
            if colon_match and 'technician_name' not in project_data:
                project_data['technician_name'] = colon_match.group(1).strip()

            # Pattern 4: "Assigned Technician ... Name (ID: 8203)" - alternate format
            alt_match = re.search(r'Assigned\s+Technician\s*[:\-]?\s*([A-Z][a-z]+\s+[A-Z][a-z0-9]+)\s*\(ID:\s*(\d+)\)', content)
            if alt_match and 'technician_name' not in project_data:
                project_data['technician_name'] = alt_match.group(1).strip()
                project_data['technician_id'] = alt_match.group(2)

            # Pattern 5: Direct "Name (ID: 8203)" after any technician mention
            direct_match = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z0-9]+)\s*\(ID:\s*(\d+)\)', content)
            if direct_match and 'technician_name' not in project_data:
                project_data['technician_name'] = direct_match.group(1).strip()
                project_data['technician_id'] = direct_match.group(2)
                logger.info(f"[CONTEXT] Pattern 5 matched: {project_data['technician_name']}")

        # Try to extract from JSON in response
        try:
            # Look for JSON blocks in the response
            json_matches = re.findall(r'```json\s*([\s\S]*?)```', content)
            for json_str in json_matches:
                data = json.loads(json_str)
                logger.info(f"[CONTEXT] Parsing JSON block, keys: {list(data.keys())}")

                # Extract installer info - check multiple possible locations
                installer = data.get('installer') or data.get('technician')
                if installer:
                    logger.info(f"[CONTEXT] Found installer data: {installer}")
                    if isinstance(installer, dict):
                        if installer.get('name') and 'technician_name' not in project_data:
                            project_data['technician_name'] = installer['name']
                            logger.info(f"[CONTEXT] Extracted technician_name from JSON: {installer['name']}")
                        if installer.get('id') and 'technician_id' not in project_data:
                            project_data['technician_id'] = str(installer['id'])
                    elif isinstance(installer, str) and 'technician_name' not in project_data:
                        project_data['technician_name'] = installer

                # Check for technician_display at root level (e.g., "Jay Installer1 (ID: 8203)")
                tech_display = data.get('technician_display', '')
                if tech_display and tech_display != 'Not assigned' and 'technician_name' not in project_data:
                    # Parse "Name (ID: 123)" format - re module already imported at top
                    display_match = re.match(r'^(.+?)\s*\(ID:\s*(\d+)\)$', tech_display)
                    if display_match:
                        project_data['technician_name'] = display_match.group(1).strip()
                        project_data['technician_id'] = display_match.group(2)
                        logger.info(f"[CONTEXT] Extracted from technician_display: {project_data['technician_name']}")
                    else:
                        project_data['technician_name'] = tech_display
                        logger.info(f"[CONTEXT] Used technician_display directly: {tech_display}")

                # Extract category from root level
                if data.get('category') and 'category' not in project_data:
                    project_data['category'] = data['category']
                    logger.info(f"[CONTEXT] Extracted category from root: {data['category']}")

                # Extract project_id from root level
                if data.get('project_id') and 'project_id' not in project_data:
                    project_data['project_id'] = data['project_id']

                # NEW: Check for projects array (from welcome/list_projects response)
                if 'projects' in data and isinstance(data['projects'], list) and len(data['projects']) > 0:
                    projects_list = data['projects']
                    logger.info(f"[CONTEXT] Found projects array with {len(projects_list)} projects")

                    # Find the target project by ID or index
                    target_proj = None
                    if target_project_id:
                        # First try exact match
                        for p in projects_list:
                            if str(p.get('id')) == str(target_project_id):
                                target_proj = p
                                logger.info(f"[CONTEXT] Matched project by exact ID: {target_project_id}")
                                break

                        # If no exact match, try partial matching
                        if not target_proj:
                            # Build temp mapping for partial match
                            temp_mapping = {str(p.get('id')): p for p in projects_list if p.get('id')}
                            matched_pid = find_project_by_partial_id(str(target_project_id), temp_mapping)
                            if matched_pid:
                                target_proj = temp_mapping[matched_pid]
                                logger.info(f"[CONTEXT] Matched project by partial ID: {target_project_id} -> {matched_pid}")
                    elif target_project_index is not None:
                        # Support negative indices: -1 = last, -2 = second to last, etc.
                        try:
                            target_proj = projects_list[target_project_index]
                            actual_id = target_proj.get('id', 'unknown')
                            logger.info(f"[CONTEXT] Matched project by index: {target_project_index} -> project #{actual_id}")
                        except IndexError:
                            logger.warning(f"[CONTEXT] Index {target_project_index} out of range for {len(projects_list)} projects")
                    elif len(projects_list) == 1:
                        # Only one project, use it
                        target_proj = projects_list[0]
                        logger.info(f"[CONTEXT] Using only project in list")

                    if target_proj:
                        # FOUND EXACT MATCH - extract all data and return immediately
                        # This prevents data from other projects bleeding in
                        matched_data = {}

                        # Extract technician from installer field
                        if target_proj.get('installer'):
                            inst = target_proj['installer']
                            if isinstance(inst, dict):
                                matched_data['technician_name'] = inst.get('name', '')
                                matched_data['technician_id'] = str(inst.get('id', ''))
                                logger.info(f"[CONTEXT] Extracted technician from projects array: {matched_data['technician_name']}")

                        # Extract scheduled date/time
                        if target_proj.get('scheduledDate'):
                            sched = target_proj['scheduledDate']
                            matched_data['scheduled_date'] = sched
                            # Parse time from "11-29-2025 08:00 AM - 11-29-2025 09:00 AM" format
                            time_range_match = re.search(
                                r'(\d{1,2}:\d{2}\s*(?:AM|PM))\s*-\s*\d{1,2}-\d{1,2}-\d{4}\s*(\d{1,2}:\d{2}\s*(?:AM|PM))',
                                sched, re.IGNORECASE
                            )
                            if time_range_match:
                                start_time = time_range_match.group(1)
                                end_time = time_range_match.group(2)
                                matched_data['scheduled_time'] = f"{start_time} - {end_time}"
                                logger.info(f"[CONTEXT] Extracted time range from projects: {matched_data['scheduled_time']}")

                        # Extract other fields
                        if target_proj.get('category'):
                            matched_data['category'] = target_proj['category']
                        if target_proj.get('id'):
                            matched_data['project_id'] = str(target_proj['id'])
                        if target_proj.get('status'):
                            matched_data['status'] = target_proj['status']
                        if target_proj.get('address'):
                            addr = target_proj['address']
                            if isinstance(addr, dict):
                                matched_data['address'] = addr.get('fullAddress') or f"{addr.get('address1', '')}, {addr.get('city', '')}, {addr.get('state', '')} {addr.get('zipcode', '')}"
                                matched_data['city'] = addr.get('city', '')
                                matched_data['state'] = addr.get('state', '')
                                logger.info(f"[CONTEXT] Extracted address: {matched_data['address']}, city={addr.get('city')}, state={addr.get('state')}")
                            else:
                                matched_data['address'] = addr

                        # RETURN IMMEDIATELY with matched data - prevents context bleeding
                        logger.info(f"[CONTEXT] EXACT MATCH found for project {target_project_id} - returning immediately")
                        logger.info(f"[CONTEXT] Final extracted project_data: {matched_data}")
                        return matched_data

                # Also check for nested project data
                if 'project' in data and isinstance(data['project'], dict):
                    proj = data['project']

                    # Check project.installer first
                    if proj.get('installer') and 'technician_name' not in project_data:
                        inst = proj['installer']
                        if isinstance(inst, dict) and inst.get('name'):
                            project_data['technician_name'] = inst['name']
                            project_data['technician_id'] = str(inst.get('id', ''))
                            logger.info(f"[CONTEXT] Extracted from nested project.installer: {inst['name']}")

                    # Also check project.technician (added alongside installer in response)
                    if proj.get('technician') and 'technician_name' not in project_data:
                        tech = proj['technician']
                        if isinstance(tech, dict) and tech.get('name'):
                            project_data['technician_name'] = tech['name']
                            project_data['technician_id'] = str(tech.get('id', ''))
                            logger.info(f"[CONTEXT] Extracted from nested project.technician: {tech['name']}")

                # Extract appointment info
                if 'appointment' in data:
                    appt = data['appointment']
                    if appt.get('date'):
                        project_data['scheduled_date'] = appt['date']
                    if appt.get('time'):
                        project_data['scheduled_time'] = appt['time']

                # Extract from scheduledDate field
                if 'scheduledDate' in data:
                    sched = data['scheduledDate']
                    project_data['scheduled_date'] = sched
                    # Parse time from "11-29-2025 08:00 AM - 11-29-2025 09:00 AM" format
                    if 'scheduled_time' not in project_data:
                        time_range_match = re.search(
                            r'(\d{1,2}:\d{2}\s*(?:AM|PM))\s*-\s*\d{1,2}-\d{1,2}-\d{4}\s*(\d{1,2}:\d{2}\s*(?:AM|PM))',
                            sched, re.IGNORECASE
                        )
                        if time_range_match:
                            start_time = time_range_match.group(1)
                            end_time = time_range_match.group(2)
                            project_data['scheduled_time'] = f"{start_time} - {end_time}"
                            logger.info(f"[CONTEXT] Extracted time range: {project_data['scheduled_time']}")

                # Extract project category
                if 'category' in data:
                    project_data['category'] = data['category']

                # Extract project ID
                if 'id' in data:
                    project_data['project_id'] = data['id']
                elif 'project_id' in data:
                    project_data['project_id'] = data['project_id']

                # Extract address
                if 'full_address' in data:
                    project_data['address'] = data['full_address']
                elif 'address' in data:
                    addr = data['address']
                    if isinstance(addr, dict):
                        project_data['address'] = addr.get('fullAddress', '')
                    else:
                        project_data['address'] = addr

        except (json.JSONDecodeError, TypeError):
            pass

        # Look for scheduled date patterns in text
        date_match = re.search(r'scheduled (?:for|on)\s+([A-Za-z]+\s+\d+(?:st|nd|rd|th)?(?:,?\s+\d{4})?)', content, re.IGNORECASE)
        if date_match and 'scheduled_date' not in project_data:
            project_data['scheduled_date'] = date_match.group(1)

        # Look for time patterns
        time_match = re.search(r'at\s+(\d{1,2}:\d{2}\s*(?:AM|PM)?)', content, re.IGNORECASE)
        if time_match and 'scheduled_time' not in project_data:
            project_data['scheduled_time'] = time_match.group(1)

        # Look for project ID patterns
        project_id_match = re.search(r'#(\d{7})\b', content)
        if project_id_match and 'project_id' not in project_data:
            project_data['project_id'] = project_id_match.group(1)

        # Look for category patterns
        category_match = re.search(r'(Decking|Flooring|Roofing|Kitchen|Bathroom|Siding|Windows)\s+(?:project|installation)', content, re.IGNORECASE)
        if category_match and 'category' not in project_data:
            project_data['category'] = category_match.group(1)

    logger.info(f"[CONTEXT] Final extracted project_data: {project_data}")
    return project_data if project_data else None


def get_bedrock_runtime():
    """Get or create Bedrock runtime client"""
    global _bedrock_runtime
    if _bedrock_runtime is None:
        config = get_config()
        boto_config = BotoConfig(
            region_name=config.region,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        _bedrock_runtime = boto3.client('bedrock-runtime', config=boto_config)
        logger.info("Bedrock runtime client created for Sonnet 3.7")
    return _bedrock_runtime


def call_sonnet(prompt: str, max_tokens: int = 1000, temperature: float = 0.0) -> str:
    """
    Call Sonnet 3.7 and return the response text
    """
    config = get_config()
    bedrock = get_bedrock_runtime()

    try:
        response = bedrock.invoke_model(
            modelId=config.orchestrator_model,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text'].strip()

    except Exception as e:
        logger.error(f"Sonnet invocation error: {e}")
        raise


def format_conversation_history(history: List[Dict]) -> str:
    """Format conversation history for Sonnet"""
    if not history:
        return "No previous conversation."

    lines = []
    # Include last 5 messages for context
    for msg in history[-5:]:
        role = "User" if msg['role'] == 'user' else "Assistant"
        content = msg['content']

        # Truncate long responses
        if len(content) > 500:
            content = content[:500] + "..."

        lines.append(f"{role}: {content}")

    return "\n".join(lines)


def intelligent_classify(
    message: str,
    conversation_history: Optional[List[Dict]] = None,
    current_workflow_state: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Use Sonnet 3.7 to intelligently classify intent and extract ALL context

    Returns:
    {
        "intent": "scheduling|information|chitchat",
        "action": "specific_action_name",
        "entities": {"project_id": "7751748", "date": "2025-11-27", ...},
        "workflow_type": "schedule_appointment|reschedule|cancel",
        "reasoning": "User wants to schedule project 7751748 for Nov 27"
    }
    """
    conversation_context = format_conversation_history(conversation_history)

    workflow_context = ""
    if current_workflow_state:
        context = current_workflow_state.get('context', {})
        project_mapping = current_workflow_state.get('project_mapping', {}) or context.get('project_mapping', {})
        viewed_projects = current_workflow_state.get('viewed_projects', [])

        # Format project_mapping for clear display
        # Show projectNumber (Order Number) for user display - never show internal IDs to users
        project_mapping_str = ""
        if project_mapping:
            mapping_lines = []
            for pid, info in project_mapping.items():
                cat = info.get('category', 'Unknown')
                project_number = info.get('projectNumber', '')
                # Only show entries with projectNumber (user-facing Order Numbers)
                # Skip reverse-lookup entries (Order Number -> internal ID mappings)
                if project_number:
                    mapping_lines.append(f"  - Project #{project_number}: category='{cat}'")
            project_mapping_str = f"""

AVAILABLE PROJECTS (use this for matching user references by category/type):
{chr(10).join(mapping_lines)}
IMPORTANT: When user says "schedule the X" where X is a category name (e.g., "storm door", "decking", "windows"),
find the project_id that has a matching category and return that project_id in entities.
"""

        # Format viewed_projects history for context awareness
        viewed_projects_str = ""
        if viewed_projects:
            viewed_lines = []
            for i, vp in enumerate(viewed_projects):
                viewed_lines.append(f"  {i+1}. #{vp.get('project_id')} - {vp.get('category', 'Unknown')} ({vp.get('status', 'Unknown')})")
            viewed_projects_str = f"""

RECENTLY VIEWED PROJECTS (projects the user has looked at in this session - most recent first):
{chr(10).join(viewed_lines)}
IMPORTANT: User can reference these by saying things like:
- "the Decking project" -> find project with matching category in this list
- "the first project I looked at" -> use the oldest viewed project
- "go back to the other project" -> use the previous project in this list
- "that project" or "it" -> use the most recently viewed project
"""

        workflow_context = f"""

Current workflow state:
- Type: {current_workflow_state.get('workflow_type', 'none')}
- Stage: {current_workflow_state.get('current_stage', 'start')}
- Context: {json.dumps(context, indent=2)}
- Summary: {current_workflow_state.get('conversation_summary', 'No summary')}
{project_mapping_str}{viewed_projects_str}"""

    prompt = f"""You are an intelligent orchestrator for a property management scheduling system.

Previous conversation:
{conversation_context}
{workflow_context}

User's current message: "{message}"

Analyze this message and provide a complete classification with ALL context extraction.

Available intents:
- scheduling: Anything related to appointments, projects, dates, times
- information: Weather queries or general info
- chitchat: Greetings, thanks, casual conversation

Available actions:
Scheduling: list_projects, get_project_details, get_available_dates, get_time_slots, confirm_appointment, reschedule_appointment, cancel_appointment, batch_schedule, defer_workflow, abandon_workflow, start_over
Information: get_weather, context_query
Chitchat: greet, general
Help: show_capabilities (when user asks "help", "what can you do", "options", "menu")

CONTEXT-BASED INFORMATION QUERIES (answer from conversation/project context):

Technician queries -> context_query with query_type: "technician"
Examples: "who is the technician", "who is coming", "who's doing the work", "technician name",
"who's the installer", "who will do the job", "tell me about the technician", "who's assigned to my project",
"what's the technician's name", "who is working on this", "installer info", "who will be coming out"

Category queries -> context_query with query_type: "category"
Examples: "what is the category", "what type of project is this", "what kind of project",
"what's the category for project X", "is this a kitchen project", "what category is project 123"

Appointment time queries -> context_query with query_type: "appointment_time"
Examples: "what time is my appointment", "when are they coming", "what's the scheduled time",
"when is the appointment", "what time should I expect them", "when will they arrive",
"appointment details", "when is the installation", "what day is my appointment", "scheduled date and time"

Address queries -> context_query with query_type: "address"
Examples: "what's the address", "where is the work being done", "installation address",
"where are they coming", "what address do you have", "job location", "where is the project"

Status/General queries -> context_query with query_type: "status"
Examples: "what's happening with my job", "status of my project", "what's going on with my project",

MULTI-FIELD QUERIES (user asks for multiple pieces of info at once):
When user asks for MULTIPLE pieces of information in a single query, use query_types (array) instead of query_type.
Examples:
- "give me technician name and appointment time for project X" -> query_types: ["technician", "appointment_time"]
- "what's the technician and scheduled date" -> query_types: ["technician", "appointment_time"]
- "tell me the address and status of the project" -> query_types: ["address", "status"]
- "who is coming and when" -> query_types: ["technician", "appointment_time"]
- "technician information and schedule start and end date" -> query_types: ["technician", "appointment_time"]

For these: Check if project details are in conversation history. Return intent=information, action=context_query
IMPORTANT: If user specifies a project reference (e.g., "for the 1st project", "for project 7751741", "for my Decking project"):
- Extract project_index (0-based) if ordinal: "1st project" -> project_index: 0, "2nd project" -> project_index: 1
- Extract project_id if specific ID mentioned
- Extract category if mentioned (e.g., "Decking project")
Example: "who is the technician for the 1st project" -> context_query with query_type: "technician", project_index: 0

WORKFLOW CONTROL:

defer_workflow - User wants to pause/wait/defer (NOT cancel):
Examples: "I will wait", "let me think about it", "not now", "maybe later", "I'll decide later",
"will do it later", "I'll get back to you", "give me some time", "hold on", "not right now",
"I need to think", "let me check my calendar", "I'll call back", "put it on hold", "I'm not ready yet", "can we do this later"
Return: intent=scheduling, action=defer_workflow

abandon_workflow - User explicitly cancels/stops:
Examples: "never mind", "cancel", "forget it", "stop", "don't bother", "skip it", "I changed my mind",
"cancel that", "no thanks", "I don't want to", "forget about it", "that's okay, nevermind", "actually no", "let's not"
Return: intent=scheduling, action=abandon_workflow

ACTION SELECTION GUIDE:
- "schedule project X" / "schedule the first project" / "book an appointment for X" -> get_available_dates (START scheduling workflow)
- "schedule the first two projects" / "schedule first 3 projects" / "schedule all projects" -> batch_schedule (MULTIPLE projects)
- "show project X" / "details for project X" / "what is project X" -> get_project_details (just show info, NOT scheduling)
- User selects a DATE from available dates -> get_time_slots
- User selects a TIME from time slots -> confirm_appointment
- "cancel this appointment" / "cancel my appointment" / "cancel this" / "cancel the booking" -> cancel_appointment (extract project_id from context)
- "reschedule this" / "reschedule my appointment" / "change the date" / "move the appointment" -> reschedule_appointment (extract project_id from context)

CRITICAL - DO NOT AUTO-ESCALATE TO SCHEDULING:
- NEVER automatically use get_available_dates just because a project has status "Ready To Schedule"
- get_available_dates ONLY when user EXPLICITLY says: "schedule", "book", "make appointment", "get dates", "find dates"
- If user says "just the X" or "only X" or "show me X" after a list -> This is FILTERING, not scheduling
- Example flow:
  - User: "what can I schedule?" -> list_projects (status=schedulable)
  - User: "just kitchen stuff" -> list_projects (category=Kitchen) - FILTER, not schedule
  - User: "just the dishwasher" -> list_projects (category=Dishwasher) OR get_project_details - FILTER/SHOW, not schedule
  - User: "schedule the dishwasher" -> get_available_dates - NOW user explicitly asked to schedule
- The words "just", "only", "show me", "the X one" = FILTER/SHOW, not SCHEDULE
- Do NOT assume user wants to schedule just because they narrowed down to one project

IMPORTANT RULES:
1. Extract ALL entities from the message AND conversation history
2. If user says "it", "that" (pronoun) - look back and find the MOST RECENTLY DISCUSSED project
3. CRITICAL - Handle ORDINAL references ("first", "last", "2nd", "3rd", etc.):
   - These refer to the ORIGINAL PROJECT LIST shown at start of conversation, NOT the most recently discussed project
   - "first project" -> return project_index: 0
   - "second project" / "2nd project" -> return project_index: 1
   - "third project" / "3rd project" -> return project_index: 2
   - "last project" -> return project_index: -1 (ALWAYS use -1, never extract project_id for "last")
   - NEVER extract project_id directly for ordinal references - ALWAYS use project_index
   - The system will resolve project_index to the actual project_id from the stored list
4. If user provides a date/time, extract it even if implicit (e.g., "tomorrow", "2pm")
5. If in an active workflow, determine what stage we're at
6. Be intelligent about corrections: "actually, make it the 28th" means update the date
7. For weather queries:
   - "weather for 1st project" / "weather for project 7751741" -> Extract location (city, state) from that project's address in conversation
   - "what's the weather" (no project specified) -> Use location from most recent project in conversation
   - Always return action: "get_weather" with entities.location as "City, ST" format (e.g., "Minneapolis, MN")
8. For list_projects with filters (POST-FILTERS - API doesn't filter, we do):
   - "scheduled projects" / "my scheduled jobs" -> entities.status = "scheduled" (matches Scheduled + Tentatively Scheduled)
   - "projects I can schedule" / "schedulable jobs" -> entities.status = "schedulable" (matches New + Ready To Schedule)
   - "kitchen projects" / "my kitchen jobs" -> entities.category = "kitchen" (bucket: Dishwasher, Ovens, Sink, etc.)
   - "new projects" -> entities.status = "New" (exact match)
   - "orders at 401 Chicago Avenue" / "projects at Main Street" -> entities.address = "401 Chicago Avenue" or "Main Street"
   - "how many jobs at Minneapolis" -> entities.address = "Minneapolis"
   - "projects assigned to John" / "jobs for technician Rajat" -> entities.technician_name = "John" or "Rajat"
   - "scheduled projects for installer Mike" -> entities.status = "scheduled", entities.technician_name = "Mike"
9. Handle batch/multiple project references:
   - "first two projects" -> extract project_ids for positions [0, 1] from conversation
   - "first 3 projects" -> extract project_ids for positions [0, 1, 2]
   - "all my projects" -> extract all project_ids from conversation
   - "projects 1 and 3" -> extract specific positions [0, 2]
   - Return entities.project_ids as ARRAY when multiple projects detected

10. CRITICAL - Project matching by LOCATION, CATEGORY, or TYPE:
   When user refers to a project by description (not ordinal like "first" or ID like "7751741"),
   you MUST search the conversation history and match using SEMANTIC/FUZZY matching:

   PRIORITY ORDER (most specific wins):
   1. ADDRESS/LOCATION match (highest priority) - street names, neighborhoods, areas, partial matches
   2. CATEGORY match - project type/category with synonyms and variations
   3. STATUS match - project status

   USE SEMANTIC MATCHING (not exact words):

   LOCATION variations - match ANY partial address component:
   - "north loop" / "the north" / "loop area" -> matches "123 North Loop Blvd"
   - "Chicago" / "Chicago place" / "on Chicago" -> matches "456 Chicago Avenue"
   - "downtown" / "city center" -> matches addresses in downtown area
   - "Main Street" / "main" / "the main one" -> matches "789 Main St"

   CATEGORY variations - match synonyms and related terms:
   - "windows" / "window" / "the window job" / "window replacement" -> category "Windows"
   - "deck" / "decking" / "deck project" / "the deck" -> category "Decking"
   - "siding" / "side" / "siding work" -> category "Siding"
   - "roof" / "roofing" / "roof job" / "the roof one" -> category "Roofing"
   - "door" / "doors" / "door replacement" -> category "Doors"
   - "gutter" / "gutters" / "gutter work" -> category "Gutters"

   STATUS variations:
   - "scheduled" / "the scheduled one" / "already scheduled" -> status "Scheduled"
   - "new" / "the new one" / "new project" -> status "New"
   - "pending" / "waiting" -> status "Pending"

   MATCHING RULES:
   - Use substring/partial matching for addresses (case-insensitive)
   - Use semantic similarity for categories (deck = decking, window = windows, etc.)
   - When user says "the X one" or "X project" or "X job" - X is the key identifier

   WHEN BOTH LOCATION AND CATEGORY ARE MENTIONED:
   - "deck project at north loop" -> Match by LOCATION first ("north loop"), verify category
   - Location is MORE SPECIFIC than category - prefer location match
   - If location matches but category doesn't, USE the location-matched project
   - Explain in reasoning: "Found project at North Loop - it's actually Windows, not Decking"

   AMBIGUITY HANDLING:
   - Multiple matches -> ask for clarification with the options
   - No matches -> return search criteria for error message
   - NEVER hallucinate project IDs - only use IDs from conversation history

   CRITICAL - EXPLICIT CATEGORY vs CONTEXT LOOKUPS:
   - When user EXPLICITLY names a category like "Washer Dryer", "Ovens", "Kitchen Sink", etc.:
     -> ALWAYS search for and return the project with THAT EXACT CATEGORY
     -> DO NOT assume it's the "recently discussed project" from context
     -> The user is asking about a DIFFERENT project, not the one being discussed
   - ONLY use "recently discussed project" when user uses PRONOUNS like:
     -> "this", "that", "it", "this one", "this project", "this appointment"
   - Example: User just discussed Kitchen Sink project, then says "details for Washer Dryer"
     -> This is asking about the Washer Dryer project, NOT the Kitchen Sink
     -> Search for project with category "Washer Dryer" and return THAT project ID

   SEARCH CONVERSATION HISTORY for project data containing:
   - Project IDs (7-digit numbers like 7751741)
   - Addresses (street names, cities, neighborhoods)
   - Categories (Windows, Decking, Siding, Roofing, etc.)
   - Status (Scheduled, New, In Progress, etc.)

Examples:

Scheduling:
{{
    "intent": "scheduling",
    "action": "get_time_slots",
    "entities": {{"project_id": "7751748", "date": "2025-11-27"}},
    "workflow_type": "schedule_appointment",
    "reasoning": "User selected Nov 27 from available dates."
}}

Ordinal reference to project (IMPORTANT: use project_index, not project_id):
{{
    "intent": "scheduling",
    "action": "get_project_details",
    "entities": {{"project_index": -1}},
    "reasoning": "User said 'details for the last project'. Using project_index: -1 to get the LAST project from the original list (not the most recently discussed one)."
}}

First project reference:
{{
    "intent": "scheduling",
    "action": "get_project_details",
    "entities": {{"project_index": 0}},
    "reasoning": "User said 'details for the first project'. Using project_index: 0 to get project at position 0 in the list."
}}

Second project reference:
{{
    "intent": "scheduling",
    "action": "get_project_details",
    "entities": {{"project_index": 1}},
    "reasoning": "User said 'show me the 2nd project'. Using project_index: 1 to get project at position 1 in the list."
}}

Weather (with context extraction):
{{
    "intent": "information",
    "action": "get_weather",
    "entities": {{"location": "Minneapolis, MN"}},
    "reasoning": "User asked about weather. Recent project details showed address in Minneapolis, MN."
}}

Weather for specific project (extract location from project):
{{
    "intent": "information",
    "action": "get_weather",
    "entities": {{"location": "Minneapolis, MN", "project_id": "7751741", "project_index": 0}},
    "reasoning": "User asked 'what is the weather for the 1st project'. Found 1st project (#7751741) has address in Minneapolis, MN. Will fetch weather for that location."
}}

Batch scheduling (multiple projects):
{{
    "intent": "scheduling",
    "action": "batch_schedule",
    "entities": {{"project_ids": ["7751741", "7751742"]}},
    "workflow_type": "batch_schedule_appointment",
    "reasoning": "User wants to schedule 'first two projects'. Looking at conversation, projects #7751741 and #7751742 are first and second in the list."
}}

Location-based project reference (PRIORITY: location over category):
{{
    "intent": "scheduling",
    "action": "get_available_dates",
    "entities": {{"project_id": "7751741"}},
    "workflow_type": "schedule_appointment",
    "reasoning": "User said 'the deck one at north'. Semantic match: 'north' matches project #7751741 at '123 North Loop Blvd'. User said 'deck' but project is actually Windows - using location match (more specific). Location takes priority."
}}

Category-based with synonym (deck = decking):
{{
    "intent": "scheduling",
    "action": "get_available_dates",
    "entities": {{"project_id": "7751748"}},
    "workflow_type": "schedule_appointment",
    "reasoning": "User said 'schedule the deck job'. Semantic match: 'deck' = 'Decking' category. Found project #7751748 with category 'Decking'."
}}

Date preference (schedule for next month/January/next week):
{{
    "intent": "scheduling",
    "action": "get_available_dates",
    "entities": {{"project_id": "7751748", "date": "next month"}},
    "workflow_type": "schedule_appointment",
    "reasoning": "User said 'schedule the deck for next month'. Include date preference so available dates start from January."
}}

Partial location match:
{{
    "intent": "scheduling",
    "action": "get_available_dates",
    "entities": {{"project_id": "7751741"}},
    "workflow_type": "schedule_appointment",
    "reasoning": "User said 'the one on Chicago'. Partial address match: 'Chicago' found in '456 Chicago Ave' for project #7751741."
}}

Informal reference with 'the X one' pattern:
{{
    "intent": "scheduling",
    "action": "get_available_dates",
    "entities": {{"project_id": "7751748"}},
    "workflow_type": "schedule_appointment",
    "reasoning": "User said 'the roof one'. Semantic match: 'roof' = 'Roofing' category. Found project #7751748 with category 'Roofing'."
}}

Status-based reference:
{{
    "intent": "scheduling",
    "action": "get_project_details",
    "entities": {{"project_id": "7751742"}},
    "reasoning": "User said 'the scheduled one'. Status match: Found project #7751742 with status 'Scheduled'."
}}

Ambiguous - multiple category matches:
{{
    "intent": "scheduling",
    "action": "clarify_project",
    "entities": {{"search_criteria": {{"category": "Windows"}}, "matching_projects": ["7751741", "7751743"]}},
    "reasoning": "User said 'the window job'. Found 2 Windows projects: #7751741 at North Loop and #7751743 at Main St. Need clarification."
}}

Context query (technician info):
{{
    "intent": "information",
    "action": "context_query",
    "entities": {{"query_type": "technician"}},
    "reasoning": "User asking about technician. Will extract from project data in conversation."
}}

Defer workflow (user wants to wait):
{{
    "intent": "scheduling",
    "action": "defer_workflow",
    "entities": {{}},
    "reasoning": "User said 'I will wait' - they want to pause the current scheduling workflow."
}}

Abandon workflow (user cancels):
{{
    "intent": "scheduling",
    "action": "abandon_workflow",
    "entities": {{}},
    "reasoning": "User said 'never mind' - they want to cancel the current scheduling process."
}}

Cancel appointment (cancel existing scheduled appointment):
{{
    "intent": "scheduling",
    "action": "cancel_appointment",
    "entities": {{"project_id": "7751742"}},
    "reasoning": "User said 'cancel this appointment'. Looking at conversation, user was just viewing project #7751742 which has a scheduled appointment. Extracting project_id from context."
}}

Reschedule appointment (reschedule existing scheduled appointment):
{{
    "intent": "scheduling",
    "action": "reschedule_appointment",
    "entities": {{"project_id": "7751742"}},
    "reasoning": "User said 'reschedule this'. Looking at conversation, user was viewing project #7751742. Extracting project_id from context to start reschedule flow."
}}

CRITICAL: For cancel_appointment and reschedule_appointment, ALWAYS extract project_id from the conversation context when user says "this", "this appointment", "this one", etc. Look for the most recently discussed project ID (format: #7751742 or Project 7751742 or id: 7751742).

Help/capabilities request:
{{
    "intent": "help",
    "action": "show_capabilities",
    "entities": {{}},
    "reasoning": "User asked 'help' or 'what can you do' - show capability list."
}}

Start over (reset conversation):
{{
    "intent": "scheduling",
    "action": "start_over",
    "entities": {{}},
    "reasoning": "User said 'start over' or 'restart' - clear all context and start fresh."
}}

List projects with technician filter:
{{
    "intent": "scheduling",
    "action": "list_projects",
    "entities": {{"status": "scheduled", "technician_name": "Rajat N"}},
    "reasoning": "User wants scheduled projects assigned to technician Rajat N. Apply both status and technician_name filters."
}}

Respond ONLY with valid JSON."""

    response_text = call_sonnet(prompt, max_tokens=800)

    try:
        # Parse JSON response with robust extraction (handles fenced JSON, leading text, etc.)
        classification = extract_first_json_object(response_text)
        logger.info(f"[SONNET] Sonnet classification: {classification}")
        return classification

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Sonnet response as JSON: {response_text}")
        # Heuristic fallback - use message content to guess intent instead of always chitchat
        fallback_intent = heuristic_intent_fallback(message)
        logger.info(f"[SONNET] Using heuristic fallback intent: {fallback_intent}")
        return {
            "intent": fallback_intent,
            "action": None,  # Let downstream handle action based on intent
            "entities": {},
            "workflow_type": None,
            "reasoning": f"JSON parse failed, heuristic fallback to {fallback_intent}"
        }


def intelligent_decide_next_action(
    message: str,
    classification: Dict[str, Any],
    workflow_state: Optional[Dict],
    conversation_history: List[Dict]
) -> Dict[str, Any]:
    """
    Use Sonnet 3.7 to intelligently decide what to do next

    Returns:
    {
        "should_call_lambda": true/false,
        "lambda_action": "get_time_slots",
        "lambda_params": {"project_id": "7751748", "date": "2025-11-27"},
        "response_to_user": "Here are available times...",
        "update_workflow_state": {...},
        "workflow_complete": false
    }
    """
    conversation_context = format_conversation_history(conversation_history)

    workflow_context = ""
    if workflow_state:
        context = workflow_state.get('context', {})
        project_mapping = context.get('project_mapping', {})

        # Format project_mapping for clear display
        project_mapping_str = ""
        if project_mapping:
            mapping_lines = []
            for pid, info in project_mapping.items():
                cat = info.get('category', 'Unknown')
                mapping_lines.append(f"  #{pid} -> {cat}")
            project_mapping_str = f"""

PROJECT MAPPING (use this to resolve category references to project_id):
{chr(10).join(mapping_lines)}"""

        workflow_context = f"""

Active workflow:
- Type: {workflow_state.get('workflow_type')}
- Stage: {workflow_state.get('current_stage')}
- Collected context: {json.dumps(context, indent=2)}
{project_mapping_str}"""

    prompt = f"""You are an intelligent workflow orchestrator. Decide what action to take next.

Previous conversation:
{conversation_context}
{workflow_context}

Classification result:
{json.dumps(classification, indent=2)}

User's message: "{message}"

Determine the next step:

1. Do we have everything needed to call a Lambda function?
   - For get_project_details: need project_id - IF user refers to project by category (e.g., "kitchen sink project"), use project_mapping from workflow context to find the matching project_id
   - For get_available_dates: need project_id (returns dates + request_id) - IF user refers to project by category, use project_mapping to resolve to project_id
     OPTIONAL: date - if user specifies a date preference, include it in lambda_params AS-IS (do NOT convert to YYYY-MM-DD):
       Examples: "next month", "January", "next week", "3rd week of January", "last week of February", "end of March"
       The Lambda function handles these expressions specially to calculate date ranges.
   - For get_time_slots: need project_id + date + request_id (request_id comes from get_available_dates)
   - For confirm_appointment: need project_id + date + time + request_id
   - For cancel_appointment: need project_id - extract from conversation context if user says "cancel this appointment" after viewing project details
   - For reschedule_appointment: need project_id - extract from conversation context if user says "reschedule this" after viewing project details
   - For list_projects: just need customer_id (already available)
     POST-FILTERS (applied after fetching - upstream API does NOT support filtering):
       - status: "schedulable" (New, Ready To Schedule), "scheduled" (Scheduled, Tentatively Scheduled), or exact status
       - category: bucket name ("Kitchen", "Windows", "Decking", "Bathroom", "Flooring") or exact category ("Storm Door", "Dishwasher")
       - projectType: "Call Back", "Installation", "Repair", "Measurement"
       - address: partial address match (e.g., "401 Chicago Avenue", "Main Street", "Minneapolis")
       - technician_name: filter by assigned technician/installer (e.g., "projects assigned to John", "Mildred's projects")
   - For get_weather: need location as "City, State" format (e.g., "Minneapolis, MN") - combine city and state from entities

IMPORTANT - POST-FILTERS vs API PARAMS:
The upstream ProjectForce API does NOT support filtering. When you specify status/category/projectType/address in lambda_params,
these are POST-FILTERS that the orchestrator applies AFTER fetching all projects. This is transparent to you - just include
the filters and the system will handle the post-filtering automatically.

CATEGORY-BASED PROJECT LOOKUP: When user refers to a project by category (e.g., "storm door project", "kitchen sink", "decking project"), check the project_mapping in workflow context to find the exact project_id that matches that category. Do NOT call list_projects if you already have project_mapping - just use it to resolve the project_id directly.

CRITICAL RULES - RESPECT THE CLASSIFICATION:

1. NEVER AUTO-SELECT DATES:
   When classification.action == "get_available_dates", you MUST call get_available_dates Lambda.
   DO NOT skip to get_time_slots even if there are available_dates in workflow context!
   User says "let's schedule it" -> ALWAYS call get_available_dates (NOT get_time_slots)
   Only call get_time_slots when user explicitly selects a date like "December 17" or "the 8th".

2. NEVER OVERRIDE get_project_details:
   When classification.action == "get_project_details", you MUST call get_project_details Lambda.
   DO NOT change it to get_available_dates or any scheduling action!
   Even if there's an active scheduling workflow, respect the user's explicit request for project details.
   User says "show details for X" -> ALWAYS call get_project_details.

3. GENERAL RULE - TRUST THE CLASSIFICATION:
   The classification already analyzed what the user wants. Your job is to EXECUTE that action, not re-interpret it.
   Only change the action when absolutely necessary (e.g., schedule_project -> get_available_dates because that's the first step).

2. If we can call Lambda:
   - Specify which action and what parameters
   - IMPORTANT: Only include parameters that have actual values - do NOT include parameters with None/null values
   - The Lambda will return data (dates, times, confirmation, etc.)

3. If we need more info from user:
   - What's missing?
   - How should we ask for it?

4. Should we update workflow state?
   - What stage are we at now?
   - What context should we save?
   - IMPORTANT: Always save category, city, state, and address from project details/list responses for future use (e.g., weather checks)

5. Is the workflow complete?
   - Set to true only after final confirmation

Respond with JSON only:
{{
    "should_call_lambda": true,
    "lambda_action": "get_time_slots",
    "lambda_params": {{
        "project_id": "7751748",
        "date": "2025-11-27",
        "request_id": "12345"  // IMPORTANT: Use request_id from workflow_state.context if available
    }},
    "format_response_as": "Show the time slots in a friendly list",
    "update_workflow_state": {{
        "workflow_type": "schedule_appointment",
        "current_stage": "awaiting_time_selection",
        "context": {{
            "project_id": "7751748",
            "date": "2025-11-27",
            "request_id": "12345",  // Keep request_id for subsequent calls
            "category": "Decking",  // IMPORTANT: Extract from project details for weather checks
            "city": "Minneapolis",  // IMPORTANT: Extract from address
            "state": "MN"  // IMPORTANT: Extract from address
        }},
        "conversation_summary": "User wants to schedule project 7751748 on Nov 27, now showing time slots"
    }},
    "workflow_complete": false
}}

OR if we need more info:
{{
    "should_call_lambda": false,
    "response_to_user": "Which time works best for you?",
    "missing_info": ["time"],
    "update_workflow_state": {{...}},
    "workflow_complete": false
}}

EXAMPLE FOR DATE PREFERENCE (schedule for next month/January/3rd week of January):
When user says "schedule this for next month", "schedule for January", or "show me 3rd week of January":
CRITICAL: Pass the date expression AS-IS - do NOT convert to YYYY-MM-DD!

User says "show me 3rd week of January":
{{
    "should_call_lambda": true,
    "lambda_action": "get_available_dates",
    "lambda_params": {{
        "project_id": "7751748",
        "date": "3rd week of January"  // PASS AS-IS - Lambda calculates the date range
    }},
    "update_workflow_state": {{
        "workflow_type": "schedule_appointment",
        "current_stage": "awaiting_date_selection",
        "context": {{"project_id": "7751748", "date_preference": "3rd week of January"}}
    }},
    "workflow_complete": false
}}

User says "schedule this for next month":
{{
    "should_call_lambda": true,
    "lambda_action": "get_available_dates",
    "lambda_params": {{
        "project_id": "7751748",
        "date": "next month"  // PASS AS-IS - Lambda calculates the date range
    }},
    "update_workflow_state": {{
        "workflow_type": "schedule_appointment",
        "current_stage": "awaiting_date_selection",
        "context": {{"project_id": "7751748", "date_preference": "next month"}}
    }},
    "workflow_complete": false
}}

User says "show me dates between 9th Jan and 18th Jan" (DATE RANGE):
{{
    "should_call_lambda": true,
    "lambda_action": "get_available_dates",
    "lambda_params": {{
        "project_id": "7751748",
        "date": "between 9th Jan and 18th Jan"  // PASS AS-IS - Lambda extracts start/end dates
    }},
    "update_workflow_state": {{
        "workflow_type": "schedule_appointment",
        "current_stage": "awaiting_date_selection",
        "context": {{"project_id": "7751748", "date_preference": "between 9th Jan and 18th Jan"}}
    }},
    "workflow_complete": false
}}

CRITICAL EXAMPLE FOR DATE SELECTION (after showing available dates):

When user says "08th Dec", "December 8", "the 8th", "next Monday", etc. (AFTER seeing available dates for a project):
This is DATE SELECTION to get time slots - NOT a new scheduling request!

User says "08th Dec" (after seeing available dates for project #7751741 with request_id 12345):
{{
    "should_call_lambda": true,
    "lambda_action": "get_time_slots",
    "lambda_params": {{
        "project_id": "7751741",
        "date": "2025-12-08",
        "request_id": "12345"
    }},
    "update_workflow_state": {{
        "workflow_type": "schedule_appointment",
        "current_stage": "awaiting_time_selection",
        "context": {{
            "project_id": "7751741",
            "date": "2025-12-08",
            "request_id": "12345"
        }}
    }},
    "workflow_complete": false
}}

User says "December 15th" or "15th" (after seeing available dates for project #7751742):
{{
    "should_call_lambda": true,
    "lambda_action": "get_time_slots",
    "lambda_params": {{
        "project_id": "7751742",
        "date": "2025-12-15",
        "request_id": "67890"
    }},
    "update_workflow_state": {{
        "workflow_type": "schedule_appointment",
        "current_stage": "awaiting_time_selection",
        "context": {{
            "project_id": "7751742",
            "date": "2025-12-15",
            "request_id": "67890"
        }}
    }},
    "workflow_complete": false
}}

IMPORTANT DATE SELECTION RULES:
1. When user provides JUST a date after available dates were shown, call get_time_slots (NOT get_available_dates)
2. Use the project_id and request_id from the CURRENT workflow context (most recently shown project)
3. Convert SPECIFIC dates to YYYY-MM-DD (e.g., "08th Dec" -> "2025-12-08", "December 15" -> "2025-12-15")
   CRITICAL EXCEPTION - Keep these expressions AS-IS (do NOT convert to YYYY-MM-DD):
   - "next week", "this week", "next month", "this month" -> pass as-is
   - "1st week of [month]", "2nd week of [month]", "3rd week of [month]", "4th week of [month]" -> pass as-is
   - "first week of [month]", "second week of [month]", "third week of [month]", "fourth week of [month]" -> pass as-is
   - "last week of [month]", "end of [month]" -> pass as-is
   - Month names alone ("January", "February") -> pass as-is
   These expressions are handled specially by the Lambda function.
4. Do NOT start a new scheduling flow - CONTINUE the existing one!
5. If "08" could be date or project, and user just saw available dates, it's a DATE selection
6. The workflow context contains the project_id and request_id you need - use them!

EXAMPLES FOR LIST_PROJECTS:

User says "list my projects" (NO status filter):
{{
    "should_call_lambda": true,
    "lambda_action": "list_projects",
    "lambda_params": {{}}  // NO status parameter - return ALL projects
}}

User says "list my scheduled projects" (WITH status filter):
{{
    "should_call_lambda": true,
    "lambda_action": "list_projects",
    "lambda_params": {{
        "status": "Scheduled"  // Include status ONLY when user specifies it
    }}
}}

User says "how many orders at 401 Chicago Avenue" (WITH address filter):
{{
    "should_call_lambda": true,
    "lambda_action": "list_projects",
    "lambda_params": {{
        "address": "401 Chicago Avenue"  // Filter by address when user specifies location
    }}
}}

User says "show me projects scheduled for January" (WITH scheduled_month filter):
{{
    "should_call_lambda": true,
    "lambda_action": "list_projects",
    "lambda_params": {{
        "status": "Scheduled",
        "scheduled_month": "January"  // Filter by appointment month
    }}
}}

User says "what appointments do I have in February" (WITH scheduled_month filter):
{{
    "should_call_lambda": true,
    "lambda_action": "list_projects",
    "lambda_params": {{
        "status": "Scheduled",
        "scheduled_month": "February"  // Filter by appointment month
    }}
}}

User asks "what is the weather like" (after viewing project in Minneapolis):
{{
    "should_call_lambda": true,
    "lambda_action": "get_weather",
    "lambda_params": {{
        "location": "Minneapolis, MN"  // Combine city and state - do NOT pass city/state/address/zipcode separately
    }}
}}

EXAMPLES FOR CANCEL/RESCHEDULE:

User says "cancel this appointment" (after viewing project #7751742 details):
{{
    "should_call_lambda": true,
    "lambda_action": "cancel_appointment",
    "lambda_params": {{
        "project_id": "7751742"  // Extract from conversation context - the most recently discussed project
    }}
}}

User says "reschedule this" (after viewing project #7751742 details):
{{
    "should_call_lambda": true,
    "lambda_action": "reschedule_appointment",
    "lambda_params": {{
        "project_id": "7751742"  // Extract from conversation context - the most recently discussed project
    }}
}}

IMPORTANT FOR CONTEXT RESOLUTION:
- When user refers to "this appointment", "this project", "this one", etc., extract the project_id from the MOST RECENT project mentioned or displayed in the conversation history.
- Look for project IDs in formats: #7751742, Project 7751742, "id": "7751742"
- If multiple projects were shown in a list and user says "the second one" or "2nd project", use that position from the list.

Respond ONLY with valid JSON."""

    response_text = call_sonnet(prompt, max_tokens=1000)

    try:
        # Parse JSON response with robust extraction (handles fenced JSON, leading text, etc.)
        decision = extract_first_json_object(response_text)
        logger.info(f"[DECISION] Sonnet decision: call_lambda={decision.get('should_call_lambda')}, action={decision.get('lambda_action')}")
        return decision

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Sonnet decision: {response_text}")
        # Heuristic fallback based on classification
        fallback_intent = classification.get('intent', 'scheduling') if classification else 'scheduling'
        logger.info(f"[DECISION] Using fallback with intent: {fallback_intent}")
        return {
            "should_call_lambda": fallback_intent == 'scheduling',  # Try Lambda for scheduling
            "lambda_action": "list_projects" if fallback_intent == 'scheduling' else None,
            "lambda_params": {},
            "response_to_user": "I'm having trouble understanding. Could you rephrase that?",
            "workflow_complete": False
        }


def orchestrate_intelligent_workflow(
    message: str,
    session_id: str,
    customer_id: str,
    client_id: str,
    pf_bearer_token: str,
    conversation_history: List[Dict],
    channel: str = 'chat',  # 'chat' or 'voice' - for channel-specific handling
    from_phone: str = '',  # For voice cache lookup
    project_id: str = '',  # From GPT-4o smart prompt embedded state (voice)
    project_status: str = '',  # From GPT-4o smart prompt embedded state (voice)
    confirmed: bool = False,  # From GPT-4o: True when user confirms appointment (Step 2)
    gpt_action: str = '',  # CRITICAL: Action from GPT-4o - TRUST THIS unless empty!
    gpt_date: str = '',  # From GPT-4o: selected date in YYYY-MM-DD format
    gpt_time: str = ''  # From GPT-4o: selected time in HH:MM format
) -> Dict[str, Any]:
    """
    Main intelligent orchestration function

    IMPORTANT: When GPT-4o provides gpt_action, we TRUST IT and execute directly.
    GPT-4o has full context via the smart system prompt (all projects, statuses, etc.)
    and knows exactly what action the user wants. Don't second-guess it.

    Args:
        message: User's message
        session_id: Session ID
        customer_id: Customer ID
        client_id: Client ID
        pf_bearer_token: ProjectForce API token
        conversation_history: Previous messages
        channel: 'chat' or 'voice'
        from_phone: Caller phone number for voice cache lookup
        project_id: Optional project_id from GPT-4o smart prompt (voice fast path)
        project_status: Optional project_status from GPT-4o smart prompt (voice fast path)
        confirmed: True when GPT-4o indicates user confirmed appointment (Step 2 of two-step booking)
        gpt_action: Action specified by GPT-4o - TRUST THIS when provided!
        gpt_date: Selected date from GPT-4o in YYYY-MM-DD format
        gpt_time: Selected time from GPT-4o in HH:MM format

    Returns:
        Response dictionary with text, intent, action, timing
    """
    timing = {}
    start_time = time.time()
    pf_http_status_code = 200  # Default PF API status code

    state_manager = get_state_manager()

    # Load current workflow state (if any)
    workflow_state = state_manager.get_state(session_id)

    # ========================================================================
    # SMART PROMPT PROJECT_ID FALLBACK (Voice only)
    # GPT-4o may pass project_id from embedded state in the smart system prompt
    # Use it as a fallback when workflow state doesn't have project context
    # ========================================================================
    if project_id and channel == 'voice':
        logger.info(f"[SMART-PROMPT] project_id passed from GPT-4o: {project_id}, status: {project_status}")
        # If workflow state exists but lacks project_id in context, inject it
        context = workflow_state.get('context', {}) if workflow_state else {}
        if workflow_state and not context.get('project_id'):
            logger.info(f"[SMART-PROMPT] Injecting project_id into workflow context as fallback")
            if 'context' not in workflow_state:
                workflow_state['context'] = {}
            workflow_state['context']['project_id'] = project_id
            if project_status:
                workflow_state['context']['project_status'] = project_status
            # Also add to project_ids list if not present
            project_ids = workflow_state['context'].get('project_ids', [])
            if project_id not in project_ids:
                workflow_state['context']['project_ids'] = [project_id] + project_ids
            state_manager.save_state(session_id, workflow_state)
            logger.info(f"[SMART-PROMPT] Workflow state updated with smart prompt project_id")
        elif not workflow_state:
            # No workflow state at all - create minimal state with project_id and status
            logger.info(f"[SMART-PROMPT] No workflow state - creating minimal state with project_id and status")
            workflow_state = {
                'workflow_type': 'smart_prompt_context',
                'current_stage': 'initial',
                'context': {
                    'project_id': project_id,
                    'project_ids': [project_id],
                    'project_status': project_status  # Store status for continuation handler
                }
            }
            state_manager.save_state(session_id, workflow_state)

    # ========================================================================
    # GPT-4O TRUST FAST PATH (Voice)
    # When GPT-4o provides both action AND project_id, TRUST IT and execute directly!
    # GPT-4o has full context via smart prompt and knows exactly what the user wants.
    # Don't second-guess with NLU/Sonnet - just execute the action.
    # ========================================================================
    valid_gpt_actions = [
        'get_available_dates', 'get_time_slots', 'confirm_appointment',
        'reschedule_appointment', 'cancel_appointment', 'get_project_details',
        'list_projects'  # Even list_projects can be trusted if GPT-4o says so
    ]

    if channel == 'voice' and gpt_action and gpt_action in valid_gpt_actions:
        logger.info(f"[GPT-4O-TRUST] GPT-4o specified action='{gpt_action}', project_id='{project_id}', date='{gpt_date}', time='{gpt_time}' - TRUSTING IT!")

        # For actions that require project_id, check we have it
        project_required_actions = ['get_available_dates', 'get_time_slots', 'confirm_appointment', 'reschedule_appointment', 'cancel_appointment', 'get_project_details']

        # If GPT-4O didn't provide project_id, get it from workflow state context
        if not project_id and workflow_state:
            context_project_id = workflow_state.get('context', {}).get('project_id')
            if context_project_id:
                project_id = str(context_project_id)
                logger.info(f"[GPT-4O-TRUST] Using project_id from workflow state: {project_id}")

        if gpt_action in project_required_actions and project_id:
            logger.info(f"[GPT-4O-TRUST] Executing {gpt_action} directly with project_id={project_id}")

            # Build params for Lambda call
            gpt_params = {
                'project_id': project_id,
                'customer_id': customer_id,
                'client_id': client_id,
                'pf_bearer_token': pf_bearer_token,
                'from_phone': from_phone
            }

            # Define message_lower early so it's available for all action types
            message_lower = message.lower() if message else ''

            # CRITICAL: Pass message to reschedule_appointment for smart intent detection
            # This allows auto-confirm when user says "reschedule" (skips redundant confirmation)
            if gpt_action == 'reschedule_appointment' and message:
                gpt_params['message'] = message
                logger.info(f"[GPT-4O-TRUST] Passing message to reschedule_appointment for smart intent")

            # CRITICAL: For get_available_dates, check if this is a reschedule scenario
            # Use rescheduler API when: user said "reschedule", or GPT action is reschedule, or project is already scheduled
            if gpt_action == 'get_available_dates':
                reschedule_keywords = ['reschedule', 'change date', 'different date', 'move appointment', 'change appointment']
                is_reschedule_context = any(kw in message_lower for kw in reschedule_keywords)

                # Also check if workflow indicates reschedule
                workflow_context = workflow_state.get('context', {}) if workflow_state else {}
                workflow_is_reschedule = workflow_context.get('is_reschedule', False)
                workflow_type = workflow_state.get('workflow_type', '') if workflow_state else ''

                # Check conversation history - if last assistant message mentioned reschedule and user confirmed
                history_indicates_reschedule = False
                if conversation_history and len(conversation_history) >= 1:
                    # Check if user is confirming ("yes", "yeah", "ok") after reschedule was mentioned
                    confirm_words = ['yes', 'yeah', 'yep', 'ok', 'okay', 'sure', 'please', 'go ahead']
                    is_confirmation = any(w in message_lower.split() for w in confirm_words) and len(message_lower.split()) <= 5
                    if is_confirmation:
                        # Check last assistant message for reschedule mention
                        last_messages = conversation_history[-2:] if len(conversation_history) >= 2 else conversation_history
                        for msg in last_messages:
                            if msg.get('role') == 'assistant':
                                assistant_text = (msg.get('content', '') or msg.get('message', '')).lower()
                                if 'reschedule' in assistant_text or 'already scheduled' in assistant_text:
                                    history_indicates_reschedule = True
                                    logger.info(f"[GPT-4O-TRUST] History indicates reschedule - user confirmed after reschedule prompt")
                                    break

                if is_reschedule_context or workflow_is_reschedule or workflow_type == 'reschedule_appointment' or history_indicates_reschedule:
                    gpt_params['is_reschedule'] = True
                    logger.info(f"[GPT-4O-TRUST] Setting is_reschedule=True (keywords={is_reschedule_context}, workflow={workflow_is_reschedule}, type={workflow_type}, history={history_indicates_reschedule})")

            # Add date from GPT-4o if provided
            if gpt_date:
                gpt_params['date'] = gpt_date
                logger.info(f"[GPT-4O-TRUST] Using date from GPT-4o: {gpt_date}")
            elif gpt_action == 'get_available_dates':
                # Fallback: try to extract date from message
                extracted_date = extract_date_from_message(message)
                if extracted_date:
                    gpt_params['date'] = extracted_date
                    logger.info(f"[GPT-4O-TRUST] Extracted date from message: {extracted_date}")

            # Add time from GPT-4o if provided
            if gpt_time:
                gpt_params['time'] = gpt_time
                logger.info(f"[GPT-4O-TRUST] Using time from GPT-4o: {gpt_time}")

            # For confirm_appointment or reschedule_appointment, include confirmed flag
            # Also detect if user is saying "yes" to a reschedule prompt
            if gpt_action in ['confirm_appointment', 'reschedule_appointment']:
                # Check if confirmed flag is already True (from handler)
                if confirmed:
                    gpt_params['confirmed'] = True
                    logger.info(f"[GPT-4O-TRUST] Including confirmed=True for {gpt_action} (from handler)")
                # Or detect affirmative response in message
                elif message_lower:
                    affirm_words = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'please', 'go ahead', 'do it', 'proceed']
                    is_affirmative = any(word in message_lower.split() for word in affirm_words) and len(message_lower.split()) <= 5
                    if is_affirmative:
                        gpt_params['confirmed'] = True
                        logger.info(f"[GPT-4O-TRUST] Including confirmed=True for {gpt_action} (detected affirmative: '{message}')")

            # Get request_id from workflow state if available
            if workflow_state and workflow_state.get('context', {}).get('request_id'):
                gpt_params['request_id'] = workflow_state['context']['request_id']
                logger.info(f"[GPT-4O-TRUST] Using request_id from workflow state: {gpt_params['request_id']}")

            try:
                lambda_response = call_lambda_directly(gpt_action, gpt_params)

                # Extract response
                response_data = lambda_response.get('response', {})
                function_response = response_data.get('functionResponse', {})
                response_body_wrapper = function_response.get('responseBody', {})
                text_wrapper = response_body_wrapper.get('TEXT', {})
                response_body_str = text_wrapper.get('body', '{}')

                if isinstance(response_body_str, str):
                    response_body = json.loads(response_body_str)
                else:
                    response_body = response_body_str

                # Check for errors
                if response_body.get('error'):
                    error_msg = response_body.get('error', 'Unknown error')
                    logger.warning(f"[GPT-4O-TRUST] Lambda returned error: {error_msg}")
                    # Fall through to normal processing on error
                else:
                    # Success! Format response for voice
                    response_text = response_body.get('message', '')
                    if not response_text:
                        # Simple inline formatting for voice
                        if gpt_action == 'get_available_dates':
                            # CRITICAL: Check already_scheduled FIRST - project may be scheduled, not "no dates"
                            if response_body.get('already_scheduled'):
                                response_text = "This project already has an appointment. Say 'reschedule' if you'd like to change it, or 'details' to hear the appointment info."
                            else:
                                dates = response_body.get('available_dates', [])
                                if dates:
                                    date_list = ', '.join(d.get('date', str(d)) if isinstance(d, dict) else str(d) for d in dates[:3])
                                    response_text = f"I have these dates available: {date_list}. Which one works for you?"
                                else:
                                    response_text = "I don't see any available dates right now. Would you like to try a different week?"
                        elif gpt_action == 'get_time_slots':
                            # scheduling-actions returns: available_slots, timeSlots, slots (rescheduler), or time_slots
                            slots = response_body.get('available_slots') or response_body.get('timeSlots') or response_body.get('slots') or response_body.get('time_slots', [])
                            logger.info(f"[GPT-4O-TRUST] Time slots response keys: {list(response_body.keys())}, slots found: {len(slots) if slots else 0}")
                            if slots:
                                # Format time slots nicely for voice (convert 08:00:00 to 8 AM)
                                def format_time_voice(t):
                                    try:
                                        if isinstance(t, str) and ':' in t:
                                            h, m = int(t.split(':')[0]), int(t.split(':')[1])
                                            suffix = 'AM' if h < 12 else 'PM'
                                            h = h if h <= 12 else h - 12
                                            h = 12 if h == 0 else h
                                            return f"{h} {suffix}" if m == 0 else f"{h}:{m:02d} {suffix}"
                                        return str(t)
                                    except:
                                        return str(t)
                                slot_list = ', '.join(format_time_voice(s) for s in slots[:4])
                                response_text = f"I have these times available: {slot_list}. Which works best for you?"
                            else:
                                response_text = "No time slots available for that date. Would you like to try a different day?"
                        elif gpt_action == 'get_project_details':
                            response_text = response_body.get('summary', "Here are your project details.")
                        elif gpt_action == 'reschedule_appointment':
                            status = response_body.get('status', '')
                            if status == 'awaiting_confirmation':
                                # Step 1: Ask for confirmation
                                response_text = response_body.get('message', "Would you like to reschedule this appointment?")
                            elif status == 'awaiting_date_selection':
                                # Step 2: Show available dates after cancel
                                dates = response_body.get('available_dates', [])
                                if dates:
                                    date_list = ', '.join(d.get('date', str(d)) if isinstance(d, dict) else str(d) for d in dates[:5])
                                    response_text = f"Great, I've cancelled your current appointment. Here are the available dates: {date_list}. Which one works for you?"
                                else:
                                    response_text = response_body.get('message', "I've cancelled your appointment but couldn't find available dates.")
                            elif status == 'rescheduled':
                                response_text = response_body.get('message', "Your appointment has been rescheduled!")
                            elif status == 'no_dates_available':
                                response_text = response_body.get('message', "No alternative dates available. Your current appointment remains unchanged.")
                            else:
                                response_text = response_body.get('message', '')

                    # Update workflow state based on action
                    if gpt_action == 'get_available_dates':
                        new_state = {
                            'workflow_type': 'schedule_appointment',
                            'current_stage': 'awaiting_date_selection',
                            'context': {
                                'project_id': project_id,
                                'project_status': project_status,
                                'available_dates': response_body.get('available_dates', []),
                                'request_id': response_body.get('request_id')
                            }
                        }
                        state_manager.save_state(session_id, new_state)
                        logger.info(f"[GPT-4O-TRUST] Saved workflow state: awaiting_date_selection")

                    elif gpt_action == 'get_time_slots':
                        # Get slots using correct field names from scheduling-actions (includes rescheduler's 'slots')
                        slots_for_state = response_body.get('available_slots') or response_body.get('timeSlots') or response_body.get('slots') or response_body.get('time_slots', [])
                        new_state = {
                            'workflow_type': 'schedule_appointment',
                            'current_stage': 'awaiting_time_selection',
                            'context': {
                                'project_id': project_id,
                                'project_status': project_status,
                                'date': gpt_params.get('date'),
                                'time_slots': slots_for_state,
                                'request_id': response_body.get('request_id')
                            }
                        }
                        state_manager.save_state(session_id, new_state)
                        logger.info(f"[GPT-4O-TRUST] Saved workflow state: awaiting_time_selection")

                    elif gpt_action == 'reschedule_appointment':
                        status = response_body.get('status', '')
                        if status == 'awaiting_date_selection':
                            new_state = {
                                'workflow_type': 'reschedule_appointment',
                                'current_stage': 'awaiting_date_selection',
                                'context': {
                                    'project_id': project_id,
                                    'project_status': project_status,
                                    'available_dates': response_body.get('available_dates', []),
                                    'request_id': response_body.get('request_id'),
                                    'is_reschedule': True
                                }
                            }
                            state_manager.save_state(session_id, new_state)
                            logger.info(f"[GPT-4O-TRUST] Saved workflow state: reschedule awaiting_date_selection")

                    timing['total'] = time.time() - start_time
                    logger.info(f"[GPT-4O-TRUST] SUCCESS! Returning response directly (bypassed classification)")
                    return {
                        'response': response_text,
                        'intent': 'scheduling',
                        'action': gpt_action,
                        'agent_name': 'Intelligent Orchestrator (GPT-4o Trust)',
                        'direct_call': True,
                        'timing': timing,
                        'pf_http_status_code': response_body.get('pf_http_status_code', 200)
                    }

            except Exception as e:
                logger.error(f"[GPT-4O-TRUST] Error executing {gpt_action}: {e}", exc_info=True)
                # Fall through to normal processing on error

        elif gpt_action == 'list_projects':
            # For list_projects, we can execute without project_id
            logger.info(f"[GPT-4O-TRUST] Executing list_projects (no project_id required)")
            # Fall through to normal processing - list_projects has complex filtering logic

    # ========================================================================
    # GPT-4O CONFIRMED FLAG HANDLER (Voice Step 2)
    # When GPT-4o passes confirmed=True, finalize the appointment booking
    # This handles the two-step confirmation flow for voice
    # ========================================================================
    if confirmed and channel == 'voice':
        logger.info(f"[VOICE-CONFIRM] GPT-4o passed confirmed=True - finalizing appointment")

        # Check if we're in awaiting_appointment_confirm stage
        current_stage = workflow_state.get('current_stage', '') if workflow_state else ''
        context = workflow_state.get('context', {}) if workflow_state else {}

        if current_stage == 'awaiting_appointment_confirm' or context.get('project_id'):
            # Get booking details from workflow context
            booking_project_id = context.get('project_id') or project_id
            booking_date = context.get('date')
            booking_time = context.get('time')
            booking_request_id = context.get('request_id')

            if booking_project_id and booking_date and booking_time and booking_request_id:
                logger.info(f"[VOICE-CONFIRM] Executing Step 2: project={booking_project_id}, date={booking_date}, time={booking_time}")

                try:
                    confirm_params = {
                        'project_id': booking_project_id,
                        'date': booking_date,
                        'time': booking_time,
                        'request_id': booking_request_id,
                        'customer_id': customer_id,
                        'client_id': client_id,
                        'pf_bearer_token': pf_bearer_token,
                        'from_phone': from_phone,
                        'confirmed': True  # CRITICAL: Step 2 - actually book the appointment
                    }

                    lambda_response = call_lambda_directly('confirm_appointment', confirm_params)
                    logger.info(f"[VOICE-CONFIRM] Lambda response received")

                    # Extract response
                    response_data = lambda_response.get('response', {})
                    function_response = response_data.get('functionResponse', {})
                    response_body_wrapper = function_response.get('responseBody', {})
                    text_wrapper = response_body_wrapper.get('TEXT', {})
                    response_body_str = text_wrapper.get('body', '{}')

                    if isinstance(response_body_str, str):
                        response_body = json.loads(response_body_str)
                    else:
                        response_body = response_body_str

                    if response_body.get('error'):
                        error_msg = response_body.get('error', 'Unknown error')
                        logger.error(f"[VOICE-CONFIRM] Booking failed: {error_msg}")
                        response_text = f"I'm sorry, I couldn't complete the booking. {error_msg}"
                    else:
                        # Success! Appointment booked
                        logger.info(f"[VOICE-CONFIRM] Appointment booked successfully!")
                        response_text = response_body.get('message', f"Your appointment is confirmed for {booking_date} at {booking_time}.")

                        # Clear workflow state
                        state_manager.reset_workflow_state(session_id)

                    timing['total'] = time.time() - start_time
                    return {
                        'response': response_text,
                        'intent': 'scheduling',
                        'action': 'confirm_appointment',
                        'agent_name': 'Intelligent Orchestrator (Voice Confirm Step 2)',
                        'direct_call': True,
                        'timing': timing,
                        'pf_http_status_code': response_body.get('pf_http_status_code', 200)
                    }

                except Exception as e:
                    logger.error(f"[VOICE-CONFIRM] Error in Step 2 booking: {e}", exc_info=True)
                    timing['total'] = time.time() - start_time
                    return {
                        'response': "I'm sorry, I had trouble completing that booking. Please try again.",
                        'intent': 'scheduling',
                        'action': 'confirm_appointment',
                        'agent_name': 'Intelligent Orchestrator (Voice Confirm Error)',
                        'direct_call': True,
                        'timing': timing
                    }
            else:
                logger.warning(f"[VOICE-CONFIRM] Missing booking details: project_id={booking_project_id}, date={booking_date}, time={booking_time}, request_id={booking_request_id}")

    # ========================================================================
    # PENDING CONFIRMATION HANDLER (Chat/SMS only)
    # Handle confirm/decline for pending scheduling actions
    # ========================================================================
    # Check for pending_action in context (where it's actually stored)
    context = workflow_state.get('context', {}) if workflow_state else {}
    pending_action_data = context.get('pending_action')
    logger.info(f"[CONFIRM-CHECK] pending_action in context: {pending_action_data is not None}, channel: {channel}")
    # pending_action_data can be a dict (from confirm flow) or string (from vague_prompts like "schedule a project")
    # Only process as confirmation if it's a dict with 'action' key
    # NOTE: Voice channel now included - GPT-4o will pass "yes"/"confirm" which we handle here
    if workflow_state and pending_action_data and isinstance(pending_action_data, dict):
        pending = pending_action_data
        pending_action = pending.get('action')
        message_lower = message.lower().strip()

        # Check for confirmation
        confirm_patterns = ['confirm', 'yes', 'ok', 'okay', 'sure', 'go ahead', 'book it', 'schedule it', 'do it', 'proceed']
        decline_patterns = ['decline', 'no', 'cancel', 'never mind', 'nevermind', 'back', 'different', 'change']

        is_confirm = any(p in message_lower for p in confirm_patterns)
        is_decline = any(p in message_lower for p in decline_patterns)

        if is_confirm and pending_action == 'confirm_appointment':
            logger.info(f"[CONFIRM] User confirmed pending appointment - executing schedule")
            # Clear pending and execute the actual scheduling
            pending_params = pending.get('params', {})
            pending_params['customer_id'] = customer_id
            pending_params['client_id'] = client_id
            pending_params['pf_bearer_token'] = pf_bearer_token
            pending_params['confirmed'] = True  # CRITICAL: Tell Lambda to actually book the appointment

            try:
                lambda_response = call_lambda_directly('confirm_appointment', pending_params)

                # Extract response
                response_data = lambda_response.get('response', {})
                function_response = response_data.get('functionResponse', {})
                response_body_wrapper = function_response.get('responseBody', {})
                text_wrapper = response_body_wrapper.get('TEXT', {})
                response_body_str = text_wrapper.get('body', '{}')

                if isinstance(response_body_str, str):
                    response_body = json.loads(response_body_str)
                else:
                    response_body = response_body_str

                # CHECK FOR ERRORS in Lambda response
                if response_body.get('error'):
                    error_msg = response_body.get('error', 'Unknown error')
                    logger.error(f"[CONFIRM] Lambda returned error: {error_msg}")

                    # Parse error message for user-friendly response
                    if 'No technician found' in error_msg:
                        user_error = "Sorry, no technician is available for that time slot. Please select a different time."
                    elif 'already booked' in error_msg or 'conflict' in error_msg.lower():
                        # ================================================================
                        # ENHANCED UX: Fetch available slots when requested slot is booked
                        # Instead of just "select a different time", show what's available
                        # ================================================================
                        user_error = "That time slot was just booked."
                        try:
                            # Get context for re-fetching slots
                            ctx = workflow_state.get('context', {}) if workflow_state else {}
                            slot_project_id = ctx.get('project_id') or pending.get('preview', {}).get('project_id')
                            slot_date = ctx.get('date') or pending.get('preview', {}).get('date_raw')

                            if slot_project_id and slot_date:
                                logger.info(f"[BOOKED-RETRY] Fetching fresh slots for project {slot_project_id} on {slot_date}")
                                slot_params = {
                                    'project_id': slot_project_id,
                                    'date': slot_date,
                                    'client_id': client_id,
                                    'customer_id': customer_id,
                                    'pf_bearer_token': pf_bearer_token
                                }
                                slot_response = call_lambda_directly('get_time_slots', slot_params)
                                slot_data = slot_response.get('response', {}).get('functionResponse', {}).get('responseBody', {}).get('TEXT', {}).get('body', '{}')
                                if isinstance(slot_data, str):
                                    slot_body = json.loads(slot_data)
                                else:
                                    slot_body = slot_data
                                fresh_slots = slot_body.get('time_slots', [])

                                if fresh_slots:
                                    # Format available slots for voice
                                    if channel == 'voice':
                                        slot_list = ', '.join(fresh_slots[:4])
                                        user_error = f"That time slot was just booked. But I found these other times available: {slot_list}. Which one works for you?"
                                    else:
                                        slot_list = ', '.join(fresh_slots[:5])
                                        user_error = f"That time slot was just booked. Here are the available times: {slot_list}. Which would you prefer?"
                                    logger.info(f"[BOOKED-RETRY] Found {len(fresh_slots)} alternative slots")
                                else:
                                    user_error = "That time slot was just booked and there are no other slots available for this date. Would you like to try a different date?"
                        except Exception as retry_err:
                            logger.warning(f"[BOOKED-RETRY] Failed to fetch fresh slots: {retry_err}")
                            user_error = "That time slot was just booked. Please select a different time."
                    elif 'SESSION_EXPIRED' in error_msg or '401' in error_msg or '403' in error_msg:
                        user_error = "Your session has expired. Please log out and log back in."
                    else:
                        user_error = "Sorry, I couldn't confirm that appointment. Please try selecting a different time."

                    # Clear pending action on error
                    if 'context' in workflow_state:
                        workflow_state['context'].pop('pending_action', None)
                    state_manager.save_state(session_id, workflow_state)

                    timing['total'] = time.time() - start_time
                    pf_status = response_body.get('pf_http_status_code', 400)
                    return {
                        'response': user_error,
                        'intent': 'scheduling',
                        'action': 'confirm_appointment',
                        'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                        'direct_call': True,
                        'timing': timing,
                        'pf_http_status_code': pf_status,
                        'error': True
                    }

                # Clear pending action from context
                if 'context' in workflow_state:
                    workflow_state['context'].pop('pending_action', None)
                state_manager.save_state(session_id, workflow_state)

                # Format success response
                project_name = pending.get('preview', {}).get('project_name', 'your project')
                date_str = pending.get('preview', {}).get('date', '')
                time_str = pending.get('preview', {}).get('time', '')

                response_text = f"All set! Your {project_name} appointment is confirmed for {date_str} at {time_str}. Is there anything else I can help you with?"

                # VOICE ENHANCEMENT: Save action to context for intelligent responses
                if channel == 'voice':
                    save_action_to_context(
                        state_manager, session_id,
                        action='confirm_appointment',
                        result='success',
                        project_id=pending.get('preview', {}).get('project_id'),
                        project_name=project_name,
                        extra_context={'scheduled_date': date_str, 'scheduled_time': time_str}
                    )

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'scheduling',
                    'action': 'confirm_appointment',
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing,
                    'pf_http_status_code': 200
                }
            except Exception as e:
                logger.error(f"[CONFIRM] Failed to execute pending appointment: {e}")
                if 'context' in workflow_state:
                    workflow_state['context'].pop('pending_action', None)
                state_manager.save_state(session_id, workflow_state)
                timing['total'] = time.time() - start_time
                return {
                    'response': "I had trouble confirming that appointment. Would you like to try again?",
                    'intent': 'scheduling',
                    'action': 'confirm_appointment',
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing,
                    'pf_http_status_code': 500
                }

        elif is_decline and pending_action:
            logger.info(f"[CONFIRM] User declined pending {pending_action}")
            # Clear pending action from context
            if 'context' in workflow_state:
                workflow_state['context'].pop('pending_action', None)
            state_manager.save_state(session_id, workflow_state)

            timing['total'] = time.time() - start_time
            return {
                'response': "No problem! Would you like to pick a different time, or is there something else I can help with?",
                'intent': 'scheduling',
                'action': 'decline_pending',
                'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                'direct_call': True,
                'timing': timing,
                'pf_http_status_code': 200
            }

    # ========================================================================
    # STEP 0: Check for workflow continuation FIRST (before classification)
    # This prevents "5th Dec" from being interpreted as "5th project"
    # ========================================================================
    continuation = check_workflow_continuation(message, workflow_state, channel)

    # Handle CONTEXT SWITCH: User mentioned a different project
    # Preserve viewed_projects history while switching to new project context
    context_switch_handled = False  # Flag to skip decision step after context switch
    if continuation and continuation.get('context_switch'):
        logger.info("[CONTEXT_SWITCH] Preserving project history during context switch")
        # Get current state to preserve viewed_projects and project_mapping
        current_state = workflow_state or {}
        viewed_projects = current_state.get('viewed_projects', [])
        project_mapping = current_state.get('project_mapping', {})

        # Reset workflow state but preserve project history
        # The new project context will be set when we process the request
        new_state = {
            'workflow_type': 'browsing',
            'current_stage': 'viewing',
            'context': {},  # Will be updated with new project
            'viewed_projects': viewed_projects,
            'project_mapping': project_mapping,
            'conversation_summary': 'User switched to a different project',
            'last_action': 'context_switch'
        }
        state_manager.save_state(session_id, new_state)
        workflow_state = new_state  # Update local variable
        continuation = None  # Skip continuation processing - process fresh
        context_switch_handled = True  # Mark that we just handled a context switch

    if continuation and continuation.get('continue_workflow'):
        logger.info(f"[CONTINUATION] Bypassing classification - user provided data at stage '{workflow_state.get('current_stage')}'")

        # Execute the continuation action directly
        try:
            action = continuation['action']
            params = continuation['params']
            next_stage = continuation['next_stage']
            preserve_context = continuation.get('preserve_context', {})
            cont_workflow_type = continuation.get('workflow_type', '')

            # ================================================================
            # HANDLE ABORT: Special case - no Lambda call needed
            # ================================================================
            if action == 'abort_workflow':
                logger.info("[CONTINUATION] Aborting workflow - clearing state")
                state_manager.clear_state(session_id)
                abort_message = continuation.get('abort_message', "No problem. What else can I help with?")
                timing['total'] = time.time() - start_time
                return {
                    'response': abort_message,
                    'intent': 'scheduling',
                    'action': 'abort_workflow',
                    'agent_name': 'Intelligent Orchestrator (Abort)',
                    'direct_call': True,
                    'timing': timing,
                    'channel': channel
                }

            # ================================================================
            # HANDLE CANCEL EXECUTE: Confirmed cancel - call actual cancel API
            # ================================================================
            if action == 'cancel_appointment_execute':
                logger.info("[CONTINUATION] Executing confirmed cancel")
                # Call the actual cancel_appointment action
                action = 'cancel_appointment'
                params['confirmed'] = True

            # Determine if this is a reschedule workflow
            is_reschedule = cont_workflow_type == 'reschedule_appointment'

            # NOTE: We no longer convert get_time_slots to get_rescheduler_slots
            # The new slotsChatbot API works for both schedule and reschedule flows
            if is_reschedule and action == 'get_time_slots':
                logger.info(f"[CONTINUATION] Reschedule workflow - using get_time_slots (slotsChatbot API)")

            # Add common params
            params.update({
                'customer_id': customer_id,
                'client_id': client_id,
                'pf_bearer_token': pf_bearer_token,
                'from_phone': from_phone
            })

            # INJECT BASE_DATE FOR GET_TIME_SLOTS in continuation handler
            # This is critical for "next month" scheduling - API URL needs base_date from get_available_dates
            if action == 'get_time_slots':
                if 'start_date' in preserve_context and 'base_date' not in params:
                    params['base_date'] = preserve_context['start_date']
                    logger.info(f"[CONTINUATION][TIME_SLOTS] Injected base_date from preserve_context: {preserve_context['start_date']}")

            # ================================================================
            # CONFIRMATION INTERCEPTION (Chat/SMS only) - In Continuation Handler
            # Before executing confirm_appointment, return preview for user approval
            # ================================================================
            if action == 'confirm_appointment' and channel != 'voice':
                logger.info(f"[CONFIRM] Intercepting confirm_appointment in continuation handler (channel={channel})")

                # Get context for preview from preserve_context and params
                project_name = preserve_context.get('category', preserve_context.get('project_name', 'Project'))
                project_id = params.get('project_id', preserve_context.get('project_id', ''))
                date_str = params.get('date', preserve_context.get('date', ''))
                time_str = params.get('time', preserve_context.get('time', ''))
                address = preserve_context.get('address', preserve_context.get('full_address', ''))
                project_type = preserve_context.get('project_type', '')

                # Format date for preview (YYYY-MM-DD -> MM/DD/YYYY with day name)
                formatted_preview_date = date_str
                try:
                    from datetime import datetime as dt
                    date_obj = dt.strptime(date_str, "%Y-%m-%d")
                    formatted_preview_date = date_obj.strftime("%a %m/%d/%Y")  # Mon 01/26/2026
                except:
                    pass  # Keep original if parsing fails

                # Store pending action in workflow state
                pending_action = {
                    'action': 'confirm_appointment',
                    'params': {
                        'project_id': project_id,
                        'date': date_str,
                        'time': time_str,
                        'request_id': params.get('request_id', preserve_context.get('request_id', ''))
                    },
                    'preview': {
                        'project_name': project_name,
                        'project_id': project_id,
                        'project_type': project_type,
                        'date': formatted_preview_date,  # Formatted for UI display
                        'rawDate': date_str,  # Keep raw for API calls
                        'time': time_str,
                        'formattedTime': format_time_12hr(time_str),
                        'address': address
                    }
                }

                # Update workflow state with pending action
                # NOTE: pending_action must be stored in 'context' as save_state only saves specific fields
                if 'context' not in workflow_state:
                    workflow_state['context'] = {}
                workflow_state['context']['pending_action'] = pending_action
                workflow_state['current_stage'] = 'awaiting_confirmation'
                state_manager.save_state(session_id, workflow_state)
                logger.info(f"[CONFIRM] Stored pending action in context, stage=awaiting_confirmation")

                # Build confirmation preview response
                # Format date for display (YYYY-MM-DD -> MM/DD/YYYY with day name)
                formatted_date_str = date_str
                try:
                    from datetime import datetime as dt
                    date_obj = dt.strptime(date_str, "%Y-%m-%d")
                    formatted_date_str = date_obj.strftime("%a %m/%d/%Y")  # Mon 01/26/2026
                except:
                    pass  # Keep original if parsing fails

                preview_text = f"📋 **Appointment Preview**\n\n"
                preview_text += f"**Project:** {project_name}\n"
                if project_type:
                    preview_text += f"**Type:** {project_type}\n"
                preview_text += f"**Date:** {formatted_date_str}\n"
                preview_text += f"**Time:** {format_time_12hr(time_str)}\n"
                if address:
                    preview_text += f"**Location:** {address}\n"
                preview_text += f"\nWould you like to confirm this appointment?"

                timing['total'] = time.time() - start_time
                return {
                    'response': preview_text,
                    'intent': 'scheduling',
                    'action': 'confirm_appointment_preview',
                    'confirmation_required': True,
                    'pending_action': pending_action.get('preview', {}),
                    'agent_name': 'Intelligent Orchestrator (Confirmation)',
                    'direct_call': True,
                    'timing': timing,
                    'channel': channel,
                    'pf_http_status_code': 200
                }

            logger.info(f"[CONTINUATION] Calling Lambda: action={action}, params={list(params.keys())}")

            # Call Lambda directly
            lambda_start = time.time()
            lambda_response = call_lambda_directly(action, params)
            timing['lambda_call'] = time.time() - lambda_start

            # Extract response
            response_data = lambda_response.get('response', {})
            func_response = response_data.get('functionResponse', {})
            body_wrapper = func_response.get('responseBody', {})
            text_body = body_wrapper.get('TEXT', {})
            body_str = text_body.get('body', '{}')

            if isinstance(body_str, str):
                response_body = json.loads(body_str)
            else:
                response_body = body_str

            # WEATHER ENRICHMENT for reschedule_appointment step 2 (available dates)
            if action == 'reschedule_appointment' and response_body.get('available_dates'):
                project_category = preserve_context.get('category')
                if project_category and is_outdoor_project(project_category):
                    logger.info(f"[CONTINUATION][WEATHER] Outdoor project ({project_category}), enriching reschedule dates with weather")
                    location = None
                    city = preserve_context.get('city')
                    state = preserve_context.get('state')
                    if city and state:
                        location = f"{city}, {state}"

                    if location:
                        try:
                            weather_params = {
                                'location': location,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            }
                            weather_response = call_lambda_directly('get_weather', weather_params)

                            w_data = weather_response.get('response', {})
                            w_func = w_data.get('functionResponse', {})
                            w_body_wrapper = w_func.get('responseBody', {})
                            w_text = w_body_wrapper.get('TEXT', {})
                            w_body_str = w_text.get('body', '{}')

                            if isinstance(w_body_str, str):
                                weather_body = json.loads(w_body_str)
                            else:
                                weather_body = w_body_str

                            # Enrich dates with weather using existing helper
                            # Signature: add_weather_indicators_to_dates(weather_data, available_dates, category)
                            available_dates = response_body.get('available_dates', [])
                            enriched_dates = add_weather_indicators_to_dates(
                                weather_body, available_dates, project_category
                            )
                            # Store as dates_with_weather for UI rendering (same as other flows)
                            response_body['dates_with_weather'] = enriched_dates
                            logger.info(f"[CONTINUATION][WEATHER] Enriched {len(enriched_dates)} reschedule dates with weather")
                        except Exception as weather_err:
                            logger.warning(f"[CONTINUATION][WEATHER] Reschedule weather enrichment failed (non-fatal): {weather_err}")

            # WEATHER ENRICHMENT for time slots (outdoor projects)
            if action in ['get_time_slots', 'get_rescheduler_slots']:
                project_category = preserve_context.get('category')
                if project_category and is_outdoor_project(project_category):
                    logger.info(f"[CONTINUATION][WEATHER] Outdoor project ({project_category}), enriching time slots with weather")
                    location = None
                    city = preserve_context.get('city')
                    state = preserve_context.get('state')
                    if city and state:
                        location = f"{city}, {state}"

                    if location:
                        try:
                            weather_params = {
                                'location': location,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            }
                            weather_response = call_lambda_directly('get_weather', weather_params)

                            w_data = weather_response.get('response', {})
                            w_func = w_data.get('functionResponse', {})
                            w_body_wrapper = w_func.get('responseBody', {})
                            w_text = w_body_wrapper.get('TEXT', {})
                            w_body_str = w_text.get('body', '{}')

                            if isinstance(w_body_str, str):
                                weather_body = json.loads(w_body_str)
                            else:
                                weather_body = w_body_str

                            # Find forecast for the selected date
                            target_date = params.get('date')
                            forecast = find_forecast_for_date(weather_body, target_date)

                            if forecast:
                                suitability = analyze_weather_suitability(forecast, project_category)
                                response_body['weather_forecast'] = forecast
                                response_body['weather_suitability'] = suitability
                                logger.info(f"[CONTINUATION][WEATHER] Added weather for {target_date}: {suitability.get('suitable', 'N/A')}")
                        except Exception as weather_err:
                            logger.warning(f"[CONTINUATION][WEATHER] Weather enrichment failed (non-fatal): {weather_err}")

            # Format the response
            response_text = format_lambda_response(action, response_body, message, channel)

            # HANDLE TWO-STEP CONFIRM: When confirm_appointment returns awaiting_confirmation (Step 1)
            # User must say "yes" before we actually confirm - DON'T reset the workflow!
            if action == 'confirm_appointment' and response_body.get('status') == 'awaiting_confirmation':
                project_id = response_body.get('project_id') or params.get('project_id')
                date = response_body.get('date') or params.get('date')
                time_slot = response_body.get('time') or params.get('time')
                request_id = response_body.get('request_id') or params.get('request_id')
                category = response_body.get('category') or preserve_context.get('category', '')

                logger.info(f"[CONTINUATION] TWO-STEP CONFIRM: Setting awaiting_appointment_confirm for project {project_id}")

                # Preserve project_mapping from existing state
                existing_mapping = workflow_state.get('project_mapping', {}) if workflow_state else {}

                # Save workflow state - user must confirm before we finalize
                state_manager.save_state(session_id, {
                    'workflow_type': 'confirm_appointment',
                    'current_stage': 'awaiting_appointment_confirm',
                    'context': {
                        'project_id': project_id,
                        'date': date,
                        'time': time_slot,
                        'request_id': request_id,
                        'category': category,
                        'project_mapping': existing_mapping,
                        'address': preserve_context.get('address', ''),
                        'project_type': preserve_context.get('project_type', '')
                    },
                    'project_mapping': existing_mapping
                })

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'scheduling',
                    'action': action,
                    'agent_name': 'Intelligent Orchestrator (Stage-Driven Continuation)',
                    'direct_call': True,
                    'timing': timing
                }

            # Update workflow state
            if next_stage == 'complete':
                # VOICE ENHANCEMENT: Save action to context before clearing state
                if channel == 'voice' and action == 'confirm_appointment':
                    project_name = preserve_context.get('category', preserve_context.get('project_name', 'project'))
                    save_action_to_context(
                        state_manager, session_id,
                        action='confirm_appointment',
                        result='success',
                        project_id=params.get('project_id', preserve_context.get('project_id')),
                        project_name=project_name,
                        extra_context={
                            'scheduled_date': params.get('date', preserve_context.get('date')),
                            'scheduled_time': params.get('time', preserve_context.get('time'))
                        }
                    )

                state_manager.reset_workflow_state(session_id)
                logger.info("[CONTINUATION] Workflow complete, state reset (memory preserved)")
            else:
                # Update context with preserved values and selected date
                new_context = {k: v for k, v in preserve_context.items() if v is not None}

                # Update date in context if this was a date selection
                if action == 'get_time_slots' or action == 'get_rescheduler_slots':
                    new_context['date'] = params.get('date')
                    # Also extract request_id from response for next step
                    if response_body.get('request_id'):
                        new_context['request_id'] = response_body['request_id']
                    # CRITICAL: Save time_slots for "Yes" auto-select logic
                    # When user says "Yes" or "That works", auto-select first time slot
                    # scheduling-actions returns: available_slots, timeSlots, slots (rescheduler), or time_slots
                    saved_slots = response_body.get('available_slots') or response_body.get('timeSlots') or response_body.get('slots') or response_body.get('time_slots')
                    if saved_slots:
                        new_context['time_slots'] = saved_slots
                        logger.info(f"[CONTINUATION] Saved {len(saved_slots)} time_slots for auto-select")

                # Extract request_id and available_dates from reschedule_appointment step 2 response (dates)
                if action == 'reschedule_appointment':
                    if response_body.get('request_id'):
                        new_context['request_id'] = response_body['request_id']
                        logger.info(f"[CONTINUATION] Extracted request_id from reschedule dates: {response_body['request_id']}")
                    # CRITICAL: Save available_dates for single-date auto-select logic
                    # When only 1 date is available and user says "yes", continuation handler needs this
                    if response_body.get('available_dates'):
                        new_context['available_dates'] = response_body['available_dates']
                        logger.info(f"[CONTINUATION] Saved {len(response_body['available_dates'])} available_dates for reschedule workflow")

                # Preserve project_mapping from existing state
                existing_mapping = workflow_state.get('project_mapping', {}) if workflow_state else {}
                state_manager.save_state(session_id, {
                    'workflow_type': cont_workflow_type,
                    'current_stage': next_stage,
                    'context': new_context,
                    'project_mapping': existing_mapping
                })
                logger.info(f"[CONTINUATION] State updated: stage={next_stage}")

            timing['total'] = time.time() - start_time
            return {
                'response': response_text,
                'intent': 'scheduling',
                'action': action,
                'agent_name': 'Intelligent Orchestrator (Stage-Driven Continuation)',
                'direct_call': True,
                'timing': timing
            }

        except Exception as cont_err:
            logger.error(f"[CONTINUATION] Error executing continuation: {cont_err}")
            # Fall through to normal classification on error

    # ========================================================================
    # STEP 0.4: VOICE-SPECIFIC - Force list_projects for "how many jobs" queries
    # This bypasses Sonnet classification which sometimes misclassifies as context_query
    # Voice-only: Chat has conversation history context, voice often starts fresh
    # ========================================================================
    if channel == 'voice':
        msg_lower = message.lower().strip()
        # Patterns that should ALWAYS trigger list_projects for voice
        list_project_patterns = [
            'how many job', 'how many project', 'how many work',
            'list my job', 'list my project', 'list my work',
            'show my job', 'show my project', 'show my work',
            'what job', 'what project', 'what work do i have',
            'any job', 'any project', 'do i have any',
            'tell me about my job', 'tell me about my project',
            'my jobs', 'my projects', 'my work'
        ]
        if any(pattern in msg_lower for pattern in list_project_patterns):
            logger.info(f"[VOICE-PRECHECK] Detected project list query, forcing list_projects action")
            try:
                # Directly call list_projects Lambda
                list_response = call_lambda_directly('list_projects', {
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_bearer_token,
                    'from_phone': from_phone  # For voice cache lookup
                })

                # Parse response
                list_data = list_response.get('response', {})
                list_func = list_data.get('functionResponse', {})
                list_body_wrapper = list_func.get('responseBody', {})
                list_text = list_body_wrapper.get('TEXT', {})
                list_body_str = list_text.get('body', '{}')

                if isinstance(list_body_str, str):
                    response_body = json.loads(list_body_str)
                else:
                    response_body = list_body_str

                # Format response for voice
                response_text = format_lambda_response('list_projects', response_body, message, channel)

                # Save project_ids AND project_mapping to workflow state for ordinal/category references
                if 'projects' in response_body:
                    project_ids = [str(p.get('id', '')) for p in response_body['projects'] if p.get('id')]
                    # Build project_mapping: project_id -> {category, category_bucket, address, status, projectNumber}
                    # category_bucket enables "show kitchen projects" to match Dishwasher, Ovens, etc.
                    # projectNumber (Order Number) enables lookup when user references by order number
                    project_mapping = {}
                    for p in response_body['projects']:
                        pid = str(p.get('id', ''))
                        if pid:
                            exact_category = p.get('category', '')
                            project_number = p.get('projectNumber', '')
                            project_mapping[pid] = {
                                'category': exact_category,
                                'category_bucket': get_category_bucket(exact_category),
                                'address': p.get('address', ''),
                                'status': p.get('status', ''),
                                'projectNumber': project_number,  # Order Number for user display
                                'project_type': p.get('projectType', p.get('ProjectType', ''))
                            }
                            # Also map by projectNumber (Order Number) for reverse lookup
                            if project_number:
                                project_mapping[project_number] = {
                                    'category': exact_category,
                                    'category_bucket': get_category_bucket(exact_category),
                                    'address': p.get('address', ''),
                                    'status': p.get('status', ''),
                                    'project_id': pid,  # Internal project ID for API calls
                                    'project_type': p.get('projectType', p.get('ProjectType', ''))
                                }
                    if project_ids:
                        logger.info(f"[VOICE-PRECHECK] Saving {len(project_ids)} project_ids and project_mapping to workflow state")
                        # Get existing state to preserve viewed_projects
                        existing_state = state_manager.get_state(session_id) or {}
                        viewed_projects = existing_state.get('viewed_projects', [])

                        state_manager.save_state(session_id, {
                            'workflow_type': 'view_projects',
                            'current_stage': 'showing_projects',
                            'context': {
                                'project_ids': project_ids,
                                'project_mapping': project_mapping,
                                'customer_id': customer_id
                            },
                            'viewed_projects': viewed_projects,
                            'project_mapping': project_mapping
                        })

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'scheduling',
                    'action': 'list_projects',
                    'agent_name': 'Intelligent Orchestrator (Voice Pre-check)',
                    'direct_call': True,
                    'timing': timing
                }
            except Exception as voice_err:
                logger.warning(f"[VOICE-PRECHECK] Error in voice pre-check: {voice_err}, falling through to normal flow")
                # Fall through to normal classification

        # ====================================================================
        # VOICE FAST PATH: Handle "schedule projects" type requests instantly
        # This bypasses Sonnet classification (6-10s) and uses voice cache
        # ====================================================================
        scheduling_patterns = [
            'schedule project', 'schedule a project', 'schedule the project',
            'schedule something', 'schedule appointment', 'schedule an appointment',
            'i want to schedule', 'let me schedule', "let's schedule",
            'book an appointment', 'book appointment', 'make an appointment',
            'schedule my', 'can i schedule', 'could i schedule',
            'i need to schedule', 'help me schedule'
        ]
        if any(pattern in msg_lower for pattern in scheduling_patterns):
            logger.info(f"[VOICE-FAST-PATH] Detected scheduling request: '{message}' - bypassing Sonnet classification")
            try:
                # Call list_projects with from_phone to use voice cache
                list_response = call_lambda_directly('list_projects', {
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_bearer_token,
                    'from_phone': from_phone  # Voice cache lookup
                })

                # Parse response
                list_data = list_response.get('response', {})
                list_func = list_data.get('functionResponse', {})
                list_body_wrapper = list_func.get('responseBody', {})
                list_text = list_body_wrapper.get('TEXT', {})
                list_body_str = list_text.get('body', '{}')

                if isinstance(list_body_str, str):
                    response_body = json.loads(list_body_str)
                else:
                    response_body = list_body_str

                projects = response_body.get('projects', [])

                # Filter to schedulable projects only (exclude already scheduled)
                schedulable_statuses = ['New', 'Ready To Schedule']
                schedulable_projects = [p for p in projects if p.get('status') in schedulable_statuses]

                logger.info(f"[VOICE-FAST-PATH] Found {len(schedulable_projects)} schedulable projects out of {len(projects)} total")

                # Handle case: All projects already scheduled
                if not schedulable_projects and projects:
                    # Check if any are scheduled
                    scheduled_projects = [p for p in projects if p.get('status') in SCHEDULED_STATUSES]
                    if scheduled_projects:
                        first = scheduled_projects[0]
                        cat = first.get('category', 'Your project')
                        project_id = str(first.get('id', ''))
                        sched_date = first.get('scheduledDate', '')
                        if sched_date:
                            voice_response = f"{cat} is already scheduled for {sched_date}. Would you like to reschedule, or check the appointment details?"
                        else:
                            voice_response = f"{cat} is already scheduled. Would you like to reschedule, or check the appointment details?"

                        # Save workflow state so "yes" or "reschedule" can continue the flow
                        project_mapping = {
                            project_id: {
                                'category': cat,
                                'category_bucket': get_category_bucket(cat),
                                'address': first.get('address', ''),
                                'status': first.get('status', ''),
                                'projectNumber': first.get('projectNumber', ''),
                                'project_type': first.get('projectType', first.get('ProjectType', '')),
                                'scheduled_date': sched_date
                            }
                        }
                        state_manager.save_state(session_id, {
                            'workflow_type': 'reschedule_offer',
                            'current_stage': 'awaiting_reschedule_confirm',
                            'context': {
                                'project_ids': [project_id],
                                'project_mapping': project_mapping,
                                'selected_project_id': project_id,
                                'customer_id': customer_id,
                                'pending_action': 'reschedule_appointment'
                            },
                            'project_mapping': project_mapping
                        })
                        logger.info(f"[VOICE-FAST-PATH] Saved reschedule_offer state for project {project_id}")

                        timing['total'] = time.time() - start_time
                        return {
                            'response': voice_response,
                            'intent': 'scheduling',
                            'action': 'already_scheduled',
                            'agent_name': 'Intelligent Orchestrator (Voice Fast Path)',
                            'direct_call': True,
                            'timing': timing,
                            'channel': channel
                        }

                # Handle case: No projects at all
                if not projects:
                    timing['total'] = time.time() - start_time
                    return {
                        'response': "I don't see any projects linked to your phone number. If you received a text or call about an appointment, you may be calling from a different number than we have on file. Would you like me to give you the office number so they can help you directly?",
                        'intent': 'scheduling',
                        'action': 'no_projects',
                        'agent_name': 'Intelligent Orchestrator (Voice Fast Path)',
                        'direct_call': True,
                        'timing': timing,
                        'channel': channel
                    }

                # Build project mapping for workflow state
                project_ids = [str(p.get('id', '')) for p in schedulable_projects if p.get('id')]
                project_mapping = {}
                for p in schedulable_projects:
                    pid = str(p.get('id', ''))
                    if pid:
                        exact_category = p.get('category', '')
                        project_number = p.get('projectNumber', '')
                        project_mapping[pid] = {
                            'category': exact_category,
                            'category_bucket': get_category_bucket(exact_category),
                            'address': p.get('address', ''),
                            'status': p.get('status', ''),
                            'projectNumber': project_number,
                            'project_type': p.get('projectType', p.get('ProjectType', ''))
                        }
                        # Also map by projectNumber (Order Number) for reverse lookup
                        if project_number:
                            project_mapping[project_number] = {
                                'category': exact_category,
                                'category_bucket': get_category_bucket(exact_category),
                                'address': p.get('address', ''),
                                'status': p.get('status', ''),
                                'project_id': pid,  # Internal project ID for API calls
                                'project_type': p.get('projectType', p.get('ProjectType', ''))
                            }

                # Format voice response for scheduling selection
                # Helper to format project names with differentiation (Type → Address → Ordinals)
                def format_project_names(projects_to_format):
                    """Format project names with Type, Address, or Ordinals for differentiation."""
                    # Debug: Log incoming project data
                    for idx, p in enumerate(projects_to_format):
                        pid = p.get('id', 'unknown')
                        cat = p.get('category', '')
                        ptype = p.get('projectType', p.get('ProjectType', ''))
                        logger.info(f"[FORMAT-NAMES] Project {idx}: id={pid}, category='{cat}', projectType='{ptype}'")

                    # First pass: check for duplicates when using category+type
                    seen_keys = set()
                    needs_address = False
                    for p in projects_to_format:
                        cat = p.get('category', 'project')
                        ptype = p.get('projectType', p.get('ProjectType', ''))
                        key = f"{cat}|{ptype}"
                        if key in seen_keys:
                            needs_address = True
                            break
                        seen_keys.add(key)

                    logger.info(f"[FORMAT-NAMES] needs_address={needs_address}, seen_keys={seen_keys}")

                    # Build names with appropriate differentiation
                    # Fallback chain: Type → Type+Address → Type+Store → Type+DateSold → Ordinals
                    names = []
                    seen_names = set()
                    for i, p in enumerate(projects_to_format):
                        cat = p.get('category', 'project')
                        ptype = p.get('projectType', p.get('ProjectType', ''))
                        addr = p.get('address', {})

                        # Extract address string
                        if isinstance(addr, dict):
                            addr_str = addr.get('address1', '') or addr.get('city', '')
                        else:
                            addr_str = str(addr).split(',')[0] if addr else ''

                        # Extract store name
                        store = p.get('store', {})
                        store_name = store.get('storeName', '') if isinstance(store, dict) else ''

                        # Extract date sold (month/year for voice)
                        date_sold = p.get('dateSold', '')
                        date_sold_str = ''
                        if date_sold:
                            try:
                                from datetime import datetime as dt_cls
                                ds = dt_cls.fromisoformat(date_sold.replace('Z', '+00:00'))
                                date_sold_str = ds.strftime('%B %Y')  # e.g., "October 2024"
                            except:
                                pass

                        # Build name: Category + Type, or Category + Address, or ordinal + Category
                        if ptype:
                            name = f"{cat} {ptype}"
                        elif addr_str:
                            name = f"{cat} at {addr_str[:25]}"
                        else:
                            name = cat

                        # If still duplicate, try adding address/store/date
                        if name in seen_names:
                            if addr_str:
                                name = f"{cat} {ptype} at {addr_str[:25]}" if ptype else f"{cat} at {addr_str[:25]}"
                            if name in seen_names and store_name:
                                name = f"{cat} {ptype} from {store_name}" if ptype else f"{cat} from {store_name}"
                            if name in seen_names and date_sold_str:
                                name = f"{cat} {ptype} sold {date_sold_str}" if ptype else f"{cat} sold {date_sold_str}"
                            # Final fallback: ordinal
                            if name in seen_names:
                                ordinal = ["first", "second", "third", "fourth", "fifth"][i] if i < 5 else f"#{i+1}"
                                name = f"the {ordinal} {cat} {ptype}" if ptype else f"the {ordinal} {cat}"

                        seen_names.add(name)
                        names.append(name)
                        logger.info(f"[FORMAT-NAMES] Project {i}: built name='{name}'")

                    logger.info(f"[FORMAT-NAMES] Final names: {names}")
                    return names

                if len(schedulable_projects) == 1:
                    # Single project - ask for confirmation
                    proj = schedulable_projects[0]
                    cat = proj.get('category', 'project')
                    ptype = proj.get('projectType', proj.get('ProjectType', ''))
                    display_name = f"{cat} {ptype}" if ptype else cat
                    voice_response = f"I see you have a {display_name} project ready to schedule. Would you like me to show you the available dates?"
                    next_stage = 'awaiting_schedule_confirm'
                elif len(schedulable_projects) <= 5:
                    # 2-5 projects - list them with differentiation
                    names = format_project_names(schedulable_projects)
                    voice_response = f"You have {len(schedulable_projects)} projects ready to schedule: " + ", ".join(names) + ". Which one would you like to schedule?"
                    next_stage = 'awaiting_project_selection'
                else:
                    # Many projects (6+) - list first 5 with differentiation
                    names = format_project_names(schedulable_projects[:5])
                    remaining = len(schedulable_projects) - 5
                    voice_response = f"You have {len(schedulable_projects)} projects ready to schedule, including: " + ", ".join(names) + f", and {remaining} more. Which one would you like to schedule?"
                    next_stage = 'awaiting_project_selection'

                # Save workflow state for next turn
                state_manager.save_state(session_id, {
                    'workflow_type': 'guided_selection',
                    'current_stage': next_stage,
                    'context': {
                        'project_ids': project_ids,
                        'project_mapping': project_mapping,
                        'customer_id': customer_id,
                        'filter_status': 'schedulable',
                        'pending_action': 'schedule_appointment'  # For continuation handler recognition
                    },
                    'project_mapping': project_mapping
                })

                timing['total'] = time.time() - start_time
                logger.info(f"[VOICE-FAST-PATH] Returning in {timing['total']:.2f}s (skipped Sonnet)")

                return {
                    'response': voice_response,
                    'intent': 'scheduling',
                    'action': 'list_projects',
                    'agent_name': 'Intelligent Orchestrator (Voice Fast Path)',
                    'direct_call': True,
                    'timing': timing,
                    'channel': channel
                }
            except Exception as voice_sched_err:
                logger.warning(f"[VOICE-FAST-PATH] Error: {voice_sched_err}, falling through to normal flow")
                # Fall through to normal classification

    # ========================================================================
    # STEP 0.4a: VAGUE CHATBOT ACTION PROMPTS - Provide guided responses
    # When user clicks action buttons like "Schedule appointments" without context,
    # guide them with a helpful response showing available options
    # ========================================================================
    msg_lower = message.lower().strip()

    # Define vague prompts that need guided responses
    vague_prompts = {
        # Exact matches for chatbot action button text
        "schedule appointments": {
            "needs": "project",
            "response_intro": "I'd be happy to help you schedule an appointment!",
            "filter_status": "schedulable"
        },
        "check available dates": {
            "needs": "project",
            "response_intro": "I can check available dates for you!",
            "filter_status": "schedulable"
        },
        "view available time slots": {
            "needs": "project_and_date",
            "response_intro": "I can show you available time slots!",
            "filter_status": "schedulable"
        },
        "retrieve project details": {
            "needs": "project",
            "response_intro": "I can show you project details!",
            "filter_status": None  # Show all projects
        },
        # Also handle variations
        "i want to schedule an appointment": {
            "needs": "project",
            "response_intro": "I'd be happy to help you schedule an appointment!",
            "filter_status": "schedulable"
        },
        "schedule an appointment": {
            "needs": "project",
            "response_intro": "I'd be happy to help you schedule an appointment!",
            "filter_status": "schedulable"
        },
        "book an appointment": {
            "needs": "project",
            "response_intro": "I'd be happy to help you book an appointment!",
            "filter_status": "schedulable"
        },
        "get available dates": {
            "needs": "project",
            "response_intro": "I can check available dates for you!",
            "filter_status": "schedulable"
        },
        "show project details": {
            "needs": "project",
            "response_intro": "I can show you project details!",
            "filter_status": None
        },
        # Common variations for scheduling
        "schedule a project": {
            "needs": "project",
            "response_intro": "I'd be happy to help you schedule a project!",
            "filter_status": "schedulable"
        },
        "schedule project": {
            "needs": "project",
            "response_intro": "I'd be happy to help you schedule a project!",
            "filter_status": "schedulable"
        },
        "i want to schedule a project": {
            "needs": "project",
            "response_intro": "I'd be happy to help you schedule a project!",
            "filter_status": "schedulable"
        },
        "i want to schedule": {
            "needs": "project",
            "response_intro": "I'd be happy to help you schedule!",
            "filter_status": "schedulable"
        },
        "schedule something": {
            "needs": "project",
            "response_intro": "I'd be happy to help you schedule!",
            "filter_status": "schedulable"
        }
    }

    # Check if message matches a vague prompt
    vague_match = vague_prompts.get(msg_lower)

    if vague_match and channel != 'voice':  # Only for chat, voice has different UX
        logger.info(f"[VAGUE-PROMPT] Detected vague chatbot action: '{message}' - providing guided response")

        try:
            # Fetch projects to show options
            list_response = call_lambda_directly('list_projects', {
                'customer_id': customer_id,
                'client_id': client_id,
                'pf_bearer_token': pf_bearer_token,
                'from_phone': from_phone
            })

            # Parse response
            list_data = list_response.get('response', {})
            list_func = list_data.get('functionResponse', {})
            list_body_wrapper = list_func.get('responseBody', {})
            list_text = list_body_wrapper.get('TEXT', {})
            list_body_str = list_text.get('body', '{}')

            if isinstance(list_body_str, str):
                response_body = json.loads(list_body_str)
            else:
                response_body = list_body_str

            # Get HTTP status
            pf_http_status_code = response_body.get('pf_http_status_code', 200)

            # Check for session errors
            if pf_http_status_code in [401, 403]:
                timing['total'] = time.time() - start_time
                return {
                    'response': "Your session has expired. Please log out and log back in to continue.",
                    'intent': 'scheduling',
                    'action': 'session_expired',
                    'agent_name': 'Intelligent Orchestrator (Vague Prompt Handler)',
                    'direct_call': True,
                    'timing': timing,
                    'pf_http_status_code': pf_http_status_code
                }

            projects = response_body.get('projects', [])

            # Apply status filter if specified
            filter_status = vague_match.get('filter_status')
            if filter_status and projects:
                if filter_status == 'schedulable':
                    projects = [p for p in projects if p.get('status') in ['New', 'Ready To Schedule']]
                elif filter_status == 'scheduled':
                    projects = [p for p in projects if p.get('status') in ['Scheduled', 'Tentatively Scheduled']]

            # Build guided response
            intro = vague_match['response_intro']

            if not projects:
                if filter_status == 'schedulable':
                    response_text = f"{intro}\n\nHowever, you don't have any projects ready to schedule at the moment. Would you like to see all your projects instead?"
                else:
                    response_text = f"{intro}\n\nHowever, I don't see any projects linked to your account. If you received a message about an appointment, you may need to contact our office directly for assistance."
            else:
                # Build project list for user to choose from
                project_lines = []
                for i, p in enumerate(projects[:10], 1):  # Limit to 10 for readability
                    category = p.get('category', 'Unknown')
                    status = p.get('status', 'Unknown')
                    order_num = p.get('projectNumber', p.get('id', ''))
                    # Truncate long order numbers for display
                    if len(str(order_num)) > 20:
                        display_id = f"...{str(order_num)[-15:]}"
                    else:
                        display_id = order_num
                    project_lines.append(f"{i}. **{category}** (Order: {display_id}) - {status}")

                projects_display = "\n".join(project_lines)

                if vague_match['needs'] == 'project':
                    response_text = f"""{intro}

Here are your {'projects ready to schedule' if filter_status == 'schedulable' else 'projects'}:

{projects_display}

Which project would you like to {'schedule' if 'schedule' in msg_lower else 'view'}? You can say things like:
- "Schedule the **first** project"
- "Show details for the **Decking** project"
- "Schedule **Kitchen Sink**\""""
                elif vague_match['needs'] == 'project_and_date':
                    response_text = f"""{intro}

First, let me know which project and date you're interested in. Here are your projects ready to schedule:

{projects_display}

You can say something like:
- "Show time slots for **Kitchen Sink** on **January 10th**"
- "Available times for the **first project** next **Monday**\""""

            # Save projects to state for follow-up
            if projects:
                project_ids = [str(p.get('id', '')) for p in projects if p.get('id')]
                project_mapping = {}
                for p in projects:
                    pid = str(p.get('id', ''))
                    if pid:
                        exact_category = p.get('category', '')
                        project_number = p.get('projectNumber', '')
                        project_mapping[pid] = {
                            'category': exact_category,
                            'category_bucket': get_category_bucket(exact_category),
                            'address': p.get('address', ''),
                            'status': p.get('status', ''),
                            'projectNumber': project_number
                        }
                        if project_number:
                            project_mapping[project_number] = {
                                'category': exact_category,
                                'category_bucket': get_category_bucket(exact_category),
                                'address': p.get('address', ''),
                                'status': p.get('status', ''),
                                'project_id': pid,
                                'project_type': p.get('projectType', p.get('ProjectType', ''))
                            }

                existing_state = state_manager.get_state(session_id) or {}
                viewed_projects = existing_state.get('viewed_projects', [])

                state_manager.save_state(session_id, {
                    'workflow_type': 'guided_selection',
                    'current_stage': 'awaiting_project_selection',
                    'context': {
                        'project_ids': project_ids,
                        'project_mapping': project_mapping,
                        'customer_id': customer_id,
                        'pending_action': msg_lower  # Remember what user wanted to do
                    },
                    'viewed_projects': viewed_projects,
                    'project_mapping': project_mapping
                })
                logger.info(f"[VAGUE-PROMPT] Saved {len(project_ids)} projects to state for guided selection")

            timing['total'] = time.time() - start_time
            return {
                'response': response_text,
                'intent': 'scheduling',
                'action': 'guided_prompt',
                'agent_name': 'Intelligent Orchestrator (Vague Prompt Handler)',
                'direct_call': True,
                'timing': timing,
                'pf_http_status_code': pf_http_status_code
            }

        except Exception as vague_err:
            logger.warning(f"[VAGUE-PROMPT] Error handling vague prompt: {vague_err}, falling through to normal flow")
            # Fall through to normal classification

    # ========================================================================
    # STEP 0.4b: CALENDAR/SCHEDULED QUERIES - Bypass workflow context
    # These are NEW queries about scheduled appointments, not continuations
    # "What's on my calendar?", "What's scheduled?", "Show my appointments"
    # ========================================================================
    msg_lower = message.lower().strip()
    calendar_patterns = [
        "what's on my calendar", "whats on my calendar", "what is on my calendar",
        "what's scheduled", "whats scheduled", "what is scheduled",
        "show my appointments", "show scheduled",
        "what appointments", "scheduled projects", "what's booked", "whats booked"
    ]
    # Don't trigger calendar query if user wants to SCHEDULE something
    # e.g., "schedule my appointments" should NOT show scheduled projects
    schedule_intent_words = ['schedule ', 'book ', 'set up ', 'make ']
    has_schedule_intent = any(word in msg_lower for word in schedule_intent_words)

    if any(pattern in msg_lower for pattern in calendar_patterns) and not has_schedule_intent:
        logger.info(f"[CALENDAR-QUERY] Detected calendar/scheduled query - bypassing workflow context")
        try:
            # Directly call list_projects with status=Scheduled filter
            list_response = call_lambda_directly('list_projects', {
                'status': 'Scheduled',
                'customer_id': customer_id,
                'client_id': client_id,
                'pf_bearer_token': pf_bearer_token,
                'from_phone': from_phone
            })

            # Parse response
            list_data = list_response.get('response', {})
            list_func = list_data.get('functionResponse', {})
            list_body_wrapper = list_func.get('responseBody', {})
            list_text = list_body_wrapper.get('TEXT', {})
            list_body_str = list_text.get('body', '{}')

            if isinstance(list_body_str, str):
                response_body = json.loads(list_body_str)
            else:
                response_body = list_body_str

            # Apply ALL filters (status, technician_name, etc.) on the result
            if 'projects' in response_body:
                original_count = len(response_body['projects'])
                # Build filter params from classification entities
                filter_params = classification.get('entities', {}).copy()
                # Ensure scheduled status filter is applied
                if 'status' not in filter_params:
                    filter_params['status'] = 'scheduled'
                response_body['projects'] = apply_project_filters(response_body['projects'], filter_params)
                logger.info(f"[CALENDAR-QUERY] Filtered {original_count} → {len(response_body['projects'])} projects (params={filter_params})")

            # Format response
            response_text = format_lambda_response('list_projects', response_body, message, channel)

            # Save project_ids to workflow state
            if 'projects' in response_body:
                project_ids = [str(p.get('id', '')) for p in response_body['projects'] if p.get('id')]
                project_mapping = {}
                for p in response_body['projects']:
                    pid = str(p.get('id', ''))
                    if pid:
                        project_number = p.get('projectNumber', '')
                        exact_category = p.get('category', '')
                        project_mapping[pid] = {
                            'category': exact_category,
                            'category_bucket': get_category_bucket(exact_category),
                            'address': p.get('address', ''),
                            'status': p.get('status', ''),
                            'projectNumber': project_number,
                            'project_type': p.get('projectType', p.get('ProjectType', ''))
                        }
                        # Also map by projectNumber (Order Number) for reverse lookup
                        if project_number:
                            project_mapping[project_number] = {
                                'category': exact_category,
                                'category_bucket': get_category_bucket(exact_category),
                                'address': p.get('address', ''),
                                'status': p.get('status', ''),
                                'project_id': pid,  # Internal project ID for API calls
                                'project_type': p.get('projectType', p.get('ProjectType', ''))
                            }
                if project_ids:
                    state_manager.save_state(session_id, {
                        'workflow_type': 'project_list',
                        'current_stage': 'showing_scheduled',
                        'context': {
                            'project_ids': project_ids,
                            'project_mapping': project_mapping
                        },
                        'project_mapping': project_mapping  # Top-level for save_state()
                    })
                    logger.info(f"[CALENDAR-QUERY] Saved {len(project_ids)} scheduled project_ids to state")

            timing['total'] = time.time() - start_time
            return {
                'response': response_text,
                'intent': 'scheduling',
                'action': 'list_projects',
                'agent_name': 'Intelligent Orchestrator (Calendar Query)',
                'direct_call': True,
                'timing': timing,
                'pf_http_status_code': 200
            }
        except Exception as cal_err:
            logger.warning(f"[CALENDAR-QUERY] Error: {cal_err}, falling through to normal flow")
            # Fall through to normal classification

    # ========================================================================
    # STEP 0.4c: CONTEXT FILTER QUERIES - "Any of these ready to schedule?"
    # When user asks about "these/those" with a status filter, filter from
    # the previous list results instead of fetching fresh from API
    # ========================================================================
    context_filter_patterns = [
        # "any of these/those [status]" patterns
        (r'\b(?:any|which|are any|are there any)\s+(?:of\s+)?(?:these|those|them)\b.*\b(?:ready to schedule|schedulable|can schedule)\b', 'schedulable'),
        (r'\b(?:any|which|are any|are there any)\s+(?:of\s+)?(?:these|those|them)\b.*\b(?:scheduled|on the books|booked)\b', 'scheduled'),
        (r'\b(?:any|which|are any|are there any)\s+(?:of\s+)?(?:these|those|them)\b.*\b(?:completed|done|finished)\b', 'completed'),
        # "[status] ones from these" patterns
        (r'\b(?:ready to schedule|schedulable)\b.*\b(?:from\s+)?(?:these|those|them)\b', 'schedulable'),
        (r'\b(?:scheduled|booked)\b.*\b(?:from\s+)?(?:these|those|them)\b', 'scheduled'),
    ]

    for pattern, status_filter in context_filter_patterns:
        if re.search(pattern, msg_lower):
            logger.info(f"[CONTEXT-FILTER] Detected '{status_filter}' filter on previous results")

            # Get project_mapping from workflow state (from previous list_projects)
            prev_project_mapping = {}
            if workflow_state:
                prev_project_mapping = workflow_state.get('project_mapping', {}) or workflow_state.get('context', {}).get('project_mapping', {})

            if prev_project_mapping:
                # Get status sets from config
                from config_loader import get_schedulable_statuses_safe, get_scheduled_statuses_safe, get_completed_statuses

                if status_filter == 'schedulable':
                    target_statuses = {s.lower() for s in get_schedulable_statuses_safe()}
                elif status_filter == 'scheduled':
                    target_statuses = {s.lower() for s in get_scheduled_statuses_safe()}
                elif status_filter == 'completed':
                    try:
                        target_statuses = {s.lower() for s in get_completed_statuses()}
                    except:
                        target_statuses = {'completed', 'done', 'finished'}
                else:
                    target_statuses = set()

                # Filter the previous results
                filtered_projects = []
                filtered_mapping = {}
                for pid, info in prev_project_mapping.items():
                    proj_status = info.get('status', '').lower()
                    if proj_status in target_statuses:
                        filtered_projects.append({
                            'id': pid,
                            'category': info.get('category', ''),
                            'address': info.get('address', ''),
                            'status': info.get('status', '')
                        })
                        filtered_mapping[pid] = info

                logger.info(f"[CONTEXT-FILTER] Filtered {len(prev_project_mapping)} → {len(filtered_projects)} projects with status '{status_filter}'")

                # Format response
                response_body = {'projects': filtered_projects}
                response_text = format_lambda_response('list_projects', response_body, message, channel)

                # Update workflow state with filtered results
                if filtered_projects:
                    project_ids = [str(p['id']) for p in filtered_projects]
                    existing_state = state_manager.get_state(session_id) or {}
                    viewed_projects = existing_state.get('viewed_projects', [])

                    state_manager.save_state(session_id, {
                        'workflow_type': 'project_list',
                        'current_stage': f'filtered_by_{status_filter}',
                        'context': {
                            'project_ids': project_ids,
                            'project_mapping': filtered_mapping,
                            'customer_id': customer_id,
                            'previous_filter': status_filter
                        },
                        'viewed_projects': viewed_projects,
                        'project_mapping': filtered_mapping
                    })

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'scheduling',
                    'action': 'list_projects',
                    'agent_name': 'Intelligent Orchestrator (Context Filter)',
                    'direct_call': True,
                    'timing': timing,
                    'pf_http_status_code': 200
                }
            else:
                logger.info(f"[CONTEXT-FILTER] No previous project_mapping found, falling through to normal flow")
            break  # Only match first pattern

    # ========================================================================
    # STEP 0.5: Check for ORDINAL PROJECT REFERENCE (before classification)
    # This handles "last project", "first project", "2nd project" etc.
    # by directly resolving the ordinal to a project_id from the stored list
    # and fetching project details - bypassing Sonnet to avoid misinterpretation
    # ========================================================================
    ordinal_index = extract_ordinal_project_reference(message)
    if ordinal_index is not None:
        logger.info(f"[ORDINAL] Detected ordinal reference: index={ordinal_index}")

        # Get project_ids from workflow state (stored when projects were listed)
        # Handle None workflow_state (e.g., fresh SMS session without prior project list)
        project_ids = (workflow_state or {}).get('context', {}).get('project_ids', [])

        if project_ids:
            try:
                # Resolve ordinal index to project_id (supports negative indices)
                resolved_project_id = str(project_ids[ordinal_index])
                logger.info(f"[ORDINAL] Resolved index {ordinal_index} to project_id={resolved_project_id} from list of {len(project_ids)} projects")

                # ALL CHANNELS: Detect action words in message (schedule, reschedule, cancel)
                # If user says "schedule the first project", route to scheduling flow, NOT get_project_details
                # Works for voice, chat, and sms channels
                message_lower = message.lower()
                detected_action = None

                # Check for SCHEDULE action (book, schedule an appointment)
                if any(word in message_lower for word in ['schedule', 'book', 'set up', 'make an appointment', 'available dates']):
                    detected_action = 'schedule'
                    logger.info(f"[ORDINAL] Detected SCHEDULE action in ordinal reference (channel={channel})")
                # Check for reschedule action
                elif any(word in message_lower for word in ['reschedule', 'move', 'change the date', 'different date', 'another date', 'change my appointment']):
                    detected_action = 'reschedule'
                    logger.info(f"[ORDINAL] Detected RESCHEDULE action in ordinal reference (channel={channel})")
                # Check for cancel action
                elif any(word in message_lower for word in ['cancel', 'remove', 'delete', 'dont want', "don't want"]):
                    detected_action = 'cancel'
                    logger.info(f"[ORDINAL] Detected CANCEL action in ordinal reference (channel={channel})")

                # If action word detected, save context and fall through to classification
                # This routes to get_available_dates instead of get_project_details
                if detected_action:
                    # Initialize workflow_state if None
                    if workflow_state is None:
                        workflow_state = {'context': {}}
                    elif 'context' not in workflow_state:
                        workflow_state['context'] = {}
                    workflow_state['context']['resolved_project_id'] = resolved_project_id
                    workflow_state['context']['ordinal_action'] = detected_action
                    state_manager.save_state(session_id, workflow_state)
                    logger.info(f"[ORDINAL] Saved resolved_project_id={resolved_project_id} for {detected_action}, falling through to classification")
                # No action word detected - proceed with get_project_details (original behavior)

                # Check if we should skip get_project_details due to action word detection
                ordinal_action = (workflow_state or {}).get('context', {}).get('ordinal_action')
                if ordinal_action:
                    # Clear the action flag and fall through to classification
                    workflow_state['context'].pop('ordinal_action', None)
                    logger.info(f"[ORDINAL] Skipping get_project_details, routing to {ordinal_action} with project_id={resolved_project_id} (channel={channel})")
                    # Raise to break out of try block and fall through to classification
                    raise Exception(f"ORDINAL_ACTION_DETECTED:{ordinal_action}")

                # Call get_project_details directly (original behavior - no action word detected)
                ordinal_start = time.time()
                details_response = call_lambda_directly('get_project_details', {
                    'project_id': resolved_project_id,
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_bearer_token,
                    'from_phone': from_phone
                })
                timing['lambda_call'] = time.time() - ordinal_start

                # Extract response body
                response_data = details_response.get('response', {})
                func_response = response_data.get('functionResponse', {})
                body_wrapper = func_response.get('responseBody', {})
                text_body = body_wrapper.get('TEXT', {})
                body_str = text_body.get('body', '{}')

                if isinstance(body_str, str):
                    response_body = json.loads(body_str)
                else:
                    response_body = body_str

                # Generate response using format_lambda_response (same pattern as rest of codebase)
                project_data = response_body.get('project', response_body)

                # VOICE-ONLY: Fetch weather for scheduled projects
                if channel == 'voice' and project_data.get('scheduledDate'):
                    try:
                        # Get city from project address
                        address_info = project_data.get('address', {})
                        city = address_info.get('city', '')
                        state = address_info.get('state', '')
                        scheduled_date = project_data.get('scheduledDate', '')

                        if city and scheduled_date:
                            location = f"{city}, {state}" if state else city
                            logger.info(f"[VOICE-WEATHER] Fetching weather for {location} on {scheduled_date}")

                            weather_response = call_lambda_directly('get_weather', {
                                'location': location,
                                'date': scheduled_date,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            })

                            # Extract weather data
                            weather_data = weather_response.get('response', {}).get('functionResponse', {}).get('responseBody', {}).get('TEXT', {}).get('body', '{}')
                            if isinstance(weather_data, str):
                                weather_data = json.loads(weather_data)

                            # Add weather to project data for voice formatting
                            if weather_data.get('weather'):
                                project_data['weather'] = weather_data.get('weather', {})
                                project_data['weather_location'] = location
                                response_body['project'] = project_data
                                logger.info(f"[VOICE-WEATHER] Added weather data: {weather_data.get('weather', {}).get('condition', 'N/A')}")
                    except Exception as weather_err:
                        logger.warning(f"[VOICE-WEATHER] Failed to fetch weather (non-critical): {weather_err}")
                        # Continue without weather - don't fail the request

                response_gen_start = time.time()

                # VOICE-SPECIFIC: Use voice formatter directly for comprehensive details
                # (Router strips JSON before format_for_voice, causing truncation)
                if channel == 'voice':
                    # Direct voice formatting - includes all details (status, technician, address, weather)
                    voice_text = _format_project_details_for_voice(response_body)
                    # Add voice engagement (opener and follow-up question)
                    voice_text = _add_voice_opener(voice_text, 'information')
                    voice_text = _add_voice_followup(voice_text, 'information')
                    response_text = voice_text
                    logger.info(f"[ORDINAL-VOICE] Used direct voice formatting ({len(response_text)} chars)")
                else:
                    # Chat/SMS: Use standard formatting with JSON
                    response_text = format_lambda_response('get_project_details', response_body, message, channel)

                timing['response_generation'] = time.time() - response_gen_start

                # Track this project in viewed_projects history
                try:
                    address_info = project_data.get('address', {})
                    state_manager.add_viewed_project(session_id, {
                        'project_id': resolved_project_id,
                        'category': project_data.get('category', ''),
                        'status': project_data.get('status', ''),
                        'city': address_info.get('city', ''),
                        'state': address_info.get('state', ''),
                        'address': address_info.get('address', '')
                    })
                    logger.info(f"[ORDINAL] Added project {resolved_project_id} to viewed_projects history")
                except Exception as track_err:
                    logger.warning(f"[ORDINAL] Failed to track viewed project (non-critical): {track_err}")

                # CRITICAL: Save current project_id to workflow_state for pronoun resolution
                # When user says "reschedule it", "it" should refer to this project
                try:
                    existing_state = workflow_state or {}
                    existing_mapping = existing_state.get('project_mapping', {}) or existing_state.get('context', {}).get('project_mapping', {})
                    state_manager.save_state(session_id, {
                        'workflow_type': 'project_details',
                        'current_stage': 'viewed_details',
                        'context': {
                            'project_id': resolved_project_id,  # CURRENT project for pronoun resolution
                            'category': project_data.get('category', ''),
                            'status': project_data.get('status', ''),
                            'project_mapping': existing_mapping
                        },
                        'project_mapping': existing_mapping
                    })
                    logger.info(f"[ORDINAL] Saved project_id {resolved_project_id} to workflow_state for pronoun resolution")
                except Exception as save_err:
                    logger.warning(f"[ORDINAL] Failed to save project_id to workflow_state: {save_err}")

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'information',
                    'action': 'get_project_details',
                    'agent_name': 'Intelligent Orchestrator (Ordinal Reference)',
                    'direct_call': True,
                    'timing': timing,
                    'channel': channel
                }

            except IndexError:
                logger.warning(f"[ORDINAL] Index {ordinal_index} out of range for {len(project_ids)} projects")
                # FALLBACK: If GPT-4o passed a project_id, use it directly
                # This handles the case where GPT-4o presented multiple projects but only passed one ID
                fallback_project_id = (workflow_state or {}).get('context', {}).get('project_id')
                if fallback_project_id and channel == 'voice':
                    logger.info(f"[ORDINAL] Using GPT-4o fallback project_id: {fallback_project_id}")
                    # Update context with resolved project_id and fall through to classification
                    if workflow_state is None:
                        workflow_state = {'context': {}}
                    elif 'context' not in workflow_state:
                        workflow_state['context'] = {}
                    workflow_state['context']['resolved_project_id'] = fallback_project_id
                    state_manager.save_state(session_id, workflow_state)
                # Fall through to normal classification
            except Exception as ordinal_err:
                # Check if this is our intentional action detection (not an error)
                if "ORDINAL_ACTION_DETECTED:" in str(ordinal_err):
                    action_type = str(ordinal_err).split(":")[-1]
                    logger.info(f"[ORDINAL] Falling through to classification for {action_type} action (channel={channel})")
                    # Fall through to normal classification (this is expected behavior)
                else:
                    logger.error(f"[ORDINAL] Error handling ordinal reference: {ordinal_err}")
                # Fall through to normal classification
        else:
            logger.info("[ORDINAL] No project_ids in workflow state, falling through to classification")

    # ========================================================================
    # Step 1: NLU CLASSIFICATION (Source of Truth for Action)
    # NLU is fast, deterministic, and usually correct
    # ========================================================================
    logger.info("[NLU] Step 1: NLU classification (action source of truth)")
    nlu_start = time.time()

    nlu_result = classify_intent_and_action(message, conversation_history)
    nlu_action = nlu_result.get('action')
    nlu_intent = nlu_result.get('intent', 'scheduling')
    nlu_params = nlu_result.get('params', {})

    timing['nlu_classification'] = time.time() - nlu_start
    logger.info(f"[NLU] Result: intent={nlu_intent}, action={nlu_action}, params={nlu_params}")

    # ========================================================================
    # Step 2: APPLY ACTION GUARDS - Rule-based validation
    # Guards can override NLU action for specific patterns
    # ========================================================================
    guard_context = {
        'workflow_state': workflow_state or {},
        'entities': nlu_params or {},
        'previous_action': workflow_state.get('context', {}).get('last_action') if workflow_state else None,
        'conversation_history': conversation_history
    }

    final_action, guard_reason = apply_guards(message, nlu_action, nlu_action, guard_context)

    if guard_reason:
        logger.info(f"[GUARD] Override: {nlu_action} → {final_action}")
    else:
        final_action = nlu_action

    # ========================================================================
    # Step 3: SONNET ENTITY ENRICHMENT (Only When Needed)
    # Sonnet ONLY extracts entities - it CANNOT change the action
    # ========================================================================
    enriched_entities = nlu_params.copy() if nlu_params else {}

    if final_action and needs_enrichment(final_action, enriched_entities):
        logger.info(f"[ENRICHER] Calling Sonnet for entity enrichment (action={final_action})")
        enricher_start = time.time()

        enricher_context = {
            'workflow_state': workflow_state or {},
            'available_dates': workflow_state.get('context', {}).get('available_dates', []) if workflow_state else [],
            'available_slots': workflow_state.get('context', {}).get('available_slots', []) if workflow_state else [],
        }

        sonnet_entities = enrich_entities(message, final_action, enricher_context)
        timing['entity_enrichment'] = time.time() - enricher_start

        # Merge Sonnet entities (Sonnet fills gaps, doesn't override NLU)
        for key, value in sonnet_entities.items():
            if key not in enriched_entities or enriched_entities[key] is None:
                enriched_entities[key] = value
                logger.info(f"[ENRICHER] Added entity: {key}={value}")
    else:
        logger.info(f"[ENRICHER] Skipped - already have needed entities")

    # Build classification object (compatible with existing code)
    classification = {
        'intent': nlu_intent,
        'action': final_action,
        'entities': enriched_entities,
        'reasoning': f"NLU: {nlu_result.get('_nlu_intent', 'unknown')} → {final_action}",
        'guard_applied': guard_reason,
        '_nlu_action': nlu_action,  # Original NLU action (for debugging)
    }

    timing['classification'] = time.time() - nlu_start

    # Log classification decision for debugging
    log_classification_decision(
        nlu_result={'action': nlu_action, 'confidence': 'high'},
        sonnet_result={'action': final_action, 'reasoning': 'Entity enrichment only'},
        final_action=final_action,
        guard_reason=guard_reason
    )

    # ========================================================================
    # HANDLE HELP/CAPABILITIES: Show user what they can do
    # ========================================================================
    if classification.get('action') == 'show_capabilities':
        logger.info("[HELP] User asked for help - showing capabilities")
        help_response = """I can help you with:

• **List your projects** - "show my projects"
• **Check project details** - "tell me about project 7751741" or "details for the first project"
• **Schedule appointments** - "schedule the first project"
• **Reschedule** - "reschedule my appointment"
• **Cancel** - "cancel my appointment"
• **Check weather** - "what's the weather?"
• **Check availability** - "what dates are available?"

You can also say "start over" at any time to reset.

What would you like to do?"""

        timing['total'] = time.time() - start_time
        return {
            'response': help_response,
            'intent': 'help',
            'action': 'show_capabilities',
            'agent_name': 'Intelligent Orchestrator (Help)',
            'direct_call': True,
            'timing': timing,
            'channel': channel
        }

    # ========================================================================
    # HANDLE START OVER: Clear all context and start fresh
    # ========================================================================
    if classification.get('action') == 'start_over':
        logger.info("[START_OVER] User wants to start fresh - clearing all state")
        state_manager.clear_state(session_id)

        start_over_response = "Okay, starting fresh. What would you like to do?"

        timing['total'] = time.time() - start_time
        return {
            'response': start_over_response,
            'intent': 'scheduling',
            'action': 'start_over',
            'agent_name': 'Intelligent Orchestrator (Start Over)',
            'direct_call': True,
            'timing': timing,
            'channel': channel
        }

    # ========================================================================
    # HANDLE CALENDAR INFO: What day is [date]?
    # Uses Python datetime for accurate day-of-week calculations
    # ========================================================================
    if classification.get('action') == 'calendar_info':
        logger.info("[CALENDAR-INFO] User asking about day of week")
        date_param = enriched_entities.get('date', '')
        calendar_response = handle_calendar_info(date_param, message)
        calendar_response['timing'] = timing
        calendar_response['timing']['total'] = time.time() - start_time
        calendar_response['channel'] = channel
        return calendar_response

    # HANDLE CONTEXT QUERIES: Answer from conversation history
    if classification.get('action') == 'context_query':
        query_type = classification.get('entities', {}).get('query_type', '')
        # Support multiple query_types (comma-separated or list)
        query_types = classification.get('entities', {}).get('query_types', [])
        if isinstance(query_types, str):
            query_types = [q.strip() for q in query_types.split(',') if q.strip()]
        if query_type and query_type not in query_types:
            query_types.insert(0, query_type)
        logger.info(f"[CONTEXT] Context query detected: query_type={query_type}, query_types={query_types}")

        # Extract project data from conversation history (pass classification for project reference)
        project_data = extract_project_data_from_history(conversation_history, classification)
        logger.info(f"[CONTEXT] Extracted project data: {project_data}")

        # VOICE-ONLY AUTO-FETCH: If no context in history but project_index specified, fetch projects automatically
        # This avoids asking "would you like me to look up project details?" and saves a round-trip on voice calls
        # Chat/SMS have conversation history with JSON responses, so they don't need this
        if not project_data and channel == 'voice':
            entities = classification.get('entities', {})
            project_index = entities.get('project_index')
            target_project_id = entities.get('project_id')

            if project_index is not None or target_project_id:
                logger.info(f"[VOICE-AUTOFETCH] No context in history but project reference found: index={project_index}, id={target_project_id}")
                logger.info(f"[VOICE-AUTOFETCH] Auto-fetching projects to answer context query...")

                try:
                    autofetch_start = time.time()

                    # Call list_projects to get all projects
                    list_response = call_lambda_directly('list_projects', {
                        'customer_id': customer_id,
                        'client_id': client_id,
                        'pf_bearer_token': pf_bearer_token,
                        'from_phone': from_phone
                    })

                    # Extract projects from response
                    list_data = list_response.get('response', {})
                    list_func = list_data.get('functionResponse', {})
                    list_body_wrapper = list_func.get('responseBody', {})
                    list_text = list_body_wrapper.get('TEXT', {})
                    list_body_str = list_text.get('body', '{}')

                    if isinstance(list_body_str, str):
                        list_body = json.loads(list_body_str)
                    else:
                        list_body = list_body_str

                    # Extract project data from fetched list
                    if 'projects' in list_body and isinstance(list_body['projects'], list):
                        fetched_projects = list_body['projects']
                        logger.info(f"[VOICE-AUTOFETCH] Fetched {len(fetched_projects)} projects in {time.time() - autofetch_start:.2f}s")

                        # Find target project by index or ID
                        target_proj = None
                        if target_project_id:
                            for p in fetched_projects:
                                if str(p.get('id')) == str(target_project_id):
                                    target_proj = p
                                    logger.info(f"[VOICE-AUTOFETCH] Found project by ID: {target_project_id}")
                                    break
                        elif project_index is not None and isinstance(project_index, int):
                            if 0 <= project_index < len(fetched_projects):
                                target_proj = fetched_projects[project_index]
                                logger.info(f"[VOICE-AUTOFETCH] Found project by index: {project_index} -> #{target_proj.get('id')}")

                        if target_proj:
                            # Build project_data from fetched project
                            project_data = {}

                            # Extract technician info
                            if target_proj.get('installer'):
                                inst = target_proj['installer']
                                if isinstance(inst, dict):
                                    project_data['technician_name'] = inst.get('name', '')
                                    project_data['technician_id'] = str(inst.get('id', ''))

                            # Extract scheduled date/time
                            if target_proj.get('scheduledDate'):
                                sched = target_proj['scheduledDate']
                                project_data['scheduled_date'] = sched
                                # Parse time from "11-29-2025 08:00 AM - 11-29-2025 09:00 AM" format
                                time_match = re.search(
                                    r'(\d{1,2}:\d{2}\s*(?:AM|PM))\s*-\s*\d{1,2}-\d{1,2}-\d{4}\s*(\d{1,2}:\d{2}\s*(?:AM|PM))',
                                    sched, re.IGNORECASE
                                )
                                if time_match:
                                    project_data['scheduled_time'] = f"{time_match.group(1)} - {time_match.group(2)}"

                            # Extract other fields
                            if target_proj.get('category'):
                                project_data['category'] = target_proj['category']
                            if target_proj.get('id'):
                                project_data['project_id'] = str(target_proj['id'])
                            if target_proj.get('address'):
                                addr = target_proj['address']
                                if isinstance(addr, dict):
                                    project_data['address'] = addr.get('fullAddress') or f"{addr.get('address1', '')}, {addr.get('city', '')}, {addr.get('state', '')} {addr.get('zipcode', '')}"
                                    project_data['city'] = addr.get('city', '')
                                    project_data['state'] = addr.get('state', '')
                                else:
                                    project_data['address'] = addr
                            if target_proj.get('status'):
                                project_data['status'] = target_proj['status']

                            logger.info(f"[VOICE-AUTOFETCH] Built project_data: {project_data}")

                            # Save project_ids AND project_mapping to workflow state for future queries
                            fetched_ids = [str(p.get('id', '')) for p in fetched_projects if p.get('id')]
                            # Build project_mapping for accurate category matching
                            # Also include projectNumber for Order Number -> Project ID resolution
                            fetched_mapping = {}
                            for p in fetched_projects:
                                pid = str(p.get('id', ''))
                                project_number = p.get('projectNumber', '')
                                if pid:
                                    fetched_mapping[pid] = {
                                        'category': p.get('category', ''),
                                        'address': p.get('address', ''),
                                        'status': p.get('status', ''),
                                        'projectNumber': project_number
                                    }
                                    # Also map by projectNumber for reverse lookup
                                    if project_number:
                                        fetched_mapping[project_number] = {
                                            'category': p.get('category', ''),
                                            'address': p.get('address', ''),
                                            'status': p.get('status', ''),
                                            'project_id': pid  # Internal project ID
                                        }
                            if fetched_ids:
                                state_manager.save_state(session_id, {
                                    'workflow_type': 'project_listing',
                                    'current_stage': 'listing_projects',
                                    'context': {
                                        'project_ids': fetched_ids,
                                        'project_mapping': fetched_mapping
                                    },
                                    'project_mapping': fetched_mapping  # Top-level for save_state()
                                })
                                logger.info(f"[VOICE-AUTOFETCH] Saved {len(fetched_ids)} project_ids and mapping to workflow state")

                            timing['autofetch'] = time.time() - autofetch_start

                except Exception as autofetch_err:
                    logger.error(f"[VOICE-AUTOFETCH] Auto-fetch failed: {autofetch_err}")
                    # Continue with None project_data - will ask user for context

        if project_data:
            # MULTI-FIELD QUERIES: Handle requests for multiple pieces of information
            # e.g., "give me technician name and appointment time for project X"
            if len(query_types) > 1:
                logger.info(f"[CONTEXT] Multi-field query detected: {query_types}")
                category = project_data.get('category', 'project')
                project_id = project_data.get('project_id', '')

                response = f"Here's the information for your **{category}** project"
                if project_id:
                    response += f" (#{project_id})"
                response += ":\n\n"

                for qt in query_types:
                    if qt == 'technician':
                        tech_name = project_data.get('technician_name', 'Not assigned yet')
                        if tech_name and tech_name != 'Not assigned yet':
                            response += f"**Technician:** {tech_name}\n"
                        else:
                            response += "**Technician:** Not yet assigned\n"

                    elif qt == 'appointment_time':
                        scheduled_date = project_data.get('scheduled_date', '')
                        scheduled_time = project_data.get('scheduled_time', '')
                        if scheduled_date:
                            formatted_date = format_date_natural(scheduled_date)
                            response += f"**Scheduled Date:** {formatted_date}\n"
                            if scheduled_time and scheduled_time not in formatted_date:
                                response += f"**Appointment Time:** {scheduled_time}\n"
                        else:
                            response += "**Scheduled:** Not yet scheduled\n"

                    elif qt == 'address':
                        address = project_data.get('address', '')
                        if address:
                            response += f"**Address:** {address}\n"

                    elif qt == 'category':
                        response += f"**Category:** {category}\n"

                    elif qt == 'status':
                        status = project_data.get('status', '')
                        if status:
                            response += f"**Status:** {status}\n"

                response += "\nIs there anything else you'd like to know?"

                timing['total'] = time.time() - start_time
                return {
                    'response': response,
                    'intent': 'information',
                    'action': 'context_query',
                    'agent_name': 'Intelligent Orchestrator (Multi-Field)',
                    'direct_call': True,
                    'timing': timing
                }

            if query_type == 'technician':
                tech_name = project_data.get('technician_name', 'Not assigned yet')
                tech_id = project_data.get('technician_id', '')
                category = project_data.get('category', 'project')
                project_id = project_data.get('project_id', '')
                scheduled_date = project_data.get('scheduled_date', '')
                scheduled_time = project_data.get('scheduled_time', '')

                if tech_name and tech_name != 'Not assigned yet':
                    # Build natural, conversational response (no IDs for customers)
                    response = f"**{tech_name}** is the technician assigned to your {category} project"
                    if project_id:
                        response += f" (#{project_id})"
                    response += "."
                    if scheduled_date:
                        # Format date naturally
                        formatted_date = format_date_natural(scheduled_date)
                        response += f" They're scheduled to arrive on **{formatted_date}**"
                        if scheduled_time and scheduled_time not in formatted_date:
                            response += f" at {scheduled_time}"
                        response += "."
                else:
                    response = f"A technician hasn't been assigned to your {category} project yet. Once your appointment is scheduled, you'll be able to see who's assigned."

            elif query_type == 'appointment_time':
                scheduled_date = project_data.get('scheduled_date', '')
                scheduled_time = project_data.get('scheduled_time', '')
                category = project_data.get('category', 'project')
                project_id = project_data.get('project_id', '')

                if scheduled_date or scheduled_time:
                    response = f"Your {category} project"
                    if project_id:
                        response += f" (#{project_id})"
                    response += " is scheduled for"
                    if scheduled_date:
                        # Format date naturally
                        formatted_date = format_date_natural(scheduled_date)
                        response += f" **{formatted_date}**"
                    if scheduled_time and scheduled_time not in (scheduled_date or ''):
                        response += f" at **{scheduled_time}**"
                    response += "."
                else:
                    response = f"Your {category} project doesn't have a scheduled appointment yet. Would you like to schedule one now?"

            elif query_type == 'address':
                address = project_data.get('address', '')
                category = project_data.get('category', 'project')
                project_id = project_data.get('project_id', '')

                if address:
                    response = f"The installation address for your {category} project"
                    if project_id:
                        response += f" (#{project_id})"
                    response += f" is **{address}**."
                else:
                    response = "I don't have the address details in our current conversation. Would you like me to look up your project details?"

            elif query_type == 'category':
                # CATEGORY QUERY - "what is the category for project X"
                category = project_data.get('category', '')
                project_id = project_data.get('project_id', '')
                status = project_data.get('status', '')
                project_type = project_data.get('project_type', 'Call Back')

                if category:
                    response = f"Project #{project_id} is a **{category}** project"
                    if status:
                        response += f" with status **{status}**"
                    response += "."
                else:
                    response = f"I couldn't find the category information for project #{project_id}. Would you like me to look up the full project details?"

            elif query_type in ['status', 'general', 'update', 'info', 'details', 'happening', 'progress']:
                # COMPREHENSIVE STATUS HANDLER - "whats happening with my job", "status of my project", etc.
                category = project_data.get('category', 'project')
                project_id = project_data.get('project_id', '')
                status = project_data.get('status', '')
                scheduled_date = project_data.get('scheduled_date', '')
                scheduled_time = project_data.get('scheduled_time', '')
                tech_name = project_data.get('technician_name', '')
                address = project_data.get('address', '')

                # Build comprehensive status response
                response = f"Here's the status of your **{category}** project"
                if project_id:
                    response += f" (#{project_id})"
                response += ":\n\n"

                # Status
                if status:
                    response += f"**Status:** {status}\n"

                # Scheduled date/time
                if scheduled_date:
                    formatted_date = format_date_natural(scheduled_date)
                    response += f"**Scheduled:** {formatted_date}"
                    if scheduled_time and scheduled_time not in formatted_date:
                        response += f" at {scheduled_time}"
                    response += "\n"
                else:
                    response += "**Scheduled:** Not yet scheduled\n"

                # Technician
                if tech_name and tech_name != 'Not assigned yet':
                    response += f"**Technician:** {tech_name}\n"
                else:
                    response += "**Technician:** Not yet assigned\n"

                # Address
                if address:
                    response += f"**Location:** {address}\n"

                # Helpful prompt
                if not scheduled_date:
                    response += "\nWould you like to schedule an appointment for this project?"
                else:
                    response += "\nIs there anything else you'd like to know about this project?"

            else:
                # SMART FALLBACK: If we have project_data but unknown query_type, show a summary anyway
                # This is better than saying "I'm not sure what you're looking for"
                logger.info(f"[CONTEXT] Unknown query_type '{query_type}', using smart fallback with available project_data")

                category = project_data.get('category', 'project')
                project_id = project_data.get('project_id', '')
                status = project_data.get('status', '')
                scheduled_date = project_data.get('scheduled_date', '')
                tech_name = project_data.get('technician_name', '')

                response = f"Here's what I know about your **{category}** project"
                if project_id:
                    response += f" (#{project_id})"
                response += ":\n\n"

                info_added = False
                if status:
                    response += f"**Status:** {status}\n"
                    info_added = True
                if scheduled_date:
                    formatted_date = format_date_natural(scheduled_date)
                    response += f"**Scheduled:** {formatted_date}\n"
                    info_added = True
                if tech_name and tech_name != 'Not assigned yet':
                    response += f"**Technician:** {tech_name}\n"
                    info_added = True

                if not info_added:
                    response = f"I found your **{category}** project"
                    if project_id:
                        response += f" (#{project_id})"
                    response += ", but I don't have detailed status information. Would you like me to get the full project details?"
                else:
                    response += "\nWhat specific information would you like to know? I can tell you about the technician, scheduled time, or address."

        else:
            # NO PROJECT DATA FALLBACK: Try to be helpful even when we can't find project info
            logger.info(f"[CONTEXT] No project_data found, offering helpful alternatives")
            response = "I couldn't find the project details you're asking about. Here's what I can do:\n\n"
            response += "1. **List your projects** - Just say 'show my projects'\n"
            response += "2. **Get specific project details** - Say 'details for project' followed by the project number\n"
            response += "3. **Schedule an appointment** - Say 'schedule' followed by the project\n\n"
            response += "Which would you like to do?"

        timing['total'] = time.time() - start_time
        return {
            'response': response,
            'intent': 'information',
            'action': 'context_query',
            'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
            'direct_call': True,
            'timing': timing
        }

    # HANDLE WEATHER QUERIES WITH PROJECT REFERENCE: Extract location from project and fetch weather
    if classification.get('action') == 'get_weather':
        entities = classification.get('entities', {})
        project_index = entities.get('project_index')
        project_id = entities.get('project_id')
        location = entities.get('location')  # May already be extracted by Sonnet enricher

        # If no location, try to get it from workflow_state context or project_mapping
        # This handles "what's the weather" after user viewed a project or is in scheduling flow
        logger.info(f"[WEATHER] location={location}, workflow_state exists={workflow_state is not None}")
        if not location and workflow_state:
            context = workflow_state.get('context', {})
            # Check both context-level AND top-level project_mapping (context switch preserves at top level)
            project_mapping = context.get('project_mapping', {}) or workflow_state.get('project_mapping', {})
            logger.info(f"[WEATHER] Fallback: current_project_id={context.get('project_id')}, city={context.get('city')}, state={context.get('state')}, project_mapping keys={list(project_mapping.keys())[:3]}")

            # FIRST: Check if city/state are directly in context (saved during scheduling workflow)
            context_city = context.get('city')
            context_state = context.get('state')
            if context_city and context_state:
                location = f"{context_city}, {context_state}"
                project_id = context.get('project_id')
                logger.info(f"[WEATHER] Got location from context city/state: {location}")

            # SECOND: Try project_mapping if still no location
            if not location:
                current_project_id = context.get('project_id')
                if current_project_id and current_project_id in project_mapping:
                    proj_info = project_mapping[current_project_id]
                    address = proj_info.get('address', '')
                    if address:
                        # Handle dict-format address
                        if isinstance(address, dict):
                            city = address.get('city', '')
                            state = address.get('state', '')
                            if city and state:
                                location = f"{city}, {state}"
                                project_id = current_project_id
                                logger.info(f"[WEATHER] Got location from project_mapping dict: {location}")
                        else:
                            # Parse city, state from string address
                            addr_match = re.search(r',\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*\d*', address)
                            if addr_match:
                                location = f"{addr_match.group(1).strip()}, {addr_match.group(2)}"
                                project_id = current_project_id
                                logger.info(f"[WEATHER] Got location from current project #{current_project_id}: {location}")

            # THIRD: Try the most recently listed project as fallback
            if not location and project_mapping:
                first_pid = list(project_mapping.keys())[0]
                proj_info = project_mapping[first_pid]
                address = proj_info.get('address', '')
                if address:
                    # Handle dict-format address
                    if isinstance(address, dict):
                        city = address.get('city', '')
                        state = address.get('state', '')
                        if city and state:
                            location = f"{city}, {state}"
                            project_id = first_pid
                            logger.info(f"[WEATHER] Got location from first project dict: {location}")
                    else:
                        addr_match = re.search(r',\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*\d*', address)
                        if addr_match:
                            location = f"{addr_match.group(1).strip()}, {addr_match.group(2)}"
                            project_id = first_pid
                            logger.info(f"[WEATHER] Got location from first project #{first_pid}: {location}")

        # AUTO-FETCH: If project ID mentioned in message, fetch THAT project's details
        # This takes priority over enricher location (which may be from previous context)
        # Extract project ID from message (PF ID like 21083_09PF05VD_xxx or internal 7-digit or short like 9000407_1_1)
        pf_id_match = re.search(r'\b(\d+_[A-Za-z0-9]+_\d+(?:_\d+)*)\b', message)
        short_id_match = re.search(r'\b(\d{7}_\d+(?:_\d+)*)\b', message)  # e.g., 9000407_1_1
        internal_id_match = re.search(r'\b(\d{7})\b', message)

        msg_project_id = None
        if pf_id_match:
            msg_project_id = pf_id_match.group(1)
        elif short_id_match:
            msg_project_id = short_id_match.group(1)
        elif internal_id_match:
            msg_project_id = internal_id_match.group(1)

        # If project ID in message, always auto-fetch that project's location (override enricher)
        if msg_project_id:
            logger.info(f"[WEATHER] Project ID in message: {msg_project_id}, will auto-fetch its location")
            # Clear enricher location to force fetch
            location = None

        if not location and msg_project_id:
            logger.info(f"[WEATHER] Auto-fetching project details for: {msg_project_id}")
            try:
                # First resolve the project ID through list_projects
                list_response = call_lambda_directly('list_projects', {
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_bearer_token,
                    'from_phone': from_phone
                })

                list_data = list_response.get('response', {})
                list_func = list_data.get('functionResponse', {})
                list_body_wrapper = list_func.get('responseBody', {})
                list_text = list_body_wrapper.get('TEXT', {})
                list_body_str = list_text.get('body', '{}')

                if isinstance(list_body_str, str):
                    list_body = json.loads(list_body_str)
                else:
                    list_body = list_body_str

                # Find the project and get its internal ID
                projects = list_body.get('projects', [])
                resolved_project_id = None
                project_address = None
                project_category = None
                project_scheduled_date = None

                for proj in projects:
                    pf_id = proj.get('projectNumber', '')
                    internal_id = str(proj.get('projectId', '') or proj.get('id', ''))

                    if msg_project_id == pf_id or msg_project_id == internal_id:
                        resolved_project_id = internal_id
                        project_address = proj.get('address', '')
                        project_category = proj.get('category', '')
                        project_scheduled_date = proj.get('scheduledDate', '')
                        logger.info(f"[WEATHER] Found project: internal_id={resolved_project_id}, address={project_address}, scheduledDate={project_scheduled_date}")
                        break

                if project_address:
                    # Handle address as dict or string
                    if isinstance(project_address, dict):
                        # Address is a dict like {'address1': '...', 'city': 'Minneapolis', 'state': 'MN', 'zipcode': '55415'}
                        city = project_address.get('city', '')
                        state = project_address.get('state', '')
                        if city and state:
                            location = f"{city}, {state}"
                            project_id = resolved_project_id
                            logger.info(f"[WEATHER] Auto-fetched location from dict: {location} for project #{resolved_project_id}")
                    else:
                        # Address is a string like "123 Main St, Minneapolis, MN 55401"
                        addr_match = re.search(r',\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*\d*', project_address)
                        if addr_match:
                            location = f"{addr_match.group(1).strip()}, {addr_match.group(2)}"
                            project_id = resolved_project_id
                            logger.info(f"[WEATHER] Auto-fetched location from string: {location} for project #{resolved_project_id}")

                    # Store in classification for context (applies to both dict and string addresses)
                    if location and resolved_project_id:
                        if 'entities' not in classification:
                            classification['entities'] = {}
                        classification['entities']['project_id'] = resolved_project_id
                        classification['entities']['project_category'] = project_category
                        if project_scheduled_date:
                            classification['entities']['scheduled_date'] = project_scheduled_date
                            logger.info(f"[WEATHER] Project has scheduled date: {project_scheduled_date}")

            except Exception as fetch_err:
                logger.warning(f"[WEATHER] Auto-fetch project details failed: {fetch_err}")

        # If we have a project reference but no location, extract from conversation history
        if (project_index is not None or project_id) and not location:
            logger.info(f"[WEATHER] Weather query with project reference: index={project_index}, id={project_id}")

            # Extract project data from conversation history (pass classification for project reference)
            project_data = extract_project_data_from_history(conversation_history, classification)

            if project_data:
                # Get location from project address
                address = project_data.get('address', '')
                if address:
                    # Parse city, state from address like "123 Main St, Minneapolis, MN 55401"
                    # Try to extract "City, ST" pattern
                    addr_match = re.search(r',\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*\d*', address)
                    if addr_match:
                        location = f"{addr_match.group(1).strip()}, {addr_match.group(2)}"
                        logger.info(f"[WEATHER] Extracted location from address: {location}")

                # Also try to get city/state directly from extraction
                if not location:
                    city = project_data.get('city', '')
                    state = project_data.get('state', '')
                    if city and state:
                        location = f"{city}, {state}"
                        logger.info(f"[WEATHER] Built location from city/state: {location}")

        if location:
            # Determine target date for weather forecast
            # Priority: user-specified date > workflow context date > scheduled date > current date + 7 days
            from datetime import datetime, timedelta
            target_date = None
            entities = classification.get('entities', {})
            user_date = entities.get('date')  # Date extracted from user message by Sonnet
            scheduled_date = entities.get('scheduled_date', '')

            # Get date from workflow context (e.g., when viewing time slots for a specific date)
            context_date = None
            if workflow_state:
                context = workflow_state.get('context', {})
                context_date = context.get('date')
                if context_date:
                    logger.info(f"[WEATHER] Found date in workflow context: {context_date}")

            if user_date:
                # Priority 1: User specified a date in their message
                target_date = user_date
                logger.info(f"[WEATHER] Using user-specified date: {target_date}")
            elif context_date:
                # Priority 2: Use date from workflow context (viewing time slots for this date)
                target_date = context_date
                logger.info(f"[WEATHER] Using workflow context date: {target_date}")
            elif scheduled_date:
                # Priority 3: Use project's scheduled date
                # Parse various date formats to YYYY-MM-DD
                try:
                    # Try MM-DD-YYYY HH:MM AM/PM format (e.g., "01-07-2026 08:00 AM")
                    if ' ' in scheduled_date:
                        date_part = scheduled_date.split(' ')[0]
                    else:
                        date_part = scheduled_date

                    # Try different formats
                    for fmt in ['%m-%d-%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%Y/%m/%d']:
                        try:
                            parsed = datetime.strptime(date_part, fmt)
                            target_date = parsed.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue

                    if not target_date:
                        target_date = scheduled_date  # Fallback to original

                    logger.info(f"[WEATHER] Using project scheduled date: {scheduled_date} -> {target_date}")
                except Exception as date_err:
                    logger.warning(f"[WEATHER] Failed to parse scheduled date: {scheduled_date}, error: {date_err}")
                    target_date = scheduled_date
            else:
                # Priority 4: No target date - show 5-day forecast from today (like chatSlots)
                # Don't set target_date so we get the full forecast
                target_date = None
                logger.info(f"[WEATHER] No date found, will show 5-day forecast from today")

            logger.info(f"[WEATHER] Fetching weather for location: {location}, date: {target_date}")

            try:
                weather_start = time.time()
                weather_params = {
                    'location': location,
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_bearer_token
                }
                if target_date:
                    weather_params['date'] = target_date

                weather_response = call_lambda_directly('get_weather', weather_params)
                timing['weather_call'] = time.time() - weather_start

                # Extract weather data from Lambda response
                w_data = weather_response.get('response', {})
                w_func = w_data.get('functionResponse', {})
                w_body_wrapper = w_func.get('responseBody', {})
                w_text = w_body_wrapper.get('TEXT', {})
                w_body_str = w_text.get('body', '{}')

                if isinstance(w_body_str, str):
                    weather_body = json.loads(w_body_str)
                else:
                    weather_body = w_body_str

                # Format the weather response (format_lambda_response already imported at top)
                weather_text = format_lambda_response('get_weather', weather_body, message, channel)

                # Add project context if available
                project_data_for_ctx = extract_project_data_from_history(conversation_history, classification)
                if project_data_for_ctx:
                    category = project_data_for_ctx.get('category', '')
                    proj_id = project_data_for_ctx.get('project_id', '')
                    if category and proj_id:
                        weather_text = f"Here's the weather forecast for your **{category}** project (#{proj_id}) in {location}:\n\n{weather_text}"
                    elif category:
                        weather_text = f"Here's the weather forecast for your **{category}** project in {location}:\n\n{weather_text}"

                timing['total'] = time.time() - start_time
                return {
                    'response': weather_text,
                    'intent': 'information',
                    'action': 'get_weather',
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing
                }

            except Exception as weather_err:
                logger.error(f"Weather fetch failed: {weather_err}")
                response = f"I couldn't fetch the weather for {location} right now. Please try again in a moment."

                timing['total'] = time.time() - start_time
                return {
                    'response': response,
                    'intent': 'information',
                    'action': 'get_weather',
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing
                }
        else:
            logger.warning("[WEATHER] Could not determine location for weather query")
            # Return helpful prompt asking for location instead of falling through
            timing['total'] = time.time() - start_time
            return {
                'response': "I'd be happy to check the weather! Which city or project would you like the forecast for?",
                'intent': 'information',
                'action': 'get_weather',
                'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                'direct_call': True,
                'needs_input': True,
                'timing': timing
            }

    # HANDLE CANCEL CONFIRMATION (User says "yes" after seeing project details for cancel)
    if workflow_state and workflow_state.get('current_stage') == 'awaiting_cancel_confirmation':
        user_lower = message.lower().strip()
        affirmative_responses = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'confirm', 'do it', 'go ahead', 'proceed', 'cancel it', 'yes please']
        negative_responses = ['no', 'nope', 'nah', 'cancel', 'never mind', 'nevermind', 'stop', 'dont', "don't", 'abort']

        if any(affirm in user_lower for affirm in affirmative_responses):
            logger.info("[CANCEL] User confirmed cancellation, proceeding with actual cancel")
            cancel_context = workflow_state.get('context', {})
            project_id = cancel_context.get('project_id')

            if project_id:
                try:
                    # Call cancel_appointment with confirmed=True
                    cancel_response = call_lambda_directly('cancel_appointment', {
                        'project_id': project_id,
                        'confirmed': 'true',  # This triggers the actual cancellation
                        'customer_id': customer_id,
                        'client_id': client_id,
                        'pf_bearer_token': pf_bearer_token
                    })

                    # Extract response
                    cancel_data = cancel_response.get('response', {})
                    cancel_func = cancel_data.get('functionResponse', {})
                    cancel_body_wrapper = cancel_func.get('responseBody', {})
                    cancel_text = cancel_body_wrapper.get('TEXT', {})
                    cancel_body_str = cancel_text.get('body', '{}')

                    if isinstance(cancel_body_str, str):
                        cancel_body = json.loads(cancel_body_str)
                    else:
                        cancel_body = cancel_body_str

                    # Format response
                    formatted_cancel = format_lambda_response('cancel_appointment', cancel_body, message, channel)

                    # VOICE ENHANCEMENT: Save action to context before clearing state
                    if channel == 'voice':
                        project_name = cancel_context.get('category', 'project')
                        save_action_to_context(
                            state_manager, session_id,
                            action='cancel_appointment',
                            result='success',
                            project_id=project_id,
                            project_name=project_name
                        )

                    # Reset workflow state (preserves memory)
                    state_manager.reset_workflow_state(session_id)
                    logger.info("[CANCEL] Cancellation complete, workflow state reset (memory preserved)")

                    timing['total'] = time.time() - start_time
                    return {
                        'response': formatted_cancel,
                        'intent': 'scheduling',
                        'action': 'cancel_appointment',
                        'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                        'direct_call': True,
                        'timing': timing
                    }

                except Exception as cancel_err:
                    logger.error(f"[CANCEL] Cancellation failed: {cancel_err}")
                    state_manager.clear_state(session_id)
                    timing['total'] = time.time() - start_time
                    return {
                        'response': f"I encountered an error while cancelling the appointment: {str(cancel_err)}. Please try again.",
                        'intent': 'scheduling',
                        'action': 'cancel_appointment',
                        'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                        'direct_call': True,
                        'timing': timing
                    }

        elif any(neg in user_lower for neg in negative_responses):
            logger.info("[CANCEL] User declined cancellation")
            state_manager.reset_workflow_state(session_id)
            timing['total'] = time.time() - start_time
            return {
                'response': "No problem, I've cancelled the cancellation request. Your appointment remains scheduled. Is there anything else I can help with?",
                'intent': 'scheduling',
                'action': 'cancel_appointment_declined',
                'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                'direct_call': True,
                'timing': timing
            }

    # HANDLE WORKFLOW DEFERRAL/ABANDONMENT
    if classification.get('action') in ['defer_workflow', 'abandon_workflow']:
        action_type = classification.get('action')
        logger.info(f"[WORKFLOW] Workflow control detected: {action_type}")

        # Get current workflow context for personalized response
        workflow_context = workflow_state.get('context', {}) if workflow_state else {}
        project_id = workflow_context.get('project_id', '')
        category = workflow_context.get('category', 'project')

        # Reset workflow state (preserves memory)
        state_manager.reset_workflow_state(session_id)
        logger.info(f"[WORKFLOW] Workflow state reset for session {session_id} (memory preserved)")

        if action_type == 'defer_workflow':
            response = "No problem! I've put the scheduling on hold for now."
            if project_id:
                response += f" When you're ready to schedule your {category} project (#{project_id}), just let me know."
            else:
                response += " When you're ready to continue, just let me know."
            response += " I'll be here to help."
        else:  # abandon_workflow
            response = "No problem, I've cancelled the scheduling."
            if project_id:
                response += f" If you'd like to schedule your {category} project (#{project_id}) later, just ask."
            response += " Let me know if there's anything else I can help with!"

        timing['total'] = time.time() - start_time
        return {
            'response': response,
            'intent': 'scheduling',
            'action': action_type,
            'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
            'direct_call': True,
            'timing': timing
        }

    # ========================================================================
    # CATEGORY-TO-PROJECT_ID RESOLVER
    # If classification has a category-based search_criteria but no project_id,
    # resolve it using project_mapping in workflow_state BEFORE decision function
    # This prevents the decision function from falling back to list_projects
    # ========================================================================
    entities = classification.get('entities', {})
    search_criteria = entities.get('search_criteria', {})
    classified_action = classification.get('action', '')

    # Check if we need to resolve category to project_id
    # Category can be in entities.search_criteria.category OR entities.category (Sonnet varies)
    category_to_resolve = search_criteria.get('category') or entities.get('category')

    # VALIDATION: If both project_id and category are present, verify they match
    # This catches cases where Sonnet hallucinates wrong project_id for a category
    needs_category_resolution = False
    if (classified_action in ['get_project_details', 'get_available_dates', 'schedule_project', 'reschedule_appointment', 'cancel_appointment']
        and category_to_resolve):

        sonnet_project_id = entities.get('project_id')

        if not sonnet_project_id:
            # No project_id, need to resolve from category
            needs_category_resolution = True
        else:
            # project_id exists - VALIDATE it matches the category
            project_mapping = {}
            if workflow_state:
                project_mapping = workflow_state.get('project_mapping', {}) or workflow_state.get('context', {}).get('project_mapping', {})

            if project_mapping and sonnet_project_id in project_mapping:
                actual_category = project_mapping[sonnet_project_id].get('category', '').lower().strip()
                requested_category = category_to_resolve.lower().strip()

                # Check if categories match (allow partial match)
                if requested_category not in actual_category and actual_category not in requested_category:
                    logger.warning(f"[CATEGORY-MISMATCH] Sonnet returned project_id={sonnet_project_id} (category={actual_category}) but user asked for '{requested_category}'")
                    logger.info(f"[CATEGORY-MISMATCH] Discarding mismatched project_id, will re-resolve from category")
                    # Remove the wrong project_id so we re-resolve below
                    entities.pop('project_id', None)
                    needs_category_resolution = True
                else:
                    logger.info(f"[CATEGORY-MATCH] Validated project_id={sonnet_project_id} matches category '{requested_category}'")

    if needs_category_resolution:

        search_category = category_to_resolve.lower().strip()
        logger.info(f"[CATEGORY-RESOLVE] Need to resolve category '{search_category}' to project_id")

        # Get project_mapping from workflow_state
        # Check both top level (after context switch) AND inside context (normal flow)
        project_mapping = {}
        if workflow_state:
            project_mapping = workflow_state.get('project_mapping', {}) or workflow_state.get('context', {}).get('project_mapping', {})

        if project_mapping:
            # Find matching project by category (case-insensitive, partial match)
            # PRIORITY: Schedulable projects first, then any matching project
            schedulable_statuses = ['new', 'ready to schedule']
            resolved_project_id = None
            fallback_project_id = None  # Non-schedulable match for error message

            for pid, info in project_mapping.items():
                cat = info.get('category', '').lower().strip()
                status = info.get('status', '').lower().strip()
                # Support partial matching: "kitchen" matches "Kitchen Sink", "storm door" matches "Storm Door"
                if search_category in cat or cat in search_category:
                    if status in schedulable_statuses:
                        resolved_project_id = pid
                        logger.info(f"[CATEGORY-RESOLVE] Matched '{search_category}' to SCHEDULABLE project #{pid} (status: {status})")
                        break
                    elif not fallback_project_id:
                        fallback_project_id = pid
                        logger.info(f"[CATEGORY-RESOLVE] Found non-schedulable '{search_category}' project #{pid} (status: {status}) - keeping as fallback")

            # If no schedulable match, use fallback (will trigger helpful error later)
            if not resolved_project_id and fallback_project_id:
                resolved_project_id = fallback_project_id
                logger.info(f"[CATEGORY-RESOLVE] No schedulable match, using fallback project #{fallback_project_id}")

            if resolved_project_id:
                # Update classification with resolved project_id
                if 'entities' not in classification:
                    classification['entities'] = {}
                classification['entities']['project_id'] = resolved_project_id
                logger.info(f"[CATEGORY-RESOLVE] Updated classification with project_id={resolved_project_id}")
            else:
                logger.warning(f"[CATEGORY-RESOLVE] Could not find project matching category '{search_category}' in mapping: {list(project_mapping.keys())}")
        else:
            # No project_mapping in workflow_state - fetch projects to resolve category
            logger.info(f"[CATEGORY-RESOLVE] No project_mapping in workflow_state - fetching projects to resolve category '{search_category}'")
            try:
                # Fetch projects to build project_mapping
                list_response = call_lambda_directly('list_projects', {
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_bearer_token,
                    'from_phone': from_phone
                })

                # Parse Bedrock agent format response (response.functionResponse.responseBody.TEXT.body)
                list_data = list_response.get('response', {})
                list_func = list_data.get('functionResponse', {})
                list_body_wrapper = list_func.get('responseBody', {})
                list_text = list_body_wrapper.get('TEXT', {})
                list_body_str = list_text.get('body', '{}')

                if isinstance(list_body_str, str):
                    projects_data = json.loads(list_body_str)
                else:
                    projects_data = list_body_str

                projects = projects_data.get('projects', [])
                if projects:
                    # Build project_mapping from fetched projects
                    # IMPORTANT: projectNumber is what users see (Order Number), id is internal
                    fetched_mapping = {}
                    for p in projects:
                        pid = str(p.get('id', ''))
                        project_number = p.get('projectNumber', '')
                        if pid:
                            fetched_mapping[pid] = {
                                'category': p.get('category', ''),
                                'address': p.get('address', ''),
                                'status': p.get('status', ''),
                                'projectNumber': project_number  # Order Number for display
                            }
                            # Also map by projectNumber for reverse lookup (Order Number -> Project ID)
                            if project_number:
                                fetched_mapping[project_number] = {
                                    'category': p.get('category', ''),
                                    'project_id': pid  # Internal project ID for API calls
                                }

                    logger.info(f"[CATEGORY-RESOLVE] Fetched {len(projects)} projects, searching for '{search_category}'")

                    # Now resolve category from fetched projects
                    # PRIORITY: Schedulable projects first, then any matching project
                    schedulable_statuses = ['new', 'ready to schedule']
                    resolved_project_id = None
                    fallback_project_id = None  # Non-schedulable match for error message

                    for pid, info in fetched_mapping.items():
                        cat = info.get('category', '').lower().strip()
                        status = info.get('status', '').lower().strip()

                        if search_category in cat or cat in search_category:
                            # Check if schedulable
                            if status in schedulable_statuses:
                                resolved_project_id = pid
                                logger.info(f"[CATEGORY-RESOLVE] Matched '{search_category}' to SCHEDULABLE project #{pid} (status: {status})")
                                break
                            elif not fallback_project_id:
                                # Keep first non-schedulable match as fallback
                                fallback_project_id = pid
                                logger.info(f"[CATEGORY-RESOLVE] Found non-schedulable '{search_category}' project #{pid} (status: {status}) - keeping as fallback")

                    # If no schedulable match, use fallback (will trigger helpful error later)
                    if not resolved_project_id and fallback_project_id:
                        resolved_project_id = fallback_project_id
                        logger.info(f"[CATEGORY-RESOLVE] No schedulable match, using fallback project #{fallback_project_id}")

                    if resolved_project_id:
                        # Update classification with resolved project_id
                        if 'entities' not in classification:
                            classification['entities'] = {}
                        classification['entities']['project_id'] = resolved_project_id
                        logger.info(f"[CATEGORY-RESOLVE] Updated classification with project_id={resolved_project_id}")

                        # Also save project_mapping to workflow_state for future use
                        project_ids = list(fetched_mapping.keys())
                        state_manager.save_state(session_id, {
                            'workflow_type': 'category_resolved',
                            'current_stage': 'resolved',
                            'context': {
                                'project_ids': project_ids,
                                'project_mapping': fetched_mapping,
                                'resolved_project_id': resolved_project_id,
                                'category': search_category
                            },
                            'project_mapping': fetched_mapping  # Top-level for save_state()
                        })
                        logger.info(f"[CATEGORY-RESOLVE] Saved project_mapping to workflow state")
                    else:
                        logger.warning(f"[CATEGORY-RESOLVE] Could not find project matching category '{search_category}' in fetched projects")
                else:
                    logger.warning(f"[CATEGORY-RESOLVE] No projects returned from list_projects")
            except Exception as fetch_err:
                logger.error(f"[CATEGORY-RESOLVE] Error fetching projects: {fetch_err}")

    # PRE-RESOLVE: Ensure project_id is resolved BEFORE Sonnet decision
    # This handles: ordinals ("first project"), context refs ("this project"), projectNumbers ("9000489")
    # Sonnet needs internal project_id to validate and make correct decisions
    if 'entities' not in classification:
        classification['entities'] = {}

    # Source 1: resolved_project_id from ordinal/context detection (already internal ID)
    if workflow_state:
        context = workflow_state.get('context', {})
        resolved_from_context = context.get('resolved_project_id')
        if resolved_from_context and not classification['entities'].get('project_id'):
            classification['entities']['project_id'] = resolved_from_context
            logger.info(f"[PRE-RESOLVE] Using resolved_project_id from context: {resolved_from_context}")

    # Source 2: projectNumber → internal project_id lookup (user said "schedule project 9000489")
    if classification['entities'].get('project_id') and workflow_state:
        raw_pid = str(classification['entities']['project_id'])
        pm = workflow_state.get('project_mapping', {}) or workflow_state.get('context', {}).get('project_mapping', {})
        if pm and raw_pid in pm:
            info = pm[raw_pid]
            resolved = info.get('project_id')
            if resolved and resolved != raw_pid:
                logger.info(f"[PRE-RESOLVE] projectNumber '{raw_pid}' → internal project_id '{resolved}'")
                classification['entities']['project_id'] = resolved
                classification['entities']['projectNumber'] = raw_pid  # Preserve original for display

    # Step 2: Intelligent decision using Sonnet 3.7
    # CONTEXT SWITCH FIX: When context switch just happened, skip the decision step
    # and use classification directly. This prevents the decision step from being
    # confused by conversation history (e.g., time slots from previous workflow)
    decision_start = time.time()

    if context_switch_handled and classification.get('action'):
        # Build decision directly from classification - don't call Sonnet decision
        logger.info(f"[DECISION] CONTEXT SWITCH: Skipping decision step, using classification directly: action={classification.get('action')}")
        decision = {
            'should_call_lambda': True,
            'lambda_action': classification.get('action'),
            'lambda_params': classification.get('entities', {}),
            'update_workflow_state': {
                'workflow_type': classification.get('workflow_type', 'browsing'),
                'current_stage': 'viewing',
                'context': classification.get('entities', {})
            }
        }
    else:
        logger.info("[DECISION] Step 2: Intelligent decision-making with Sonnet 3.7")
        decision = intelligent_decide_next_action(
            message,
            classification,
            workflow_state,
            conversation_history
        )

    timing['decision'] = time.time() - decision_start

    # BATCH SCHEDULING: Handle multi-project scheduling
    if classification.get('action') == 'batch_schedule' or decision.get('lambda_action') == 'batch_schedule':
        project_ids = classification.get('entities', {}).get('project_ids', [])
        batch_count = classification.get('entities', {}).get('count', 0)

        # Fallback: If Sonnet provided a count but not enough project_ids, extract from conversation
        if batch_count > len(project_ids):
            logger.info(f"[BATCH] Batch count ({batch_count}) > extracted IDs ({len(project_ids)}), extracting from conversation...")

            # Start with any IDs Sonnet already provided
            all_found_ids = list(project_ids)

            # Look for project list in conversation history - check ALL assistant messages
            for msg in reversed(conversation_history):
                content = msg.get('content', '')
                role = msg.get('role', '')

                # Look in assistant messages that likely contain project lists
                # Check for: #7751741 format, "Project #" mentions, or JSON with project IDs
                if role == 'assistant' and ('Project' in content or '"id"' in content or '#77' in content):
                    logger.info(f"[BATCH] Checking message for project IDs: {content[:100]}...")

                    # Try ALL patterns and accumulate IDs
                    # Pattern 1: #7751741 format (with # prefix)
                    found_ids = re.findall(r'#(\d{7})\b', content)

                    # Pattern 2: "id": "7751741" format (JSON)
                    found_ids.extend(re.findall(r'"id"\s*:\s*"?(\d{7})"?', content))

                    # Pattern 3: Project 7751741 or Project #7751741
                    found_ids.extend(re.findall(r'Project\s+#?(\d{7})\b', content, re.IGNORECASE))

                    if found_ids:
                        # Add unique IDs to our list
                        for pid in found_ids:
                            if pid not in all_found_ids:
                                all_found_ids.append(pid)

                        logger.info(f"[BATCH] Found IDs in this message: {found_ids}, total unique: {all_found_ids}")

                        if len(all_found_ids) >= batch_count:
                            project_ids = all_found_ids[:batch_count]
                            logger.info(f"[BATCH] Extracted project IDs from conversation: {project_ids}")
                            break

            # Use whatever we found
            if len(all_found_ids) > len(project_ids):
                project_ids = all_found_ids[:batch_count]

            # If we still don't have enough IDs, log a warning
            if len(project_ids) < batch_count:
                logger.warning(f"[BATCH] Could only find {len(project_ids)} project IDs, user requested {batch_count}")

        if project_ids and len(project_ids) > 1:
            logger.info(f"[BATCH] Batch scheduling detected: {len(project_ids)} projects - {project_ids}")

            # Initialize batch mode - start with first project
            first_project_id = project_ids[0]

            # Convert to get_available_dates for first project
            decision['should_call_lambda'] = True
            decision['lambda_action'] = 'get_available_dates'
            decision['lambda_params'] = {'project_id': first_project_id}

            # Set up batch tracking in workflow state
            if not decision.get('update_workflow_state'):
                decision['update_workflow_state'] = {}

            decision['update_workflow_state'].update({
                'workflow_type': 'batch_schedule_appointment',
                'current_stage': 'awaiting_date_selection',
                'context': {
                    'batch_mode': True,
                    'project_ids': project_ids,
                    'current_index': 0,
                    'total_projects': len(project_ids),
                    'completed_projects': [],
                    'project_id': first_project_id
                }
            })

            logger.info(f"[BATCH] Starting batch scheduling with project #{first_project_id} (1 of {len(project_ids)})")

    # Step 3: Execute decision
    if decision.get('should_call_lambda'):
        # Call Lambda function
        lambda_action = decision['lambda_action']
        lambda_params = decision['lambda_params']

        # CHAD FEEDBACK FIX: Lock project context - don't re-list if user is mid-workflow
        # "The AI is re-listing projects after a customer has already selected one, causing loops"
        if lambda_action == 'list_projects' and workflow_state:
            current_stage = workflow_state.get('current_stage', '')
            ws_context = workflow_state.get('context', {})
            selected_project_id = ws_context.get('project_id')

            # Scheduling workflow stages where we should NOT re-list
            scheduling_stages = [
                'awaiting_date_selection', 'awaiting_time_selection',
                'awaiting_appointment_confirm', 'awaiting_reschedule_confirm',
                'awaiting_cancel_confirmation'
            ]

            # Check if user EXPLICITLY asked to see all projects
            msg_lower = message.lower()
            explicit_list_patterns = [
                'list all', 'show all', 'all my project', 'all project',
                'what project', 'how many project', 'my project',
                'start over', 'different project', 'other project', 'back to'
            ]
            is_explicit_list_request = any(p in msg_lower for p in explicit_list_patterns)

            if selected_project_id and current_stage in scheduling_stages and not is_explicit_list_request:
                logger.warning(f"[LIST_PROJECTS] BLOCKED - mid-workflow. stage={current_stage}, project={selected_project_id}, msg='{message[:50]}'")
                # Don't re-list - return helpful message and keep workflow state
                category = ws_context.get('category', 'your project')
                if current_stage == 'awaiting_date_selection':
                    return {
                        'response': f"We're currently scheduling your {category} project. Please select a date, or say 'start over' to choose a different project.",
                        'intent': 'scheduling',
                        'action': 'blocked_relist',
                        'agent_name': 'Intelligent Orchestrator (Context Lock)'
                    }
                elif current_stage == 'awaiting_time_selection':
                    return {
                        'response': f"We're selecting a time for your {category} appointment. Please pick a time, or say 'start over' to choose a different project.",
                        'intent': 'scheduling',
                        'action': 'blocked_relist',
                        'agent_name': 'Intelligent Orchestrator (Context Lock)'
                    }
                else:
                    return {
                        'response': f"We're in the middle of scheduling your {category} project. Please confirm or say 'start over' to begin again.",
                        'intent': 'scheduling',
                        'action': 'blocked_relist',
                        'agent_name': 'Intelligent Orchestrator (Context Lock)'
                    }

        # FIX: Prevent conversation context bleeding for list_projects
        # When user says "list my projects", we should ALWAYS fetch ALL projects
        # from the API, not filter by project_ids extracted from conversation history.
        # Only preserve 'status' filter if explicitly requested (e.g., "schedulable", "New").
        if lambda_action == 'list_projects':
            if 'project_ids' in lambda_params:
                logger.info(f"[LIST_PROJECTS] Removing conversation project_ids from params - will fetch fresh from API")
                del lambda_params['project_ids']
            if 'project_id' in lambda_params:
                logger.info(f"[LIST_PROJECTS] Removing conversation project_id from params - will fetch fresh from API")
                del lambda_params['project_id']

            # Extract date filter from message for appointment status queries
            # e.g., "Is someone coming today?" → filter by today's date
            extracted_date = extract_date_from_message(message)
            if extracted_date and 'scheduled_date' not in lambda_params:
                logger.info(f"[LIST_PROJECTS] Extracted date filter from message: {extracted_date}")
                lambda_params['scheduled_date'] = extracted_date

        # WORKFLOW SWITCH DETECTION (Hybrid Approach):
        # Clear stale workflow state when user starts a DIFFERENT workflow type
        # This prevents issues like "schedule 3rd project" using reschedule API
        # because old workflow_state had workflow_type='reschedule_appointment'
        WORKFLOW_ACTIONS = {
            'schedule_appointment': 'schedule_appointment',
            'schedule_project': 'schedule_appointment',  # Alias for schedule_appointment
            'get_available_dates': 'schedule_appointment',
            'get_time_slots': 'schedule_appointment',
            'reschedule_appointment': 'reschedule_appointment',
            'cancel_appointment': 'cancel_appointment',
            'list_projects': 'project_listing',
        }

        new_workflow_type = None
        forced_workflow_type = None  # Set when workflow switch detected - overrides Sonnet's workflow_type
        classified_action = classification.get('action', '')

        # Determine what workflow the NEW action belongs to
        if classified_action in WORKFLOW_ACTIONS:
            new_workflow_type = WORKFLOW_ACTIONS[classified_action]

        # Also check if classification explicitly specifies workflow_type
        if classification.get('workflow_type'):
            new_workflow_type = classification.get('workflow_type')

        # If we have an old workflow state AND the new action is for a DIFFERENT workflow, clear it
        if workflow_state and new_workflow_type:
            old_workflow_type = workflow_state.get('workflow_type')

            # Check if user is working with a different project (same workflow type but new project)
            # IMPORTANT: Only consider this a "new project" if the classification explicitly has workflow_type
            # (indicating a new workflow request like "schedule project X"), NOT for continuations like date selection
            new_project_id = classification.get('entities', {}).get('project_id')
            old_project_id = workflow_state.get('context', {}).get('project_id')

            # Only treat as new project if:
            # 1. Classification explicitly has workflow_type (new workflow, not continuation)
            # 2. AND the project IDs are different
            has_explicit_workflow = classification.get('workflow_type') is not None
            is_new_project = (has_explicit_workflow and
                              new_project_id and
                              old_project_id and
                              str(new_project_id) != str(old_project_id))

            if old_workflow_type and old_workflow_type != new_workflow_type:
                logger.info(f"[WORKFLOW SWITCH] Resetting old '{old_workflow_type}' state - user starting new '{new_workflow_type}' workflow")
                state_manager.reset_workflow_state(session_id)
                workflow_state = state_manager.get_state(session_id)  # Reload to get preserved project_mapping
                forced_workflow_type = new_workflow_type  # Override Sonnet's workflow_type when saving state
            elif is_new_project and new_workflow_type in ['schedule_appointment', 'reschedule_appointment', 'cancel_appointment']:
                logger.info(f"[WORKFLOW SWITCH] New project {new_project_id} detected (explicit workflow_type={classification.get('workflow_type')}) - resetting old workflow state for project {old_project_id}")
                state_manager.reset_workflow_state(session_id)
                workflow_state = state_manager.get_state(session_id)  # Reload to get preserved project_mapping

        # RESCHEDULE: Use get_rescheduler_slots instead of get_available_dates/get_time_slots
        # For already scheduled projects, the normal slots API returns "Job already requested"
        # NOTE: Only use classification's workflow_type, NOT old workflow_state, to avoid
        # confusing a new "schedule" request with an old "reschedule" workflow
        is_reschedule = (
            classification.get('action') == 'reschedule_appointment' or
            classification.get('workflow_type') == 'reschedule_appointment'
        )

        # Also check workflow state but ONLY if classification doesn't have workflow_type
        # (meaning we're continuing an existing workflow, not starting a new one)
        if not classification.get('workflow_type') and workflow_state:
            is_reschedule = is_reschedule or workflow_state.get('workflow_type') == 'reschedule_appointment'

        # Determine if this is a NEW reschedule request vs continuing an existing reschedule workflow
        is_new_reschedule_request = (
            classification.get('action') == 'reschedule_appointment' or
            classification.get('workflow_type') == 'reschedule_appointment'
        )

        if is_reschedule and lambda_action in ['get_available_dates', 'get_time_slots']:
            # For NEW reschedule requests: use reschedule_appointment action
            # This action first cancels the existing appointment (changing status from
            # "Customer Scheduled" to "Customer to Schedule") then gets available slots
            if is_new_reschedule_request:
                logger.info(f"[RESCHEDULE] New reschedule request - using reschedule_appointment action (cancel + get slots)")
                lambda_action = 'reschedule_appointment'
                decision['lambda_action'] = 'reschedule_appointment'
            else:
                # For CONTINUATION (user selecting date/time): use get_time_slots with new slotsChatbot API
                # NOTE: We no longer use get_rescheduler_slots - the new slotsChatbot API works for reschedule too
                logger.info(f"[RESCHEDULE] Continuing reschedule workflow - using {lambda_action} (slotsChatbot API)")
                # Keep the action as-is (get_time_slots) - it will use the new slotsChatbot API

        # RESOLVE project_index to project_id for ALL channels
        # This handles ordinal references like "last project", "first project", "3rd project"
        # project_index can be negative (-1 = last, -2 = second to last, etc.)
        if 'project_index' in lambda_params and 'project_id' not in lambda_params:
            project_index = lambda_params.get('project_index')
            logger.info(f"[ORDINAL] Resolving project_index={project_index} to project_id")

            resolved = False

            # First try: Get project_ids from workflow_state.context
            if workflow_state:
                context = workflow_state.get('context', {})
                project_ids = context.get('project_ids', [])
                if project_ids and isinstance(project_ids, list):
                    logger.info(f"[ORDINAL] Found {len(project_ids)} project_ids in workflow_state")
                    # project_index supports negative indices: -1 = last, -2 = second to last, etc.
                    if isinstance(project_index, int):
                        try:
                            resolved_id = str(project_ids[project_index])
                            lambda_params['project_id'] = resolved_id
                            del lambda_params['project_index']
                            logger.info(f"[ORDINAL] Resolved from workflow_state: project_index={project_index} -> project_id={resolved_id}")
                            resolved = True
                        except IndexError:
                            logger.warning(f"[ORDINAL] project_index={project_index} out of range (have {len(project_ids)} projects)")

            if not resolved:
                # AUTO-FETCH: If no project_ids in workflow_state, fetch them first
                logger.info(f"[ORDINAL] No project_ids in workflow_state - auto-fetching projects first")
                try:
                    # Call list_projects to get all projects
                    list_response = call_lambda_directly('list_projects', {
                        'customer_id': customer_id,
                        'client_id': client_id,
                        'pf_bearer_token': pf_bearer_token,
                        'from_phone': from_phone
                    })

                    # Extract projects from response
                    list_data = list_response.get('response', {})
                    list_func = list_data.get('functionResponse', {})
                    list_body_wrapper = list_func.get('responseBody', {})
                    list_text = list_body_wrapper.get('TEXT', {})
                    list_body_str = list_text.get('body', '{}')

                    if isinstance(list_body_str, str):
                        list_body = json.loads(list_body_str)
                    else:
                        list_body = list_body_str

                    # Extract project_ids AND project_mapping (for weather/context lookups)
                    if 'projects' in list_body and isinstance(list_body['projects'], list):
                        fetched_projects = list_body['projects']
                        fetched_ids = [str(p.get('id', '')) for p in fetched_projects if p.get('id')]

                        # Build project_mapping: project_id -> {category, address, status}
                        # This enables weather queries, category-based lookups, and other context-aware features
                        # IMPORTANT: projectNumber is what users see (Order Number), id is internal
                        fetched_mapping = {}
                        for p in fetched_projects:
                            pid = str(p.get('id', ''))
                            project_number = p.get('projectNumber', '')
                            if pid:
                                fetched_mapping[pid] = {
                                    'category': p.get('category', ''),
                                    'address': p.get('address', ''),
                                    'status': p.get('status', ''),
                                    'projectNumber': project_number  # Order Number for display
                                }
                                # Also map by projectNumber for reverse lookup (Order Number -> Project ID)
                                if project_number:
                                    fetched_mapping[project_number] = {
                                        'category': p.get('category', ''),
                                        'project_id': pid  # Internal project ID for API calls
                                    }

                        if fetched_ids:
                            logger.info(f"[ORDINAL] Auto-fetched {len(fetched_ids)} project_ids: {fetched_ids[:5]}...")

                            # Save to workflow_state for future queries
                            if not workflow_state:
                                workflow_state = {'context': {}}
                            if 'context' not in workflow_state:
                                workflow_state['context'] = {}
                            workflow_state['context']['project_ids'] = fetched_ids
                            workflow_state['context']['project_mapping'] = fetched_mapping

                            # Save to DynamoDB (includes project_mapping for weather/category lookups)
                            state_manager.save_state(session_id, {
                                'workflow_type': 'project_listing',
                                'current_stage': 'listing_projects',
                                'context': {
                                    'project_ids': fetched_ids,
                                    'project_mapping': fetched_mapping
                                },
                                'project_mapping': fetched_mapping  # Top-level for save_state()
                            })

                            # Now resolve project_index (supports negative indices)
                            if isinstance(project_index, int):
                                try:
                                    resolved_id = str(fetched_ids[project_index])
                                    lambda_params['project_id'] = resolved_id
                                    del lambda_params['project_index']
                                    logger.info(f"[ORDINAL] Auto-resolved: project_index={project_index} -> project_id={resolved_id}")
                                    resolved = True
                                except IndexError:
                                    logger.warning(f"[ORDINAL] project_index={project_index} out of range (fetched {len(fetched_ids)} projects)")

                except Exception as fetch_err:
                    logger.error(f"[ORDINAL] Auto-fetch projects failed: {fetch_err}")

                if not resolved:
                    logger.warning(f"[ORDINAL] Could not resolve project_index={project_index}")

        # Add auth params
        lambda_params.update({
            'customer_id': customer_id,
            'client_id': client_id,
            'pf_bearer_token': pf_bearer_token,
            'from_phone': from_phone
        })

        # INJECT BASE_DATE FOR GET_TIME_SLOTS: Use start_date from workflow state (saved by get_available_dates)
        # This is critical for "next month" scheduling - the API URL needs base_date from get_available_dates
        if lambda_action == 'get_time_slots':
            context = workflow_state.get('context', {}) if workflow_state else {}
            if 'start_date' in context and 'base_date' not in lambda_params:
                lambda_params['base_date'] = context['start_date']
                logger.info(f"[TIME_SLOTS] Injected base_date from workflow state: {context['start_date']}")

        # ORDER NUMBER → PROJECT ID RESOLUTION
        # Users see/say Order Numbers (projectNumber) but API requires internal Project IDs
        # Order Numbers can be ANY format (e.g., "AI-PRO-100000", "21083_09PF05VD_...", etc.)
        # Always try to resolve before making Lambda calls that use project_id
        if 'project_id' in lambda_params and lambda_action != 'list_projects':
            raw_project_id = str(lambda_params['project_id'])
            project_mapping = {}
            if workflow_state:
                project_mapping = workflow_state.get('project_mapping', {}) or workflow_state.get('context', {}).get('project_mapping', {})

            # Try to resolve from existing mapping first (EXACT match only to avoid stale data issues)
            resolved_id = None
            if project_mapping:
                # Only use mapping if we have an EXACT match (case-insensitive for alphanumeric)
                # First try exact case match
                if raw_project_id in project_mapping:
                    info = project_mapping[raw_project_id]
                    resolved_id = info.get('project_id', raw_project_id)
                    logger.info(f"[ORDER-RESOLVE] Exact match in mapping: '{raw_project_id}' -> '{resolved_id}'")
                else:
                    # Try case-insensitive match for alphanumeric projectNumbers
                    raw_lower = raw_project_id.lower()
                    for pid in project_mapping.keys():
                        if pid.lower() == raw_lower:
                            info = project_mapping[pid]
                            resolved_id = info.get('project_id', pid)
                            logger.info(f"[ORDER-RESOLVE] Case-insensitive match: '{raw_project_id}' -> '{pid}' -> '{resolved_id}'")
                            break

            # If not resolved, ALWAYS auto-fetch fresh projects
            # This handles: projectNumbers (numeric or alphanumeric), stale mappings, new projects
            if not resolved_id:
                logger.info(f"[ORDER-RESOLVE] '{raw_project_id}' not found in mapping - auto-fetching projects")
                try:
                    list_response = call_lambda_directly('list_projects', {
                        'customer_id': customer_id,
                        'client_id': client_id,
                        'pf_bearer_token': pf_bearer_token,
                        'from_phone': from_phone
                    })
                    list_data = list_response.get('response', {})
                    list_func = list_data.get('functionResponse', {})
                    list_body_wrapper = list_func.get('responseBody', {})
                    list_text = list_body_wrapper.get('TEXT', {})
                    list_body_str = list_text.get('body', '{}')
                    if isinstance(list_body_str, str):
                        list_body = json.loads(list_body_str)
                    else:
                        list_body = list_body_str

                    if 'projects' in list_body and isinstance(list_body['projects'], list):
                        project_mapping = {}  # Fresh mapping
                        for p in list_body['projects']:
                            pid = str(p.get('id', ''))
                            project_number = p.get('projectNumber', '')
                            project_status = p.get('status', '')
                            if pid:
                                # Map by internal ID - include status for reschedule detection
                                exact_category = p.get('category', '')
                                project_mapping[pid] = {
                                    'projectNumber': project_number,
                                    'category': exact_category,
                                    'category_bucket': get_category_bucket(exact_category),
                                    'status': project_status,
                                    'project_type': p.get('projectType', p.get('ProjectType', ''))
                                }
                                # Also map by Order Number for reverse lookup
                                if project_number:
                                    project_mapping[project_number] = {
                                        'project_id': pid,
                                        'category': exact_category,
                                        'category_bucket': get_category_bucket(exact_category),
                                        'status': project_status,
                                        'project_type': p.get('projectType', p.get('ProjectType', ''))
                                    }
                        logger.info(f"[ORDER-RESOLVE] Auto-fetched {len(list_body['projects'])} projects, mapping keys: {list(project_mapping.keys())[:10]}")

                        # Try EXACT match first (case-insensitive for alphanumeric projectNumbers)
                        if raw_project_id in project_mapping:
                            info = project_mapping[raw_project_id]
                            resolved_id = info.get('project_id', raw_project_id)
                            logger.info(f"[ORDER-RESOLVE] Exact match after fetch: '{raw_project_id}' -> '{resolved_id}'")
                        else:
                            # Try case-insensitive match
                            raw_lower = raw_project_id.lower()
                            for pid in project_mapping.keys():
                                if pid.lower() == raw_lower:
                                    info = project_mapping[pid]
                                    resolved_id = info.get('project_id', pid)
                                    logger.info(f"[ORDER-RESOLVE] Case-insensitive match after fetch: '{raw_project_id}' -> '{resolved_id}'")
                                    break

                        # If still not found, project doesn't exist for this customer
                        if not resolved_id:
                            logger.warning(f"[ORDER-RESOLVE] Project '{raw_project_id}' not found in customer's projects")
                    else:
                        # list_projects didn't return projects - likely an error
                        error_msg = list_body.get('error', list_body.get('message', 'unknown error'))
                        logger.warning(f"[ORDER-RESOLVE] list_projects failed: {error_msg}")
                except Exception as fetch_err:
                    logger.warning(f"[ORDER-RESOLVE] Auto-fetch failed: {fetch_err}")

            if resolved_id and resolved_id != raw_project_id:
                logger.info(f"[ORDER-RESOLVE] ✅ Resolved '{raw_project_id}' -> Internal Project ID '{resolved_id}'")
                lambda_params['project_id'] = resolved_id
            elif not resolved_id:
                # Project not found - pass as-is and let Lambda handle the error
                logger.warning(f"[ORDER-RESOLVE] ⚠️ Could not resolve '{raw_project_id}' - passing as-is")

        # Convert schedule_project to get_available_dates (schedule_project is the classifier action,
        # but the Lambda only understands get_available_dates)
        if lambda_action == 'schedule_project':
            logger.info(f"[ACTION CONVERT] Converting schedule_project -> get_available_dates")
            lambda_action = 'get_available_dates'
            decision['lambda_action'] = 'get_available_dates'

        # ============================================================================
        # AUTO-CONVERT TO RESCHEDULE: If get_available_dates is called on a project
        # that is already scheduled, auto-convert to reschedule_appointment.
        # This handles the case where NLU classifies "reschedule this week" as
        # get_available_dates instead of reschedule_appointment.
        # PF API returns "Not allowed" for get_available_dates on scheduled projects.
        # ============================================================================
        if lambda_action == 'get_available_dates' and not is_reschedule:
            project_id_to_check = lambda_params.get('project_id')
            if project_id_to_check:
                # Check if project is already scheduled
                project_status = None

                # First try: Get status from project_mapping (populated during order-resolve)
                if project_mapping:
                    project_info = project_mapping.get(str(project_id_to_check), {})
                    project_status = project_info.get('status', '')

                # Second try: Check workflow state context
                if not project_status and workflow_state:
                    context = workflow_state.get('context', {})
                    ctx_mapping = context.get('project_mapping', {})
                    if ctx_mapping:
                        project_info = ctx_mapping.get(str(project_id_to_check), {})
                        project_status = project_info.get('status', '')

                # Check if project is schedulable, already scheduled, or not allowed
                if project_status:
                    scheduled_statuses = ['Scheduled', 'Customer Scheduled', 'Tentatively Scheduled']
                    schedulable_statuses = ['New', 'Ready To Schedule']

                    if project_status in scheduled_statuses:
                        logger.info(f"[AUTO-RESCHEDULE] Project {project_id_to_check} is already scheduled (status='{project_status}')")
                        logger.info(f"[AUTO-RESCHEDULE] Converting get_available_dates -> reschedule_appointment")
                        lambda_action = 'reschedule_appointment'
                        decision['lambda_action'] = 'reschedule_appointment'
                        is_reschedule = True
                        is_new_reschedule_request = True
                    elif project_status in schedulable_statuses:
                        logger.info(f"[SCHEDULE-CHECK] Project {project_id_to_check} status='{project_status}' - proceeding with get_available_dates")
                    else:
                        # Status not schedulable (e.g., Ready for Quote, Completed, etc.)
                        logger.warning(f"[SCHEDULE-CHECK] Project {project_id_to_check} status='{project_status}' is NOT schedulable")
                        timing['total'] = time.time() - start_time
                        return {
                            'response': f"This project can't be scheduled right now. The status is '{project_status}'. Please contact our office for assistance.",
                            'intent': 'scheduling',
                            'action': 'schedule_not_allowed',
                            'agent_name': 'Intelligent Orchestrator (Schedule Check)',
                            'direct_call': True,
                            'timing': timing,
                            'pf_http_status_code': 400
                        }

        logger.info(f"[LAMBDA] Calling Lambda: {lambda_action} with params: {lambda_params}")
        lambda_start = time.time()

        # AUTO-FETCH PROJECT DETAILS: When starting scheduling/rescheduling workflow, fetch project info first
        # This ensures we have category, city, state for weather-aware scheduling
        if lambda_action in ['get_available_dates', 'get_rescheduler_slots', 'reschedule_appointment']:
            project_id = lambda_params.get('project_id')
            existing_category = workflow_state.get('context', {}).get('category') if workflow_state else None

            if project_id and not existing_category:
                logger.info(f"[PROJECT] Auto-fetching project details for weather-aware scheduling (project_id={project_id})")
                try:
                    details_response = call_lambda_directly('get_project_details', {
                        'project_id': project_id,
                        'customer_id': customer_id,
                        'client_id': client_id,
                        'pf_bearer_token': pf_bearer_token,
                        'from_phone': from_phone
                    })

                    # Extract project info
                    details_data = details_response.get('response', {})
                    details_func = details_data.get('functionResponse', {})
                    details_body_wrapper = details_func.get('responseBody', {})
                    details_text = details_body_wrapper.get('TEXT', {})
                    details_body_str = details_text.get('body', '{}')

                    if isinstance(details_body_str, str):
                        project_info = json.loads(details_body_str)
                    else:
                        project_info = details_body_str

                    # Extract category, project_type and location from project details
                    # Response structure: {"project": {"address": {...}, "projectType": "..."}, "category": "...", "full_address": "..."}
                    project_category = project_info.get('category', '')

                    # Try nested project.address first
                    project_obj = project_info.get('project', {})
                    # Extract project_type from nested project object
                    project_type_val = project_obj.get('projectType', project_obj.get('ProjectType', '')) if isinstance(project_obj, dict) else ''
                    address_obj = project_obj.get('address', {}) if isinstance(project_obj, dict) else {}

                    if isinstance(address_obj, dict) and address_obj:
                        project_city = address_obj.get('city', '')
                        project_state = address_obj.get('state', '')
                        project_address = address_obj.get('fullAddress', '') or project_info.get('full_address', '')
                    else:
                        # Fallback: parse from full_address "Street, City, State ZIP"
                        full_addr = project_info.get('full_address', '')
                        project_address = full_addr
                        # Try to extract city/state from "..., City, State ZIP"
                        parts = full_addr.split(',')
                        if len(parts) >= 2:
                            city_part = parts[-2].strip() if len(parts) >= 2 else ''
                            state_zip = parts[-1].strip().split() if parts else []
                            project_city = city_part
                            project_state = state_zip[0] if state_zip else ''
                        else:
                            project_city = ''
                            project_state = ''

                    logger.info(f"[PROJECT] Address extraction: project_obj keys={list(project_obj.keys()) if isinstance(project_obj, dict) else 'N/A'}, address_obj={address_obj}")

                    if project_category or project_city:
                        logger.info(f"[PROJECT] Extracted: category={project_category}, city={project_city}, state={project_state}")

                        # Update or create workflow state with project info
                        if not decision.get('update_workflow_state'):
                            decision['update_workflow_state'] = {'context': {}}
                        if 'context' not in decision['update_workflow_state']:
                            decision['update_workflow_state']['context'] = {}

                        decision['update_workflow_state']['context'].update({
                            'category': project_category,
                            'project_type': project_type_val,
                            'city': project_city,
                            'state': project_state,
                            'address': project_address,
                            'project_id': project_id
                        })

                        # Also update the current workflow_state for use in this request
                        if workflow_state is None:
                            workflow_state = {'context': {}}
                        if 'context' not in workflow_state:
                            workflow_state['context'] = {}
                        workflow_state['context'].update({
                            'category': project_category,
                            'project_type': project_type_val,
                            'city': project_city,
                            'state': project_state,
                            'address': project_address,
                            'project_id': project_id  # CRITICAL: Include project_id for pronoun resolution
                        })

                except Exception as details_error:
                    logger.warning(f"Auto-fetch project details failed (non-fatal): {details_error}")
                    # Continue with scheduling - weather check will be skipped

        # ====================================================================
        # CONFIRMATION INTERCEPTION (Chat/SMS only)
        # Before executing confirm_appointment, return preview for user approval
        # ====================================================================
        if lambda_action == 'confirm_appointment' and channel != 'voice':
            logger.info(f"[CONFIRM] Intercepting confirm_appointment for user confirmation (channel={channel})")

            # Get context for preview
            context = workflow_state.get('context', {}) if workflow_state else {}
            project_name = context.get('category', context.get('project_name', 'Project'))
            project_id = lambda_params.get('project_id', context.get('project_id', ''))
            date_str = lambda_params.get('date', context.get('date', ''))
            time_str = lambda_params.get('time', context.get('time', ''))
            address = context.get('address', context.get('full_address', ''))
            project_type = context.get('project_type', '')

            # Format date for preview (YYYY-MM-DD -> MM/DD/YYYY with day name)
            formatted_preview_date = date_str
            try:
                from datetime import datetime as dt
                date_obj = dt.strptime(date_str, "%Y-%m-%d")
                formatted_preview_date = date_obj.strftime("%a %m/%d/%Y")  # Mon 01/26/2026
            except:
                pass  # Keep original if parsing fails

            # Store pending action in workflow state
            pending_action = {
                'action': 'confirm_appointment',
                'params': {
                    'project_id': project_id,
                    'date': date_str,
                    'time': time_str,
                    'request_id': lambda_params.get('request_id', context.get('request_id', ''))
                },
                'preview': {
                    'project_name': project_name,
                    'project_id': project_id,
                    'project_type': project_type,
                    'date': formatted_preview_date,  # Formatted for UI display
                    'rawDate': date_str,  # Keep raw for API calls
                    'time': time_str,
                    'formattedTime': format_time_12hr(time_str),
                    'address': address
                }
            }

            if workflow_state is None:
                workflow_state = {}
            # NOTE: pending_action must be stored in 'context' as save_state only saves specific fields
            if 'context' not in workflow_state:
                workflow_state['context'] = {}
            workflow_state['context']['pending_action'] = pending_action
            workflow_state['current_stage'] = 'awaiting_confirmation'
            state_manager.save_state(session_id, workflow_state)

            # Build confirmation preview response
            # Format date for display (YYYY-MM-DD -> MM/DD/YYYY with day name)
            formatted_date_str = date_str
            try:
                from datetime import datetime as dt
                date_obj = dt.strptime(date_str, "%Y-%m-%d")
                formatted_date_str = date_obj.strftime("%a %m/%d/%Y")  # Mon 01/26/2026
            except:
                pass  # Keep original if parsing fails

            preview_text = f"📋 **Appointment Preview**\n\n"
            preview_text += f"**Project:** {project_name}\n"
            if project_type:
                preview_text += f"**Type:** {project_type}\n"
            preview_text += f"**Date:** {formatted_date_str}\n"
            preview_text += f"**Time:** {format_time_12hr(time_str)}\n"
            if address:
                preview_text += f"**Location:** {address}\n"
            preview_text += f"\nWould you like to confirm this appointment?"

            timing['total'] = time.time() - start_time
            return {
                'response': preview_text,
                'intent': 'scheduling',
                'action': 'confirm_appointment_preview',
                'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                'direct_call': True,
                'timing': timing,
                'confirmation_required': True,
                'pending_action': pending_action.get('preview', {}),
                'pf_http_status_code': 200
            }

        # ====================================================================
        # VOICE: For confirm_appointment, add confirmed=True to book immediately
        # GPT-4o manages the conversation, so we trust it when it sends confirm_appointment
        # This ensures voice calls skip Step 1 preview and go directly to Step 2 booking
        # ====================================================================
        if lambda_action == 'confirm_appointment' and channel == 'voice':
            lambda_params['confirmed'] = True
            logger.info(f"[VOICE-CONFIRM] Voice channel - adding confirmed=True to confirm_appointment params")

        # ====================================================================
        # VALIDATION: confirm_appointment requires both date AND time
        # If GPT-4o calls confirm_appointment without time, return error
        # This is a safety net - GPT-4o should follow the scheduling flow
        # ====================================================================
        if lambda_action == 'confirm_appointment':
            has_date = lambda_params.get('date') or context.get('date')
            has_time = lambda_params.get('time') or context.get('time')

            if not has_time:
                logger.warning(f"[CONFIRM-VALIDATION] confirm_appointment called without time - date={has_date}, time={has_time}")
                # Try to get time slots for the date if we have a date
                if has_date and lambda_params.get('project_id'):
                    timing['total'] = time.time() - start_time
                    return {
                        'response': f"Before I can confirm, I need to know what time works for you. What time would you prefer?",
                        'intent': 'scheduling',
                        'action': 'confirm_appointment',
                        'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                        'direct_call': True,
                        'timing': timing,
                        'validation_error': 'missing_time',
                        'pf_http_status_code': 200
                    }
                else:
                    timing['total'] = time.time() - start_time
                    return {
                        'response': "I need both a date and time to confirm your appointment. What date and time would you like?",
                        'intent': 'scheduling',
                        'action': 'confirm_appointment',
                        'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                        'direct_call': True,
                        'timing': timing,
                        'validation_error': 'missing_date_time',
                        'pf_http_status_code': 200
                    }

        try:
            lambda_response = call_lambda_directly(lambda_action, lambda_params)
            timing['lambda_call'] = time.time() - lambda_start

            # Extract response from Lambda
            response_data = lambda_response.get('response', {})
            function_response = response_data.get('functionResponse', {})
            response_body_wrapper = function_response.get('responseBody', {})
            text_wrapper = response_body_wrapper.get('TEXT', {})
            response_body_str = text_wrapper.get('body', '{}')

            if isinstance(response_body_str, str):
                response_body = json.loads(response_body_str)
            else:
                response_body = response_body_str

            # POST-FILTER PROJECTS: Apply semantic filters since upstream API doesn't filter
            # Use lambda_params which contains status, category, projectType from classification
            # SKIP if scheduling-actions already handled special cases (already_scheduled, status_reason)
            if lambda_action == 'list_projects' and 'projects' in response_body and isinstance(response_body['projects'], list):
                # Skip post-filter if Lambda already handled "no schedulable" case
                if response_body.get('already_scheduled') or response_body.get('status_reason'):
                    logger.info(f"[FILTER] Skipping post-filter - Lambda returned special case: already_scheduled={response_body.get('already_scheduled')}, status_reason={response_body.get('status_reason')}")
                else:
                    original_count = len(response_body['projects'])
                    # DEBUG: Log filter params before applying
                    logger.info(f"[FILTER-DEBUG] About to filter {original_count} projects with params: {lambda_params}")
                    if original_count > 0:
                        # Log first project's installer info for debugging
                        first_proj = response_body['projects'][0]
                        logger.info(f"[FILTER-DEBUG] First project installer: {first_proj.get('installer', 'NOT FOUND')}")
                    response_body['projects'] = apply_project_filters(response_body['projects'], lambda_params)
                    filtered_count = len(response_body['projects'])
                    logger.info(f"[FILTER] Applied post-filters: {original_count} -> {filtered_count} projects")

            # Extract PF API HTTP status code from Lambda response
            # Check both 'pf_http_status_code' and 'pf_status_code' for compatibility
            pf_http_status_code = response_body.get('pf_http_status_code') or response_body.get('pf_status_code', 200)

            # CHECK FOR AUTH ERRORS: If the API returned 401/403, the session has expired
            if pf_http_status_code in [401, 403]:
                logger.info(f"[AUTH] PF API returned {pf_http_status_code} - session expired")
                response_text = "Your session has expired. Please log in again to continue."
                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': classification.get('intent', 'unknown'),
                    'action': decision.get('lambda_action') or classification.get('action'),
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing,
                    'pf_http_status_code': 401  # Always return 401 for auth errors so frontend can redirect
                }

            # CHECK FOR LAMBDA ERRORS: If Lambda returned an error in response body
            if response_body.get('error'):
                error_msg = response_body.get('error', 'Unknown error')
                logger.error(f"[LAMBDA_ERROR] Lambda {lambda_action} returned error: {error_msg}")

                # Parse error message for user-friendly response
                if 'No technician found' in error_msg:
                    user_error = "Sorry, no technician is available for that time slot. Please select a different time."
                elif 'already booked' in error_msg or 'conflict' in error_msg.lower():
                    # ================================================================
                    # ENHANCED UX: Fetch available slots when requested slot is booked
                    # Instead of just "select a different time", show what's available
                    # ================================================================
                    user_error = "That time slot was just booked."
                    try:
                        # Get context for re-fetching slots
                        ctx = workflow_state.get('context', {}) if workflow_state else {}
                        slot_project_id = ctx.get('project_id') or lambda_params.get('project_id')
                        slot_date = ctx.get('date') or lambda_params.get('date')

                        if slot_project_id and slot_date:
                            logger.info(f"[BOOKED-RETRY] Fetching fresh slots for project {slot_project_id} on {slot_date}")
                            slot_params = {
                                'project_id': slot_project_id,
                                'date': slot_date,
                                'client_id': client_id,
                                'customer_id': customer_id,
                                'pf_bearer_token': pf_bearer_token
                            }
                            slot_response = call_lambda_directly('get_time_slots', slot_params)
                            slot_data = slot_response.get('response', {}).get('functionResponse', {}).get('responseBody', {}).get('TEXT', {}).get('body', '{}')
                            if isinstance(slot_data, str):
                                slot_body = json.loads(slot_data)
                            else:
                                slot_body = slot_data
                            fresh_slots = slot_body.get('time_slots', [])

                            if fresh_slots:
                                # Format available slots for voice
                                if channel == 'voice':
                                    slot_list = ', '.join(fresh_slots[:4])
                                    user_error = f"That time slot was just booked. But I found these other times available: {slot_list}. Which one works for you?"
                                else:
                                    slot_list = ', '.join(fresh_slots[:5])
                                    user_error = f"That time slot was just booked. Here are the available times: {slot_list}. Which would you prefer?"
                                logger.info(f"[BOOKED-RETRY] Found {len(fresh_slots)} alternative slots")
                            else:
                                user_error = "That time slot was just booked and there are no other slots available for this date. Would you like to try a different date?"
                    except Exception as retry_err:
                        logger.warning(f"[BOOKED-RETRY] Failed to fetch fresh slots: {retry_err}")
                        user_error = "That time slot was just booked. Please select a different time."
                elif 'SESSION_EXPIRED' in error_msg or '401' in error_msg or '403' in error_msg:
                    user_error = "Your session has expired. Please log out and log back in."
                elif 'Invalid' in error_msg:
                    user_error = "Sorry, there was an issue with that request. Please try again."
                else:
                    user_error = f"Sorry, I couldn't complete that action. Please try again."

                timing['total'] = time.time() - start_time
                return {
                    'response': user_error,
                    'intent': classification.get('intent', 'unknown'),
                    'action': lambda_action,
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing,
                    'pf_http_status_code': pf_http_status_code,
                    'error': True
                }

            # PROACTIVE WEATHER WARNINGS: Add weather indicators when showing available dates
            if lambda_action == 'get_available_dates':
                available_dates = response_body.get('available_dates', [])
                project_category = workflow_state.get('context', {}).get('category') if workflow_state else None

                if available_dates and project_category and is_outdoor_project(project_category):
                    logger.info(f"[WEATHER] Proactive weather check for {project_category}: {len(available_dates)} dates")

                    # Extract location from workflow state
                    location = extract_location_from_context(workflow_state)

                    if location:
                        try:
                            # Fetch weather forecast
                            weather_params = {
                                'location': location,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            }

                            logger.info(f"[WEATHER] Fetching weather for {location}")
                            weather_response = call_lambda_directly('get_weather', weather_params)

                            # Extract weather data
                            w_data = weather_response.get('response', {})
                            w_func = w_data.get('functionResponse', {})
                            w_body_wrapper = w_func.get('responseBody', {})
                            w_text = w_body_wrapper.get('TEXT', {})
                            w_body_str = w_text.get('body', '{}')

                            if isinstance(w_body_str, str):
                                weather_body = json.loads(w_body_str)
                            else:
                                weather_body = w_body_str

                            # Enrich dates with weather indicators
                            enriched_dates = add_weather_indicators_to_dates(
                                weather_body,
                                available_dates,
                                project_category
                            )

                            # Inject enriched dates into response
                            response_body['dates_with_weather'] = enriched_dates

                            # Count suitable vs unsuitable dates
                            suitable_count = sum(1 for d in enriched_dates if d.get('suitable'))
                            unsuitable_count = len(enriched_dates) - suitable_count

                            if unsuitable_count > 0:
                                logger.info(f"[WARNING] Proactive warning: {unsuitable_count}/{len(enriched_dates)} dates have weather concerns")
                                response_body['has_weather_concerns'] = True
                                response_body['suitable_date_count'] = suitable_count
                                response_body['unsuitable_date_count'] = unsuitable_count

                        except Exception as weather_err:
                            logger.warning(f"Proactive weather check failed (non-fatal): {weather_err}")
                            # Continue without weather indicators
                    else:
                        logger.warning("No location found for proactive weather check")

            # PROACTIVE WEATHER WARNINGS FOR RESCHEDULER: Same as get_available_dates
            if lambda_action == 'get_rescheduler_slots':
                available_dates = response_body.get('available_dates', [])
                project_category = workflow_state.get('context', {}).get('category') if workflow_state else None

                # Only add weather if we have dates (not slots) and it's an outdoor project
                if available_dates and not response_body.get('slots') and project_category and is_outdoor_project(project_category):
                    logger.info(f"[WEATHER] Proactive weather check for reschedule ({project_category}): {len(available_dates)} dates")

                    # Extract location from workflow state
                    location = extract_location_from_context(workflow_state)

                    if location:
                        try:
                            # Fetch weather forecast
                            weather_params = {
                                'location': location,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            }

                            logger.info(f"[WEATHER] Fetching weather for reschedule at {location}")
                            weather_response = call_lambda_directly('get_weather', weather_params)

                            # Extract weather data
                            w_data = weather_response.get('response', {})
                            w_func = w_data.get('functionResponse', {})
                            w_body_wrapper = w_func.get('responseBody', {})
                            w_text = w_body_wrapper.get('TEXT', {})
                            w_body_str = w_text.get('body', '{}')

                            if isinstance(w_body_str, str):
                                weather_body = json.loads(w_body_str)
                            else:
                                weather_body = w_body_str

                            # Enrich dates with weather indicators
                            enriched_dates = add_weather_indicators_to_dates(
                                weather_body,
                                available_dates,
                                project_category
                            )

                            # Inject enriched dates into response
                            response_body['dates_with_weather'] = enriched_dates

                            # Count suitable vs unsuitable dates
                            suitable_count = sum(1 for d in enriched_dates if d.get('suitable'))
                            unsuitable_count = len(enriched_dates) - suitable_count

                            if unsuitable_count > 0:
                                logger.info(f"[WARNING] Proactive reschedule warning: {unsuitable_count}/{len(enriched_dates)} dates have weather concerns")
                                response_body['has_weather_concerns'] = True
                                response_body['suitable_date_count'] = suitable_count
                                response_body['unsuitable_date_count'] = unsuitable_count

                        except Exception as weather_err:
                            logger.warning(f"Proactive reschedule weather check failed (non-fatal): {weather_err}")
                            # Continue without weather indicators
                    else:
                        logger.warning("No location found for proactive reschedule weather check")

            # PROACTIVE WEATHER WARNINGS FOR reschedule_appointment action: Same as get_rescheduler_slots
            # The reschedule_appointment action returns available_dates when status='awaiting_date_selection'
            if lambda_action == 'reschedule_appointment' and response_body.get('status') == 'awaiting_date_selection':
                available_dates = response_body.get('available_dates', [])
                project_category = workflow_state.get('context', {}).get('category') if workflow_state else None

                if available_dates and project_category and is_outdoor_project(project_category):
                    logger.info(f"[WEATHER] Proactive weather check for reschedule_appointment ({project_category}): {len(available_dates)} dates")

                    # Extract location from workflow state
                    location = extract_location_from_context(workflow_state)

                    if location:
                        try:
                            # Fetch weather forecast
                            weather_params = {
                                'location': location,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            }

                            logger.info(f"[WEATHER] Fetching weather for reschedule_appointment at {location}")
                            weather_response = call_lambda_directly('get_weather', weather_params)

                            # Extract weather data
                            w_data = weather_response.get('response', {})
                            w_func = w_data.get('functionResponse', {})
                            w_body_wrapper = w_func.get('responseBody', {})
                            w_text = w_body_wrapper.get('TEXT', {})
                            w_body_str = w_text.get('body', '{}')

                            if isinstance(w_body_str, str):
                                weather_body = json.loads(w_body_str)
                            else:
                                weather_body = w_body_str

                            # Enrich dates with weather indicators
                            enriched_dates = add_weather_indicators_to_dates(
                                weather_body,
                                available_dates,
                                project_category
                            )

                            # Inject enriched dates into response
                            response_body['dates_with_weather'] = enriched_dates

                            # Also add project info for router's weather enrichment
                            response_body['project_category'] = project_category
                            response_body['project_city'] = workflow_state.get('context', {}).get('city', '')
                            response_body['project_state'] = workflow_state.get('context', {}).get('state', '')

                            # Count suitable vs unsuitable dates
                            suitable_count = sum(1 for d in enriched_dates if d.get('suitable'))
                            unsuitable_count = len(enriched_dates) - suitable_count

                            if unsuitable_count > 0:
                                logger.info(f"[WARNING] Proactive reschedule_appointment warning: {unsuitable_count}/{len(enriched_dates)} dates have weather concerns")
                                response_body['has_weather_concerns'] = True
                                response_body['suitable_date_count'] = suitable_count
                                response_body['unsuitable_date_count'] = unsuitable_count

                        except Exception as weather_err:
                            logger.warning(f"Proactive reschedule_appointment weather check failed (non-fatal): {weather_err}")
                            # Continue without weather indicators
                    else:
                        logger.warning("No location found for proactive reschedule_appointment weather check")

            # WEATHER-AWARE SCHEDULING: Check weather for outdoor projects when showing time slots
            if lambda_action in ['get_time_slots', 'get_available_timeslots']:
                # Get project category from workflow state
                project_category = workflow_state.get('context', {}).get('category') if workflow_state else None

                if project_category and is_outdoor_project(project_category):
                    logger.info(f"[WEATHER]  Outdoor project detected ({project_category}), checking weather...")

                    # Extract location from workflow state
                    location = extract_location_from_context(workflow_state)

                    if location:
                        try:
                            # Get target date from params
                            target_date = lambda_params.get('date')

                            # Call weather API
                            weather_params = {
                                'location': location,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            }

                            logger.info(f"[WEATHER]  Fetching weather for {location} on {target_date}")
                            weather_response = call_lambda_directly('get_weather', weather_params)

                            # Extract weather data
                            weather_data = weather_response.get('response', {})
                            weather_function_response = weather_data.get('functionResponse', {})
                            weather_body_wrapper = weather_function_response.get('responseBody', {})
                            weather_text_wrapper = weather_body_wrapper.get('TEXT', {})
                            weather_body_str = weather_text_wrapper.get('body', '{}')

                            if isinstance(weather_body_str, str):
                                weather_body = json.loads(weather_body_str)
                            else:
                                weather_body = weather_body_str

                            # Get forecast for target date + 5 days
                            # Simple: just show the weather info to the customer
                            weather_info = weather_body.get('weather', {})
                            forecast_list = weather_info.get('forecast', [])

                            if forecast_list:
                                # Find forecasts starting from target date
                                from datetime import datetime, timedelta
                                try:
                                    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
                                    end_dt = target_dt + timedelta(days=5)

                                    # Filter forecast to target date + 5 days
                                    relevant_forecast = []
                                    for day in forecast_list:
                                        day_date = day.get('date', '')
                                        if day_date:
                                            try:
                                                day_dt = datetime.strptime(day_date, "%Y-%m-%d")
                                                if target_dt <= day_dt <= end_dt:
                                                    relevant_forecast.append({
                                                        'date': day_date,
                                                        'condition': day.get('condition', 'Unknown'),
                                                        'high_temp': day.get('max_temp_f'),
                                                        'low_temp': day.get('min_temp_f'),
                                                        'precipitation': day.get('precipitation_probability', 0)
                                                    })
                                            except:
                                                continue

                                    if relevant_forecast:
                                        logger.info(f"[WEATHER] Showing {len(relevant_forecast)} days forecast starting {target_date}")
                                        response_body['weather_forecast'] = relevant_forecast

                                        # Also include current conditions if available
                                        current = weather_info.get('current', {})
                                        if current:
                                            response_body['current_weather'] = {
                                                'temp': current.get('temp_f'),
                                                'condition': current.get('condition', 'Unknown'),
                                                'humidity': current.get('humidity'),
                                                'wind': current.get('wind_mph')
                                            }
                                except Exception as e:
                                    logger.warning(f"Error processing forecast dates: {e}")

                        except Exception as weather_error:
                            logger.warning(f"Weather check failed (non-fatal): {weather_error}")
                            # Continue without weather warning - don't block the flow
                    else:
                        logger.warning(f"No location found in workflow state for weather check")

            # Format response for user (with conversational wrapper from Claude)
            # VOICE ENHANCEMENT: Build voice context for intelligent formatting
            voice_ctx = None
            if channel == 'voice':
                try:
                    voice_ctx = build_voice_context(
                        session_id=session_id,
                        workflow_state=workflow_state,
                        current_action=lambda_action,
                        projects=response_body.get('projects') if lambda_action == 'list_projects' else None
                    )
                except Exception as ctx_err:
                    logger.warning(f"[VOICE_CTX] Failed to build voice context (non-fatal): {ctx_err}")

            formatted_response = format_lambda_response(lambda_action, response_body, message, channel, voice_context=voice_ctx)

            response_text = formatted_response

            # HANDLE ALREADY-SCHEDULED RESCHEDULE OFFER: When get_available_dates returns already_scheduled, save state for confirmation
            if lambda_action == 'get_available_dates' and response_body.get('already_scheduled'):
                project_id = response_body.get('project_id') or lambda_params.get('project_id')
                logger.info(f"[WORKFLOW] Project {project_id} already scheduled - saving state for reschedule offer confirmation")

                # Preserve project_mapping from existing state
                existing_mapping = workflow_state.get('project_mapping', {}) if workflow_state else {}
                existing_context = workflow_state.get('context', {}) if workflow_state else {}

                # Build project_mapping with this project if not already present
                if project_id and str(project_id) not in existing_mapping:
                    existing_mapping[str(project_id)] = existing_context.get('project_info', {})

                # Save workflow state so we can handle "yes" confirmation
                # NOTE: Use 'awaiting_reschedule_confirm' and 'reschedule_offer' to match continuation handler
                state_manager.save_state(session_id, {
                    'workflow_type': 'reschedule_offer',  # Matches handler at line 804
                    'current_stage': 'awaiting_reschedule_confirm',  # Matches handler at line 804
                    'context': {
                        'project_id': project_id,
                        'selected_project_id': project_id,  # Handler expects this
                        'project_ids': [project_id] if project_id else [],
                        'already_scheduled': True,
                        'project_mapping': existing_mapping
                    },
                    'project_mapping': existing_mapping,
                    'conversation_summary': f"Project #{project_id} already scheduled - offered reschedule, awaiting user confirmation"
                })

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'scheduling',
                    'action': 'get_available_dates',
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing
                }

            # HANDLE CANCEL/RESCHEDULE CONFIRMATION WORKFLOW: When cancel or reschedule returns awaiting_confirmation, set workflow state
            # For reschedule, we need to preserve the workflow_type so we can continue to date selection after cancel
            if (lambda_action in ['cancel_appointment', 'reschedule_appointment']) and response_body.get('status') == 'awaiting_confirmation':
                project_id = response_body.get('project_id') or lambda_params.get('project_id')
                project = response_body.get('project', {})

                # Determine if this is a reschedule workflow
                is_reschedule = lambda_action == 'reschedule_appointment'
                wf_type = 'reschedule_appointment' if is_reschedule else 'cancel_appointment'

                logger.info(f"[WORKFLOW] Setting awaiting_cancel_confirmation workflow state for project {project_id}, workflow_type={wf_type}")

                # Preserve project_mapping from existing state
                existing_mapping = workflow_state.get('project_mapping', {}) if workflow_state else {}
                # Save workflow state for confirmation step
                state_manager.save_state(session_id, {
                    'workflow_type': wf_type,  # Preserve reschedule_appointment if that's what started this
                    'current_stage': 'awaiting_cancel_confirmation',
                    'context': {
                        'project_id': project_id,
                        'project': project,
                        'category': project.get('category', ''),
                        'project_type': project.get('projectType', project.get('ProjectType', '')),
                        'scheduled_date': project.get('scheduledDate', ''),
                        'city': project.get('city', project.get('address', {}).get('city', '')),
                        'state': project.get('state', project.get('address', {}).get('state', '')),
                        'project_mapping': existing_mapping
                    },
                    'project_mapping': existing_mapping,
                    'conversation_summary': f"User wants to {'reschedule' if is_reschedule else 'cancel'} project #{project_id}, awaiting confirmation"
                })

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'scheduling',
                    'action': wf_type,
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing
                }

            # HANDLE TWO-STEP RESCHEDULE WORKFLOW: When reschedule returns awaiting_reschedule_confirm, set workflow state
            # NOTE: At this stage, the appointment has NOT been cancelled yet - we're waiting for user consent
            if lambda_action == 'reschedule_appointment' and response_body.get('status') == 'awaiting_reschedule_confirm':
                project_id = response_body.get('project_id') or lambda_params.get('project_id')

                logger.info(f"[RESCHEDULE] Setting awaiting_reschedule_confirm workflow state for project {project_id}")

                # Get project details from workflow state or response
                project_category = workflow_state.get('context', {}).get('category', '') if workflow_state else ''
                project_type_ctx = workflow_state.get('context', {}).get('project_type', '') if workflow_state else ''
                project_city = workflow_state.get('context', {}).get('city', '') if workflow_state else ''
                project_state = workflow_state.get('context', {}).get('state', '') if workflow_state else ''

                # Preserve project_mapping from existing state
                existing_mapping = workflow_state.get('project_mapping', {}) if workflow_state else {}
                # Save workflow state - user must confirm before we cancel
                state_manager.save_state(session_id, {
                    'workflow_type': 'reschedule_appointment',
                    'current_stage': 'awaiting_reschedule_confirm',
                    'context': {
                        'project_id': project_id,
                        'category': project_category,
                        'project_type': project_type_ctx,
                        'city': project_city,
                        'state': project_state,
                        'project_mapping': existing_mapping
                    },
                    'project_mapping': existing_mapping,
                    'conversation_summary': f"User asked about scheduled project #{project_id} - awaiting confirmation to reschedule (appointment NOT cancelled yet)"
                })

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'scheduling',
                    'action': 'reschedule_appointment',
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing
                }

            # HANDLE TWO-STEP CONFIRM WORKFLOW: When confirm_appointment returns awaiting_confirmation
            # User must say "yes" before we actually confirm the appointment
            if lambda_action == 'confirm_appointment' and response_body.get('status') == 'awaiting_confirmation':
                project_id = response_body.get('project_id') or lambda_params.get('project_id')
                date = response_body.get('date') or lambda_params.get('date')
                time_slot = response_body.get('time') or lambda_params.get('time')
                request_id = response_body.get('request_id') or lambda_params.get('request_id')
                category = response_body.get('category') or (workflow_state.get('context', {}).get('category', '') if workflow_state else '')

                logger.info(f"[CONFIRM] Setting awaiting_appointment_confirm workflow state for project {project_id}")

                # Preserve project_mapping from existing state
                existing_mapping = workflow_state.get('project_mapping', {}) if workflow_state else {}
                existing_context = workflow_state.get('context', {}) if workflow_state else {}

                # Save workflow state - user must confirm before we finalize
                state_manager.save_state(session_id, {
                    'workflow_type': 'confirm_appointment',
                    'current_stage': 'awaiting_appointment_confirm',
                    'context': {
                        'project_id': project_id,
                        'date': date,
                        'time': time_slot,
                        'request_id': request_id,
                        'category': category,
                        'project_mapping': existing_mapping,
                        'address': existing_context.get('address', ''),
                        'project_type': existing_context.get('project_type', '')
                    },
                    'project_mapping': existing_mapping,
                    'conversation_summary': f"User selected {date} at {time_slot} for project #{project_id} - awaiting final confirmation"
                })

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'scheduling',
                    'action': 'confirm_appointment',
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing
                }

            # CRITICAL: Extract request_id from Lambda response and add to workflow state
            # request_id is required for get_time_slots and confirm_appointment
            # FIX: Create update_workflow_state if missing - ensures request_id is always saved
            if 'request_id' in response_body and response_body['request_id']:
                logger.info(f"[STATE] Extracted request_id from Lambda response: {response_body['request_id']}")

                # Ensure update_workflow_state exists - create if Sonnet didn't provide one
                if not decision.get('update_workflow_state'):
                    # Preserve existing workflow context if available
                    existing_context = workflow_state.get('context', {}) if workflow_state else {}
                    decision['update_workflow_state'] = {
                        'workflow_type': workflow_state.get('workflow_type', 'schedule_appointment') if workflow_state else 'schedule_appointment',
                        'current_stage': 'awaiting_date_selection',
                        'context': {
                            'project_id': existing_context.get('project_id') or lambda_params.get('project_id'),
                            'category': existing_context.get('category'),
                            'city': existing_context.get('city'),
                            'state': existing_context.get('state')
                        }
                    }
                    logger.info(f"[STATE] Created update_workflow_state for request_id preservation")

                if 'context' not in decision['update_workflow_state']:
                    decision['update_workflow_state']['context'] = {}
                decision['update_workflow_state']['context']['request_id'] = response_body['request_id']
                logger.info(f"[STATE] Added request_id to workflow state context: {response_body['request_id']}")

            # Save available_dates AND start_date to workflow state for get_time_slots
            if 'available_dates' in response_body and response_body['available_dates']:
                logger.info(f"[DATES] Saving {len(response_body['available_dates'])} available dates to workflow state")

                # Ensure update_workflow_state exists for dates
                if not decision.get('update_workflow_state'):
                    existing_context = workflow_state.get('context', {}) if workflow_state else {}
                    decision['update_workflow_state'] = {
                        'workflow_type': workflow_state.get('workflow_type', 'schedule_appointment') if workflow_state else 'schedule_appointment',
                        'current_stage': 'awaiting_date_selection',
                        'context': {
                            'project_id': existing_context.get('project_id') or lambda_params.get('project_id'),
                            'category': existing_context.get('category'),
                            'city': existing_context.get('city'),
                            'state': existing_context.get('state')
                        }
                    }
                    logger.info(f"[STATE] Created update_workflow_state for available_dates preservation")

                if 'context' not in decision['update_workflow_state']:
                    decision['update_workflow_state']['context'] = {}
                decision['update_workflow_state']['context']['available_dates'] = response_body['available_dates']

                # CRITICAL: Save start_date (base_date) for get_time_slots URL construction
                if response_body.get('start_date'):
                    decision['update_workflow_state']['context']['start_date'] = response_body['start_date']
                    logger.info(f"[DATES] Saved start_date/base_date: {response_body['start_date']}")

            # CHAD FEEDBACK FIX: Save time_slots to workflow state for "Yes" auto-select
            # When user says "Yes" or "That works" after times are shown, auto-select first slot
            # scheduling-actions returns: available_slots, timeSlots, slots (rescheduler), or time_slots
            time_slots_data = response_body.get('available_slots') or response_body.get('timeSlots') or response_body.get('slots') or response_body.get('time_slots')
            if lambda_action == 'get_time_slots' and time_slots_data:
                logger.info(f"[TIME_SLOTS] Saving {len(time_slots_data)} time slots to workflow state")

                # Ensure update_workflow_state exists for time slots
                if not decision.get('update_workflow_state'):
                    existing_context = workflow_state.get('context', {}) if workflow_state else {}
                    decision['update_workflow_state'] = {
                        'workflow_type': workflow_state.get('workflow_type', 'schedule_appointment') if workflow_state else 'schedule_appointment',
                        'current_stage': 'awaiting_time_selection',
                        'context': {
                            'project_id': existing_context.get('project_id') or lambda_params.get('project_id'),
                            'date': lambda_params.get('date') or existing_context.get('date'),
                            'request_id': existing_context.get('request_id'),
                            'category': existing_context.get('category'),
                            'city': existing_context.get('city'),
                            'state': existing_context.get('state')
                        }
                    }
                    logger.info(f"[TIME_SLOTS] Created update_workflow_state for time_slots preservation")

                if 'context' not in decision['update_workflow_state']:
                    decision['update_workflow_state']['context'] = {}

                # Set stage to awaiting_time_selection
                decision['update_workflow_state']['current_stage'] = 'awaiting_time_selection'
                decision['update_workflow_state']['context']['time_slots'] = time_slots_data
                decision['update_workflow_state']['context']['date'] = lambda_params.get('date') or decision['update_workflow_state']['context'].get('date')
                logger.info(f"[TIME_SLOTS] Saved time_slots and set stage to awaiting_time_selection")

            # ========================================================================
            # PAST DATE CLEANUP: When user requests a date that's entirely in the past,
            # clear the date from context so it doesn't persist to subsequent requests
            # ========================================================================
            if lambda_action == 'get_available_dates' and response_body.get('week_in_past'):
                logger.info(f"[DATE-CLEANUP] Week/date is in the past - clearing stale date from context")
                # Ensure update_workflow_state exists
                if not decision.get('update_workflow_state'):
                    existing_context = workflow_state.get('context', {}) if workflow_state else {}
                    decision['update_workflow_state'] = {
                        'workflow_type': workflow_state.get('workflow_type', 'schedule_appointment') if workflow_state else 'schedule_appointment',
                        'current_stage': 'awaiting_date_selection',
                        'context': {
                            'project_id': existing_context.get('project_id') or lambda_params.get('project_id'),
                            'category': existing_context.get('category'),
                            'city': existing_context.get('city'),
                            'state': existing_context.get('state'),
                            'project_mapping': existing_context.get('project_mapping', {})
                        }
                    }
                if 'context' not in decision['update_workflow_state']:
                    decision['update_workflow_state']['context'] = {}
                # Clear date, start_date, and available_dates since they're stale
                decision['update_workflow_state']['context']['date'] = None
                decision['update_workflow_state']['context']['start_date'] = None
                decision['update_workflow_state']['context']['available_dates'] = []
                logger.info(f"[DATE-CLEANUP] Cleared date, start_date, available_dates from context")

            # ========================================================================
            # CIRCUIT BREAKER: Track "no dates available" responses to prevent loops
            # After 2 empty date responses in a session, offer alternative paths.
            # This prevents the frustrating loop seen in Amy's call (11 "booked up" messages)
            # ========================================================================
            # Log circuit breaker check for debugging
            date_count = response_body.get('dateCount', len(response_body.get('available_dates', [])))
            logger.info(f"[CIRCUIT-BREAKER-CHECK] action={lambda_action}, dateCount={date_count}, available_dates={len(response_body.get('available_dates', []))}")

            if lambda_action in ['get_available_dates', 'reschedule_appointment'] and date_count == 0:
                # Get current no_dates_count from workflow state
                existing_context = workflow_state.get('context', {}) if workflow_state else {}
                no_dates_count = existing_context.get('no_dates_count', 0) + 1

                logger.info(f"[CIRCUIT-BREAKER] No dates available (count: {no_dates_count})")

                # Ensure we have workflow state to save the counter
                if not decision.get('update_workflow_state'):
                    decision['update_workflow_state'] = {
                        'workflow_type': workflow_state.get('workflow_type', 'schedule_appointment') if workflow_state else 'schedule_appointment',
                        'current_stage': 'awaiting_date_selection',
                        'context': {}
                    }
                if 'context' not in decision['update_workflow_state']:
                    decision['update_workflow_state']['context'] = {}

                decision['update_workflow_state']['context']['no_dates_count'] = no_dates_count

                # After 2 "no dates" responses, trigger circuit breaker
                if no_dates_count >= 2:
                    logger.info(f"[CIRCUIT-BREAKER] Triggered after {no_dates_count} empty responses - offering alternatives")
                    response_body['circuit_breaker_triggered'] = True
                    response_body['circuit_breaker_count'] = no_dates_count
                    # Add message for voice formatter to use
                    response_body['message'] = "Our schedule is quite full right now. Would you like me to check a specific date you have in mind, or would you prefer to call our office to speak with someone who can help?"

            # SAVE PROJECT_IDS AND PROJECT_MAPPING: Save to workflow state when listing projects
            # This enables ordinal references like "last project", "first project", "2nd project"
            # AND category-based lookups AND weather queries for BOTH voice and chat channels
            if 'projects' in response_body and isinstance(response_body['projects'], list):
                projects_list = response_body['projects']
                project_ids = [str(p.get('id', '')) for p in projects_list if p.get('id')]

                # Build project_mapping: project_id -> {category, category_bucket, address, status, project_type}
                # category_bucket enables "show kitchen projects" to match Dishwasher, Ovens, etc.
                # Also map by projectNumber for lookup when user references by order number
                project_mapping = {}
                for p in projects_list:
                    pid = str(p.get('id', ''))
                    if pid:
                        exact_category = p.get('category', '')
                        project_number = p.get('projectNumber', '')
                        project_mapping[pid] = {
                            'category': exact_category,
                            'category_bucket': get_category_bucket(exact_category),
                            'address': p.get('address', ''),
                            'status': p.get('status', ''),
                            'projectNumber': project_number,
                            'project_type': p.get('projectType', p.get('ProjectType', ''))
                        }
                        # Also map by projectNumber (Order Number) for reverse lookup
                        if project_number:
                            project_mapping[project_number] = {
                                'category': exact_category,
                                'category_bucket': get_category_bucket(exact_category),
                                'address': p.get('address', ''),
                                'status': p.get('status', ''),
                                'project_id': pid,  # Internal project ID for API calls
                                'project_type': p.get('projectType', p.get('ProjectType', ''))
                            }

                if project_ids:
                    logger.info(f"[PROJECTS] Saving {len(project_ids)} project_ids and project_mapping to workflow state (channel={channel})")

                    if decision.get('update_workflow_state'):
                        if 'context' not in decision['update_workflow_state']:
                            decision['update_workflow_state']['context'] = {}
                        decision['update_workflow_state']['context']['project_ids'] = project_ids
                        decision['update_workflow_state']['context']['project_mapping'] = project_mapping
                        decision['update_workflow_state']['project_mapping'] = project_mapping  # Top-level for save_state()
                    else:
                        # Create update_workflow_state if Sonnet didn't provide one
                        # IMPORTANT: project_mapping must be at top level AND in context for save_state() to find it
                        decision['update_workflow_state'] = {
                            'workflow_type': 'project_listing',
                            'current_stage': 'listing_projects',
                            'context': {
                                'project_ids': project_ids,
                                'project_mapping': project_mapping
                            },
                            'project_mapping': project_mapping  # Top-level for save_state()
                        }
                        logger.info(f"[PROJECTS] Created workflow state with project_ids and project_mapping")

                    # VOICE ENHANCEMENT: Cache upcoming appointments for proactive highlights
                    if channel == 'voice':
                        cache_upcoming_appointments(state_manager, session_id, projects_list)

            # SAVE CURRENT PROJECT_ID: When viewing a single project, save its ID for follow-up queries
            # This enables "details for ovens project" -> "what's the weather" to work correctly
            if 'project' in response_body and isinstance(response_body['project'], dict):
                single_project = response_body['project']
                viewed_project_id = str(single_project.get('id', ''))

                if viewed_project_id:
                    logger.info(f"[PROJECT] User viewed project #{viewed_project_id}, saving to workflow state (channel={channel})")

                    # Build project info for this single project
                    address_data = single_project.get('address', {})
                    viewed_project_info = {
                        'category': single_project.get('category', ''),
                        'address': address_data,
                        'status': single_project.get('status', '')
                    }
                    # Extract city/state for weather queries
                    if isinstance(address_data, dict):
                        project_city = address_data.get('city', '')
                        project_state = address_data.get('state', '')
                    else:
                        # Parse from string address (e.g., "..., Fort White, FL 32038")
                        addr_match = re.search(r',\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*\d*', str(address_data))
                        if addr_match:
                            project_city = addr_match.group(1).strip()
                            project_state = addr_match.group(2)
                        else:
                            project_city = ''
                            project_state = ''

                    if decision.get('update_workflow_state'):
                        if 'context' not in decision['update_workflow_state']:
                            decision['update_workflow_state']['context'] = {}
                        decision['update_workflow_state']['context']['project_id'] = viewed_project_id
                        # Save city/state for weather queries ("what's the weather" after viewing project)
                        if project_city:
                            decision['update_workflow_state']['context']['city'] = project_city
                        if project_state:
                            decision['update_workflow_state']['context']['state'] = project_state
                        # Also update project_mapping with this project's info
                        existing_mapping = decision['update_workflow_state']['context'].get('project_mapping', {})
                        existing_mapping[viewed_project_id] = viewed_project_info
                        decision['update_workflow_state']['context']['project_mapping'] = existing_mapping
                    else:
                        # Create update_workflow_state if Sonnet didn't provide one
                        decision['update_workflow_state'] = {
                            'workflow_type': 'project_view',
                            'current_stage': 'viewing_project',
                            'context': {
                                'project_id': viewed_project_id,
                                'project_mapping': {viewed_project_id: viewed_project_info},
                                'city': project_city,
                                'state': project_state
                            },
                            'project_mapping': {viewed_project_id: viewed_project_info}  # Top-level for save_state()
                        }
                        logger.info(f"[PROJECT] Created workflow state with project_id={viewed_project_id}, city={project_city}, state={project_state}")

                    # TRACK VIEWED PROJECT: Add to viewed_projects history for ordinal references
                    # This enables "2nd project" after user has viewed multiple projects
                    try:
                        address_info = single_project.get('address', {})
                        state_manager.add_viewed_project(session_id, {
                            'project_id': viewed_project_id,
                            'category': single_project.get('category', ''),
                            'status': single_project.get('status', ''),
                            'city': address_info.get('city', '') if isinstance(address_info, dict) else '',
                            'state': address_info.get('state', '') if isinstance(address_info, dict) else '',
                            'address': address_info.get('address', '') if isinstance(address_info, dict) else str(address_info)
                        })
                        logger.info(f"[VIEWED] Added project #{viewed_project_id} to viewed_projects history")
                    except Exception as track_err:
                        logger.warning(f"[VIEWED] Failed to track viewed project (non-critical): {track_err}")

            # BATCH SCHEDULING: Auto-advance to next project after confirm_appointment
            if lambda_action == 'confirm_appointment':
                batch_context = workflow_state.get('context', {}) if workflow_state else {}

                if batch_context.get('batch_mode'):
                    current_index = batch_context.get('current_index', 0)
                    project_ids = batch_context.get('project_ids', [])
                    completed = batch_context.get('completed_projects', [])

                    # Mark current project as completed
                    current_project_id = batch_context.get('project_id')
                    if current_project_id:
                        completed.append(current_project_id)

                    next_index = current_index + 1
                    logger.info(f"[BATCH] Batch progress: completed {len(completed)}/{len(project_ids)}")

                    if next_index < len(project_ids):
                        # More projects to schedule
                        next_project_id = project_ids[next_index]
                        logger.info(f"[BATCH] Advancing to next project: #{next_project_id} ({next_index + 1} of {len(project_ids)})")

                        # Fetch available dates for next project
                        try:
                            next_dates_response = call_lambda_directly('get_available_dates', {
                                'project_id': next_project_id,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            })

                            # Extract dates from response
                            next_dates_data = next_dates_response.get('response', {})
                            next_dates_func = next_dates_data.get('functionResponse', {})
                            next_dates_body_wrapper = next_dates_func.get('responseBody', {})
                            next_dates_text = next_dates_body_wrapper.get('TEXT', {})
                            next_dates_body_str = next_dates_text.get('body', '{}')

                            if isinstance(next_dates_body_str, str):
                                next_dates_body = json.loads(next_dates_body_str)
                            else:
                                next_dates_body = next_dates_body_str

                            # Fetch project details for next project (for weather checking)
                            next_project_category = None
                            next_project_city = None
                            next_project_state = None
                            try:
                                next_details_response = call_lambda_directly('get_project_details', {
                                    'project_id': next_project_id,
                                    'customer_id': customer_id,
                                    'client_id': client_id,
                                    'pf_bearer_token': pf_bearer_token
                                })
                                next_details_data = next_details_response.get('response', {})
                                next_details_func = next_details_data.get('functionResponse', {})
                                next_details_body_wrapper = next_details_func.get('responseBody', {})
                                next_details_text = next_details_body_wrapper.get('TEXT', {})
                                next_details_body_str = next_details_text.get('body', '{}')

                                if isinstance(next_details_body_str, str):
                                    next_project_info = json.loads(next_details_body_str)
                                else:
                                    next_project_info = next_details_body_str

                                next_project_category = next_project_info.get('category', '')
                                next_proj_obj = next_project_info.get('project', {})
                                next_addr_obj = next_proj_obj.get('address', {}) if isinstance(next_proj_obj, dict) else {}
                                if isinstance(next_addr_obj, dict) and next_addr_obj:
                                    next_project_city = next_addr_obj.get('city', '')
                                    next_project_state = next_addr_obj.get('state', '')
                                logger.info(f"[PROJECT] Next project details: category={next_project_category}, city={next_project_city}")

                            except Exception as next_details_err:
                                logger.warning(f"Failed to fetch next project details (non-fatal): {next_details_err}")

                            # PROACTIVE WEATHER: Add weather indicators for next project dates
                            next_available_dates = next_dates_body.get('available_dates', [])
                            if next_available_dates and next_project_category and is_outdoor_project(next_project_category):
                                next_location = f"{next_project_city}, {next_project_state}" if next_project_city and next_project_state else None
                                if next_location:
                                    try:
                                        logger.info(f"[WEATHER] Proactive weather for next batch project ({next_project_category})")
                                        next_weather_response = call_lambda_directly('get_weather', {
                                            'location': next_location,
                                            'customer_id': customer_id,
                                            'client_id': client_id,
                                            'pf_bearer_token': pf_bearer_token
                                        })
                                        nw_data = next_weather_response.get('response', {})
                                        nw_func = nw_data.get('functionResponse', {})
                                        nw_body_wrapper = nw_func.get('responseBody', {})
                                        nw_text = nw_body_wrapper.get('TEXT', {})
                                        nw_body_str = nw_text.get('body', '{}')

                                        if isinstance(nw_body_str, str):
                                            next_weather_body = json.loads(nw_body_str)
                                        else:
                                            next_weather_body = nw_body_str

                                        # Enrich dates with weather indicators
                                        next_enriched_dates = add_weather_indicators_to_dates(
                                            next_weather_body,
                                            next_available_dates,
                                            next_project_category
                                        )
                                        next_dates_body['dates_with_weather'] = next_enriched_dates

                                        # Count warnings
                                        next_unsuitable = sum(1 for d in next_enriched_dates if not d.get('suitable'))
                                        next_suitable = len(next_enriched_dates) - next_unsuitable
                                        if next_unsuitable > 0:
                                            next_dates_body['has_weather_concerns'] = True
                                            next_dates_body['suitable_date_count'] = next_suitable
                                            next_dates_body['unsuitable_date_count'] = next_unsuitable
                                            logger.info(f"[WARNING] Next project has {next_unsuitable}/{len(next_enriched_dates)} dates with weather concerns")

                                    except Exception as next_weather_err:
                                        logger.warning(f"Weather check for next batch project failed (non-fatal): {next_weather_err}")

                            # Format the next project's dates (with weather if available)
                            next_dates_formatted = format_lambda_response('get_available_dates', next_dates_body, message, channel)
                            logger.info(f"[BATCH] Next dates formatted length: {len(next_dates_formatted)} chars")

                            # Append to response
                            logger.info(f"[BATCH] Response text BEFORE append: {len(response_text)} chars")
                            response_text += f"\n\n---\n\n**Now let's schedule project #{next_project_id} ({next_index + 1} of {len(project_ids)})**\n\n{next_dates_formatted}"
                            logger.info(f"[BATCH] Response text AFTER append: {len(response_text)} chars")

                            # Update workflow state for next project
                            decision['update_workflow_state'] = {
                                'workflow_type': 'batch_schedule_appointment',
                                'current_stage': 'awaiting_date_selection',
                                'context': {
                                    'batch_mode': True,
                                    'project_ids': project_ids,
                                    'current_index': next_index,
                                    'total_projects': len(project_ids),
                                    'completed_projects': completed,
                                    'project_id': next_project_id,
                                    'available_dates': next_dates_body.get('available_dates', []),
                                    'request_id': next_dates_body.get('request_id'),
                                    # Save project info for weather checking on date selection
                                    'category': next_project_category,
                                    'city': next_project_city,
                                    'state': next_project_state
                                }
                            }
                            decision['workflow_complete'] = False

                        except Exception as batch_error:
                            logger.error(f"Failed to fetch dates for next project in batch: {batch_error}")
                            response_text += f"\n\nI encountered an issue moving to the next project. Please try scheduling project #{next_project_id} separately."

                    else:
                        # All projects scheduled!
                        logger.info(f"[BATCH] Batch complete! All {len(project_ids)} projects scheduled")
                        response_text += f"\n\n---\n\n**All done!** All {len(project_ids)} projects are now scheduled."
                        decision['workflow_complete'] = True

        except Exception as e:
            logger.error(f"Lambda call failed: {e}")
            # Provide a natural, helpful error message instead of exposing error details
            error_str = str(e).lower()

            # ERROR RECOVERY: Clear corrupted workflow state on serious errors
            # This prevents subsequent requests from failing due to stale/corrupt state
            should_clear_state = False

            if 'timeout' in error_str or 'timed out' in error_str:
                response_text = "That's taking longer than expected. Mind trying again?"
            elif 'token' in error_str or 'auth' in error_str or 'expired' in error_str or '401' in error_str or '403' in error_str:
                # IMPORTANT: Set pf_http_status_code to 401 so frontend knows to prompt re-login
                pf_http_status_code = 401
                response_text = "Your session has expired. Please log in again to continue."
                should_clear_state = True  # Auth errors often corrupt state
                logger.info(f"[AUTH] Session expired - setting pf_http_status_code=401 for frontend re-login prompt")
            elif 'project' in error_str and 'not found' in error_str:
                response_text = "I couldn't find that project. Want me to show you your project list?"
            else:
                response_text = "Oops, something went sideways. Mind trying that again?"

            # Clear workflow state on serious errors to allow recovery
            if should_clear_state:
                try:
                    # Preserve project_ids and project_mapping if they exist (for list recovery)
                    existing_state = workflow_state or {}
                    preserved_mapping = existing_state.get('project_mapping', {})
                    preserved_ids = existing_state.get('context', {}).get('project_ids', [])

                    if preserved_mapping or preserved_ids:
                        # Reset to clean state but preserve project list info
                        state_manager.save_state(session_id, {
                            'workflow_type': 'error_recovery',
                            'current_stage': 'clean',
                            'context': {
                                'project_ids': preserved_ids,
                                'project_mapping': preserved_mapping
                            },
                            'project_mapping': preserved_mapping,
                            'conversation_summary': f'Recovered from error: {str(e)[:100]}'
                        })
                        logger.info(f"[ERROR_RECOVERY] Reset workflow state, preserved {len(preserved_ids)} project_ids")
                    else:
                        # No project info to preserve, clear completely
                        state_manager.clear_state(session_id)
                        logger.info("[ERROR_RECOVERY] Cleared corrupted workflow state")
                except Exception as clear_err:
                    logger.warning(f"[ERROR_RECOVERY] Failed to clear state (non-critical): {clear_err}")

            # Prevent state update after error
            decision['update_workflow_state'] = None

    else:
        # FALLBACK: If classification says get_project_details and we have a project_id,
        # try calling the Lambda anyway even if Sonnet said should_call_lambda=False
        classified_action = classification.get('action', '') if classification else ''
        classified_project_id = classification.get('entities', {}).get('project_id') if classification else None

        if classified_action == 'get_project_details' and classified_project_id:
            logger.info(f"[FALLBACK] Sonnet said should_call_lambda=False but classification has get_project_details with project_id={classified_project_id} - trying Lambda anyway")

            try:
                # First try partial matching against project_mapping if available
                actual_project_id = classified_project_id
                if workflow_state:
                    project_mapping = workflow_state.get('project_mapping', {}) or workflow_state.get('context', {}).get('project_mapping', {})
                    if project_mapping:
                        matched_id = find_project_by_partial_id(str(classified_project_id), project_mapping)
                        if matched_id:
                            actual_project_id = matched_id
                            logger.info(f"[FALLBACK] Partial match: {classified_project_id} -> {actual_project_id}")

                fallback_response = call_lambda_directly('get_project_details', {
                    'project_id': actual_project_id,
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_bearer_token
                })

                # Extract response
                fallback_data = fallback_response.get('response', {})
                fallback_func = fallback_data.get('functionResponse', {})
                fallback_body_wrapper = fallback_func.get('responseBody', {})
                fallback_text = fallback_body_wrapper.get('TEXT', {})
                fallback_body_str = fallback_text.get('body', '{}')

                if isinstance(fallback_body_str, str):
                    fallback_body = json.loads(fallback_body_str)
                else:
                    fallback_body = fallback_body_str

                # Check for errors in response
                if fallback_body.get('error'):
                    logger.warning(f"[FALLBACK] Lambda returned error: {fallback_body.get('error')}")
                    response_text = decision.get('response_to_user', f"I couldn't find project #{classified_project_id}. Would you like me to show your project list?")
                else:
                    # Success! Format the response
                    project = fallback_body.get('project', fallback_body)
                    category = project.get('category', project.get('Category', 'Unknown'))
                    status = project.get('status', project.get('Status', ''))
                    project_type = project.get('projectType', project.get('ProjectType', ''))

                    # Check what info was requested
                    info_type = classification.get('entities', {}).get('information_type', '')

                    if info_type == 'category':
                        response_text = f"Project #{actual_project_id} is a **{category}** project"
                        if status:
                            response_text += f" with status **{status}**"
                        response_text += "."
                    else:
                        # Generic project details response
                        response_text = f"**Project #{actual_project_id}**\n\n"
                        response_text += f"**Category:** {category}\n"
                        if status:
                            response_text += f"**Status:** {status}\n"
                        if project_type:
                            response_text += f"**Type:** {project_type}\n"

                    logger.info(f"[FALLBACK] Successfully fetched project details for {actual_project_id}")

            except Exception as fallback_err:
                logger.error(f"[FALLBACK] get_project_details failed: {fallback_err}")
                response_text = decision.get('response_to_user', "How can I help you?")
        else:
            # Use Sonnet's direct response
            response_text = decision.get('response_to_user', "How can I help you?")

    # Step 4: Update workflow state
    if decision.get('update_workflow_state'):
        new_state = decision['update_workflow_state']

        # CRITICAL: Preserve batch context from existing workflow state
        # Sonnet's update_workflow_state may not include batch fields, so we must merge them
        if workflow_state and workflow_state.get('context', {}).get('batch_mode'):
            existing_batch_context = workflow_state.get('context', {})
            batch_fields = ['batch_mode', 'project_ids', 'current_index', 'total_projects', 'completed_projects']

            if 'context' not in new_state:
                new_state['context'] = {}

            for field in batch_fields:
                if field in existing_batch_context and field not in new_state['context']:
                    new_state['context'][field] = existing_batch_context[field]
                    logger.info(f"[BATCH] Preserved batch field: {field}={existing_batch_context[field]}")

        # CRITICAL: Preserve project_mapping - Sonnet's response never includes it
        if workflow_state:
            existing_mapping = workflow_state.get('project_mapping', {}) or workflow_state.get('context', {}).get('project_mapping', {})
            if existing_mapping and not new_state.get('project_mapping'):
                new_state['project_mapping'] = existing_mapping
                if 'context' not in new_state:
                    new_state['context'] = {}
                if not new_state['context'].get('project_mapping'):
                    new_state['context']['project_mapping'] = existing_mapping
                logger.info(f"[STATE] Preserved project_mapping ({len(existing_mapping)} projects) in new_state")

        # WORKFLOW SWITCH FIX: When user switches from reschedule to schedule (or vice versa),
        # Sonnet's update_workflow_state may still have the OLD workflow_type from its context.
        # Override with the correct new workflow type to prevent "schedule" using "reschedule" API.
        if forced_workflow_type and new_state.get('workflow_type') != forced_workflow_type:
            old_wf_type = new_state.get('workflow_type', 'unset')
            new_state['workflow_type'] = forced_workflow_type
            logger.info(f"[WORKFLOW SWITCH] Overriding Sonnet's workflow_type '{old_wf_type}' -> '{forced_workflow_type}'")

        state_manager.save_state(session_id, new_state)

    # Step 5: Clear workflow if complete
    # VOICE FIX: Don't clear workflow state after list_projects - we need project_ids for follow-up queries
    # like "tell me about the third project"
    lambda_action = decision.get('lambda_action', '')
    if decision.get('workflow_complete'):
        # Preserve workflow state for actions that need follow-up context
        # project_mapping is needed for category-based queries like "details for dishwasher"
        actions_that_need_context = {'list_projects', 'get_project_details'}
        if lambda_action in actions_that_need_context:
            logger.info(f"[STATE] Keeping workflow state after {lambda_action} (project_mapping needed for follow-up)")
        else:
            state_manager.reset_workflow_state(session_id)
            logger.info("[OK] Workflow complete, state reset (memory preserved)")

    timing['total'] = time.time() - start_time

    logger.info(f"[TIMING]  Intelligent Orchestration: Total={timing['total']:.2f}s | Classification={timing.get('classification', 0):.2f}s | Decision={timing.get('decision', 0):.2f}s")
    logger.info(f"[BATCH] FINAL response_text length: {len(response_text)} chars")

    return {
        'response': response_text,
        'intent': classification.get('intent', 'unknown'),
        'action': decision.get('lambda_action') or classification.get('action'),
        'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
        'direct_call': True,
        'timing': timing,
        'pf_http_status_code': pf_http_status_code
    }
