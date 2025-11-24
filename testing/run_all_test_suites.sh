#!/bin/bash
# Master Test Runner - Runs all test suites
# Usage: ./run_all_test_suites.sh

cd "$(dirname "$0")"

echo ""
echo "=========================================="
echo "ProjectForce Bedrock - Test Suite Runner"
echo "=========================================="
echo ""
echo "Running all test suites..."
echo ""

# Make all test suites executable
chmod +x test_suite_*.sh run_quick_tests.sh

# Track results
TOTAL_SUITES=7
PASSED=0
FAILED=0

# Run original quick tests
echo ""
echo "▶️  Running: Quick Tests (Sanity Check)"
if ./run_quick_tests.sh > /tmp/test_quick.log 2>&1; then
    echo "✅ Quick Tests: PASSED"
    ((PASSED++))
else
    echo "❌ Quick Tests: FAILED"
    ((FAILED++))
fi

# Run Test Suite 1
echo ""
echo "▶️  Running: Test Suite 1 - Basic Workflow"
if ./test_suite_1_basic_workflow.sh > /tmp/test_suite_1.log 2>&1; then
    echo "✅ Test Suite 1: PASSED"
    ((PASSED++))
else
    echo "❌ Test Suite 1: FAILED"
    ((FAILED++))
fi

# Run Test Suite 2
echo ""
echo "▶️  Running: Test Suite 2 - Context Resolution"
if ./test_suite_2_context_resolution.sh > /tmp/test_suite_2.log 2>&1; then
    echo "✅ Test Suite 2: PASSED"
    ((PASSED++))
else
    echo "❌ Test Suite 2: FAILED"
    ((FAILED++))
fi

# Run Test Suite 3
echo ""
echo "▶️  Running: Test Suite 3 - Advanced Filtering"
if ./test_suite_3_filtering.sh > /tmp/test_suite_3.log 2>&1; then
    echo "✅ Test Suite 3: PASSED"
    ((PASSED++))
else
    echo "❌ Test Suite 3: FAILED"
    ((FAILED++))
fi

# Run Test Suite 4
echo ""
echo "▶️  Running: Test Suite 4 - Mixed Chitchat & Business"
if ./test_suite_4_chitchat_mixed.sh > /tmp/test_suite_4.log 2>&1; then
    echo "✅ Test Suite 4: PASSED"
    ((PASSED++))
else
    echo "❌ Test Suite 4: FAILED"
    ((FAILED++))
fi

# Run Test Suite 5
echo ""
echo "▶️  Running: Test Suite 5 - Scheduling Operations"
if ./test_suite_5_scheduling.sh > /tmp/test_suite_5.log 2>&1; then
    echo "✅ Test Suite 5: PASSED"
    ((PASSED++))
else
    echo "❌ Test Suite 5: FAILED"
    ((FAILED++))
fi

# Run Test Suite 6
echo ""
echo "▶️  Running: Test Suite 6 - Notes Functionality"
if ./test_suite_6_notes.sh > /tmp/test_suite_6.log 2>&1; then
    echo "✅ Test Suite 6: PASSED"
    ((PASSED++))
else
    echo "❌ Test Suite 6: FAILED"
    ((FAILED++))
fi

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Total Suites: $TOTAL_SUITES"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 All test suites passed!"
    echo ""
    echo "Logs saved to /tmp/test_*.log"
    exit 0
else
    echo "⚠️  Some test suites failed"
    echo ""
    echo "Check logs in /tmp/test_*.log for details"
    exit 1
fi
