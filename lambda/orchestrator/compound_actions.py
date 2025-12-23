"""
Compound Action Detection Module for ProjectForce Orchestrator

Handles multi-intent messages like:
- "Cancel the storm door and schedule the decking"
- "Show my projects then schedule the first one"
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Action verbs that indicate scheduling actions
ACTION_VERBS = {
    "schedule", "reschedule", "cancel", "book", "move", "change",
    "show", "list", "tell", "what", "check", "get", "find"
}

# Compound connectors (regex patterns)
COMPOUND_CONNECTORS = [
    r'\s+and\s+(?:also\s+)?',      # "and", "and also"
    r'\s+then\s+',                   # "then"
    r'\s*,\s+(?:and\s+)?(?:also\s+)?',  # ", and", ", also", ","
    r'\s+also\s+',                   # "also"
    r'\s*;\s*',                      # ";"
]


def detect_compound_actions(message: str) -> Tuple[bool, List[str]]:
    """
    Detect if message contains multiple actions and split them.

    Args:
        message: User message to analyze

    Returns:
        Tuple of (is_compound, list_of_sub_messages)

    Examples:
        >>> detect_compound_actions("Cancel the storm door and schedule the decking")
        (True, ["Cancel the storm door", "schedule the decking"])

        >>> detect_compound_actions("Show my projects")
        (False, ["Show my projects"])
    """
    m = message.strip()

    # Quick check: must have at least 2 action verbs
    m_lower = m.lower()
    verb_count = sum(1 for verb in ACTION_VERBS if verb in m_lower)
    if verb_count < 2:
        return False, [m]

    # Try to split on connectors
    for connector in COMPOUND_CONNECTORS:
        parts = re.split(connector, m, flags=re.IGNORECASE)
        if len(parts) >= 2:
            # Validate each part has an action verb
            valid_parts = []
            for part in parts:
                part = part.strip()
                if part and any(verb in part.lower() for verb in ACTION_VERBS):
                    valid_parts.append(part)

            if len(valid_parts) >= 2:
                logger.info(f"[COMPOUND] Detected {len(valid_parts)} actions: {valid_parts}")
                return True, valid_parts

    return False, [m]


def classify_compound_message(
    message: str,
    classify_func,
    conversation_history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Classify a message that may contain multiple actions.

    Args:
        message: User message to classify
        classify_func: The single-message classification function to use
        conversation_history: Optional conversation history for context

    Returns:
        For single action: Standard classification result from classify_func
        For compound: {
            "type": "compound",
            "intents": [classification1, classification2, ...],
            "execution": "sequential",
            "original_message": "...",
            "_sub_messages": [...]
        }
    """
    is_compound, sub_messages = detect_compound_actions(message)

    if not is_compound:
        # Single action - use standard classification
        return classify_func(message, conversation_history)

    # Classify each sub-message
    intents = []
    for i, sub_msg in enumerate(sub_messages):
        logger.info(f"[COMPOUND] Classifying part {i+1}: '{sub_msg}'")
        result = classify_func(sub_msg, conversation_history)
        result['_sub_message'] = sub_msg
        intents.append(result)

    return {
        "type": "compound",
        "intents": intents,
        "execution": "sequential",
        "original_message": message,
        "_sub_messages": sub_messages
    }


def execute_compound_actions(
    compound_result: Dict[str, Any],
    execute_func,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute a compound action result sequentially.

    Args:
        compound_result: Result from classify_compound_message with type="compound"
        execute_func: Function to execute each individual action
        context: Execution context (credentials, session, etc.)

    Returns:
        Combined result with all action outcomes
    """
    if compound_result.get("type") != "compound":
        raise ValueError("Expected compound result")

    intents = compound_result.get("intents", [])
    results = []
    all_success = True

    for i, intent in enumerate(intents):
        logger.info(f"[COMPOUND] Executing action {i+1}/{len(intents)}: {intent.get('action')}")

        try:
            result = execute_func(intent, context)
            results.append({
                "index": i,
                "sub_message": intent.get("_sub_message"),
                "action": intent.get("action"),
                "success": True,
                "result": result
            })
        except Exception as e:
            logger.error(f"[COMPOUND] Action {i+1} failed: {e}")
            all_success = False
            results.append({
                "index": i,
                "sub_message": intent.get("_sub_message"),
                "action": intent.get("action"),
                "success": False,
                "error": str(e)
            })

    return {
        "type": "compound_result",
        "all_success": all_success,
        "action_count": len(intents),
        "results": results,
        "original_message": compound_result.get("original_message")
    }


def format_compound_response(compound_result: Dict[str, Any]) -> str:
    """
    Format a compound result for user-friendly output.

    Args:
        compound_result: Result from execute_compound_actions

    Returns:
        Formatted response string
    """
    results = compound_result.get("results", [])

    if compound_result.get("all_success"):
        responses = []
        for r in results:
            if r.get("result") and isinstance(r["result"], dict):
                responses.append(r["result"].get("response", f"Completed: {r['action']}"))
            else:
                responses.append(f"Completed: {r['action']}")
        return " ".join(responses)
    else:
        # Mixed results
        success_count = sum(1 for r in results if r.get("success"))
        fail_count = len(results) - success_count

        parts = []
        for r in results:
            if r.get("success"):
                parts.append(f"✓ {r['action']}")
            else:
                parts.append(f"✗ {r['action']}: {r.get('error', 'failed')}")

        return f"Completed {success_count}/{len(results)} actions. " + "; ".join(parts)
