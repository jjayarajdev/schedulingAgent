"""
Context Resolver for Multi-Turn Conversations
Resolves references like "the second one", "that project", "that day" from conversation history
"""
import json
import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger()


def resolve_context_references(
    message: str,
    conversation_history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Resolve contextual references from conversation history

    Handles:
    - Position references: "the second one", "3rd project", "last one"
    - Pronoun references: "it", "that", "this one"
    - Temporal references: "that day", "then", "at that time"
    - Implicit references: "schedule it"  extract project from previous turn

    Args:
        message: Current user message with potential references
        conversation_history: Previous conversation

    Returns:
        Dictionary with:
        - resolved_message: Message with references resolved
        - entities: Extracted entities (project_ids, dates, etc.)
        - references: List of resolved references

    Examples:
        >>> history = [{'role': 'assistant', 'content': 'Projects: A (123), B (456)'}]
        >>> resolve_context_references("show me the second one", history)
        {
            'resolved_message': 'show me project 456',
            'entities': {'project_id': '456'},
            'references': [{'type': 'position', 'original': 'second one', 'resolved': '456'}]
        }
    """
    if not conversation_history or len(conversation_history) == 0:
        return {
            'resolved_message': message,
            'entities': {},
            'references': []
        }

    entities = {}
    references = []
    resolved_message = message

    # Extract entities from conversation history
    context = _extract_context_from_history(conversation_history)

    # Resolve position references ("2nd one", "last project", "first one")
    resolved_message, position_refs = _resolve_position_references(resolved_message, context)
    references.extend(position_refs)
    entities.update({ref['entity_type']: ref['resolved'] for ref in position_refs})

    # Resolve pronoun references ("it", "that", "this")
    resolved_message, pronoun_refs = _resolve_pronoun_references(resolved_message, context)
    references.extend(pronoun_refs)
    entities.update({ref['entity_type']: ref['resolved'] for ref in pronoun_refs})

    # Resolve temporal references ("that day", "then")
    resolved_message, temporal_refs = _resolve_temporal_references(resolved_message, context)
    references.extend(temporal_refs)
    entities.update({ref['entity_type']: ref['resolved'] for ref in temporal_refs})

    # IMPLICIT CONTINUATION: If no project_id extracted yet, use last_project from context
    # This handles queries like "what dates are available?" after "show me details for project 123"
    if 'project_id' not in entities and context.get('last_project'):
        # Check if message seems scheduling-related (dates, times, schedule, book, reschedule)
        scheduling_keywords = ['date', 'time', 'slot', 'available', 'schedule', 'book', 'reschedule', 'appointment', 'when']
        if any(keyword in message.lower() for keyword in scheduling_keywords):
            entities['project_id'] = context['last_project']
            logger.info(f" Implicit continuation: Using last_project={context['last_project']} (no explicit reference)")

    if references:
        logger.info(f" Resolved {len(references)} reference(s) in message")
        for ref in references:
            logger.debug(f"  - {ref['type']}: '{ref['original']}'  '{ref['resolved']}'")

    return {
        'resolved_message': resolved_message,
        'entities': entities,
        'references': references
    }


def _extract_project_ids_from_content(content: str) -> List[str]:
    """
    Enhanced project ID extraction from conversation content

    Handles:
    - Direct JSON: {"projects": [{"id": "123"}]}
    - Nested JSON strings: {"response": "{\"projects\":[...]}"}
    - Multiple levels of nesting
    - Regex fallback for plain text

    Returns:
        List of project IDs found (in order of appearance)
    """
    project_ids = []

    # Strategy 1: Try parsing as direct JSON
    try:
        data = json.loads(content)
        project_ids.extend(_extract_ids_from_data(data))
    except:
        pass

    # Strategy 2: Look for nested JSON strings (common in Lambda responses)
    # Pattern: "response": "{...}"
    nested_json_pattern = r'"response":\s*"(\{[^"]*(?:\\"[^"]*)*\})"'
    nested_matches = re.findall(nested_json_pattern, content)

    for nested_json_str in nested_matches:
        try:
            # Unescape the JSON string
            unescaped = nested_json_str.replace('\\"', '"').replace('\\\\', '\\')
            nested_data = json.loads(unescaped)
            project_ids.extend(_extract_ids_from_data(nested_data))
        except Exception as e:
            logger.debug(f"Failed to parse nested JSON: {e}")

    # Strategy 3: Find all JSON-like structures with regex
    # Look for {"id":"7751741"} patterns
    id_pattern = r'"id":\s*"(\d{7})"'
    regex_ids = re.findall(id_pattern, content)
    project_ids.extend(regex_ids)

    # Strategy 4: Find standalone 7-digit numbers (project IDs)
    standalone_ids = re.findall(r'\b(\d{7})\b', content)
    project_ids.extend(standalone_ids)

    # Remove duplicates while preserving order
    seen = set()
    unique_ids = []
    for pid in project_ids:
        if pid not in seen:
            seen.add(pid)
            unique_ids.append(pid)

    if unique_ids:
        logger.debug(f"Extracted {len(unique_ids)} project ID(s) from content")

    return unique_ids


def _extract_ids_from_data(data: Any) -> List[str]:
    """
    Recursively extract project IDs from parsed JSON data

    Args:
        data: Parsed JSON data (dict, list, or primitive)

    Returns:
        List of project IDs found
    """
    ids = []

    if isinstance(data, dict):
        # Check for direct 'id' field
        if 'id' in data:
            id_val = str(data['id'])
            if id_val.isdigit() and len(id_val) == 7:
                ids.append(id_val)

        # Check for 'projects' array
        if 'projects' in data and isinstance(data['projects'], list):
            for project in data['projects']:
                if isinstance(project, dict) and 'id' in project:
                    id_val = str(project['id'])
                    if id_val.isdigit() and len(id_val) == 7:
                        ids.append(id_val)

        # Check for 'project' object
        if 'project' in data and isinstance(data['project'], dict):
            if 'id' in data['project']:
                id_val = str(data['project']['id'])
                if id_val.isdigit() and len(id_val) == 7:
                    ids.append(id_val)

        # Recursively check all dict values
        for value in data.values():
            ids.extend(_extract_ids_from_data(value))

    elif isinstance(data, list):
        # Recursively check list items
        for item in data:
            ids.extend(_extract_ids_from_data(item))

    return ids


def _extract_context_from_history(conversation_history: List[Dict]) -> Dict[str, Any]:
    """
    Extract entities and context from conversation history

    Returns dictionary with:
    - project_ids: ORDERED list from most recently displayed list (for positional refs like "10th project")
    - last_displayed_list: Most recent multi-project list shown to user
    - last_project: Most recently mentioned single project (for pronoun refs like "it")
    - dates: List of mentioned dates
    - times: List of mentioned times
    """
    context = {
        'project_ids': [],  # Will be set to last_displayed_list for positional references
        'last_displayed_list': None,  # Most recent list with multiple projects
        'dates': [],
        'times': [],
        'last_project': None,  # Most recently mentioned single project
        'last_date': None,
        'last_time': None
    }

    # Track all project mentions for finding the most recent single mention
    all_project_mentions = []

    # Process history in reverse (most recent first)
    for msg in reversed(conversation_history[-5:]):  # Last 5 messages
        content = msg.get('content', '')

        # Extract project IDs using enhanced JSON parsing
        project_ids_found = _extract_project_ids_from_content(content)

        # If this message has MULTIPLE projects (likely a list), save for positional refs
        if len(project_ids_found) > 1 and context['last_displayed_list'] is None:
            context['last_displayed_list'] = project_ids_found.copy()
            logger.debug(f" Found list with {len(project_ids_found)} projects for positional refs")

        # Track all individual project mentions (chronological order, newest first)
        for pid in project_ids_found:
            if pid not in all_project_mentions:
                all_project_mentions.append(pid)

        # OLD: Try JSON first - REPLACED WITH ENHANCED FUNCTION ABOVE
        # try:
        #     # Check if content contains JSON
        #     if '```json' in content:
        #         json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        #         if json_match:
        #             json_str = json_match.group(1)
        #         else:
        #             json_str = content
        #
        #         data = json.loads(json_str)
        #
        #         # Extract project IDs from JSON
        #         if 'projects' in data:
        #             for project in data['projects']:
        #                 project_id = str(project.get('id', ''))
        #                 if project_id and project_id not in context['project_ids']:
        #                     context['project_ids'].append(project_id)
        #
        #         elif 'project' in data:
        #             project_id = str(data['project'].get('id', ''))
        #             if project_id and project_id not in context['project_ids']:
        #                 context['project_ids'].append(project_id)
        #
        # except Exception as e:
        #     logger.debug(f"JSON parsing failed in history: {e}")

        # Extract dates (YYYY-MM-DD or "Nov 14", etc.)
        date_matches = re.findall(r'\b(\d{4}-\d{2}-\d{2})\b', content)
        for date in date_matches:
            if date not in context['dates']:
                context['dates'].append(date)

        # Extract times
        time_matches = re.findall(r'\b(\d{1,2}:\d{2}(?:\s*[AP]M)?)\b', content, re.IGNORECASE)
        for time in time_matches:
            if time not in context['times']:
                context['times'].append(time)

    # Set project_ids for positional references
    # Use last_displayed_list if available, otherwise use all mentions
    if context['last_displayed_list']:
        context['project_ids'] = context['last_displayed_list']
        logger.debug(f" Using last displayed list ({len(context['project_ids'])} projects) for positional refs")
    else:
        context['project_ids'] = all_project_mentions
        logger.debug(f"  No list found, using all mentions ({len(all_project_mentions)} projects)")

    # Set last_project for pronoun references ("it", "schedule it")
    # This is the most recently mentioned single project (chronologically)
    if all_project_mentions:
        context['last_project'] = all_project_mentions[0]  # First in reversed list = most recent
        logger.debug(f" last_project for pronouns: {context['last_project']}")

    # Set last date/time
    if context['dates']:
        context['last_date'] = context['dates'][0]  # First = most recent

    if context['times']:
        context['last_time'] = context['times'][0]  # First = most recent

    logger.debug(f"Context: {len(context['project_ids'])} projects in list, "
                f"last_project={context.get('last_project')}, "
                f"{len(context['dates'])} dates, {len(context['times'])} times")

    return context


def _resolve_position_references(message: str, context: Dict) -> tuple:
    """
    Resolve position references like "second one", "3rd project", "last"

    Returns: (resolved_message, list_of_references)
    """
    references = []
    resolved_message = message

    project_ids = context.get('project_ids', [])

    if not project_ids:
        return resolved_message, references

    # Pattern: "the second one", "2nd one", "second project", "the last", "first"
    patterns = [
        (r'\b(?:the\s+)?first(?:\s+one| project| item)?\b', 0),
        (r'\b(?:the\s+)?second(?:\s+one| project| item)?\b', 1),
        (r'\b(?:the\s+)?third(?:\s+one| project| item)?\b', 2),
        (r'\b(?:the\s+)?fourth(?:\s+one| project| item)?\b', 3),
        (r'\b(?:the\s+)?fifth(?:\s+one| project| item)?\b', 4),
        (r'\b(?:the\s+)?(\d+)(?:st|nd|rd|th)(?:\s+one| project| item)?\b', None),  # "3rd one"
        (r'\b(?:the\s+)?last(?:\s+one| project| item)?\b', -1)
    ]

    for pattern, index in patterns:
        match = re.search(pattern, resolved_message, re.IGNORECASE)

        if match:
            # For numeric patterns, extract the number
            if index is None:
                index = int(match.group(1)) - 1  # Convert to 0-indexed

            # Check if index is valid
            if -len(project_ids) <= index < len(project_ids):
                project_id = project_ids[index]

                # Replace reference with actual project ID
                resolved_message = resolved_message[:match.start()] + f"project {project_id}" + resolved_message[match.end():]

                references.append({
                    'type': 'position',
                    'original': match.group(0),
                    'resolved': project_id,
                    'entity_type': 'project_id'
                })

                logger.debug(f"Resolved position reference: '{match.group(0)}'  project {project_id}")

                break  # Only resolve first match

    return resolved_message, references


def _resolve_pronoun_references(message: str, context: Dict) -> tuple:
    """
    Resolve pronoun references like "it", "that", "this one"

    Returns: (resolved_message, list_of_references)
    """
    references = []
    resolved_message = message

    # Patterns: "schedule it", "book that", "show this one"
    pronoun_patterns = [
        r'\b(it)\b',
        r'\b(that)\b',
        r'\b(this)(?:\s+one)?\b'
    ]

    for pattern in pronoun_patterns:
        match = re.search(pattern, resolved_message, re.IGNORECASE)

        if match:
            # Resolve to last mentioned entity (project, date, etc.)
            if context.get('last_project'):
                project_id = context['last_project']
                resolved_message = resolved_message[:match.start()] + f"project {project_id}" + resolved_message[match.end():]

                references.append({
                    'type': 'pronoun',
                    'original': match.group(0),
                    'resolved': project_id,
                    'entity_type': 'project_id'
                })

                logger.debug(f"Resolved pronoun: '{match.group(0)}'  project {project_id}")

                break  # Only resolve first match

    return resolved_message, references


def _resolve_temporal_references(message: str, context: Dict) -> tuple:
    """
    Resolve temporal references like "that day", "then", "at that time"

    Returns: (resolved_message, list_of_references)
    """
    references = []
    resolved_message = message

    # Patterns: "that day", "then", "at that time"
    temporal_patterns = [
        r'\b(that day)\b',
        r'\b(then)\b',
        r'\b(?:at\s+)?(that time)\b'
    ]

    for pattern in temporal_patterns:
        match = re.search(pattern, resolved_message, re.IGNORECASE)

        if match:
            # Resolve to last mentioned date/time
            if 'day' in match.group(0).lower() and context.get('last_date'):
                date = context['last_date']
                resolved_message = resolved_message[:match.start()] + f"on {date}" + resolved_message[match.end():]

                references.append({
                    'type': 'temporal',
                    'original': match.group(0),
                    'resolved': date,
                    'entity_type': 'date'
                })

                logger.debug(f"Resolved temporal reference: '{match.group(0)}'  {date}")

            elif 'time' in match.group(0).lower() and context.get('last_time'):
                time = context['last_time']
                resolved_message = resolved_message[:match.start()] + f"at {time}" + resolved_message[match.end():]

                references.append({
                    'type': 'temporal',
                    'original': match.group(0),
                    'resolved': time,
                    'entity_type': 'time'
                })

                logger.debug(f"Resolved temporal reference: '{match.group(0)}'  {time}")

            break  # Only resolve first match

    return resolved_message, references


def extract_entities_from_message(message: str) -> Dict[str, Any]:
    """
    Extract explicit entities from message (without needing history)

    Extracts:
    - Project IDs (7-digit numbers)
    - Dates (various formats)
    - Times
    - Filters (status, category, projectType)

    Returns:
        Dictionary of extracted entities
    """
    entities = {}

    # Extract project IDs
    project_id_matches = re.findall(r'\b(\d{7})\b', message)
    if project_id_matches:
        entities['project_id'] = project_id_matches[0]

    # Extract dates
    date_matches = re.findall(r'\b(\d{4}-\d{2}-\d{2})\b', message)
    if date_matches:
        entities['date'] = date_matches[0]

    # Extract times
    time_matches = re.findall(r'\b(\d{1,2}:\d{2}(?:\s*[AP]M)?)\b', message, re.IGNORECASE)
    if time_matches:
        entities['time'] = time_matches[0]

    # Extract status filters
    if re.search(r'\bscheduled\b', message, re.IGNORECASE) and not re.search(r'\bready to schedule\b', message, re.IGNORECASE):
        entities['status'] = 'Scheduled'
    elif re.search(r'\bready to schedule\b', message, re.IGNORECASE):
        entities['status'] = 'Ready To Schedule'
    elif re.search(r'\bnew\b', message, re.IGNORECASE):
        entities['status'] = 'New'
    elif re.search(r'\bcompleted\b', message, re.IGNORECASE):
        entities['status'] = 'Completed'

    return entities
