"""
Context Extraction from Conversation History
Extracts location and other contextual information from previous messages
"""
import json
import re
import logging
from typing import Optional, List, Dict

logger = logging.getLogger()


def extract_location_from_history(conversation_history: List[Dict]) -> Optional[str]:
    """
    Extract location from conversation history by looking for addresses in project data

    Args:
        conversation_history: List of conversation messages

    Returns:
        City name or None if not found
    """
    if not conversation_history:
        logger.debug("No conversation history available")
        return None

    logger.debug(f"Scanning {len(conversation_history)} messages for location...")

    # Look through recent assistant messages for project addresses
    for msg in reversed(conversation_history):
        if msg['role'] != 'assistant':
            continue

        content = msg['content']

        # Try to parse JSON responses that might contain project addresses
        try:
            # Extract JSON from markdown block or direct JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                logger.debug("Found JSON in markdown block")
            elif content.strip().startswith('{'):
                data = json.loads(content)
                logger.debug("Found direct JSON")
            else:
                continue

            # Check for project list with addresses
            if 'projects' in data and isinstance(data['projects'], list) and len(data['projects']) > 0:
                logger.debug(f"Found projects list with {len(data['projects'])} projects")
                first_project = data['projects'][0]
                if 'address' in first_project:
                    addr = first_project['address']
                    logger.debug(f"Address type: {type(addr)}, keys: {addr.keys() if isinstance(addr, dict) else 'N/A'}")
                    if isinstance(addr, dict) and 'city' in addr:
                        city = addr['city']
                        logger.info(f"✅ Extracted city from project address: {city}")
                        return city

        except (json.JSONDecodeError, KeyError, IndexError, AttributeError) as e:
            logger.debug(f"JSON parse error: {e}")
            continue

    logger.debug("No location found in conversation history")
    return None


def extract_project_context(conversation_history: List[Dict]) -> Dict:
    """
    Extract project-related context from conversation history

    Args:
        conversation_history: List of conversation messages

    Returns:
        Dictionary with extracted context (project_ids, addresses, dates, etc.)
    """
    context = {
        'project_ids': [],
        'locations': [],
        'recent_dates': [],
        'recent_times': []
    }

    if not conversation_history:
        return context

    for msg in reversed(conversation_history[-5:]):  # Check last 5 messages
        content = msg['content']

        # Extract project IDs (7-digit numbers)
        project_ids = re.findall(r'\b\d{7}\b', content)
        context['project_ids'].extend(project_ids)

        # Extract dates (various formats)
        dates = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?:, \d{4})?\b', content, re.IGNORECASE)
        context['recent_dates'].extend(dates)

        # Extract times (12-hour format)
        times = re.findall(r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b', content)
        context['recent_times'].extend(times)

    # Remove duplicates and keep most recent
    context['project_ids'] = list(dict.fromkeys(context['project_ids']))[:3]
    context['recent_dates'] = list(dict.fromkeys(context['recent_dates']))[:3]
    context['recent_times'] = list(dict.fromkeys(context['recent_times']))[:3]

    return context


def should_infer_location(message: str, conversation_history: List[Dict]) -> bool:
    """
    Determine if we should attempt location inference for weather queries

    Args:
        message: Current user message
        conversation_history: Previous conversation

    Returns:
        True if location inference should be attempted
    """
    # Check if message is a weather query
    weather_keywords = ['weather', 'forecast', 'temperature', 'rain', 'sunny', 'cloudy', 'conditions']

    message_lower = message.lower()
    is_weather_query = any(keyword in message_lower for keyword in weather_keywords)

    if not is_weather_query:
        return False

    # Check if location is already mentioned in message
    # Simple heuristic: if message has "in" or "at" followed by a word, location is explicit
    has_explicit_location = bool(re.search(r'\b(?:in|at)\s+\w+', message_lower))

    if has_explicit_location:
        logger.debug("Weather query has explicit location, skipping inference")
        return False

    # Weather query without explicit location - attempt inference
    logger.info("Weather query without explicit location - attempting inference from history")
    return True


def extract_pronoun_reference(message: str, conversation_history: List[Dict]) -> Optional[Dict]:
    """
    Detect pronouns (it, that, this) and resolve them to the most recently mentioned project

    Args:
        message: Current user message
        conversation_history: Previous conversation

    Returns:
        Dictionary with resolved project context, or None if no pronoun detected
    """
    message_lower = message.lower()

    # Check if message contains pronouns that likely refer to a project
    pronouns = ['it', 'that', 'this', 'them', 'these', 'those']
    has_pronoun = any(re.search(rf'\b{pronoun}\b', message_lower) for pronoun in pronouns)

    if not has_pronoun:
        return None

    logger.info(f"Detected pronoun reference in message: '{message}'")

    # Extract the most recently mentioned project from conversation history
    if not conversation_history:
        logger.warning("No conversation history available for pronoun resolution")
        return None

    # Look for project IDs in recent messages (working backwards)
    for msg in reversed(conversation_history):
        content = msg['content']

        # Try to extract project info from JSON responses
        try:
            # Check for JSON in markdown block or direct JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            elif content.strip().startswith('{'):
                data = json.loads(content)
            else:
                # Also try plain text extraction for project IDs
                project_ids = re.findall(r'(?:project|Project)\s+(\d{7})', content)
                if project_ids:
                    logger.info(f"Found project ID in plain text: {project_ids[0]}")
                    return {
                        'project_id': project_ids[0],
                        'source': 'plain_text'
                    }
                continue

            # Check for single project details (most specific)
            if 'project' in data and isinstance(data['project'], dict):
                project_id = data['project'].get('id')
                if project_id:
                    logger.info(f"✅ Resolved pronoun to project ID: {project_id} (from project details)")
                    return {
                        'project_id': str(project_id),
                        'project_info': data['project'],
                        'source': 'project_details'
                    }

            # Check for project list (use last mentioned project in list)
            if 'projects' in data and isinstance(data['projects'], list) and len(data['projects']) > 0:
                # Use the LAST project in the list (most recently discussed)
                last_project = data['projects'][-1]
                project_id = last_project.get('id')
                if project_id:
                    logger.info(f"✅ Resolved pronoun to project ID: {project_id} (last project in list)")
                    return {
                        'project_id': str(project_id),
                        'project_info': last_project,
                        'source': 'project_list'
                    }

        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            logger.debug(f"JSON parse error during pronoun resolution: {e}")
            continue

    logger.warning("Could not resolve pronoun - no project found in conversation history")
    return None
