"""
Intent and Action Classification using Claude Sonnet
Extracted from pf_proxy.py for production Lambda use
"""
import json
import re
import logging
from typing import Dict, List, Optional
import boto3
from botocore.config import Config as BotoConfig

from config import get_config

logger = logging.getLogger()

# Boto3 client singleton (reused across Lambda invocations)
_bedrock_runtime_client = None


def get_bedrock_client():
    """Get or create Bedrock runtime client with connection pooling"""
    global _bedrock_runtime_client
    if _bedrock_runtime_client is None:
        config = get_config()
        boto_config = BotoConfig(
            region_name=config.region,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        _bedrock_runtime_client = boto3.client('bedrock-runtime', config=boto_config)
        logger.info("Bedrock runtime client created")
    return _bedrock_runtime_client


def classify_intent_and_action(message: str, conversation_history: Optional[List[Dict]] = None) -> Dict:
    """
    Enhanced intent and action classification using Claude Sonnet with conversation context

    Args:
        message: Current user message
        conversation_history: List of previous messages with role/content

    Returns:
        Dictionary with:
        - intent: scheduling/information/chitchat
        - action: specific action name (or null if needs agent)
        - can_call_direct: true/false
        - params: extracted parameters (or null if none)

    Examples:
        >>> classify_intent_and_action("show my projects")
        {'intent': 'scheduling', 'action': 'list_projects', 'can_call_direct': True, 'params': None}

        >>> classify_intent_and_action("show scheduled projects")
        {'intent': 'scheduling', 'action': 'list_projects', 'can_call_direct': True, 'params': {'status': 'Scheduled'}}

        >>> classify_intent_and_action("schedule project 123")
        {'intent': 'scheduling', 'action': None, 'can_call_direct': False, 'params': None}
    """
    config = get_config()

    # Build context from conversation history
    context_str = ""
    if conversation_history and len(conversation_history) > 0:
        context_str = "\n\nConversation history (most recent last):\n"
        # Include last 3 messages for context
        recent_history = conversation_history[-3:]

        for msg in recent_history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            content = msg['content']

            # For assistant messages with JSON, extract just project IDs for efficiency
            if role == "Assistant" and '"projects"' in content and len(content) > 1000:
                try:
                    # Try to extract JSON from markdown code block
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        json_str = content

                    data = json.loads(json_str)
                    project_ids = [str(p['id']) for p in data.get('projects', [])]
                    if project_ids:
                        content = f"[Project list with IDs: {', '.join(project_ids[:10])}]"
                except Exception as e:
                    logger.warning(f"JSON parsing failed, using regex fallback: {e}")
                    project_ids = re.findall(r'"projects"\s*:\s*\[(?:[^]]*?"id"\s*:\s*"(\d+)"[^]]*?)+\]', content)
                    if project_ids:
                        content = f"[Project list with IDs: {', '.join(project_ids[:10])}]"
            else:
                content = content[:500]  # Truncate for context efficiency

            context_str += f"{role}: {content}\n"

    prompt = f"""You are an intent classifier for a property management scheduling system.

Classify the user message and determine if we can call Lambda directly or need an agent.
{context_str}
Current user message: "{message}"

Respond in JSON format with FOUR fields:
1. intent: scheduling/information/chitchat
2. action: specific action name (or null if needs agent conversation)
3. can_call_direct: true/false
4. params: object with extracted parameters (or null if none)

** INDUSTRY TERMINOLOGY MAPPING **

The user may use contractor/customer industry slang. Map these to the correct actions:

PROJECT SYNONYMS (all refer to projects):
- "job/jobs" = projects (e.g., "show my jobs" = "show my projects")
- "order/orders" = projects (e.g., "what orders can I schedule" = "what projects can I schedule")
- "install/installs" = projects, often type=Installation
- "work order/work orders" = projects
- "ticket/tickets" = projects
- "booking/bookings" = projects with appointments
- "service call" = project (often type=Repair or Call Back)
- "appointment/appointments" = scheduled projects

CATEGORY KEYWORDS (map to category filter):
- Flooring: "floor", "flooring", "hardwood", "carpet", "LVP", "luxury vinyl", "vinyl", "tile", "laminate"
- Decking: "deck", "decking", "patio", "composite", "outdoor", "pergola"
- Kitchen: "cabinet", "cabinets", "countertop", "granite", "quartz", "kitchen reno", "kitchen remodel", "backsplash", "sink", "kitchen sink"
- Windows: "window", "windows", "patio door", "sliding door", "replacement window"
- Door: "door", "doors", "entry door", "storm door", "screen door", "exterior door", "interior door"
- Bathroom: "bathroom", "bath", "bathroom remodel"
- Dishwasher: "dishwasher"
- Ovens: "oven", "ovens", "range", "stove"
- Washer Dryer: "washer", "dryer", "washer dryer", "laundry"
- Cooktop: "cooktop", "electric cooktop", "stovetop", "burner"
- Millwork: "millwork", "trim", "molding", "moulding", "baseboard", "crown molding", "wainscoting", "mantel", "mantle", "staircase", "stairs", "railing", "custom woodwork", "wood trim"
- Floor Installation: "floor installation", "floor install" (maps to Flooring)

SCHEDULING PHRASES:
- "book me in" / "get me booked" / "get me scheduled" = schedule_project
- "when are they coming?" / "when are they coming out?" = get_project_details (asking for scheduled date)
- "what's my slot?" / "when's my slot?" = get_project_details or get_time_slots
- "what's on the calendar?" / "what's on the books?" = list_projects with status=Scheduled

STATUS PHRASES:
- "ready to go" = status: Ready To Schedule
- "on the books" / "on the calendar" = status: Scheduled
- "waiting" / "in the queue" = status: Pending
- "done" / "finished" = status: Completed
- "underway" = status: In Progress

** INTENT CATEGORIES **

**SCHEDULING intent:**
- Anything related to projects, appointments, dates, times, booking, project notes
- Includes industry terms: jobs, installs, work orders, tickets, bookings, service calls
- Examples: "show my projects", "show my jobs", "list my installs", "schedule project 123", "book me in"

**INFORMATION intent:**
- Weather queries ONLY
- External data queries (NOT project-related)
- Examples: "what's the weather", "weather in Tampa", "forecast for tomorrow"

**CHITCHAT intent:**
- Greetings, thanks, casual conversation
- Examples: "hello", "thank you", "how are you"

** CRITICAL RULE: UNDERSTAND SEMANTIC INTENT **

Think about what the user is TRYING TO DO, not just the words they use:

**QUERY Intent (can_call_direct=TRUE):**
- User wants to SEE/VIEW/GET information
- User is ASKING ABOUT something
- User wants to KNOW/CHECK/DISPLAY data
- Examples of query intent:
  * "show my projects" (wants to VIEW)
  * "what projects do I have" (wants to KNOW)
  * "details for project 123" (wants to SEE)
  * "available dates for project 456" (wants to CHECK)
  * "what times are free on Nov 14" (wants to KNOW)

**ACTION Intent (can_call_direct=FALSE):**
- User wants to DO something / MAKE A CHANGE
- User wants to CREATE/MODIFY/DELETE an appointment
- User is requesting an operation that changes state
- User needs confirmation before proceeding
- Examples of action intent:
  * "schedule project 123" (wants to CREATE appointment)
  * "book the last project" (wants to CREATE appointment)
  * "I want to set up an appointment" (wants to CREATE)
  * "reschedule my meeting" (wants to MODIFY)
  * "cancel my appointment" (wants to DELETE)
  * "let's go with Nov 14" (implicit booking confirmation)
  * "yes, book it" (confirmation of action)

**How to decide:**
1. Ask yourself: "Is the user asking for information, or asking to do something?"
2. If ASKING FOR INFO -> can_call_direct=true
3. If REQUESTING AN ACTION -> can_call_direct=false

Even if the message doesn't contain explicit action verbs, use semantic understanding:
- "I'll take project 123 for tomorrow" -> ACTION (implied booking)
- "Can you tell me about project 123" -> QUERY (asking for info)
- "Let's go with 2pm on Friday" -> ACTION (implicit confirmation)
- "What times work for Friday" -> QUERY (asking for info)

DIRECT Lambda actions:

**CHITCHAT actions (always can_call_direct=true):**
greet:
- Examples: "hi", "hello", "hey", "good morning"
- Response: intent=chitchat, action=greet, can_call_direct=true, params=null

help:
- Examples: "help", "what can you do", "how does this work"
- Response: intent=chitchat, action=help, can_call_direct=true, params=null

general:
- Examples: "thank you", "thanks", "bye", "goodbye"
- Response: intent=chitchat, action=general, can_call_direct=true, params=null

**INFORMATION actions (always can_call_direct=true):**
get_weather:
- Examples: "weather in Tampa", "what's the weather", "forecast for tomorrow"
- Extract location from message if mentioned
- Response: intent=information, action=get_weather, can_call_direct=true, params={{"location":"..."}} if found

**SCHEDULING QUERY actions (simple data retrieval):**

list_projects:
- Examples: "show my projects", "list projects", "what projects do I have", "display projects"
- ALSO RECOGNIZES (industry terms): "show my jobs", "show my orders", "what orders can I schedule",
  "list my installs", "what work orders do I have", "my appointments", "my service calls",
  "show my floor jobs", "my deck work", "what's on the books"
- MUST be pure queries (show/list/get/display/what)
- NO action verbs allowed
- IMPORTANT: Extract filter parameters if mentioned:
  * status: "scheduled", "unscheduled", "new", "completed", "pending", "on the books", "ready to go", etc.
    - "unscheduled" = projects with status "New" (not yet scheduled)
    - "scheduled" / "on the books" / "on the calendar" = projects with status "Scheduled" (have appointment)
    - "ready to go" = status "Ready To Schedule"
    Examples: "show scheduled projects", "what's on the books", "show unscheduled projects", "list new projects"
  * category: "Decking", "Flooring", "Kitchen", "Bathroom", "Windows", etc.
    - Flooring keywords: floor, flooring, hardwood, carpet, LVP, vinyl, tile, laminate
    - Decking keywords: deck, decking, patio, composite, outdoor
    - Kitchen keywords: cabinet, countertop, granite, quartz, kitchen reno
    - Windows keywords: window, door, replacement
    Examples: "show decking projects", "my flooring jobs", "hardwood installs", "my deck jobs", "cabinet work"
  * projectType: "Call Back", "Installation", "Repair", "Measurement", etc.
    - "install/installs" often implies type=Installation
    - "service call" often implies type=Repair or Call Back
    Examples: "list call back projects", "show installation jobs", "my repair work"
- Response: intent=scheduling, action=list_projects, can_call_direct=true, params={{status/category/projectType if found, otherwise null}}

get_project_details:
- Examples: "show details for 7751742", "details for project 123", "show me project 7751742"
- ALSO RECOGNIZES: "tell me about that job", "details for the install", "what's happening with my floor job?",
  "when are they coming?", "when are they coming out?", "what's my slot?"
- MUST be pure queries
- CRITICAL FOR POSITION REFERENCES: "2nd project", "3rd one", "first project", "details for 2", "that job", "the install"
- When user uses ordinal/position reference (1st, 2nd, 3rd, first, second, etc):
  * Look in conversation history for project IDs
  * Extract the Nth project ID from that list
  * DO NOT use the number as project_id - extract the actual ID!
  * Example: History has [7751741, 7751742, 7751743], user says "2nd project" -> use "7751742"
- If you CANNOT find project IDs in history for a position reference:
  * Set can_call_direct=false (needs agent to handle ambiguity)
- Response: intent=scheduling, action=get_project_details, can_call_direct=true, params with ACTUAL project_id

get_available_dates:
- Examples: "show dates for project 123", "available dates", "when can I schedule project 456", "what dates are available"
- MUST be pure queries asking ABOUT availability (not BOOKING)
- Extract project_id if mentioned
- Response: intent=scheduling, action=get_available_dates, can_call_direct=true, params with project_id if found

get_time_slots:
- Examples: "show times for Nov 14", "available slots for Nov 14", "what times on November 14"
- ONLY when user is ASKING about time slots, NOT booking
- Extract date from message
- CRITICAL: If conversation history shows available dates for a project, extract that project_id too
- Response: intent=scheduling, action=get_time_slots, can_call_direct=true, params with date AND project_id if found in context

**SCHEDULING WORKFLOW actions (multi-step but using Lambda orchestration):**
schedule_project:
- Examples: "schedule it", "book project 123", "I want to schedule", "schedule the last one"
- ALSO RECOGNIZES: "book me in", "get me booked", "get me scheduled", "set up an appointment",
  "get this on the calendar", "when can they come out?", "let's get this scheduled"
- This triggers a multi-step workflow managed by Lambda (not Bedrock)
- Response: intent=scheduling, action=schedule_project, can_call_direct=true, params={{"project_id":"..."}}

confirm_appointment:
- Examples: "2pm", "Nov 25", "the first one" (when responding to date/time selection)
- Response: intent=scheduling, action=confirm_appointment, can_call_direct=true, params extracted

reschedule_appointment:
- Examples: "reschedule project 123", "change my appointment", "I need to reschedule", "move my appointment"
- ALSO RECOGNIZES: "move my install", "change the time", "push it back", "can we move it?",
  "need a different time", "that date doesn't work", "change my booking"
- This initiates a reschedule flow: cancel existing -> get new slots -> confirm new appointment
- Response: intent=scheduling, action=reschedule_appointment, can_call_direct=true, params={{"project_id":"..."}}

cancel_appointment:
- Examples: "cancel my appointment", "cancel project 123", "I need to cancel", "cancel the booking"
- ALSO RECOGNIZES: "cancel the install", "cancel my job", "I can't make it", "need to cancel",
  "scratch that appointment", "remove the booking"
- Response: intent=scheduling, action=cancel_appointment, can_call_direct=true, params={{"project_id":"..."}}

get_rescheduler_slots:
- Examples: "what dates are available to reschedule?", "show reschedule options", "when can I reschedule to?"
- Use when user explicitly asks about rescheduling availability (not regular scheduling)
- Response: intent=scheduling, action=get_rescheduler_slots, can_call_direct=true, params={{"project_id":"...", "date":"YYYY-MM-DD" if mentioned}}

add_note:
- Examples: "add a note to project 123", "add note"
- Response: intent=scheduling, action=add_note, can_call_direct=true, params={{"project_id":"..."}}

list_notes:
- Examples: "show notes for project 123", "list notes"
- Response: intent=scheduling, action=list_notes, can_call_direct=true, params={{"project_id":"..."}}

[OK] ALL intents now use can_call_direct=TRUE (NO Bedrock agents)

Example JSON responses (respond with VALID JSON only):

Example 1 - Query intent (Direct Lambda):
For "show details for 7751742":
{{"intent":"scheduling","action":"get_project_details","can_call_direct":true,"params":{{"project_id":"7751742"}}}}
Reasoning: User wants to VIEW information -> QUERY

Example 2 - Query with position reference (Direct Lambda):
History shows: projects with ids ["7751741", "7751742", "7751743", ...]
For "show me the 3rd project":
{{"intent":"scheduling","action":"get_project_details","can_call_direct":true,"params":{{"project_id":"7751743"}}}}
Reasoning: User wants to SEE info -> QUERY. "3rd project" = id at index 2 = "7751743"

Example 3 - Schedule action (Lambda Workflow):
For "schedule the last project":
{{"intent":"scheduling","action":"schedule_project","can_call_direct":true,"params":{{"project_id":"7751743"}}}}
Reasoning: User wants to CREATE appointment -> triggers Lambda workflow orchestration (multi-step)

Example 4 - Time selection in workflow:
For "2pm" (when previous message showed time slots):
{{"intent":"scheduling","action":"confirm_appointment","can_call_direct":true,"params":{{"time":"2pm"}}}}
Reasoning: User selecting time slot -> part of workflow, handled by Lambda

Example 5 - Query about availability (Direct Lambda):
For "what dates are free for project 123":
{{"intent":"scheduling","action":"get_available_dates","can_call_direct":true,"params":{{"project_id":"123"}}}}
Reasoning: User wants to CHECK availability -> QUERY (asking, not booking)

Example 6 - Confirmation intent (Agent):
For "yes, that works":
{{"intent":"scheduling","action":null,"can_call_direct":false,"params":null}}
Reasoning: Confirmation of previous action -> needs agent context

Example 7 - Query with conversational phrasing (Direct Lambda):
For "can you tell me what projects I have":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":null}}
Reasoning: Polite phrasing but semantic intent is VIEW/GET info -> QUERY

Example 8 - Information intent (Direct Lambda):
For "what's the weather in Tampa":
{{"intent":"information","action":"get_weather","can_call_direct":true,"params":{{"location":"Tampa"}}}}
Reasoning: Weather query -> INFORMATION intent (call pf-information-actions directly)

Example 9 - Chitchat (Direct Lambda):
For "hello":
{{"intent":"chitchat","action":"greet","can_call_direct":true,"params":null}}
Reasoning: Greeting -> CHITCHAT intent (call pf-chitchat-actions directly)

Example 10 - Query with status filter (Direct Lambda):
For "show the scheduled projects":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":{{"status":"Scheduled"}}}}
Reasoning: User wants to VIEW filtered list -> QUERY with filter

Example 11 - Query with category filter (Direct Lambda):
For "list my decking projects":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":{{"category":"Decking"}}}}
Reasoning: User wants to VIEW category-specific projects -> QUERY with filter

Example 12 - Query with multiple filters (Direct Lambda):
For "show scheduled decking projects":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":{{"status":"Scheduled","category":"Decking"}}}}
Reasoning: User wants to VIEW with multiple filters -> QUERY with multiple params

Example 13 - Industry term "jobs" (Direct Lambda):
For "show my jobs":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":null}}
Reasoning: "jobs" = "projects" in industry terminology -> list_projects

Example 13b - Industry term "orders" (Direct Lambda):
For "what orders can I schedule":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":{{"status":"New"}}}}
Reasoning: "orders" = "projects", "can I schedule" implies unscheduled/New status -> list_projects with filter

Example 14 - Industry term with category (Direct Lambda):
For "my hardwood installs":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":{{"category":"Flooring"}}}}
Reasoning: "hardwood" maps to Flooring category, "installs" = projects

Example 15 - Industry scheduling phrase (Direct Lambda):
For "book me in for next week":
{{"intent":"scheduling","action":"schedule_project","can_call_direct":true,"params":null}}
Reasoning: "book me in" = schedule_project trigger

Example 16 - Industry status phrase (Direct Lambda):
For "what's on the books":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":{{"status":"Scheduled"}}}}
Reasoning: "on the books" = scheduled status filter

Example 17 - Deck work query (Direct Lambda):
For "show my deck jobs":
{{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":{{"category":"Decking"}}}}
Reasoning: "deck" maps to Decking category, "jobs" = projects

Remember: Focus on WHAT THE USER WANTS TO ACCOMPLISH, not the exact words they use.
Weather queries ALWAYS go to "information" intent, NOT "chitchat".
For filters: Match natural language to field values (e.g., "scheduled" -> "Scheduled", "call back" -> "Call Back").

** CRITICAL: For list_projects action, ALWAYS extract filter parameters from the user message **

Analyze the current user message: "{message}"

Step 1: Identify the intent (scheduling/information/chitchat)
Step 2: Identify the action (list_projects/get_project_details/etc)
Step 3: Extract ANY filters mentioned in the message:
   STATUS FILTERS:
   - "scheduled" / "on the books" / "on the calendar" -> {{"status":"Scheduled"}}
   - "ready to schedule" / "ready to go" -> {{"status":"Ready To Schedule"}}
   - "new" / "unscheduled" -> {{"status":"New"}}
   - "completed" / "done" / "finished" -> {{"status":"Completed"}}
   - "pending" / "waiting" / "in the queue" -> {{"status":"Pending"}}
   - "in progress" / "underway" -> {{"status":"In Progress"}}

   CATEGORY FILTERS (industry terms):
   - "decking" / "deck" / "patio" / "composite" -> {{"category":"Decking"}}
   - "flooring" / "floor" / "hardwood" / "carpet" / "LVP" / "tile" / "laminate" / "vinyl" -> {{"category":"Flooring"}}
   - "kitchen" / "cabinet" / "countertop" / "granite" / "quartz" / "sink" / "kitchen sink" -> {{"category":"Kitchen"}}
   - "window" / "windows" / "replacement window" / "patio door" / "sliding door" -> {{"category":"Windows"}}
   - "door" / "doors" / "entry door" / "storm door" / "screen door" / "exterior door" / "interior door" -> {{"category":"Door"}}
   - "bathroom" / "bath" -> {{"category":"Bathroom"}}
   - "dishwasher" -> {{"category":"Dishwasher"}}
   - "oven" / "ovens" / "range" / "stove" -> {{"category":"Ovens"}}
   - "washer" / "dryer" / "washer dryer" / "laundry" -> {{"category":"Washer Dryer"}}
   - "cooktop" / "electric cooktop" / "stovetop" / "burner" -> {{"category":"ELECTRIC COOKTOP"}}
   - "millwork" / "trim" / "molding" / "moulding" / "baseboard" / "crown molding" / "wainscoting" / "mantel" / "staircase" / "stairs" / "railing" / "custom woodwork" / "wood trim" -> {{"category":"Millwork"}}
   - "floor installation" / "floor install" -> {{"category":"Flooring"}}

   PROJECT TYPE FILTERS:
   - "call back" / "callback" -> {{"projectType":"Call Back"}}
   - "installation" / "install" -> {{"projectType":"Installation"}}
   - "repair" / "service call" -> {{"projectType":"Repair"}}
   - "measurement" -> {{"projectType":"Measurement"}}

   - If NO filters mentioned -> params should be null

Respond ONLY with the JSON object, nothing else."""

    try:
        bedrock_runtime = get_bedrock_client()

        # Use Sonnet 3.7 for superior classification accuracy
        response = bedrock_runtime.invoke_model(
            modelId=config.orchestrator_model,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,  # More tokens for complex reasoning
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        classification_text = response_body['content'][0]['text'].strip()

        logger.info(f"Raw classification response: {classification_text}")

        # Parse JSON response
        classification = json.loads(classification_text)

        logger.info(f"[OK] Classification: {classification} for message: '{message[:50]}...'")
        return classification

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse classification JSON: {e}")
        logger.error(f"Classification text: {classification_text if 'classification_text' in locals() else 'N/A'}")
        # Fallback: chitchat intent, requires agent
        return {
            'intent': 'chitchat',
            'action': None,
            'can_call_direct': False,
            'params': None
        }
    except Exception as e:
        logger.error(f"Classification error: {e}")
        # Fallback: chitchat intent, requires agent
        return {
            'intent': 'chitchat',
            'action': None,
            'can_call_direct': False,
            'params': None
        }
