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

            lines = [f"Found {len(projects)} project(s):\n"]
            for i, project in enumerate(projects, 1):
                status = project.get('status', 'Unknown')
                category = project.get('category', 'Not specified')
                project_type = project.get('projectType', 'Not specified')
                scheduled_date = project.get('scheduledDate', 'Not scheduled')
                address = project.get('address', {})
                full_address = address.get('fullAddress', 'No address')

                lines.append(f"{i}. Project {project.get('id', 'Unknown')}")
                lines.append(f"   Status: {status}")
                lines.append(f"   Category: {category}")
                lines.append(f"   Type: {project_type}")
                lines.append(f"   Scheduled: {scheduled_date}")
                lines.append(f"   Address: {full_address}")

                tech = project.get('technician', {})
                if tech and tech.get('name'):
                    lines.append(f"   Technician: {tech.get('name')} (#{tech.get('id', 'N/A')})")
                lines.append("")  # Empty line between projects

            return "\n".join(lines)

        elif action == 'get_project_details':
            project = response_body.get('project', {})
            if not project:
                return "Project details not found."

            lines = [f"Details for Project {project.get('id', 'Unknown')}:\n"]
            lines.append(f"Status: {project.get('status', 'Unknown')}")
            lines.append(f"Category: {project.get('category', 'Not specified')}")
            lines.append(f"Project Type: {project.get('projectType', 'Not specified')}")
            lines.append(f"Scheduled Date: {project.get('scheduledDate', 'Not scheduled')}")

            address = project.get('address', {})
            if address.get('fullAddress'):
                lines.append(f"Address: {address['fullAddress']}")

            tech = project.get('technician', {})
            if tech and tech.get('name'):
                lines.append(f"Technician: {tech.get('name')} (#{tech.get('id', 'N/A')})")

            customer = project.get('customer', {})
            if customer and customer.get('name'):
                lines.append(f"Customer: {customer.get('name')}")
                if customer.get('email'):
                    lines.append(f"Email: {customer.get('email')}")
                if customer.get('phone'):
                    lines.append(f"Phone: {customer.get('phone')}")

            return "\n".join(lines)

        elif action == 'get_available_dates':
            dates = response_body.get('available_dates', [])
            if not dates:
                return "No available dates found for this project."

            lines = ["Available dates:\n"]
            for date in dates:
                lines.append(f"- {date}")

            return "\n".join(lines)

        elif action in ['get_time_slots', 'get_available_timeslots']:
            slots = response_body.get('time_slots', [])
            if not slots:
                return "No available time slots found for this date."

            lines = ["Available time slots:\n"]
            for slot in slots:
                lines.append(f"- {slot}")

            return "\n".join(lines)

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
        'list_projects': config.scheduling_lambda,
        'get_project_details': config.scheduling_lambda,
        'get_available_dates': config.scheduling_lambda,
        'get_time_slots': config.scheduling_lambda,
        'get_available_timeslots': config.scheduling_lambda  # Alias for get_time_slots
    }

    function_name = lambda_functions.get(action)
    if not function_name:
        raise ValueError(f"Unknown action: {action}")

    # Construct Lambda event (Bedrock agent format)
    event = {
        'actionGroup': 'scheduling-actions',
        'function': action,
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


def invoke_bedrock_agent(
    message: str,
    session_id: str,
    session_attributes: Dict[str, str],
    conversation_history: Optional[list] = None
) -> Dict[str, Any]:
    """
    Invoke Bedrock agent (Supervisor or direct agent routing)

    Args:
        message: User message
        session_id: Session identifier
        session_attributes: Session attributes (customer_id, client_id, tokens, etc.)
        conversation_history: Previous conversation for context

    Returns:
        Dictionary with:
        - response: Agent response text
        - agent_name: Name of agent invoked
        - intent: Classified intent
        - timing: Performance metrics
    """
    config = get_config()
    bedrock_client = get_bedrock_agent_client()

    timing = {}
    start_time = time.time()

    # Classify intent
    classification = classify_intent_and_action(message, conversation_history)
    intent = classification.get('intent', 'chitchat')
    timing['classification'] = time.time() - start_time

    logger.info(f"Intent classified as: {intent}")

    # Determine which agent to invoke
    if config.use_supervisor:
        # Use Supervisor agent
        agent_id = config.supervisor_agent_id
        alias_id = config.supervisor_alias_id
        agent_name = "Supervisor Agent"
        logger.info(f"Routing via SUPERVISOR: {agent_id} (Alias: {alias_id})")
    else:
        # Direct routing to intent-specific agent
        agents = config.agents
        agent_config = agents.get(intent, agents.get('chitchat'))
        agent_id = agent_config['agent_id']
        alias_id = agent_config['alias_id']
        agent_name = f"{intent.capitalize()} Agent"
        logger.info(f"Routing to {intent.upper()} agent: {agent_id} (bypassing Supervisor)")

    # Enhance session attributes with context
    enhanced_attributes = dict(session_attributes)

    # For Information Agent: Extract location from conversation history if available
    if intent == 'information' and 'weather' in message.lower():
        location = extract_location_from_history(conversation_history or [])
        if location:
            logger.info(f"📍 Extracted location from history: {location}")
            enhanced_attributes['inferred_location'] = location

    # Build conversation context and enhance the message
    context_summary = build_conversation_context(conversation_history)
    enhanced_message = message

    if context_summary:
        # Prepend conversation context to help agent understand references
        enhanced_message = f"""<conversation_history>
{context_summary}
</conversation_history>

<current_message>
{message}
</current_message>"""
        logger.info(f"📝 Added conversation context ({len(conversation_history or [])} messages) to agent prompt")

    # PRONOUN RESOLUTION: Detect and resolve pronouns like "it", "that", "this"
    pronoun_ref = extract_pronoun_reference(message, conversation_history or [])
    if pronoun_ref:
        project_id = pronoun_ref.get('project_id')
        project_info = pronoun_ref.get('project_info', {})

        # Add explicit pronoun resolution to the message
        resolution_context = f"\n\n<pronoun_resolution>\nThe user's pronoun refers to Project {project_id}"

        if project_info:
            # Add key project details to help agent understand context
            status = project_info.get('status', 'Unknown')
            category = project_info.get('category', '')
            scheduled_date = project_info.get('scheduledDate', '')

            resolution_context += f"\nProject Details:"
            resolution_context += f"\n- Status: {status}"
            if category:
                resolution_context += f"\n- Category: {category}"
            if scheduled_date:
                resolution_context += f"\n- Scheduled: {scheduled_date}"

        resolution_context += "\n</pronoun_resolution>"

        enhanced_message += resolution_context
        logger.info(f"🔗 Resolved pronoun to project {project_id}")

        # Also add to session attributes for Lambda calls
        enhanced_attributes['resolved_project_id'] = project_id

    # Invoke the selected agent
    invoke_start = time.time()
    response = bedrock_client.invoke_agent(
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        inputText=enhanced_message,
        sessionState={
            'sessionAttributes': enhanced_attributes
        }
    )
    timing['bedrock_invoke'] = time.time() - invoke_start

    # Process event stream
    event_stream = response['completion']
    stream_start = time.time()

    full_response = []
    for event in event_stream:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                text = chunk['bytes'].decode('utf-8')
                full_response.append(text)

    timing['stream_processing'] = time.time() - stream_start
    timing['total'] = time.time() - start_time

    response_text = ''.join(full_response)

    logger.info(f"⏱️  Agent Performance: Total={timing['total']:.2f}s | "
                f"Invoke={timing['bedrock_invoke']:.2f}s | "
                f"Stream={timing['stream_processing']:.2f}s | "
                f"Classification={timing['classification']:.3f}s")
    logger.info(f"📝 Agent response (first 100 chars): {response_text[:100]}...")

    # FORMATTING FIX: Check if agent returned raw JSON and format it
    formatted_response = response_text
    try:
        # Try to parse as JSON
        if response_text.strip().startswith('{') and '"action"' in response_text:
            response_data = json.loads(response_text)
            action_name = response_data.get('action')

            # Format using the same function as Direct Lambda
            if action_name:
                formatted_response = format_lambda_response(action_name, response_data)
                logger.info(f"✅ Formatted agent JSON response for action: {action_name}")
    except (json.JSONDecodeError, KeyError) as e:
        # Not JSON or formatting failed - use original response
        logger.debug(f"Agent response not JSON or formatting failed: {e}")
        formatted_response = response_text

    return {
        'response': formatted_response,
        'agent_name': agent_name,
        'intent': intent,
        'timing': timing,
        'direct_call': False
    }


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

    # OPTIMIZATION: Call Lambda directly for simple data retrieval
    if config.allow_direct_lambda and can_call_direct and action:
        logger.info(f"⚡ DIRECT LAMBDA CALL: {action} (bypassing agent)")

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
            logger.error(f"Direct Lambda call failed: {e}, falling back to agent")
            # Fall through to agent invocation below

    # FALLBACK: Use Bedrock agent for complex queries or if direct call fails
    logger.info(f"Routing to Bedrock agent (reason: can_call_direct={can_call_direct}, action={action})")

    # Use resolved message for agent (with context already resolved)
    agent_result = invoke_bedrock_agent(
        message=resolved_message,
        session_id=session_id,
        session_attributes=session_attributes,
        conversation_history=conversation_history
    )

    # Merge classification timing with agent timing
    agent_result['timing']['classification'] = timing['classification']

    return agent_result
