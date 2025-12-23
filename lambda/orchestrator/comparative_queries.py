"""
Comparative Queries Module for ProjectForce Orchestrator

Handles comparison queries across multiple projects:
- "Which project has the earliest available slot?"
- "What's the soonest I can get all three done?"
- "Which one can be scheduled this week?"
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def compare_project_availability(
    projects_with_slots: List[Dict[str, Any]],
    comparison_type: str = "earliest_slot"
) -> Dict[str, Any]:
    """
    Compare availability across multiple projects.

    Args:
        projects_with_slots: List of dicts, each with:
            - project_id: str
            - category: str
            - available_slots: list of {date, time} dicts
        comparison_type: One of:
            - "earliest_slot": Find project with earliest available slot
            - "latest_slot": Find project with latest available slot
            - "most_options": Find project with most available slots
            - "all_fit_earliest": Find earliest date when all projects could be scheduled

    Returns:
        Comparison result with winner project and summary message

    Examples:
        >>> projects = [
        ...     {"project_id": "1", "category": "Kitchen", "available_slots": [{"date": "2024-01-15"}]},
        ...     {"project_id": "2", "category": "Flooring", "available_slots": [{"date": "2024-01-10"}]}
        ... ]
        >>> compare_project_availability(projects, "earliest_slot")
        {
            "comparison_type": "earliest_slot",
            "result": {"project_id": "2", "category": "Flooring", "earliest_slot": {"date": "2024-01-10"}},
            "message": "The Flooring project has the earliest available slot on January 10."
        }
    """
    if not projects_with_slots:
        return {
            "comparison_type": comparison_type,
            "result": None,
            "message": "No projects to compare."
        }

    if comparison_type == "earliest_slot":
        return _find_earliest_slot(projects_with_slots)
    elif comparison_type == "latest_slot":
        return _find_latest_slot(projects_with_slots)
    elif comparison_type == "most_options":
        return _find_most_options(projects_with_slots)
    elif comparison_type == "all_fit_earliest":
        return _find_all_fit_earliest(projects_with_slots)
    else:
        return {
            "comparison_type": comparison_type,
            "result": None,
            "message": f"Unknown comparison type: {comparison_type}"
        }


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime object."""
    if not date_str:
        return None
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _find_earliest_slot(projects: List[Dict]) -> Dict[str, Any]:
    """Find project with the earliest available slot."""
    earliest = None
    earliest_project = None

    for proj in projects:
        slots = proj.get("available_slots", [])
        for slot in slots:
            slot_date = _parse_date(slot.get("date", ""))
            if slot_date:
                if earliest is None or slot_date < earliest:
                    earliest = slot_date
                    earliest_project = {
                        "project_id": proj.get("project_id"),
                        "category": proj.get("category"),
                        "earliest_slot": slot
                    }

    if earliest_project:
        return {
            "comparison_type": "earliest_slot",
            "result": earliest_project,
            "message": f"The {earliest_project['category']} project has the earliest available slot on {earliest.strftime('%B %d')}."
        }

    return {
        "comparison_type": "earliest_slot",
        "result": None,
        "message": "No available slots found for any project."
    }


def _find_latest_slot(projects: List[Dict]) -> Dict[str, Any]:
    """Find project with the latest available slot."""
    latest = None
    latest_project = None

    for proj in projects:
        slots = proj.get("available_slots", [])
        for slot in slots:
            slot_date = _parse_date(slot.get("date", ""))
            if slot_date:
                if latest is None or slot_date > latest:
                    latest = slot_date
                    latest_project = {
                        "project_id": proj.get("project_id"),
                        "category": proj.get("category"),
                        "latest_slot": slot
                    }

    if latest_project:
        return {
            "comparison_type": "latest_slot",
            "result": latest_project,
            "message": f"The {latest_project['category']} project has the latest available slot on {latest.strftime('%B %d')}."
        }

    return {
        "comparison_type": "latest_slot",
        "result": None,
        "message": "No available slots found for any project."
    }


def _find_most_options(projects: List[Dict]) -> Dict[str, Any]:
    """Find project with most available slots."""
    max_slots = 0
    max_project = None

    for proj in projects:
        slots = proj.get("available_slots", [])
        if len(slots) > max_slots:
            max_slots = len(slots)
            max_project = {
                "project_id": proj.get("project_id"),
                "category": proj.get("category"),
                "slot_count": len(slots)
            }

    if max_project:
        return {
            "comparison_type": "most_options",
            "result": max_project,
            "message": f"The {max_project['category']} project has the most options with {max_slots} available slots."
        }

    return {
        "comparison_type": "most_options",
        "result": None,
        "message": "No available slots found for any project."
    }


def _find_all_fit_earliest(projects: List[Dict]) -> Dict[str, Any]:
    """Find the earliest date when ALL projects have availability."""
    # Collect all available dates per project
    dates_per_project = []
    for proj in projects:
        slots = proj.get("available_slots", [])
        dates = {_parse_date(s.get("date", "")) for s in slots if _parse_date(s.get("date", ""))}
        if not dates:
            return {
                "comparison_type": "all_fit_earliest",
                "result": None,
                "message": f"The {proj.get('category', 'unknown')} project has no available slots."
            }
        dates_per_project.append(dates)

    if not dates_per_project:
        return {
            "comparison_type": "all_fit_earliest",
            "result": None,
            "message": "No projects with availability to compare."
        }

    # Find intersection of all date sets
    common_dates = dates_per_project[0]
    for dates in dates_per_project[1:]:
        common_dates = common_dates.intersection(dates)

    if common_dates:
        earliest_common = min(common_dates)
        return {
            "comparison_type": "all_fit_earliest",
            "result": {
                "common_date": earliest_common.strftime("%Y-%m-%d"),
                "project_count": len(projects)
            },
            "message": f"All {len(projects)} projects can be scheduled on {earliest_common.strftime('%B %d')}."
        }
    else:
        return {
            "comparison_type": "all_fit_earliest",
            "result": None,
            "message": "There's no single date when all projects can be scheduled. You may need to schedule them on different days."
        }


def compare_project_status(
    projects: List[Dict[str, Any]],
    comparison_type: str = "progress"
) -> Dict[str, Any]:
    """
    Compare project status/progress across multiple projects.

    Args:
        projects: List of projects with status information
        comparison_type: One of "progress", "status", "completion"

    Returns:
        Comparison result with summary
    """
    if not projects:
        return {
            "comparison_type": comparison_type,
            "result": None,
            "message": "No projects to compare."
        }

    # Group by status
    status_groups = {}
    for proj in projects:
        status = proj.get("status", proj.get("Status", "Unknown"))
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(proj)

    # Build summary
    summary_parts = []
    for status, group in status_groups.items():
        names = [p.get("category", p.get("Category", "project")) for p in group[:3]]
        if len(group) > 3:
            summary_parts.append(f"{len(group)} projects are {status}")
        else:
            summary_parts.append(f"{', '.join(names)} {'is' if len(names) == 1 else 'are'} {status}")

    return {
        "comparison_type": comparison_type,
        "result": {
            "status_groups": status_groups,
            "total_projects": len(projects)
        },
        "message": ". ".join(summary_parts) + "."
    }


def rank_projects_by_urgency(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank projects by scheduling urgency.

    Projects are ranked by:
    1. Status (schedulable > scheduled > other)
    2. Earliest available date

    Args:
        projects: List of projects with status and availability

    Returns:
        Sorted list of projects with urgency_rank added
    """
    URGENCY_ORDER = {
        "new": 1,
        "ready to schedule": 1,
        "schedulable": 1,
        "tentatively scheduled": 2,
        "scheduled": 3,
        "in progress": 4,
        "completed": 5,
        "cancelled": 6,
    }

    def get_urgency(proj):
        status = (proj.get("status", proj.get("Status", "")) or "").lower()
        return URGENCY_ORDER.get(status, 3)

    ranked = []
    for proj in projects:
        ranked.append({
            **proj,
            "urgency_rank": get_urgency(proj)
        })

    ranked.sort(key=lambda p: p["urgency_rank"])
    return ranked
