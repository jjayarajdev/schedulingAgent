"""
DSPy Date Interpreter for Lambda

Lightweight wrapper for LLM-based date interpretation.
Falls back to regex if DSPy/Bedrock unavailable.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger()

# Feature flag
USE_LLM_DATE_INTERPRETER = os.environ.get('USE_LLM_DATE_INTERPRETER', 'true').lower() == 'true'

# Cache for repeated queries
_date_cache: Dict[str, Dict] = {}
_cache_ttl = 300  # 5 minutes


def interpret_date(
    phrase: str,
    current_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Interpret a natural language date expression.

    Args:
        phrase: Natural language date (e.g., "first week of January", "01/08")
        current_date: Today's date in YYYY-MM-DD format (defaults to actual today)

    Returns:
        dict with:
        - start_date: str or None (YYYY-MM-DD)
        - end_date: str or None (YYYY-MM-DD)
        - is_past: bool
        - date_type: "specific_day" | "week" | "month" | "date_range"
        - interpretation: str (human-readable explanation)
    """
    if current_date is None:
        current_date = datetime.now().strftime("%Y-%m-%d")

    # Check cache
    cache_key = f"{phrase}|{current_date}"
    if cache_key in _date_cache:
        cached = _date_cache[cache_key]
        if (datetime.now() - cached['_cached_at']).seconds < _cache_ttl:
            logger.info(f"[DATE-LLM] Cache hit for '{phrase}'")
            return cached['result']

    if USE_LLM_DATE_INTERPRETER:
        try:
            result = _interpret_with_bedrock(phrase, current_date)
            # Cache result
            _date_cache[cache_key] = {'result': result, '_cached_at': datetime.now()}
            return result
        except Exception as e:
            logger.warning(f"[DATE-LLM] Bedrock failed: {e}, using fallback")

    # Fallback to simple interpretation
    return _fallback_interpret(phrase, current_date)


def _interpret_with_bedrock(phrase: str, current_date: str) -> Dict[str, Any]:
    """Use Bedrock Claude to interpret the date."""
    import boto3

    bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

    # Build prompt with few-shot examples
    prompt = f"""You are a date interpreter for a scheduling system. Given a natural language date phrase and today's date, extract the specific date range.

CRITICAL RULES:
1. Week 1 of a month = days from 1st until the day before first Monday (partial week)
2. Week 2+ = Monday to Sunday weeks (full weeks)
3. IMPORTANT: If ALL dates in the requested period are BEFORE today:
   - Set is_past=true
   - Set start_date=null and end_date=null (NOT the actual past dates)
4. If SOME dates are past but some are future:
   - Set is_past=false
   - Return ONLY the future dates (start_date = first date >= today)
5. For MM/DD format without year (like "01/08"), assume current year unless past, then next year
6. "first week" and "1st week" mean the same thing - Week 1
7. Ignore extra words like "show me", "available dates for" - focus on the week/date reference

EXAMPLES:

Phrase: "first week of January"
Today: 2026-01-06
Analysis: January 2026 starts on Thursday (Jan 1). First Monday is Jan 5. So Week 1 = Jan 1-4 (Thu-Sun).
Today is Jan 6, so ALL of Week 1 is past. Return null dates.
Result: {{"start_date": null, "end_date": null, "is_past": true, "date_type": "week", "interpretation": "First week of January (Jan 1-4) has already passed."}}

Phrase: "1st week of Jan"
Today: 2026-01-06
Analysis: "1st week" = "first week" = Week 1. January 2026 Week 1 = Jan 1-4.
Today is Jan 6, so ALL dates are past. Return null dates.
Result: {{"start_date": null, "end_date": null, "is_past": true, "date_type": "week", "interpretation": "1st week of January (Jan 1-4) has already passed."}}

Phrase: "show me the 1st week available dates for jan"
Today: 2026-01-06
Analysis: Ignore "show me the" and "available dates for". Focus on "1st week" + "jan" = Week 1 of January.
Week 1 = Jan 1-4. All past, return null.
Result: {{"start_date": null, "end_date": null, "is_past": true, "date_type": "week", "interpretation": "First week of January (Jan 1-4) has already passed."}}

Phrase: "first week of April"
Today: 2026-01-06
Analysis: April 2026 starts on Wednesday (Apr 1). First Monday is Apr 6. So Week 1 = Apr 1-5 (Wed-Sun).
All dates are in the future.
Result: {{"start_date": "2026-04-01", "end_date": "2026-04-05", "is_past": false, "date_type": "week", "interpretation": "First week of April 2026: Apr 1-5 (Wed-Sun before first Monday)."}}

Phrase: "01/08"
Today: 2026-01-06
Analysis: MM/DD format means January 8. Jan 8, 2026 is in the future.
Result: {{"start_date": "2026-01-08", "end_date": "2026-01-08", "is_past": false, "date_type": "specific_day", "interpretation": "January 8, 2026."}}

Phrase: "2nd week of January"
Today: 2026-01-06
Analysis: Week 2 of January = Jan 5-11 (Mon-Sun). Today is Jan 6, so Jan 5 is past.
Since SOME dates (Jan 7-11) are still in future, return only those future dates.
Result: {{"start_date": "2026-01-07", "end_date": "2026-01-11", "is_past": false, "date_type": "week", "interpretation": "2nd week of January (Jan 5-11), available dates: Jan 7-11."}}

Phrase: "between Jan 9 and 18"
Today: 2026-01-06
Analysis: Explicit date range from January 9 to January 18, 2026.
Result: {{"start_date": "2026-01-09", "end_date": "2026-01-18", "is_past": false, "date_type": "date_range", "interpretation": "Date range: January 9-18, 2026."}}

NOW INTERPRET THIS:

Phrase: "{phrase}"
Today: {current_date}

Return ONLY a JSON object with these fields: start_date, end_date, is_past, date_type, interpretation
"""

    response = bedrock.invoke_model(
        modelId='us.anthropic.claude-3-haiku-20240307-v1:0',  # Cross-region inference profile for Haiku
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 500,
            'temperature': 0,
            'messages': [{'role': 'user', 'content': prompt}]
        })
    )

    response_body = json.loads(response['body'].read())
    content = response_body['content'][0]['text']

    # Extract JSON from response
    import re
    json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
    if json_match:
        result = json.loads(json_match.group())
        # Normalize null strings to None
        if result.get('start_date') in ('null', 'None', ''):
            result['start_date'] = None
        if result.get('end_date') in ('null', 'None', ''):
            result['end_date'] = None

        # POST-PROCESSING VALIDATION: Verify is_past based on actual dates
        # This catches LLM errors where dates are past but is_past=false
        today_dt = datetime.strptime(current_date, "%Y-%m-%d")
        if result.get('end_date'):
            try:
                end_dt = datetime.strptime(result['end_date'], "%Y-%m-%d")
                if end_dt.date() < today_dt.date():
                    # All dates are past - force is_past=true and null dates
                    logger.info(f"[DATE-LLM] Post-processing: end_date {result['end_date']} < today {current_date}, forcing is_past=true")
                    result['is_past'] = True
                    result['start_date'] = None
                    result['end_date'] = None
                    result['interpretation'] = f"The requested period has already passed (ended {end_dt.strftime('%b %d')})."
            except ValueError:
                pass  # Invalid date format, skip validation

        # If start_date is past but end_date is future, adjust start to today
        if result.get('start_date') and not result.get('is_past'):
            try:
                start_dt = datetime.strptime(result['start_date'], "%Y-%m-%d")
                if start_dt.date() < today_dt.date():
                    # Adjust start to today
                    new_start = today_dt.strftime("%Y-%m-%d")
                    logger.info(f"[DATE-LLM] Post-processing: adjusting start from {result['start_date']} to {new_start}")
                    result['start_date'] = new_start
            except ValueError:
                pass

        result['_source'] = 'bedrock'
        logger.info(f"[DATE-LLM] Interpreted '{phrase}' -> {result['start_date']} to {result['end_date']} ({result.get('date_type', 'unknown')})")
        return result

    raise ValueError(f"Could not parse JSON from response: {content}")


def _fallback_interpret(phrase: str, current_date: str) -> Dict[str, Any]:
    """Simple fallback when LLM unavailable."""
    today = datetime.strptime(current_date, "%Y-%m-%d")
    tomorrow = today + timedelta(days=1)

    # Very basic parsing
    phrase_lower = phrase.lower()

    # Check for "past" indicators
    if 'yesterday' in phrase_lower:
        return {
            'start_date': None,
            'end_date': None,
            'is_past': True,
            'date_type': 'specific_day',
            'interpretation': 'Yesterday is in the past.',
            '_source': 'fallback'
        }

    # Default: 2 days (balance between options and API performance)
    return {
        'start_date': tomorrow.strftime("%Y-%m-%d"),
        'end_date': (tomorrow + timedelta(days=1)).strftime("%Y-%m-%d"),
        'is_past': False,
        'date_type': 'day',
        'interpretation': f'Defaulting to next 2 days from {tomorrow.strftime("%Y-%m-%d")}',
        '_source': 'fallback'
    }


def convert_to_legacy_format(result: Dict[str, Any]) -> tuple:
    """
    Convert LLM result to legacy format expected by handler.py

    Returns: (start_date, strategy, days_to_fetch, end_date) or (None, 'week_past', 0) if past
    """
    if result.get('is_past'):
        return (None, 'week_past', 0)

    start_date = result.get('start_date')
    end_date = result.get('end_date')
    date_type = result.get('date_type', 'week')

    if not start_date:
        return (None, 'week_past', 0)

    # Calculate days
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end_dt - start_dt).days + 1
    else:
        days = 1 if date_type == 'specific_day' else 5

    # Map date_type to strategy
    strategy_map = {
        'specific_day': 'specific_day',
        'week': 'week',
        'month': 'week',
        'date_range': 'date_range'
    }
    strategy = strategy_map.get(date_type, 'week')

    return (start_date, strategy, days, end_date)
