"""
Multi-Agent Router (Enhanced)
Routes requests to multiple agents with parallel/sequential execution
Bypasses Supervisor for better performance
"""
import json
import logging
import time
from typing import Dict, List, Optional, Any

from config import get_config
from multi_agent_classifier import classify_multi_agent_intent
from context_resolver import resolve_context_references
from parallel_executor import execute_agents_in_parallel, execute_agents_sequentially
from result_combiner import combine_agent_results
from voice_formatter import format_response_for_channel
from classifier import classify_intent_and_action, apply_project_filters
from router import call_lambda_directly, invoke_bedrock_agent

logger = logging.getLogger()


def route_with_multi_agent_orchestration(
    message: str,
    session_id: str,
    customer_id: str,
    client_id: str,
    pf_bearer_token: str,
    conversation_history: Optional[List[Dict]] = None,
    channel: str = 'chat'
) -> Dict[str, Any]:
    """
    Enhanced routing with multi-agent orchestration

    Supports:
    - Single agent (optimized path)
    - Parallel multi-agent (simultaneous execution)
    - Sequential multi-agent (ordered execution)
    - Conditional multi-agent (decision-based)

    Args:
        message: User message
        session_id: Session identifier
        customer_id: Customer ID
        client_id: Client ID
        pf_bearer_token: API bearer token
        conversation_history: Previous conversation
        channel: Channel type ('voice' or 'chat') - determines response formatting

    Returns:
        Dictionary with response, timing, and metadata
    """
    config = get_config()
    timing = {}
    start_time = time.time()

    logger.info(f" Multi-agent routing for: '{message[:50]}...'")

    # Step 1: Resolve contextual references
    context_start = time.time()
    resolved_context = resolve_context_references(message, conversation_history)
    resolved_message = resolved_context['resolved_message']
    entities = resolved_context['entities']
    timing['context_resolution'] = time.time() - context_start

    if resolved_context['references']:
        logger.info(f" Resolved {len(resolved_context['references'])} reference(s): {resolved_message}")

    # Step 2: Classify intent with multi-agent awareness
    classification_start = time.time()
    classification = classify_multi_agent_intent(resolved_message, conversation_history)
    timing['classification'] = time.time() - classification_start

    intent = classification['intent']
    agents_needed = classification['agents_needed']
    orchestration_type = classification['orchestration_type']
    can_optimize = classification['can_optimize']

    logger.info(f" Classification: {orchestration_type} | Agents: {agents_needed} | Optimize: {can_optimize}")

    # Session attributes
    session_attributes = {
        'customer_id': customer_id,
        'client_id': client_id,
        'pf_bearer_token': pf_bearer_token,
        'channel': channel  # 'voice' or 'chat' - for response formatting
    }

    # Step 3: Route based on orchestration type
    if orchestration_type == 'single':
        # Single agent routing (existing fast path logic)
        result = _route_single_agent(
            resolved_message=resolved_message,
            original_message=message,
            intent=intent,
            can_optimize=can_optimize,
            entities=entities,
            session_id=session_id,
            session_attributes=session_attributes,
            conversation_history=conversation_history
        )

    elif orchestration_type == 'parallel':
        # Parallel multi-agent execution
        result = _route_parallel_agents(
            resolved_message=resolved_message,
            agents_needed=agents_needed,
            session_id=session_id,
            session_attributes=session_attributes,
            conversation_history=conversation_history
        )

    elif orchestration_type == 'sequential':
        # Sequential multi-agent execution
        result = _route_sequential_agents(
            resolved_message=resolved_message,
            agents_needed=agents_needed,
            session_id=session_id,
            session_attributes=session_attributes,
            conversation_history=conversation_history
        )

    elif orchestration_type == 'conditional':
        # Conditional multi-agent execution
        result = _route_conditional_agents(
            resolved_message=resolved_message,
            agents_needed=agents_needed,
            dependencies=classification.get('dependencies', {}),
            session_id=session_id,
            session_attributes=session_attributes,
            conversation_history=conversation_history
        )

    else:
        # Fallback to single agent
        logger.warning(f"Unknown orchestration type: {orchestration_type}, falling back to single agent")
        result = _route_single_agent(
            resolved_message=resolved_message,
            original_message=message,
            intent=intent,
            can_optimize=False,
            entities=entities,
            session_id=session_id,
            session_attributes=session_attributes,
            conversation_history=conversation_history
        )

    # Step 4: Format response for channel (voice or text)
    result['response'] = format_response_for_channel(
        result['response'],
        intent,
        session_attributes
    )

    # Add timing info
    result['timing']['total'] = time.time() - start_time
    result['timing'].update(timing)

    logger.info(f"  Total orchestration time: {result['timing']['total']:.2f}s")

    return result


def _route_single_agent(
    resolved_message: str,
    original_message: str,
    intent: str,
    can_optimize: bool,
    entities: Dict,
    session_id: str,
    session_attributes: Dict,
    conversation_history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Route to single agent with optional direct Lambda optimization

    This is the fast path for simple queries.
    """
    config = get_config()

    # Try direct Lambda optimization if enabled
    if config.allow_direct_lambda and can_optimize:
        # Use existing single-action classifier
        action_classification = classify_intent_and_action(resolved_message, conversation_history)
        action = action_classification.get('action')
        can_call_direct = action_classification.get('can_call_direct', False)

        if can_call_direct and action:
            logger.info(f" Fast path: Direct Lambda call for {action}")

            try:
                # Merge params: classifier first, then context entities (entities override classifier)
                classifier_params = action_classification.get('params') or {}

                # Filter out None values from classifier to allow context entities to take precedence
                classifier_params_filtered = {k: v for k, v in classifier_params.items() if v is not None}

                lambda_params = {
                    'customer_id': session_attributes['customer_id'],
                    'client_id': session_attributes['client_id'],
                    'pf_bearer_token': session_attributes['pf_bearer_token'],
                    **classifier_params_filtered,  # Include classifier params (filtered)
                    **entities  # Include resolved entities (take precedence over classifier)
                }

                lambda_response = call_lambda_directly(action, lambda_params)

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

                # POST-FILTER PROJECTS: Apply semantic filters since upstream API doesn't filter
                # lambda_params may contain status, category, projectType from classification
                if action == 'list_projects' and 'projects' in response_body and isinstance(response_body['projects'], list):
                    original_count = len(response_body['projects'])
                    response_body['projects'] = apply_project_filters(response_body['projects'], lambda_params)
                    filtered_count = len(response_body['projects'])
                    if original_count != filtered_count:
                        logger.info(f"[FILTER] Applied post-filters: {original_count} -> {filtered_count} projects (params={lambda_params})")

                formatted_response = json.dumps(response_body, separators=(',', ':'))

                return {
                    'response': formatted_response,
                    'intent': intent,
                    'action': action,
                    'agent_name': 'Direct Lambda',
                    'direct_call': True,
                    'timing': {}
                }

            except Exception as e:
                logger.error(f"Direct Lambda failed: {e}, falling back to agent")
                # Fall through to agent invocation

    # Use Bedrock agent (direct to specialist, bypassing Supervisor)
    logger.info(f" Routing to {intent} agent directly (bypassing Supervisor)")

    agent_result = invoke_bedrock_agent(
        message=resolved_message,
        session_id=session_id,
        session_attributes=session_attributes,
        conversation_history=conversation_history
    )

    return agent_result


def _route_parallel_agents(
    resolved_message: str,
    agents_needed: List[str],
    session_id: str,
    session_attributes: Dict,
    conversation_history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Execute multiple agents in parallel for faster response

    Example: "show my projects and weather"  invoke scheduling + information simultaneously
    """
    config = get_config()

    logger.info(f" Parallel execution: {len(agents_needed)} agents")

    # Build agent configs
    agent_configs = []

    for agent_name in agents_needed:
        agent_config_data = config.agents.get(agent_name)

        if not agent_config_data:
            logger.warning(f"Agent {agent_name} not found in config, skipping")
            continue

        agent_configs.append({
            'name': agent_name,
            'agent_id': agent_config_data['agent_id'],
            'alias_id': agent_config_data['alias_id'],
            'message': resolved_message  # Same message for all agents in parallel
        })

    # Execute in parallel
    results = execute_agents_in_parallel(
        agents=agent_configs,
        message=resolved_message,
        session_id=session_id,
        session_attributes=session_attributes
    )

    # Combine results
    combined = combine_agent_results(
        results=results,
        orchestration_type='parallel',
        original_message=resolved_message
    )

    return {
        'response': combined['response'],
        'intent': 'multi_agent',
        'action': None,
        'agent_name': f"Multi-Agent ({', '.join(combined['agents_used'])})",
        'direct_call': False,
        'timing': {'agent_execution': combined['timing']},
        'agents_used': combined['agents_used']
    }


def _route_sequential_agents(
    resolved_message: str,
    agents_needed: List[str],
    session_id: str,
    session_attributes: Dict,
    conversation_history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Execute agents sequentially (one after another)

    Example: "check weather then show outdoor projects"  information THEN scheduling
    """
    config = get_config()

    logger.info(f"  Sequential execution: {len(agents_needed)} agents")

    # Build agent configs
    agent_configs = []

    for agent_name in agents_needed:
        agent_config_data = config.agents.get(agent_name)

        if not agent_config_data:
            logger.warning(f"Agent {agent_name} not found in config, skipping")
            continue

        agent_configs.append({
            'name': agent_name,
            'agent_id': agent_config_data['agent_id'],
            'alias_id': agent_config_data['alias_id'],
            'message': resolved_message
        })

    # Execute sequentially
    results = execute_agents_sequentially(
        agents=agent_configs,
        message=resolved_message,
        session_id=session_id,
        session_attributes=session_attributes
    )

    # Combine results
    combined = combine_agent_results(
        results=results,
        orchestration_type='sequential',
        original_message=resolved_message
    )

    return {
        'response': combined['response'],
        'intent': 'multi_agent',
        'action': None,
        'agent_name': f"Multi-Agent Sequential ({'  '.join(combined['agents_used'])})",
        'direct_call': False,
        'timing': {'agent_execution': combined['timing']},
        'agents_used': combined['agents_used']
    }


def _route_conditional_agents(
    resolved_message: str,
    agents_needed: List[str],
    dependencies: Dict,
    session_id: str,
    session_attributes: Dict,
    conversation_history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Execute agents conditionally based on previous results

    Example: "if weather is good, schedule project"  check weather, then conditionally schedule
    """
    # For now, implement conditional as sequential with smart result checking
    # Future enhancement: Add conditional logic evaluation

    logger.info(f" Conditional execution: {len(agents_needed)} agents with dependencies")

    # Execute sequentially and let agents handle conditional logic in their prompts
    return _route_sequential_agents(
        resolved_message=resolved_message,
        agents_needed=agents_needed,
        session_id=session_id,
        session_attributes=session_attributes,
        conversation_history=conversation_history
    )
