"""
NLU-Style Intent Classifier for ProjectForce

Architecture:
- Intent Taxonomy: Well-defined intents with clear semantics
- Parameter Extraction: Systematic slot filling from utterance
- Action Mapping: Intent → Lambda action (deterministic)

This replaces the fuzzy "intent + action in one prompt" approach with structured NLU.
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

logger = logging.getLogger()
_bedrock_runtime_client = None


# ═══════════════════════════════════════════════════════════════════════════════
# INTENT TAXONOMY
# ═══════════════════════════════════════════════════════════════════════════════

# Primary intents with their action mappings
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

    # Non-scheduling intents
    "Weather_Request": "get_weather",
    "Greeting": "greet",
    "Help_Request": "help",
    "Farewell": "general",
    "Thanks": "general",
}

# Intent categories for routing
INTENT_CATEGORIES = {
    "scheduling": {
        "Project_List_Request", "Project_Information_Request", "Availability_Check",
        "Time_Slot_Check", "Reschedule_Availability_Check", "Note_List_Request",
        "Schedule_Request", "Reschedule_Request", "Cancel_Request",
        "Appointment_Confirmation", "Note_Add_Request",
    },
    "information": {"Weather_Request"},
    "chitchat": {"Greeting", "Help_Request", "Farewell", "Thanks"},
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENTITY DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMIC STATUS & CATEGORY CONFIG (loaded from S3 via config_loader)
# ═══════════════════════════════════════════════════════════════════════════════
# These are now loaded dynamically from S3 config files.
# The functions below provide backward-compatible access.

def _get_schedulable_statuses():
    """Get schedulable statuses from external config."""
    return get_schedulable_statuses_safe()

def _get_scheduled_statuses():
    """Get scheduled statuses from external config."""
    return get_scheduled_statuses_safe()

def _get_category_buckets():
    """Get category buckets from external config."""
    return get_all_category_buckets_safe()

# Backward-compatible exports (computed on first access)
# These are kept for imports in other modules
SCHEDULABLE_STATUSES = None  # Will be populated on first use
SCHEDULED_STATUSES = None    # Will be populated on first use
CATEGORY_BUCKETS = None      # Will be populated on first use

def _init_backward_compat():
    """Initialize backward-compatible module-level variables."""
    global SCHEDULABLE_STATUSES, SCHEDULED_STATUSES, CATEGORY_BUCKETS
    if SCHEDULABLE_STATUSES is None:
        SCHEDULABLE_STATUSES = _get_schedulable_statuses()
    if SCHEDULED_STATUSES is None:
        SCHEDULED_STATUSES = _get_scheduled_statuses()
    if CATEGORY_BUCKETS is None:
        CATEGORY_BUCKETS = _get_category_buckets()

# Status aliases (user terms → canonical status)
STATUS_ALIASES = {
    # Schedulable
    "new": "New",
    "unscheduled": "New",
    "ready to schedule": "Ready To Schedule",
    "ready to go": "Ready To Schedule",
    "schedulable": "schedulable",  # Special: matches SCHEDULABLE_STATUSES
    "can schedule": "schedulable",
    "available to schedule": "schedulable",

    # Scheduled
    "scheduled": "Scheduled",
    "on the books": "Scheduled",
    "on the calendar": "Scheduled",
    "booked": "Scheduled",
    "tentatively scheduled": "Tentatively Scheduled",
    "tentative": "Tentatively Scheduled",

    # Other
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

# Project type aliases
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

def _norm(s: Any) -> str:
    """Normalize for case/whitespace-insensitive comparisons."""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip().lower())


def _get_field(obj: Dict[str, Any], candidates: List[str]) -> Any:
    """Retrieve first available field from dict using multiple candidate keys."""
    for k in candidates:
        if k in obj:
            return obj.get(k)
    return None


def extract_first_json_object(text: str) -> Dict[str, Any]:
    """Extract first valid JSON object from model output (handles code fences and extra text)."""
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
# POST-FILTERING (for upstream APIs that don't support filtering)
# ═══════════════════════════════════════════════════════════════════════════════

def apply_project_filters(projects: List[Dict[str, Any]], params: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply semantic filters to a list of project records.

    Supported params:
    - status: "schedulable", "scheduled", or exact status value
    - category: bucket name or exact category
    - projectType: exact type value
    """
    if not params:
        return projects

    out = projects

    # ---- STATUS FILTER ----
    status = params.get("status")
    if status:
        s = _norm(status)
        schedulable_statuses = _get_schedulable_statuses()
        scheduled_statuses = _get_scheduled_statuses()

        if s == "schedulable":
            out = [
                p for p in out
                if _get_field(p, ["Status", "status"]) in schedulable_statuses
                or _norm(_get_field(p, ["Status", "status"])) in {_norm(x) for x in schedulable_statuses}
            ]
        elif s == "scheduled":
            out = [
                p for p in out
                if _get_field(p, ["Status", "status"]) in scheduled_statuses
                or _norm(_get_field(p, ["Status", "status"])) in {_norm(x) for x in scheduled_statuses}
            ]
        else:
            out = [
                p for p in out
                if _norm(_get_field(p, ["Status", "status"])) == s
            ]

    # ---- CATEGORY FILTER ----
    category = params.get("category")
    if category:
        c = _norm(category)
        category_buckets = _get_category_buckets()

        # Helper: check if project category matches any keyword in bucket (partial match)
        def _matches_bucket(proj_category: str, bucket_keywords: set) -> bool:
            """Check if project category contains any bucket keyword or vice versa."""
            pc = _norm(proj_category)
            for kw in bucket_keywords:
                # Match if keyword is in category OR category is in keyword
                # e.g., "door" in "exterior doors" OR "exterior door" == "exterior doors" (close enough)
                if kw in pc or pc in kw:
                    return True
            return False

        if c in category_buckets:
            # Direct bucket name match (e.g., "kitchen", "fencing")
            allowed = category_buckets[c]
            logger.info(f"[FILTER] Using bucket '{c}' with {len(allowed)} keywords")
            out = [
                p for p in out
                if _matches_bucket(_get_field(p, ["Category", "category"]) or "", allowed)
            ]
        else:
            # Check if term is a keyword in any bucket (e.g., "fence" → "fencing" bucket)
            resolved_bucket = find_category_bucket_for_keyword(c)
            if resolved_bucket and resolved_bucket in category_buckets:
                allowed = category_buckets[resolved_bucket]
                logger.info(f"[FILTER] Resolved keyword '{c}' to bucket '{resolved_bucket}' with {len(allowed)} keywords")
                out = [
                    p for p in out
                    if _matches_bucket(_get_field(p, ["Category", "category"]) or "", allowed)
                ]
            else:
                # Fall back to partial match on category value
                # (e.g., "fence" matches "Fence Installation", "fence repair", etc.)
                logger.info(f"[FILTER] No bucket match for '{c}', using partial match")
                out = [
                    p for p in out
                    if c in _norm(_get_field(p, ["Category", "category"]) or "")
                ]

    # ---- PROJECT TYPE FILTER ----
    project_type = params.get("projectType")
    if project_type:
        pt = _norm(project_type)
        out = [
            p for p in out
            if _norm(_get_field(p, ["Type", "type", "projectType"])) == pt
        ]

    # ---- TECHNICIAN/INSTALLER FILTER ----
    # Check both 'technician_name' (NLU) and 'assignee' (Sonnet enricher)
    technician_name = params.get("technician_name") or params.get("assignee")
    if technician_name:
        tn = _norm(technician_name)
        logger.info(f"[FILTER] Filtering by technician_name: '{technician_name}'")

        def _get_installer_name(project: Dict) -> str:
            """Extract installer/technician name from project."""
            # Check 'installer' object (from list_projects format)
            installer = project.get('installer', {})
            if isinstance(installer, dict):
                name = installer.get('name', '')
                if name:
                    return name
            # Check 'technician' object (from get_project_details format)
            technician = project.get('technician', {})
            if isinstance(technician, dict):
                name = technician.get('name', '')
                if name:
                    return name
            return ''

        out = [
            p for p in out
            if tn in _norm(_get_installer_name(p))
        ]
        logger.info(f"[FILTER] After technician filter: {len(out)} projects")

    # ---- ADDRESS FILTER ----
    address = params.get("address")
    if address:
        addr = _norm(address)
        logger.info(f"[FILTER] Filtering by address: '{address}'")

        def _get_address_string(project: Dict) -> str:
            """Extract address as searchable string from project."""
            addr_field = project.get('address', project.get('Address', ''))
            if isinstance(addr_field, str):
                return addr_field
            if isinstance(addr_field, dict):
                # Handle object format: {street, city, state, zip}
                parts = [
                    addr_field.get('street', ''),
                    addr_field.get('address', ''),  # Some APIs use 'address' inside object
                    addr_field.get('city', ''),
                    addr_field.get('state', ''),
                    addr_field.get('zip', ''),
                ]
                return ' '.join(p for p in parts if p)
            return ''

        out = [
            p for p in out
            if addr in _norm(_get_address_string(p))
        ]
        logger.info(f"[FILTER] After address filter: {len(out)} projects")

    return out


# ═══════════════════════════════════════════════════════════════════════════════
# FAST PATH (deterministic, no LLM needed)
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
        # Extract location if present
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

    # Determine category
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
        "_nlu_intent": intent,  # Keep for debugging
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT SUMMARIZER
# ═══════════════════════════════════════════════════════════════════════════════

def _summarize_history(conversation_history: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """
    Summarize conversation history and extract project IDs for ordinal resolution.
    Returns: (context_string, list_of_project_ids)
    """
    if not conversation_history:
        return "", []

    recent = conversation_history[-3:]
    lines = []
    all_project_ids = []

    for msg in recent:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = (msg.get("content") or "")

        if role == "Assistant":
            # Extract project IDs from assistant responses
            ids = []
            ids += re.findall(r'"id"\s*:\s*"?(\d+)"?', content)
            ids += re.findall(r"project\s*#?\s*(\d+)", content, flags=re.IGNORECASE)
            # De-dup preserve order
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

### Information Request Intents (user wants to VIEW/CHECK data):
- **Project_List_Request**: User wants to see a LIST of projects
  Triggers: "show my projects", "list jobs", "what projects do I have", "display orders"
  Parameters: status, category, projectType, technician_name, address (optional filters)
  Notes:
    - technician_name: filter by assigned technician/installer (e.g., "projects assigned to John")
    - address: filter by installation address (e.g., "projects at 401 Chicago Avenue", "orders at Main Street")

- **Project_Information_Request**: User wants DETAILS about a specific project or category
  Triggers: "details for X", "tell me about X", "what is this X project about", "show me X project"
  Parameters: project_id OR category, information_type (overview/schedule/status)

- **Availability_Check**: User wants to see available DATES for scheduling
  Triggers: "what dates are available", "when can I schedule", "show dates for project X"
  Parameters: project_id

- **Time_Slot_Check**: User wants to see available TIME SLOTS on a specific date
  Triggers: "what times on Nov 14", "show slots for tomorrow", "available times"
  Parameters: date, project_id

- **Note_List_Request**: User wants to see notes on a project
  Triggers: "show notes for project X", "list notes"
  Parameters: project_id

### Action Request Intents (user wants to CHANGE something):
- **Schedule_Request**: User wants to BOOK/SCHEDULE a project
  Triggers: "schedule project X", "book me in", "set up appointment", "get this scheduled"
  Parameters: project_id

- **Reschedule_Request**: User wants to CHANGE an existing appointment
  Triggers: "reschedule project X", "move my appointment", "change the time"
  Parameters: project_id

- **Cancel_Request**: User wants to CANCEL an appointment
  Triggers: "cancel project X", "cancel my appointment", "I can't make it"
  Parameters: project_id

- **Appointment_Confirmation**: User is CONFIRMING a date/time selection
  Triggers: "2pm", "Nov 25", "the first one", "yes that works"
  Parameters: date, time, slot_index

- **Note_Add_Request**: User wants to ADD a note to a project
  Triggers: "add a note to project X", "add note"
  Parameters: project_id, note_text

### Other Intents:
- **Weather_Request**: User asks about weather
- **Greeting**: "hello", "hi", "hey"
- **Help_Request**: "help", "what can you do"
- **Thanks**: "thank you", "thanks"
- **Farewell**: "bye", "goodbye"

## PARAMETER EXTRACTION

### project_id:
- Extract project references EXACTLY as written by the user (preserve complete format)
- Project IDs can be ANY format: numeric ("90000087"), alphanumeric ("AI-PRO-1000010"), or complex ("21083_09PF05VD_123")
- Examples:
  * "AI-PRO-1000010 status" → project_id: "AI-PRO-1000010"
  * "project 90000087" → project_id: "90000087"
  * "what about 21083_09PF05VD_123" → project_id: "21083_09PF05VD_123"
- NEVER strip prefixes or modify the ID format - extract it exactly as the user wrote it
- Resolve ordinals from context: "2nd project" → use ID from history
- If ordinal cannot be resolved, set project_id: null

### category:
IMPORTANT: The category value depends on the intent:

For **Project_List_Request** (filtering a list): Use BUCKET names
  * Kitchen, Windows, Decking, Flooring, Bathroom
  * Example: "show my kitchen projects" → category="Kitchen"

For **Project_Information_Request** (specific project details): Use EXACT category name
  * Preserve the exact category mentioned by user
  * "Dishwasher" → category="Dishwasher" (NOT "Kitchen")
  * "Electric Cooktop" → category="Electric Cooktop" (NOT "Kitchen")
  * "Storm Door" → category="Storm Door" (NOT "Windows")
  * "Exterior Doors" → category="Exterior Doors" (NOT "Windows")
  * Example: "details for dishwasher project" → category="Dishwasher"
  * Example: "what is this electric cooktop project about" → category="Electric Cooktop"

### status (for filtering):
- "schedulable", "can schedule", "available to schedule" → "schedulable"
- "scheduled", "on the books", "booked" → "Scheduled"
- "new", "unscheduled" → "New"
- "ready to schedule", "ready to go" → "Ready To Schedule"

### date/time:
- Extract date mentions: "Nov 14", "tomorrow", "next Tuesday"
- Extract time mentions: "2pm", "morning", "afternoon"

## CRITICAL DISTINCTIONS

**Project_List_Request vs Project_Information_Request:**
- "show my projects" → Project_List_Request (wants a LIST)
- "show my kitchen projects" → Project_List_Request with category="Kitchen" (bucket name)
- "details for dishwasher project" → Project_Information_Request with category="Dishwasher" (EXACT name)
- "what is this electric cooktop project about" → Project_Information_Request with category="Electric Cooktop" (EXACT name)
- "tell me about the storm door" → Project_Information_Request with category="Storm Door" (EXACT name)

**Availability_Check vs Schedule_Request:**
- "what dates are available" → Availability_Check (ASKING, not booking)
- "schedule it for Nov 14" → Schedule_Request (BOOKING)

{context_section}

## USER UTTERANCE
"{message}"

Respond with JSON only."""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════

def classify_intent_and_action(message: str, conversation_history: Optional[List[Dict]] = None) -> Dict:
    """
    NLU-style intent classification with structured parameter extraction.

    Returns:
        {
            "intent": "scheduling" | "information" | "chitchat",
            "action": action_name or null,
            "can_call_direct": boolean,
            "params": extracted parameters or null,
            "_nlu_intent": original NLU intent name (for debugging)
        }
    """
    # Fast path for trivial messages
    fp = _fast_path(message)
    if fp:
        logger.info(f"[FAST] {fp['_nlu_intent']} for: '{message[:50]}...'")
        return fp

    cfg = get_config()
    context_str, project_ids = _summarize_history(conversation_history or [])

    # Build context section for prompt
    context_section = ""
    if context_str:
        context_section = f"\n## CONVERSATION CONTEXT\n{context_str}"
    if project_ids:
        context_section += f"\nProject IDs from context (for ordinal resolution): [{', '.join(project_ids[:10])}]"

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

        # Validate intent exists
        if intent not in INTENT_ACTION_MAP:
            logger.warning(f"Unknown intent '{intent}', using heuristic fallback")
            return {
                "intent": heuristic_intent_fallback(message),
                "action": None,
                "can_call_direct": False,
                "params": None,
            }

        # Build response
        result = _build_response(intent, params if params else None)

        # Post-process: normalize status/category values
        if result["params"]:
            _normalize_params(result["params"])

        logger.info(f"[OK] NLU: {intent} → {result['action']} for: '{message[:60]}...'")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse NLU JSON: {e}")
        logger.error(f"NLU text: {classification_text or 'N/A'}")
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
    # Normalize status
    if "status" in params:
        s = _norm(params["status"])
        if s in STATUS_ALIASES:
            params["status"] = STATUS_ALIASES[s]

    # Normalize projectType
    if "projectType" in params:
        pt = _norm(params["projectType"])
        if pt in PROJECT_TYPE_ALIASES:
            params["projectType"] = PROJECT_TYPE_ALIASES[pt]


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════
# Initialize backward-compatible module-level variables at import time.
# This ensures CATEGORY_BUCKETS, SCHEDULED_STATUSES, etc. are populated
# when other modules import them.

_init_backward_compat()
