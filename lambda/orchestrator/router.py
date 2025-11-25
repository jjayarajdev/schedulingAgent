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


def format_lambda_response(action: str, response_body: Dict[str, Any]) -> str:
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
                return "You have no projects matching your criteria."

            # Return JSON for UI to render as a table
            result = {
                "message": f"Found {len(projects)} project(s):",
                "projects": projects
            }
            return f"```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_project_details':
            project = response_body.get('project', {})
            if not project:
                return "Project details not found."

            # Return JSON for UI to render as a detailed card
            result = {
                "message": f"Project #{project.get('id', 'Unknown')} Details",
                "project": project
            }
            return f"```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_available_dates':
            dates = response_body.get('available_dates', [])
            if not dates:
                return "No available dates found for this project."

            # Format dates for UI rendering
            from datetime import datetime
            formatted_dates = []
            for date_str in dates:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    formatted_dates.append({
                        "date": date_str,
                        "dayShort": date_obj.strftime("%a"),  # Mon, Tue
                        "monthDay": date_obj.strftime("%b %d"),  # Nov 25
                        "dayName": date_obj.strftime("%A")  # Monday
                    })
                except:
                    formatted_dates.append({"date": date_str, "monthDay": date_str})

            # Return JSON for UI to render as date cards
            result = {
                "message": "Available dates for scheduling:",
                "dates": formatted_dates,
                "dateCount": len(formatted_dates)
            }
            return f"```json\n{json.dumps(result, indent=2)}\n```"

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

            # Return JSON for UI to render as time slot cards
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
            return f"```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'get_business_hours':
            working_days = response_body.get('working_days', [])
            non_working_days = response_body.get('non_working_days', [])

            if not working_days:
                return "Business hours not configured."

            lines = ["Business Hours:\n"]
            for day_info in working_days:
                lines.append(f"- {day_info['day']}: {day_info['start']} - {day_info['end']}")

            if non_working_days:
                lines.append(f"\nClosed: {', '.join(non_working_days)}")

            return "\n".join(lines)

        elif action in ['greet', 'help', 'general']:
            # Chitchat actions - return message directly
            return response_body.get('message', "Hello! How can I help you today?")

        elif action == 'confirm_appointment':
            # Check for errors first
            if 'error' in response_body:
                error_message = response_body['error']
                result = {
                    "message": f"❌ Failed to confirm appointment: {error_message}",
                    "status": "error",
                    "details": response_body
                }
                return f"```json\n{json.dumps(result, indent=2)}\n```"

            # Format successful appointment confirmation response
            appointment = response_body.get('appointment', {})
            if not appointment and response_body.get('success'):
                # Handle simplified success response
                result_data = {
                    'message': 'Appointment confirmed successfully!',
                    'status': 'confirmed',
                    'details': response_body
                }
                return f"```json\n{json.dumps(result_data, indent=2)}\n```"

            result = {
                "message": "✅ Appointment confirmed!",
                "appointment": appointment or response_body,
                "status": "confirmed"
            }
            return f"```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'reschedule_appointment':
            # Check for errors first
            if 'error' in response_body:
                error_message = response_body['error']
                result = {
                    "message": f"❌ Failed to reschedule appointment: {error_message}",
                    "status": "error",
                    "details": response_body
                }
                return f"```json\n{json.dumps(result, indent=2)}\n```"

            # Format successful reschedule confirmation response
            appointment = response_body.get('appointment', {})
            result = {
                "message": "✅ Appointment rescheduled successfully!",
                "appointment": appointment or response_body,
                "status": "success"
            }
            return f"```json\n{json.dumps(result, indent=2)}\n```"

        elif action == 'cancel_appointment':
            # Check for errors first
            if 'error' in response_body:
                error_message = response_body['error']
                result = {
                    "message": f"❌ Failed to cancel appointment: {error_message}",
                    "status": "error",
                    "details": response_body
                }
                return f"```json\n{json.dumps(result, indent=2)}\n```"

            # Format successful cancellation confirmation response
            result = {
                "message": "✅ Appointment cancelled successfully!",
                "details": response_body,
                "status": "success"
            }
            return f"```json\n{json.dumps(result, indent=2)}\n```"

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

            # Return JSON for UI to render as weather card
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
            return f"```json\n{json.dumps(result, indent=2)}\n```"

        else:
            # Fallback: return JSON for unknown actions
            return json.dumps(response_body, indent=2)

    except Exception as e:
        logger.error(f"Error formatting Lambda response: {e}")
        # Fallback to JSON if formatting fails
        return json.dumps(response_body, indent=2)


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

    logger.info(f"⚡ Calling Lambda directly: {function_name}.{action}")
    logger.debug(f"Lambda event: {json.dumps(event, indent=2)}")

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
    pf_bearer_token: str,
    conversation_history: Optional[list] = None
) -> Dict[str, Any]:
    """
    Route request to either Direct Lambda or Bedrock Agent
    Uses multi-agent orchestration when enabled

    Args:
        message: User message
        session_id: Session identifier
        customer_id: Customer ID
        client_id: Client ID
        pf_bearer_token: ProjectForce API bearer token
        conversation_history: Previous conversation for context

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
        logger.info("🎯 Using multi-agent orchestration")

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
    logger.info("📍 Using standard routing")

    timing = {}
    start_time = time.time()

    # CONTEXT RESOLUTION: Resolve references like "last project", "it", "that" BEFORE classification
    resolved_context = resolve_context_references(message, conversation_history)
    resolved_message = resolved_context['resolved_message']
    resolved_entities = resolved_context['entities']

    # Log context resolution
    if resolved_message != message:
        logger.info(f"🔗 Context resolved: '{message}' → '{resolved_message}'")
    if resolved_entities:
        logger.info(f"📎 Resolved entities: {resolved_entities}")

    # Use resolved message for classification
    classification = classify_intent_and_action(resolved_message, conversation_history)
    intent = classification.get('intent', 'chitchat')
    action = classification.get('action')
    can_call_direct = classification.get('can_call_direct', False)
    extracted_params = classification.get('params') or {}

    # Merge resolved entities with extracted params (resolved entities take precedence)
    merged_params = {**extracted_params, **resolved_entities}

    timing['classification'] = time.time() - start_time

    logger.info(f"📋 Classification: intent={intent}, action={action}, can_call_direct={can_call_direct}")
    logger.info(f"📋 Extracted params: {extracted_params}")
    if resolved_entities:
        logger.info(f"📋 Merged params (with resolved entities): {merged_params}")

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
        logger.info(f"🧠 INTELLIGENT ORCHESTRATION: Using Sonnet 3.7 for workflow decisions")

        try:
            from intelligent_orchestrator import orchestrate_intelligent_workflow

            intelligent_result = orchestrate_intelligent_workflow(
                message=resolved_message,
                session_id=session_id,
                customer_id=customer_id,
                client_id=client_id,
                pf_bearer_token=pf_bearer_token,
                conversation_history=conversation_history
            )

            return intelligent_result

        except Exception as e:
            logger.error(f"Intelligent orchestration failed: {e}")
            # Fall through to direct Lambda call below

    # OPTIMIZATION: Call Lambda directly for simple data retrieval
    if config.allow_direct_lambda and can_call_direct and action:
        logger.info(f"⚡ DIRECT LAMBDA CALL: {action} (bypassing Bedrock)")

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

            # Format response for UI - convert JSON to human-readable text
            formatted_response = format_lambda_response(action, response_body)
            logger.debug(f"Formatted response: {formatted_response[:200]}...")

            logger.info(f"⏱️  Direct Lambda Performance: Total={timing['total']:.2f}s | "
                        f"Lambda={timing['lambda_direct']:.2f}s | "
                        f"Classification={timing['classification']:.3f}s")

            return {
                'response': formatted_response,
                'intent': intent,
                'action': action,
                'agent_name': 'Direct Lambda',
                'direct_call': True,
                'timing': timing
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
    logger.warning(f"⚠️ No handler found for: intent={intent}, action={action}, can_call_direct={can_call_direct}")

    timing['total'] = time.time() - start_time
    return {
        'response': "I'm not sure how to help with that. Please try rephrasing your request or ask for help to see what I can do.",
        'intent': intent,
        'action': action or 'unknown',
        'agent_name': 'Orchestrator',
        'direct_call': False,
        'timing': timing
    }
