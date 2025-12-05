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
from classifier import classify_intent_and_action
from context_extraction import extract_location_from_history, extract_pronoun_reference
from context_resolver import resolve_context_references
from voice_formatter import format_for_voice

logger = logging.getLogger()

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


def generate_conversational_response(action: str, user_message: str, structured_data: Dict[str, Any]) -> str:
    """
    Use Claude via Bedrock Converse API to generate conversational response

    Args:
        action: The action performed (list_projects, get_project_details, etc.)
        user_message: Original user message
        structured_data: Structured data from Lambda response

    Returns:
        Conversational response from Claude
    """
    try:
        client = get_bedrock_runtime_client()

        # Create prompt for Claude
        system_prompt = """You help customers with scheduling. Be DIRECT. No filler.

BANNED PHRASES - NEVER USE THESE:
- "Let me check" / "Let me look" / "Let me find"
- "One moment" / "Just a moment" / "Give me a second"
- "I'm checking" / "I'm looking" / "I'm searching"
- "Hold on" / "Bear with me" / "Just a sec"
- "Sure thing" / "Absolutely" / "Of course"
- "I'd be happy to" / "I can help with that"
- "Here's what I found" / "Here's what I see"

RULES:
1. Start with the answer, not filler
2. Max 1-2 sentences
3. Use contractions (you've, it's, don't)

Examples:
USER: "Show my projects"
WRONG: "Let me check on that for you. One moment. Okay, so you've got 8 projects."
RIGHT: "You've got 8 projects. Which one?"

USER: "Schedule for next week"
WRONG: "Sure thing! Let me look that up. I found 5 available dates."
RIGHT: "5 dates available next week. Which day?"

Weather Warning Guidelines:
- If data contains 'weatherWarning', warn about bad weather conditions in simple terms
- Use phrases like "rain and snow" instead of "precipitation"
- Explain why it matters: "That's not ideal for outdoor work"
- If 'betterDates' are provided, suggest them as alternatives
- Be helpful, not alarming - respect their choice if they still want that date
- Tone: like a helpful neighbor giving advice

IMPORTANT - When 'allDatesHaveWeatherConcerns' is true:
- Tell the user: "Unfortunately, all available dates this week have similar weather concerns"
- Explain briefly what the weather issue is (cold, snow, rain)
- Give them clear options: "You can proceed anyway and our crew will do their best, or wait for new dates to open up"
- Do NOT keep suggesting they pick a different day - there are no better options right now

Proactive Weather Indicators in Available Dates:
- If dates have 'weatherIndicator' fields ([OK], [WARNING], or [ERROR]), mention which dates look good vs concerning
- For [WARNING] or [ERROR] dates, briefly mention the concern (e.g., "cold weather", "snow expected")
- If 'weatherSummary' shows weather concerns, mention: "A few of these dates have weather to consider"
- Show the weather-suitable dates as good options: "Nov 28 and Nov 29 look great weather-wise"
- Present ALL dates but help user make informed choice
- Keep it brief - just highlight the key info, don't explain every date's weather"""

        user_prompt = f"""The user asked: "{user_message}"

I retrieved the following data from our system:
{json.dumps(structured_data, indent=2)}

Please write a friendly, conversational response that:
1. Acknowledges their request
2. Presents the information in a natural, easy-to-understand way
3. Simply states the facts without asking follow-up questions

IMPORTANT: Do NOT end with questions like "Would you like...", "Do you need...", "Can I help with...". Just present the information.

Example of good response:
"Just letting you know that your service appointment is all set. Your project (#7751746) is scheduled for November 26, 2025, from 8:00 AM to 9:00 AM. Our technician, Jay Installer1, will be visiting your place at 401 Chicago Avenue, Minneapolis, MN 55415."

Keep your response concise (3-5 sentences) and friendly. Do NOT include the raw JSON data - I'll show that separately."""

        # Call Claude via Bedrock Converse API (using cross-region inference profile)
        response = client.converse(
            modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_prompt}]
                }
            ],
            system=[{"text": system_prompt}],
            inferenceConfig={
                "maxTokens": 500,
                "temperature": 0.7,
                "topP": 0.9
            }
        )

        # Extract conversational text
        conversational_text = response['output']['message']['content'][0]['text']
        logger.info(f"[OK] Generated conversational response ({len(conversational_text)} chars)")

        return conversational_text.strip()

    except Exception as e:
        logger.error(f"Failed to generate conversational response: {e}")
        # Fallback to simple message if Claude fails
        return f"Here's the information you requested about {action.replace('_', ' ')}:"


def format_lambda_response(action: str, response_body: Dict[str, Any], user_message: str = "") -> str:
    """
    Format Lambda response with conversational text + structured JSON

    Args:
        action: The action that was performed (list_projects, get_project_details, etc.)
        response_body: The Lambda response body (parsed JSON)
        user_message: Original user message for context

    Returns:
        Formatted response with conversational text and structured JSON
    """
    try:
        if action == 'list_projects':
            projects = response_body.get('projects', [])
            if not projects:
                return "You have no projects matching your criteria."

            # Prepare structured data
            result = {
                "message": f"Found {len(projects)} project(s):",
                "projects": projects
            }

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result)

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_project_details':
            project = response_body.get('project', {})
            if not project:
                return "Project details not found."

            # Prepare structured data
            result = {
                "message": f"Project #{project.get('id', 'Unknown')} Details",
                "project": project
            }

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result)

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_available_dates':
            dates = response_body.get('available_dates', [])
            if not dates:
                return "No available dates found for this project."

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
                            "dayShort": date_obj.strftime("%a"),
                            "monthDay": date_obj.strftime("%b %d"),
                            "dayName": date_obj.strftime("%A"),
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
                            "dayShort": date_obj.strftime("%a"),
                            "monthDay": date_obj.strftime("%b %d"),
                            "dayName": date_obj.strftime("%A")
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
            conversational = generate_conversational_response(action, user_message, result)

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

                conversational = generate_conversational_response('get_time_slots', user_message, result)
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Otherwise show available dates
            if not dates:
                return "No available dates found for rescheduling this project."

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
                            "dayShort": date_obj.strftime("%a"),
                            "monthDay": date_obj.strftime("%b %d"),
                            "dayName": date_obj.strftime("%A"),
                            "formatted": date_obj.strftime("%A, %B %d, %Y"),
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
                            "dayShort": date_obj.strftime("%a"),
                            "monthDay": date_obj.strftime("%b %d"),
                            "dayName": date_obj.strftime("%A"),
                            "formatted": date_obj.strftime("%A, %B %d, %Y")
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
            conversational = generate_conversational_response(action, user_message, result)
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action in ['get_time_slots', 'get_available_timeslots']:
            # Try multiple field names for compatibility
            slots = response_body.get('available_slots') or response_body.get('timeSlots') or response_body.get('time_slots', [])
            if not slots:
                return "No available time slots found for this date."

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
            conversational = generate_conversational_response(action, user_message, result)

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
            conversational = generate_conversational_response(action, user_message, result)

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

            # Format successful appointment confirmation response
            appointment = response_body.get('appointment', {})
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
            conversational = generate_conversational_response(action, user_message, result)

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
                conversational = generate_conversational_response(action, user_message, result)
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Handle timeout status from scheduling Lambda
            if response_body.get('status') == 'timeout':
                result = {
                    "message": response_body.get('message', 'The rescheduling service is taking too long to respond. Please try again in a few minutes.'),
                    "status": "timeout",
                    "project_id": response_body.get('project_id'),
                    "action_type": "reschedule"
                }
                conversational = generate_conversational_response(action, user_message, result)
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Handle error status from scheduling Lambda
            if response_body.get('status') == 'error':
                result = {
                    "message": response_body.get('message', 'Unable to reschedule the appointment. Please try again.'),
                    "status": "error",
                    "project_id": response_body.get('project_id'),
                    "action_type": "reschedule"
                }
                conversational = generate_conversational_response(action, user_message, result)
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
                conversational = generate_conversational_response(action, user_message, result)
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Handle "awaiting_date_selection" status - reschedule workflow started, show available dates
            if response_body.get('status') == 'awaiting_date_selection':
                available_dates = response_body.get('available_dates', [])
                project_id = response_body.get('project_id', '')

                # Add weather indicators to dates if we have project location info
                if available_dates:
                    try:
                        available_dates = add_weather_indicators_to_dates(
                            available_dates,
                            response_body.get('project_category'),
                            response_body.get('project_city'),
                            response_body.get('project_state')
                        )
                    except Exception as e:
                        logger.warning(f"Failed to add weather indicators to reschedule dates: {e}")

                result = {
                    "message": f"I've initiated the rescheduling process for project #{project_id}. Here are the available dates:",
                    "project_id": project_id,
                    "available_dates": available_dates,
                    "request_id": response_body.get('request_id'),
                    "status": "awaiting_date_selection",
                    "action_type": "reschedule"
                }

                conversational = generate_conversational_response(action, user_message, result)
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Format successful reschedule confirmation response
            appointment = response_body.get('appointment', {})
            result = {
                "message": "[OK] Appointment rescheduled successfully!",
                "appointment": appointment or response_body,
                "status": "success"
            }

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result)

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
                conversational = generate_conversational_response(action, user_message, result)
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Check for "cannot cancel" status
            if response_body.get('status') in ['cannot_cancel', 'not_scheduled']:
                result = {
                    "message": response_body.get('message', 'Cannot cancel this appointment'),
                    "status": response_body.get('status'),
                    "details": response_body
                }
                conversational = generate_conversational_response(action, user_message, result)
                return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

            # Format successful cancellation confirmation response
            result = {
                "message": "[OK] Appointment cancelled successfully!",
                "details": response_body,
                "status": "success"
            }

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result)

            # Return both conversational and structured
            return f"{conversational}\n\n```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_weather':
            # Format weather data for UI rendering
            weather_data = response_body.get('weather', {})
            location_data = weather_data.get('location', {})
            current_data = weather_data.get('current', {})
            forecast_data = weather_data.get('forecast', [])

            # Build location string
            location_name = location_data.get('name', response_body.get('location', 'Unknown'))
            admin1 = location_data.get('admin1', '')
            country = location_data.get('country', '')

            if admin1 and country:
                location_str = f"{location_name}, {admin1}, {country}"
            elif admin1:
                location_str = f"{location_name}, {admin1}"
            else:
                location_str = location_name

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

            # Prepare structured data for UI
            result = {
                "location": location_str,
                "current": {
                    "temperature": current_data.get('temp_f', current_data.get('temp_F', 0)),
                    "condition": current_data.get('condition', 'Unknown'),
                    "humidity": current_data.get('humidity', 0),
                    "windSpeed": current_data.get('wind_mph', current_data.get('windspeedMiles', 0))
                },
                "forecast": formatted_forecast
            }

            # Generate conversational response using Claude
            conversational = generate_conversational_response(action, user_message, result)

            # Return both conversational and structured
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

    Designed for simple, conversational English suitable for ages 20-80.

    Args:
        user_name: User's display name (may be empty)
        projects: List of user's projects from list_projects

    Returns:
        Friendly welcome message mentioning their projects
    """
    try:
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

        system_prompt = """You are a friendly assistant for a home services company.
Write a warm welcome message following these EXACT rules:

STRICT RULES:
1. If user name is provided, ALWAYS start with "Hello, [Name]!" - NEVER skip the name
2. If no name provided, start with just "Hello!"
3. State the EXACT project count: "You have X projects" (use the actual number)
4. List project types with their statuses naturally (e.g., "a Decking installation that's ready to schedule, plus 2 Flooring projects")
5. Keep it brief: 2-4 sentences MAXIMUM
6. End with ONE simple offer: "Let me know which one you'd like to work on" or "I'm here to help"
7. NO emojis, NO multiple questions, NO jargon

EXAMPLES TO FOLLOW:

With name, multiple projects:
"Hello, John! Welcome back. You have 3 projects with us - a Decking installation that's ready to schedule, plus 2 Flooring projects. Let me know which one you'd like to work on, or just ask me anything."

With name, 1 scheduled project:
"Hello, Sarah! Welcome back. You have a Roofing project (#7751746) that's scheduled for November 26th. I'm here if you need to make changes or have questions."

With name, no projects:
"Hello, Mike! Welcome to ProjectForce. You don't have any projects set up yet. When you're ready to get started, I'm here to help."

No name, multiple projects:
"Hello! Welcome back. You have 3 projects with us - a Decking installation that's ready to schedule, plus 2 Flooring projects. Let me know which one you'd like to work on." """

        user_prompt = f"""User name: {user_name if user_name else '(none provided)'}
Total projects: {len(projects)}
Project details:
{project_data}

Write the welcome greeting following the EXACT format shown in the examples. Use the actual project count and types from the data above."""

        response = client.converse(
            modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_prompt}]
                }
            ],
            system=[{"text": system_prompt}],
            inferenceConfig={
                "maxTokens": 300,
                "temperature": 0.7,
                "topP": 0.9
            }
        )

        greeting = response['output']['message']['content'][0]['text']
        logger.info(f"[OK] Generated welcome greeting ({len(greeting)} chars)")
        return greeting.strip()

    except Exception as e:
        logger.error(f"Failed to generate welcome greeting: {e}")
        # Fallback greeting
        name_part = f", {user_name}" if user_name else ""
        if projects:
            return f"Hello{name_part}! Welcome back. You have {len(projects)} project(s) with us. Let me know how I can help you today."
        else:
            return f"Hello{name_part}! Welcome to ProjectForce. You don't have any projects set up yet. I'm here when you're ready to get started."


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
        logger.info(f"[INFO] Found {len(projects)} projects for user")

        # STORE project_ids in workflow_state for ordinal reference resolution
        # This enables "first project", "last project", "3rd project" to work correctly
        if projects:
            project_ids = [str(p.get('id', '')) for p in projects if p.get('id')]
            if project_ids:
                try:
                    from workflow_state import get_state_manager
                    state_manager = get_state_manager()
                    state_manager.save_state(session_id, {
                        'workflow_type': 'project_list',
                        'current_stage': 'projects_displayed',
                        'context': {
                            'project_ids': project_ids,
                            'project_count': len(project_ids)
                        }
                    })
                    logger.info(f"[WORKFLOW] Stored {len(project_ids)} project_ids in workflow state for ordinal refs")
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
            'performance': timing
        }

    except Exception as e:
        logger.error(f"Welcome request failed: {e}")
        # Return graceful fallback
        name_part = f", {user_name}" if user_name else ""
        return {
            'response': f"Hello{name_part}! Welcome to ProjectForce. I'm here to help with your home service projects.",
            'agent_name': 'Welcome',
            'intent': 'welcome',
            'action': 'welcome_fallback',
            'session_id': session_id,
            'direct_call': True,
            'projects': [],
            'performance': {'total': time.time() - start_time}
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

    # Map action to Lambda function
    lambda_functions = {
        # Chitchat actions
        'greet': 'pf-chitchat-actions',
        'help': 'pf-chitchat-actions',
        'general': 'pf-chitchat-actions',
        # Information actions
        'get_weather': 'pf-information-actions',
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
        'cancel_appointment': config.scheduling_lambda
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
            if key not in ['customer_id', 'client_id', 'pf_bearer_token']
        ],
        'sessionAttributes': {
            'customer_id': params.get('customer_id', ''),
            'client_id': params.get('client_id', ''),
            'pf_bearer_token': params.get('pf_bearer_token', '')
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
    channel: str = 'chat'
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
                channel=channel
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

    # Merge resolved entities with extracted params (resolved entities take precedence)
    merged_params = {**extracted_params, **resolved_entities}

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

    # INTELLIGENT ORCHESTRATION: Use Sonnet 3.5 for ALL workflow decisions
    # NO hardcoding, NO regex - pure intelligence!
    workflow_actions = [
        'schedule_project', 'confirm_appointment', 'reschedule_appointment',
        'cancel_appointment', 'add_note', 'list_notes'
    ]

    # Weather requests without explicit location need intelligent context extraction
    needs_intelligent_orchestration = (
        action in workflow_actions or
        intent == 'scheduling' or
        (action == 'get_weather' and not merged_params.get('location') and not merged_params.get('latitude'))
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
                channel=channel  # Pass channel for voice-specific handling
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
                **merged_params  # Add merged params (extracted + resolved entities)
            }

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

            # Format response for UI - conversational text + structured JSON
            formatted_response = format_lambda_response(action, response_body, message)
            logger.debug(f"Formatted response: {formatted_response[:200]}...")

            # VOICE ADAPTATION: For voice channel, extract conversational text only
            if channel == 'voice':
                # Strip JSON block and keep only conversational text
                if '```json' in formatted_response:
                    voice_response = formatted_response.split('```json')[0].strip()
                else:
                    voice_response = formatted_response
                # Apply voice formatting (natural dates, numbers, etc.)
                voice_response = format_for_voice(voice_response, intent)
                formatted_response = voice_response
                logger.info(f"[VOICE] Adapted response for voice channel ({len(formatted_response)} chars)")

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
            return {
                'response': f"I encountered an error processing your request: {str(e)}. Please try again.",
                'intent': intent,
                'action': action,
                'agent_name': 'Direct Lambda',
                'direct_call': False,
                'timing': timing
            }

    # NO BEDROCK FALLBACK - All actions should be handled by direct Lambda or workflow
    logger.warning(f"[WARNING] No handler found for: intent={intent}, action={action}, can_call_direct={can_call_direct}")

    timing['total'] = time.time() - start_time
    return {
        'response': "I'm not sure how to help with that. Please try rephrasing your request or ask for help to see what I can do.",
        'intent': intent,
        'action': action or 'unknown',
        'agent_name': 'Orchestrator',
        'direct_call': False,
        'timing': timing
    }
