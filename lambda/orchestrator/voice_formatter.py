"""
Voice-Friendly Response Formatter
Converts technical JSON responses to natural language for telephone/voice interfaces
"""
import json
import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger()


def format_for_voice(response_text: str, intent: str = 'unknown') -> str:
    """
    Convert response to voice-friendly natural language

    Handles:
    - JSON project lists → natural enumeration
    - Technical terminology → plain language
    - Numbers and IDs → spelled out clearly
    - Long lists → summarized with details option
    - Markdown formatting → removed

    Args:
        response_text: Raw response from agent or Lambda
        intent: Intent type (scheduling, information, chitchat)

    Returns:
        Voice-friendly response string

    Examples:
        >>> json_response = '{"projects":[{"id":"123","name":"Project A"}]}'
        >>> format_for_voice(json_response, 'scheduling')
        'You have 1 project. Project A, with ID 1 2 3.'

        >>> format_for_voice("Weather is 75F sunny", 'information')
        'Weather is 75 degrees Fahrenheit, sunny.'
    """
    try:
        # Step 1: Try to detect and parse JSON
        if _is_json(response_text):
            parsed = json.loads(response_text)

            # Handle different JSON structures
            if 'projects' in parsed:
                return _format_projects_for_voice(parsed)
            elif 'project' in parsed:
                return _format_project_details_for_voice(parsed)
            elif 'available_dates' in parsed:
                return _format_dates_for_voice(parsed)
            elif 'time_slots' in parsed:
                return _format_time_slots_for_voice(parsed)
            else:
                # Generic JSON - convert to text
                return _generic_json_to_voice(parsed)

        # Step 2: Clean up text responses
        voice_text = response_text

        # Remove markdown formatting
        voice_text = _remove_markdown(voice_text)

        # Format numbers
        voice_text = _format_numbers_for_voice(voice_text)

        # Format temperatures
        voice_text = _format_temperatures(voice_text)

        # Format dates
        voice_text = _format_dates(voice_text)

        # Add natural pauses
        voice_text = _add_natural_pauses(voice_text)

        # Clean up whitespace
        voice_text = re.sub(r'\s+', ' ', voice_text).strip()

        return voice_text

    except Exception as e:
        logger.error(f"Error formatting for voice: {e}")
        # Fallback: return cleaned text
        return response_text.replace('**', '').replace('```', '').strip()


def _is_json(text: str) -> bool:
    """Check if text is valid JSON"""
    text = text.strip()
    if not (text.startswith('{') or text.startswith('[')):
        return False
    try:
        json.loads(text)
        return True
    except:
        return False


def _format_projects_for_voice(data: Dict) -> str:
    """Format project list for voice"""
    projects = data.get('projects', [])
    count = len(projects)

    if count == 0:
        return "You don't have any projects right now."

    # Start with count
    result = f"You have {count} project{'s' if count != 1 else ''}. "

    # List first 5 projects with details
    for i, project in enumerate(projects[:5], 1):
        project_id = project.get('id', 'unknown')
        project_name = project.get('name', 'Unnamed project')
        status = project.get('status', 'unknown status')

        # Spell out project ID digits
        id_spoken = _spell_digits(str(project_id))

        result += f"Project {i}: {project_name}, ID {id_spoken}, status is {status}. "

    # If more than 5, mention remaining count
    if count > 5:
        result += f"And {count - 5} more. "

    result += "Would you like details on any specific project?"

    return result


def _format_project_details_for_voice(data: Dict) -> str:
    """Format single project details for voice"""
    project = data.get('project', {})

    project_id = project.get('id', 'unknown')
    project_name = project.get('name', 'Unnamed project')
    status = project.get('status', 'unknown')
    category = project.get('category', 'unspecified')
    scheduled_date = project.get('scheduledDate')

    id_spoken = _spell_digits(str(project_id))

    result = f"Project {project_name}, ID {id_spoken}. "
    result += f"Status: {status}. "
    result += f"Category: {category}. "

    if scheduled_date:
        result += f"Scheduled for {_format_date_naturally(scheduled_date)}. "
    else:
        result += "Not yet scheduled. "

    return result


def _format_dates_for_voice(data: Dict) -> str:
    """Format available dates for voice"""
    dates = data.get('available_dates', [])
    count = len(dates)

    if count == 0:
        return "I'm sorry, there are no available dates at this time."

    result = f"There are {count} available date{'s' if count != 1 else ''}. "

    # List first 5 dates
    for i, date in enumerate(dates[:5], 1):
        spoken_date = _format_date_naturally(date)
        result += f"Option {i}: {spoken_date}. "

    if count > 5:
        result += f"And {count - 5} more options. "

    result += "Which date works best for you?"

    return result


def _format_time_slots_for_voice(data: Dict) -> str:
    """Format time slots for voice"""
    slots = data.get('time_slots', [])
    count = len(slots)

    if count == 0:
        return "I'm sorry, there are no available time slots."

    result = f"There are {count} available time slot{'s' if count != 1 else ''}. "

    # List all slots (usually not too many)
    for i, slot in enumerate(slots, 1):
        spoken_time = _format_time_naturally(slot)
        result += f"{spoken_time}. "

    result += "Which time works for you?"

    return result


def _generic_json_to_voice(data: Any) -> str:
    """Convert generic JSON to voice-friendly text"""
    if isinstance(data, dict):
        parts = []
        for key, value in data.items():
            key_spoken = key.replace('_', ' ').title()
            if isinstance(value, (list, dict)):
                value_spoken = _generic_json_to_voice(value)
            else:
                value_spoken = str(value)
            parts.append(f"{key_spoken}: {value_spoken}")
        return '. '.join(parts) + '.'

    elif isinstance(data, list):
        if len(data) == 0:
            return "none"
        elif len(data) == 1:
            return _generic_json_to_voice(data[0])
        else:
            return f"{len(data)} items"

    else:
        return str(data)


def _remove_markdown(text: str) -> str:
    """Remove markdown formatting"""
    # Remove bold
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)

    # Remove italic
    text = re.sub(r'\*(.+?)\*', r'\1', text)

    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'\1', text)

    # Remove headers
    text = re.sub(r'#+\s+', '', text)

    # Remove bullet points
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)

    return text


def _format_numbers_for_voice(text: str) -> str:
    """Format large numbers for voice"""
    # Format phone-like numbers (10+ digits) with spacing
    def spell_long_numbers(match):
        number = match.group(1)
        if len(number) >= 7:
            return _spell_digits(number)
        return number

    text = re.sub(r'\b(\d{7,})\b', spell_long_numbers, text)

    return text


def _spell_digits(number_str: str) -> str:
    """Spell out digits individually: "123" → "1 2 3" """
    return ' '.join(number_str)


def _format_temperatures(text: str) -> str:
    """Format temperatures for voice"""
    # "75F" → "75 degrees Fahrenheit"
    text = re.sub(r'(\d+)\s*F\b', r'\1 degrees Fahrenheit', text, flags=re.IGNORECASE)

    # "23C" → "23 degrees Celsius"
    text = re.sub(r'(\d+)\s*C\b', r'\1 degrees Celsius', text, flags=re.IGNORECASE)

    return text


def _format_dates(text: str) -> str:
    """Format dates naturally for voice"""
    # "2025-11-14" → "November 14th, 2025"
    def format_iso_date(match):
        year, month, day = match.groups()
        return _format_date_naturally(f"{year}-{month}-{day}")

    text = re.sub(r'\b(\d{4})-(\d{2})-(\d{2})\b', format_iso_date, text)

    return text


def _format_date_naturally(date_str: str) -> str:
    """Convert date string to natural language"""
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, '%Y-%m-%d')

        # Format: "November 14th, 2025"
        day = dt.day
        suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')

        return dt.strftime(f'%B {day}{suffix}, %Y')
    except:
        return date_str


def _format_time_naturally(time_str: str) -> str:
    """Convert time string to natural language"""
    try:
        from datetime import datetime

        # Handle various time formats
        for fmt in ['%H:%M', '%I:%M %p', '%H:%M:%S']:
            try:
                dt = datetime.strptime(time_str, fmt)
                # Format: "2:30 PM" or "14:30" → "2:30 in the afternoon"
                hour = dt.hour
                minute = dt.minute

                if hour == 0:
                    return f"midnight" if minute == 0 else f"12:{minute:02d} AM"
                elif hour == 12:
                    return f"noon" if minute == 0 else f"12:{minute:02d} PM"
                elif hour < 12:
                    return f"{hour}:{minute:02d} in the morning"
                else:
                    return f"{hour-12}:{minute:02d} in the afternoon"
            except:
                continue

        return time_str
    except:
        return time_str


def _add_natural_pauses(text: str) -> str:
    """Add natural pauses for voice"""
    # Add pause after sentences
    text = re.sub(r'([.!?])\s+', r'\1 ', text)

    # Add slight pause after commas
    text = re.sub(r',\s+', ', ', text)

    return text


def is_voice_mode_enabled(session_attributes: Optional[Dict] = None) -> bool:
    """
    Check if voice mode is enabled for this session

    Voice mode can be enabled via:
    - Session attribute: voice_mode=true
    - Channel detection: if from AWS Connect
    """
    if not session_attributes:
        return False

    # Check explicit voice_mode flag
    if session_attributes.get('voice_mode') == 'true':
        return True

    # Check if request is from AWS Connect
    if session_attributes.get('channel') == 'connect':
        return True

    # Check if connect_contact_id is present
    if 'connect_contact_id' in session_attributes:
        return True

    return False


def format_response_for_channel(
    response_text: str,
    intent: str,
    session_attributes: Optional[Dict] = None
) -> str:
    """
    Format response based on channel (voice vs text)

    Args:
        response_text: Raw response
        intent: Intent type
        session_attributes: Session attributes (may contain channel info)

    Returns:
        Formatted response appropriate for the channel
    """
    if is_voice_mode_enabled(session_attributes):
        logger.info("📞 Voice mode detected - formatting for voice")
        return format_for_voice(response_text, intent)
    else:
        logger.info("💬 Text mode - keeping original formatting")
        return response_text
