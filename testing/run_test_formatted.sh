#!/bin/bash
# Run any test suite with formatted output
# Usage: ./run_test_formatted.sh test_suite_1_basic_workflow.sh

cd "$(dirname "$0")"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <test_suite_script>"
    echo ""
    echo "Available test suites:"
    echo "  • test_suite_1_basic_workflow.sh"
    echo "  • test_suite_2_context_resolution.sh"
    echo "  • test_suite_3_filtering.sh"
    echo "  • test_suite_4_chitchat_mixed.sh"
    echo "  • test_suite_5_scheduling.sh"
    echo "  • run_quick_tests.sh"
    echo ""
    echo "Example: $0 test_suite_1_basic_workflow.sh"
    exit 1
fi

TEST_SCRIPT="$1"

if [ ! -f "$TEST_SCRIPT" ]; then
    echo "Error: Test script not found: $TEST_SCRIPT"
    exit 1
fi

echo "Running $TEST_SCRIPT with formatted output..."
echo ""

# Run test and pipe through formatter
./"$TEST_SCRIPT" 2>&1 | python3 format_results.py
