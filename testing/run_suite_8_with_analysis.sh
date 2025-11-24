#!/bin/bash
# Quick runner for Test Suite 8 with automatic analysis
# Usage: ./run_suite_8_with_analysis.sh

set -e  # Exit on error

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  TEST SUITE 8: Multi-Intent & Complex Query Edge Cases            ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if test_config.sh exists
if [ ! -f "test_config.sh" ]; then
    echo "❌ Error: test_config.sh not found!"
    echo "   Please create test_config.sh with your API credentials."
    echo ""
    echo "   Example:"
    echo "   export API_ENDPOINT=\"https://your-api.execute-api.us-east-1.amazonaws.com/dev/invoke-agent\""
    echo "   export PF_TOKEN=\"your-token\""
    echo "   export PF_CLIENT_ID=\"your-client-id\""
    echo "   export PF_USER_ID=your-user-id"
    exit 1
fi

# Source configuration
source test_config.sh

echo "✅ Configuration loaded"
echo "   API Endpoint: $API_ENDPOINT"
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "⚠️  Warning: jq is not installed. Results will not be formatted."
    echo "   Install with: brew install jq (macOS) or apt-get install jq (Linux)"
    echo ""
fi

# Prompt user
echo "This test suite will run 40+ edge case tests."
echo "Estimated time: 10-15 minutes"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Test cancelled."
    exit 0
fi

echo ""
echo "🚀 Starting Test Suite 8..."
echo ""

# Run test suite
./test_suite_8_multi_intent_edge_cases.sh

# Find the most recent results file
RESULTS_FILE=$(ls -t test_suite_8_results_*.json 2>/dev/null | head -1)

if [ -z "$RESULTS_FILE" ]; then
    echo "❌ Error: No results file found!"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                         ANALYZING RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    echo "📊 Running Python analyzer..."
    echo ""
    python3 analyze_suite_8_results.py "$RESULTS_FILE"

    # Ask if user wants CSV export
    echo ""
    read -p "Export results to CSV? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        CSV_FILE="${RESULTS_FILE%.json}.csv"
        python3 analyze_suite_8_results.py "$RESULTS_FILE" --csv "$CSV_FILE"
        echo "✅ CSV exported to: $CSV_FILE"
    fi
else
    echo "⚠️  Python 3 not found. Showing basic jq analysis..."
    echo ""

    if command -v jq &> /dev/null; then
        echo "Summary by Agent:"
        cat "$RESULTS_FILE" | jq -r '.[] | .response.agent_name' | sort | uniq -c | sort -rn
        echo ""

        echo "Summary by Intent:"
        cat "$RESULTS_FILE" | jq -r '.[] | .response.intent' | sort | uniq -c | sort -rn
        echo ""

        echo "Errors:"
        cat "$RESULTS_FILE" | jq '.[] | select(.response.error) | {test, name, error: .response.error}'
    else
        echo "Install jq or python3 for detailed analysis."
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                            COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Results saved to: $RESULTS_FILE"
echo ""
echo "Next steps:"
echo "  1. Review the analysis report above"
echo "  2. Check TEST_SUITE_8_README.md for interpretation guidance"
echo "  3. Share results with the team for discussion"
echo "  4. Prioritize improvements based on recommendations"
echo ""
