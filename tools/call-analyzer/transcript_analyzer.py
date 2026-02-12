"""
Transcript Analyzer - Categorize call outcomes and detect issues
"""
import re
from typing import Dict, List, Tuple


# Outcome categories
OUTCOME_CATEGORIES = {
    'appointment_confirmed': [
        'has been submitted',
        'appointment request',
        'scheduled for',
        'confirmed for',
        'booked for',
        'submitting your request',
        'submitted your request',
        'office will review',
        'will review and update',
        'will review and confirm',
    ],
    'no_availability': [
        'no appointments are available',
        'no dates available',
        'schedule is quite full',
        "wasn't able to find any openings",
        'not finding any openings',
    ],
    'office_handoff': [
        'office number',
        'reach window treatments',
        'speak with someone directly',
        '8 6 0 2 6 9',
    ],
    'cancellation_request': [
        'cancel',
        "can't cancel",
        'not able to cancel',
    ],
    'reschedule_request': [
        'reschedule',
        'change the date',
        'different date',
        'move my appointment',
    ],
    'project_not_schedulable': [
        "can't be scheduled",
        'status is left message',
        "don't see any projects",
        'not ready to schedule',
    ],
    'ai_identity_question': [
        'are you ai',
        'is this ai',
        'are you a robot',
        'real person',
        'talking to a robot',
        'you sound so real',
    ],
}

# Issue patterns
ISSUE_PATTERNS = {
    'timeout': [
        'timeout',
        'timed out',
        'few more seconds',
    ],
    'api_error': [
        'trouble with that',
        'technical issue',
        'having trouble',
    ],
    'repeat_response': [
        # Detected by counting repeated phrases
    ],
    'customer_frustration': [
        'frustrated',
        'same conversation',
        'had this conversation before',
        'real representative',
        'how is that gonna be different',
    ],
    'check_further_loop': [
        'check further out',
        'would you like me to check further',
    ],
    'phone_number_inconsistency': [
        # Detected by analyzing phone number repetitions
    ],
    'time_format_confusion': [
        '12 11 pm',
        '12 11 am',
    ],
    'expected_call_transfer': [
        'connect me',
        'transfer me',
        'going to connect me',
    ],
}


def analyze_transcript(transcript: str) -> Dict:
    """
    Analyze a call transcript for outcomes and issues.

    Args:
        transcript: Raw transcript text

    Returns:
        Dictionary with analysis results
    """
    if not transcript:
        return {
            'outcome': 'unknown',
            'issues': [],
            'ai_turns': 0,
            'user_turns': 0,
            'key_phrases': [],
        }

    transcript_lower = transcript.lower()

    # Determine outcome
    outcome = _determine_outcome(transcript_lower)

    # Detect issues
    issues = _detect_issues(transcript, transcript_lower)

    # Count turns
    ai_turns = transcript.count('AI:')
    user_turns = transcript.count('User:')

    # Extract key phrases
    key_phrases = _extract_key_phrases(transcript)

    return {
        'outcome': outcome,
        'issues': issues,
        'ai_turns': ai_turns,
        'user_turns': user_turns,
        'key_phrases': key_phrases,
    }


def _determine_outcome(transcript_lower: str) -> str:
    """Determine the primary outcome of the call."""
    # Check in priority order
    for outcome, patterns in OUTCOME_CATEGORIES.items():
        for pattern in patterns:
            if pattern in transcript_lower:
                return outcome

    return 'other'


def _detect_issues(transcript: str, transcript_lower: str) -> List[str]:
    """Detect issues in the transcript."""
    issues = []

    # Check issue patterns
    for issue, patterns in ISSUE_PATTERNS.items():
        if issue in ['phone_number_inconsistency', 'repeat_response']:
            continue  # These are detected by special functions
        for pattern in patterns:
            if pattern in transcript_lower:
                issues.append(issue)
                break

    # Check for repeated responses
    if _has_repeated_responses(transcript):
        issues.append('repeat_response')

    # Check for phone number inconsistency
    if _has_phone_number_inconsistency(transcript):
        issues.append('phone_number_inconsistency')

    # Check for "check further out" loop (2+ times = loop)
    loop_count = _count_check_further_loops(transcript)
    if loop_count >= 2:
        issues.append('check_further_loop')

    # Check for silence timeout end reason (would need to be passed in)
    if 'silence-timed-out' in transcript_lower:
        issues.append('silence_timeout')

    return list(set(issues))


def _has_repeated_responses(transcript: str) -> bool:
    """Check if AI gave the same response multiple times."""
    # Extract AI responses
    ai_responses = re.findall(r'AI: ([^\n]+)', transcript)

    # Check for duplicates
    seen = set()
    for response in ai_responses:
        # Normalize
        normalized = response.strip().lower()[:50]
        if normalized in seen:
            return True
        seen.add(normalized)

    return False


def _has_phone_number_inconsistency(transcript: str) -> bool:
    """Check if phone number was repeated differently."""
    # Find all phone number patterns (digit sequences spoken as words)
    phone_patterns = re.findall(r'(?:\d\s*){7,10}', transcript)

    if len(phone_patterns) >= 2:
        # Normalize by removing spaces
        normalized = [p.replace(' ', '') for p in phone_patterns]
        # Check if any two are different
        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                if normalized[i] != normalized[j] and len(normalized[i]) == len(normalized[j]):
                    return True
    return False


def _count_check_further_loops(transcript: str) -> int:
    """Count how many times 'check further out' was asked."""
    pattern = r'would you like me to check further|check further out'
    matches = re.findall(pattern, transcript.lower())
    return len(matches)


def _extract_key_phrases(transcript: str) -> List[str]:
    """Extract key phrases from transcript."""
    key_phrases = []

    # Date mentions
    dates = re.findall(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+(?:st|nd|rd|th)?', transcript, re.IGNORECASE)
    key_phrases.extend(dates[:3])

    # Time mentions
    times = re.findall(r'\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)', transcript)
    key_phrases.extend(times[:3])

    # Project types
    projects = re.findall(r'(?:blinds|decking|fence|window|door|balcony|bathroom|kitchen)', transcript, re.IGNORECASE)
    key_phrases.extend(list(set(projects)))

    return key_phrases


def categorize_call(call: Dict) -> Dict:
    """
    Add categorization to a call based on all available data.

    Args:
        call: Call dictionary with transcript and other data

    Returns:
        Call with added categorization
    """
    transcript = call.get('transcript', '')
    end_reason = call.get('end_reason', '')

    # Analyze transcript
    analysis = analyze_transcript(transcript)

    # Add end reason to issues if relevant
    if end_reason == 'silence-timed-out':
        if 'silence_timeout' not in analysis['issues']:
            analysis['issues'].append('silence_timeout')

    # Determine category for reporting
    if analysis['outcome'] == 'appointment_confirmed':
        category = 'SUCCESS'
    elif analysis['outcome'] == 'no_availability':
        category = 'NO_AVAILABILITY'
    elif analysis['outcome'] == 'office_handoff':
        category = 'OFFICE_HANDOFF'
    elif analysis['outcome'] == 'cancellation_request':
        category = 'CANCELLATION'
    elif analysis['outcome'] == 'reschedule_request':
        category = 'RESCHEDULE'
    elif analysis['outcome'] == 'project_not_schedulable':
        category = 'NOT_SCHEDULABLE'
    else:
        category = 'OTHER'

    call['analysis'] = analysis
    call['category'] = category

    return call


def generate_summary_stats(calls: List[Dict]) -> Dict:
    """
    Generate summary statistics for a list of calls.

    Args:
        calls: List of categorized calls

    Returns:
        Dictionary with summary stats
    """
    stats = {
        'total_calls': len(calls),
        'by_category': {},
        'by_outcome': {},
        'issues_count': {},
        'with_logs': 0,
        'without_logs': 0,
    }

    for call in calls:
        # Category counts
        category = call.get('category', 'OTHER')
        stats['by_category'][category] = stats['by_category'].get(category, 0) + 1

        # Outcome counts
        outcome = call.get('analysis', {}).get('outcome', 'unknown')
        stats['by_outcome'][outcome] = stats['by_outcome'].get(outcome, 0) + 1

        # Issue counts
        issues = call.get('analysis', {}).get('issues', [])
        for issue in issues:
            stats['issues_count'][issue] = stats['issues_count'].get(issue, 0) + 1

        # Log presence
        if call.get('log_insights', {}).get('has_logs'):
            stats['with_logs'] += 1
        else:
            stats['without_logs'] += 1

    # Calculate percentages
    if stats['total_calls'] > 0:
        stats['success_rate'] = round(
            stats['by_category'].get('SUCCESS', 0) / stats['total_calls'] * 100, 1
        )
        stats['no_availability_rate'] = round(
            stats['by_category'].get('NO_AVAILABILITY', 0) / stats['total_calls'] * 100, 1
        )

    return stats
