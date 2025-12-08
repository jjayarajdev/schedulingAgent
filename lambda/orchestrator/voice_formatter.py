"""
Voice-Friendly Response Formatter
Converts technical JSON responses to natural language for telephone/voice interfaces

DESIGN PRINCIPLE (from Chad's feedback):
- Be DIRECT like ChatGPT - no filler phrases
- SHORT responses - 1-2 sentences max
- NO "um", "hmm", "let me check" - just answer
- NO "Great!", "Good news!" - just answer
- Sound natural but EFFICIENT

SSML FEATURES:
- <speak>...</speak> wrapper for all voice output
- <break time="..."/> for natural pauses
- <prosody rate="slow"> for critical info (dates, times, addresses)
- <prosody pitch="high"> for questions
"""
import json
import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger()


# ============================================================================
# SSML HELPER FUNCTIONS
# ============================================================================

def _ssml_break(ms: int = 300) -> str:
    """Insert a pause. Default 300ms."""
    return f'<break time="{ms}ms"/>'


def _ssml_slow(text: str) -> str:
    """Slow down speech for important info (dates, addresses, numbers)."""
    return f'<prosody rate="slow">{text}</prosody>'


def _ssml_question(text: str) -> str:
    """Add slight pitch rise for questions."""
    return f'<prosody pitch="+5%">{text}</prosody>'


def _wrap_ssml(text: str) -> str:
    """Wrap text in <speak> tags for SSML output."""
    # Clean up any existing speak tags
    text = re.sub(r'</?speak>', '', text)
    # Escape special characters that could break SSML
    text = text.replace('&', '&amp;')
    # Don't double-escape already escaped entities
    text = re.sub(r'&amp;(amp|lt|gt|quot|apos);', r'&\1;', text)
    return f'<speak>{text}</speak>'


def _is_ssml(text: str) -> bool:
    """Check if text is already SSML formatted."""
    return text.strip().startswith('<speak>')


# ============================================================================
# CASUAL LANGUAGE REPLACEMENTS
# Convert formal language to contractions (keeps it natural but brief)
# ============================================================================
CASUAL_REPLACEMENTS = {
    # Contractions only - no filler phrases
    "I am": "I'm",
    "you are": "you're",
    "you have": "you've",
    "we will": "we'll",
    "let us": "let's",
    "that is": "that's",
    "there are": "there's",
    "I have": "I've",
    "do not": "don't",
    "cannot": "can't",
    "will not": "won't",
    "it is": "it's",
    "is not": "isn't",
    "are not": "aren't",
    "would not": "wouldn't",
    "could not": "couldn't",
    # Simplify corporate speak
    "I would be happy to": "I can",
    "I am unable to": "I can't",
    "Unfortunately": "Sorry,",
    "I apologize": "Sorry",
}


def _casualize_language(text: str) -> str:
    """Apply contractions to make text sound natural."""
    for formal, casual in CASUAL_REPLACEMENTS.items():
        text = re.sub(rf'\b{re.escape(formal)}\b', casual, text, flags=re.IGNORECASE)
    return text


def format_for_voice(response_text: str, intent: str = 'unknown', use_ssml: bool = True) -> str:
    """
    Convert response to natural, DIRECT speech with SSML support.

    Design: Be like ChatGPT - direct, efficient, no filler.
    - No "um", "hmm", "let me check"
    - No "Great!", "Good news!"
    - Short responses (1-2 sentences)
    - Just answer the question

    SSML Features:
    - <speak>...</speak> wrapper for all voice output
    - <break time="..."/> for natural pauses
    - <prosody rate="slow"> for critical info (dates, times, addresses)
    - <prosody pitch="+5%"> for questions

    Args:
        response_text: Raw response from agent or Lambda
        intent: Intent type (scheduling, information, chitchat)
        use_ssml: Whether to wrap output in SSML tags (default True)

    Returns:
        Voice-friendly text wrapped in SSML <speak> tags
    """
    try:
        # Step 1: Try to detect and parse JSON
        if _is_json(response_text):
            parsed = json.loads(response_text)

            # Handle different JSON structures
            if 'projects' in parsed:
                voice_text = _format_projects_for_voice(parsed)
            elif 'project' in parsed:
                voice_text = _format_project_details_for_voice(parsed)
            elif 'available_dates' in parsed:
                voice_text = _format_dates_for_voice(parsed)
            elif 'time_slots' in parsed:
                voice_text = _format_time_slots_for_voice(parsed)
            else:
                voice_text = _generic_json_to_voice(parsed)

            # Apply contractions
            voice_text = _casualize_language(voice_text)

            # Add follow-up if appropriate
            voice_text = _add_voice_followup(voice_text, intent)

            # Wrap in SSML if enabled
            if use_ssml and not _is_ssml(voice_text):
                voice_text = _wrap_ssml(voice_text)

            return voice_text

        # Step 2: Handle text responses
        voice_text = response_text

        # Summarize long date lists
        voice_text = _summarize_dates_in_text(voice_text)

        # Remove markdown
        voice_text = _remove_markdown(voice_text)

        # Apply contractions
        voice_text = _casualize_language(voice_text)

        # Remove project IDs (hard to hear on phone)
        voice_text = re.sub(r'[Pp]roject\s*\(?\s*#?\d{6,}\s*\)?', 'your project', voice_text)
        voice_text = re.sub(r'#\d{6,}', '', voice_text)

        # Remove technical parenthetical content
        voice_text = re.sub(r'\([^)]*ID[^)]*\)', '', voice_text)
        voice_text = re.sub(r'\([^)]*#\d+[^)]*\)', '', voice_text)

        # Shorten to 2-3 sentences max
        sentences = re.split(r'(?<=[.!?])\s+', voice_text)
        if len(sentences) > 3:
            voice_text = ' '.join(sentences[:3])
            if not voice_text.endswith(('.', '!', '?')):
                voice_text += '.'

        # Format numbers, temps, dates for voice
        voice_text = _format_numbers_for_voice(voice_text)
        voice_text = _format_temperatures(voice_text)
        voice_text = _format_dates(voice_text)

        # Clean up whitespace
        voice_text = re.sub(r'\s+', ' ', voice_text).strip()
        voice_text = re.sub(r'\s+([.,!?])', r'\1', voice_text)

        # Cap length (~300 chars)
        if len(voice_text) > 300:
            break_point = voice_text.rfind('.', 0, 280)
            if break_point > 100:
                voice_text = voice_text[:break_point + 1]

        # Add follow-up if appropriate
        voice_text = _add_voice_followup(voice_text, intent)

        # Final cleanup
        voice_text = re.sub(r'\s+', ' ', voice_text).strip()

        # Wrap in SSML if enabled
        if use_ssml and not _is_ssml(voice_text):
            voice_text = _wrap_ssml(voice_text)

        return voice_text

    except Exception as e:
        logger.error(f"Error formatting for voice: {e}")
        error_msg = "Sorry, let me try that again."
        return _wrap_ssml(error_msg) if use_ssml else error_msg


def _add_voice_followup(text: str, intent: str) -> str:
    """
    Add follow-up question to keep conversation going.
    Only adds if response doesn't already end with a question.
    """
    # Don't add follow-up for goodbye/thank you
    if intent.lower() in ['goodbye', 'thankyou', 'thank_you', 'chitchat', 'welcome']:
        return text

    text_stripped = text.strip()

    # Don't add if already ends with question
    if text_stripped.endswith('?'):
        return text

    # Don't add if too short (might be error)
    if len(text_stripped) < 20:
        return text

    text_lower = text_stripped.lower()

    # Don't add if contains goodbye phrases
    goodbye_phrases = [
        'goodbye', 'bye', 'take care', 'have a good day',
        'thank you for calling', 'thanks for calling'
    ]
    for phrase in goodbye_phrases:
        if phrase in text_lower:
            return text

    # Don't add if already has engagement phrase
    engagement_phrases = [
        'anything else', 'would you like', 'do you want',
        'can i help', 'what else', 'is there anything', 'let me know'
    ]
    for phrase in engagement_phrases:
        if phrase in text_lower:
            return text

    # Add simple follow-up
    if not text_stripped.endswith('.'):
        text_stripped += '.'

    return text_stripped + " Anything else?"


def _summarize_dates_in_text(text: str) -> str:
    """Summarize long date lists for voice."""
    text_lower = text.lower()

    # Check if this is about dates
    date_indicators = [
        'available date', 'dates available', 'scheduling option',
        'dates for your project', 'following dates'
    ]

    is_dates_response = any(indicator in text_lower for indicator in date_indicators)
    if not is_dates_response:
        return text

    # Extract count
    count_match = re.search(r'(\d+)\s*(?:available\s*)?dates?', text_lower)
    date_count = int(count_match.group(1)) if count_match else None

    # Extract date range
    range_match = re.search(
        r'(?:from\s+)?(\w+\s+\d+(?:st|nd|rd|th)?)\s*(?:through|to|until|-)\s*(?:the\s+)?(\d+(?:st|nd|rd|th)?|\w+\s+\d+(?:st|nd|rd|th)?)',
        text, re.IGNORECASE
    )
    date_range = None
    if range_match:
        start_date = range_match.group(1)
        end_date = range_match.group(2)
        date_range = f"{start_date} through {end_date}"

    # Only summarize if many dates
    if date_count and date_count > 5:
        logger.info(f"[VOICE] Summarizing {date_count} dates")

        if date_range:
            return f"You've got {date_count} dates from {date_range}. Want this week, next week, or later?"
        else:
            return f"You've got {date_count} dates available. Want this week, next week, or later?"

    return text


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
    """Format project list - short and direct with SSML breaks."""
    projects = data.get('projects', [])
    count = len(projects)

    if count == 0:
        return "You don't have any projects right now."

    if count == 1:
        p = projects[0]
        category = p.get('category', 'project')
        status = p.get('status', '')
        return f"You've got one {category} project,{_ssml_break(200)} {status.lower()}."

    # Multiple - be brief with pauses between categories
    result = f"You've got {count} projects.{_ssml_break(300)} "

    # Group by category
    categories = {}
    for p in projects:
        cat = p.get('category', 'Other')
        categories[cat] = categories.get(cat, 0) + 1

    cat_parts = []
    for cat, num in list(categories.items())[:3]:
        cat_parts.append(f"{num} {cat}" if num > 1 else f"one {cat}")

    if cat_parts:
        result += f"{_ssml_break(200)}".join(cat_parts) + f".{_ssml_break(300)} "

    result += _ssml_question("Which one?")
    return result


def _format_project_details_for_voice(data: Dict) -> str:
    """Format project details - direct, no fluff, with SSML prosody for dates."""
    project = data.get('project', {})

    status = project.get('status', 'unknown')
    category = project.get('category', 'project')
    scheduled_date = project.get('scheduledDate')

    # Technician
    installer_info = project.get('installer', {})
    technician = project.get('technician', {})
    tech_name = technician.get('name') or installer_info.get('name', '')

    # Build brief response with SSML
    parts = []

    parts.append(f"Your {category} project is {status}.")

    if scheduled_date:
        # Slow down for the date - critical info
        date_str = _format_date_naturally(scheduled_date)
        parts.append(f"Scheduled for {_ssml_slow(date_str)}.")
    else:
        parts.append("Not scheduled yet.")

    if tech_name:
        parts.append(f"{_ssml_break(200)}Technician: {tech_name}.")

    return f"{_ssml_break(200)}".join(parts[:3])  # Max 3 sentences with pauses


def _format_dates_for_voice(data: Dict) -> str:
    """Format available dates - brief summary with SSML prosody for dates."""
    dates = data.get('available_dates', [])
    count = len(dates)

    if count == 0:
        return "No dates available right now."

    if count <= 3:
        # List them all with slow prosody for each date
        date_strs = [_ssml_slow(_format_date_naturally(d)) for d in dates]
        dates_text = f",{_ssml_break(200)} ".join(date_strs)
        return f"Available:{_ssml_break(200)} {dates_text}.{_ssml_break(300)} {_ssml_question('Which works?')}"

    # Many dates - summarize with slow prosody for range
    first = _ssml_slow(_format_date_naturally(dates[0]))
    last = _ssml_slow(_format_date_naturally(dates[-1]))
    return f"{count} dates from {first} to {last}.{_ssml_break(300)} {_ssml_question('Which week works?')}"


def _format_time_slots_for_voice(data: Dict) -> str:
    """Format time slots with SSML prosody."""
    slots = data.get('time_slots', [])
    count = len(slots)

    if count == 0:
        return "No time slots available."

    # List them with slow prosody for times
    times = [_ssml_slow(_format_time_naturally(s)) for s in slots[:4]]
    times_text = f",{_ssml_break(200)} ".join(times)
    return f"Available:{_ssml_break(200)} {times_text}.{_ssml_break(300)} {_ssml_question('Which time?')}"


def _generic_json_to_voice(data: Any) -> str:
    """Convert generic JSON to text."""
    if isinstance(data, dict):
        parts = []
        for key, value in list(data.items())[:3]:
            key_spoken = key.replace('_', ' ')
            if isinstance(value, (list, dict)):
                continue
            parts.append(f"{key_spoken}: {value}")
        return '. '.join(parts) + '.' if parts else "Got it."
    elif isinstance(data, list):
        return f"{len(data)} items." if data else "None."
    return str(data)


def _remove_markdown(text: str) -> str:
    """Remove markdown formatting."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'#+\s+', '', text)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    return text


def _format_numbers_for_voice(text: str) -> str:
    """Format large numbers for voice."""
    def spell_long_numbers(match):
        number = match.group(1)
        if len(number) >= 7:
            return ' '.join(number)
        return number
    return re.sub(r'\b(\d{7,})\b', spell_long_numbers, text)


def _format_temperatures(text: str) -> str:
    """Format temperatures for voice."""
    text = re.sub(r'(\d+)\s*F\b', r'\1 degrees', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d+)\s*C\b', r'\1 degrees', text, flags=re.IGNORECASE)
    return text


def _format_dates(text: str) -> str:
    """Format ISO dates naturally."""
    def format_iso_date(match):
        year, month, day = match.groups()
        return _format_date_naturally(f"{year}-{month}-{day}")
    return re.sub(r'\b(\d{4})-(\d{2})-(\d{2})\b', format_iso_date, text)


def _format_date_naturally(date_str: str) -> str:
    """Convert date string to natural language."""
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        day = dt.day
        suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        return dt.strftime(f'%B {day}{suffix}')
    except:
        return date_str


def _format_time_naturally(time_str: str) -> str:
    """Convert time to natural language."""
    try:
        from datetime import datetime
        for fmt in ['%H:%M', '%I:%M %p', '%H:%M:%S']:
            try:
                dt = datetime.strptime(time_str, fmt)
                hour = dt.hour
                minute = dt.minute

                if hour == 0:
                    return "midnight" if minute == 0 else f"12:{minute:02d} AM"
                elif hour == 12:
                    return "noon" if minute == 0 else f"12:{minute:02d} PM"
                elif hour < 12:
                    return f"{hour}:{minute:02d} AM"
                else:
                    return f"{hour-12}:{minute:02d} PM"
            except:
                continue
        return time_str
    except:
        return time_str


def is_voice_mode_enabled(session_attributes: Optional[Dict] = None) -> bool:
    """Check if voice mode is enabled."""
    if not session_attributes:
        return False

    if session_attributes.get('voice_mode') == 'true':
        return True

    channel = session_attributes.get('channel', '').lower()
    if channel in ['voice', 'connect']:
        return True

    if 'connect_contact_id' in session_attributes:
        return True

    return False


def format_response_for_channel(
    response_text: str,
    intent: str,
    session_attributes: Optional[Dict] = None,
    use_ssml: bool = True
) -> str:
    """
    Format response based on channel (voice vs text).

    For voice channels, applies SSML formatting with:
    - <speak> wrapper
    - <break> pauses for natural rhythm
    - <prosody rate="slow"> for dates, times, addresses
    - <prosody pitch="+5%"> for questions

    Args:
        response_text: Raw response text
        intent: Intent type for contextual formatting
        session_attributes: Session context (voice_mode, channel, etc.)
        use_ssml: Whether to include SSML tags (default True for voice)

    Returns:
        Formatted response (SSML for voice, plain text for chat)
    """
    if is_voice_mode_enabled(session_attributes):
        logger.info("Voice mode - formatting for voice with SSML")
        return format_for_voice(response_text, intent, use_ssml=use_ssml)
    else:
        logger.info("Text mode - keeping original")
        return response_text
