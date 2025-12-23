"""
Relative Scheduling Module for ProjectForce Orchestrator

Handles scheduling relative to other appointments:
- "Schedule the flooring after the dishwasher install"
- "Book it the day before my oven appointment"
- "Schedule it the same week as the kitchen sink"
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _norm(s: Any) -> str:
    """Normalize for case/whitespace-insensitive comparisons."""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip().lower())


def resolve_relative_date(
    anchor_date: str,
    relation: str,
    offset: Optional[str] = None
) -> Optional[str]:
    """
    Calculate target date based on anchor date and relation.

    Args:
        anchor_date: The anchor appointment date (YYYY-MM-DD or similar)
        relation: One of "before", "after", "same_day", "same_week", "next_day", "day_before"
        offset: Optional offset like "1 day", "2 days", "1 week"

    Returns:
        Target date in YYYY-MM-DD format, or None if calculation fails

    Examples:
        >>> resolve_relative_date("2024-01-15", "after", "1 day")
        "2024-01-16"

        >>> resolve_relative_date("2024-01-15", "before", "2 days")
        "2024-01-13"

        >>> resolve_relative_date("2024-01-15", "same_week")
        "2024-01-15"  # Monday of that week
    """
    if not anchor_date:
        return None

    # Parse anchor date
    anchor_dt = None
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]:
        try:
            anchor_dt = datetime.strptime(anchor_date.split("T")[0], fmt.split("T")[0])
            break
        except ValueError:
            continue

    if anchor_dt is None:
        logger.warning(f"[RELATIVE] Could not parse anchor date: {anchor_date}")
        return None

    # Parse offset if provided
    offset_days = 0
    if offset:
        offset_match = re.match(r"(\d+)\s*(day|days|week|weeks)", offset.lower())
        if offset_match:
            num = int(offset_match.group(1))
            unit = offset_match.group(2)
            if "week" in unit:
                offset_days = num * 7
            else:
                offset_days = num

    # Calculate target date based on relation
    if relation == "same_day":
        target_dt = anchor_dt
    elif relation == "next_day":
        target_dt = anchor_dt + timedelta(days=1)
    elif relation == "day_before":
        target_dt = anchor_dt - timedelta(days=1)
    elif relation == "after":
        target_dt = anchor_dt + timedelta(days=max(offset_days, 1))
    elif relation == "before":
        target_dt = anchor_dt - timedelta(days=max(offset_days, 1))
    elif relation == "same_week":
        # Get Monday of anchor week
        target_dt = anchor_dt - timedelta(days=anchor_dt.weekday())
    elif relation == "next_week":
        # Get Monday of next week
        target_dt = anchor_dt + timedelta(days=(7 - anchor_dt.weekday()))
    else:
        logger.warning(f"[RELATIVE] Unknown relation: {relation}")
        return None

    result = target_dt.strftime("%Y-%m-%d")
    logger.info(f"[RELATIVE] Resolved: anchor={anchor_date}, relation={relation}, offset={offset} -> {result}")
    return result


def find_anchor_project_appointment(
    projects: List[Dict[str, Any]],
    anchor_reference: str
) -> Optional[Dict[str, Any]]:
    """
    Find a project by reference and return its appointment info.

    Args:
        projects: List of projects with appointment data
        anchor_reference: Reference to the anchor project (e.g., "dishwasher", "kitchen sink", "123")

    Returns:
        Dict with appointment_date, appointment_time, project_id, category, or None if not found

    Example:
        >>> projects = [{"id": "123", "category": "Dishwasher", "appointment_date": "2024-01-15"}]
        >>> find_anchor_project_appointment(projects, "dishwasher")
        {"project_id": "123", "category": "Dishwasher", "appointment_date": "2024-01-15", "appointment_time": None}
    """
    ref = _norm(anchor_reference)

    for project in projects:
        # Check category match
        category = _norm(project.get("category", project.get("Category", "")))
        if ref in category or category in ref:
            appointment_date = _extract_appointment_date(project)
            if appointment_date:
                return {
                    "project_id": project.get("id", project.get("project_id")),
                    "category": project.get("category", project.get("Category")),
                    "appointment_date": appointment_date,
                    "appointment_time": _extract_appointment_time(project),
                }

        # Check project ID match
        pid = str(project.get("id", project.get("project_id", "")))
        if ref == pid or ref == _norm(pid):
            appointment_date = _extract_appointment_date(project)
            if appointment_date:
                return {
                    "project_id": pid,
                    "category": project.get("category", project.get("Category")),
                    "appointment_date": appointment_date,
                    "appointment_time": _extract_appointment_time(project),
                }

    logger.info(f"[RELATIVE] No matching anchor project found for: {anchor_reference}")
    return None


def _extract_appointment_date(project: Dict) -> Optional[str]:
    """Extract appointment date from project using various field names."""
    return (
        project.get("appointment_date") or
        project.get("appointmentDate") or
        project.get("scheduled_date") or
        project.get("scheduledDate") or
        project.get("date")
    )


def _extract_appointment_time(project: Dict) -> Optional[str]:
    """Extract appointment time from project using various field names."""
    return (
        project.get("appointment_time") or
        project.get("appointmentTime") or
        project.get("scheduled_time") or
        project.get("scheduledTime") or
        project.get("time")
    )


def parse_relative_reference(message: str) -> Optional[Dict[str, Any]]:
    """
    Parse a message for relative scheduling references.

    Args:
        message: User message to parse

    Returns:
        Dict with anchor_project, relation, offset if found, None otherwise

    Examples:
        >>> parse_relative_reference("schedule it after the dishwasher")
        {"anchor_project": "dishwasher", "relation": "after", "offset": None}

        >>> parse_relative_reference("book it the day before my oven appointment")
        {"anchor_project": "oven", "relation": "before", "offset": "1 day"}
    """
    m = message.lower()

    # Pattern: "after the X" or "after my X"
    after_match = re.search(r"after\s+(?:the|my)?\s*(\w+(?:\s+\w+)?)\s*(?:install|appointment|project)?", m)
    if after_match:
        return {
            "anchor_project": after_match.group(1).strip(),
            "relation": "after",
            "offset": None
        }

    # Pattern: "before the X" or "before my X"
    before_match = re.search(r"before\s+(?:the|my)?\s*(\w+(?:\s+\w+)?)\s*(?:install|appointment|project)?", m)
    if before_match:
        return {
            "anchor_project": before_match.group(1).strip(),
            "relation": "before",
            "offset": None
        }

    # Pattern: "the day before/after my X"
    day_match = re.search(r"(?:the\s+)?day\s+(before|after)\s+(?:the|my)?\s*(\w+(?:\s+\w+)?)", m)
    if day_match:
        return {
            "anchor_project": day_match.group(2).strip(),
            "relation": day_match.group(1),
            "offset": "1 day"
        }

    # Pattern: "same week as X"
    same_week_match = re.search(r"same\s+week\s+as\s+(?:the|my)?\s*(\w+(?:\s+\w+)?)", m)
    if same_week_match:
        return {
            "anchor_project": same_week_match.group(1).strip(),
            "relation": "same_week",
            "offset": None
        }

    # Pattern: "week after X"
    week_after_match = re.search(r"(?:the\s+)?week\s+after\s+(?:the|my)?\s*(\w+(?:\s+\w+)?)", m)
    if week_after_match:
        return {
            "anchor_project": week_after_match.group(1).strip(),
            "relation": "after",
            "offset": "1 week"
        }

    return None


def resolve_relative_scheduling(
    target_project_id: str,
    relative_to: Dict[str, Any],
    all_projects: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Resolve a complete relative scheduling request.

    Args:
        target_project_id: The project to schedule
        relative_to: Dict with anchor_project, relation, offset
        all_projects: List of all projects for anchor lookup

    Returns:
        Dict with target_date, anchor_info, or None if resolution fails
    """
    anchor_reference = relative_to.get("anchor_project")
    relation = relative_to.get("relation", "after")
    offset = relative_to.get("offset")

    # Find anchor project appointment
    anchor_info = find_anchor_project_appointment(all_projects, anchor_reference)
    if not anchor_info:
        return {
            "success": False,
            "error": f"Could not find appointment for '{anchor_reference}' to schedule relative to."
        }

    # Calculate target date
    target_date = resolve_relative_date(
        anchor_info["appointment_date"],
        relation,
        offset
    )

    if not target_date:
        return {
            "success": False,
            "error": f"Could not calculate date relative to {anchor_reference}'s appointment."
        }

    return {
        "success": True,
        "target_project_id": target_project_id,
        "target_date": target_date,
        "anchor_info": anchor_info,
        "relation": relation,
        "offset": offset
    }
