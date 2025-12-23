"""
Preference/Fallback Logic Module for ProjectForce Orchestrator

Handles scheduling preferences with primary/fallback options:
- Date preferences (Tuesday if available, otherwise Wednesday)
- Time preferences (morning preferred, afternoon is fine)
- Exclusion preferences (any time except evening)
"""
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _norm(s: Any) -> str:
    """Normalize for case/whitespace-insensitive comparisons."""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip().lower())


# Time period mapping
TIME_PERIODS = {
    "morning": ["8", "9", "10", "11"],
    "afternoon": ["12", "13", "14", "15", "16"],
    "evening": ["17", "18", "19", "20"],
}

# Day name mapping
DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def find_matching_slot_with_fallback(
    available_slots: List[Dict[str, Any]],
    date_preference: Optional[Dict[str, Any]] = None,
    time_preference: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Find a matching slot using primary preference first, then fallbacks.

    Args:
        available_slots: List of available slots with 'date' and 'time' fields
        date_preference: {"primary": "Tuesday", "fallback": ["Wednesday"], "exclude": [...]}
        time_preference: {"primary": "morning", "fallback": ["afternoon"], "exclude": [...]}

    Returns:
        Tuple of (matching_slot, preference_used) where preference_used is:
        - "primary" if primary preference matched
        - "fallback_date_1", "fallback_date_2", etc. if a date fallback matched
        - "fallback_time_1", etc. if a time fallback matched
        - "any_available" if using first valid slot
        - "none" if no match found
    """
    if not available_slots:
        return None, "none"

    # Parse preferences
    date_pref = date_preference or {}
    time_pref = time_preference or {}

    primary_date = _norm(date_pref.get("primary", ""))
    fallback_dates = [_norm(d) for d in date_pref.get("fallback", [])]
    exclude_dates = {_norm(d) for d in date_pref.get("exclude", [])}

    primary_time = _norm(time_pref.get("primary", ""))
    fallback_times = [_norm(t) for t in time_pref.get("fallback", [])]
    exclude_times = {_norm(t) for t in time_pref.get("exclude", [])}

    # Filter out excluded slots first
    valid_slots = [s for s in available_slots if not _is_excluded(s, exclude_dates, exclude_times)]

    if not valid_slots:
        logger.info("[PREFERENCE] All slots excluded by exclusion rules")
        return None, "none"

    # Try primary preferences first
    if primary_date or primary_time:
        for slot in valid_slots:
            date_match = _matches_date(slot.get("date", ""), primary_date) if primary_date else True
            time_match = _matches_time(slot.get("time", ""), primary_time) if primary_time else True
            if date_match and time_match:
                logger.info(f"[PREFERENCE] Found primary match: {slot}")
                return slot, "primary"

    # Try fallback date combinations
    for i, fallback_date in enumerate(fallback_dates):
        for slot in valid_slots:
            date_match = _matches_date(slot.get("date", ""), fallback_date)
            time_match = _matches_time(slot.get("time", ""), primary_time) if primary_time else True
            if date_match and time_match:
                logger.info(f"[PREFERENCE] Found fallback date match: {slot}")
                return slot, f"fallback_date_{i+1}"

    # Try fallback time combinations
    for i, fallback_time in enumerate(fallback_times):
        for slot in valid_slots:
            date_match = _matches_date(slot.get("date", ""), primary_date) if primary_date else True
            time_match = _matches_time(slot.get("time", ""), fallback_time)
            if date_match and time_match:
                logger.info(f"[PREFERENCE] Found fallback time match: {slot}")
                return slot, f"fallback_time_{i+1}"

    # Last resort: return first valid slot if "any" is in fallbacks
    if "any" in fallback_dates or "any" in fallback_times or (not primary_date and not primary_time):
        logger.info(f"[PREFERENCE] Using first available slot: {valid_slots[0]}")
        return valid_slots[0], "any_available"

    logger.info("[PREFERENCE] No matching slot found")
    return None, "none"


def _matches_date(slot_date: str, target: str) -> bool:
    """Check if slot date matches target."""
    if not target or target == "any":
        return True

    sd = _norm(slot_date)

    # Check for day name (Monday, Tuesday, etc.)
    if target in DAY_NAMES:
        try:
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(slot_date, fmt)
                    return DAY_NAMES[dt.weekday()] == target
                except ValueError:
                    continue
        except Exception:
            pass

    return target in sd


def _matches_time(slot_time: str, target: str) -> bool:
    """Check if slot time matches target."""
    if not target or target == "any":
        return True

    st = _norm(slot_time)

    # Check for time period
    if target in TIME_PERIODS:
        for hour in TIME_PERIODS[target]:
            if hour in st or f"{hour}:" in slot_time:
                return True
        return False

    # Direct match
    return target in st


def _is_excluded(slot: Dict, exclude_dates: set, exclude_times: set) -> bool:
    """Check if slot is in exclusion list."""
    slot_date = _norm(slot.get("date", ""))
    slot_time = _norm(slot.get("time", ""))

    for ed in exclude_dates:
        if _matches_date(slot_date, ed):
            return True

    for et in exclude_times:
        if _matches_time(slot_time, et):
            return True

    return False


def parse_preference_from_message(message: str) -> Dict[str, Any]:
    """
    Extract date/time preferences with fallbacks from a message.

    Patterns detected:
    - "X if available, otherwise Y"
    - "X preferred, but Y is fine"
    - "X or Y, whichever is available"
    - "any X except Y"

    Returns:
        Dict with date_preference and/or time_preference structures
    """
    m = _norm(message)
    result = {}

    # Pattern: "X if available, otherwise Y"
    if_otherwise = re.search(r"(\w+)\s+if\s+available[,\s]+otherwise\s+(\w+)", m)
    if if_otherwise:
        primary, fallback = if_otherwise.groups()
        if primary in DAY_NAMES or "day" in primary:
            result["date_preference"] = {"primary": primary, "fallback": [fallback]}
        elif primary in TIME_PERIODS or "am" in primary or "pm" in primary:
            result["time_preference"] = {"primary": primary, "fallback": [fallback]}

    # Pattern: "X preferred, but Y is fine"
    preferred_but = re.search(r"(\w+)\s+preferred[,\s]+but\s+(\w+)\s+is\s+(?:fine|ok|okay)", m)
    if preferred_but:
        primary, fallback = preferred_but.groups()
        if primary in TIME_PERIODS:
            result["time_preference"] = {"primary": primary, "fallback": [fallback]}
        elif primary in DAY_NAMES:
            result["date_preference"] = {"primary": primary, "fallback": [fallback]}

    # Pattern: "any X except Y"
    any_except = re.search(r"any(?:time|day)?\s+except\s+(\w+)", m)
    if any_except:
        excluded = any_except.group(1)
        if excluded in TIME_PERIODS or "am" in excluded or "pm" in excluded:
            result["time_preference"] = {"primary": "any", "exclude": [excluded]}
        elif excluded in DAY_NAMES:
            result["date_preference"] = {"primary": "any", "exclude": [excluded]}

    return result
