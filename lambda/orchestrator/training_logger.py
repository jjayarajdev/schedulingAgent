"""
Training Data Logger for Continuous Learning

Logs classified queries to S3/DynamoDB for:
1. Collecting training examples from production
2. Identifying misclassifications for review
3. Building dataset for periodic re-optimization

Usage:
    from training_logger import log_classification, log_feedback

    # Log every classification
    log_classification(
        message="schedule my kitchen project",
        classification_result={"intent": "scheduling", "action": "get_available_dates"},
        conversation_context=context_summary
    )

    # Log user feedback (corrections)
    log_feedback(
        log_id="abc123",
        correct_intent="information",
        correct_action="get_project_details"
    )
"""
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()

# Configuration
TRAINING_LOG_ENABLED = os.environ.get('TRAINING_LOG_ENABLED', 'true').lower() == 'true'
TRAINING_LOG_BUCKET = os.environ.get('TRAINING_LOG_BUCKET', 'projectforce-training-logs')
TRAINING_LOG_TABLE = os.environ.get('TRAINING_LOG_TABLE', 'projectforce-training-logs')
TRAINING_LOG_PREFIX = os.environ.get('TRAINING_LOG_PREFIX', 'classification-logs/')

# Sampling rate (log 1 in N requests to reduce volume)
SAMPLING_RATE = int(os.environ.get('TRAINING_LOG_SAMPLE_RATE', '1'))  # 1 = log all

# Cache clients
_s3_client = None
_dynamodb_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client


def _get_dynamodb():
    global _dynamodb_client
    if _dynamodb_client is None:
        _dynamodb_client = boto3.resource('dynamodb')
    return _dynamodb_client


# =============================================================================
# MAIN LOGGING FUNCTIONS
# =============================================================================

def log_classification(
    message: str,
    classification_result: Dict[str, Any],
    conversation_context: str = "",
    workflow_state: Optional[Dict] = None,
    session_id: str = "",
    user_id: str = "",
    channel: str = "chat",
    response_time_ms: int = 0,
    metadata: Optional[Dict] = None
) -> Optional[str]:
    """
    Log a classification event for training data collection.

    Args:
        message: The user's message that was classified
        classification_result: The classification output (intent, action, etc.)
        conversation_context: Summary of recent conversation
        workflow_state: Current workflow state if any
        session_id: Session identifier
        user_id: User identifier (anonymized)
        channel: 'chat', 'voice', or 'sms'
        response_time_ms: Classification latency
        metadata: Additional metadata

    Returns:
        log_id for later reference, or None if logging failed/skipped
    """
    if not TRAINING_LOG_ENABLED:
        return None

    # Sampling
    if SAMPLING_RATE > 1:
        import random
        if random.randint(1, SAMPLING_RATE) != 1:
            return None

    try:
        log_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'

        log_entry = {
            "log_id": log_id,
            "timestamp": timestamp,
            "message": message,
            "conversation_context": conversation_context,
            "classification": {
                "intent": classification_result.get("intent"),
                "action": classification_result.get("action"),
                "confidence": classification_result.get("confidence", "unknown"),
                "nlu_intent": classification_result.get("_nlu_intent"),
                "reasoning": classification_result.get("reasoning", ""),
            },
            "workflow_state": workflow_state or {},
            "session_id": session_id,
            "user_id": _anonymize_user_id(user_id),
            "channel": channel,
            "response_time_ms": response_time_ms,
            "metadata": metadata or {},
            "feedback": None,  # Will be updated if user provides feedback
            "reviewed": False,  # For manual review workflow
        }

        # Log to S3 (primary storage for batch processing)
        _log_to_s3(log_entry)

        # Also log to DynamoDB for quick queries
        _log_to_dynamodb(log_entry)

        return log_id

    except Exception as e:
        logger.error(f"Failed to log classification: {e}")
        return None


def log_feedback(
    log_id: str,
    correct_intent: Optional[str] = None,
    correct_action: Optional[str] = None,
    feedback_type: str = "correction",  # "correction", "confirm", "reject"
    feedback_source: str = "user",  # "user", "reviewer", "automated"
    notes: str = ""
) -> bool:
    """
    Log feedback/correction for a previous classification.

    This is used for:
    1. User corrections ("I meant to cancel, not reschedule")
    2. Reviewer corrections during manual review
    3. Automated corrections based on user behavior

    Args:
        log_id: The original log entry ID
        correct_intent: The correct intent (if different)
        correct_action: The correct action (if different)
        feedback_type: Type of feedback
        feedback_source: Who provided the feedback
        notes: Additional notes

    Returns:
        True if feedback was logged successfully
    """
    try:
        table = _get_dynamodb().Table(TRAINING_LOG_TABLE)

        feedback = {
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "correct_intent": correct_intent,
            "correct_action": correct_action,
            "feedback_type": feedback_type,
            "feedback_source": feedback_source,
            "notes": notes
        }

        table.update_item(
            Key={"log_id": log_id},
            UpdateExpression="SET feedback = :fb, reviewed = :r",
            ExpressionAttributeValues={
                ":fb": feedback,
                ":r": True
            }
        )

        logger.info(f"Logged feedback for {log_id}: {feedback_type}")
        return True

    except Exception as e:
        logger.error(f"Failed to log feedback: {e}")
        return False


def log_conversation_outcome(
    session_id: str,
    outcome: str,  # "success", "abandoned", "error", "escalated"
    final_action: Optional[str] = None,
    turns: int = 0
):
    """
    Log the outcome of a conversation for training signal.

    Successful conversations indicate good classifications.
    Abandoned/error conversations may indicate problems.
    """
    try:
        table = _get_dynamodb().Table(TRAINING_LOG_TABLE)

        # Update all logs in this session with outcome
        # Note: In production, you'd use a GSI on session_id
        table.update_item(
            Key={"session_id": session_id},
            UpdateExpression="SET conversation_outcome = :o, final_action = :a, turn_count = :t",
            ExpressionAttributeValues={
                ":o": outcome,
                ":a": final_action,
                ":t": turns
            },
            ConditionExpression="attribute_exists(session_id)"
        )

    except Exception as e:
        # This is expected to fail for items that don't exist
        pass


# =============================================================================
# STORAGE BACKENDS
# =============================================================================

def _log_to_s3(log_entry: Dict) -> bool:
    """Log entry to S3 for batch processing."""
    try:
        s3 = _get_s3()

        # Organize by date for easy batch processing
        timestamp = datetime.utcnow()
        key = (
            f"{TRAINING_LOG_PREFIX}"
            f"year={timestamp.year}/"
            f"month={timestamp.month:02d}/"
            f"day={timestamp.day:02d}/"
            f"{log_entry['log_id']}.json"
        )

        s3.put_object(
            Bucket=TRAINING_LOG_BUCKET,
            Key=key,
            Body=json.dumps(log_entry, default=str),
            ContentType='application/json'
        )

        return True

    except Exception as e:
        logger.error(f"S3 logging failed: {e}")
        return False


def _log_to_dynamodb(log_entry: Dict) -> bool:
    """Log entry to DynamoDB for quick queries."""
    try:
        table = _get_dynamodb().Table(TRAINING_LOG_TABLE)

        # Add TTL for automatic cleanup (90 days)
        ttl = int((datetime.utcnow() + timedelta(days=90)).timestamp())
        log_entry['ttl'] = ttl

        table.put_item(Item=log_entry)
        return True

    except Exception as e:
        logger.error(f"DynamoDB logging failed: {e}")
        return False


# =============================================================================
# DATA RETRIEVAL FOR TRAINING
# =============================================================================

def get_training_examples(
    start_date: datetime,
    end_date: datetime,
    include_feedback_only: bool = False,
    min_confidence: str = None,
    limit: int = 1000
) -> List[Dict]:
    """
    Retrieve logged examples for training.

    Args:
        start_date: Start of date range
        end_date: End of date range
        include_feedback_only: Only include entries with feedback
        min_confidence: Filter by confidence level
        limit: Maximum entries to return

    Returns:
        List of training examples
    """
    examples = []

    try:
        s3 = _get_s3()

        # Iterate through date range
        current = start_date
        while current <= end_date and len(examples) < limit:
            prefix = (
                f"{TRAINING_LOG_PREFIX}"
                f"year={current.year}/"
                f"month={current.month:02d}/"
                f"day={current.day:02d}/"
            )

            response = s3.list_objects_v2(
                Bucket=TRAINING_LOG_BUCKET,
                Prefix=prefix,
                MaxKeys=min(1000, limit - len(examples))
            )

            for obj in response.get('Contents', []):
                try:
                    data = s3.get_object(
                        Bucket=TRAINING_LOG_BUCKET,
                        Key=obj['Key']
                    )
                    entry = json.loads(data['Body'].read().decode('utf-8'))

                    # Apply filters
                    if include_feedback_only and not entry.get('feedback'):
                        continue

                    if min_confidence:
                        conf = entry.get('classification', {}).get('confidence', '')
                        if conf != min_confidence:
                            continue

                    examples.append(entry)

                except Exception as e:
                    logger.warning(f"Failed to read {obj['Key']}: {e}")

            current += timedelta(days=1)

    except Exception as e:
        logger.error(f"Failed to retrieve training examples: {e}")

    return examples


def export_for_dspy(
    start_date: datetime,
    end_date: datetime,
    output_format: str = "dspy"
) -> List[Dict]:
    """
    Export logged data in DSPy training format.

    Returns examples in the format expected by DSPy training.
    """
    raw_examples = get_training_examples(start_date, end_date)

    dspy_examples = []
    for ex in raw_examples:
        # Use feedback if available, otherwise use original classification
        feedback = ex.get('feedback', {})

        intent = feedback.get('correct_intent') or ex['classification']['intent']
        action = feedback.get('correct_action') or ex['classification']['action']

        dspy_example = {
            "message": ex['message'],
            "conversation_summary": ex.get('conversation_context', ''),
            "intent": intent,
            "action": action,
            "confidence": "high" if feedback else ex['classification']['confidence'],
            "reasoning": ex['classification'].get('reasoning', ''),
            # Mark if this was corrected
            "_corrected": feedback.get('feedback_type') == 'correction',
            "_original_intent": ex['classification']['intent'],
            "_original_action": ex['classification']['action'],
        }

        dspy_examples.append(dspy_example)

    return dspy_examples


# =============================================================================
# UTILITIES
# =============================================================================

def _anonymize_user_id(user_id: str) -> str:
    """Anonymize user ID for privacy."""
    if not user_id:
        return ""

    # Keep last 4 characters for debugging, hash the rest
    import hashlib
    if len(user_id) > 4:
        prefix = hashlib.sha256(user_id[:-4].encode()).hexdigest()[:8]
        return f"{prefix}...{user_id[-4:]}"
    return user_id


def get_logging_stats(days: int = 7) -> Dict[str, Any]:
    """Get statistics about logged training data."""
    try:
        table = _get_dynamodb().Table(TRAINING_LOG_TABLE)

        # This is a simplified version - in production you'd use aggregations
        response = table.scan(
            Select='COUNT',
            FilterExpression='#ts > :start',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':start': (datetime.utcnow() - timedelta(days=days)).isoformat()
            }
        )

        return {
            "total_logs": response.get('Count', 0),
            "period_days": days,
            "logging_enabled": TRAINING_LOG_ENABLED,
            "sampling_rate": SAMPLING_RATE,
            "s3_bucket": TRAINING_LOG_BUCKET,
            "dynamodb_table": TRAINING_LOG_TABLE
        }

    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# BATCH EXPORT FOR RETRAINING
# =============================================================================

def create_training_batch(
    output_bucket: str,
    output_key: str,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """
    Create a training batch file from logged data.

    This is called by the retraining script to prepare data.
    """
    examples = export_for_dspy(start_date, end_date)

    if not examples:
        return {"error": "No examples found", "count": 0}

    # Write to S3
    s3 = _get_s3()
    s3.put_object(
        Bucket=output_bucket,
        Key=output_key,
        Body=json.dumps(examples, default=str),
        ContentType='application/json'
    )

    return {
        "output": f"s3://{output_bucket}/{output_key}",
        "count": len(examples),
        "corrected_count": sum(1 for ex in examples if ex.get('_corrected')),
        "date_range": f"{start_date.date()} to {end_date.date()}"
    }
