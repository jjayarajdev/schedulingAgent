#!/bin/bash

# ============================================================================
# Test Runner for API Migration Implementation
# Runs unit tests and integration tests
# ============================================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================================"
echo "Running API Migration Tests"
echo "============================================================================"

# Set environment variables for testing
export USE_MOCK_API="true"
export API_ENVIRONMENT="dev"
export PYTHONPATH="${SCRIPT_DIR}/../lambda/shared-layer/python/lib:${SCRIPT_DIR}/../lambda/scheduling-actions:${PYTHONPATH}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track test results
UNIT_TESTS_PASSED=0
INTEGRATION_TESTS_PASSED=0

echo ""
echo "============================================================================"
echo "Unit Tests"
echo "============================================================================"

# Run unit tests
echo ""
echo "${YELLOW}Running validator tests...${NC}"
if python3 unit/test_validators.py -v; then
    echo "${GREEN}✓ Validator tests passed${NC}"
    UNIT_TESTS_PASSED=$((UNIT_TESTS_PASSED + 1))
else
    echo "${RED}✗ Validator tests failed${NC}"
fi

echo ""
echo "${YELLOW}Running error handler tests...${NC}"
if python3 unit/test_error_handler.py -v; then
    echo "${GREEN}✓ Error handler tests passed${NC}"
    UNIT_TESTS_PASSED=$((UNIT_TESTS_PASSED + 1))
else
    echo "${RED}✗ Error handler tests failed${NC}"
fi

echo ""
echo "${YELLOW}Running API client tests...${NC}"
if python3 unit/test_api_client.py -v; then
    echo "${GREEN}✓ API client tests passed${NC}"
    UNIT_TESTS_PASSED=$((UNIT_TESTS_PASSED + 1))
else
    echo "${RED}✗ API client tests failed${NC}"
fi

echo ""
echo "============================================================================"
echo "Integration Tests"
echo "============================================================================"

echo ""
echo "${YELLOW}Running scheduling flow tests...${NC}"
if python3 integration/test_scheduling_flow.py -v; then
    echo "${GREEN}✓ Scheduling flow tests passed${NC}"
    INTEGRATION_TESTS_PASSED=$((INTEGRATION_TESTS_PASSED + 1))
else
    echo "${RED}✗ Scheduling flow tests failed${NC}"
fi

echo ""
echo "============================================================================"
echo "Test Summary"
echo "============================================================================"

echo ""
echo "Unit Tests: ${UNIT_TESTS_PASSED}/3 passed"
echo "Integration Tests: ${INTEGRATION_TESTS_PASSED}/1 passed"
echo ""

TOTAL_PASSED=$((UNIT_TESTS_PASSED + INTEGRATION_TESTS_PASSED))
TOTAL_TESTS=4

if [ $TOTAL_PASSED -eq $TOTAL_TESTS ]; then
    echo "${GREEN}✅ All tests passed! ($TOTAL_PASSED/$TOTAL_TESTS)${NC}"
    exit 0
else
    echo "${RED}❌ Some tests failed ($TOTAL_PASSED/$TOTAL_TESTS)${NC}"
    exit 1
fi
