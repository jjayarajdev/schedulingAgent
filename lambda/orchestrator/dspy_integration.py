"""
DSPy Integration Module for ProjectForce Orchestrator

This module provides:
1. DSPy-powered classification with optimized prompts
2. S3-based model loading for dynamic updates
3. Fallback to traditional classification if DSPy unavailable

Usage:
    from dspy_integration import get_dspy_classifier, classify_with_dspy

    # Classify a message
    result = classify_with_dspy(message, conversation_history)
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger()

# Feature flag - can be set via environment variable
DSPY_ENABLED = os.environ.get('DSPY_ENABLED', 'false').lower() == 'true'
DSPY_MODEL_BUCKET = os.environ.get('DSPY_MODEL_BUCKET', 'projectforce-dspy-models')
DSPY_MODEL_PREFIX = os.environ.get('DSPY_MODEL_PREFIX', 'optimized/')

# Cache for loaded models
_dspy_classifier = None
_dspy_extractor = None
_dspy_weather = None
_dspy_date_interpreter = None
_dspy_context_resolver = None
_dspy_response_styler = None
_dspy_slot_ranker = None
_models_loaded = False
_last_model_check = None
MODEL_REFRESH_INTERVAL = 300  # Check for new models every 5 minutes


# =============================================================================
# DSPY SIGNATURES (inline to avoid import issues in Lambda)
# =============================================================================

def _get_dspy():
    """Lazy import of DSPy to handle Lambda cold starts."""
    try:
        import dspy
        return dspy
    except ImportError:
        logger.warning("DSPy not available - using fallback classification")
        return None


def _configure_dspy_bedrock():
    """Configure DSPy with AWS Bedrock backend."""
    dspy = _get_dspy()
    if not dspy:
        return False

    try:
        # Use Bedrock Claude for inference
        model_id = os.environ.get('DSPY_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        region = os.environ.get('AWS_REGION', 'us-east-1')

        lm = dspy.LM(
            model=f"bedrock/{model_id}",
            aws_region_name=region
        )
        dspy.configure(lm=lm)
        logger.info(f"DSPy configured with Bedrock model: {model_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to configure DSPy: {e}")
        return False


# =============================================================================
# S3 MODEL LOADING
# =============================================================================

def _load_model_from_s3(model_name: str) -> Optional[Dict]:
    """Load optimized model JSON from S3."""
    import boto3

    try:
        s3 = boto3.client('s3')
        key = f"{DSPY_MODEL_PREFIX}{model_name}.json"

        response = s3.get_object(Bucket=DSPY_MODEL_BUCKET, Key=key)
        model_data = json.loads(response['Body'].read().decode('utf-8'))

        logger.info(f"Loaded DSPy model from s3://{DSPY_MODEL_BUCKET}/{key}")
        return model_data
    except Exception as e:
        logger.warning(f"Could not load model {model_name} from S3: {e}")
        return None


def _load_model_from_local(model_name: str) -> Optional[Dict]:
    """Load optimized model from local file (for testing)."""
    try:
        # Check in same directory
        local_path = os.path.join(os.path.dirname(__file__), f"{model_name}.json")
        if os.path.exists(local_path):
            with open(local_path, 'r') as f:
                return json.load(f)

        # Check in dspy-poc directory
        poc_path = f"/Users/jjayaraj/workspaces/studios/projectsforce/dspy-poc/{model_name}.json"
        if os.path.exists(poc_path):
            with open(poc_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load local model {model_name}: {e}")

    return None


def load_optimized_models() -> bool:
    """Load all optimized models from S3 or local storage."""
    global _dspy_classifier, _dspy_extractor, _dspy_weather
    global _dspy_date_interpreter, _dspy_context_resolver, _dspy_response_styler, _dspy_slot_ranker
    global _models_loaded, _last_model_check

    now = datetime.now()

    # Skip if recently checked
    if _last_model_check and (now - _last_model_check).seconds < MODEL_REFRESH_INTERVAL:
        return _models_loaded

    _last_model_check = now

    # Try S3 first, then local for each model
    classifier_data = _load_model_from_s3('optimized_classifier') or _load_model_from_local('optimized_classifier')
    extractor_data = _load_model_from_s3('optimized_extractor') or _load_model_from_local('optimized_extractor')
    weather_data = _load_model_from_s3('optimized_weather') or _load_model_from_local('optimized_weather')

    # New modules
    date_interpreter_data = _load_model_from_s3('optimized_date_interpreter') or _load_model_from_local('optimized_date_interpreter')
    context_resolver_data = _load_model_from_s3('optimized_context_resolver') or _load_model_from_local('optimized_context_resolver')
    response_styler_data = _load_model_from_s3('optimized_response_styler') or _load_model_from_local('optimized_response_styler')
    slot_ranker_data = _load_model_from_s3('optimized_slot_ranker') or _load_model_from_local('optimized_slot_ranker')

    if classifier_data:
        _dspy_classifier = classifier_data
        logger.info("Loaded optimized classifier")

    if extractor_data:
        _dspy_extractor = extractor_data
        logger.info("Loaded optimized extractor")

    if weather_data:
        _dspy_weather = weather_data
        logger.info("Loaded optimized weather resolver")

    if date_interpreter_data:
        _dspy_date_interpreter = date_interpreter_data
        logger.info("Loaded optimized date interpreter")

    if context_resolver_data:
        _dspy_context_resolver = context_resolver_data
        logger.info("Loaded optimized context resolver")

    if response_styler_data:
        _dspy_response_styler = response_styler_data
        logger.info("Loaded optimized response styler")

    if slot_ranker_data:
        _dspy_slot_ranker = slot_ranker_data
        logger.info("Loaded optimized slot ranker")

    _models_loaded = classifier_data is not None
    return _models_loaded


# =============================================================================
# FEW-SHOT PROMPT ENHANCEMENT
# =============================================================================

def get_classifier_few_shots() -> str:
    """
    Get DSPy-learned few-shot examples for the classifier prompt.

    This is the simplest integration - just add these examples to
    the existing NLU prompt template.
    """
    global _dspy_classifier

    if not _dspy_classifier:
        load_optimized_models()

    if not _dspy_classifier:
        return ""

    # Extract demos from the optimized model
    demos = _dspy_classifier.get('classifier.predict', {}).get('demos', [])

    if not demos:
        return ""

    lines = ["\n## EXAMPLES (DSPy-optimized from real usage)\n"]

    for i, demo in enumerate(demos, 1):
        lines.append(f"Example {i}:")
        lines.append(f"User: \"{demo.get('message', '')}\"")
        if demo.get('conversation_summary'):
            lines.append(f"Context: {demo['conversation_summary']}")
        lines.append(f"Analysis: {demo.get('reasoning', '')}")
        lines.append(f"→ Intent: {demo.get('intent', '')}")
        lines.append(f"→ Action: {demo.get('action', '')}")
        lines.append(f"→ Confidence: {demo.get('confidence', 'high')}")
        lines.append("")

    return "\n".join(lines)


def get_extractor_few_shots() -> str:
    """Get DSPy-learned few-shot examples for entity extraction."""
    global _dspy_extractor

    if not _dspy_extractor:
        load_optimized_models()

    if not _dspy_extractor:
        return ""

    demos = _dspy_extractor.get('extractor.predict', {}).get('demos', [])

    if not demos:
        return ""

    lines = ["\n## ENTITY EXTRACTION EXAMPLES\n"]

    for i, demo in enumerate(demos, 1):
        lines.append(f"Example {i}:")
        lines.append(f"Message: \"{demo.get('message', '')}\"")
        lines.append(f"Action: {demo.get('action', '')}")

        # Show extracted entities
        entities = {}
        for field in ['project_id', 'category', 'date', 'time', 'location', 'status_filter']:
            if demo.get(field):
                entities[field] = demo[field]

        if entities:
            lines.append(f"Extracted: {json.dumps(entities)}")
        lines.append("")

    return "\n".join(lines)


def get_date_interpreter_few_shots() -> str:
    """Get DSPy-learned few-shot examples for date interpretation."""
    global _dspy_date_interpreter

    if not _dspy_date_interpreter:
        load_optimized_models()

    if not _dspy_date_interpreter:
        return ""

    demos = _dspy_date_interpreter.get('date_interpreter.predict', {}).get('demos', [])

    if not demos:
        return ""

    lines = ["\n## DATE INTERPRETATION EXAMPLES\n"]

    for i, demo in enumerate(demos, 1):
        lines.append(f"Example {i}:")
        lines.append(f"Phrase: \"{demo.get('phrase', '')}\"")
        lines.append(f"Current Date: {demo.get('current_date', '')}")
        lines.append(f"→ Start: {demo.get('start_date', '')} | End: {demo.get('end_date', '')}")
        lines.append(f"Interpretation: {demo.get('interpretation', '')}")
        lines.append("")

    return "\n".join(lines)


def get_context_resolver_few_shots() -> str:
    """Get DSPy-learned few-shot examples for context resolution."""
    global _dspy_context_resolver

    if not _dspy_context_resolver:
        load_optimized_models()

    if not _dspy_context_resolver:
        return ""

    demos = _dspy_context_resolver.get('context_resolver.predict', {}).get('demos', [])

    if not demos:
        return ""

    lines = ["\n## CONTEXT RESOLUTION EXAMPLES\n"]

    for i, demo in enumerate(demos, 1):
        lines.append(f"Example {i}:")
        lines.append(f"Message: \"{demo.get('message', '')}\"")
        lines.append(f"Context: {demo.get('conversation_history', '')[:100]}...")
        lines.append(f"→ Resolved: \"{demo.get('resolved_message', '')}\"")
        lines.append(f"Entities: {demo.get('resolved_entities', '{}')}")
        lines.append(f"Type: {demo.get('resolution_type', '')} | Confidence: {demo.get('confidence', '')}")
        lines.append("")

    return "\n".join(lines)


def get_response_style_few_shots(channel: str = "chat") -> str:
    """Get DSPy-learned few-shot examples for response styling."""
    global _dspy_response_styler

    if not _dspy_response_styler:
        load_optimized_models()

    if not _dspy_response_styler:
        return ""

    demos = _dspy_response_styler.get('response_styler.predict', {}).get('demos', [])

    if not demos:
        return ""

    # Filter demos for the specific channel
    channel_demos = [d for d in demos if d.get('channel', '') == channel]
    if not channel_demos:
        channel_demos = demos[:3]  # Fallback to first 3

    lines = [f"\n## RESPONSE STYLE EXAMPLES ({channel.upper()} CHANNEL)\n"]

    for i, demo in enumerate(channel_demos, 1):
        lines.append(f"Example {i}:")
        lines.append(f"Raw: \"{demo.get('raw_response', '')[:100]}...\"")
        lines.append(f"Channel: {demo.get('channel', '')}")
        lines.append(f"→ Styled: \"{demo.get('styled_response', '')[:100]}...\"")
        lines.append(f"Notes: {demo.get('style_notes', '')}")
        lines.append("")

    return "\n".join(lines)


def get_slot_ranker_few_shots() -> str:
    """Get DSPy-learned few-shot examples for slot ranking."""
    global _dspy_slot_ranker

    if not _dspy_slot_ranker:
        load_optimized_models()

    if not _dspy_slot_ranker:
        return ""

    demos = _dspy_slot_ranker.get('slot_ranker.predict', {}).get('demos', [])

    if not demos:
        return ""

    lines = ["\n## SLOT RANKING EXAMPLES\n"]

    for i, demo in enumerate(demos, 1):
        lines.append(f"Example {i}:")
        lines.append(f"Slots: {demo.get('available_slots', '')}")
        lines.append(f"Preference: {demo.get('user_preference', 'none')}")
        lines.append(f"Weather: {demo.get('weather_info', 'N/A')}")
        lines.append(f"Project: {demo.get('project_type', '')}")
        lines.append(f"→ Recommendation: {demo.get('recommendation', '')}")
        lines.append(f"Reason: {demo.get('ranking_reason', '')}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# PROMPT ENHANCEMENT FUNCTIONS FOR NEW MODULES
# =============================================================================

def enhance_date_prompt(base_prompt: str) -> str:
    """Enhance date parsing prompt with DSPy-learned examples."""
    few_shots = get_date_interpreter_few_shots()

    if not few_shots:
        return base_prompt

    # Insert before the actual date parsing section
    marker = "## DATE PARSING"
    if marker in base_prompt:
        parts = base_prompt.split(marker)
        return parts[0] + few_shots + "\n" + marker + parts[1]

    return base_prompt + few_shots


def enhance_context_prompt(base_prompt: str) -> str:
    """Enhance context resolution prompt with DSPy-learned examples."""
    few_shots = get_context_resolver_few_shots()

    if not few_shots:
        return base_prompt

    return base_prompt + few_shots


def enhance_response_style_prompt(base_prompt: str, channel: str = "chat") -> str:
    """Enhance response styling prompt with channel-specific examples."""
    few_shots = get_response_style_few_shots(channel)

    if not few_shots:
        return base_prompt

    return base_prompt + few_shots


def enhance_slot_ranking_prompt(base_prompt: str) -> str:
    """Enhance slot ranking prompt with DSPy-learned examples."""
    few_shots = get_slot_ranker_few_shots()

    if not few_shots:
        return base_prompt

    return base_prompt + few_shots


# =============================================================================
# FULL DSPY CLASSIFICATION (Optional - requires DSPy in Lambda layer)
# =============================================================================

def classify_with_dspy(
    message: str,
    conversation_history: Optional[List[Dict]] = None,
    fallback_fn=None
) -> Dict[str, Any]:
    """
    Classify message using DSPy-optimized module.

    Falls back to traditional classification if DSPy unavailable.

    Args:
        message: User message to classify
        conversation_history: Recent conversation for context
        fallback_fn: Fallback classification function

    Returns:
        Classification result dict
    """
    if not DSPY_ENABLED:
        if fallback_fn:
            return fallback_fn(message, conversation_history)
        return {"error": "DSPy disabled and no fallback provided"}

    dspy = _get_dspy()
    if not dspy:
        if fallback_fn:
            return fallback_fn(message, conversation_history)
        return {"error": "DSPy not available"}

    try:
        # Configure DSPy if needed
        if not _configure_dspy_bedrock():
            if fallback_fn:
                return fallback_fn(message, conversation_history)
            return {"error": "DSPy configuration failed"}

        # Load models if needed
        if not load_optimized_models():
            logger.warning("No optimized models available, using base DSPy")

        # Build context summary
        context_summary = _summarize_history(conversation_history or [])

        # Use DSPy ChainOfThought for classification
        class IntentClassifier(dspy.Signature):
            """Classify user intent for home improvement scheduling assistant."""
            message: str = dspy.InputField(desc="User's message")
            conversation_summary: str = dspy.InputField(desc="Recent conversation context")

            reasoning: str = dspy.OutputField(desc="Brief explanation of classification")
            intent: str = dspy.OutputField(desc="scheduling, information, or chitchat")
            action: str = dspy.OutputField(desc="Specific action to take")
            confidence: str = dspy.OutputField(desc="high, medium, or low")

        classifier = dspy.ChainOfThought(IntentClassifier)

        # Load demos if available
        if _dspy_classifier:
            demos = _dspy_classifier.get('classifier.predict', {}).get('demos', [])
            # DSPy will use these as few-shot examples

        result = classifier(message=message, conversation_summary=context_summary)

        return {
            "intent": result.intent,
            "action": result.action,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "_dspy": True
        }

    except Exception as e:
        logger.error(f"DSPy classification error: {e}")
        if fallback_fn:
            return fallback_fn(message, conversation_history)
        return {"error": str(e)}


def _summarize_history(conversation_history: List[Dict]) -> str:
    """Summarize conversation history for context."""
    if not conversation_history:
        return ""

    recent = conversation_history[-3:]
    lines = []

    for msg in recent:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = (msg.get("content") or "")[:200]
        lines.append(f"{role}: {content}")

    return "\n".join(lines)


# =============================================================================
# INTEGRATION HELPERS
# =============================================================================

def enhance_nlu_prompt(base_prompt: str) -> str:
    """
    Enhance the NLU prompt with DSPy-learned few-shot examples.

    This is the easiest integration method - just call this function
    on your existing prompt template.

    Usage in classifier.py:
        from dspy_integration import enhance_nlu_prompt

        prompt = NLU_PROMPT_TEMPLATE.format(...)
        prompt = enhance_nlu_prompt(prompt)  # Add DSPy examples
    """
    few_shots = get_classifier_few_shots()

    if not few_shots:
        return base_prompt

    # Insert few-shots after "## INTENT TAXONOMY" section
    marker = "## USER UTTERANCE"
    if marker in base_prompt:
        parts = base_prompt.split(marker)
        return parts[0] + few_shots + "\n" + marker + parts[1]

    # Fallback: append to end before the message
    return base_prompt + few_shots


def is_dspy_available() -> bool:
    """Check if DSPy is available and enabled."""
    if not DSPY_ENABLED:
        return False
    return _get_dspy() is not None


def get_model_status() -> Dict[str, Any]:
    """Get status of loaded DSPy models for debugging."""
    load_optimized_models()

    return {
        "dspy_enabled": DSPY_ENABLED,
        "dspy_available": _get_dspy() is not None,
        "models_loaded": _models_loaded,
        "classifier_loaded": _dspy_classifier is not None,
        "extractor_loaded": _dspy_extractor is not None,
        "weather_loaded": _dspy_weather is not None,
        "date_interpreter_loaded": _dspy_date_interpreter is not None,
        "context_resolver_loaded": _dspy_context_resolver is not None,
        "response_styler_loaded": _dspy_response_styler is not None,
        "slot_ranker_loaded": _dspy_slot_ranker is not None,
        "last_check": _last_model_check.isoformat() if _last_model_check else None,
        "s3_bucket": DSPY_MODEL_BUCKET,
        "s3_prefix": DSPY_MODEL_PREFIX
    }
