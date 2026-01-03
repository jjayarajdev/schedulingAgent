"""
DSPy Signatures for ProjectForce Orchestrator

Signatures define the input/output structure for each LLM call.
DSPy uses these to automatically generate and optimize prompts.
"""
import dspy
from typing import Literal


# =============================================================================
# INTENT CLASSIFICATION
# =============================================================================

class IntentClassifier(dspy.Signature):
    """Classify user intent for a home improvement scheduling assistant.

    The assistant helps homeowners manage projects like kitchen remodels,
    decking, roofing, appliance installations, etc.
    """

    message: str = dspy.InputField(desc="User's message")
    conversation_summary: str = dspy.InputField(
        desc="Summary of recent conversation context",
        default=""
    )

    intent: Literal["scheduling", "information", "chitchat"] = dspy.OutputField(
        desc="High-level intent category"
    )
    action: str = dspy.OutputField(
        desc="Specific action: list_projects, get_project_details, get_available_dates, "
             "get_time_slots, confirm_appointment, reschedule_appointment, cancel_appointment, "
             "get_weather, greet, help, general"
    )
    confidence: Literal["high", "medium", "low"] = dspy.OutputField(
        desc="Classification confidence"
    )
    reasoning: str = dspy.OutputField(
        desc="Brief explanation of why this classification was chosen"
    )


# =============================================================================
# ENTITY EXTRACTION
# =============================================================================

class EntityExtractor(dspy.Signature):
    """Extract structured entities from user message for API calls.

    Entities are parameters needed to execute the classified action.
    """

    message: str = dspy.InputField(desc="User's message")
    action: str = dspy.InputField(desc="Classified action to execute")
    available_projects: str = dspy.InputField(
        desc="JSON list of user's projects with id, category, status",
        default="[]"
    )
    workflow_context: str = dspy.InputField(
        desc="Current workflow state including project_id, date, city, state",
        default="{}"
    )

    project_id: str = dspy.OutputField(
        desc="Project ID if mentioned or inferable. Use exact ID from available_projects.",
        default=""
    )
    category: str = dspy.OutputField(
        desc="Project category like 'Decking', 'Kitchen Sink', 'Roofing'",
        default=""
    )
    date: str = dspy.OutputField(
        desc="Date in YYYY-MM-DD format or relative like 'next week', 'tomorrow'",
        default=""
    )
    time: str = dspy.OutputField(
        desc="Time slot like '8:00 AM', '1:00 PM'",
        default=""
    )
    location: str = dspy.OutputField(
        desc="City, State format for weather queries",
        default=""
    )
    status_filter: str = dspy.OutputField(
        desc="Status filter: 'scheduled', 'ready to schedule', 'all'",
        default=""
    )


# =============================================================================
# WEATHER CONTEXT RESOLVER
# =============================================================================

class WeatherContextResolver(dspy.Signature):
    """Resolve location and date for weather queries from conversation context.

    When user asks about weather without specifying location/date,
    infer from the current scheduling workflow context.
    """

    message: str = dspy.InputField(desc="User's weather query")
    workflow_context: str = dspy.InputField(
        desc="JSON with project_id, city, state, date, category from current workflow"
    )
    conversation_summary: str = dspy.InputField(
        desc="Recent conversation context",
        default=""
    )

    location: str = dspy.OutputField(
        desc="City, State format (e.g., 'Minneapolis, MN')"
    )
    target_date: str = dspy.OutputField(
        desc="Date for weather forecast in YYYY-MM-DD format"
    )
    reasoning: str = dspy.OutputField(
        desc="How location and date were determined"
    )


# =============================================================================
# ACTION GUARD
# =============================================================================

class ActionGuard(dspy.Signature):
    """Validate and potentially correct classified actions.

    Guards prevent common classification errors like auto-escalating
    to scheduling when user just wants to view projects.
    """

    message: str = dspy.InputField(desc="User's message")
    classified_action: str = dspy.InputField(desc="Action from classifier")
    workflow_stage: str = dspy.InputField(
        desc="Current workflow stage: listing_projects, awaiting_date_selection, "
             "awaiting_time_selection, awaiting_confirmation, none",
        default="none"
    )
    previous_action: str = dspy.InputField(
        desc="Previous action in conversation",
        default=""
    )

    final_action: str = dspy.OutputField(
        desc="Validated/corrected action"
    )
    was_corrected: bool = dspy.OutputField(
        desc="True if action was changed from classifier's output"
    )
    guard_reason: str = dspy.OutputField(
        desc="Explanation if action was corrected, empty otherwise",
        default=""
    )


# =============================================================================
# RESPONSE FORMATTER
# =============================================================================

class VoiceResponseFormatter(dspy.Signature):
    """Format API response for natural voice output.

    Convert structured data into conversational speech optimized
    for text-to-speech delivery.
    """

    action: str = dspy.InputField(desc="Action that was executed")
    api_response: str = dspy.InputField(desc="JSON response from API")
    user_message: str = dspy.InputField(desc="Original user message")

    voice_response: str = dspy.OutputField(
        desc="Natural, conversational response under 50 words. "
             "Speak dates as 'Tuesday, January 6th' not '01-06-2026'. "
             "Speak times as '8 AM' not '08:00'."
    )
    follow_up_prompt: str = dspy.OutputField(
        desc="Optional question to continue conversation",
        default=""
    )


class ChatResponseFormatter(dspy.Signature):
    """Format API response for chat/SMS output.

    Convert structured data into clear, concise text with markdown
    formatting where appropriate.
    """

    action: str = dspy.InputField(desc="Action that was executed")
    api_response: str = dspy.InputField(desc="JSON response from API")
    user_message: str = dspy.InputField(desc="Original user message")

    chat_response: str = dspy.OutputField(
        desc="Clear response under 100 words. Use bullet points for lists. "
             "Include key details like dates, times, project names."
    )


# =============================================================================
# DATE INTERPRETER
# =============================================================================

class DateInterpreter(dspy.Signature):
    """Convert natural language date expressions to specific date ranges.

    Handles relative expressions like 'next week', 'end of January',
    'day after tomorrow', etc.
    """

    phrase: str = dspy.InputField(desc="Natural language date expression")
    current_date: str = dspy.InputField(desc="Today's date in YYYY-MM-DD format")

    start_date: str = dspy.OutputField(
        desc="Start date of range in YYYY-MM-DD format"
    )
    end_date: str = dspy.OutputField(
        desc="End date of range in YYYY-MM-DD format"
    )
    interpretation: str = dspy.OutputField(
        desc="Human-readable explanation of the date range"
    )


# =============================================================================
# CONTEXT RESOLVER
# =============================================================================

class ContextResolver(dspy.Signature):
    """Resolve pronouns, references, and ambiguous entities from conversation context.

    Handles 'it', 'that one', 'the first one', 'my kitchen project', etc.
    """

    message: str = dspy.InputField(desc="User's message with potential references")
    conversation_history: str = dspy.InputField(
        desc="Recent conversation context including projects discussed"
    )

    resolved_message: str = dspy.OutputField(
        desc="Message with resolved entities (e.g., 'reschedule it' -> 'reschedule project 9000489')"
    )
    resolved_entities: str = dspy.OutputField(
        desc="JSON dict of resolved entities like {project_id, category, date, time}"
    )
    resolution_type: str = dspy.OutputField(
        desc="Type of resolution: pronoun, demonstrative, ordinal, category, implicit, ambiguous"
    )
    confidence: Literal["high", "medium", "low"] = dspy.OutputField(
        desc="Confidence in resolution"
    )


# =============================================================================
# RESPONSE STYLER
# =============================================================================

class ResponseStyler(dspy.Signature):
    """Adapt response tone and format based on channel (voice/sms/chat).

    Voice: conversational, natural flow, no markdown
    SMS: ultra-concise, abbreviations OK
    Chat: balanced, markdown formatting
    """

    raw_response: str = dspy.InputField(desc="Raw response content to style")
    channel: Literal["voice", "sms", "chat"] = dspy.InputField(
        desc="Output channel"
    )
    context: str = dspy.InputField(
        desc="What action was being performed",
        default=""
    )

    styled_response: str = dspy.OutputField(
        desc="Response adapted for the channel"
    )
    style_notes: str = dspy.OutputField(
        desc="Notes on styling decisions made",
        default=""
    )


# =============================================================================
# SLOT RANKER
# =============================================================================

class SlotRanker(dspy.Signature):
    """Rank time slots based on user preferences, weather, and project type.

    Consider:
    - User's time preference (morning, afternoon, earliest, latest)
    - Weather conditions for outdoor projects
    - Project type (indoor vs outdoor)
    """

    available_slots: str = dspy.InputField(
        desc="JSON list of available time slots"
    )
    user_preference: str = dspy.InputField(
        desc="User's time preference: morning, afternoon, earliest, latest, or empty",
        default=""
    )
    weather_info: str = dspy.InputField(
        desc="Weather conditions for the date",
        default=""
    )
    project_type: str = dspy.InputField(
        desc="Project type like 'Indoor - Kitchen' or 'Outdoor - Decking'"
    )

    ranked_slots: str = dspy.OutputField(
        desc="JSON list of slots in recommended order"
    )
    recommendation: str = dspy.OutputField(
        desc="Top recommended time slot"
    )
    ranking_reason: str = dspy.OutputField(
        desc="Explanation of ranking logic"
    )
