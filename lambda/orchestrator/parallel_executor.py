"""
Parallel Agent Execution
Invokes multiple Bedrock agents simultaneously for faster responses
"""
import json
import logging
import time
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.config import Config as BotoConfig

from config import get_config

logger = logging.getLogger()


def invoke_single_agent(
    agent_name: str,
    agent_id: str,
    alias_id: str,
    message: str,
    session_id: str,
    session_attributes: Dict[str, str]
) -> Dict[str, Any]:
    """
    Invoke a single Bedrock agent

    Args:
        agent_name: Name of the agent (for logging)
        agent_id: Bedrock agent ID
        alias_id: Agent alias ID
        message: User message
        session_id: Session identifier
        session_attributes: Session attributes (credentials, context)

    Returns:
        Dictionary with:
        - agent_name: Name of agent
        - response: Agent response text
        - success: Boolean
        - error: Error message if failed
        - timing: Execution time
    """
    start_time = time.time()

    try:
        # Create Bedrock client (thread-safe)
        config = get_config()
        boto_config = BotoConfig(
            region_name=config.region,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        bedrock_client = boto3.client('bedrock-agent-runtime', config=boto_config)

        logger.info(f"🚀 Invoking {agent_name} agent ({agent_id})")

        # Invoke agent
        response = bedrock_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=f"{session_id}-{agent_name}",  # Unique session per agent
            inputText=message,
            sessionState={
                'sessionAttributes': session_attributes
            }
        )

        # Process event stream
        event_stream = response['completion']
        full_response = []

        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    full_response.append(text)

        response_text = ''.join(full_response)
        execution_time = time.time() - start_time

        logger.info(f"✅ {agent_name} completed in {execution_time:.2f}s: {response_text[:100]}...")

        return {
            'agent_name': agent_name,
            'response': response_text,
            'success': True,
            'error': None,
            'timing': execution_time
        }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"❌ {agent_name} failed after {execution_time:.2f}s: {e}")

        return {
            'agent_name': agent_name,
            'response': None,
            'success': False,
            'error': str(e),
            'timing': execution_time
        }


def execute_agents_in_parallel(
    agents: List[Dict[str, str]],
    message: str,
    session_id: str,
    session_attributes: Dict[str, str],
    max_workers: int = 3
) -> List[Dict[str, Any]]:
    """
    Execute multiple agents in parallel using ThreadPoolExecutor

    Args:
        agents: List of agent configs:
            [
                {'name': 'scheduling', 'agent_id': 'XXX', 'alias_id': 'YYY', 'message': 'show projects'},
                {'name': 'information', 'agent_id': 'ZZZ', 'alias_id': 'AAA', 'message': 'show weather'}
            ]
        message: Original user message (used if agent doesn't have custom message)
        session_id: Base session ID
        session_attributes: Session attributes
        max_workers: Maximum number of parallel threads (default: 3)

    Returns:
        List of agent results (same structure as invoke_single_agent)

    Example:
        >>> agents = [
        ...     {'name': 'scheduling', 'agent_id': 'A', 'alias_id': 'X', 'message': 'show projects'},
        ...     {'name': 'information', 'agent_id': 'B', 'alias_id': 'Y', 'message': 'show weather'}
        ... ]
        >>> results = execute_agents_in_parallel(agents, "original message", "session-123", {})
        >>> len(results)
        2
        >>> all(r['success'] for r in results)
        True
    """
    start_time = time.time()

    logger.info(f"⚡ Executing {len(agents)} agents in PARALLEL (max_workers={max_workers})")

    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all agent invocations
        future_to_agent = {}

        for agent_config in agents:
            agent_name = agent_config['name']
            agent_id = agent_config['agent_id']
            alias_id = agent_config['alias_id']
            agent_message = agent_config.get('message', message)  # Use custom message or fallback to original

            future = executor.submit(
                invoke_single_agent,
                agent_name=agent_name,
                agent_id=agent_id,
                alias_id=alias_id,
                message=agent_message,
                session_id=session_id,
                session_attributes=session_attributes
            )

            future_to_agent[future] = agent_name

        # Collect results as they complete
        for future in as_completed(future_to_agent):
            agent_name = future_to_agent[future]
            try:
                result = future.result()
                results.append(result)
                logger.debug(f"✅ Collected result from {agent_name}")
            except Exception as e:
                logger.error(f"❌ Exception collecting result from {agent_name}: {e}")
                results.append({
                    'agent_name': agent_name,
                    'response': None,
                    'success': False,
                    'error': str(e),
                    'timing': 0
                })

    total_time = time.time() - start_time
    successful_count = sum(1 for r in results if r['success'])

    logger.info(f"⏱️  Parallel execution complete: {successful_count}/{len(agents)} succeeded in {total_time:.2f}s")

    # Sort results by original agent order for consistency
    agent_names = [a['name'] for a in agents]
    results.sort(key=lambda r: agent_names.index(r['agent_name']) if r['agent_name'] in agent_names else 999)

    return results


def execute_agents_sequentially(
    agents: List[Dict[str, str]],
    message: str,
    session_id: str,
    session_attributes: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Execute multiple agents sequentially (one after another)

    This is used when agent outputs need to feed into subsequent agents.

    Args:
        agents: List of agent configs (same format as parallel execution)
        message: Original user message
        session_id: Base session ID
        session_attributes: Session attributes

    Returns:
        List of agent results in execution order

    Example:
        >>> agents = [
        ...     {'name': 'information', 'agent_id': 'A', 'alias_id': 'X', 'message': 'check weather'},
        ...     {'name': 'scheduling', 'agent_id': 'B', 'alias_id': 'Y', 'message': 'schedule if good'}
        ... ]
        >>> results = execute_agents_sequentially(agents, "message", "session-123", {})
    """
    start_time = time.time()

    logger.info(f"⏭️  Executing {len(agents)} agents SEQUENTIALLY")

    results = []

    for i, agent_config in enumerate(agents):
        agent_name = agent_config['name']
        agent_id = agent_config['agent_id']
        alias_id = agent_config['alias_id']

        # For subsequent agents, optionally incorporate previous agent's response
        agent_message = agent_config.get('message', message)

        # If this is not the first agent, add context from previous agent
        if i > 0 and results[-1]['success']:
            previous_result = results[-1]
            agent_message = f"""Previous agent ({previous_result['agent_name']}) responded:
{previous_result['response']}

Now handle this: {agent_message}"""

        logger.info(f"🔄 Step {i+1}/{len(agents)}: Invoking {agent_name}")

        result = invoke_single_agent(
            agent_name=agent_name,
            agent_id=agent_id,
            alias_id=alias_id,
            message=agent_message,
            session_id=session_id,
            session_attributes=session_attributes
        )

        results.append(result)

        # If agent failed and it's critical, stop execution
        if not result['success']:
            logger.warning(f"⚠️  {agent_name} failed, stopping sequential execution")
            break

    total_time = time.time() - start_time
    successful_count = sum(1 for r in results if r['success'])

    logger.info(f"⏱️  Sequential execution complete: {successful_count}/{len(agents)} succeeded in {total_time:.2f}s")

    return results
