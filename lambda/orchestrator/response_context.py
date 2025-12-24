"""
Response Context Builder for Voice Enhancements
Builds enriched context for intelligent, context-aware voice responses.

VOICE-ONLY: This module only activates when channel == 'voice'.
Chat/SMS responses remain unchanged.

Context includes:
- Conversation state (just_arrived, exploring, scheduling, post_action)
- Last action memory (what happened, result, which project)
- Upcoming appointments (proactive highlights)
- Time context (morning call, appointment today/tomorrow)
- Projects already mentioned (avoid repetition)
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger()


# ============================================================================
# CONVERSATION STATES
# ============================================================================
class ConversationState:
    """Enum-like class for conversation states"""
    JUST_ARRIVED = 'just_arrived'      # First interaction or new session
    EXPLORING = 'exploring'            # Browsing projects, asking questions
    SCHEDULING = 'scheduling'          # In middle of scheduling flow
    POST_ACTION = 'post_action'        # Just completed an action (schedule, cancel, etc.)
    RETURNING = 'returning'            # Called before, has history


# ============================================================================
# VOICE FILLERS - Phrases to emit before slow operations
# ============================================================================
VOICE_FILLERS = {
    'list_projects': "Let me pull up your projects...",
    'get_project_details': "Let me check on that...",
    'get_available_dates': "Checking availability...",
    'get_time_slots': "Looking at the times for that day...",
    'schedule_project': "Booking that for you...",
    'confirm_appointment': "Confirming your appointment...",
    'cancel_appointment': "Canceling that appointment...",
    'reschedule_appointment': "Working on rescheduling that...",
    'default': "One moment..."
}


def get_filler_for_action(action: str) -> str:
    """Get appropriate filler phrase for an action."""
    return VOICE_FILLERS.get(action, VOICE_FILLERS['default'])


# ============================================================================
# CONTEXT BUILDER
# ============================================================================
def build_voice_context(
    session_id: str,
    workflow_state: Optional[Dict[str, Any]] = None,
    current_action: Optional[str] = None,
    current_result: Optional[str] = None,
    projects: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Build enriched context for voice response formatting.

    This is the main entry point - call this before formatting voice responses.

    Args:
        session_id: Current session ID
        workflow_state: Current workflow state from DynamoDB (optional, will fetch if not provided)
        current_action: The action that was just performed (optional)
        current_result: Result of the action - 'success' or 'failure' (optional)
        projects: List of customer's projects (optional, for appointment extraction)

    Returns:
        Enriched context dictionary for voice formatting
    """
    context = {
        'conversation_state': ConversationState.JUST_ARRIVED,
        'last_action': None,
        'last_result': None,
        'last_project_name': None,
        'last_project_id': None,
        'upcoming_appointments': [],
        'projects_mentioned': [],
        'time_context': get_time_context(),
        'session_id': session_id
    }

    # Load from workflow state if available
    if workflow_state:
        state_context = workflow_state.get('context', {})

        # Extract last action info
        context['last_action'] = state_context.get('last_action')
        context['last_result'] = state_context.get('last_result')
        context['last_project_name'] = state_context.get('last_project_name')
        context['last_project_id'] = state_context.get('last_project_id')
        context['projects_mentioned'] = state_context.get('projects_mentioned_this_session', [])

        # Get cached upcoming appointments
        context['upcoming_appointments'] = state_context.get('upcoming_appointments', [])

        # Determine conversation state
        context['conversation_state'] = determine_conversation_state(
            workflow_state=workflow_state,
            current_action=current_action,
            current_result=current_result
        )

    # Override with current action if provided
    if current_action:
        context['current_action'] = current_action
    if current_result:
        context['current_result'] = current_result

    # Extract upcoming appointments from projects if provided
    if projects:
        context['upcoming_appointments'] = extract_upcoming_appointments(projects)

    logger.info(f"[VOICE_CTX] Built context: state={context['conversation_state']}, "
                f"last_action={context['last_action']}, upcoming={len(context['upcoming_appointments'])}")

    return context


def determine_conversation_state(
    workflow_state: Optional[Dict[str, Any]] = None,
    current_action: Optional[str] = None,
    current_result: Optional[str] = None
) -> str:
    """
    Determine the current conversation state based on workflow and action.

    States:
    - JUST_ARRIVED: No workflow state or fresh session
    - EXPLORING: Browsing projects, viewing details
    - SCHEDULING: In the middle of scheduling flow
    - POST_ACTION: Just completed an action (schedule, cancel, etc.)
    - RETURNING: Has prior history, coming back

    Returns:
        ConversationState value
    """
    if not workflow_state:
        return ConversationState.JUST_ARRIVED

    workflow_type = workflow_state.get('workflow_type', '')
    current_stage = workflow_state.get('current_stage', '')
    context = workflow_state.get('context', {})
    viewed_projects = workflow_state.get('viewed_projects', [])

    # Check if just completed an action
    if current_result == 'success' and current_action in [
        'schedule_project', 'confirm_appointment', 'cancel_appointment', 'reschedule_appointment'
    ]:
        return ConversationState.POST_ACTION

    # Check workflow stages
    if current_stage in ['awaiting_date_selection', 'awaiting_time_selection', 'awaiting_confirmation']:
        return ConversationState.SCHEDULING

    # Has history but not in active workflow
    if viewed_projects and len(viewed_projects) > 0:
        # Check if this is a returning user (viewed projects earlier)
        last_viewed_at = max(p.get('viewed_at', 0) for p in viewed_projects)
        time_since_last = time.time() - last_viewed_at

        # If more than 5 minutes since last view, consider them "returning"
        if time_since_last > 300:
            return ConversationState.RETURNING

        return ConversationState.EXPLORING

    # Default to just arrived
    return ConversationState.JUST_ARRIVED


def get_time_context() -> Dict[str, Any]:
    """
    Get time-based context for response personalization.

    Returns:
        Dictionary with:
        - is_morning: bool (before noon)
        - is_afternoon: bool (noon to 5pm)
        - is_evening: bool (after 5pm)
        - greeting: Appropriate greeting for time of day
        - today: Today's date string
        - tomorrow: Tomorrow's date string
    """
    now = datetime.now()
    hour = now.hour

    return {
        'is_morning': hour < 12,
        'is_afternoon': 12 <= hour < 17,
        'is_evening': hour >= 17,
        'greeting': 'Good morning' if hour < 12 else ('Good afternoon' if hour < 17 else 'Good evening'),
        'today': now.strftime('%Y-%m-%d'),
        'tomorrow': (now + timedelta(days=1)).strftime('%Y-%m-%d'),
        'current_hour': hour
    }


def extract_upcoming_appointments(projects: List[Dict]) -> List[Dict[str, Any]]:
    """
    Extract upcoming scheduled appointments from project list.

    Args:
        projects: List of project dictionaries

    Returns:
        List of upcoming appointments sorted by date, limited to next 5
    """
    upcoming = []
    today = datetime.now().date()

    for project in projects:
        status = (project.get('status') or '').lower()

        # Only include scheduled projects
        if 'scheduled' not in status:
            continue

        # Get scheduled date
        scheduled_date_str = project.get('scheduledDate') or project.get('scheduled_date')
        if not scheduled_date_str:
            continue

        try:
            # Parse date (handle various formats)
            if 'T' in scheduled_date_str:
                scheduled_date = datetime.fromisoformat(scheduled_date_str.replace('Z', '+00:00')).date()
            else:
                scheduled_date = datetime.strptime(scheduled_date_str[:10], '%Y-%m-%d').date()

            # Only include future appointments
            if scheduled_date >= today:
                upcoming.append({
                    'project_id': str(project.get('id', '')),
                    'project_name': project.get('category') or project.get('projectType', 'Project'),
                    'date': scheduled_date_str[:10],
                    'time': project.get('scheduledTime') or project.get('scheduled_time', ''),
                    'days_away': (scheduled_date - today).days,
                    'is_today': scheduled_date == today,
                    'is_tomorrow': scheduled_date == today + timedelta(days=1),
                    'address': project.get('address') or project.get('fullAddress', '')
                })
        except Exception as e:
            logger.debug(f"Could not parse date {scheduled_date_str}: {e}")
            continue

    # Sort by date and limit to 5
    upcoming.sort(key=lambda x: x['date'])
    return upcoming[:5]


# ============================================================================
# SESSION ENRICHMENT - Save action results to session
# ============================================================================
def save_action_to_context(
    state_manager,
    session_id: str,
    action: str,
    result: str,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    extra_context: Optional[Dict] = None
) -> bool:
    """
    Save action result to session context for future reference.
    Call this after each action completes.

    Args:
        state_manager: WorkflowStateManager instance
        session_id: Current session ID
        action: Action that was performed (e.g., 'schedule_project')
        result: 'success' or 'failure'
        project_id: ID of project acted upon (optional)
        project_name: Human-readable project name (optional)
        extra_context: Additional context to save (optional)

    Returns:
        True if saved successfully
    """
    try:
        # Get current state
        state = state_manager.get_state(session_id)
        if not state:
            state = {
                'workflow_type': 'browsing',
                'current_stage': 'viewing',
                'context': {},
                'viewed_projects': [],
                'project_mapping': {}
            }

        context = state.get('context', {})

        # Update action memory
        context['last_action'] = action
        context['last_result'] = result
        context['last_action_timestamp'] = int(time.time())

        if project_id:
            context['last_project_id'] = project_id
        if project_name:
            context['last_project_name'] = project_name

        # Track mentioned projects (avoid duplicates)
        mentioned = context.get('projects_mentioned_this_session', [])
        if project_id and project_id not in mentioned:
            mentioned.append(project_id)
            context['projects_mentioned_this_session'] = mentioned[-20:]  # Keep last 20

        # Merge extra context
        if extra_context:
            context.update(extra_context)

        state['context'] = context
        state['last_action'] = action  # Also save at top level for backward compatibility

        success = state_manager.save_state(session_id, state)

        if success:
            logger.info(f"[ACTION_CTX] Saved: action={action}, result={result}, project={project_name or project_id}")

        return success

    except Exception as e:
        logger.error(f"Error saving action to context: {e}")
        return False


def cache_upcoming_appointments(
    state_manager,
    session_id: str,
    projects: List[Dict]
) -> bool:
    """
    Cache upcoming appointments in session for quick access.
    Call this after fetching project list.

    Args:
        state_manager: WorkflowStateManager instance
        session_id: Current session ID
        projects: List of projects from API

    Returns:
        True if cached successfully
    """
    try:
        upcoming = extract_upcoming_appointments(projects)

        state = state_manager.get_state(session_id)
        if not state:
            state = {
                'workflow_type': 'browsing',
                'current_stage': 'viewing',
                'context': {},
                'viewed_projects': [],
                'project_mapping': {}
            }

        context = state.get('context', {})
        context['upcoming_appointments'] = upcoming
        context['appointments_cached_at'] = int(time.time())
        state['context'] = context

        success = state_manager.save_state(session_id, state)

        if success:
            logger.info(f"[APPT_CACHE] Cached {len(upcoming)} upcoming appointments")

        return success

    except Exception as e:
        logger.error(f"Error caching appointments: {e}")
        return False


# ============================================================================
# RESPONSE RULES - Determine how to format based on context
# ============================================================================
def get_response_rules(voice_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine response formatting rules based on context.

    Returns:
        Dictionary with formatting rules:
        - lead_with_reminder: bool - Should we mention upcoming appointment first?
        - reminder_text: str - The reminder text if applicable
        - use_brief_format: bool - Should we use abbreviated response?
        - skip_project_list: bool - Should we skip listing projects user already knows?
        - celebration_mode: bool - Did user just complete something successfully?
        - suggest_next_action: bool - Should we suggest what to do next?
        - next_action_text: str - Suggested next action text
    """
    rules = {
        'lead_with_reminder': False,
        'reminder_text': '',
        'use_brief_format': False,
        'skip_project_list': False,
        'celebration_mode': False,
        'suggest_next_action': False,
        'next_action_text': ''
    }

    state = voice_context.get('conversation_state')
    upcoming = voice_context.get('upcoming_appointments', [])
    time_ctx = voice_context.get('time_context', {})

    # Check for appointment today or tomorrow
    if upcoming:
        today_appt = next((a for a in upcoming if a.get('is_today')), None)
        tomorrow_appt = next((a for a in upcoming if a.get('is_tomorrow')), None)

        if today_appt:
            rules['lead_with_reminder'] = True
            rules['reminder_text'] = (
                f"Quick reminder - your {today_appt['project_name']} appointment is today"
                + (f" at {today_appt['time']}" if today_appt.get('time') else "")
                + "."
            )
        elif tomorrow_appt:
            rules['lead_with_reminder'] = True
            rules['reminder_text'] = (
                f"Heads up - your {tomorrow_appt['project_name']} appointment is tomorrow"
                + (f" at {tomorrow_appt['time']}" if tomorrow_appt.get('time') else "")
                + "."
            )

    # Post-action state
    if state == ConversationState.POST_ACTION:
        rules['celebration_mode'] = True
        rules['use_brief_format'] = True
        rules['suggest_next_action'] = True

        # Count remaining schedulable projects
        # This would need to be passed in context
        rules['next_action_text'] = "Want to schedule another project?"

    # Returning user
    if state == ConversationState.RETURNING:
        rules['use_brief_format'] = True
        last_project = voice_context.get('last_project_name')
        if last_project:
            rules['next_action_text'] = f"Welcome back! Last time you were looking at {last_project}."

    # If many projects mentioned, use brief format
    if len(voice_context.get('projects_mentioned', [])) > 3:
        rules['use_brief_format'] = True

    return rules


# ============================================================================
# STATUS SUMMARY - Group projects by status for voice
# ============================================================================
def summarize_projects_by_status(projects: List[Dict]) -> Dict[str, Any]:
    """
    Summarize projects by status for voice-friendly output.
    Instead of listing 10 projects, say "3 scheduled, 4 ready to schedule, 3 in progress"

    Args:
        projects: List of project dictionaries

    Returns:
        Summary dictionary with counts and formatted text
    """
    status_counts = {}

    for project in projects:
        status = project.get('status', 'Unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    # Build voice-friendly summary
    parts = []

    # Priority order for mentioning statuses
    priority_statuses = [
        ('Scheduled', 'scheduled'),
        ('Tentatively Scheduled', 'tentatively scheduled'),
        ('Ready To Schedule', 'ready to schedule'),
        ('New', 'new'),
        ('In Progress', 'in progress'),
        ('Completed', 'completed')
    ]

    for status_key, spoken in priority_statuses:
        count = status_counts.get(status_key, 0)
        if count > 0:
            parts.append(f"{count} {spoken}")

    # Handle any remaining statuses
    for status, count in status_counts.items():
        if status not in [s[0] for s in priority_statuses]:
            parts.append(f"{count} {status.lower()}")

    total = len(projects)

    return {
        'total': total,
        'status_counts': status_counts,
        'summary_text': ', '.join(parts) if parts else 'no projects',
        'has_schedulable': status_counts.get('Ready To Schedule', 0) + status_counts.get('New', 0) > 0,
        'schedulable_count': status_counts.get('Ready To Schedule', 0) + status_counts.get('New', 0),
        'scheduled_count': status_counts.get('Scheduled', 0) + status_counts.get('Tentatively Scheduled', 0)
    }
