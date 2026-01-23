"""
Request Routing Logic
Routes requests to either Direct Lambda calls or Bedrock Agents
Supports multi-agent orchestration with parallel/sequential execution
"""
import json
import logging
import time
from typing import Dict, Optional, Any
import boto3
from botocore.config import Config as BotoConfig

from config import get_config
from classifier import classify_intent_and_action, apply_project_filters
from context_extraction import extract_location_from_history, extract_pronoun_reference
from context_resolver import resolve_context_references
from voice_formatter import format_for_voice, format_voice_with_context, format_projects_summary_for_voice

logger = logging.getLogger()

# ============================================================================
# Retry configuration for Bedrock calls
# ============================================================================
MAX_RETRIES = 3
INITIAL_BACKOFF = 0.5  # seconds


def retry_with_backoff(func, max_retries=MAX_RETRIES, initial_backoff=INITIAL_BACKOFF):
    """
    Execute a function with exponential backoff retry logic.

    Args:
        func: Callable to execute
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial wait time in seconds

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            error_str = str(e).lower()

            # Don't retry on auth errors or invalid requests
            if 'accessdenied' in error_str or 'validationexception' in error_str:
                logger.error(f"Non-retryable error: {e}")
                raise

            # Retry on throttling, timeout, or transient errors
            if attempt < max_retries - 1:
                wait_time = initial_backoff * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed. Last error: {e}")

    raise last_exception


# ============================================================================
# DynamoDB client for notes lookup
# ============================================================================
_dynamodb_resource = None

def get_dynamodb_resource():
    """Get cached DynamoDB resource."""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource('dynamodb')
    return _dynamodb_resource

def fetch_project_notes(project_id: str) -> list:
    """
    Fetch notes for a project from DynamoDB.
    Returns empty list if no notes found or on error.
    """
    try:
        config = get_config()
        # Notes table name follows pattern: {RESOURCE_PREFIX}-project-notes-{ENVIRONMENT}
        table_name = f"{config.resource_prefix}-project-notes-{config.environment}"

        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(table_name)

        response = table.query(
            KeyConditionExpression='project_id = :pid',
            ExpressionAttributeValues={
                ':pid': str(project_id)
            },
            ScanIndexForward=False  # Sort by timestamp descending (newest first)
        )

        notes = response.get('Items', [])
        logger.info(f"[NOTES] Fetched {len(notes)} notes for project {project_id}")
        return notes

    except Exception as e:
        logger.warning(f"[NOTES] Failed to fetch notes for project {project_id}: {e}")
        return []

# ============================================================================
# NEXT ACTION SUGGESTIONS - Added for proactive UX
# Append helpful follow-up suggestions after completing actions
# ============================================================================
NEXT_ACTION_SUGGESTIONS = {
    'confirm_appointment': "\n\nNeed to make changes later? Just say 'reschedule' or 'cancel'.",
    'cancel_appointment': "\n\nWant to reschedule instead? Say 'schedule' to pick new dates.",
    'list_projects': "\n\nSay a project number or 'first', 'second' to see details.",
    'get_project_details': "\n\nWant to schedule this one? Say 'schedule it'.",
    'reschedule_appointment': "\n\nNeed to make more changes? Just let me know.",
}

# ============================================================================
# ERROR RESPONSES - Natural, helpful messages with recovery paths
# ============================================================================
ERROR_RESPONSES = {
    'invalid_project': "Hmm, I don't see that project in your account. Want me to show you your project list?",
    'no_dates': "No openings this week, unfortunately. I can check next week if you'd like.",
    'api_error': "Oops, something hiccuped on my end. Mind trying that again?",
    'unknown_input': "Sorry, I didn't quite get that. What would you like help with?",
    'timeout': "Taking longer than usual - give me one more try?",
    'bedrock_error': "I'm having trouble processing that right now. Let me try a simpler approach.",
    'no_context': "I need a bit more info. Which project are you asking about?",
}


def add_next_action_suggestion(response: str, action: str, is_voice: bool = False) -> str:
    """Add helpful next-action suggestion to response."""
    if is_voice:
        # For voice, suggestions are handled separately
        return response

    suggestion = NEXT_ACTION_SUGGESTIONS.get(action, "")
    if suggestion and not response.endswith('?'):
        return response + suggestion
    return response


def get_error_response(error_type: str, details: str = None) -> str:
    """Get user-friendly error message with recovery suggestion."""
    base_message = ERROR_RESPONSES.get(error_type, ERROR_RESPONSES['unknown_input'])
    if details:
        return f"{base_message}\n\n(Details: {details})"
    return base_message

# Boto3 clients (reused across Lambda invocations)
_lambda_client = None
_bedrock_agent_client = None


def get_lambda_client():
    """Get or create Lambda client with connection pooling"""
    global _lambda_client
    if _lambda_client is None:
        config = get_config()
        boto_config = BotoConfig(
            region_name=config.region,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        _lambda_client = boto3.client('lambda', config=boto_config)
        logger.info("Lambda client created")
    return _lambda_client


def get_bedrock_agent_client():
    """Get or create Bedrock agent runtime client with connection pooling"""
    global _bedrock_agent_client
    if _bedrock_agent_client is None:
        config = get_config()
        boto_config = BotoConfig(
            region_name=config.region,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        _bedrock_agent_client = boto3.client('bedrock-agent-runtime', config=boto_config)
        logger.info("Bedrock agent runtime client created")
    return _bedrock_agent_client


_bedrock_runtime_client = None


def get_bedrock_runtime_client():
    """Get or create Bedrock runtime client for Claude API"""
    global _bedrock_runtime_client
    if _bedrock_runtime_client is None:
        config = get_config()
        boto_config = BotoConfig(
            region_name=config.region,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        _bedrock_runtime_client = boto3.client('bedrock-runtime', config=boto_config)
        logger.info("Bedrock runtime client created")
    return _bedrock_runtime_client


def generate_conversational_response(action: str, user_message: str, structured_data: Dict[str, Any], channel: str = 'chat') -> str:
    """
    Use Claude via Bedrock Converse API to generate conversational response.
    Includes retry logic with exponential backoff for reliability.

    Args:
        action: The action performed (list_projects, get_project_details, etc.)
        user_message: Original user message
        structured_data: Structured data from Lambda response
        channel: 'chat' or 'voice' - voice gets ultra-short responses

    Returns:
        Conversational response from Claude
    """
    client = get_bedrock_runtime_client()

    # VOICE-SPECIFIC PROMPT: Ultra-concise for phone calls
    if channel == 'voice':
        system_prompt = """You're on a PHONE CALL. Be ULTRA concise - max 1-2 SHORT sentences.

RULES:
1. MAX 2 sentences total
2. Say dates naturally: "December fifteenth" not "December 15, 2025"
3. No project IDs or technical details
4. Use contractions (you've, it's, there's)
5. End with simple question if needed

BANNED PHRASES:
- "Let me check" / "One moment" / "I found"
- "I'd be happy to" / "Sure thing"
- Any address details (too long for voice)

Examples:
"You've got 3 projects: Plumbing, Solar, and Decking. Which one?"
"Your Solar project is scheduled for December fifteenth with Mike."
"5 dates available. December tenth through the fifteenth. Which works?"
"Got 3 morning slots: 8 AM, 9 AM, and 10 AM. Which time?"
"It's 72 and sunny in Minneapolis. Great day for outdoor work."
"""
        user_prompt = f"""User asked: "{user_message}"
Data: {json.dumps(structured_data, indent=2)}

Give a 1-2 sentence voice response. NO addresses, NO project IDs. End with a simple question if user needs to choose."""

        max_tokens = 150  # Much shorter for voice
    else:
        # CHAT PROMPT: Natural, conversational - like texting a helpful friend
        system_prompt = """You're a friendly assistant helping someone manage their home projects.
Write like you're texting a friend - warm, casual, helpful. Not corporate. Not robotic.

TONE:
- Like a helpful neighbor, not a call center script
- Warm but efficient - get to the point
- Use "you" and "your" naturally
- It's okay to show personality

NEVER SAY:
- "Let me check/look/find" (you already have the info!)
- "One moment" / "Hold on" (no delays in chat)
- "I'd be happy to" / "Certainly" / "Absolutely" (too formal)
- "Here's what I found" (just say it)

CRITICAL - NEVER HALLUCINATE:
- ONLY mention technician/installer names if they appear in the data
- NEVER invent or guess names (like "Alice", "Jake", "Bob")
- If user mentions a name not in the data, say "I don't see a technician name in your project details"
- Stick strictly to facts in the provided data

GOOD EXAMPLES:
"You've got 3 projects lined up - a kitchen remodel, deck work, and some plumbing. What should we tackle?"
"Good news - your deck install is all set for January 15th at 8 AM."
"Got 5 open dates next week. Tuesday and Thursday look best weather-wise."

BAD EXAMPLES (don't do this):
"I have retrieved your project information. You currently have 3 projects in our system."
"Let me check on that for you. One moment please. I found 5 available dates."

Weather responses:
- Start with location and current conditions: "It's 72°F and sunny in Minneapolis right now"
- Include relevant forecast briefly: "Tomorrow looks similar, high of 75"
- For outdoor projects, note scheduling impact: "Great weather for deck work this week"
- If rain/bad weather: "Heads up - Wednesday might be rainy. Thursday looks better"
- Keep it conversational, not a data dump - NO raw numbers like "humidity: 65"

Keep it to 2-3 sentences max. Be helpful, not verbose."""

        user_prompt = f"""User said: "{user_message}"

Here's the data:
{json.dumps(structured_data, indent=2)}

Write a natural response - like you're texting them back.
Don't end with questions unless they need to make a choice.
Skip the JSON - that'll show separately."""

        max_tokens = 300  # Reduced from 500 - encourages brevity

    def make_bedrock_call():
        """Inner function for retry wrapper"""
        return client.converse(
            modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_prompt}]
                }
            ],
            system=[{"text": system_prompt}],
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": 0.7,
                "topP": 0.9
            }
        )

    try:
        # Use retry logic for reliability
        response = retry_with_backoff(make_bedrock_call)

        # Extract conversational text
        conversational_text = response['output']['message']['content'][0]['text']
        logger.info(f"[OK] Generated conversational response for {channel} ({len(conversational_text)} chars)")

        return conversational_text.strip()

    except Exception as e:
        logger.error(f"Failed to generate conversational response after retries: {e}")

        # Smart fallback based on action type
        fallback_messages = {
            'list_projects': f"Here are your {structured_data.get('projects', []).__len__()} projects.",
            'get_project_details': "Here are the project details.",
            'get_available_dates': f"Found {len(structured_data.get('dates', []))} available dates.",
            'get_time_slots': f"Found {len(structured_data.get('timeSlots', []))} time slots.",
            'confirm_appointment': "Your appointment is confirmed!",
            'cancel_appointment': "Your appointment has been cancelled.",
            'reschedule_appointment': "Your appointment has been rescheduled.",
            'get_weather': f"Current weather: {structured_data.get('current', {}).get('temperature', 'N/A')}°F and {structured_data.get('current', {}).get('condition', 'unknown conditions')} in {structured_data.get('location', 'your area')}.",
        }

        return fallback_messages.get(action, "Here's what I found:")


def format_lambda_response(action: str, response_body: Dict[str, Any], user_message: str = "", channel: str = 'chat', voice_context: Optional[Dict] = None) -> str:
    """
    Format Lambda response with conversational text + structured JSON

    Args:
        action: The action that was performed (list_projects, get_project_details, etc.)
        response_body: The Lambda response body (parsed JSON)
        user_message: Original user message for context
        channel: 'chat' or 'voice' - voice gets concise responses without JSON
        voice_context: Optional enriched context for voice channel (proactive reminders, etc.)

    Returns:
        Formatted response with conversational text and structured JSON (chat)
        or just conversational text (voice)
    """
    try:
        if action == 'list_projects':
            # Check if all projects are already scheduled (user wanted to schedule but nothing schedulable)
            if response_body.get('already_scheduled'):
                projects = response_body.get('projects', [])
                message = response_body.get('message', 'Your projects are already scheduled.')

                if channel == 'voice':
                    # For voice: friendly message about scheduled projects
                    if projects:
                        first_proj = projects[0]
                        cat = first_proj.get('category', 'Your project')
                        date = first_proj.get('scheduledDate', '')
                        if date:
                            return f"{cat} is already scheduled for {date}. Would you like to reschedule, or check the appointment details?"
                        return f"{cat} is already scheduled. Would you like to reschedule, or check the appointment details?"
                    return "Your projects are already scheduled. Would you like to reschedule, or check the appointment details?"

                # For chat: include structured data
                result = {
                    "message": message,
                    "projects": projects,
                    "already_scheduled": True,
                    "offer_reschedule": True
                }
                return f"{message}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            projects = response_body.get('projects', [])
            if not projects:
                return "I don't see any projects linked to your phone number. If you received a text or call about an appointment, you may be calling from a different number than we have on file. Would you like me to give you the office number so they can help you directly?"

            # Prepare structured data
            result = {
                "message": f"Found {len(projects)} project(s):",
                "projects": projects
            }

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result, channel)

            # For voice, apply context-aware formatting if available
            if channel == 'voice':
                if voice_context:
                    # Use intelligent summary with context (proactive reminders, status grouping)
                    logger.info("[VOICE_CTX] Applying context-aware formatting for list_projects")
                    return format_voice_with_context(conversational, action, voice_context)
                return conversational

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_project_details':
            project = response_body.get('project', {})
            if not project:
                return "I couldn't find that project. Could you double-check the project number or tell me more about which one you're looking for?"

            # Fetch notes for this project from DynamoDB
            project_id = project.get('id')
            notes = []
            if project_id:
                notes = fetch_project_notes(str(project_id))

            # Prepare structured data
            # Use projectNumber (Order Number) for customer-facing message, fallback to id
            display_number = project.get('projectNumber', project.get('id', 'Unknown'))
            result = {
                "message": f"Project #{display_number} Details",
                "project": project
            }

            # Include notes if any exist
            if notes:
                result["notes"] = notes
                result["notes_count"] = len(notes)
                logger.info(f"[PROJECT_DETAILS] Including {len(notes)} notes for project {project_id}")

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result, channel)

            # For voice, return only conversational text (no JSON)
            if channel == 'voice':
                return conversational

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_available_dates':
            # Check if project is already scheduled - offer reschedule instead of error
            if response_body.get('already_scheduled'):
                project_id = response_body.get('project_id', '')
                # Build response that offers reschedule
                result = {
                    "message": "This project is already scheduled.",
                    "already_scheduled": True,
                    "project_id": project_id,
                    "offer_reschedule": True
                }
                if channel == 'voice':
                    return "This project is already scheduled. Would you like to reschedule it instead?"
                return f"This project is already scheduled. Would you like to reschedule it?\n\n```json\n{json.dumps(result, indent=2)}\n```"

            dates = response_body.get('available_dates', [])
            if not dates:
                return "Hmm, no open dates for this project right now. Want me to check again in a few days, or should we look at a different project?"

            # Check for weather-enriched dates (proactive weather warnings)
            dates_with_weather = response_body.get('dates_with_weather', [])
            has_weather_concerns = response_body.get('has_weather_concerns', False)

            # DEBUG: Log what we received
            logger.info(f"[DEBUG] dates_with_weather count: {len(dates_with_weather)}")
            if dates_with_weather:
                logger.info(f"[DEBUG] First date with weather: {dates_with_weather[0]}")

            # Format dates for UI rendering
            from datetime import datetime
            formatted_dates = []

            if dates_with_weather:
                # Use enriched dates with weather indicators
                for enriched_date in dates_with_weather:
                    date_str = enriched_date.get('date', '')
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_dates.append({
                            "date": date_str,
                            "displayDate": date_obj.strftime("%m/%d/%Y"),
                            "dayShort": date_obj.strftime("%a"),
                            "monthDay": date_obj.strftime("%m/%d"),
                            "dayName": date_obj.strftime("%A"),
                            "formatted": date_obj.strftime("%a %m/%d/%Y"),
                            # Weather info
                            "weatherIndicator": enriched_date.get('indicator', ''),
                            "weatherSuitable": enriched_date.get('suitable', True),
                            "weatherSeverity": enriched_date.get('severity', 'low'),
                            "weatherCondition": enriched_date.get('condition', ''),
                            "weatherWarnings": enriched_date.get('warnings', []),
                            "highTemp": enriched_date.get('high_temp'),
                            "lowTemp": enriched_date.get('low_temp')
                        })
                    except:
                        formatted_dates.append({
                            "date": date_str,
                            "monthDay": date_str,
                            "weatherIndicator": enriched_date.get('indicator', ''),
                            "weatherSuitable": enriched_date.get('suitable', True)
                        })

                logger.info(f"[WEATHER] Formatted {len(formatted_dates)} dates with weather indicators")
            else:
                # No weather data - use basic date formatting
                for date_str in dates:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_dates.append({
                            "date": date_str,
                            "displayDate": date_obj.strftime("%m/%d/%Y"),
                            "dayShort": date_obj.strftime("%a"),
                            "monthDay": date_obj.strftime("%m/%d"),
                            "dayName": date_obj.strftime("%A"),
                            "formatted": date_obj.strftime("%a %m/%d/%Y")
                        })
                    except:
                        formatted_dates.append({"date": date_str, "monthDay": date_str})

            # Prepare structured data
            result = {
                "message": "Available dates for scheduling:",
                "dates": formatted_dates,
                "dateCount": len(formatted_dates)
            }

            # Note: Weather forecast will be shown when user selects a specific date
            # This keeps the available dates response simple and focused

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result, channel)

            # For voice, return only conversational text (no JSON)
            if channel == 'voice':
                return conversational

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_rescheduler_slots':
            # Handle rescheduler slots response
            # This API returns both dates and slots - check which we're showing
            slots = response_body.get('slots', [])
            dates = response_body.get('available_dates', [])

            # Check for error/timeout status
            if response_body.get('status') == 'cannot_reschedule':
                return response_body.get('message', 'Cannot reschedule this project.')
            if response_body.get('status') == 'timeout':
                return response_body.get('message', 'The rescheduling service is temporarily unavailable. Please try again in a few minutes.')

            # If we have time slots, show them (user selected a date)
            if slots:
                formatted_slots = []
                grouped_slots = {"morning": [], "afternoon": [], "evening": []}

                for slot in slots:
                    try:
                        time_parts = slot.split(":")
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])

                        am_pm = "AM" if hour < 12 else "PM"
                        display_hour = hour if hour <= 12 else hour - 12
                        display_hour = 12 if display_hour == 0 else display_hour

                        formatted_time = f"{display_hour}:{minute:02d} {am_pm}"
                        formatted_slots.append(formatted_time)

                        if hour < 12:
                            grouped_slots["morning"].append(formatted_time)
                        elif hour < 17:
                            grouped_slots["afternoon"].append(formatted_time)
                        else:
                            grouped_slots["evening"].append(formatted_time)
                    except:
                        formatted_slots.append(slot)

                result = {
                    "message": "Available time slots for rescheduling:",
                    "timeSlots": formatted_slots,
                    "timeSlotsGrouped": {
                        "morning": {"label": "Morning", "slots": grouped_slots["morning"], "count": len(grouped_slots["morning"])},
                        "afternoon": {"label": "Afternoon", "slots": grouped_slots["afternoon"], "count": len(grouped_slots["afternoon"])},
                        "evening": {"label": "Evening", "slots": grouped_slots["evening"], "count": len(grouped_slots["evening"])}
                    },
                    "slotCount": len(formatted_slots),
                    "isReschedule": True
                }

                conversational = generate_conversational_response('get_time_slots', user_message, result, channel)
                if channel == 'voice':
                    return conversational
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Otherwise show available dates
            if not dates:
                return "No openings for rescheduling right now. Would you like me to keep the current appointment, or should I check again later?"

            # Check for weather-enriched dates (same as get_available_dates)
            dates_with_weather = response_body.get('dates_with_weather', [])
            has_weather_concerns = response_body.get('has_weather_concerns', False)

            # Format dates - same format as schedule flow with weather support
            formatted_dates = []

            if dates_with_weather:
                # Use enriched dates with weather indicators
                for enriched_date in dates_with_weather:
                    date_str = enriched_date.get('date', '')
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_dates.append({
                            "date": date_str,
                            "displayDate": date_obj.strftime("%m/%d/%Y"),
                            "dayShort": date_obj.strftime("%a"),
                            "monthDay": date_obj.strftime("%m/%d"),
                            "dayName": date_obj.strftime("%A"),
                            "formatted": date_obj.strftime("%a %m/%d/%Y"),
                            # Weather info
                            "weatherIndicator": enriched_date.get('indicator', ''),
                            "weatherSuitable": enriched_date.get('suitable', True),
                            "weatherSeverity": enriched_date.get('severity', 'low'),
                            "weatherCondition": enriched_date.get('condition', ''),
                            "weatherWarnings": enriched_date.get('warnings', []),
                            "highTemp": enriched_date.get('high_temp'),
                            "lowTemp": enriched_date.get('low_temp')
                        })
                    except:
                        formatted_dates.append({
                            "date": date_str,
                            "monthDay": date_str,
                            "weatherIndicator": enriched_date.get('indicator', ''),
                            "weatherSuitable": enriched_date.get('suitable', True)
                        })

                logger.info(f"[WEATHER] Formatted {len(formatted_dates)} reschedule dates with weather indicators")
            else:
                # No weather data - use basic date formatting
                for date_str in dates:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_dates.append({
                            "date": date_str,
                            "displayDate": date_obj.strftime("%m/%d/%Y"),
                            "dayShort": date_obj.strftime("%a"),
                            "monthDay": date_obj.strftime("%m/%d"),
                            "dayName": date_obj.strftime("%A"),
                            "formatted": date_obj.strftime("%a %m/%d/%Y")
                        })
                    except:
                        formatted_dates.append({"date": date_str, "monthDay": date_str})

            # Sort dates chronologically
            formatted_dates.sort(key=lambda x: x.get('date', ''))

            result = {
                "message": "Available dates for rescheduling:",
                "dates": formatted_dates,
                "dateCount": len(formatted_dates),
                "isReschedule": True,
                "hasWeatherConcerns": has_weather_concerns
            }

            # Generate conversational response
            conversational = generate_conversational_response(action, user_message, result, channel)
            if channel == 'voice':
                return conversational
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action in ['get_time_slots', 'get_available_timeslots']:
            # Try multiple field names for compatibility
            slots = response_body.get('available_slots') or response_body.get('timeSlots') or response_body.get('time_slots', [])
            if not slots:
                return "That day's pretty booked up. Want to try a different date?"

            # Format times nicely (convert 24h to 12h with AM/PM)
            formatted_slots = []
            grouped_slots = {"morning": [], "afternoon": [], "evening": []}

            for slot in slots:
                try:
                    # Parse time (format: "HH:MM" or "HH:MM:SS")
                    time_parts = slot.split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])

                    # Convert to 12h format
                    am_pm = "AM" if hour < 12 else "PM"
                    display_hour = hour if hour <= 12 else hour - 12
                    display_hour = 12 if display_hour == 0 else display_hour

                    formatted_time = f"{display_hour}:{minute:02d} {am_pm}"
                    formatted_slots.append(formatted_time)

                    # Group by time of day
                    if hour < 12:
                        grouped_slots["morning"].append(formatted_time)
                    elif hour < 17:
                        grouped_slots["afternoon"].append(formatted_time)
                    else:
                        grouped_slots["evening"].append(formatted_time)
                except:
                    formatted_slots.append(slot)

            # Prepare structured data
            result = {
                "message": "Available time slots for this date:",
                "timeSlots": formatted_slots,
                "timeSlotsGrouped": {
                    "morning": {"label": "Morning", "slots": grouped_slots["morning"], "count": len(grouped_slots["morning"])},
                    "afternoon": {"label": "Afternoon", "slots": grouped_slots["afternoon"], "count": len(grouped_slots["afternoon"])},
                    "evening": {"label": "Evening", "slots": grouped_slots["evening"], "count": len(grouped_slots["evening"])}
                },
                "slotCount": len(formatted_slots)
            }

            # Add weather forecast if present (for selected date + 5 days)
            if 'weather_forecast' in response_body:
                result['weatherForecast'] = response_body['weather_forecast']
                logger.info(f"[WEATHER] Including {len(response_body['weather_forecast'])} day forecast")

            if 'current_weather' in response_body:
                result['currentWeather'] = response_body['current_weather']

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result, channel)

            # For voice, return only conversational text (no JSON)
            if channel == 'voice':
                return conversational

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_business_hours':
            working_days = response_body.get('working_days', [])
            non_working_days = response_body.get('non_working_days', [])

            if not working_days:
                return "Business hours not configured."

            # Prepare structured data
            result = {
                "message": "Business Hours",
                "workingDays": working_days,
                "nonWorkingDays": non_working_days
            }

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result, channel)

            # For voice, return only conversational text (no JSON)
            if channel == 'voice':
                return conversational

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action in ['greet', 'help', 'general']:
            # Chitchat actions - return message directly
            return response_body.get('message', "Hello! How can I help you today?")

        elif action == 'confirm_appointment':
            # Check for errors first
            if 'error' in response_body:
                error_message = response_body['error']
                # Generate friendly error message
                friendly_error = f"I wasn't able to confirm this appointment. The system reported: {error_message}. Please try again or contact support if the problem continues."
                logger.warning(f"[ERROR] Appointment confirmation failed: {error_message}")
                return friendly_error

            # Helper to convert date from YYYY-MM-DD to MM/DD/YYYY
            def format_date_display(date_str):
                if not date_str:
                    return date_str
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    return date_obj.strftime("%m/%d/%Y")
                except:
                    return date_str

            # Format successful appointment confirmation response
            appointment = response_body.get('appointment', {})

            # Format dates in appointment object
            if appointment:
                if 'scheduled_date' in appointment:
                    appointment['scheduled_date'] = format_date_display(appointment['scheduled_date'])
                if 'scheduledDate' in appointment:
                    appointment['scheduledDate'] = format_date_display(appointment['scheduledDate'])

            # Also format top-level scheduled_date if present
            if 'scheduled_date' in response_body:
                response_body['scheduled_date'] = format_date_display(response_body['scheduled_date'])

            if not appointment and response_body.get('success'):
                # Handle simplified success response
                result = {
                    'message': 'Appointment confirmed successfully!',
                    'status': 'confirmed',
                    'details': response_body
                }
            else:
                result = {
                    "message": "[OK] Appointment confirmed!",
                    "appointment": appointment or response_body,
                    "status": "confirmed"
                }

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result, channel)

            # For voice, return only conversational text (no JSON)
            if channel == 'voice':
                return conversational

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'reschedule_appointment':
            # Check for errors first
            if 'error' in response_body:
                error_message = response_body['error']
                friendly_error = f"I wasn't able to reschedule this appointment. The system reported: {error_message}. Please try again or contact support if the problem continues."
                logger.warning(f"[ERROR] Appointment reschedule failed: {error_message}")
                return friendly_error

            # Check for "cannot reschedule" status
            if response_body.get('status') == 'cannot_reschedule':
                result = {
                    "message": response_body.get('message', 'Cannot reschedule this appointment'),
                    "status": "cannot_reschedule",
                    "details": response_body
                }
                conversational = generate_conversational_response(action, user_message, result, channel)
                if channel == 'voice':
                    return conversational
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Handle timeout status from scheduling Lambda
            if response_body.get('status') == 'timeout':
                result = {
                    "message": response_body.get('message', 'The rescheduling service is taking too long to respond. Please try again in a few minutes.'),
                    "status": "timeout",
                    "project_id": response_body.get('project_id'),
                    "action_type": "reschedule"
                }
                conversational = generate_conversational_response(action, user_message, result, channel)
                if channel == 'voice':
                    return conversational
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Handle error status from scheduling Lambda
            if response_body.get('status') == 'error':
                result = {
                    "message": response_body.get('message', 'Unable to reschedule the appointment. Please try again.'),
                    "status": "error",
                    "project_id": response_body.get('project_id'),
                    "action_type": "reschedule"
                }
                conversational = generate_conversational_response(action, user_message, result, channel)
                if channel == 'voice':
                    return conversational
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Handle "cancelled_awaiting_dates" status - Step 1 of reschedule complete, waiting for user to confirm
            if response_body.get('status') == 'cancelled_awaiting_dates':
                project_id = response_body.get('project_id', '')
                result = {
                    "message": response_body.get('message', f"I've cancelled your existing appointment for project #{project_id}. Would you like me to show you the available dates for rescheduling?"),
                    "project_id": project_id,
                    "status": "cancelled_awaiting_dates",
                    "action_type": "reschedule",
                    "requires_confirmation": True
                }
                conversational = generate_conversational_response(action, user_message, result, channel)
                if channel == 'voice':
                    return conversational
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Handle "awaiting_date_selection" status - reschedule workflow started, show available dates
            if response_body.get('status') == 'awaiting_date_selection':
                available_dates = response_body.get('available_dates', [])
                project_id = response_body.get('project_id', '')

                # Check for weather-enriched dates (same as get_available_dates)
                dates_with_weather = response_body.get('dates_with_weather', [])
                has_weather_concerns = response_body.get('has_weather_concerns', False)

                from datetime import datetime
                formatted_dates = []

                if dates_with_weather:
                    # Use enriched dates with weather indicators (same as scheduling)
                    for enriched_date in dates_with_weather:
                        date_str = enriched_date.get('date', '')
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            formatted_dates.append({
                                "date": date_obj.strftime("%m/%d/%Y"),
                                "displayDate": date_obj.strftime("%m/%d/%Y"),
                                "dayShort": date_obj.strftime("%a"),
                                "monthDay": date_obj.strftime("%m/%d"),
                                "dayName": date_obj.strftime("%A"),
                                "formatted": date_obj.strftime("%a %m/%d/%Y"),
                                # Weather info
                                "weatherIndicator": enriched_date.get('indicator', ''),
                                "weatherSuitable": enriched_date.get('suitable', True),
                                "weatherSeverity": enriched_date.get('severity', 'low'),
                                "weatherCondition": enriched_date.get('condition', ''),
                                "weatherWarnings": enriched_date.get('warnings', []),
                                "highTemp": enriched_date.get('high_temp'),
                                "lowTemp": enriched_date.get('low_temp')
                            })
                        except:
                            formatted_dates.append({
                                "date": date_str,
                                "monthDay": date_str,
                                "weatherIndicator": enriched_date.get('indicator', ''),
                                "weatherSuitable": enriched_date.get('suitable', True)
                            })

                    logger.info(f"[WEATHER] Formatted {len(formatted_dates)} reschedule dates with weather indicators")
                else:
                    # No weather data - use basic date formatting (convert to MM/DD/YYYY)
                    for date_str in available_dates:
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            formatted_dates.append({
                                "date": date_obj.strftime("%m/%d/%Y"),
                                "displayDate": date_obj.strftime("%m/%d/%Y"),
                                "dayShort": date_obj.strftime("%a"),
                                "monthDay": date_obj.strftime("%m/%d"),
                                "dayName": date_obj.strftime("%A"),
                                "formatted": date_obj.strftime("%a %m/%d/%Y")
                            })
                        except:
                            formatted_dates.append({"date": date_str, "monthDay": date_str})

                result = {
                    "message": f"I've initiated the rescheduling process for project #{project_id}. Here are the available dates:",
                    "project_id": project_id,
                    "dates": formatted_dates,
                    "dateCount": len(formatted_dates),
                    "request_id": response_body.get('request_id'),
                    "status": "awaiting_date_selection",
                    "action_type": "reschedule"
                }

                # Add weather concern flags if present
                if has_weather_concerns:
                    result['has_weather_concerns'] = True
                    result['suitable_date_count'] = response_body.get('suitable_date_count', 0)
                    result['unsuitable_date_count'] = response_body.get('unsuitable_date_count', 0)

                conversational = generate_conversational_response(action, user_message, result, channel)
                if channel == 'voice':
                    return conversational
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Format successful reschedule confirmation response
            appointment = response_body.get('appointment', {})

            # Helper to convert date from YYYY-MM-DD to MM/DD/YYYY
            def format_date_display(date_str):
                if not date_str:
                    return date_str
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    return date_obj.strftime("%m/%d/%Y")
                except:
                    return date_str

            # Format dates in appointment object
            if appointment:
                if 'scheduled_date' in appointment:
                    appointment['scheduled_date'] = format_date_display(appointment['scheduled_date'])
                if 'scheduledDate' in appointment:
                    appointment['scheduledDate'] = format_date_display(appointment['scheduledDate'])

            # Also format top-level scheduled_date if present
            if 'scheduled_date' in response_body:
                response_body['scheduled_date'] = format_date_display(response_body['scheduled_date'])

            result = {
                "message": "[OK] Appointment rescheduled successfully!",
                "appointment": appointment or response_body,
                "status": "success"
            }

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result, channel)

            # For voice, return only conversational text (no JSON)
            if channel == 'voice':
                return conversational

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'cancel_appointment':
            # Check for errors first
            if 'error' in response_body:
                error_message = response_body['error']
                result = {
                    "message": f"[ERROR] Failed to cancel appointment: {error_message}",
                    "status": "error",
                    "details": response_body
                }
                return f"```json\n{json.dumps(result, indent=2)}\n```"

            # Check if awaiting confirmation (two-step cancel flow)
            if response_body.get('status') == 'awaiting_confirmation':
                project = response_body.get('project', {})
                project_id = response_body.get('project_id', '')
                scheduled_date = project.get('scheduledDate', 'N/A')
                category = project.get('category', 'Project')
                project_type = project.get('projectType', '')

                result = {
                    "message": f"Found project #{project_id} ({category} - {project_type}) scheduled for {scheduled_date}. Please confirm you want to cancel this appointment.",
                    "status": "awaiting_confirmation",
                    "project": project,
                    "requires_confirmation": True
                }

                # Generate conversational response asking for confirmation
                conversational = generate_conversational_response(action, user_message, result, channel)
                if channel == 'voice':
                    return conversational
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Check for "cannot cancel" status
            if response_body.get('status') in ['cannot_cancel', 'not_scheduled']:
                result = {
                    "message": response_body.get('message', 'Cannot cancel this appointment'),
                    "status": response_body.get('status'),
                    "details": response_body
                }
                conversational = generate_conversational_response(action, user_message, result, channel)
                if channel == 'voice':
                    return conversational
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Format successful cancellation confirmation response
            result = {
                "message": "[OK] Appointment cancelled successfully!",
                "details": response_body,
                "status": "success"
            }

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result, channel)

            # For voice, return only conversational text (no JSON)
            if channel == 'voice':
                return conversational

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_weather':
            # Format weather data for UI rendering
            # Handle both nested structure (weather.current) and flat structure (current)
            weather_data = response_body.get('weather', {})

            # Try nested first, then flat
            location_data = weather_data.get('location', {}) or response_body.get('location_data', {})
            current_data = weather_data.get('current', {}) or response_body.get('current', {})
            forecast_data = weather_data.get('forecast', []) or response_body.get('forecast', [])

            # Build location string
            # Handle both dict location_data and string location
            raw_location = response_body.get('location', '')
            if isinstance(raw_location, str) and raw_location:
                # Flat structure: location is a string like "Minneapolis, MN, United States"
                location_str = raw_location
            elif isinstance(location_data, dict):
                # Nested structure: location_data is a dict
                location_name = location_data.get('name', 'Unknown')
                admin1 = location_data.get('admin1', '')
                country = location_data.get('country', '')

                if admin1 and country:
                    location_str = f"{location_name}, {admin1}, {country}"
                elif admin1:
                    location_str = f"{location_name}, {admin1}"
                else:
                    location_str = location_name
            else:
                location_str = 'Unknown Location'

            # Format forecast with day names
            from datetime import datetime
            formatted_forecast = []
            for day in forecast_data:
                try:
                    date_obj = datetime.strptime(day.get('date', ''), "%Y-%m-%d")
                    day_name = date_obj.strftime("%A")
                except:
                    day_name = day.get('date', 'Unknown')

                formatted_forecast.append({
                    "day": day_name,
                    "condition": day.get('condition', 'Unknown'),
                    "high": day.get('max_temp_f', 0),
                    "low": day.get('min_temp_f', 0),
                    "precipitation": day.get('precipitation_probability', 0)
                })

            # Get target date info (for scheduled projects or +7 days)
            target_date = response_body.get('target_date')
            target_forecast = response_body.get('target_forecast')

            # Format target forecast if available
            formatted_target = None
            if target_forecast:
                try:
                    date_obj = datetime.strptime(target_forecast.get('date', ''), "%Y-%m-%d")
                    formatted_target = {
                        "date": target_forecast.get('date'),
                        "displayDate": date_obj.strftime("%m/%d/%Y"),
                        "day": date_obj.strftime("%A %m/%d"),
                        "condition": target_forecast.get('condition', 'Unknown'),
                        "high": target_forecast.get('max_temp_f', 0),
                        "low": target_forecast.get('min_temp_f', 0),
                        "precipitation": target_forecast.get('precipitation_probability', 0)
                    }
                except:
                    formatted_target = target_forecast

            # Prepare structured data for UI
            result = {
                "location": location_str,
                "current": {
                    "temperature": current_data.get('temp_f', current_data.get('temp_F', 0)),
                    "condition": current_data.get('condition', 'Unknown'),
                    "humidity": current_data.get('humidity', 0),
                    "windSpeed": current_data.get('wind_mph', current_data.get('windspeedMiles', 0))
                },
                "forecast": formatted_forecast,
                "target_date": target_date,
                "target_forecast": formatted_target
            }

            # Validate weather data - don't return zeros/Unknown
            is_invalid = (
                location_str in ['Unknown', 'Unknown Location'] or
                (result['current']['temperature'] == 0 and
                 result['current']['humidity'] == 0 and
                 result['current']['condition'] == 'Unknown')
            )
            if is_invalid:
                logger.warning(f"[WEATHER] Invalid weather data - location: {location_str}, temp: {result['current']['temperature']}")
                if channel == 'voice':
                    return "I couldn't get the weather. Which city would you like me to check?"
                return "I couldn't retrieve weather data. Please specify a city name (e.g., 'weather in Minneapolis') or ask about a specific project's location."

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result, channel)

            # For voice, return only conversational text (no JSON)
            if channel == 'voice':
                return conversational

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'add_note':
            # Format add_note response for UI
            project_id = response_body.get('project_id', 'Unknown')
            note_text = response_body.get('note_text', '')
            author = response_body.get('author', 'Agent')
            note_data = response_body.get('note_data', {})
            created_at = note_data.get('created_at', '')

            # Prepare structured result with clean message
            result = {
                "status": "success",
                "message": "Note added for reference",
                "note": {
                    "project_id": project_id,
                    "text": note_text,
                    "author": author,
                    "created_at": created_at
                }
            }

            # Generate conversational response
            if channel == 'voice':
                return f"I've added the note to project {project_id}. The note says: {note_text}"

            # Chat response - clean checkmark confirmation
            conversational = f"Note added for reference"

            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'list_notes':
            # Format list_notes response for UI
            project_id = response_body.get('project_id', 'Unknown')
            notes = response_body.get('notes', [])
            total_count = response_body.get('total_count', len(notes))

            if not notes:
                if channel == 'voice':
                    return f"There are no notes for project {project_id}."
                return f"No notes found for project #{project_id}."

            # Prepare structured result
            result = {
                "project_id": project_id,
                "notes": notes,
                "total_count": total_count
            }

            # Generate conversational response
            if channel == 'voice':
                note_summaries = []
                for i, note in enumerate(notes[:3], 1):  # Limit to first 3 for voice
                    note_summaries.append(f"Note {i}: {note.get('note_text', '')[:50]}")
                return f"Project {project_id} has {total_count} notes. " + ". ".join(note_summaries)

            conversational = f"Found {total_count} note(s) for project #{project_id}"

            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        else:
            # Fallback: return JSON for unknown actions
            return json.dumps(response_body, indent=2)

    except Exception as e:
        logger.error(f"Error formatting Lambda response: {e}")
        # Fallback to JSON if formatting fails
        return json.dumps(response_body, indent=2)


def generate_welcome_greeting(user_name: str, projects: list) -> str:
    """
    Use Claude to generate a personalized welcome greeting with project summary.
    Includes retry logic for reliability.

    Designed for simple, conversational English suitable for ages 20-80.

    Args:
        user_name: User's display name (may be empty)
        projects: List of user's projects from list_projects

    Returns:
        Friendly welcome message mentioning their projects
    """
    client = get_bedrock_runtime_client()

    # Build project summary for the prompt
    if projects:
        project_summary = []
        for p in projects:
            status = p.get('status', 'Unknown')
            category = p.get('category', 'Project')
            proj_id = p.get('id', '')
            scheduled_date = p.get('scheduledDate', '')

            if scheduled_date:
                project_summary.append(f"- {category} (#{proj_id}): {status}, scheduled for {scheduled_date}")
            else:
                project_summary.append(f"- {category} (#{proj_id}): {status}")

        project_data = "\n".join(project_summary)
    else:
        project_data = "No projects found"

    system_prompt = """You're welcoming someone to their home services account.
Be warm and natural - like a friendly neighbor, not a corporate script.

GUIDELINES:
- Use their name if provided: "Hey John!" or "Hi Sarah!"
- No name? Just "Hey there!" or "Hi!"
- Mention what they have going on (projects, appointments)
- Keep it SHORT - 2-3 sentences max
- End with something helpful, not salesy

GOOD EXAMPLES:
"Hey John! Good to see you. You've got 3 projects going - your deck's ready to schedule whenever you are."
"Hi there! You have a roofing appointment coming up on the 26th. Need to make any changes?"
"Hey Sarah! Looks like your kitchen remodel is all scheduled. Anything else I can help with?"

AVOID:
- "Welcome back to ProjectForce" (too formal)
- "I'm here to assist you" (robotic)
- Long lists of everything they could do
- Multiple questions at the end"""

    user_prompt = f"""Name: {user_name if user_name else 'none'}
Projects: {len(projects)}
Details:
{project_data}

Write a brief, friendly welcome. Be conversational."""

    def make_bedrock_call():
        """Inner function for retry wrapper"""
        return client.converse(
            modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_prompt}]
                }
            ],
            system=[{"text": system_prompt}],
            inferenceConfig={
                "maxTokens": 200,
                "temperature": 0.7,
                "topP": 0.9
            }
        )

    try:
        # Use retry logic for reliability
        response = retry_with_backoff(make_bedrock_call)

        greeting = response['output']['message']['content'][0]['text']
        logger.info(f"[OK] Generated welcome greeting ({len(greeting)} chars)")
        return greeting.strip()

    except Exception as e:
        logger.error(f"Failed to generate welcome greeting after retries: {e}")
        # Fallback greeting - still friendly
        name_part = f" {user_name}" if user_name else ""
        if projects:
            project_types = list(set(p.get('category', 'project') for p in projects[:3]))
            types_str = ", ".join(project_types[:2])
            return f"Hey{name_part}! You've got {len(projects)} project(s) with us - {types_str}. What can I help you with?"
        else:
            return f"Hey{name_part}! Welcome. No projects set up yet, but I'm here when you're ready."


def handle_welcome_request(
    customer_id: str,
    client_id: str,
    pf_bearer_token: str,
    user_name: str,
    session_id: str
) -> Dict[str, Any]:
    """
    Handle welcome request triggered by frontend after login.

    Fetches user's projects and generates a personalized greeting.

    Args:
        customer_id: User's customer ID
        client_id: Client ID
        pf_bearer_token: API bearer token
        user_name: User's display name
        session_id: Session identifier

    Returns:
        Response dict with greeting, projects, and metadata
    """
    import time
    start_time = time.time()

    try:
        # Fetch user's projects
        logger.info(f"[INFO] Fetching projects for welcome greeting (customer_id={customer_id})")

        projects_response = call_lambda_directly('list_projects', {
            'customer_id': customer_id,
            'client_id': client_id,
            'pf_bearer_token': pf_bearer_token
        })

        # Extract projects from Lambda response
        response_data = projects_response.get('response', {})
        function_response = response_data.get('functionResponse', {})
        response_body_wrapper = function_response.get('responseBody', {})
        text_wrapper = response_body_wrapper.get('TEXT', {})
        response_body_str = text_wrapper.get('body', '{}')

        if isinstance(response_body_str, str):
            response_body = json.loads(response_body_str)
        else:
            response_body = response_body_str

        projects = response_body.get('projects', [])
        pf_http_status_code = response_body.get('pf_http_status_code', 200)
        logger.info(f"[INFO] Found {len(projects)} projects for user")

        # STORE project_ids AND project_mapping in workflow_state
        # This enables ordinal refs ("first project") AND category refs ("kitchen sink project")
        if projects:
            project_ids = [str(p.get('id', '')) for p in projects if p.get('id')]
            # Build project_mapping for category-based lookups
            project_mapping = {}
            for p in projects:
                pid = str(p.get('id', ''))
                if pid:
                    project_mapping[pid] = {
                        'category': p.get('category', ''),
                        'address': p.get('address', ''),
                        'status': p.get('status', '')
                    }
            if project_ids:
                try:
                    from workflow_state import get_state_manager
                    state_manager = get_state_manager()
                    state_manager.save_state(session_id, {
                        'workflow_type': 'project_list',
                        'current_stage': 'projects_displayed',
                        'context': {
                            'project_ids': project_ids,
                            'project_mapping': project_mapping,
                            'project_count': len(project_ids)
                        }
                    })
                    logger.info(f"[WORKFLOW] Stored {len(project_ids)} project_ids and project_mapping in workflow state")
                except Exception as e:
                    logger.warning(f"[WORKFLOW] Failed to store project_ids in workflow state: {e}")

        # Generate personalized greeting
        greeting = generate_welcome_greeting(user_name, projects)

        # Format response with JSON block (like list_projects does)
        # This ensures the frontend renders the project table
        if projects:
            result = {
                "message": f"Found {len(projects)} project(s):",
                "projects": projects
            }
            formatted_response = f"{greeting}\n\n```json\n{json.dumps(result, indent=2)}\n```"
        else:
            formatted_response = greeting

        timing = {
            'total': time.time() - start_time
        }

        logger.info(f"[WELCOME] Welcome response generated in {timing['total']:.2f}s")

        return {
            'response': formatted_response,
            'agent_name': 'Welcome',
            'intent': 'welcome',
            'action': 'welcome_with_projects',
            'session_id': session_id,
            'direct_call': True,
            'projects': projects,  # Include projects for frontend rendering
            'timing': timing,
            'pf_http_status_code': pf_http_status_code,
            'agenticscheduler_http_status_code': 200
        }

    except Exception as e:
        logger.error(f"Welcome request failed: {e}")
        error_str = str(e).lower()

        # Check if this is an auth/session error
        is_auth_error = any(keyword in error_str for keyword in ['token', 'auth', 'expired', '401', '403', 'unauthorized'])

        if is_auth_error:
            logger.info(f"[AUTH] Welcome failed due to session expiration - setting pf_http_status_code=401")
            return {
                'response': "Your session has expired. Please log in again to continue.",
                'agent_name': 'Welcome',
                'intent': 'welcome',
                'action': 'session_expired',
                'session_id': session_id,
                'direct_call': True,
                'projects': [],
                'timing': {'total': time.time() - start_time},
                'pf_http_status_code': 401,
                'agenticscheduler_http_status_code': 200
            }

        # Return graceful fallback for non-auth errors
        name_part = f", {user_name}" if user_name else ""
        return {
            'response': f"Hello{name_part}! Welcome to ProjectForce. I'm here to help with your home service projects.",
            'agent_name': 'Welcome',
            'intent': 'welcome',
            'action': 'welcome_fallback',
            'session_id': session_id,
            'direct_call': True,
            'projects': [],
            'timing': {'total': time.time() - start_time},
            'pf_http_status_code': None,
            'agenticscheduler_http_status_code': 200
        }


def call_lambda_directly(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Lambda function directly for simple actions

    Args:
        action: Action name (list_projects, get_project_details, etc.)
        params: Parameters including customer_id, client_id, pf_bearer_token, and action-specific params

    Returns:
        Lambda response payload

    Raises:
        ValueError: If action is unknown
        Exception: If Lambda invocation fails
    """
    config = get_config()
    lambda_client = get_lambda_client()

    # Map action to Lambda function (use config values for dynamic naming)
    lambda_functions = {
        # Chitchat actions
        'greet': config.chitchat_lambda,
        'help': config.chitchat_lambda,
        'general': config.chitchat_lambda,
        # Information actions
        'get_weather': config.information_lambda,
        # Scheduling query actions
        'list_projects': config.scheduling_lambda,
        'get_project_details': config.scheduling_lambda,
        'get_available_dates': config.scheduling_lambda,
        'get_time_slots': config.scheduling_lambda,
        'get_available_timeslots': config.scheduling_lambda,  # Alias for get_time_slots
        'get_business_hours': config.scheduling_lambda,
        'get_rescheduler_slots': config.scheduling_lambda,  # For reschedule workflow
        # Scheduling write actions
        'confirm_appointment': config.scheduling_lambda,
        'reschedule_appointment': config.scheduling_lambda,
        'cancel_appointment': config.scheduling_lambda,
        # Notes actions - add/create
        'add_notes': config.notes_lambda,
        'add_note': config.notes_lambda,
        'add_project_note': config.notes_lambda,
        'addprojectnote': config.notes_lambda,
        'create_note': config.notes_lambda,
        'save_note': config.notes_lambda,
        'add_reminder': config.notes_lambda,
        'add_comment': config.notes_lambda,
        'add_project_comment': config.notes_lambda,
        'note': config.notes_lambda,
        # Notes actions - list/get
        'list_notes': config.notes_lambda,
        'get_notes': config.notes_lambda,
        'get_project_notes': config.notes_lambda,
        'view_notes': config.notes_lambda,
        'show_notes': config.notes_lambda,
        'list_reminders': config.notes_lambda,
        'get_reminders': config.notes_lambda,
        'list_comments': config.notes_lambda,
        'get_comments': config.notes_lambda
    }

    function_name = lambda_functions.get(action)
    if not function_name:
        raise ValueError(f"Unknown action: {action}")

    # Convert action name from underscore to kebab-case for apiPath
    # (e.g., confirm_appointment -> confirm-appointment)
    api_path = '/' + action.replace('_', '-')

    # Construct Lambda event (Bedrock agent format)
    event = {
        'actionGroup': 'scheduling-actions',
        'function': action,
        'apiPath': api_path,  # Scheduling Lambda reads from apiPath
        'httpMethod': 'POST',
        'parameters': [
            {'name': key, 'value': str(value)}
            for key, value in params.items()
            if key not in ['customer_id', 'client_id', 'pf_bearer_token', 'from_phone']
        ],
        'sessionAttributes': {
            'customer_id': params.get('customer_id', ''),
            'client_id': params.get('client_id', ''),
            'pf_bearer_token': params.get('pf_bearer_token', ''),
            'from_phone': params.get('from_phone', '')  # For voice cache lookup
        }
    }

    logger.info(f"[LAMBDA] Calling Lambda directly: {function_name}.{action}")
    logger.debug(f"Lambda event: {json.dumps(event, indent=2)}")

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        payload = json.loads(response['Payload'].read())
        logger.info(f"[OK] Lambda direct call successful")
        return payload

    except Exception as e:
        logger.error(f"Lambda direct call error: {e}")
        raise


def build_conversation_context(conversation_history: Optional[list], max_messages: int = 4) -> str:
    """
    Build a compact conversation context summary from recent history

    Args:
        conversation_history: List of previous messages
        max_messages: Maximum number of recent messages to include

    Returns:
        Formatted context string
    """
    if not conversation_history or len(conversation_history) == 0:
        return ""

    # Get last N messages (excluding current)
    recent_messages = conversation_history[-max_messages:] if len(conversation_history) > max_messages else conversation_history

    context_lines = []
    for msg in recent_messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')

        # Truncate long messages
        if len(content) > 150:
            content = content[:150] + "..."

        context_lines.append(f"{role.upper()}: {content}")

    if context_lines:
        return "\n".join(context_lines)

    return ""


# DEPRECATED: Bedrock agents are no longer used
# All functionality moved to direct Lambda calls and workflow orchestration
# The invoke_bedrock_agent() function has been removed.


def route_request(
    message: str,
    session_id: str,
    customer_id: str,
    client_id: str,
    pf_bearer_token: str = None,
    conversation_history: Optional[list] = None,
    channel: str = 'chat',
    from_phone: str = '',
    project_id: str = ''
) -> Dict[str, Any]:
    """
    Route request to either Direct Lambda or Bedrock Agent
    Uses multi-agent orchestration when enabled

    Args:
        message: User message
        session_id: Session identifier
        customer_id: Customer ID
        client_id: Client ID
        pf_bearer_token: ProjectForce API bearer token (optional - can use Secrets Manager)
        conversation_history: Previous conversation for context
        channel: Channel type ('voice' or 'chat') - determines response formatting
        from_phone: Caller phone number for voice cache lookup
        project_id: Optional project_id from GPT-4o smart prompt embedded state

    Returns:
        Dictionary with:
        - response: Response text (JSON string or plain text)
        - intent: Classified intent
        - action: Action name (if direct call)
        - agent_name: Agent name (if agent call)
        - direct_call: True/False
        - timing: Performance metrics
    """
    config = get_config()

    # NEW: Use multi-agent orchestration if enabled
    if config.enable_multi_agent_orchestration:
        logger.info("[ORCHESTRATION] Using multi-agent orchestration")

        try:
            from multi_agent_router import route_with_multi_agent_orchestration

            return route_with_multi_agent_orchestration(
                message=message,
                session_id=session_id,
                customer_id=customer_id,
                client_id=client_id,
                pf_bearer_token=pf_bearer_token,
                conversation_history=conversation_history
            )
        except ImportError as e:
            logger.warning(f"Multi-agent router not available: {e}, falling back to standard routing")
        except Exception as e:
            logger.error(f"Multi-agent routing error: {e}, falling back to standard routing")

    # FALLBACK: Use standard routing
    logger.info("[ROUTING] Using standard routing")

    timing = {}
    start_time = time.time()

    # ========================================================================
    # ORDINAL PROJECT REFERENCES: Route directly to intelligent orchestrator
    # Skip context_resolver for "first project", "last project", "2nd project" etc.
    # to use workflow_state's project_ids list instead of conversation history parsing
    # ========================================================================
    from intelligent_orchestrator import extract_ordinal_project_reference

    ordinal_index = extract_ordinal_project_reference(message)
    if ordinal_index is not None:
        logger.info(f"[ORDINAL] Detected ordinal reference in message: index={ordinal_index}")
        logger.info(f"[ORDINAL] Routing directly to intelligent orchestrator (skip context_resolver)")

        try:
            from intelligent_orchestrator import orchestrate_intelligent_workflow

            intelligent_result = orchestrate_intelligent_workflow(
                message=message,  # Pass ORIGINAL message (not resolved)
                session_id=session_id,
                customer_id=customer_id,
                client_id=client_id,
                pf_bearer_token=pf_bearer_token,
                conversation_history=conversation_history,
                channel=channel,
                from_phone=from_phone,
                project_id=project_id  # From GPT-4o smart prompt embedded state
            )

            # VOICE ADAPTATION: For voice channel, format the response
            if channel == 'voice' and 'response' in intelligent_result:
                response_text = intelligent_result['response']
                # Strip JSON block and keep only conversational text
                if '```json' in response_text:
                    voice_response = response_text.split('```json')[0].strip()
                else:
                    voice_response = response_text
                # Apply voice formatting (includes date summarization)
                voice_response = format_for_voice(voice_response, intelligent_result.get('intent', 'unknown'))
                intelligent_result['response'] = voice_response
                intelligent_result['channel'] = channel
                logger.info(f"[VOICE] Adapted ordinal orchestrator response for voice")

            timing['total'] = time.time() - start_time
            return intelligent_result

        except Exception as e:
            logger.error(f"[ORDINAL] Error in ordinal routing: {e}")
            # Fall through to normal flow on error

    # CONTEXT RESOLUTION: Resolve references like "last project", "it", "that" BEFORE classification
    resolved_context = resolve_context_references(message, conversation_history)
    resolved_message = resolved_context['resolved_message']
    resolved_entities = resolved_context['entities']

    # Log context resolution
    if resolved_message != message:
        logger.info(f"[CONTEXT] Context resolved: '{message}' -> '{resolved_message}'")
    if resolved_entities:
        logger.info(f"[ENTITIES] Resolved entities: {resolved_entities}")

    # Use resolved message for classification
    classification = classify_intent_and_action(resolved_message, conversation_history)
    intent = classification.get('intent', 'chitchat')
    action = classification.get('action')
    can_call_direct = classification.get('can_call_direct', False)
    extracted_params = classification.get('params') or {}

    # Merge resolved entities with extracted params
    # IMPORTANT: Extracted params (from user's explicit input) take precedence over resolved entities (from context)
    # e.g., "schedule project 9000489" should use 9000489, not last_project from context
    merged_params = {**resolved_entities, **extracted_params}

    timing['classification'] = time.time() - start_time

    logger.info(f"[INFO] Classification: intent={intent}, action={action}, can_call_direct={can_call_direct}")
    logger.info(f"[INFO] Extracted params: {extracted_params}")
    if resolved_entities:
        logger.info(f"[INFO] Merged params (with resolved entities): {merged_params}")

    # Session attributes for agent calls
    session_attributes = {
        'customer_id': customer_id,
        'client_id': client_id,
        'pf_bearer_token': pf_bearer_token
    }

    # INTELLIGENT ORCHESTRATION: Use Sonnet 3.7 for ALL workflow decisions
    # NO hardcoding, NO regex - pure intelligence!
    workflow_actions = [
        'schedule_project', 'confirm_appointment', 'reschedule_appointment',
        'cancel_appointment', 'add_note', 'list_notes'
    ]

    # Weather ALWAYS goes through intelligent orchestration for proper context extraction
    # Sonnet enricher handles location resolution from project context
    needs_intelligent_orchestration = (
        action in workflow_actions or
        intent == 'scheduling' or
        action == 'get_weather'  # Always use Sonnet for weather context
    )

    if needs_intelligent_orchestration:
        logger.info(f"[SONNET] INTELLIGENT ORCHESTRATION: Using Sonnet 3.7 for workflow decisions")

        try:
            from intelligent_orchestrator import orchestrate_intelligent_workflow

            intelligent_result = orchestrate_intelligent_workflow(
                message=resolved_message,
                session_id=session_id,
                customer_id=customer_id,
                client_id=client_id,
                pf_bearer_token=pf_bearer_token,
                conversation_history=conversation_history,
                channel=channel,  # Pass channel for voice-specific handling
                from_phone=from_phone,
                project_id=project_id  # From GPT-4o smart prompt embedded state
            )

            # VOICE ADAPTATION: For voice channel, format the response
            if channel == 'voice' and 'response' in intelligent_result:
                response_text = intelligent_result['response']
                # Strip JSON block and keep only conversational text
                if '```json' in response_text:
                    voice_response = response_text.split('```json')[0].strip()
                else:
                    voice_response = response_text
                # Apply voice formatting
                voice_response = format_for_voice(voice_response, intelligent_result.get('intent', 'unknown'))
                intelligent_result['response'] = voice_response
                intelligent_result['channel'] = channel
                logger.info(f"[VOICE] Adapted intelligent orchestrator response for voice")

            return intelligent_result

        except Exception as e:
            logger.error(f"Intelligent orchestration failed: {e}")
            # Fall through to direct Lambda call below

    # OPTIMIZATION: Call Lambda directly for simple data retrieval
    if config.allow_direct_lambda and can_call_direct and action:
        logger.info(f"[LAMBDA] DIRECT LAMBDA CALL: {action} (bypassing Bedrock)")

        try:
            lambda_start = time.time()

            # Prepare Lambda parameters (merge session params with merged params)
            lambda_params = {
                'customer_id': customer_id,
                'client_id': client_id,
                'pf_bearer_token': pf_bearer_token,
                'from_phone': from_phone,  # For voice cache lookup
                **merged_params  # Add merged params (extracted + resolved entities)
            }

            # STATIC GREETING: Return consistent J greeting for SMS/Chat (skip chitchat Lambda)
            if action == 'greet':
                static_greeting = "I'm J, your AI assistant from ProjectForce! I can help you view your projects, check available dates, or schedule appointments. What would you like to do today?"
                logger.info(f"[GREET] Returning static J greeting for channel={channel}")
                timing['total'] = time.time() - start_time
                return {
                    'response': static_greeting,
                    'agent_name': 'chitchat',
                    'intent': 'chitchat',
                    'action': 'greet',
                    'direct_call': True,
                    'timing': timing,
                    'routing_method': 'static_greeting'
                }

            # CALENDAR INFO: What day is [date]? - Use Python datetime for accurate answers
            if action == 'calendar_info':
                logger.info(f"[CALENDAR-INFO] Handling day-of-week question")
                from datetime import datetime as dt
                import re as regex

                # Month name mapping
                months = {
                    'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
                    'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
                    'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
                    'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
                }

                target_date = None
                current_date = dt.now()
                date_param = merged_params.get('date', '')

                # Try YYYY-MM-DD format first (from LLM)
                if date_param:
                    try:
                        target_date = dt.strptime(date_param, "%Y-%m-%d")
                    except ValueError:
                        pass

                # Fallback: parse natural language from message
                if not target_date:
                    msg_lower = message.lower()
                    date_match = regex.search(r'(\w+)\s+(\d+)(?:st|nd|rd|th)?', msg_lower)
                    if date_match:
                        month_str = date_match.group(1).lower()
                        day = int(date_match.group(2))
                        month = months.get(month_str)
                        if month:
                            year = current_date.year
                            try:
                                target_date = dt(year, month, day)
                                if target_date < current_date:
                                    year += 1
                                    target_date = dt(year, month, day)
                            except ValueError:
                                pass

                if target_date:
                    day_name = target_date.strftime("%A")
                    formatted_date = target_date.strftime("%B %d, %Y")
                    date_iso = target_date.strftime("%Y-%m-%d")
                    response_text = f"{formatted_date} is a {day_name}."

                    # Save the date to workflow state so "book this date" can reference it
                    from workflow_state import get_state_manager
                    state_manager = get_state_manager()
                    current_state = state_manager.get_state(session_id) or {}
                    if 'context' not in current_state:
                        current_state['context'] = {}
                    current_state['context']['last_calendar_date'] = date_iso
                    current_state['context']['last_calendar_date_display'] = formatted_date
                    state_manager.save_state(session_id, current_state)
                    logger.info(f"[CALENDAR-INFO] Saved {date_iso} to context for 'this date' references")
                else:
                    response_text = "I couldn't understand that date. Could you please say it again, like 'September 14th'?"

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'agent_name': 'calendar',
                    'intent': 'information',
                    'action': 'calendar_info',
                    'direct_call': True,
                    'timing': timing,
                    'routing_method': 'calendar_info_handler'
                }

            # CHITCHAT ACTIONS: Always pass the message so chitchat Lambda can do its own intent detection
            chitchat_actions = ['help', 'general', 'chitchat']  # 'greet' handled above
            if action in chitchat_actions:
                lambda_params['message'] = message  # Pass original message
                logger.info(f"[CHITCHAT] Passing message to chitchat Lambda: '{message[:50]}...'")

            # WEATHER AUTO-FETCH: If no location provided, try to get it from conversation history
            if action == 'get_weather' and not lambda_params.get('location'):
                logger.info(f"[WEATHER] No location in params, checking conversation history for project")

                # Try to find project in conversation history
                project_id_from_history = None
                if conversation_history:
                    for entry in reversed(conversation_history):
                        # Check assistant responses for project details
                        if entry.get('role') == 'assistant':
                            content = entry.get('content', '')
                            if isinstance(content, str):
                                # Look for project ID patterns in recent responses
                                import re
                                # Match patterns like "Project #9000407" or "project_id: 9000407"
                                proj_match = re.search(r'Project\s*#?\s*(\d{7})', content, re.IGNORECASE)
                                if proj_match:
                                    project_id_from_history = proj_match.group(1)
                                    logger.info(f"[WEATHER] Found project ID in history: {project_id_from_history}")
                                    break

                # If we found a project, fetch its location
                if project_id_from_history:
                    try:
                        logger.info(f"[WEATHER] Auto-fetching location for project: {project_id_from_history}")
                        project_response = call_lambda_directly('get_project_details', {
                            'customer_id': customer_id,
                            'client_id': client_id,
                            'pf_bearer_token': pf_bearer_token,
                            'project_id': project_id_from_history
                        })

                        # Extract project data
                        proj_resp = project_response.get('response', {})
                        proj_func = proj_resp.get('functionResponse', {})
                        proj_body_wrapper = proj_func.get('responseBody', {})
                        proj_text = proj_body_wrapper.get('TEXT', {})
                        proj_body_str = proj_text.get('body', '{}')

                        if isinstance(proj_body_str, str):
                            proj_body = json.loads(proj_body_str)
                        else:
                            proj_body = proj_body_str

                        # Extract location from project details
                        project_data = proj_body.get('project', proj_body)
                        city = project_data.get('city', '')
                        state = project_data.get('state', '')

                        if city and state:
                            location = f"{city}, {state}"
                            lambda_params['location'] = location
                            logger.info(f"[WEATHER] Auto-fetched location: {location} for project #{project_id_from_history}")
                        elif city:
                            lambda_params['location'] = city
                            logger.info(f"[WEATHER] Auto-fetched location (city only): {city}")
                    except Exception as fetch_err:
                        logger.warning(f"[WEATHER] Auto-fetch project location failed: {fetch_err}")

            # Call Lambda directly
            lambda_response = call_lambda_directly(action, lambda_params)
            timing['lambda_direct'] = time.time() - lambda_start
            timing['total'] = time.time() - start_time

            # Extract response body from Lambda response
            # Lambda returns nested structure: response.functionResponse.responseBody.TEXT.body
            logger.debug(f"Lambda raw response keys: {lambda_response.keys()}")

            response_data = lambda_response.get('response', {})
            function_response = response_data.get('functionResponse', {})
            response_body_wrapper = function_response.get('responseBody', {})
            text_wrapper = response_body_wrapper.get('TEXT', {})
            response_body_str = text_wrapper.get('body', '{}')

            # Parse the JSON string
            if isinstance(response_body_str, str):
                response_body = json.loads(response_body_str)
            else:
                response_body = response_body_str

            # POST-FILTER PROJECTS: Apply semantic filters since upstream API doesn't filter
            # merged_params may contain status, category, projectType, address, technician_name from classification
            if action == 'list_projects' and 'projects' in response_body and isinstance(response_body['projects'], list):
                original_count = len(response_body['projects'])
                # DEBUG: Log filter params and first project's installer
                logger.info(f"[FILTER-DEBUG] Filtering {original_count} projects with params: {merged_params}")
                if original_count > 0:
                    first_proj = response_body['projects'][0]
                    logger.info(f"[FILTER-DEBUG] Sample project installer: {first_proj.get('installer', 'NOT FOUND')}, technician: {first_proj.get('technician', 'NOT FOUND')}")
                response_body['projects'] = apply_project_filters(response_body['projects'], merged_params)
                filtered_count = len(response_body['projects'])
                logger.info(f"[FILTER] Result: {original_count} -> {filtered_count} projects")

            # Format response for UI - conversational text + structured JSON
            # Pass channel so voice gets concise responses directly from Claude
            formatted_response = format_lambda_response(action, response_body, message, channel)
            logger.debug(f"Formatted response: {formatted_response[:200]}...")

            # VOICE ADAPTATION: Apply additional voice formatting (SSML, date formatting)
            if channel == 'voice':
                # Apply voice formatting (natural dates, numbers, SSML)
                formatted_response = format_for_voice(formatted_response, intent)
                logger.info(f"[VOICE] Applied voice formatting ({len(formatted_response)} chars)")

            logger.info(f"[TIMING]  Direct Lambda Performance: Total={timing['total']:.2f}s | "
                        f"Lambda={timing['lambda_direct']:.2f}s | "
                        f"Classification={timing['classification']:.3f}s")

            return {
                'response': formatted_response,
                'intent': intent,
                'action': action,
                'agent_name': 'Direct Lambda',
                'direct_call': True,
                'timing': timing,
                'channel': channel
            }

        except Exception as e:
            logger.error(f"Direct Lambda call failed: {e}")
            timing['total'] = time.time() - start_time
            error_str = str(e).lower()

            # Check if this is an auth/session error
            is_auth_error = any(keyword in error_str for keyword in ['token', 'auth', 'expired', '401', '403', 'unauthorized'])

            if is_auth_error:
                logger.info(f"[AUTH] Lambda call failed due to session expiration - setting pf_http_status_code=401")
                return {
                    'response': "Your session has expired. Please log in again to continue.",
                    'intent': intent,
                    'action': action,
                    'agent_name': 'Direct Lambda',
                    'direct_call': False,
                    'timing': timing,
                    'pf_http_status_code': 401,
                    'agenticscheduler_http_status_code': 200
                }

            # Use improved error response for non-auth errors
            error_response = get_error_response('api_error', str(e) if 'timeout' not in error_str else None)
            if 'timeout' in error_str:
                error_response = get_error_response('timeout')
            return {
                'response': error_response,
                'intent': intent,
                'action': action,
                'agent_name': 'Direct Lambda',
                'direct_call': False,
                'timing': timing,
                'pf_http_status_code': 200,
                'agenticscheduler_http_status_code': 500
            }

    # NO BEDROCK FALLBACK - All actions should be handled by direct Lambda or workflow
    logger.warning(f"[WARNING] No handler found for: intent={intent}, action={action}, can_call_direct={can_call_direct}")

    timing['total'] = time.time() - start_time
    return {
        'response': get_error_response('unknown_input'),
        'intent': intent,
        'action': action or 'unknown',
        'agent_name': 'Orchestrator',
        'direct_call': False,
        'timing': timing
    }
