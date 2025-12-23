"""
NLU-Style Intent Classifier for ProjectForce

Architecture:
- Intent Taxonomy: Well-defined intents with clear semantics
- Parameter Extraction: Systematic slot filling from utterance
- Action Mapping: Intent -> Lambda action (deterministic)

This module provides the core NLU classification. Additional functionality
is organized into separate modules:
- filters.py: Post-filtering (inclusion, exclusion, ordinals)
- preferences.py: Fallback/preference logic
- compound_actions.py: Multi-intent detection
- batch_operations.py: Batch operation helpers
- relative_scheduling.py: Relative scheduling
- comparative_queries.py: Comparative queries
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.config import Config as BotoConfig

from config import get_config
from config_loader import (
    get_schedulable_statuses_safe,
    get_scheduled_statuses_safe,
    get_all_category_buckets_safe,
    resolve_status_alias,
    find_category_bucket_for_keyword,
)

# Import from refactored modules for re-export (backward compatibility)
from filters import apply_project_filters, _norm, _get_field
from preferences import find_matching_slot_with_fallback, parse_preference_from_message
from compound_actions import (
    detect_compound_actions,
    classify_compound_message,
    execute_compound_actions,
    format_compound_response,
)
from batch_operations import (
    is_batch_operation,
    prepare_batch_operation,
    execute_batch_operation,
    format_batch_result,
)
from relative_scheduling import (
    resolve_relative_date,
    find_anchor_project_appointment,
    parse_relative_reference,
    resolve_relative_scheduling,
)
from comparative_queries import (
    compare_project_availability,
    compare_project_status,
    rank_projects_by_urgency,
)

logger = logging.getLogger(__name__)
_bedrock_runtime_client = None


# ═══════════════════════════════════════════════════════════════════════════════
# INTENT TAXONOMY
# ═══════════════════════════════════════════════════════════════════════════════

INTENT_ACTION_MAP = {
    # Information Requests (Query intents - read-only)
    "Project_List_Request": "list_projects",
    "Project_Information_Request": "get_project_details",
    "Availability_Check": "get_available_dates",
    "Time_Slot_Check": "get_time_slots",
    "Reschedule_Availability_Check": "get_rescheduler_slots",
    "Note_List_Request": "list_notes",

    # Action Requests (Mutation intents - change state)
    "Schedule_Request": "schedule_project",
    "Reschedule_Request": "reschedule_appointment",
    "Cancel_Request": "cancel_appointment",
    "Appointment_Confirmation": "confirm_appointment",
    "Note_Add_Request": "add_note",

    # Batch Action Requests (operate on multiple projects)
    "Batch_Schedule_Request": "batch_schedule",
    "Batch_Cancel_Request": "batch_cancel",
    "Batch_Reschedule_Request": "batch_reschedule",

    # Comparative Queries (compare across projects)
    "Compare_Availability": "compare_availability",
    "Compare_Projects": "compare_projects",

    # Non-scheduling intents
    "Weather_Request": "get_weather",
    "Greeting": "greet",
    "Help_Request": "help",
    "Farewell": "general",
    "Thanks": "general",
}

INTENT_CATEGORIES = {
    "scheduling": {
        "Project_List_Request", "Project_Information_Request", "Availability_Check",
        "Time_Slot_Check", "Reschedule_Availability_Check", "Note_List_Request",
        "Schedule_Request", "Reschedule_Request", "Cancel_Request",
        "Appointment_Confirmation", "Note_Add_Request",
        "Batch_Schedule_Request", "Batch_Cancel_Request", "Batch_Reschedule_Request",
        "Compare_Availability", "Compare_Projects",
    },
    "information": {"Weather_Request"},
    "chitchat": {"Greeting", "Help_Request", "Farewell", "Thanks"},
}


# ═══════════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

SCHEDULABLE_STATUSES = None
SCHEDULED_STATUSES = None
CATEGORY_BUCKETS = None


def _init_backward_compat():
    """Initialize backward-compatible module-level variables."""
    global SCHEDULABLE_STATUSES, SCHEDULED_STATUSES, CATEGORY_BUCKETS
    if SCHEDULABLE_STATUSES is None:
        SCHEDULABLE_STATUSES = get_schedulable_statuses_safe()
    if SCHEDULED_STATUSES is None:
        SCHEDULED_STATUSES = get_scheduled_statuses_safe()
    if CATEGORY_BUCKETS is None:
        CATEGORY_BUCKETS = get_all_category_buckets_safe()


# ═══════════════════════════════════════════════════════════════════════════════
# ALIASES
# ═══════════════════════════════════════════════════════════════════════════════

STATUS_ALIASES = {
    "new": "New",
    "unscheduled": "New",
    "ready to schedule": "Ready To Schedule",
    "ready to go": "Ready To Schedule",
    "schedulable": "schedulable",
    "can schedule": "schedulable",
    "available to schedule": "schedulable",
    "scheduled": "Scheduled",
    "on the books": "Scheduled",
    "on the calendar": "Scheduled",
    "booked": "Scheduled",
    "tentatively scheduled": "Tentatively Scheduled",
    "tentative": "Tentatively Scheduled",
    "completed": "Completed",
    "done": "Completed",
    "finished": "Completed",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "in progress": "In Progress",
    "underway": "In Progress",
    "pending": "Pending",
    "waiting": "Pending",
    "in the queue": "Pending",
}

PROJECT_TYPE_ALIASES = {
    "call back": "Call Back",
    "callback": "Call Back",
    "installation": "Installation",
    "install": "Installation",
    "installs": "Installation",
    "repair": "Repair",
    "service call": "Repair",
    "measurement": "Measurement",
    "measure": "Measurement",
}


# ═══════════════════════════════════════════════════════════════════════════════
# BEDROCK CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

def get_bedrock_client():
    """Get or create Bedrock runtime client with connection pooling."""
    global _bedrock_runtime_client
    if _bedrock_runtime_client is None:
        cfg = get_config()
        boto_config = BotoConfig(
            region_name=cfg.region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        _bedrock_runtime_client = boto3.client("bedrock-runtime", config=boto_config)
        logger.info("Bedrock runtime client created")
    return _bedrock_runtime_client


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def extract_first_json_object(text: str) -> Dict[str, Any]:
    """Extract first valid JSON object from model output."""
    if not text:
        raise json.JSONDecodeError("Empty model response", "", 0)

    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)

    try:
        return json.loads(t)
    except Exception:
        pass

    start = t.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object start found", t, 0)

    depth = 0
    for i in range(start, len(t)):
        ch = t[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = t[start : i + 1]
                return json.loads(candidate)

    raise json.JSONDecodeError("Unbalanced JSON braces", t, start)


def heuristic_intent_fallback(message: str) -> str:
    """Safer fallback intent when model response is unusable."""
    m = (message or "").lower()
    keywords = ["project", "job", "order", "schedule", "appointment", "book", "install", "work order", "ticket"]
    if any(k in m for k in keywords):
        return "scheduling"
    if "weather" in m or "forecast" in m:
        return "information"
    return "chitchat"


# ═══════════════════════════════════════════════════════════════════════════════
# FAST PATH
# ═══════════════════════════════════════════════════════════════════════════════

_FASTPATH_GREETINGS = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon"}
_FASTPATH_HELP = {"help", "what can you do", "how does this work", "?"}
_FASTPATH_THANKS = {"thanks", "thank you", "thx", "ty"}
_FASTPATH_BYE = {"bye", "goodbye", "see you", "later"}


def _fast_path(message: str) -> Optional[Dict[str, Any]]:
    """Handle trivial messages without LLM call."""
    m = (message or "").strip().lower()

    if m in _FASTPATH_GREETINGS:
        return _build_response("Greeting", None)
    if m in _FASTPATH_HELP:
        return _build_response("Help_Request", None)
    if m in _FASTPATH_THANKS:
        return _build_response("Thanks", None)
    if m in _FASTPATH_BYE:
        return _build_response("Farewell", None)
    if "weather" in m or "forecast" in m:
        loc_match = re.search(r"(?:weather|forecast)\s+(?:in|for|at)\s+(\w+(?:\s+\w+)?)", m)
        params = {"location": loc_match.group(1)} if loc_match else None
        return _build_response("Weather_Request", params)

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def _build_response(intent: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build standardized classification response from intent."""
    action = INTENT_ACTION_MAP.get(intent)

    category = "chitchat"
    for cat, intents in INTENT_CATEGORIES.items():
        if intent in intents:
            category = cat
            break

    return {
        "intent": category,
        "action": action,
        "can_call_direct": action is not None,
        "params": params,
        "_nlu_intent": intent,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT SUMMARIZER
# ═══════════════════════════════════════════════════════════════════════════════

def _summarize_history(conversation_history: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """Summarize conversation history and extract project IDs for ordinal resolution."""
    if not conversation_history:
        return "", []

    recent = conversation_history[-3:]
    lines = []
    all_project_ids = []

    for msg in recent:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = (msg.get("content") or "")

        if role == "Assistant":
            ids = []
            ids += re.findall(r'"id"\s*:\s*"?(\d+)"?', content)
            ids += re.findall(r"project\s*#?\s*(\d+)", content, flags=re.IGNORECASE)
            seen = set()
            for _id in ids:
                if _id not in seen:
                    seen.add(_id)
                    all_project_ids.append(_id)

            if ids:
                content = f"[Listed projects: {', '.join(ids[:10])}]"
            else:
                content = content[:500]
        else:
            content = content[:500]

        lines.append(f"{role}: {content}")

    context_str = "Recent conversation:\n" + "\n".join(lines) if lines else ""
    return context_str, all_project_ids


# ═══════════════════════════════════════════════════════════════════════════════
# NLU PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

NLU_PROMPT_TEMPLATE = """You are an NLU (Natural Language Understanding) system for a project scheduling assistant.

Analyze the user utterance and extract structured information.

## OUTPUT FORMAT (JSON only):
{{
  "intent": "<intent_name>",
  "parameters": {{...}},
  "confidence": "high" | "medium" | "low"
}}

## INTENT TAXONOMY

### Information Request Intents:
- **Project_List_Request**: User wants to see a LIST of projects
  Parameters: status, category, projectType, technician_name, address
  Exclusion: exclude_status, exclude_category, exclude_technician, exclude_address (arrays)
  Ordinal: ordinal (for "2nd kitchen project")

- **Project_Information_Request**: User wants DETAILS about a specific project
  Parameters: project_id OR category

- **Availability_Check**: User wants available DATES
  Parameters: project_id

- **Time_Slot_Check**: User wants available TIME SLOTS
  Parameters: date, project_id

### Action Request Intents:
- **Schedule_Request**: User wants to BOOK/SCHEDULE
  Parameters: project_id, date_preference, time_preference, relative_to

- **Reschedule_Request**: User wants to CHANGE appointment
  Parameters: project_id

- **Cancel_Request**: User wants to CANCEL
  Parameters: project_id

- **Appointment_Confirmation**: User CONFIRMING selection
  Parameters: date, time, slot_index

### Batch Intents:
- **Batch_Schedule_Request**: Schedule MULTIPLE projects
- **Batch_Cancel_Request**: Cancel MULTIPLE appointments
- **Batch_Reschedule_Request**: Reschedule MULTIPLE

### Comparative Intents:
- **Compare_Availability**: Compare scheduling across projects
- **Compare_Projects**: Compare project status

### Other:
- **Weather_Request**, **Greeting**, **Help_Request**, **Thanks**, **Farewell**

## PARAMETER EXTRACTION

### Exclusion (negation) - IMPORTANT:
When user says "except", "but not", "excluding", "other than", extract exclude_* parameters:
- "show all projects except kitchen" -> exclude_category: ["Kitchen"]
- "list projects but not the scheduled ones" -> exclude_status: ["Scheduled"]
- "show projects excluding Mildred's" -> exclude_technician: ["Mildred"]
- "projects except at 401 Chicago" -> exclude_address: ["401 Chicago"]
- "everything but the kitchen projects" -> exclude_category: ["Kitchen"]

CRITICAL: Do NOT use inclusion filters when user says "except/but not/excluding". Use exclude_* instead.

### Ordinal with filters:
- "2nd kitchen project" -> category: "Kitchen", ordinal: "second"
- "first project at Chicago" -> address: "Chicago", ordinal: "first"

### Preferences with fallback:
- "Tuesday if available, otherwise Wednesday" ->
  date_preference: {{"primary": "Tuesday", "fallback": ["Wednesday"]}}

### Relative scheduling:
- "after the dishwasher" ->
  relative_to: {{"anchor_project": "dishwasher", "relation": "after"}}

{context_section}

## USER UTTERANCE
"{message}"

Respond with JSON only."""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════

def classify_intent_and_action(
    message: str,
    conversation_history: Optional[List[Dict]] = None
) -> Dict:
    """
    NLU-style intent classification with structured parameter extraction.

    Returns:
        {
            "intent": "scheduling" | "information" | "chitchat",
            "action": action_name or null,
            "can_call_direct": boolean,
            "params": extracted parameters or null,
            "_nlu_intent": original NLU intent name
        }
    """
    # Fast path for trivial messages
    fp = _fast_path(message)
    if fp:
        logger.info(f"[FAST] {fp['_nlu_intent']} for: '{message[:50]}...'")
        return fp

    cfg = get_config()
    context_str, project_ids = _summarize_history(conversation_history or [])

    context_section = ""
    if context_str:
        context_section = f"\n## CONVERSATION CONTEXT\n{context_str}"
    if project_ids:
        context_section += f"\nProject IDs from context: [{', '.join(project_ids[:10])}]"

    prompt = NLU_PROMPT_TEMPLATE.format(
        context_section=context_section,
        message=message
    )

    classification_text = ""
    try:
        bedrock = get_bedrock_client()
        response = bedrock.invoke_model(
            modelId=cfg.orchestrator_model,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 400,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}],
            }),
        )

        response_body = json.loads(response["body"].read())
        classification_text = (response_body["content"][0]["text"] or "").strip()
        logger.info(f"Raw NLU response: {classification_text}")

        nlu_result = extract_first_json_object(classification_text)
        intent = nlu_result.get("intent", "")
        params = nlu_result.get("parameters")

        if intent not in INTENT_ACTION_MAP:
            logger.warning(f"Unknown intent '{intent}', using heuristic fallback")
            return {
                "intent": heuristic_intent_fallback(message),
                "action": None,
                "can_call_direct": False,
                "params": None,
            }

        result = _build_response(intent, params if params else None)

        if result["params"]:
            _normalize_params(result["params"])

        logger.info(f"[OK] NLU: {intent} -> {result['action']} for: '{message[:60]}...'")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse NLU JSON: {e}")
        return {
            "intent": heuristic_intent_fallback(message),
            "action": None,
            "can_call_direct": False,
            "params": None,
        }
    except Exception as e:
        logger.error(f"NLU error: {e}")
        return {
            "intent": heuristic_intent_fallback(message),
            "action": None,
            "can_call_direct": False,
            "params": None,
        }


def _normalize_params(params: Dict[str, Any]) -> None:
    """Normalize parameter values in-place."""
    if "status" in params:
        s = _norm(params["status"])
        if s in STATUS_ALIASES:
            params["status"] = STATUS_ALIASES[s]

    if "projectType" in params:
        pt = _norm(params["projectType"])
        if pt in PROJECT_TYPE_ALIASES:
            params["projectType"] = PROJECT_TYPE_ALIASES[pt]


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

_init_backward_compat()
