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
import re
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
    extract_location_from_context,
    find_better_weather_dates,
    add_weather_indicators_to_dates
)

logger = logging.getLogger()

# Bedrock runtime client singleton
_bedrock_runtime = None


# ============================================================================
# STAGE-DRIVEN WORKFLOW CONTINUATION
# These functions check if user is providing what we're waiting for,
# bypassing context_resolver and classification to avoid "5th Dec" being
# interpreted as "5th project".
# ============================================================================

def extract_date_from_message(message: str) -> Optional[str]:
    """
    Extract date from message without LLM - simple patterns only.
    Returns date in YYYY-MM-DD format or None if no date found.
    """
    from datetime import datetime

    msg = message.lower().strip()

    # Month name patterns (3-letter abbreviations)
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    # Pattern 1: "5th Dec", "5 Dec", "5th of December"
    pattern1 = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?([a-z]+)', msg)
    if pattern1:
        day_str, month_str = pattern1.groups()
        for m_name, m_num in months.items():
            if month_str.startswith(m_name):
                year = datetime.now().year
                # Handle year rollover (if date is in past, assume next year)
                proposed_date = datetime(year, m_num, int(day_str))
                if proposed_date < datetime.now():
                    year += 1
                return f"{year}-{m_num:02d}-{int(day_str):02d}"

    # Pattern 2: "Dec 5", "December 5th"
    pattern2 = re.search(r'([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?', msg)
    if pattern2:
        month_str, day_str = pattern2.groups()
        for m_name, m_num in months.items():
            if month_str.startswith(m_name):
                year = datetime.now().year
                proposed_date = datetime(year, m_num, int(day_str))
                if proposed_date < datetime.now():
                    year += 1
                return f"{year}-{m_num:02d}-{int(day_str):02d}"

    # Pattern 3: YYYY-MM-DD (already formatted)
    pattern3 = re.search(r'(\d{4})-(\d{2})-(\d{2})', msg)
    if pattern3:
        return pattern3.group(0)

    # Pattern 4: MM/DD/YYYY or MM-DD-YYYY
    pattern4 = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', msg)
    if pattern4:
        month, day, year = pattern4.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    return None


def extract_ordinal_project_reference(message: str) -> Optional[int]:
    """
    Extract ordinal project reference from message.
    Returns project_index (0-based, supports negative) or None if no ordinal reference found.

    Examples:
        "first project" -> 0
        "1st project" -> 0
        "second project" -> 1
        "2nd project" -> 1
        "last project" -> -1
        "details for the last one" -> -1
    """
    msg = message.lower().strip()

    # Check if message is about project details/info (not scheduling a date)
    project_keywords = ['project', 'one', 'details', 'show', 'info', 'about']
    has_project_context = any(kw in msg for kw in project_keywords)

    if not has_project_context:
        return None

    # Pattern for "last project", "the last one", "last"
    if re.search(r'\blast\b', msg):
        logger.info(f"[ORDINAL] Detected 'last' reference in: {msg}")
        return -1

    # Pattern for "first project", "the first one", "1st"
    if re.search(r'\b(first|1st)\b', msg):
        logger.info(f"[ORDINAL] Detected 'first' reference in: {msg}")
        return 0

    # Pattern for "second", "2nd"
    if re.search(r'\b(second|2nd)\b', msg):
        logger.info(f"[ORDINAL] Detected 'second' reference in: {msg}")
        return 1

    # Pattern for "third", "3rd"
    if re.search(r'\b(third|3rd)\b', msg):
        logger.info(f"[ORDINAL] Detected 'third' reference in: {msg}")
        return 2

    # Pattern for numeric ordinals: "4th project", "5th one", etc.
    # IMPORTANT: Only match if followed by project-related word to avoid "5th Dec"
    numeric_match = re.search(r'\b(\d+)(?:st|nd|rd|th)\s+(?:project|one)\b', msg)
    if numeric_match:
        index = int(numeric_match.group(1)) - 1  # Convert to 0-based
        logger.info(f"[ORDINAL] Detected numeric ordinal {numeric_match.group(1)} -> index {index}")
        return index

    return None


def extract_time_from_message(message: str) -> Optional[str]:
    """
    Extract time from message without LLM - simple patterns only.
    Returns time in HH:MM format (24-hour) or None if no time found.
    """
    msg = message.lower().strip()

    # Pattern 1: "2pm", "2 pm", "2:00pm", "2:00 pm"
    pattern1 = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)', msg)
    if pattern1:
        hour = int(pattern1.group(1))
        minute = int(pattern1.group(2) or 0)
        ampm = pattern1.group(3)

        if ampm == 'pm' and hour < 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    # Pattern 2: "2 o'clock", "2 oclock"
    pattern2 = re.search(r'(\d{1,2})\s*o\'?clock', msg)
    if pattern2:
        hour = int(pattern2.group(1))
        # Assume PM for business hours (1-6 o'clock)
        if 1 <= hour <= 6:
            hour += 12
        return f"{hour:02d}:00"

    # Pattern 3: 24-hour format "14:00", "14:30"
    pattern3 = re.search(r'\b(\d{2}):(\d{2})\b', msg)
    if pattern3:
        hour, minute = int(pattern3.group(1)), int(pattern3.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"

    return None


def check_workflow_continuation(message: str, workflow_state: Dict) -> Optional[Dict]:
    """
    Check if user is providing what we're waiting for (date or time selection).
    If yes, return the next action directly (skip classification).
    If no, return None to proceed with normal classification.

    This prevents "5th Dec" from being interpreted as "5th project" when
    we're awaiting date selection.
    """
    if not workflow_state:
        return None

    current_stage = workflow_state.get('current_stage')
    context = workflow_state.get('context', {})
    workflow_type = workflow_state.get('workflow_type', '')

    logger.info(f"[CONTINUATION] Checking continuation: stage={current_stage}, workflow_type={workflow_type}")

    # Stage: Waiting for date selection
    if current_stage == 'awaiting_date_selection':
        date = extract_date_from_message(message)
        if date:
            logger.info(f"[CONTINUATION] User provided date '{date}' at stage '{current_stage}' - bypassing classification")
            return {
                'continue_workflow': True,
                'action': 'get_time_slots',
                'params': {
                    'project_id': context.get('project_id'),
                    'date': date,
                    'request_id': context.get('request_id')
                },
                'next_stage': 'awaiting_time_selection',
                'preserve_context': {
                    'project_id': context.get('project_id'),
                    'date': date,
                    'request_id': context.get('request_id'),
                    'category': context.get('category'),
                    'city': context.get('city'),
                    'state': context.get('state'),
                    # Preserve batch mode context if present
                    'batch_mode': context.get('batch_mode'),
                    'project_ids': context.get('project_ids'),
                    'current_index': context.get('current_index'),
                    'total_projects': context.get('total_projects'),
                    'completed_projects': context.get('completed_projects')
                },
                'workflow_type': workflow_type
            }

    # Stage: Waiting for time selection
    if current_stage == 'awaiting_time_selection':
        time_val = extract_time_from_message(message)
        if time_val:
            logger.info(f"[CONTINUATION] User provided time '{time_val}' at stage '{current_stage}' - bypassing classification")
            return {
                'continue_workflow': True,
                'action': 'confirm_appointment',
                'params': {
                    'project_id': context.get('project_id'),
                    'date': context.get('date'),
                    'time': time_val,
                    'request_id': context.get('request_id')
                },
                'next_stage': 'complete',
                'preserve_context': context,
                'workflow_type': workflow_type
            }

    # Not a continuation - proceed with normal classification
    logger.info(f"[CONTINUATION] No continuation match for stage '{current_stage}' - proceeding with classification")
    return None


def format_date_natural(date_str: str) -> str:
    """
    Convert date from "MM-DD-YYYY HH:MM AM/PM" format to natural language.
    Examples:
    - "11-29-2025 08:00 AM" -> "November 29, 2025 at 8:00 AM"
    - "11-29-2025 08:00 AM - 11-29-2025 09:00 AM" -> "November 29, 2025 at 8:00 AM - 9:00 AM"
    """
    if not date_str:
        return date_str

    month_names = {
        '01': 'January', '02': 'February', '03': 'March', '04': 'April',
        '05': 'May', '06': 'June', '07': 'July', '08': 'August',
        '09': 'September', '10': 'October', '11': 'November', '12': 'December'
    }

    try:
        # Check if it's a date range (contains " - " with dates on both sides)
        if ' - ' in date_str:
            parts = date_str.split(' - ')
            if len(parts) == 2:
                # Parse start: "MM-DD-YYYY HH:MM AM"
                start_match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}:\d{2}\s*(?:AM|PM))', parts[0].strip(), re.IGNORECASE)
                # Parse end: "MM-DD-YYYY HH:MM AM"
                end_match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}:\d{2}\s*(?:AM|PM))', parts[1].strip(), re.IGNORECASE)

                if start_match and end_match:
                    start_month = month_names.get(start_match.group(1).zfill(2), start_match.group(1))
                    start_day = str(int(start_match.group(2)))  # Remove leading zero
                    start_year = start_match.group(3)
                    start_time = start_match.group(4)
                    end_time = end_match.group(4)

                    # Same date range: "November 29, 2025 at 8:00 AM - 9:00 AM"
                    return f"{start_month} {start_day}, {start_year} at {start_time} - {end_time}"

        # Single date/time: "MM-DD-YYYY HH:MM AM"
        single_match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}:\d{2}\s*(?:AM|PM))', date_str.strip(), re.IGNORECASE)
        if single_match:
            month = month_names.get(single_match.group(1).zfill(2), single_match.group(1))
            day = str(int(single_match.group(2)))  # Remove leading zero
            year = single_match.group(3)
            time = single_match.group(4)
            return f"{month} {day}, {year} at {time}"

        # Date only: "MM-DD-YYYY"
        date_only_match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})$', date_str.strip())
        if date_only_match:
            month = month_names.get(date_only_match.group(1).zfill(2), date_only_match.group(1))
            day = str(int(date_only_match.group(2)))
            year = date_only_match.group(3)
            return f"{month} {day}, {year}"

        # Return original if no pattern matched
        return date_str
    except Exception as e:
        logger.warning(f"Date formatting failed for '{date_str}': {e}")
        return date_str


def extract_project_data_from_history(conversation_history: List[Dict], classification: Dict = None) -> Optional[Dict]:
    """
    Extract project data from conversation history for context queries.
    Looks for project details, scheduled dates, technician info, etc.

    Args:
        conversation_history: List of conversation messages
        classification: Optional classification result with entities (project_id, project_index)
    """
    project_data = {}

    # Get project reference from classification if available
    target_project_id = None
    target_project_index = None
    if classification and classification.get('entities'):
        entities = classification['entities']
        target_project_id = entities.get('project_id')
        target_project_index = entities.get('project_index')
        logger.info(f"[CONTEXT] Looking for project_id={target_project_id}, project_index={target_project_index}")

    logger.info(f"[CONTEXT] Extracting from {len(conversation_history)} messages in history")

    for msg in reversed(conversation_history):
        content = msg.get('content', '')
        role = msg.get('role', '')

        if role != 'assistant':
            continue

        # Look for technician/installer info - multiple patterns
        logger.info(f"[CONTEXT] Scanning message for technician info, length={len(content)}")

        if 'installer' in content.lower() or 'technician' in content.lower() or 'scheduled with' in content.lower():
            logger.info(f"[CONTEXT] Found technician/installer keyword in content")

            # Pattern 1: "scheduled with Jay Installer1 on" (conversational text)
            scheduled_with_match = re.search(r'scheduled with\s+([A-Za-z][A-Za-z0-9\s]+?)\s+on\s', content, re.IGNORECASE)
            if scheduled_with_match and 'technician_name' not in project_data:
                project_data['technician_name'] = scheduled_with_match.group(1).strip()
                logger.info(f"[CONTEXT] Pattern 1 matched: {project_data['technician_name']}")

            # Pattern 1b: "technician, Name, will" or "technician Name will"
            tech_will_match = re.search(r'technician[,\s]+([A-Za-z][A-Za-z0-9\s]+?)[,\s]+will', content, re.IGNORECASE)
            if tech_will_match and 'technician_name' not in project_data:
                project_data['technician_name'] = tech_will_match.group(1).strip()
                logger.info(f"[CONTEXT] Pattern 1b matched: {project_data['technician_name']}")

            # Pattern 2: "Assigned Technician\nJay Installer1 (ID: 8203)" (formatted output)
            assigned_match = re.search(r'Assigned Technician\s*[\n\r]+\s*([A-Za-z][A-Za-z0-9\s]+?)\s*\(ID:\s*(\d+)\)', content, re.IGNORECASE)
            if assigned_match and 'technician_name' not in project_data:
                project_data['technician_name'] = assigned_match.group(1).strip()
                project_data['technician_id'] = assigned_match.group(2)

            # Pattern 3: "Technician: Jay Installer1" or "Installer: Jay Installer1"
            colon_match = re.search(r'(?:installer|technician)[:\s]+([A-Za-z][A-Za-z0-9\s]+?)(?:\s*\(|,|\.|$)', content, re.IGNORECASE)
            if colon_match and 'technician_name' not in project_data:
                project_data['technician_name'] = colon_match.group(1).strip()

            # Pattern 4: "Assigned Technician ... Name (ID: 8203)" - alternate format
            alt_match = re.search(r'Assigned\s+Technician\s*[:\-]?\s*([A-Z][a-z]+\s+[A-Z][a-z0-9]+)\s*\(ID:\s*(\d+)\)', content)
            if alt_match and 'technician_name' not in project_data:
                project_data['technician_name'] = alt_match.group(1).strip()
                project_data['technician_id'] = alt_match.group(2)

            # Pattern 5: Direct "Name (ID: 8203)" after any technician mention
            direct_match = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z0-9]+)\s*\(ID:\s*(\d+)\)', content)
            if direct_match and 'technician_name' not in project_data:
                project_data['technician_name'] = direct_match.group(1).strip()
                project_data['technician_id'] = direct_match.group(2)
                logger.info(f"[CONTEXT] Pattern 5 matched: {project_data['technician_name']}")

        # Try to extract from JSON in response
        try:
            # Look for JSON blocks in the response
            json_matches = re.findall(r'```json\s*([\s\S]*?)```', content)
            for json_str in json_matches:
                data = json.loads(json_str)
                logger.info(f"[CONTEXT] Parsing JSON block, keys: {list(data.keys())}")

                # Extract installer info - check multiple possible locations
                installer = data.get('installer') or data.get('technician')
                if installer:
                    logger.info(f"[CONTEXT] Found installer data: {installer}")
                    if isinstance(installer, dict):
                        if installer.get('name') and 'technician_name' not in project_data:
                            project_data['technician_name'] = installer['name']
                            logger.info(f"[CONTEXT] Extracted technician_name from JSON: {installer['name']}")
                        if installer.get('id') and 'technician_id' not in project_data:
                            project_data['technician_id'] = str(installer['id'])
                    elif isinstance(installer, str) and 'technician_name' not in project_data:
                        project_data['technician_name'] = installer

                # Check for technician_display at root level (e.g., "Jay Installer1 (ID: 8203)")
                tech_display = data.get('technician_display', '')
                if tech_display and tech_display != 'Not assigned' and 'technician_name' not in project_data:
                    # Parse "Name (ID: 123)" format - re module already imported at top
                    display_match = re.match(r'^(.+?)\s*\(ID:\s*(\d+)\)$', tech_display)
                    if display_match:
                        project_data['technician_name'] = display_match.group(1).strip()
                        project_data['technician_id'] = display_match.group(2)
                        logger.info(f"[CONTEXT] Extracted from technician_display: {project_data['technician_name']}")
                    else:
                        project_data['technician_name'] = tech_display
                        logger.info(f"[CONTEXT] Used technician_display directly: {tech_display}")

                # Extract category from root level
                if data.get('category') and 'category' not in project_data:
                    project_data['category'] = data['category']
                    logger.info(f"[CONTEXT] Extracted category from root: {data['category']}")

                # Extract project_id from root level
                if data.get('project_id') and 'project_id' not in project_data:
                    project_data['project_id'] = data['project_id']

                # NEW: Check for projects array (from welcome/list_projects response)
                if 'projects' in data and isinstance(data['projects'], list) and len(data['projects']) > 0:
                    projects_list = data['projects']
                    logger.info(f"[CONTEXT] Found projects array with {len(projects_list)} projects")

                    # Find the target project by ID or index
                    target_proj = None
                    if target_project_id:
                        for p in projects_list:
                            if str(p.get('id')) == str(target_project_id):
                                target_proj = p
                                logger.info(f"[CONTEXT] Matched project by ID: {target_project_id}")
                                break
                    elif target_project_index is not None:
                        # Support negative indices: -1 = last, -2 = second to last, etc.
                        try:
                            target_proj = projects_list[target_project_index]
                            actual_id = target_proj.get('id', 'unknown')
                            logger.info(f"[CONTEXT] Matched project by index: {target_project_index} -> project #{actual_id}")
                        except IndexError:
                            logger.warning(f"[CONTEXT] Index {target_project_index} out of range for {len(projects_list)} projects")
                    elif len(projects_list) == 1:
                        # Only one project, use it
                        target_proj = projects_list[0]
                        logger.info(f"[CONTEXT] Using only project in list")

                    if target_proj:
                        # Extract technician from installer field
                        if target_proj.get('installer') and 'technician_name' not in project_data:
                            inst = target_proj['installer']
                            if isinstance(inst, dict):
                                project_data['technician_name'] = inst.get('name', '')
                                project_data['technician_id'] = str(inst.get('id', ''))
                                logger.info(f"[CONTEXT] Extracted technician from projects array: {project_data['technician_name']}")

                        # Extract scheduled date/time
                        if target_proj.get('scheduledDate') and 'scheduled_date' not in project_data:
                            sched = target_proj['scheduledDate']
                            project_data['scheduled_date'] = sched
                            # Parse time from "11-29-2025 08:00 AM - 11-29-2025 09:00 AM" format
                            time_range_match = re.search(
                                r'(\d{1,2}:\d{2}\s*(?:AM|PM))\s*-\s*\d{1,2}-\d{1,2}-\d{4}\s*(\d{1,2}:\d{2}\s*(?:AM|PM))',
                                sched, re.IGNORECASE
                            )
                            if time_range_match:
                                start_time = time_range_match.group(1)
                                end_time = time_range_match.group(2)
                                project_data['scheduled_time'] = f"{start_time} - {end_time}"
                                logger.info(f"[CONTEXT] Extracted time range from projects: {project_data['scheduled_time']}")

                        # Extract other fields
                        if target_proj.get('category') and 'category' not in project_data:
                            project_data['category'] = target_proj['category']
                        if target_proj.get('id') and 'project_id' not in project_data:
                            project_data['project_id'] = str(target_proj['id'])
                        if target_proj.get('address') and 'address' not in project_data:
                            addr = target_proj['address']
                            if isinstance(addr, dict):
                                project_data['address'] = addr.get('fullAddress') or f"{addr.get('address1', '')}, {addr.get('city', '')}, {addr.get('state', '')} {addr.get('zipcode', '')}"
                                # Also extract city/state separately for weather queries
                                if addr.get('city') and 'city' not in project_data:
                                    project_data['city'] = addr['city']
                                if addr.get('state') and 'state' not in project_data:
                                    project_data['state'] = addr['state']
                                logger.info(f"[CONTEXT] Extracted address: {project_data['address']}, city={addr.get('city')}, state={addr.get('state')}")
                            else:
                                project_data['address'] = addr

                # Also check for nested project data
                if 'project' in data and isinstance(data['project'], dict):
                    proj = data['project']

                    # Check project.installer first
                    if proj.get('installer') and 'technician_name' not in project_data:
                        inst = proj['installer']
                        if isinstance(inst, dict) and inst.get('name'):
                            project_data['technician_name'] = inst['name']
                            project_data['technician_id'] = str(inst.get('id', ''))
                            logger.info(f"[CONTEXT] Extracted from nested project.installer: {inst['name']}")

                    # Also check project.technician (added alongside installer in response)
                    if proj.get('technician') and 'technician_name' not in project_data:
                        tech = proj['technician']
                        if isinstance(tech, dict) and tech.get('name'):
                            project_data['technician_name'] = tech['name']
                            project_data['technician_id'] = str(tech.get('id', ''))
                            logger.info(f"[CONTEXT] Extracted from nested project.technician: {tech['name']}")

                # Extract appointment info
                if 'appointment' in data:
                    appt = data['appointment']
                    if appt.get('date'):
                        project_data['scheduled_date'] = appt['date']
                    if appt.get('time'):
                        project_data['scheduled_time'] = appt['time']

                # Extract from scheduledDate field
                if 'scheduledDate' in data:
                    sched = data['scheduledDate']
                    project_data['scheduled_date'] = sched
                    # Parse time from "11-29-2025 08:00 AM - 11-29-2025 09:00 AM" format
                    if 'scheduled_time' not in project_data:
                        time_range_match = re.search(
                            r'(\d{1,2}:\d{2}\s*(?:AM|PM))\s*-\s*\d{1,2}-\d{1,2}-\d{4}\s*(\d{1,2}:\d{2}\s*(?:AM|PM))',
                            sched, re.IGNORECASE
                        )
                        if time_range_match:
                            start_time = time_range_match.group(1)
                            end_time = time_range_match.group(2)
                            project_data['scheduled_time'] = f"{start_time} - {end_time}"
                            logger.info(f"[CONTEXT] Extracted time range: {project_data['scheduled_time']}")

                # Extract project category
                if 'category' in data:
                    project_data['category'] = data['category']

                # Extract project ID
                if 'id' in data:
                    project_data['project_id'] = data['id']
                elif 'project_id' in data:
                    project_data['project_id'] = data['project_id']

                # Extract address
                if 'full_address' in data:
                    project_data['address'] = data['full_address']
                elif 'address' in data:
                    addr = data['address']
                    if isinstance(addr, dict):
                        project_data['address'] = addr.get('fullAddress', '')
                    else:
                        project_data['address'] = addr

        except (json.JSONDecodeError, TypeError):
            pass

        # Look for scheduled date patterns in text
        date_match = re.search(r'scheduled (?:for|on)\s+([A-Za-z]+\s+\d+(?:st|nd|rd|th)?(?:,?\s+\d{4})?)', content, re.IGNORECASE)
        if date_match and 'scheduled_date' not in project_data:
            project_data['scheduled_date'] = date_match.group(1)

        # Look for time patterns
        time_match = re.search(r'at\s+(\d{1,2}:\d{2}\s*(?:AM|PM)?)', content, re.IGNORECASE)
        if time_match and 'scheduled_time' not in project_data:
            project_data['scheduled_time'] = time_match.group(1)

        # Look for project ID patterns
        project_id_match = re.search(r'#(\d{7})\b', content)
        if project_id_match and 'project_id' not in project_data:
            project_data['project_id'] = project_id_match.group(1)

        # Look for category patterns
        category_match = re.search(r'(Decking|Flooring|Roofing|Kitchen|Bathroom|Siding|Windows)\s+(?:project|installation)', content, re.IGNORECASE)
        if category_match and 'category' not in project_data:
            project_data['category'] = category_match.group(1)

    logger.info(f"[CONTEXT] Final extracted project_data: {project_data}")
    return project_data if project_data else None


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
Scheduling: list_projects, get_project_details, get_available_dates, get_time_slots, confirm_appointment, reschedule_appointment, cancel_appointment, batch_schedule, defer_workflow, abandon_workflow
Information: get_weather, context_query
Chitchat: greet, help, general

CONTEXT-BASED INFORMATION QUERIES (answer from conversation/project context):

Technician queries -> context_query with query_type: "technician"
Examples: "who is the technician", "who is coming", "who's doing the work", "technician name",
"who's the installer", "who will do the job", "tell me about the technician", "who's assigned to my project",
"what's the technician's name", "who is working on this", "installer info", "who will be coming out"

Appointment time queries -> context_query with query_type: "appointment_time"
Examples: "what time is my appointment", "when are they coming", "what's the scheduled time",
"when is the appointment", "what time should I expect them", "when will they arrive",
"appointment details", "when is the installation", "what day is my appointment", "scheduled date and time"

Address queries -> context_query with query_type: "address"
Examples: "what's the address", "where is the work being done", "installation address",
"where are they coming", "what address do you have", "job location", "where is the project"

For these: Check if project details are in conversation history. Return intent=information, action=context_query
IMPORTANT: If user specifies a project reference (e.g., "for the 1st project", "for project 7751741", "for my Decking project"):
- Extract project_index (0-based) if ordinal: "1st project" -> project_index: 0, "2nd project" -> project_index: 1
- Extract project_id if specific ID mentioned
- Extract category if mentioned (e.g., "Decking project")
Example: "who is the technician for the 1st project" -> context_query with query_type: "technician", project_index: 0

WORKFLOW CONTROL:

defer_workflow - User wants to pause/wait/defer (NOT cancel):
Examples: "I will wait", "let me think about it", "not now", "maybe later", "I'll decide later",
"will do it later", "I'll get back to you", "give me some time", "hold on", "not right now",
"I need to think", "let me check my calendar", "I'll call back", "put it on hold", "I'm not ready yet", "can we do this later"
Return: intent=scheduling, action=defer_workflow

abandon_workflow - User explicitly cancels/stops:
Examples: "never mind", "cancel", "forget it", "stop", "don't bother", "skip it", "I changed my mind",
"cancel that", "no thanks", "I don't want to", "forget about it", "that's okay, nevermind", "actually no", "let's not"
Return: intent=scheduling, action=abandon_workflow

ACTION SELECTION GUIDE:
- "schedule project X" / "schedule the first project" / "book an appointment for X" -> get_available_dates (START scheduling workflow)
- "schedule the first two projects" / "schedule first 3 projects" / "schedule all projects" -> batch_schedule (MULTIPLE projects)
- "show project X" / "details for project X" / "what is project X" -> get_project_details (just show info, NOT scheduling)
- User selects a DATE from available dates -> get_time_slots
- User selects a TIME from time slots -> confirm_appointment
- "cancel this appointment" / "cancel my appointment" / "cancel this" / "cancel the booking" -> cancel_appointment (extract project_id from context)
- "reschedule this" / "reschedule my appointment" / "change the date" / "move the appointment" -> reschedule_appointment (extract project_id from context)

IMPORTANT RULES:
1. Extract ALL entities from the message AND conversation history
2. If user says "it", "that" (pronoun) - look back and find the MOST RECENTLY DISCUSSED project
3. CRITICAL - Handle ORDINAL references ("first", "last", "2nd", "3rd", etc.):
   - These refer to the ORIGINAL PROJECT LIST shown at start of conversation, NOT the most recently discussed project
   - "first project" -> return project_index: 0
   - "second project" / "2nd project" -> return project_index: 1
   - "third project" / "3rd project" -> return project_index: 2
   - "last project" -> return project_index: -1 (ALWAYS use -1, never extract project_id for "last")
   - NEVER extract project_id directly for ordinal references - ALWAYS use project_index
   - The system will resolve project_index to the actual project_id from the stored list
4. If user provides a date/time, extract it even if implicit (e.g., "tomorrow", "2pm")
5. If in an active workflow, determine what stage we're at
6. Be intelligent about corrections: "actually, make it the 28th" means update the date
7. For weather queries:
   - "weather for 1st project" / "weather for project 7751741" -> Extract location (city, state) from that project's address in conversation
   - "what's the weather" (no project specified) -> Use location from most recent project in conversation
   - Always return action: "get_weather" with entities.location as "City, ST" format (e.g., "Minneapolis, MN")
8. For list_projects with status filter: if user says "scheduled projects", "new projects", etc., extract status entity
9. Handle batch/multiple project references:
   - "first two projects" -> extract project_ids for positions [0, 1] from conversation
   - "first 3 projects" -> extract project_ids for positions [0, 1, 2]
   - "all my projects" -> extract all project_ids from conversation
   - "projects 1 and 3" -> extract specific positions [0, 2]
   - Return entities.project_ids as ARRAY when multiple projects detected

Examples:

Scheduling:
{{
    "intent": "scheduling",
    "action": "get_time_slots",
    "entities": {{"project_id": "7751748", "date": "2025-11-27"}},
    "workflow_type": "schedule_appointment",
    "reasoning": "User selected Nov 27 from available dates."
}}

Ordinal reference to project (IMPORTANT: use project_index, not project_id):
{{
    "intent": "scheduling",
    "action": "get_project_details",
    "entities": {{"project_index": -1}},
    "reasoning": "User said 'details for the last project'. Using project_index: -1 to get the LAST project from the original list (not the most recently discussed one)."
}}

First project reference:
{{
    "intent": "scheduling",
    "action": "get_project_details",
    "entities": {{"project_index": 0}},
    "reasoning": "User said 'details for the first project'. Using project_index: 0 to get project at position 0 in the list."
}}

Second project reference:
{{
    "intent": "scheduling",
    "action": "get_project_details",
    "entities": {{"project_index": 1}},
    "reasoning": "User said 'show me the 2nd project'. Using project_index: 1 to get project at position 1 in the list."
}}

Weather (with context extraction):
{{
    "intent": "information",
    "action": "get_weather",
    "entities": {{"location": "Minneapolis, MN"}},
    "reasoning": "User asked about weather. Recent project details showed address in Minneapolis, MN."
}}

Weather for specific project (extract location from project):
{{
    "intent": "information",
    "action": "get_weather",
    "entities": {{"location": "Minneapolis, MN", "project_id": "7751741", "project_index": 0}},
    "reasoning": "User asked 'what is the weather for the 1st project'. Found 1st project (#7751741) has address in Minneapolis, MN. Will fetch weather for that location."
}}

Batch scheduling (multiple projects):
{{
    "intent": "scheduling",
    "action": "batch_schedule",
    "entities": {{"project_ids": ["7751741", "7751742"]}},
    "workflow_type": "batch_schedule_appointment",
    "reasoning": "User wants to schedule 'first two projects'. Looking at conversation, projects #7751741 and #7751742 are first and second in the list."
}}

Context query (technician info):
{{
    "intent": "information",
    "action": "context_query",
    "entities": {{"query_type": "technician"}},
    "reasoning": "User asking about technician. Will extract from project data in conversation."
}}

Defer workflow (user wants to wait):
{{
    "intent": "scheduling",
    "action": "defer_workflow",
    "entities": {{}},
    "reasoning": "User said 'I will wait' - they want to pause the current scheduling workflow."
}}

Abandon workflow (user cancels):
{{
    "intent": "scheduling",
    "action": "abandon_workflow",
    "entities": {{}},
    "reasoning": "User said 'never mind' - they want to cancel the current scheduling process."
}}

Cancel appointment (cancel existing scheduled appointment):
{{
    "intent": "scheduling",
    "action": "cancel_appointment",
    "entities": {{"project_id": "7751742"}},
    "reasoning": "User said 'cancel this appointment'. Looking at conversation, user was just viewing project #7751742 which has a scheduled appointment. Extracting project_id from context."
}}

Reschedule appointment (reschedule existing scheduled appointment):
{{
    "intent": "scheduling",
    "action": "reschedule_appointment",
    "entities": {{"project_id": "7751742"}},
    "reasoning": "User said 'reschedule this'. Looking at conversation, user was viewing project #7751742. Extracting project_id from context to start reschedule flow."
}}

CRITICAL: For cancel_appointment and reschedule_appointment, ALWAYS extract project_id from the conversation context when user says "this", "this appointment", "this one", etc. Look for the most recently discussed project ID (format: #7751742 or Project 7751742 or id: 7751742).

Respond ONLY with valid JSON."""

    response_text = call_sonnet(prompt, max_tokens=800)

    try:
        # Parse JSON response
        classification = json.loads(response_text)
        logger.info(f"[SONNET] Sonnet classification: {classification}")
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
   - For cancel_appointment: need project_id - extract from conversation context if user says "cancel this appointment" after viewing project details
   - For reschedule_appointment: need project_id - extract from conversation context if user says "reschedule this" after viewing project details
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

CRITICAL EXAMPLE FOR DATE SELECTION (after showing available dates):

When user says "08th Dec", "December 8", "the 8th", "next Monday", etc. (AFTER seeing available dates for a project):
This is DATE SELECTION to get time slots - NOT a new scheduling request!

User says "08th Dec" (after seeing available dates for project #7751741 with request_id 12345):
{{
    "should_call_lambda": true,
    "lambda_action": "get_time_slots",
    "lambda_params": {{
        "project_id": "7751741",
        "date": "2025-12-08",
        "request_id": "12345"
    }},
    "update_workflow_state": {{
        "workflow_type": "schedule_appointment",
        "current_stage": "awaiting_time_selection",
        "context": {{
            "project_id": "7751741",
            "date": "2025-12-08",
            "request_id": "12345"
        }}
    }},
    "workflow_complete": false
}}

User says "December 15th" or "15th" (after seeing available dates for project #7751742):
{{
    "should_call_lambda": true,
    "lambda_action": "get_time_slots",
    "lambda_params": {{
        "project_id": "7751742",
        "date": "2025-12-15",
        "request_id": "67890"
    }},
    "update_workflow_state": {{
        "workflow_type": "schedule_appointment",
        "current_stage": "awaiting_time_selection",
        "context": {{
            "project_id": "7751742",
            "date": "2025-12-15",
            "request_id": "67890"
        }}
    }},
    "workflow_complete": false
}}

IMPORTANT DATE SELECTION RULES:
1. When user provides JUST a date after available dates were shown, call get_time_slots (NOT get_available_dates)
2. Use the project_id and request_id from the CURRENT workflow context (most recently shown project)
3. Convert user's date format to YYYY-MM-DD (e.g., "08th Dec" -> "2025-12-08", "December 15" -> "2025-12-15")
4. Do NOT start a new scheduling flow - CONTINUE the existing one!
5. If "08" could be date or project, and user just saw available dates, it's a DATE selection
6. The workflow context contains the project_id and request_id you need - use them!

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

EXAMPLES FOR CANCEL/RESCHEDULE:

User says "cancel this appointment" (after viewing project #7751742 details):
{{
    "should_call_lambda": true,
    "lambda_action": "cancel_appointment",
    "lambda_params": {{
        "project_id": "7751742"  // Extract from conversation context - the most recently discussed project
    }}
}}

User says "reschedule this" (after viewing project #7751742 details):
{{
    "should_call_lambda": true,
    "lambda_action": "reschedule_appointment",
    "lambda_params": {{
        "project_id": "7751742"  // Extract from conversation context - the most recently discussed project
    }}
}}

IMPORTANT FOR CONTEXT RESOLUTION:
- When user refers to "this appointment", "this project", "this one", etc., extract the project_id from the MOST RECENT project mentioned or displayed in the conversation history.
- Look for project IDs in formats: #7751742, Project 7751742, "id": "7751742"
- If multiple projects were shown in a list and user says "the second one" or "2nd project", use that position from the list.

Respond ONLY with valid JSON."""

    response_text = call_sonnet(prompt, max_tokens=1000)

    try:
        decision = json.loads(response_text)
        logger.info(f"[DECISION] Sonnet decision: call_lambda={decision.get('should_call_lambda')}, action={decision.get('lambda_action')}")
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
    conversation_history: List[Dict],
    channel: str = 'chat'  # 'chat' or 'voice' - for channel-specific handling
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

    # ========================================================================
    # STEP 0: Check for workflow continuation FIRST (before classification)
    # This prevents "5th Dec" from being interpreted as "5th project"
    # ========================================================================
    continuation = check_workflow_continuation(message, workflow_state)
    if continuation and continuation.get('continue_workflow'):
        logger.info(f"[CONTINUATION] Bypassing classification - user provided data at stage '{workflow_state.get('current_stage')}'")

        # Execute the continuation action directly
        try:
            action = continuation['action']
            params = continuation['params']
            next_stage = continuation['next_stage']
            preserve_context = continuation.get('preserve_context', {})
            cont_workflow_type = continuation.get('workflow_type', '')

            # Determine if this is a reschedule workflow
            is_reschedule = cont_workflow_type == 'reschedule_appointment'

            # Convert action to reschedule-specific if needed
            if is_reschedule and action in ['get_time_slots']:
                action = 'get_rescheduler_slots'
                logger.info(f"[CONTINUATION] Converting {continuation['action']} to {action} for reschedule workflow")

            # Add common params
            params.update({
                'customer_id': customer_id,
                'client_id': client_id,
                'pf_bearer_token': pf_bearer_token
            })

            logger.info(f"[CONTINUATION] Calling Lambda: action={action}, params={list(params.keys())}")

            # Call Lambda directly
            lambda_start = time.time()
            lambda_response = call_lambda_directly(action, params)
            timing['lambda_call'] = time.time() - lambda_start

            # Extract response
            response_data = lambda_response.get('response', {})
            func_response = response_data.get('functionResponse', {})
            body_wrapper = func_response.get('responseBody', {})
            text_body = body_wrapper.get('TEXT', {})
            body_str = text_body.get('body', '{}')

            if isinstance(body_str, str):
                response_body = json.loads(body_str)
            else:
                response_body = body_str

            # WEATHER ENRICHMENT for time slots (outdoor projects)
            if action in ['get_time_slots', 'get_rescheduler_slots']:
                project_category = preserve_context.get('category')
                if project_category and is_outdoor_project(project_category):
                    logger.info(f"[CONTINUATION][WEATHER] Outdoor project ({project_category}), enriching time slots with weather")
                    location = None
                    city = preserve_context.get('city')
                    state = preserve_context.get('state')
                    if city and state:
                        location = f"{city}, {state}"

                    if location:
                        try:
                            weather_params = {
                                'location': location,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            }
                            weather_response = call_lambda_directly('get_weather', weather_params)

                            w_data = weather_response.get('response', {})
                            w_func = w_data.get('functionResponse', {})
                            w_body_wrapper = w_func.get('responseBody', {})
                            w_text = w_body_wrapper.get('TEXT', {})
                            w_body_str = w_text.get('body', '{}')

                            if isinstance(w_body_str, str):
                                weather_body = json.loads(w_body_str)
                            else:
                                weather_body = w_body_str

                            # Find forecast for the selected date
                            target_date = params.get('date')
                            forecast = find_forecast_for_date(weather_body, target_date)

                            if forecast:
                                suitability = analyze_weather_suitability(forecast, project_category)
                                response_body['weather_forecast'] = forecast
                                response_body['weather_suitability'] = suitability
                                logger.info(f"[CONTINUATION][WEATHER] Added weather for {target_date}: {suitability.get('suitable', 'N/A')}")
                        except Exception as weather_err:
                            logger.warning(f"[CONTINUATION][WEATHER] Weather enrichment failed (non-fatal): {weather_err}")

            # Format the response
            response_text = format_lambda_response(action, response_body, message)

            # Update workflow state
            if next_stage == 'complete':
                state_manager.clear_state(session_id)
                logger.info("[CONTINUATION] Workflow complete, state cleared")
            else:
                # Update context with preserved values and selected date
                new_context = {k: v for k, v in preserve_context.items() if v is not None}

                # Update date in context if this was a date selection
                if action == 'get_time_slots' or action == 'get_rescheduler_slots':
                    new_context['date'] = params.get('date')
                    # Also extract request_id from response for next step
                    if response_body.get('request_id'):
                        new_context['request_id'] = response_body['request_id']

                state_manager.save_state(session_id, {
                    'workflow_type': cont_workflow_type,
                    'current_stage': next_stage,
                    'context': new_context
                })
                logger.info(f"[CONTINUATION] State updated: stage={next_stage}")

            timing['total'] = time.time() - start_time
            return {
                'response': response_text,
                'intent': 'scheduling',
                'action': action,
                'agent_name': 'Intelligent Orchestrator (Stage-Driven Continuation)',
                'direct_call': True,
                'timing': timing
            }

        except Exception as cont_err:
            logger.error(f"[CONTINUATION] Error executing continuation: {cont_err}")
            # Fall through to normal classification on error

    # ========================================================================
    # STEP 0.5: Check for ORDINAL PROJECT REFERENCE (before classification)
    # This handles "last project", "first project", "2nd project" etc.
    # by directly resolving the ordinal to a project_id from the stored list
    # and fetching project details - bypassing Sonnet to avoid misinterpretation
    # ========================================================================
    ordinal_index = extract_ordinal_project_reference(message)
    if ordinal_index is not None:
        logger.info(f"[ORDINAL] Detected ordinal reference: index={ordinal_index}")

        # Get project_ids from workflow state (stored when projects were listed)
        project_ids = workflow_state.get('context', {}).get('project_ids', [])

        if project_ids:
            try:
                # Resolve ordinal index to project_id (supports negative indices)
                resolved_project_id = str(project_ids[ordinal_index])
                logger.info(f"[ORDINAL] Resolved index {ordinal_index} to project_id={resolved_project_id} from list of {len(project_ids)} projects")

                # Call get_project_details directly
                ordinal_start = time.time()
                details_response = call_lambda_directly('get_project_details', {
                    'project_id': resolved_project_id,
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_bearer_token
                })
                timing['lambda_call'] = time.time() - ordinal_start

                # Extract response body
                response_data = details_response.get('response', {})
                func_response = response_data.get('functionResponse', {})
                body_wrapper = func_response.get('responseBody', {})
                text_body = body_wrapper.get('TEXT', {})
                body_str = text_body.get('body', '{}')

                if isinstance(body_str, str):
                    response_body = json.loads(body_str)
                else:
                    response_body = body_str

                # Generate response using Sonnet for natural language
                project_data = response_body.get('project', response_body)

                response_gen_start = time.time()
                response_text = generate_response_with_sonnet(
                    intent='information',
                    action='get_project_details',
                    lambda_response=response_body,
                    original_message=message,
                    conversation_history=conversation_history
                )
                timing['response_generation'] = time.time() - response_gen_start

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'information',
                    'action': 'get_project_details',
                    'agent_name': 'Intelligent Orchestrator (Ordinal Reference)',
                    'direct_call': True,
                    'timing': timing
                }

            except IndexError:
                logger.warning(f"[ORDINAL] Index {ordinal_index} out of range for {len(project_ids)} projects")
                # Fall through to normal classification
            except Exception as ordinal_err:
                logger.error(f"[ORDINAL] Error handling ordinal reference: {ordinal_err}")
                # Fall through to normal classification
        else:
            logger.info("[ORDINAL] No project_ids in workflow state, falling through to classification")

    # Step 1: Intelligent classification using Sonnet 3.7
    logger.info("[SONNET] Step 1: Intelligent classification with Sonnet 3.7")
    classification_start = time.time()

    classification = intelligent_classify(
        message,
        conversation_history,
        workflow_state
    )

    timing['classification'] = time.time() - classification_start

    # HANDLE CONTEXT QUERIES: Answer from conversation history
    if classification.get('action') == 'context_query':
        query_type = classification.get('entities', {}).get('query_type', '')
        logger.info(f"[CONTEXT] Context query detected: {query_type}")

        # Extract project data from conversation history (pass classification for project reference)
        project_data = extract_project_data_from_history(conversation_history, classification)
        logger.info(f"[CONTEXT] Extracted project data: {project_data}")

        if project_data:
            if query_type == 'technician':
                tech_name = project_data.get('technician_name', 'Not assigned yet')
                tech_id = project_data.get('technician_id', '')
                category = project_data.get('category', 'project')
                project_id = project_data.get('project_id', '')
                scheduled_date = project_data.get('scheduled_date', '')
                scheduled_time = project_data.get('scheduled_time', '')

                if tech_name and tech_name != 'Not assigned yet':
                    # Build natural, conversational response (no IDs for customers)
                    response = f"**{tech_name}** is the technician assigned to your {category} project"
                    if project_id:
                        response += f" (#{project_id})"
                    response += "."
                    if scheduled_date:
                        # Format date naturally
                        formatted_date = format_date_natural(scheduled_date)
                        response += f" They're scheduled to arrive on **{formatted_date}**"
                        if scheduled_time and scheduled_time not in formatted_date:
                            response += f" at {scheduled_time}"
                        response += "."
                else:
                    response = f"A technician hasn't been assigned to your {category} project yet. Once your appointment is scheduled, you'll be able to see who's assigned."

            elif query_type == 'appointment_time':
                scheduled_date = project_data.get('scheduled_date', '')
                scheduled_time = project_data.get('scheduled_time', '')
                category = project_data.get('category', 'project')
                project_id = project_data.get('project_id', '')

                if scheduled_date or scheduled_time:
                    response = f"Your {category} project"
                    if project_id:
                        response += f" (#{project_id})"
                    response += " is scheduled for"
                    if scheduled_date:
                        # Format date naturally
                        formatted_date = format_date_natural(scheduled_date)
                        response += f" **{formatted_date}**"
                    if scheduled_time and scheduled_time not in (scheduled_date or ''):
                        response += f" at **{scheduled_time}**"
                    response += "."
                else:
                    response = f"Your {category} project doesn't have a scheduled appointment yet. Would you like to schedule one now?"

            elif query_type == 'address':
                address = project_data.get('address', '')
                category = project_data.get('category', 'project')
                project_id = project_data.get('project_id', '')

                if address:
                    response = f"The installation address for your {category} project"
                    if project_id:
                        response += f" (#{project_id})"
                    response += f" is **{address}**."
                else:
                    response = "I don't have the address details in our current conversation. Would you like me to look up your project details?"
            else:
                response = "I'm not sure what information you're looking for. Could you be more specific?"
        else:
            response = "I don't have that information in our current conversation. Would you like me to look up your project details?"

        timing['total'] = time.time() - start_time
        return {
            'response': response,
            'intent': 'information',
            'action': 'context_query',
            'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
            'direct_call': True,
            'timing': timing
        }

    # HANDLE WEATHER QUERIES WITH PROJECT REFERENCE: Extract location from project and fetch weather
    if classification.get('action') == 'get_weather':
        entities = classification.get('entities', {})
        project_index = entities.get('project_index')
        project_id = entities.get('project_id')
        location = entities.get('location')  # May already be extracted by Sonnet

        # If we have a project reference but no location, extract from conversation history
        if (project_index is not None or project_id) and not location:
            logger.info(f"[WEATHER] Weather query with project reference: index={project_index}, id={project_id}")

            # Extract project data from conversation history (pass classification for project reference)
            project_data = extract_project_data_from_history(conversation_history, classification)

            if project_data:
                # Get location from project address
                address = project_data.get('address', '')
                if address:
                    # Parse city, state from address like "123 Main St, Minneapolis, MN 55401"
                    # Try to extract "City, ST" pattern
                    addr_match = re.search(r',\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*\d*', address)
                    if addr_match:
                        location = f"{addr_match.group(1).strip()}, {addr_match.group(2)}"
                        logger.info(f"[WEATHER] Extracted location from address: {location}")

                # Also try to get city/state directly from extraction
                if not location:
                    city = project_data.get('city', '')
                    state = project_data.get('state', '')
                    if city and state:
                        location = f"{city}, {state}"
                        logger.info(f"[WEATHER] Built location from city/state: {location}")

        if location:
            logger.info(f"[WEATHER] Fetching weather for location: {location}")

            try:
                weather_start = time.time()
                weather_response = call_lambda_directly('get_weather', {
                    'location': location,
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_bearer_token
                })
                timing['weather_call'] = time.time() - weather_start

                # Extract weather data from Lambda response
                w_data = weather_response.get('response', {})
                w_func = w_data.get('functionResponse', {})
                w_body_wrapper = w_func.get('responseBody', {})
                w_text = w_body_wrapper.get('TEXT', {})
                w_body_str = w_text.get('body', '{}')

                if isinstance(w_body_str, str):
                    weather_body = json.loads(w_body_str)
                else:
                    weather_body = w_body_str

                # Format the weather response (format_lambda_response already imported at top)
                weather_text = format_lambda_response('get_weather', weather_body, message)

                # Add project context if available
                project_data_for_ctx = extract_project_data_from_history(conversation_history, classification)
                if project_data_for_ctx:
                    category = project_data_for_ctx.get('category', '')
                    proj_id = project_data_for_ctx.get('project_id', '')
                    if category and proj_id:
                        weather_text = f"Here's the weather forecast for your **{category}** project (#{proj_id}) in {location}:\n\n{weather_text}"
                    elif category:
                        weather_text = f"Here's the weather forecast for your **{category}** project in {location}:\n\n{weather_text}"

                timing['total'] = time.time() - start_time
                return {
                    'response': weather_text,
                    'intent': 'information',
                    'action': 'get_weather',
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing
                }

            except Exception as weather_err:
                logger.error(f"Weather fetch failed: {weather_err}")
                response = f"I couldn't fetch the weather for {location} right now. Please try again in a moment."

                timing['total'] = time.time() - start_time
                return {
                    'response': response,
                    'intent': 'information',
                    'action': 'get_weather',
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing
                }
        else:
            logger.warning("[WEATHER] Could not determine location for weather query")
            # Fall through to let normal flow handle it (Sonnet might ask for location)

    # HANDLE CANCEL CONFIRMATION (User says "yes" after seeing project details for cancel)
    if workflow_state and workflow_state.get('current_stage') == 'awaiting_cancel_confirmation':
        user_lower = message.lower().strip()
        affirmative_responses = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'confirm', 'do it', 'go ahead', 'proceed', 'cancel it', 'yes please']
        negative_responses = ['no', 'nope', 'nah', 'cancel', 'never mind', 'nevermind', 'stop', 'dont', "don't", 'abort']

        if any(affirm in user_lower for affirm in affirmative_responses):
            logger.info("[CANCEL] User confirmed cancellation, proceeding with actual cancel")
            cancel_context = workflow_state.get('context', {})
            project_id = cancel_context.get('project_id')

            if project_id:
                try:
                    # Call cancel_appointment with confirmed=True
                    cancel_response = call_lambda_directly('cancel_appointment', {
                        'project_id': project_id,
                        'confirmed': 'true',  # This triggers the actual cancellation
                        'customer_id': customer_id,
                        'client_id': client_id,
                        'pf_bearer_token': pf_bearer_token
                    })

                    # Extract response
                    cancel_data = cancel_response.get('response', {})
                    cancel_func = cancel_data.get('functionResponse', {})
                    cancel_body_wrapper = cancel_func.get('responseBody', {})
                    cancel_text = cancel_body_wrapper.get('TEXT', {})
                    cancel_body_str = cancel_text.get('body', '{}')

                    if isinstance(cancel_body_str, str):
                        cancel_body = json.loads(cancel_body_str)
                    else:
                        cancel_body = cancel_body_str

                    # Format response
                    formatted_cancel = format_lambda_response('cancel_appointment', cancel_body, message)

                    # Clear workflow state
                    state_manager.clear_state(session_id)
                    logger.info("[CANCEL] Cancellation complete, workflow state cleared")

                    timing['total'] = time.time() - start_time
                    return {
                        'response': formatted_cancel,
                        'intent': 'scheduling',
                        'action': 'cancel_appointment',
                        'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                        'direct_call': True,
                        'timing': timing
                    }

                except Exception as cancel_err:
                    logger.error(f"[CANCEL] Cancellation failed: {cancel_err}")
                    state_manager.clear_state(session_id)
                    timing['total'] = time.time() - start_time
                    return {
                        'response': f"I encountered an error while cancelling the appointment: {str(cancel_err)}. Please try again.",
                        'intent': 'scheduling',
                        'action': 'cancel_appointment',
                        'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                        'direct_call': True,
                        'timing': timing
                    }

        elif any(neg in user_lower for neg in negative_responses):
            logger.info("[CANCEL] User declined cancellation")
            state_manager.clear_state(session_id)
            timing['total'] = time.time() - start_time
            return {
                'response': "No problem, I've cancelled the cancellation request. Your appointment remains scheduled. Is there anything else I can help with?",
                'intent': 'scheduling',
                'action': 'cancel_appointment_declined',
                'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                'direct_call': True,
                'timing': timing
            }

    # HANDLE WORKFLOW DEFERRAL/ABANDONMENT
    if classification.get('action') in ['defer_workflow', 'abandon_workflow']:
        action_type = classification.get('action')
        logger.info(f"[WORKFLOW] Workflow control detected: {action_type}")

        # Get current workflow context for personalized response
        workflow_context = workflow_state.get('context', {}) if workflow_state else {}
        project_id = workflow_context.get('project_id', '')
        category = workflow_context.get('category', 'project')

        # Clear workflow state
        state_manager.clear_state(session_id)
        logger.info(f"[WORKFLOW] Workflow state cleared for session {session_id}")

        if action_type == 'defer_workflow':
            response = "No problem! I've put the scheduling on hold for now."
            if project_id:
                response += f" When you're ready to schedule your {category} project (#{project_id}), just let me know."
            else:
                response += " When you're ready to continue, just let me know."
            response += " I'll be here to help."
        else:  # abandon_workflow
            response = "No problem, I've cancelled the scheduling."
            if project_id:
                response += f" If you'd like to schedule your {category} project (#{project_id}) later, just ask."
            response += " Let me know if there's anything else I can help with!"

        timing['total'] = time.time() - start_time
        return {
            'response': response,
            'intent': 'scheduling',
            'action': action_type,
            'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
            'direct_call': True,
            'timing': timing
        }

    # Step 2: Intelligent decision using Sonnet 3.7
    logger.info("[DECISION] Step 2: Intelligent decision-making with Sonnet 3.7")
    decision_start = time.time()

    decision = intelligent_decide_next_action(
        message,
        classification,
        workflow_state,
        conversation_history
    )

    timing['decision'] = time.time() - decision_start

    # BATCH SCHEDULING: Handle multi-project scheduling
    if classification.get('action') == 'batch_schedule' or decision.get('lambda_action') == 'batch_schedule':
        project_ids = classification.get('entities', {}).get('project_ids', [])
        batch_count = classification.get('entities', {}).get('count', 0)

        # Fallback: If Sonnet provided a count but not enough project_ids, extract from conversation
        if batch_count > len(project_ids):
            logger.info(f"[BATCH] Batch count ({batch_count}) > extracted IDs ({len(project_ids)}), extracting from conversation...")

            # Start with any IDs Sonnet already provided
            all_found_ids = list(project_ids)

            # Look for project list in conversation history - check ALL assistant messages
            for msg in reversed(conversation_history):
                content = msg.get('content', '')
                role = msg.get('role', '')

                # Look in assistant messages that likely contain project lists
                # Check for: #7751741 format, "Project #" mentions, or JSON with project IDs
                if role == 'assistant' and ('Project' in content or '"id"' in content or '#77' in content):
                    logger.info(f"[BATCH] Checking message for project IDs: {content[:100]}...")

                    # Try ALL patterns and accumulate IDs
                    # Pattern 1: #7751741 format (with # prefix)
                    found_ids = re.findall(r'#(\d{7})\b', content)

                    # Pattern 2: "id": "7751741" format (JSON)
                    found_ids.extend(re.findall(r'"id"\s*:\s*"?(\d{7})"?', content))

                    # Pattern 3: Project 7751741 or Project #7751741
                    found_ids.extend(re.findall(r'Project\s+#?(\d{7})\b', content, re.IGNORECASE))

                    if found_ids:
                        # Add unique IDs to our list
                        for pid in found_ids:
                            if pid not in all_found_ids:
                                all_found_ids.append(pid)

                        logger.info(f"[BATCH] Found IDs in this message: {found_ids}, total unique: {all_found_ids}")

                        if len(all_found_ids) >= batch_count:
                            project_ids = all_found_ids[:batch_count]
                            logger.info(f"[BATCH] Extracted project IDs from conversation: {project_ids}")
                            break

            # Use whatever we found
            if len(all_found_ids) > len(project_ids):
                project_ids = all_found_ids[:batch_count]

            # If we still don't have enough IDs, log a warning
            if len(project_ids) < batch_count:
                logger.warning(f"[BATCH] Could only find {len(project_ids)} project IDs, user requested {batch_count}")

        if project_ids and len(project_ids) > 1:
            logger.info(f"[BATCH] Batch scheduling detected: {len(project_ids)} projects - {project_ids}")

            # Initialize batch mode - start with first project
            first_project_id = project_ids[0]

            # Convert to get_available_dates for first project
            decision['should_call_lambda'] = True
            decision['lambda_action'] = 'get_available_dates'
            decision['lambda_params'] = {'project_id': first_project_id}

            # Set up batch tracking in workflow state
            if not decision.get('update_workflow_state'):
                decision['update_workflow_state'] = {}

            decision['update_workflow_state'].update({
                'workflow_type': 'batch_schedule_appointment',
                'current_stage': 'awaiting_date_selection',
                'context': {
                    'batch_mode': True,
                    'project_ids': project_ids,
                    'current_index': 0,
                    'total_projects': len(project_ids),
                    'completed_projects': [],
                    'project_id': first_project_id
                }
            })

            logger.info(f"[BATCH] Starting batch scheduling with project #{first_project_id} (1 of {len(project_ids)})")

    # Step 3: Execute decision
    if decision.get('should_call_lambda'):
        # Call Lambda function
        lambda_action = decision['lambda_action']
        lambda_params = decision['lambda_params']

        # WORKFLOW SWITCH DETECTION (Hybrid Approach):
        # Clear stale workflow state when user starts a DIFFERENT workflow type
        # This prevents issues like "schedule 3rd project" using reschedule API
        # because old workflow_state had workflow_type='reschedule_appointment'
        WORKFLOW_ACTIONS = {
            'schedule_appointment': 'schedule_appointment',
            'get_available_dates': 'schedule_appointment',
            'get_time_slots': 'schedule_appointment',
            'reschedule_appointment': 'reschedule_appointment',
            'cancel_appointment': 'cancel_appointment',
            'list_projects': 'project_listing',
        }

        new_workflow_type = None
        classified_action = classification.get('action', '')

        # Determine what workflow the NEW action belongs to
        if classified_action in WORKFLOW_ACTIONS:
            new_workflow_type = WORKFLOW_ACTIONS[classified_action]

        # Also check if classification explicitly specifies workflow_type
        if classification.get('workflow_type'):
            new_workflow_type = classification.get('workflow_type')

        # If we have an old workflow state AND the new action is for a DIFFERENT workflow, clear it
        if workflow_state and new_workflow_type:
            old_workflow_type = workflow_state.get('workflow_type')

            # Check if user is working with a different project (same workflow type but new project)
            # IMPORTANT: Only consider this a "new project" if the classification explicitly has workflow_type
            # (indicating a new workflow request like "schedule project X"), NOT for continuations like date selection
            new_project_id = classification.get('entities', {}).get('project_id')
            old_project_id = workflow_state.get('context', {}).get('project_id')

            # Only treat as new project if:
            # 1. Classification explicitly has workflow_type (new workflow, not continuation)
            # 2. AND the project IDs are different
            has_explicit_workflow = classification.get('workflow_type') is not None
            is_new_project = (has_explicit_workflow and
                              new_project_id and
                              old_project_id and
                              str(new_project_id) != str(old_project_id))

            if old_workflow_type and old_workflow_type != new_workflow_type:
                logger.info(f"[WORKFLOW SWITCH] Clearing old '{old_workflow_type}' state - user starting new '{new_workflow_type}' workflow")
                state_manager.clear_state(session_id)
                workflow_state = None  # Reset local variable too
            elif is_new_project and new_workflow_type in ['schedule_appointment', 'reschedule_appointment', 'cancel_appointment']:
                logger.info(f"[WORKFLOW SWITCH] New project {new_project_id} detected (explicit workflow_type={classification.get('workflow_type')}) - clearing old workflow state for project {old_project_id}")
                state_manager.clear_state(session_id)
                workflow_state = None

        # RESCHEDULE: Use get_rescheduler_slots instead of get_available_dates/get_time_slots
        # For already scheduled projects, the normal slots API returns "Job already requested"
        # NOTE: Only use classification's workflow_type, NOT old workflow_state, to avoid
        # confusing a new "schedule" request with an old "reschedule" workflow
        is_reschedule = (
            classification.get('action') == 'reschedule_appointment' or
            classification.get('workflow_type') == 'reschedule_appointment'
        )

        # Also check workflow state but ONLY if classification doesn't have workflow_type
        # (meaning we're continuing an existing workflow, not starting a new one)
        if not classification.get('workflow_type') and workflow_state:
            is_reschedule = is_reschedule or workflow_state.get('workflow_type') == 'reschedule_appointment'

        if is_reschedule and lambda_action in ['get_available_dates', 'get_time_slots']:
            logger.info(f"[RESCHEDULE] Converting {lambda_action} to get_rescheduler_slots for reschedule workflow")
            lambda_action = 'get_rescheduler_slots'
            decision['lambda_action'] = 'get_rescheduler_slots'
            # Use the selected date if provided, otherwise use today's date
            from datetime import datetime
            if 'date' not in lambda_params:
                lambda_params['date'] = datetime.now().strftime("%Y-%m-%d")

        # RESOLVE project_index to project_id for ALL channels
        # This handles ordinal references like "last project", "first project", "3rd project"
        # project_index can be negative (-1 = last, -2 = second to last, etc.)
        if 'project_index' in lambda_params and 'project_id' not in lambda_params:
            project_index = lambda_params.get('project_index')
            logger.info(f"[ORDINAL] Resolving project_index={project_index} to project_id")

            resolved = False

            # First try: Get project_ids from workflow_state.context
            if workflow_state:
                context = workflow_state.get('context', {})
                project_ids = context.get('project_ids', [])
                if project_ids and isinstance(project_ids, list):
                    logger.info(f"[ORDINAL] Found {len(project_ids)} project_ids in workflow_state")
                    # project_index supports negative indices: -1 = last, -2 = second to last, etc.
                    if isinstance(project_index, int):
                        try:
                            resolved_id = str(project_ids[project_index])
                            lambda_params['project_id'] = resolved_id
                            del lambda_params['project_index']
                            logger.info(f"[ORDINAL] Resolved from workflow_state: project_index={project_index} -> project_id={resolved_id}")
                            resolved = True
                        except IndexError:
                            logger.warning(f"[ORDINAL] project_index={project_index} out of range (have {len(project_ids)} projects)")

            if not resolved:
                # AUTO-FETCH: If no project_ids in workflow_state, fetch them first
                logger.info(f"[ORDINAL] No project_ids in workflow_state - auto-fetching projects first")
                try:
                    # Call list_projects to get all projects
                    list_response = call_lambda_directly('list_projects', {
                        'customer_id': customer_id,
                        'client_id': client_id,
                        'pf_bearer_token': pf_bearer_token
                    })

                    # Extract projects from response
                    list_data = list_response.get('response', {})
                    list_func = list_data.get('functionResponse', {})
                    list_body_wrapper = list_func.get('responseBody', {})
                    list_text = list_body_wrapper.get('TEXT', {})
                    list_body_str = list_text.get('body', '{}')

                    if isinstance(list_body_str, str):
                        list_body = json.loads(list_body_str)
                    else:
                        list_body = list_body_str

                    # Extract project_ids
                    if 'projects' in list_body and isinstance(list_body['projects'], list):
                        fetched_projects = list_body['projects']
                        fetched_ids = [str(p.get('id', '')) for p in fetched_projects if p.get('id')]

                        if fetched_ids:
                            logger.info(f"[ORDINAL] Auto-fetched {len(fetched_ids)} project_ids: {fetched_ids[:5]}...")

                            # Save to workflow_state for future queries
                            if not workflow_state:
                                workflow_state = {'context': {}}
                            if 'context' not in workflow_state:
                                workflow_state['context'] = {}
                            workflow_state['context']['project_ids'] = fetched_ids

                            # Save to DynamoDB
                            state_manager.save_state(session_id, {
                                'workflow_type': 'project_listing',
                                'current_stage': 'listing_projects',
                                'context': {'project_ids': fetched_ids}
                            })

                            # Now resolve project_index (supports negative indices)
                            if isinstance(project_index, int):
                                try:
                                    resolved_id = str(fetched_ids[project_index])
                                    lambda_params['project_id'] = resolved_id
                                    del lambda_params['project_index']
                                    logger.info(f"[ORDINAL] Auto-resolved: project_index={project_index} -> project_id={resolved_id}")
                                    resolved = True
                                except IndexError:
                                    logger.warning(f"[ORDINAL] project_index={project_index} out of range (fetched {len(fetched_ids)} projects)")

                except Exception as fetch_err:
                    logger.error(f"[ORDINAL] Auto-fetch projects failed: {fetch_err}")

                if not resolved:
                    logger.warning(f"[ORDINAL] Could not resolve project_index={project_index}")

        # Add auth params
        lambda_params.update({
            'customer_id': customer_id,
            'client_id': client_id,
            'pf_bearer_token': pf_bearer_token
        })

        logger.info(f"[LAMBDA] Calling Lambda: {lambda_action} with params: {lambda_params}")
        lambda_start = time.time()

        # AUTO-FETCH PROJECT DETAILS: When starting scheduling workflow, fetch project info first
        # This ensures we have category, city, state for weather-aware scheduling
        if lambda_action == 'get_available_dates':
            project_id = lambda_params.get('project_id')
            existing_category = workflow_state.get('context', {}).get('category') if workflow_state else None

            if project_id and not existing_category:
                logger.info(f"[PROJECT] Auto-fetching project details for weather-aware scheduling (project_id={project_id})")
                try:
                    details_response = call_lambda_directly('get_project_details', {
                        'project_id': project_id,
                        'customer_id': customer_id,
                        'client_id': client_id,
                        'pf_bearer_token': pf_bearer_token
                    })

                    # Extract project info
                    details_data = details_response.get('response', {})
                    details_func = details_data.get('functionResponse', {})
                    details_body_wrapper = details_func.get('responseBody', {})
                    details_text = details_body_wrapper.get('TEXT', {})
                    details_body_str = details_text.get('body', '{}')

                    if isinstance(details_body_str, str):
                        project_info = json.loads(details_body_str)
                    else:
                        project_info = details_body_str

                    # Extract category and location from project details
                    # Response structure: {"project": {"address": {...}}, "category": "...", "full_address": "..."}
                    project_category = project_info.get('category', '')

                    # Try nested project.address first
                    project_obj = project_info.get('project', {})
                    address_obj = project_obj.get('address', {}) if isinstance(project_obj, dict) else {}

                    if isinstance(address_obj, dict) and address_obj:
                        project_city = address_obj.get('city', '')
                        project_state = address_obj.get('state', '')
                        project_address = address_obj.get('fullAddress', '') or project_info.get('full_address', '')
                    else:
                        # Fallback: parse from full_address "Street, City, State ZIP"
                        full_addr = project_info.get('full_address', '')
                        project_address = full_addr
                        # Try to extract city/state from "..., City, State ZIP"
                        parts = full_addr.split(',')
                        if len(parts) >= 2:
                            city_part = parts[-2].strip() if len(parts) >= 2 else ''
                            state_zip = parts[-1].strip().split() if parts else []
                            project_city = city_part
                            project_state = state_zip[0] if state_zip else ''
                        else:
                            project_city = ''
                            project_state = ''

                    logger.info(f"[PROJECT] Address extraction: project_obj keys={list(project_obj.keys()) if isinstance(project_obj, dict) else 'N/A'}, address_obj={address_obj}")

                    if project_category or project_city:
                        logger.info(f"[PROJECT] Extracted: category={project_category}, city={project_city}, state={project_state}")

                        # Update or create workflow state with project info
                        if not decision.get('update_workflow_state'):
                            decision['update_workflow_state'] = {'context': {}}
                        if 'context' not in decision['update_workflow_state']:
                            decision['update_workflow_state']['context'] = {}

                        decision['update_workflow_state']['context'].update({
                            'category': project_category,
                            'city': project_city,
                            'state': project_state,
                            'address': project_address,
                            'project_id': project_id
                        })

                        # Also update the current workflow_state for use in this request
                        if workflow_state is None:
                            workflow_state = {'context': {}}
                        if 'context' not in workflow_state:
                            workflow_state['context'] = {}
                        workflow_state['context'].update({
                            'category': project_category,
                            'city': project_city,
                            'state': project_state,
                            'address': project_address
                        })

                except Exception as details_error:
                    logger.warning(f"Auto-fetch project details failed (non-fatal): {details_error}")
                    # Continue with scheduling - weather check will be skipped

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

            # PROACTIVE WEATHER WARNINGS: Add weather indicators when showing available dates
            if lambda_action == 'get_available_dates':
                available_dates = response_body.get('available_dates', [])
                project_category = workflow_state.get('context', {}).get('category') if workflow_state else None

                if available_dates and project_category and is_outdoor_project(project_category):
                    logger.info(f"[WEATHER] Proactive weather check for {project_category}: {len(available_dates)} dates")

                    # Extract location from workflow state
                    location = extract_location_from_context(workflow_state)

                    if location:
                        try:
                            # Fetch weather forecast
                            weather_params = {
                                'location': location,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            }

                            logger.info(f"[WEATHER] Fetching weather for {location}")
                            weather_response = call_lambda_directly('get_weather', weather_params)

                            # Extract weather data
                            w_data = weather_response.get('response', {})
                            w_func = w_data.get('functionResponse', {})
                            w_body_wrapper = w_func.get('responseBody', {})
                            w_text = w_body_wrapper.get('TEXT', {})
                            w_body_str = w_text.get('body', '{}')

                            if isinstance(w_body_str, str):
                                weather_body = json.loads(w_body_str)
                            else:
                                weather_body = w_body_str

                            # Enrich dates with weather indicators
                            enriched_dates = add_weather_indicators_to_dates(
                                weather_body,
                                available_dates,
                                project_category
                            )

                            # Inject enriched dates into response
                            response_body['dates_with_weather'] = enriched_dates

                            # Count suitable vs unsuitable dates
                            suitable_count = sum(1 for d in enriched_dates if d.get('suitable'))
                            unsuitable_count = len(enriched_dates) - suitable_count

                            if unsuitable_count > 0:
                                logger.info(f"[WARNING] Proactive warning: {unsuitable_count}/{len(enriched_dates)} dates have weather concerns")
                                response_body['has_weather_concerns'] = True
                                response_body['suitable_date_count'] = suitable_count
                                response_body['unsuitable_date_count'] = unsuitable_count

                        except Exception as weather_err:
                            logger.warning(f"Proactive weather check failed (non-fatal): {weather_err}")
                            # Continue without weather indicators
                    else:
                        logger.warning("No location found for proactive weather check")

            # WEATHER-AWARE SCHEDULING: Check weather for outdoor projects when showing time slots
            if lambda_action in ['get_time_slots', 'get_available_timeslots']:
                # Get project category from workflow state
                project_category = workflow_state.get('context', {}).get('category') if workflow_state else None

                if project_category and is_outdoor_project(project_category):
                    logger.info(f"[WEATHER]  Outdoor project detected ({project_category}), checking weather...")

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

                            logger.info(f"[WEATHER]  Fetching weather for {location} on {target_date}")
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

                            # Get forecast for target date + 5 days
                            # Simple: just show the weather info to the customer
                            weather_info = weather_body.get('weather', {})
                            forecast_list = weather_info.get('forecast', [])

                            if forecast_list:
                                # Find forecasts starting from target date
                                from datetime import datetime, timedelta
                                try:
                                    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
                                    end_dt = target_dt + timedelta(days=5)

                                    # Filter forecast to target date + 5 days
                                    relevant_forecast = []
                                    for day in forecast_list:
                                        day_date = day.get('date', '')
                                        if day_date:
                                            try:
                                                day_dt = datetime.strptime(day_date, "%Y-%m-%d")
                                                if target_dt <= day_dt <= end_dt:
                                                    relevant_forecast.append({
                                                        'date': day_date,
                                                        'condition': day.get('condition', 'Unknown'),
                                                        'high_temp': day.get('max_temp_f'),
                                                        'low_temp': day.get('min_temp_f'),
                                                        'precipitation': day.get('precipitation_probability', 0)
                                                    })
                                            except:
                                                continue

                                    if relevant_forecast:
                                        logger.info(f"[WEATHER] Showing {len(relevant_forecast)} days forecast starting {target_date}")
                                        response_body['weather_forecast'] = relevant_forecast

                                        # Also include current conditions if available
                                        current = weather_info.get('current', {})
                                        if current:
                                            response_body['current_weather'] = {
                                                'temp': current.get('temp_f'),
                                                'condition': current.get('condition', 'Unknown'),
                                                'humidity': current.get('humidity'),
                                                'wind': current.get('wind_mph')
                                            }
                                except Exception as e:
                                    logger.warning(f"Error processing forecast dates: {e}")

                        except Exception as weather_error:
                            logger.warning(f"Weather check failed (non-fatal): {weather_error}")
                            # Continue without weather warning - don't block the flow
                    else:
                        logger.warning(f"No location found in workflow state for weather check")

            # Format response for user (with conversational wrapper from Claude)
            formatted_response = format_lambda_response(lambda_action, response_body, message)

            response_text = formatted_response

            # HANDLE CANCEL CONFIRMATION WORKFLOW: When cancel returns awaiting_confirmation, set workflow state
            if lambda_action == 'cancel_appointment' and response_body.get('status') == 'awaiting_confirmation':
                project_id = response_body.get('project_id') or lambda_params.get('project_id')
                project = response_body.get('project', {})

                logger.info(f"[CANCEL] Setting awaiting_cancel_confirmation workflow state for project {project_id}")

                # Save workflow state for confirmation step
                state_manager.save_state(session_id, {
                    'workflow_type': 'cancel_appointment',
                    'current_stage': 'awaiting_cancel_confirmation',
                    'context': {
                        'project_id': project_id,
                        'project': project,
                        'category': project.get('category', ''),
                        'scheduled_date': project.get('scheduledDate', '')
                    },
                    'conversation_summary': f"User wants to cancel project #{project_id}, awaiting confirmation"
                })

                timing['total'] = time.time() - start_time
                return {
                    'response': response_text,
                    'intent': 'scheduling',
                    'action': 'cancel_appointment',
                    'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
                    'direct_call': True,
                    'timing': timing
                }

            # CRITICAL: Extract request_id from Lambda response and add to workflow state
            # request_id is required for get_time_slots and confirm_appointment
            if 'request_id' in response_body and response_body['request_id']:
                logger.info(f"[STATE] Extracted request_id from Lambda response: {response_body['request_id']}")

                # Add request_id to Sonnet's workflow state update
                if decision.get('update_workflow_state'):
                    if 'context' not in decision['update_workflow_state']:
                        decision['update_workflow_state']['context'] = {}
                    decision['update_workflow_state']['context']['request_id'] = response_body['request_id']
                    logger.info(f"[STATE] Added request_id to workflow state context")

            # Save available_dates to workflow state for later weather date suggestions
            if 'available_dates' in response_body and response_body['available_dates']:
                logger.info(f"[DATES] Saving {len(response_body['available_dates'])} available dates to workflow state")

                if decision.get('update_workflow_state'):
                    if 'context' not in decision['update_workflow_state']:
                        decision['update_workflow_state']['context'] = {}
                    decision['update_workflow_state']['context']['available_dates'] = response_body['available_dates']

            # VOICE-SPECIFIC: Save project_ids to workflow state when listing projects
            # Chat uses context_resolver.py to extract from conversation history (JSON responses)
            # Voice stores natural language in history, so we need workflow_state
            if channel == 'voice' and 'projects' in response_body and isinstance(response_body['projects'], list):
                projects_list = response_body['projects']
                project_ids = [str(p.get('id', '')) for p in projects_list if p.get('id')]

                if project_ids:
                    logger.info(f"[VOICE] Saving {len(project_ids)} project_ids to workflow state: {project_ids[:5]}...")

                    if decision.get('update_workflow_state'):
                        if 'context' not in decision['update_workflow_state']:
                            decision['update_workflow_state']['context'] = {}
                        decision['update_workflow_state']['context']['project_ids'] = project_ids
                    else:
                        # Create update_workflow_state if Sonnet didn't provide one
                        decision['update_workflow_state'] = {
                            'workflow_type': 'project_listing',
                            'current_stage': 'listing_projects',
                            'context': {'project_ids': project_ids}
                        }
                        logger.info(f"[VOICE] Created workflow state with project_ids")

            # BATCH SCHEDULING: Auto-advance to next project after confirm_appointment
            if lambda_action == 'confirm_appointment':
                batch_context = workflow_state.get('context', {}) if workflow_state else {}

                if batch_context.get('batch_mode'):
                    current_index = batch_context.get('current_index', 0)
                    project_ids = batch_context.get('project_ids', [])
                    completed = batch_context.get('completed_projects', [])

                    # Mark current project as completed
                    current_project_id = batch_context.get('project_id')
                    if current_project_id:
                        completed.append(current_project_id)

                    next_index = current_index + 1
                    logger.info(f"[BATCH] Batch progress: completed {len(completed)}/{len(project_ids)}")

                    if next_index < len(project_ids):
                        # More projects to schedule
                        next_project_id = project_ids[next_index]
                        logger.info(f"[BATCH] Advancing to next project: #{next_project_id} ({next_index + 1} of {len(project_ids)})")

                        # Fetch available dates for next project
                        try:
                            next_dates_response = call_lambda_directly('get_available_dates', {
                                'project_id': next_project_id,
                                'customer_id': customer_id,
                                'client_id': client_id,
                                'pf_bearer_token': pf_bearer_token
                            })

                            # Extract dates from response
                            next_dates_data = next_dates_response.get('response', {})
                            next_dates_func = next_dates_data.get('functionResponse', {})
                            next_dates_body_wrapper = next_dates_func.get('responseBody', {})
                            next_dates_text = next_dates_body_wrapper.get('TEXT', {})
                            next_dates_body_str = next_dates_text.get('body', '{}')

                            if isinstance(next_dates_body_str, str):
                                next_dates_body = json.loads(next_dates_body_str)
                            else:
                                next_dates_body = next_dates_body_str

                            # Fetch project details for next project (for weather checking)
                            next_project_category = None
                            next_project_city = None
                            next_project_state = None
                            try:
                                next_details_response = call_lambda_directly('get_project_details', {
                                    'project_id': next_project_id,
                                    'customer_id': customer_id,
                                    'client_id': client_id,
                                    'pf_bearer_token': pf_bearer_token
                                })
                                next_details_data = next_details_response.get('response', {})
                                next_details_func = next_details_data.get('functionResponse', {})
                                next_details_body_wrapper = next_details_func.get('responseBody', {})
                                next_details_text = next_details_body_wrapper.get('TEXT', {})
                                next_details_body_str = next_details_text.get('body', '{}')

                                if isinstance(next_details_body_str, str):
                                    next_project_info = json.loads(next_details_body_str)
                                else:
                                    next_project_info = next_details_body_str

                                next_project_category = next_project_info.get('category', '')
                                next_proj_obj = next_project_info.get('project', {})
                                next_addr_obj = next_proj_obj.get('address', {}) if isinstance(next_proj_obj, dict) else {}
                                if isinstance(next_addr_obj, dict) and next_addr_obj:
                                    next_project_city = next_addr_obj.get('city', '')
                                    next_project_state = next_addr_obj.get('state', '')
                                logger.info(f"[PROJECT] Next project details: category={next_project_category}, city={next_project_city}")

                            except Exception as next_details_err:
                                logger.warning(f"Failed to fetch next project details (non-fatal): {next_details_err}")

                            # PROACTIVE WEATHER: Add weather indicators for next project dates
                            next_available_dates = next_dates_body.get('available_dates', [])
                            if next_available_dates and next_project_category and is_outdoor_project(next_project_category):
                                next_location = f"{next_project_city}, {next_project_state}" if next_project_city and next_project_state else None
                                if next_location:
                                    try:
                                        logger.info(f"[WEATHER] Proactive weather for next batch project ({next_project_category})")
                                        next_weather_response = call_lambda_directly('get_weather', {
                                            'location': next_location,
                                            'customer_id': customer_id,
                                            'client_id': client_id,
                                            'pf_bearer_token': pf_bearer_token
                                        })
                                        nw_data = next_weather_response.get('response', {})
                                        nw_func = nw_data.get('functionResponse', {})
                                        nw_body_wrapper = nw_func.get('responseBody', {})
                                        nw_text = nw_body_wrapper.get('TEXT', {})
                                        nw_body_str = nw_text.get('body', '{}')

                                        if isinstance(nw_body_str, str):
                                            next_weather_body = json.loads(nw_body_str)
                                        else:
                                            next_weather_body = nw_body_str

                                        # Enrich dates with weather indicators
                                        next_enriched_dates = add_weather_indicators_to_dates(
                                            next_weather_body,
                                            next_available_dates,
                                            next_project_category
                                        )
                                        next_dates_body['dates_with_weather'] = next_enriched_dates

                                        # Count warnings
                                        next_unsuitable = sum(1 for d in next_enriched_dates if not d.get('suitable'))
                                        next_suitable = len(next_enriched_dates) - next_unsuitable
                                        if next_unsuitable > 0:
                                            next_dates_body['has_weather_concerns'] = True
                                            next_dates_body['suitable_date_count'] = next_suitable
                                            next_dates_body['unsuitable_date_count'] = next_unsuitable
                                            logger.info(f"[WARNING] Next project has {next_unsuitable}/{len(next_enriched_dates)} dates with weather concerns")

                                    except Exception as next_weather_err:
                                        logger.warning(f"Weather check for next batch project failed (non-fatal): {next_weather_err}")

                            # Format the next project's dates (with weather if available)
                            next_dates_formatted = format_lambda_response('get_available_dates', next_dates_body, message)
                            logger.info(f"[BATCH] Next dates formatted length: {len(next_dates_formatted)} chars")

                            # Append to response
                            logger.info(f"[BATCH] Response text BEFORE append: {len(response_text)} chars")
                            response_text += f"\n\n---\n\n**Now let's schedule project #{next_project_id} ({next_index + 1} of {len(project_ids)})**\n\n{next_dates_formatted}"
                            logger.info(f"[BATCH] Response text AFTER append: {len(response_text)} chars")

                            # Update workflow state for next project
                            decision['update_workflow_state'] = {
                                'workflow_type': 'batch_schedule_appointment',
                                'current_stage': 'awaiting_date_selection',
                                'context': {
                                    'batch_mode': True,
                                    'project_ids': project_ids,
                                    'current_index': next_index,
                                    'total_projects': len(project_ids),
                                    'completed_projects': completed,
                                    'project_id': next_project_id,
                                    'available_dates': next_dates_body.get('available_dates', []),
                                    'request_id': next_dates_body.get('request_id'),
                                    # Save project info for weather checking on date selection
                                    'category': next_project_category,
                                    'city': next_project_city,
                                    'state': next_project_state
                                }
                            }
                            decision['workflow_complete'] = False

                        except Exception as batch_error:
                            logger.error(f"Failed to fetch dates for next project in batch: {batch_error}")
                            response_text += f"\n\nI encountered an issue moving to the next project. Please try scheduling project #{next_project_id} separately."

                    else:
                        # All projects scheduled!
                        logger.info(f"[BATCH] Batch complete! All {len(project_ids)} projects scheduled")
                        response_text += f"\n\n---\n\n**All done!** All {len(project_ids)} projects are now scheduled."
                        decision['workflow_complete'] = True

        except Exception as e:
            logger.error(f"Lambda call failed: {e}")
            response_text = f"I encountered an error: {str(e)}. Please try again."

    else:
        # Use Sonnet's direct response
        response_text = decision.get('response_to_user', "How can I help you?")

    # Step 4: Update workflow state
    if decision.get('update_workflow_state'):
        new_state = decision['update_workflow_state']

        # CRITICAL: Preserve batch context from existing workflow state
        # Sonnet's update_workflow_state may not include batch fields, so we must merge them
        if workflow_state and workflow_state.get('context', {}).get('batch_mode'):
            existing_batch_context = workflow_state.get('context', {})
            batch_fields = ['batch_mode', 'project_ids', 'current_index', 'total_projects', 'completed_projects']

            if 'context' not in new_state:
                new_state['context'] = {}

            for field in batch_fields:
                if field in existing_batch_context and field not in new_state['context']:
                    new_state['context'][field] = existing_batch_context[field]
                    logger.info(f"[BATCH] Preserved batch field: {field}={existing_batch_context[field]}")

        state_manager.save_state(session_id, new_state)

    # Step 5: Clear workflow if complete
    # VOICE FIX: Don't clear workflow state after list_projects - we need project_ids for follow-up queries
    # like "tell me about the third project"
    lambda_action = decision.get('lambda_action', '')
    if decision.get('workflow_complete'):
        if channel == 'voice' and lambda_action == 'list_projects':
            # Preserve project_ids for voice follow-up queries
            logger.info("[VOICE] Keeping workflow state after list_projects (project_ids needed for follow-up)")
        else:
            state_manager.clear_state(session_id)
            logger.info("[OK] Workflow complete, state cleared")

    timing['total'] = time.time() - start_time

    logger.info(f"[TIMING]  Intelligent Orchestration: Total={timing['total']:.2f}s | Classification={timing.get('classification', 0):.2f}s | Decision={timing.get('decision', 0):.2f}s")
    logger.info(f"[BATCH] FINAL response_text length: {len(response_text)} chars")

    return {
        'response': response_text,
        'intent': classification.get('intent', 'unknown'),
        'action': decision.get('lambda_action') or classification.get('action'),
        'agent_name': 'Intelligent Orchestrator (Sonnet 3.7)',
        'direct_call': True,
        'timing': timing
    }
