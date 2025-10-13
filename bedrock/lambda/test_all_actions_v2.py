#!/usr/bin/env python3
"""
Comprehensive Test Suite for All Lambda Actions
Tests all 12 actions across 3 Lambda functions in mock mode
"""

import json
import os
import sys
import importlib.util
from datetime import datetime

# Set mock mode
os.environ['USE_MOCK_API'] = 'true'

# Test results storage
test_results = []

def load_lambda_handler(lambda_dir):
    """Dynamically load handler module from specific directory"""
    handler_path = os.path.join(lambda_dir, 'handler.py')
    spec = importlib.util.spec_from_file_location(f"handler_{lambda_dir.replace('-', '_')}", handler_path)
    module = importlib.util.module_from_spec(spec)

    # Add the lambda directory to sys.path temporarily
    sys.path.insert(0, lambda_dir)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)

    return module.lambda_handler

def run_test(test_name, lambda_dir, event):
    """Run a single test and capture results"""
    print(f"\n{'='*80}")
    print(f"🧪 Testing: {test_name}")
    print('='*80)

    try:
        # Load the handler
        lambda_handler = load_lambda_handler(lambda_dir)

        start_time = datetime.now()
        result = lambda_handler(event, None)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() * 1000

        # Check if response is successful
        status_code = result.get('response', {}).get('httpStatusCode', 500)
        success = status_code == 200

        # Extract body
        body_str = result.get('response', {}).get('responseBody', {}).get('application/json', {}).get('body', '{}')
        body = json.loads(body_str)

        test_results.append({
            'test_name': test_name,
            'success': success,
            'status_code': status_code,
            'duration_ms': duration,
            'mock_mode': body.get('mock_mode', False),
            'action': body.get('action', 'unknown'),
            'lambda_dir': lambda_dir
        })

        if success:
            print(f"✅ PASSED ({duration:.2f}ms)")
            print(f"Mock Mode: {body.get('mock_mode')}")
            print(f"Action: {body.get('action')}")
            # Show condensed response
            body_copy = body.copy()
            for key in body_copy:
                if isinstance(body_copy[key], (list, dict)) and len(str(body_copy[key])) > 100:
                    body_copy[key] = f"<{type(body_copy[key]).__name__} with {len(body_copy[key])} items>"
            print(f"Response: {json.dumps(body_copy, indent=2)}")
        else:
            print(f"❌ FAILED (Status: {status_code})")
            print(f"Error: {body.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        test_results.append({
            'test_name': test_name,
            'success': False,
            'status_code': 500,
            'duration_ms': 0,
            'error': str(e),
            'lambda_dir': lambda_dir
        })
        return None

# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                 Lambda Functions Comprehensive Test Suite                  ║
║                       Testing All 12 Actions in Mock Mode                  ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    # Scheduling Actions (6 tests)
    print("\n" + "="*80)
    print("📅 SCHEDULING ACTIONS (6 actions)")
    print("="*80)

    run_test("1. List Projects", "scheduling-actions", {
        "apiPath": "/list-projects",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    run_test("2. Get Available Dates", "scheduling-actions", {
        "apiPath": "/get-available-dates",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    run_test("3. Get Time Slots", "scheduling-actions", {
        "apiPath": "/get-time-slots",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "date", "value": "2025-10-15"},
            {"name": "request_id", "value": "REQ-123"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    run_test("4. Confirm Appointment", "scheduling-actions", {
        "apiPath": "/confirm-appointment",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "date", "value": "2025-10-15"},
            {"name": "time", "value": "10:00 AM"},
            {"name": "request_id", "value": "REQ-123"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    run_test("5. Reschedule Appointment", "scheduling-actions", {
        "apiPath": "/reschedule-appointment",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "new_date", "value": "2025-10-20"},
            {"name": "new_time", "value": "02:00 PM"},
            {"name": "request_id", "value": "REQ-123"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    run_test("6. Cancel Appointment", "scheduling-actions", {
        "apiPath": "/cancel-appointment",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    # Information Actions (4 tests)
    print("\n" + "="*80)
    print("ℹ️  INFORMATION ACTIONS (4 actions)")
    print("="*80)

    run_test("7. Get Project Details", "information-actions", {
        "apiPath": "/get-project-details",
        "httpMethod": "POST",
        "actionGroup": "information",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    run_test("8. Get Appointment Status", "information-actions", {
        "apiPath": "/get-appointment-status",
        "httpMethod": "POST",
        "actionGroup": "information",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    run_test("9. Get Working Hours", "information-actions", {
        "apiPath": "/get-working-hours",
        "httpMethod": "POST",
        "actionGroup": "information",
        "parameters": [
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    run_test("10. Get Weather", "information-actions", {
        "apiPath": "/get-weather",
        "httpMethod": "POST",
        "actionGroup": "information",
        "parameters": [
            {"name": "location", "value": "Tampa, FL"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    # Notes Actions (2 tests)
    print("\n" + "="*80)
    print("📝 NOTES ACTIONS (2 actions)")
    print("="*80)

    run_test("11. Add Note", "notes-actions", {
        "apiPath": "/add-note",
        "httpMethod": "POST",
        "actionGroup": "notes",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "note_text", "value": "Customer confirmed appointment for next week"},
            {"name": "author", "value": "Test Agent"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    run_test("12. List Notes", "notes-actions", {
        "apiPath": "/list-notes",
        "httpMethod": "POST",
        "actionGroup": "notes",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    })

    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)

    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r['success'])
    failed_tests = total_tests - passed_tests
    avg_duration = sum(r.get('duration_ms', 0) for r in test_results) / total_tests if total_tests > 0 else 0

    print(f"\nTotal Tests:    {total_tests}")
    print(f"✅ Passed:       {passed_tests}")
    print(f"❌ Failed:       {failed_tests}")
    print(f"⚡ Avg Duration: {avg_duration:.2f}ms")
    print(f"📈 Pass Rate:    {(passed_tests/total_tests*100):.1f}%")

    # Break down by Lambda
    print("\n📦 By Lambda Function:")
    for lambda_name in ["scheduling-actions", "information-actions", "notes-actions"]:
        lambda_results = [r for r in test_results if r.get('lambda_dir') == lambda_name]
        if lambda_results:
            passed = sum(1 for r in lambda_results if r['success'])
            total = len(lambda_results)
            print(f"   {lambda_name:25s}: {passed}/{total} passed")

    # List failed tests
    if failed_tests > 0:
        print("\n❌ Failed Tests:")
        for r in test_results:
            if not r['success']:
                print(f"   - {r['test_name']}: {r.get('error', 'Status ' + str(r['status_code']))}")

    # Success message
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Lambda functions are ready for deployment.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the output above.")

    return passed_tests == total_tests

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    success = main()
    sys.exit(0 if success else 1)
