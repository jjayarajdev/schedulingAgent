#!/bin/bash

echo "================================================================================"
echo "AWS Lambda Functions Test Suite"
echo "================================================================================"
echo "Date: $(date)"
echo "Region: us-east-1"
echo "Mock Mode: true"
echo "================================================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to test Lambda
test_lambda() {
    local name=$1
    local function_name=$2
    local payload=$3

    echo "Testing: $name"

    aws lambda invoke \
      --function-name $function_name \
      --cli-binary-format raw-in-base64-out \
      --payload "$payload" \
      --region us-east-1 \
      response.json > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        status_code=$(cat response.json | jq -r '.response.httpStatusCode')
        if [ "$status_code" == "200" ]; then
            echo -e "${GREEN}✅ PASS${NC} - HTTP $status_code"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}❌ FAIL${NC} - HTTP $status_code"
            cat response.json | jq -r '.response.responseBody."application/json".body'
            ((TESTS_FAILED++))
        fi
    else
        echo -e "${RED}❌ FAIL${NC} - Lambda invocation failed"
        ((TESTS_FAILED++))
    fi
    echo ""
}

echo "================================================================================"
echo "Testing Scheduling Lambda (6 actions)"
echo "================================================================================"
echo ""

# Test 1: List Projects
test_lambda \
    "list_projects - Get all projects for customer" \
    "scheduling-agent-scheduling-actions" \
    '{"actionGroup":"scheduling_actions","apiPath":"/list-projects","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[{"name":"customer_id","type":"string","value":"CUST001"}]}}}}'

# Test 2: Get Available Dates
test_lambda \
    "get_available_dates - Get available dates for project 12347" \
    "scheduling-agent-scheduling-actions" \
    '{"actionGroup":"scheduling_actions","apiPath":"/get-available-dates","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[{"name":"project_id","type":"string","value":"12347"}]}}}}'

echo "================================================================================"
echo "Testing Information Lambda (4 actions)"
echo "================================================================================"
echo ""

# Test 3: Get Project Details
test_lambda \
    "get_project_details - Get details for project 12345" \
    "scheduling-agent-information-actions" \
    '{"actionGroup":"information_actions","apiPath":"/get-project-details","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[{"name":"project_id","type":"string","value":"12345"},{"name":"customer_id","type":"string","value":"CUST001"}]}}}}'

# Test 4: Get Appointment Status
test_lambda \
    "get_appointment_status - Get status for project 12345" \
    "scheduling-agent-information-actions" \
    '{"actionGroup":"information_actions","apiPath":"/get-appointment-status","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[{"name":"project_id","type":"string","value":"12345"}]}}}}'

# Test 5: Get Working Hours
test_lambda \
    "get_working_hours - Get business hours" \
    "scheduling-agent-information-actions" \
    '{"actionGroup":"information_actions","apiPath":"/get-working-hours","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[]}}}}'

# Test 6: Get Weather
test_lambda \
    "get_weather - Get weather for Tampa" \
    "scheduling-agent-information-actions" \
    '{"actionGroup":"information_actions","apiPath":"/get-weather","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[{"name":"location","type":"string","value":"Tampa, FL"}]}}}}'

echo "================================================================================"
echo "Testing Notes Lambda (2 actions)"
echo "================================================================================"
echo ""

# Test 7: Add Note
test_lambda \
    "add_note - Add note to project 12345" \
    "scheduling-agent-notes-actions" \
    '{"actionGroup":"notes_actions","apiPath":"/add-note","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[{"name":"project_id","type":"string","value":"12345"},{"name":"note_text","type":"string","value":"Test note - automated test"},{"name":"author","type":"string","value":"Test Script"}]}}}}'

# Test 8: List Notes
test_lambda \
    "list_notes - List notes for project 12345" \
    "scheduling-agent-notes-actions" \
    '{"actionGroup":"notes_actions","apiPath":"/list-notes","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[{"name":"project_id","type":"string","value":"12345"}]}}}}'

# Cleanup
rm -f response.json

echo "================================================================================"
echo "Test Summary"
echo "================================================================================"
echo ""
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Test agents in Bedrock Console"
    echo "2. Test multi-agent workflows"
    echo "3. Update agent instructions with B2B logic"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check the output above for details.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "- Check Lambda CloudWatch logs for errors"
    echo "- Verify USE_MOCK_API=true environment variable"
    echo "- Ensure Lambda functions were deployed successfully"
    exit 1
fi
