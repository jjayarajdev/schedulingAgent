"""
Multi-Agent Result Combiner
Combines responses from multiple agents into coherent output
"""
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger()


def combine_agent_results(
    results: List[Dict[str, Any]],
    orchestration_type: str,
    original_message: str
) -> Dict[str, Any]:
    """
    Combine results from multiple agents into a single coherent response

    Args:
        results: List of agent results from parallel/sequential execution
        orchestration_type: Type of orchestration (parallel, sequential, conditional)
        original_message: Original user message for context

    Returns:
        Dictionary with:
        - response: Combined response text
        - agents_used: List of agent names
        - success: Overall success boolean
        - timing: Combined timing information
        - errors: List of errors if any

    Example:
        >>> results = [
        ...     {'agent_name': 'scheduling', 'response': 'You have 8 projects', 'success': True},
        ...     {'agent_name': 'information', 'response': 'Weather is sunny, 75F', 'success': True}
        ... ]
        >>> combined = combine_agent_results(results, 'parallel', 'show projects and weather')
        >>> 'projects' in combined['response'] and 'Weather' in combined['response']
        True
    """
    successful_results = [r for r in results if r['success']]
    failed_results = [r for r in results if not r['success']]

    # Calculate total timing
    total_timing = sum(r.get('timing', 0) for r in results)
    agents_used = [r['agent_name'] for r in results]

    logger.info(f"Combining {len(successful_results)}/{len(results)} successful agent results")

    # If all agents failed
    if len(successful_results) == 0:
        error_messages = [f"{r['agent_name']}: {r['error']}" for r in failed_results]
        return {
            'response': f"I apologize, but I encountered errors processing your request. Please try again.",
            'agents_used': agents_used,
            'success': False,
            'timing': total_timing,
            'errors': error_messages
        }

    # If partial success (some agents failed)
    if len(failed_results) > 0:
        logger.warning(f"{len(failed_results)} agent(s) failed: {[r['agent_name'] for r in failed_results]}")

    # Combine responses based on orchestration type
    if orchestration_type == 'parallel':
        combined_response = _combine_parallel_results(successful_results, original_message)
    elif orchestration_type == 'sequential':
        combined_response = _combine_sequential_results(successful_results, original_message)
    elif orchestration_type == 'conditional':
        combined_response = _combine_conditional_results(successful_results, original_message)
    else:
        # Single agent or unknown - just return first result
        combined_response = successful_results[0]['response'] if successful_results else ""

    # Add warnings for failed agents if any
    if len(failed_results) > 0:
        failed_names = [r['agent_name'] for r in failed_results]
        combined_response += f"\n\n(Note: Could not retrieve information from {', '.join(failed_names)})"

    return {
        'response': combined_response,
        'agents_used': agents_used,
        'success': len(successful_results) > 0,
        'timing': total_timing,
        'errors': [f"{r['agent_name']}: {r['error']}" for r in failed_results] if failed_results else []
    }


def _combine_parallel_results(results: List[Dict[str, Any]], original_message: str) -> str:
    """
    Combine results from parallel execution

    For parallel queries like "show my projects and weather",
    we want to present both results clearly.

    Args:
        results: List of successful agent results
        original_message: Original user message

    Returns:
        Combined response string
    """
    if len(results) == 1:
        return results[0]['response']

    # Build a coherent narrative combining multiple results
    combined_parts = []

    for i, result in enumerate(results):
        agent_name = result['agent_name']
        response = result['response']

        # Clean up agent response (remove any agent-specific prefixes)
        response = response.strip()

        # Add section header for clarity
        if agent_name == 'scheduling':
            combined_parts.append(f"**Your Projects:**\n{response}")
        elif agent_name == 'information':
            combined_parts.append(f"**Weather Information:**\n{response}")
        elif agent_name == 'chitchat':
            combined_parts.append(response)
        else:
            combined_parts.append(f"**{agent_name.capitalize()}:**\n{response}")

    # Join with double newline for readability
    return "\n\n".join(combined_parts)


def _combine_sequential_results(results: List[Dict[str, Any]], original_message: str) -> str:
    """
    Combine results from sequential execution

    For sequential queries like "check weather then schedule",
    we want to show the flow of operations.

    Args:
        results: List of successful agent results in execution order
        original_message: Original user message

    Returns:
        Combined response string
    """
    if len(results) == 1:
        return results[0]['response']

    # For sequential, the last agent's response is usually the most important
    # But we want to acknowledge previous steps

    combined_parts = []

    for i, result in enumerate(results):
        agent_name = result['agent_name']
        response = result['response'].strip()

        if i < len(results) - 1:
            # Intermediate steps - show briefly
            combined_parts.append(f"Step {i+1} ({agent_name}): {response[:200]}...")
        else:
            # Final step - show full response
            combined_parts.append(f"**Result:**\n{response}")

    return "\n\n".join(combined_parts)


def _combine_conditional_results(results: List[Dict[str, Any]], original_message: str) -> str:
    """
    Combine results from conditional execution

    For conditional queries like "if weather is good, schedule project",
    we want to show decision logic.

    Args:
        results: List of successful agent results
        original_message: Original user message

    Returns:
        Combined response string
    """
    if len(results) == 1:
        return results[0]['response']

    # Similar to sequential, but emphasize the conditional nature
    combined_parts = []

    for i, result in enumerate(results):
        agent_name = result['agent_name']
        response = result['response'].strip()

        if i == 0:
            # First agent provides the condition
            combined_parts.append(f"**Condition Check ({agent_name}):**\n{response}")
        else:
            # Subsequent agents show the action taken
            combined_parts.append(f"**Action Taken:**\n{response}")

    return "\n\n".join(combined_parts)


def format_for_ui(response: Dict[str, Any], format_type: str = 'default') -> str:
    """
    Format combined response for different UI types

    Args:
        response: Combined response dictionary from combine_agent_results()
        format_type: 'default', 'json', 'voice', 'markdown'

    Returns:
        Formatted response string
    """
    if format_type == 'json':
        return json.dumps(response, indent=2)

    elif format_type == 'voice':
        # Voice formatting is handled by voice_formatter.py
        # This is just a simple fallback
        return response['response'].replace('**', '').replace('\n\n', '. ')

    elif format_type == 'markdown':
        # Already in markdown format
        return response['response']

    else:
        # Default: just return the response text
        return response['response']
