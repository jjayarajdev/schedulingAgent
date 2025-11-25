"""
Intelligent Workflow Orchestrator
Uses Sonnet 3.7 for ALL decision-making - NO HARDCODING, NO REGEX

Sonnet 3.7 handles:
- Intent understanding
- Context retention across turns
- Entity extraction from natural language
- Workflow stage detection
- Next action decisions
- Response generation

ZERO hardcoded state machines or regex patterns!
"""
import json
import logging
import time
import boto3
from typing import Dict, Any, List, Optional
from botocore.config import Config as BotoConfig

from config import get_config
from workflow_state import get_state_manager
from router import call_lambda_directly, format_lambda_response
from weather_aware_scheduling import (
    is_outdoor_project,
    find_forecast_for_date,
    analyze_weather_suitability,
    extract_location_from_context
)

logger = logging.getLogger()

# Bedrock runtime client singleton
_bedrock_runtime = None


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
        workflow_context = f"""

Current workflow state:
- Type: {current_workflow_state.get('workflow_type', 'none')}
- Stage: {current_workflow_state.get('current_stage', 'start')}
- Context: {json.dumps(current_workflow_state.get('context', {}), indent=2)}
- Summary: {current_workflow_state.get('conversation_summary', 'No summary')}
"""

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
Scheduling: list_projects, get_project_details, get_available_dates, get_time_slots, confirm_appointment, reschedule_appointment, cancel_appointment
Information: get_weather
Chitchat: greet, help, general

IMPORTANT RULES:
1. Extract ALL entities from the message AND conversation history
2. If user says "it", "that", "the last one" - look back and find what they're referring to
3. Handle ordinal references: "last project" = most recent in list, "first project" = first in list, "second project" = 2nd in list, etc.
4. If user provides a date/time, extract it even if implicit (e.g., "tomorrow", "2pm")
5. If in an active workflow, determine what stage we're at
6. Be intelligent about corrections: "actually, make it the 28th" means update the date
7. For weather queries without explicit location, extract city/state from recent project addresses in conversation
8. For list_projects with status filter: if user says "scheduled projects", "new projects", etc., extract status entity

Examples:

Scheduling:
{{
    "intent": "scheduling",
    "action": "get_time_slots",
    "entities": {{"project_id": "7751748", "date": "2025-11-27"}},
    "workflow_type": "schedule_appointment",
    "reasoning": "User selected Nov 27 from available dates."
}}

Ordinal reference to project:
{{
    "intent": "scheduling",
    "action": "get_project_details",
    "entities": {{"project_id": "7751748"}},
    "reasoning": "User said 'details for the last project'. Looking at conversation, the last project mentioned in the list was #7751748."
}}

Weather (with context extraction):
{{
    "intent": "information",
    "action": "get_weather",
    "entities": {{"location": "Minneapolis, MN"}},
    "reasoning": "User asked about weather. Recent project details showed address in Minneapolis, MN."
}}

Respond ONLY with valid JSON."""

    response_text = call_sonnet(prompt, max_tokens=800)

    try:
        # Parse JSON response
        classification = json.loads(response_text)
        logger.info(f"🧠 Sonnet classification: {classification}")
        return classification

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Sonnet response as JSON: {response_text}")
        # Fallback
        return {
            "intent": "chitchat",
            "action": "general",
            "entities": {},
            "workflow_type": None,
            "reasoning": "Failed to parse response"
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
        workflow_context = f"""

Active workflow:
- Type: {workflow_state.get('workflow_type')}
- Stage: {workflow_state.get('current_stage')}
- Collected context: {json.dumps(workflow_state.get('context', {}), indent=2)}
"""

    prompt = f"""You are an intelligent workflow orchestrator. Decide what action to take next.

Previous conversation:
{conversation_context}
{workflow_context}

Classification result:
{json.dumps(classification, indent=2)}

User's message: "{message}"

Determine the next step:

1. Do we have everything needed to call a Lambda function?
   - For get_available_dates: need project_id (returns dates + request_id)
   - For get_time_slots: need project_id + date + request_id (request_id comes from get_available_dates)
   - For confirm_appointment: need project_id + date + time + request_id
   - For list_projects: just need customer_id (already available), optional: status filter if user specified (e.g., "Scheduled", "New", "Customer Scheduled", "Ready To Schedule", "Awaiting Confirmation", "Pending Signature")
   - For get_weather: need location as "City, State" format (e.g., "Minneapolis, MN") - combine city and state from entities

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

User asks "what is the weather like" (after viewing project in Minneapolis):
{{
    "should_call_lambda": true,
    "lambda_action": "get_weather",
    "lambda_params": {{
        "location": "Minneapolis, MN"  // Combine city and state - do NOT pass city/state/address/zipcode separately
    }}
}}

Respond ONLY with valid JSON."""

    response_text = call_sonnet(prompt, max_tokens=1000)

    try:
        decision = json.loads(response_text)
        logger.info(f"🎯 Sonnet decision: call_lambda={decision.get('should_call_lambda')}, action={decision.get('lambda_action')}")
        return decision

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Sonnet decision: {response_text}")
        # Fallback
        return {
            "should_call_lambda": False,
            "response_to_user": "I'm having trouble understanding. Could you rephrase that?",
            "workflow_complete": False
        }


def orchestrate_intelligent_workflow(
    message: str,
    session_id: str,
    customer_id: str,
    client_id: str,
    pf_bearer_token: str,
    conversation_history: List[Dict]
) -> Dict[str, Any]:
    """
    Main intelligent orchestration function
    Uses Sonnet 3.7 for ALL decisions - NO hardcoding!

    Args:
        message: User's message
        session_id: Session ID
        customer_id: Customer ID
        client_id: Client ID
        pf_bearer_token: ProjectForce API token
        conversation_history: Previous messages

    Returns:
        Response dictionary with text, intent, action, timing
    """
    timing = {}
    start_time = time.time()

    state_manager = get_state_manager()

    # Load current workflow state (if any)
    workflow_state = state_manager.get_state(session_id)

    # Step 1: Intelligent classification using Sonnet 3.7
    logger.info("🧠 Step 1: Intelligent classification with Sonnet 3.7")
    classification_start = time.time()

    classification = intelligent_classify(
        message,
        conversation_history,
        workflow_state
    )

    timing['classification'] = time.time() - classification_start

    # Step 2: Intelligent decision using Sonnet 3.7
    logger.info("🎯 Step 2: Intelligent decision-making with Sonnet 3.7")
    decision_start = time.time()

    decision = intelligent_decide_next_action(
        message,
        classification,
        workflow_state,
        conversation_history
    )

    timing['decision'] = time.time() - decision_start

    # Step 3: Execute decision
    if decision.get('should_call_lambda'):
        # Call Lambda function
        lambda_action = decision['lambda_action']
        lambda_params = decision['lambda_params']

        # Add auth params
        lambda_params.update({
            'customer_id': customer_id,
            'client_id': client_id,
            'pf_bearer_token': pf_bearer_token
        })

        logger.info(f"⚡ Calling Lambda: {lambda_action} with params: {lambda_params}")
        lambda_start = time.time()

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

            # WEATHER-AWARE SCHEDULING: Check weather for outdoor projects when showing time slots
            if lambda_action in ['get_time_slots', 'get_available_timeslots']:
                # Get project category from workflow state
                project_category = workflow_state.get('context', {}).get('category') if workflow_state else None

                if project_category and is_outdoor_project(project_category):
                    logger.info(f"🌤️  Outdoor project detected ({project_category}), checking weather...")

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

                            logger.info(f"🌤️  Fetching weather for {location} on {target_date}")
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

                            # Find forecast for target date
                            forecast = find_forecast_for_date(weather_body, target_date)

                            if forecast:
                                # Analyze weather suitability
                                assessment = analyze_weather_suitability(
                                    forecast,
                                    project_category,
                                    target_date
                                )

                                if not assessment['suitable']:
                                    # Inject weather warning into response
                                    logger.info(f"⚠️  Weather warning: {assessment['severity']} - {', '.join(assessment['warnings'])}")
                                    response_body['weather_warning'] = assessment
                                else:
                                    logger.info(f"✅ Weather looks good for {project_category}")

                        except Exception as weather_error:
                            logger.warning(f"Weather check failed (non-fatal): {weather_error}")
                            # Continue without weather warning - don't block the flow
                    else:
                        logger.warning(f"No location found in workflow state for weather check")

            # Format response for user (with conversational wrapper from Claude)
            formatted_response = format_lambda_response(lambda_action, response_body, message)

            response_text = formatted_response

            # CRITICAL: Extract request_id from Lambda response and add to workflow state
            # request_id is required for get_time_slots and confirm_appointment
            if 'request_id' in response_body and response_body['request_id']:
                logger.info(f"📌 Extracted request_id from Lambda response: {response_body['request_id']}")

                # Add request_id to Sonnet's workflow state update
                if decision.get('update_workflow_state'):
                    if 'context' not in decision['update_workflow_state']:
                        decision['update_workflow_state']['context'] = {}
                    decision['update_workflow_state']['context']['request_id'] = response_body['request_id']
                    logger.info(f"📌 Added request_id to workflow state context")

        except Exception as e:
            logger.error(f"Lambda call failed: {e}")
            response_text = f"I encountered an error: {str(e)}. Please try again."

    else:
        # Use Sonnet's direct response
        response_text = decision.get('response_to_user', "How can I help you?")

    # Step 4: Update workflow state
    if decision.get('update_workflow_state'):
        new_state = decision['update_workflow_state']
        state_manager.save_state(session_id, new_state)

    # Step 5: Clear workflow if complete
    if decision.get('workflow_complete'):
        state_manager.clear_state(session_id)
        logger.info("✅ Workflow complete, state cleared")

    timing['total'] = time.time() - start_time

    logger.info(f"⏱️  Intelligent Orchestration: Total={timing['total']:.2f}s | Classification={timing.get('classification', 0):.2f}s | Decision={timing.get('decision', 0):.2f}s")

    return {
        'response': response_text,
        'intent': classification.get('intent', 'unknown'),
        'action': decision.get('lambda_action') or classification.get('action'),
        'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
        'direct_call': True,
        'timing': timing
    }
