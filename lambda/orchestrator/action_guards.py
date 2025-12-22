"""
Action Guards - Rule-based validation layer

These guards prevent common classification errors by applying
simple, deterministic rules AFTER Sonnet classification but
BEFORE action execution.

Guards are Python functions, NOT LLM prompts - they're fast,
predictable, and testable.
"""

import logging
import re
from typing import Dict, Optional, Tuple

logger = logging.getLogger()


# ═══════════════════════════════════════════════════════════════════════════════
# GUARD DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

def guard_no_auto_schedule(message: str, nlu_action: str, sonnet_action: str, context: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    GUARD: Don't auto-escalate to scheduling

    Problem: Sonnet sees "Ready To Schedule" and assumes user wants to schedule
    Solution: Only use get_available_dates if user explicitly asks

    Returns: (override_action, reason) or (None, None) if guard doesn't apply
    """
    if sonnet_action != 'get_available_dates':
        return None, None

    msg_lower = message.lower().strip()

    # Explicit schedule keywords - these ARE scheduling requests
    schedule_keywords = [
        'schedule', 'book', 'appointment', 'get dates', 'find dates',
        'when can', 'available dates', 'open slots', 'set up', 'arrange'
    ]

    if any(kw in msg_lower for kw in schedule_keywords):
        return None, None  # User explicitly wants to schedule

    # "just X" pattern after listing = filtering, not scheduling
    if msg_lower.startswith('just ') or msg_lower.startswith('only '):
        return nlu_action or 'get_project_details', "GUARD: 'just X' is filtering, not scheduling"

    # "the X one" pattern = selecting/viewing, not scheduling
    if re.search(r'the \w+ one', msg_lower):
        return nlu_action or 'get_project_details', "GUARD: 'the X one' is selecting, not scheduling"

    # "show me X" = viewing, not scheduling
    if 'show me' in msg_lower or 'show the' in msg_lower:
        return nlu_action or 'get_project_details', "GUARD: 'show me X' is viewing, not scheduling"

    # Default: if NLU said something different, trust NLU
    if nlu_action and nlu_action != 'get_available_dates':
        return nlu_action, f"GUARD: NLU={nlu_action}, no schedule keyword found"

    return None, None


def guard_calendar_query(message: str, nlu_action: str, sonnet_action: str, context: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    GUARD: Calendar queries bypass workflow context

    Problem: User asks "what's on my calendar" but system returns previous project
    Solution: Calendar queries always fetch fresh scheduled projects

    Returns: (override_action, reason) or (None, None) if guard doesn't apply
    """
    msg_lower = message.lower().strip()

    calendar_patterns = [
        "what's on my calendar", "whats on my calendar", "what is on my calendar",
        "what's scheduled", "whats scheduled", "what is scheduled",
        "show scheduled", "my scheduled", "show my schedule",
        "upcoming appointments", "my appointments", "what appointments"
    ]

    if any(pattern in msg_lower for pattern in calendar_patterns):
        return 'list_projects', "GUARD: Calendar query - fetch scheduled projects"

    return None, None


def guard_filter_after_list(message: str, nlu_action: str, sonnet_action: str, context: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    GUARD: Filtering after a list should stay as list_projects

    Problem: User says "just kitchen stuff" after list, Sonnet escalates to details/scheduling
    Solution: Filtering keywords keep the list_projects action

    Returns: (override_action, reason) or (None, None) if guard doesn't apply
    """
    msg_lower = message.lower().strip()

    # Check if previous action was list_projects
    prev_action = context.get('previous_action')
    if prev_action != 'list_projects':
        return None, None

    # Filtering patterns
    filter_patterns = [
        r'^just\s+\w+',           # "just kitchen"
        r'^only\s+\w+',           # "only decking"
        r'^show\s+\w+\s+only',    # "show kitchen only"
        r'^\w+\s+stuff$',         # "kitchen stuff"
        r'^\w+\s+ones?$',         # "kitchen ones"
        r'^\w+\s+projects?$',     # "kitchen projects"
    ]

    for pattern in filter_patterns:
        if re.match(pattern, msg_lower):
            return 'list_projects', f"GUARD: Filter pattern '{pattern}' after list"

    return None, None


def guard_context_query_needs_context(message: str, nlu_action: str, sonnet_action: str, context: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    GUARD: context_query only works if we have context

    Problem: Sonnet returns context_query but there's no project in context
    Solution: Fall back to asking user to specify project

    Returns: (override_action, reason) or (None, None) if guard doesn't apply
    """
    if sonnet_action != 'context_query':
        return None, None

    # Check if we have project context
    workflow_state = context.get('workflow_state', {})
    project_mapping = workflow_state.get('project_mapping', {})
    current_project = workflow_state.get('context', {}).get('project_id')

    if current_project or project_mapping:
        return None, None  # We have context, allow context_query

    # No context available - can't answer context query
    return 'list_projects', "GUARD: No project context for context_query, show projects first"


def guard_cancel_needs_scheduled(message: str, nlu_action: str, sonnet_action: str, context: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    GUARD: Can't cancel a project that isn't scheduled

    Problem: User says "cancel" but project isn't scheduled
    Solution: Check project status before allowing cancel

    Returns: (override_action, reason) or (None, None) if guard doesn't apply
    """
    if sonnet_action != 'cancel_appointment':
        return None, None

    # Get project status from context
    entities = context.get('entities', {})
    project_id = entities.get('project_id')

    if not project_id:
        return None, None  # Let it proceed, will handle missing project_id later

    # Check project_mapping for status
    workflow_state = context.get('workflow_state', {})
    project_mapping = workflow_state.get('project_mapping', {})
    project_info = project_mapping.get(project_id, {})
    status = project_info.get('status', '').lower()

    scheduled_statuses = ['scheduled', 'tentatively scheduled', 'customer scheduled']

    if status and status not in scheduled_statuses:
        return 'get_project_details', f"GUARD: Can't cancel project with status '{status}'"

    return None, None


def guard_reschedule_needs_scheduled(message: str, nlu_action: str, sonnet_action: str, context: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    GUARD: Can't reschedule a project that isn't scheduled

    Similar to cancel guard - check status before allowing reschedule

    Returns: (override_action, reason) or (None, None) if guard doesn't apply
    """
    if sonnet_action != 'reschedule_appointment':
        return None, None

    entities = context.get('entities', {})
    project_id = entities.get('project_id')

    if not project_id:
        return None, None

    workflow_state = context.get('workflow_state', {})
    project_mapping = workflow_state.get('project_mapping', {})
    project_info = project_mapping.get(project_id, {})
    status = project_info.get('status', '').lower()

    scheduled_statuses = ['scheduled', 'tentatively scheduled', 'customer scheduled']

    if status and status not in scheduled_statuses:
        return 'get_project_details', f"GUARD: Can't reschedule project with status '{status}'"

    return None, None


# ═══════════════════════════════════════════════════════════════════════════════
# GUARD RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

# List of all guards in priority order
ALL_GUARDS = [
    guard_calendar_query,        # Highest priority - bypass workflow
    guard_no_auto_schedule,      # Prevent auto-escalation
    guard_filter_after_list,     # Keep filtering as list_projects
    guard_context_query_needs_context,
    guard_cancel_needs_scheduled,
    guard_reschedule_needs_scheduled,
]


def apply_guards(
    message: str,
    nlu_action: Optional[str],
    sonnet_action: str,
    context: Dict
) -> Tuple[str, Optional[str]]:
    """
    Apply all guards and return final action

    Args:
        message: User's message
        nlu_action: Action from NLU classifier (may be None)
        sonnet_action: Action from Sonnet classifier
        context: Dict with workflow_state, entities, previous_action, etc.

    Returns:
        (final_action, guard_reason) - guard_reason is None if no guard fired
    """
    for guard in ALL_GUARDS:
        override_action, reason = guard(message, nlu_action, sonnet_action, context)

        if override_action:
            logger.info(f"[GUARD] {guard.__name__}: {sonnet_action} → {override_action}")
            logger.info(f"[GUARD] Reason: {reason}")
            return override_action, reason

    # No guard fired, use Sonnet's action
    return sonnet_action, None


def log_classification_decision(
    nlu_result: Dict,
    sonnet_result: Dict,
    final_action: str,
    guard_reason: Optional[str]
):
    """Log classification decisions for debugging"""
    nlu_action = nlu_result.get('action', 'N/A') if nlu_result else 'N/A'
    nlu_confidence = nlu_result.get('confidence', 'N/A') if nlu_result else 'N/A'
    sonnet_action = sonnet_result.get('action', 'N/A')
    sonnet_reasoning = sonnet_result.get('reasoning', 'N/A')[:100] if sonnet_result.get('reasoning') else 'N/A'

    log_msg = f"""
[CLASSIFICATION DECISION]
  NLU Action:     {nlu_action} (confidence: {nlu_confidence})
  Sonnet Action:  {sonnet_action}
  Final Action:   {final_action}
  Guard Applied:  {guard_reason or 'None'}
  Sonnet Reason:  {sonnet_reasoning}
"""
    logger.info(log_msg)
