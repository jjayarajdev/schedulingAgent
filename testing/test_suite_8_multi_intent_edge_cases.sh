#!/bin/bash
# Test Suite 8: Multi-Intent & Complex Query Edge Cases
# Covers: Hybrid queries, conditional logic, sequential multi-step, multiple entities
#
# Purpose: Test system robustness with complex, ambiguous, or multi-intent messages
# Expected behavior: System should either handle gracefully OR provide clear error/clarification

source test_config.sh

SESSION_ID="test-suite-8-$(date +%s)"
RESULTS_FILE="test_suite_8_results_$(date +%Y%m%d_%H%M%S).json"

echo ""
echo "=========================================="
echo "Test Suite 8: Multi-Intent Edge Cases"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo "Results will be saved to: $RESULTS_FILE"
echo ""
echo "⚠️  NOTE: These are edge cases. Some may not work as expected."
echo "    We're testing to understand current system behavior."
echo ""

# Helper function to make API call and log results
test_call() {
    local test_num="$1"
    local test_name="$2"
    local message="$3"
    local expected_behavior="$4"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 Test 8.${test_num}: ${test_name}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "User Message: \"${message}\""
    echo "Expected Behavior: ${expected_behavior}"
    echo ""
    echo "Response:"
    echo "---"

    response=$(curl -s -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{
        "message": "'"$message"'",
        "session_id": "'"$SESSION_ID"'",
        "pf_token": "'"$PF_TOKEN"'",
        "pf_client_id": "'"$PF_CLIENT_ID"'",
        "pf_user_id": '"$PF_USER_ID"'
      }')

    echo "$response" | jq '.' 2>/dev/null || echo "$response"
    echo "---"
    echo ""

    # Log to results file
    echo "{\"test\":\"8.${test_num}\",\"name\":\"${test_name}\",\"message\":\"${message}\",\"expected\":\"${expected_behavior}\",\"response\":$response}" >> "$RESULTS_FILE"

    sleep 3
}

# Initialize results file
echo "[" > "$RESULTS_FILE"

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  CATEGORY 1: QUERY + ACTION HYBRID     │"
echo "└─────────────────────────────────────────┘"
echo ""

test_call "1.1" \
    "Query + Action in single message" \
    "show my projects and schedule the first one" \
    "Should either: (A) List projects then prompt for scheduling, OR (B) Ask for clarification about which to do first, OR (C) Fail with clear error"

test_call "1.2" \
    "Query then immediate action reference" \
    "list all my projects and book the second one for tomorrow" \
    "Should list projects, then either prompt for confirmation or ask user to explicitly request scheduling after seeing list"

test_call "1.3" \
    "Multiple queries in one message" \
    "show my projects and also show me project details for 7751742" \
    "Should either handle both queries (multi-agent parallel) OR prioritize the first query OR ask for clarification"

test_call "1.4" \
    "Action verb at end of query" \
    "what projects do I have that I can schedule today" \
    "Should be treated as QUERY (asking what's available) not ACTION (booking)"

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  CATEGORY 2: CONDITIONAL MULTI-INTENT  │"
echo "└─────────────────────────────────────────┘"
echo ""

test_call "2.1" \
    "Weather conditional scheduling" \
    "what's the weather and book project 123 if it's good" \
    "Should either: (A) Use multi-agent orchestration (info+scheduling), OR (B) Ask user to check weather first then schedule separately, OR (C) Only answer weather query"

test_call "2.2" \
    "If-then logic in single message" \
    "if it's sunny tomorrow, schedule my outdoor project" \
    "Should either: (A) Route to information agent for weather conditional, OR (B) Ask for clarification about which project, OR (C) Explain can't handle conditional logic"

test_call "2.3" \
    "Conditional with project filter" \
    "show me new projects and if there are more than 3, schedule the first one" \
    "Should either: (A) List new projects, OR (B) Ask user to schedule after reviewing list, OR (C) Explain can't execute conditional count logic"

test_call "2.4" \
    "Conditional based on availability" \
    "check available dates for project 7751742 and if Nov 25th is free, book it" \
    "Should either: (A) Show available dates then prompt for booking, OR (B) Execute as sequential multi-agent, OR (C) Only show dates"

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  CATEGORY 3: SEQUENTIAL MULTI-STEP     │"
echo "└─────────────────────────────────────────┘"
echo ""

test_call "3.1" \
    "Explicit 3-step sequence" \
    "list my projects, then show weather, then schedule one" \
    "Should either: (A) Use sequential multi-agent orchestration, OR (B) Execute only first step and ask user to proceed, OR (C) Ask user to issue commands one at a time"

test_call "3.2" \
    "Sequential with dependencies" \
    "show me project 7751742 details, then check available dates for it, then show time slots for the first available date" \
    "Should either: (A) Execute as multi-step orchestration, OR (B) Handle first step and prompt for next, OR (C) Only execute first query"

test_call "3.3" \
    "Sequential cross-domain" \
    "first tell me the weather, then based on that show my outdoor projects, then schedule the first one" \
    "Should either: (A) Use information + scheduling agents sequentially, OR (B) Execute only weather query, OR (C) Ask for step-by-step commands"

test_call "3.4" \
    "Numbered step sequence" \
    "I want to: 1) see my new projects, 2) get details on project 7751742, 3) schedule it for next week" \
    "Should either: (A) Recognize as multi-step plan and execute sequentially, OR (B) Execute first step only, OR (C) Ask user to break down into separate messages"

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  CATEGORY 4: MULTIPLE ENTITY QUERIES   │"
echo "└─────────────────────────────────────────┘"
echo ""

# First, let's get some project IDs
echo "📝 Test 8.4.0: Setup - Getting project list for multiple entity tests"
setup_response=$(curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me all my projects",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }')

echo "$setup_response" | jq -r '.response' | jq -r '.projects[0:3] | .[] | .id' 2>/dev/null | head -3 > /tmp/project_ids.txt
PROJECT_ID_1=$(sed -n '1p' /tmp/project_ids.txt)
PROJECT_ID_2=$(sed -n '2p' /tmp/project_ids.txt)
PROJECT_ID_3=$(sed -n '3p' /tmp/project_ids.txt)

echo "Extracted Project IDs: $PROJECT_ID_1, $PROJECT_ID_2, $PROJECT_ID_3"
echo ""
sleep 2

test_call "4.1" \
    "Multiple project IDs - explicit listing" \
    "show me details for project $PROJECT_ID_1, project $PROJECT_ID_2, and project $PROJECT_ID_3" \
    "Should either: (A) Use multi-agent parallel to fetch all 3, OR (B) Fetch only first project, OR (C) Ask user to query one at a time"

test_call "4.2" \
    "Multiple project IDs - comma separated" \
    "give me details for $PROJECT_ID_1, $PROJECT_ID_2, $PROJECT_ID_3" \
    "Should extract all project IDs and either handle sequentially or ask for clarification"

test_call "4.3" \
    "Multiple projects with action verb" \
    "schedule projects $PROJECT_ID_1 and $PROJECT_ID_2 for next week" \
    "Should either: (A) Route to agent for multi-project scheduling, OR (B) Ask user to schedule one at a time, OR (C) Attempt scheduling first project only"

test_call "4.4" \
    "Range reference after list" \
    "show me details for the first three projects from my list" \
    "Should either: (A) Reference previous project list and fetch first 3, OR (B) Ask for clarification on which list, OR (C) Fetch first project only"

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  CATEGORY 5: AMBIGUOUS INTENT          │"
echo "└─────────────────────────────────────────┘"
echo ""

test_call "5.1" \
    "Ambiguous 'schedule' usage" \
    "schedule" \
    "Should ask for clarification: 'schedule what?' or 'do you want to see your schedule or create an appointment?'"

test_call "5.2" \
    "Ambiguous project reference" \
    "I need project 123" \
    "Should ask: 'Do you want to see details for project 123 or schedule it?'"

test_call "5.3" \
    "Ambiguous filtering" \
    "weather scheduled project" \
    "Should either: (A) Classify as information intent (weather query), OR (B) Classify as scheduling intent (scheduled projects), OR (C) Ask for clarification"

test_call "5.4" \
    "Mixed tense and intent" \
    "projects for tomorrow" \
    "Should either: (A) List projects scheduled for tomorrow (QUERY), OR (B) Ask which project to schedule for tomorrow (ACTION prep)"

test_call "5.5" \
    "Implicit multi-action" \
    "cancel my appointment and schedule a new one" \
    "Should either: (A) Route to agent for cancellation first, OR (B) Ask user to cancel first then schedule, OR (C) Explain it needs separate commands"

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  CATEGORY 6: MALFORMED / EDGE INPUTS   │"
echo "└─────────────────────────────────────────┘"
echo ""

test_call "6.1" \
    "Self-correction mid-sentence" \
    "schedule... actually, show me my projects first" \
    "Should recognize correction and execute 'show my projects' (QUERY)"

test_call "6.2" \
    "Multiple conflicting filters" \
    "show me new and scheduled and completed projects" \
    "Should either: (A) Apply all status filters (OR logic), OR (B) Use only first filter, OR (C) Ask for clarification"

test_call "6.3" \
    "Negation filter (unsupported)" \
    "show projects that are NOT scheduled" \
    "Should either: (A) Ignore negation and show all, OR (B) Ask for clarification, OR (C) Explain negation not supported"

test_call "6.4" \
    "Question within question" \
    "can you show me - wait do I have any new projects?" \
    "Should recognize final question as 'list new projects'"

test_call "6.5" \
    "Incomplete action sequence" \
    "book project 7751742 for" \
    "Should ask for clarification: 'When would you like to schedule this project?'"

test_call "6.6" \
    "Multiple project references with different types" \
    "show me the 2nd project and also project 7751742" \
    "Should either: (A) Resolve both references and fetch both, OR (B) Fetch only first reference, OR (C) Ask for clarification"

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  CATEGORY 7: CONTEXT STRESS TESTS      │"
echo "└─────────────────────────────────────────┘"
echo ""

test_call "7.1" \
    "Reference without prior context" \
    "schedule the first one for tomorrow" \
    "Should either: (A) Ask 'the first one of what?', OR (B) Explain no project list in history, OR (C) Fail gracefully"

test_call "7.2" \
    "Ambiguous pronoun with multiple contexts" \
    "tell me about it" \
    "Should either: (A) Ask for clarification about what 'it' refers to, OR (B) Use last mentioned entity from history, OR (C) Explain ambiguous reference"

test_call "7.3" \
    "Deep reference chain" \
    "show me my projects" \
    "First setup call for reference chain"
sleep 2

test_call "7.4" \
    "Reference to 2nd level history" \
    "the second one" \
    "Should resolve to 2nd project from previous list"
sleep 2

test_call "7.5" \
    "Nested reference after action" \
    "schedule that for the first available date" \
    "Should either: (A) Use context to determine project + fetch dates, OR (B) Ask which project, OR (C) Explain needs explicit project"

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  CATEGORY 8: PERFORMANCE EDGE CASES    │"
echo "└─────────────────────────────────────────┘"
echo ""

test_call "8.1" \
    "Extremely long message" \
    "I would like to see all of my projects that are currently in the system and I'm particularly interested in the ones that are marked as new because those are the ones I haven't reviewed yet and I want to make sure I don't miss any important opportunities and also could you tell me if any of them are related to flooring or decking work because those are my specialties" \
    "Should extract intent (list new projects, filter by flooring/decking) despite verbosity"

test_call "8.2" \
    "Rapid-fire multi-query" \
    "projects weather dates slots schedule" \
    "Should either: (A) Attempt to parse keywords, OR (B) Ask for complete sentence, OR (C) Route to chitchat as unclear"

test_call "8.3" \
    "Message with special characters" \
    "show me project #7751742 & details (if available)" \
    "Should handle special chars and extract project ID 7751742"

test_call "8.4" \
    "Empty context reference" \
    "what about that?" \
    "Should ask for clarification about what 'that' refers to when context is unclear"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Suite 8 Completed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Results saved to: $RESULTS_FILE"
echo ""

# Close JSON array
echo "]" >> "$RESULTS_FILE"

echo "To analyze results, run:"
echo "  cat $RESULTS_FILE | jq '.[] | {test, name, expected, agent_name: .response.agent_name, intent: .response.intent, action: .response.action, direct_call: .response.direct_call}'"
echo ""
echo "Or use the Python formatter:"
echo "  python3 format_results.py $RESULTS_FILE"
echo ""
