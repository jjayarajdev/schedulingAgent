"""
Voice-Friendly Response Formatter
Converts technical JSON responses to natural, conversational language for telephone/voice interfaces

DESIGN PRINCIPLE:
- CONVERSATIONAL - natural human-like speech, not robotic
- Use openers: "I found...", "Here's what I see...", "Great news..."
- Use connectors: "...and it's scheduled for...", "...which is..."
- Keep responses short (1-3 sentences) but warm
- Sound like a helpful assistant, not a machine

SSML FEATURES:
- <speak><amazon:domain name="conversational">...</amazon:domain></speak> for natural voice
- <break time="..."/> for natural pauses between segments
- <prosody rate="95%"> for main body (telephone clarity)
- <prosody rate="slow"> for critical info (dates, times, addresses)
- <prosody pitch="+5%"> for questions
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
    """Wrap text in SSML with Amazon conversational domain for natural voice."""
    # Clean up any existing speak/domain tags
    text = re.sub(r'</?speak>', '', text)
    text = re.sub(r'</?amazon:domain[^>]*>', '', text)
    # Escape special characters that could break SSML
    text = text.replace('&', '&amp;')
    # Don't double-escape already escaped entities
    text = re.sub(r'&amp;(amp|lt|gt|quot|apos);', r'&\1;', text)
    # Wrap in conversational domain for natural-sounding speech (works with Joanna Neural)
    return f'<speak><amazon:domain name="conversational">{text}</amazon:domain></speak>'


def _is_ssml(text: str) -> bool:
    """Check if text is already SSML formatted."""
    return text.strip().startswith('<speak>')


def _ssml_body(text: str) -> str:
    """Wrap body text at 95% rate for telephone clarity."""
    return f'<prosody rate="95%">{text}</prosody>'


# ============================================================================
# CONVERSATIONAL OPENERS - Natural phrases to start responses
# ============================================================================
CONVERSATIONAL_OPENERS = {
    'list_projects': "I found",
    'project_details': "Here's what I found.",
    'available_dates': "Great news,",
    'time_slots': "I found some times for you.",
    'scheduling': "I can help with that.",
    'confirmation': "All set!",
    'cancellation': "I've taken care of that.",
    'default': "Here's what I found.",
}


def _get_opener(context_type: str) -> str:
    """Get a conversational opener for the context type."""
    return CONVERSATIONAL_OPENERS.get(context_type.lower(), CONVERSATIONAL_OPENERS['default'])


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
    Convert response to natural, CONVERSATIONAL speech with SSML support.

    Design: Sound like a friendly, helpful assistant.
    - Use conversational openers: "I found...", "Here's what I see..."
    - Use natural connectors: "...and it's scheduled for..."
    - Keep responses ultra-short (1-2 sentences, ~200 chars max)
    - Sound human, not robotic

    SSML Features:
    - <speak><amazon:domain name="conversational">...</amazon:domain></speak> wrapper
    - <prosody rate="95%"> for main body (telephone clarity)
    - <break time="..."/> for natural pauses between segments
    - <prosody rate="slow"> for critical info (dates, times, addresses)
    - <prosody pitch="+5%"> for questions

    Args:
        response_text: Raw response from agent or Lambda
        intent: Intent type (scheduling, information, chitchat)
        use_ssml: Whether to wrap output in SSML tags (default True)

    Returns:
        Voice-friendly text wrapped in SSML with conversational domain
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

            # Apply body prosody for telephone clarity (95% rate)
            voice_text = _ssml_body(voice_text)

            # Wrap in SSML with conversational domain
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

        # Shorten to 2 sentences max for voice
        sentences = re.split(r'(?<=[.!?])\s+', voice_text)
        if len(sentences) > 2:
            voice_text = ' '.join(sentences[:2])
            if not voice_text.endswith(('.', '!', '?')):
                voice_text += '.'

        # Format numbers, temps, dates for voice
        voice_text = _format_numbers_for_voice(voice_text)
        voice_text = _format_temperatures(voice_text)
        voice_text = _format_dates(voice_text)

        # Clean up whitespace
        voice_text = re.sub(r'\s+', ' ', voice_text).strip()
        voice_text = re.sub(r'\s+([.,!?])', r'\1', voice_text)

        # Cap length (~200 chars for voice brevity)
        if len(voice_text) > 200:
            break_point = voice_text.rfind('.', 0, 180)
            if break_point > 80:
                voice_text = voice_text[:break_point + 1]

        # Add follow-up if appropriate
        voice_text = _add_voice_followup(voice_text, intent)

        # Final cleanup
        voice_text = re.sub(r'\s+', ' ', voice_text).strip()

        # Apply body prosody for telephone clarity (95% rate)
        voice_text = _ssml_body(voice_text)

        # Wrap in SSML with conversational domain
        if use_ssml and not _is_ssml(voice_text):
            voice_text = _wrap_ssml(voice_text)

        return voice_text

    except Exception as e:
        logger.error(f"Error formatting for voice: {e}")
        error_msg = "I'm sorry, I had trouble with that. Could you try again?"
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


def _format_type_naturally(project_type: str) -> str:
    """Format project type with natural article (a/an)."""
    if not project_type:
        return ""
    article = "an" if project_type[0].lower() in 'aeiou' else "a"
    return f", it's {article} {project_type}"


def _format_projects_for_voice(data: Dict) -> str:
    """Format project list - conversational with SSML breaks."""
    projects = data.get('projects', [])
    count = len(projects)

    if count == 0:
        return "I don't see any projects linked to your phone number. If you received a text or call about an appointment, you may be calling from a different number than we have on file. Would you like me to give you the office number so they can help you directly?"

    if count == 1:
        p = projects[0]
        category = p.get('category', 'project')
        project_type = p.get('projectType', '')
        status = p.get('status', '')
        type_phrase = _format_type_naturally(project_type)
        return f"{_get_opener('list_projects')} one {category} project for you{type_phrase},{_ssml_break(200)} and it's {status.lower()}."

    # Multiple - conversational with pauses between categories and types
    result = f"{_get_opener('list_projects')} {count} projects for you.{_ssml_break(300)} "

    # Group by category with type info
    cat_type_info = {}
    for p in projects:
        cat = p.get('category', 'Other')
        ptype = p.get('projectType', '')
        if cat not in cat_type_info:
            cat_type_info[cat] = {'count': 0, 'types': set()}
        cat_type_info[cat]['count'] += 1
        if ptype:
            cat_type_info[cat]['types'].add(ptype)

    cat_parts = []
    for cat, info in list(cat_type_info.items())[:3]:
        num = info['count']
        types = list(info['types'])
        if num > 1:
            cat_parts.append(f"{num} {cat}")
        elif types:
            # Single project with type - mention it naturally
            cat_parts.append(f"one {cat}, {'an' if types[0][0].lower() in 'aeiou' else 'a'} {types[0]}")
        else:
            cat_parts.append(f"one {cat}")

    if cat_parts:
        result += "That includes " + f",{_ssml_break(200)} ".join(cat_parts) + f".{_ssml_break(300)} "

    result += _ssml_question("Which one would you like to hear about?")
    return result


def _format_project_details_for_voice(data: Dict) -> str:
    """Format project details - conversational with SSML prosody for dates."""
    project = data.get('project', {})

    status = project.get('status', 'unknown')
    category = project.get('category', 'project')
    project_type = project.get('projectType', '')
    scheduled_date = project.get('scheduledDate')

    # Technician
    installer_info = project.get('installer', {})
    technician = project.get('technician', {})
    tech_name = technician.get('name') or installer_info.get('name', '')

    # Format type naturally
    type_phrase = _format_type_naturally(project_type)

    # Build conversational response with SSML
    result = f"{_get_opener('project_details')}{_ssml_break(200)} "
    result += f"Your {category} project{type_phrase}"

    # Only show scheduled date if status indicates it's actually scheduled
    status_lower = status.lower() if status else ''
    is_scheduled = status_lower in ['scheduled', 'customer scheduled', 'tentatively scheduled']

    if is_scheduled and scheduled_date:
        # Use connector and slow down for the date - critical info
        date_str = _format_date_naturally(scheduled_date)
        result += f" is scheduled for {_ssml_slow(date_str)}."
    elif status_lower in ['ready to schedule', 'new', 'ready']:
        result += " is ready to schedule."
    else:
        result += f" is {status}."

    if tech_name:
        result += f"{_ssml_break(200)} Your technician will be {tech_name}."

    return result


def _format_dates_for_voice(data: Dict) -> str:
    """Format available dates - conversational with SSML prosody for dates."""
    dates = data.get('available_dates', [])
    count = len(dates)
    auto_expanded = data.get('auto_expanded', False)
    circuit_breaker = data.get('circuit_breaker_triggered', False)

    if count == 0:
        # Priority 1: Circuit breaker triggered (repeated "no dates" in same session)
        if circuit_breaker:
            return "Our schedule is quite full right now. Would you like me to check a specific date you have in mind, or would you prefer to call our office to speak with someone who can help?"
        # Priority 2: Auto-expansion already tried (checked 14 days)
        if auto_expanded:
            return "I'm sorry, our schedule is quite full for the next two weeks. Would you like me to check a specific date you have in mind, or would you prefer to speak with someone from our scheduling team?"
        # First time - generic message (auto-expand will happen on backend)
        return "I'm sorry, there aren't any dates available right now."

    if count <= 3:
        # List them all with slow prosody for each date
        date_strs = [_ssml_slow(_format_date_naturally(d)) for d in dates]
        dates_text = f",{_ssml_break(200)} ".join(date_strs)
        return f"{_get_opener('available_dates')} I found {count} dates available.{_ssml_break(200)} You can choose from {dates_text}.{_ssml_break(300)} {_ssml_question('Which one works best for you?')}"

    # Many dates - summarize with slow prosody for range
    first = _ssml_slow(_format_date_naturally(dates[0]))
    last = _ssml_slow(_format_date_naturally(dates[-1]))
    return f"{_get_opener('available_dates')} I found {count} dates for you,{_ssml_break(200)} from {first} to {last}.{_ssml_break(300)} {_ssml_question('Would you prefer this week, next week, or later?')}"


def _format_time_slots_for_voice(data: Dict) -> str:
    """Format time slots with conversational style and SSML prosody."""
    slots = data.get('time_slots', [])
    count = len(slots)

    if count == 0:
        return "I'm sorry, there aren't any time slots available for that date."

    # List them with slow prosody for times
    times = [_ssml_slow(_format_time_naturally(s)) for s in slots[:4]]
    times_text = f",{_ssml_break(200)} ".join(times)
    return f"{_get_opener('time_slots')}{_ssml_break(200)} You can choose from {times_text}.{_ssml_break(300)} {_ssml_question('Which time works best?')}"


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


# ============================================================================
# CONTEXT-AWARE VOICE FORMATTING (Voice Enhancement)
# ============================================================================

def format_voice_with_context(
    response_text: str,
    action: str,
    voice_context: Optional[Dict] = None,
    use_ssml: bool = True
) -> str:
    """
    Format response with conversation context awareness.

    VOICE-ONLY: This function applies intelligent context-aware formatting
    based on what just happened in the conversation.

    Context-Aware Rules:
    1. POST_ACTION: After scheduling, lead with celebration, suggest next action
    2. REMINDER: If appointment is today/tomorrow, mention it first
    3. BRIEF: If we already told them about projects, don't repeat full list
    4. RETURNING: Welcome back, reference last interaction

    Args:
        response_text: Raw response from Lambda
        action: The action that was just performed
        voice_context: Enriched context from build_voice_context()
        use_ssml: Whether to include SSML tags

    Returns:
        Context-aware, SSML-formatted voice response
    """
    if not voice_context:
        # No context - use standard formatting
        return format_for_voice(response_text, action, use_ssml=use_ssml)

    try:
        from response_context import ConversationState, get_response_rules, summarize_projects_by_status

        rules = get_response_rules(voice_context)
        final_text = ""

        # Rule 1: Lead with reminder if appointment is today/tomorrow
        if rules.get('lead_with_reminder') and rules.get('reminder_text'):
            final_text = rules['reminder_text'] + f"{_ssml_break(400)} "
            logger.info("[VOICE_CTX] Adding proactive reminder to response")

        # Rule 2: Celebration mode after successful action
        if rules.get('celebration_mode'):
            last_action = voice_context.get('last_action')
            last_project = voice_context.get('last_project_name', 'your project')

            if last_action == 'confirm_appointment':
                # Response already has confirmation - just add context-aware follow-up
                logger.info("[VOICE_CTX] Post-scheduling celebration mode")

        # Rule 3: Use brief format if many projects already mentioned
        if rules.get('use_brief_format'):
            # Summarize instead of listing
            logger.info("[VOICE_CTX] Using brief format (many projects mentioned)")

        # Add the main response
        final_text += response_text

        # Rule 4: Add contextual next action suggestion
        if rules.get('suggest_next_action') and rules.get('next_action_text'):
            if not final_text.rstrip().endswith('?'):
                final_text = final_text.rstrip()
                if not final_text.endswith('.'):
                    final_text += '.'
                final_text += f"{_ssml_break(300)} {rules['next_action_text']}"
                logger.info("[VOICE_CTX] Added next action suggestion")

        # Apply standard voice formatting
        return format_for_voice(final_text, action, use_ssml=use_ssml)

    except Exception as e:
        logger.warning(f"Context-aware formatting failed (falling back to standard): {e}")
        return format_for_voice(response_text, action, use_ssml=use_ssml)


def format_projects_summary_for_voice(projects: List[Dict], voice_context: Optional[Dict] = None) -> str:
    """
    Format project list with intelligent summarization for voice.

    Instead of listing all 10 projects:
    - Summarize by status: "You have 10 projects - 3 scheduled, 4 ready to schedule, 3 in progress"
    - Highlight what's actionable: "Would you like to schedule one of the ready ones?"
    - Mention upcoming appointments first if relevant

    Args:
        projects: List of project dictionaries
        voice_context: Enriched context from build_voice_context()

    Returns:
        Voice-friendly summary of projects
    """
    try:
        from response_context import summarize_projects_by_status

        summary = summarize_projects_by_status(projects)
        total = summary['total']

        if total == 0:
            return "I don't see any projects linked to your phone number. If you received a text or call about an appointment, you may be calling from a different number than we have on file. Would you like me to give you the office number so they can help you directly?"

        if total == 1:
            project = projects[0]
            category = project.get('category', 'project')
            project_type = project.get('projectType', '')
            status = (project.get('status') or '').lower()
            type_phrase = _format_type_naturally(project_type)
            return f"You have one {category} project{type_phrase}, and it's {status}."

        # Build intelligent summary
        result = f"You have {total} projects.{_ssml_break(200)} "

        # Lead with scheduled count if any
        scheduled_count = summary.get('scheduled_count', 0)
        schedulable_count = summary.get('schedulable_count', 0)

        if scheduled_count > 0:
            result += f"{scheduled_count} {'is' if scheduled_count == 1 else 'are'} already scheduled"
            if schedulable_count > 0:
                result += f", and {schedulable_count} {'is' if schedulable_count == 1 else 'are'} ready to schedule"
            result += f".{_ssml_break(300)} "
        elif schedulable_count > 0:
            result += f"{schedulable_count} {'is' if schedulable_count == 1 else 'are'} ready to schedule.{_ssml_break(300)} "

        # Add proactive suggestion
        if summary.get('has_schedulable'):
            result += _ssml_question("Would you like to schedule one?")
        else:
            result += _ssml_question("Which one would you like to hear about?")

        return result

    except Exception as e:
        logger.warning(f"Project summary formatting failed: {e}")
        # Fallback to standard formatting
        return _format_projects_for_voice({'projects': projects})
