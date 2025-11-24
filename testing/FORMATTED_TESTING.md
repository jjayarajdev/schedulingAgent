# Formatted Test Results - User Guide

## Overview

Test results can now be displayed in a **clean, readable table format** instead of raw JSON output. The formatter automatically:
- ✅ Strips null/empty values
- ✅ Formats data in aligned tables
- ✅ Color-codes results (errors in red, direct calls in green, agent calls in yellow)
- ✅ Shows performance metrics (total time, classification time, etc.)
- ✅ Provides summaries (avg/min/max times, error count)
- ✅ Truncates long responses for readability

## Quick Start

### Method 1: Run with Formatter (Recommended)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/bedrock/testing

# Run any test suite with formatted output
./run_test_formatted.sh test_suite_1_basic_workflow.sh
./run_test_formatted.sh test_suite_2_context_resolution.sh
./run_test_formatted.sh run_quick_tests.sh
```

### Method 2: Pipe Existing Test to Formatter

```bash
# Run test and pipe through formatter
./test_suite_1_basic_workflow.sh | python3 format_results.py

# Or save raw output first, then format
./test_suite_1_basic_workflow.sh > /tmp/test_output.txt
cat /tmp/test_output.txt | python3 format_results.py
```

### Method 3: Format Saved Log Files

```bash
# Format previously saved test logs
cat /tmp/test_suite_1.log | python3 format_results.py
```

## Example Output

### Table Format
```
╔════════════════════════════════════════════════════════════════════════════════╗
║ Test Suite 1: Basic Project Workflow                                          ║
╚════════════════════════════════════════════════════════════════════════════════╝
Session: test-suite-1-1763143877

══════════════════════════════════════════════════════════════════════════════════
Test     Agent              Type       Time         Response
══════════════════════════════════════════════════════════════════════════════════
1.1      Chitchat Agent     Agent      5.63s        Hello! I'm here to help you schedule appointments...
         └─ User greets the system

1.2      Direct Lambda      Direct     1.98s        You have 8 Decking Call Back projects at 401 Chicago...
         └─ User asks for all projects

1.3      Direct Lambda      Direct     2.02s        You have 4 Decking Call Back projects at 401 Chicago...
         └─ User filters for new projects

1.4      Direct Lambda      Direct     3.19s        ❌ ERROR: Failed to fetch project details: 500
         └─ User asks for details of 2nd project

1.5      Scheduling Agent   Agent      7.60s        Which project would you like to schedule?
         └─ User schedules the project
══════════════════════════════════════════════════════════════════════════════════

══════════════════════════════════════════════════════════════════════════════════
Performance Summary
══════════════════════════════════════════════════════════════════════════════════

Call Distribution:
  • Direct Lambda Calls: 3
  • Bedrock Agent Calls: 2

Direct Lambda Performance:
  • Average: 2.40s
  • Min: 1.98s
  • Max: 3.19s

Bedrock Agent Performance:
  • Average: 6.61s
  • Min: 5.63s
  • Max: 7.60s

══════════════════════════════════════════════════════════════════════════════════
Errors Found: 1
══════════════════════════════════════════════════════════════════════════════════
Test 4: ❌ ERROR: Failed to fetch project details: 500

✓ Test suite completed
```

## Features Explained

### 1. **Color Coding**
- 🟢 **Green** - Direct Lambda calls (fast, efficient)
- 🟡 **Yellow** - Bedrock Agent calls (slower but more intelligent)
- 🔴 **Red** - Errors or failures
- 🔵 **Blue** - Test descriptions and headers

### 2. **Performance Metrics**
Shows timing breakdown for each test:
- **Total**: Complete request time
- **Classify**: Intent classification time
- **Lambda**: Direct Lambda execution time
- **Bedrock**: Bedrock agent invocation time
- **Stream**: Response streaming time

### 3. **Response Truncation**
Long responses are automatically truncated to 80 characters with "..." to keep the table readable.

### 4. **Error Highlighting**
Errors are extracted and summarized at the bottom for quick identification.

### 5. **Performance Summary**
Automatically calculates:
- Call distribution (direct vs agent)
- Average/min/max times for each type
- Total errors found

## Customization

### Adjust Truncation Length

Edit `format_results.py` line with `truncate_string()`:

```python
# Current: 80 characters
response_short = truncate_string(response_text, 80)

# Change to 120 characters
response_short = truncate_string(response_text, 120)
```

### Adjust Context Messages Shown

Edit `router.py` line 116:

```python
# Current: Last 4 messages
def build_conversation_context(conversation_history, max_messages=4):

# Change to last 6 messages
def build_conversation_context(conversation_history, max_messages=6):
```

### Disable Colors

If your terminal doesn't support ANSI colors, disable them in `format_results.py`:

```python
class Colors:
    HEADER = ''
    BLUE = ''
    CYAN = ''
    GREEN = ''
    YELLOW = ''
    RED = ''
    BOLD = ''
    UNDERLINE = ''
    END = ''
```

## Available Test Suites

| Test Suite | Description | Focus Area |
|------------|-------------|------------|
| `run_quick_tests.sh` | Quick sanity check | Basic functionality |
| `test_suite_1_basic_workflow.sh` | Basic project workflow | List, filter, details, schedule |
| `test_suite_2_context_resolution.sh` | Context tracking | Ordinal refs, pronouns, implicit context |
| `test_suite_3_filtering.sh` | Advanced filtering | Status, category, type filters |
| `test_suite_4_chitchat_mixed.sh` | Agent routing | Mixed chitchat and business |
| `test_suite_5_scheduling.sh` | Scheduling workflows | Schedule, reschedule operations |

## Comparison: Before vs After

### Before (Raw JSON)
```json
{"response": "You have 8 Decking Call Back projects at 401 Chicago Avenue, Minneapolis:","projects":[{"id":"7751741","projectNumber":"21083_09PF05VD_1762166550719","status":"Scheduled","category":"Decking","projectType":"Call Back","scheduledDate":"11-11-2025 01:00 PM","scheduledEndDate":"11-11-2025 01:10 PM",...}],"agent_name":"Direct Lambda","intent":"scheduling","action":"list_projects","session_id":"test-suite-1-1763143877","direct_call":true,"performance":{"classification":1.740790843963623,"lambda_direct":0.24142789840698242,"total":1.9823861122131348}}
```

### After (Formatted Table)
```
1.2      Direct Lambda      Direct     1.98s        You have 8 Decking Call Back projects at 401 Chicago...
         └─ User asks for all projects
```

## Tips

1. **Save Formatted Output**
   ```bash
   ./run_test_formatted.sh test_suite_1.sh > formatted_results.txt
   ```

2. **Compare Test Runs**
   ```bash
   # Before changes
   ./test_suite_1.sh | python3 format_results.py > before.txt

   # After changes
   ./test_suite_1.sh | python3 format_results.py > after.txt

   # Compare
   diff before.txt after.txt
   ```

3. **Watch Tests in Real-time**
   ```bash
   # The formatter processes output as it arrives
   ./run_test_formatted.sh test_suite_1.sh
   ```

4. **Filter Specific Errors**
   ```bash
   ./test_suite_1.sh 2>&1 | python3 format_results.py | grep "ERROR"
   ```

## Troubleshooting

### Issue: "No JSON responses found"
**Cause**: Test didn't return any JSON
**Fix**: Run test without formatter to see raw output:
```bash
./test_suite_1.sh
```

### Issue: Colors not displaying
**Cause**: Terminal doesn't support ANSI colors
**Fix**: Disable colors (see Customization section) or use:
```bash
./test_suite_1.sh | python3 format_results.py | cat
```

### Issue: Table alignment off
**Cause**: Response text too long
**Fix**: Reduce truncation length or use wider terminal:
```bash
# Make terminal wider (at least 150 characters)
```

## Files

| File | Purpose |
|------|---------|
| `format_results.py` | Main formatter script |
| `run_test_formatted.sh` | Wrapper to run tests with formatting |
| `FORMATTED_TESTING.md` | This documentation |

## Integration with CI/CD

The formatter can be used in automated testing:

```bash
#!/bin/bash
# ci-test.sh

cd testing

# Run all tests with formatted output
for suite in test_suite_*.sh; do
    echo "Running $suite..."
    ./run_test_formatted.sh "$suite"

    # Check exit code
    if [ $? -ne 0 ]; then
        echo "FAILED: $suite"
        exit 1
    fi
done

echo "All tests passed!"
```

---

**Last Updated**: 2025-11-14
**Version**: 1.0
**Author**: Claude Code
