"""
Batch Operations Module for ProjectForce Orchestrator

Handles operations on multiple projects at once:
- "Schedule all my kitchen projects"
- "Cancel everything for next week"
- "Reschedule all Tuesday appointments"
"""
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Keywords that indicate batch operations
BATCH_KEYWORDS = {"all", "every", "everything", "each", "multiple", "batch"}


def _norm(s: Any) -> str:
    """Normalize for case/whitespace-insensitive comparisons."""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip().lower())


def is_batch_operation(message: str, params: Optional[Dict] = None) -> bool:
    """
    Detect if a message is requesting a batch operation.

    Args:
        message: User message to analyze
        params: Optional classification params

    Returns:
        True if the message contains batch keywords like "all", "every", etc.

    Examples:
        >>> is_batch_operation("schedule all my kitchen projects")
        True
        >>> is_batch_operation("schedule the kitchen project")
        False
    """
    m = _norm(message)
    return any(kw in m for kw in BATCH_KEYWORDS)


def prepare_batch_operation(
    projects: List[Dict[str, Any]],
    action: str,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Prepare a batch operation for execution.

    Args:
        projects: List of projects to operate on (already filtered)
        action: The action to perform (batch_schedule, batch_cancel, batch_reschedule)
        params: Additional parameters

    Returns:
        Batch operation descriptor with confirmation prompt

    Example:
        >>> projects = [{"id": "123", "category": "Kitchen Sink"}, {"id": "456", "category": "Dishwasher"}]
        >>> prepare_batch_operation(projects, "batch_schedule")
        {
            "type": "batch",
            "action": "batch_schedule",
            "projects": ["123", "456"],
            "count": 2,
            "requires_confirmation": True,
            "confirmation_message": "I found 2 projects to schedule: Kitchen Sink, Dishwasher. Do you want me to proceed with all of them?",
            "ready_to_execute": False
        }
    """
    if not projects:
        return {
            "type": "batch",
            "action": action,
            "projects": [],
            "count": 0,
            "requires_confirmation": False,
            "confirmation_message": "No projects match your criteria.",
            "ready_to_execute": False
        }

    # Extract project names for display
    project_names = [
        p.get("category", p.get("Category", f"Project {p.get('id', 'unknown')}"))
        for p in projects[:10]  # Limit to first 10 for display
    ]

    action_verb = {
        "batch_schedule": "schedule",
        "batch_cancel": "cancel",
        "batch_reschedule": "reschedule"
    }.get(action, action.replace("batch_", ""))

    if len(projects) > 10:
        names_str = ", ".join(project_names) + f", and {len(projects) - 10} more"
    else:
        names_str = ", ".join(project_names)

    return {
        "type": "batch",
        "action": action,
        "projects": [p.get("id", p.get("project_id")) for p in projects],
        "project_details": projects,
        "count": len(projects),
        "requires_confirmation": True,
        "confirmation_message": f"I found {len(projects)} projects to {action_verb}: {names_str}. Do you want me to proceed with all of them?",
        "ready_to_execute": False
    }


def execute_batch_operation(
    batch_descriptor: Dict[str, Any],
    execute_single_func,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute a batch operation on multiple projects.

    Args:
        batch_descriptor: Result from prepare_batch_operation
        execute_single_func: Function to execute on each project
        context: Execution context (credentials, session, etc.)

    Returns:
        Batch result with success/failure for each project
    """
    if batch_descriptor.get("type") != "batch":
        raise ValueError("Expected batch descriptor")

    if not batch_descriptor.get("ready_to_execute"):
        return {
            "type": "batch_result",
            "status": "pending_confirmation",
            "message": batch_descriptor.get("confirmation_message")
        }

    projects = batch_descriptor.get("project_details", [])
    action = batch_descriptor.get("action")
    results = []
    success_count = 0
    fail_count = 0

    for project in projects:
        project_id = project.get("id", project.get("project_id"))
        project_name = project.get("category", project.get("Category", f"Project {project_id}"))

        try:
            result = execute_single_func(project_id, action, context)
            results.append({
                "project_id": project_id,
                "project_name": project_name,
                "success": True,
                "result": result
            })
            success_count += 1
            logger.info(f"[BATCH] {action} succeeded for {project_name} ({project_id})")
        except Exception as e:
            results.append({
                "project_id": project_id,
                "project_name": project_name,
                "success": False,
                "error": str(e)
            })
            fail_count += 1
            logger.error(f"[BATCH] {action} failed for {project_name} ({project_id}): {e}")

    return {
        "type": "batch_result",
        "action": action,
        "total": len(projects),
        "success_count": success_count,
        "fail_count": fail_count,
        "all_success": fail_count == 0,
        "results": results
    }


def format_batch_result(batch_result: Dict[str, Any]) -> str:
    """
    Format a batch result for user-friendly output.

    Args:
        batch_result: Result from execute_batch_operation

    Returns:
        Formatted response string
    """
    if batch_result.get("status") == "pending_confirmation":
        return batch_result.get("message", "Please confirm the batch operation.")

    action = batch_result.get("action", "process").replace("batch_", "")
    total = batch_result.get("total", 0)
    success = batch_result.get("success_count", 0)
    fail = batch_result.get("fail_count", 0)

    if batch_result.get("all_success"):
        if total == 1:
            return f"Successfully {action}d 1 project."
        else:
            return f"Successfully {action}d all {total} projects."
    else:
        msg = f"Completed {success} of {total} projects."
        if fail > 0:
            failed_names = [
                r.get("project_name", r.get("project_id"))
                for r in batch_result.get("results", [])
                if not r.get("success")
            ][:3]  # Limit to 3
            if failed_names:
                msg += f" Failed: {', '.join(failed_names)}"
                if fail > 3:
                    msg += f" and {fail - 3} more"
        return msg


def confirm_batch_operation(batch_descriptor: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mark a batch operation as confirmed and ready to execute.

    Args:
        batch_descriptor: Result from prepare_batch_operation

    Returns:
        Updated batch descriptor with ready_to_execute=True
    """
    return {
        **batch_descriptor,
        "ready_to_execute": True
    }
