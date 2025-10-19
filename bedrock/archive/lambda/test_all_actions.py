#!/usr/bin/env python3
"""
Comprehensive Test Suite for All Lambda Actions
Tests all 12 actions across 3 Lambda functions in mock mode
"""

import json
import os
import sys
from datetime import datetime

# Set mock mode
os.environ['USE_MOCK_API'] = 'true'

# Test results storage
test_results = []

def run_test(test_name, test_func):
    """Run a single test and capture results"""
    print(f"\n{'='*80}")
    print(f"🧪 Testing: {test_name}")
    print('='*80)

    try:
        start_time = datetime.now()
        result = test_func()
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
            'action': body.get('action', 'unknown')
        })

        if success:
            print(f"✅ PASSED ({duration:.2f}ms)")
            print(f"Mock Mode: {body.get('mock_mode')}")
            print(f"Response Preview: {json.dumps(body, indent=2)[:500]}...")
        else:
            print(f"❌ FAILED (Status: {status_code})")
            print(f"Error: {body.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        test_results.append({
            'test_name': test_name,
            'success': False,
            'status_code': 500,
            'duration_ms': 0,
            'error': str(e)
        })
        return None

# ============================================================================
# Scheduling Actions Tests (6 actions)
# ============================================================================

def test_list_projects():
    """Test list_projects action"""
    sys.path.insert(0, 'scheduling-actions')
    from handler import lambda_handler

    event = {
        "apiPath": "/list-projects",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }
    return lambda_handler(event, None)

def test_get_available_dates():
    """Test get_available_dates action"""
    sys.path.insert(0, 'scheduling-actions')
    from handler import lambda_handler

    event = {
        "apiPath": "/get-available-dates",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }
    return lambda_handler(event, None)

def test_get_time_slots():
    """Test get_time_slots action"""
    sys.path.insert(0, 'scheduling-actions')
    from handler import lambda_handler

    event = {
        "apiPath": "/get-time-slots",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "date", "value": "2025-10-15"},
            {"name": "request_id", "value": "REQ-123"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }
    return lambda_handler(event, None)

def test_confirm_appointment():
    """Test confirm_appointment action"""
    sys.path.insert(0, 'scheduling-actions')
    from handler import lambda_handler

    event = {
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
    }
    return lambda_handler(event, None)

def test_reschedule_appointment():
    """Test reschedule_appointment action"""
    sys.path.insert(0, 'scheduling-actions')
    from handler import lambda_handler

    event = {
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
    }
    return lambda_handler(event, None)

def test_cancel_appointment():
    """Test cancel_appointment action"""
    sys.path.insert(0, 'scheduling-actions')
    from handler import lambda_handler

    event = {
        "apiPath": "/cancel-appointment",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }
    return lambda_handler(event, None)

# ============================================================================
# Information Actions Tests (4 actions)
# ============================================================================

def test_get_project_details():
    """Test get_project_details action"""
    sys.path.insert(0, 'information-actions')
    from handler import lambda_handler

    event = {
        "apiPath": "/get-project-details",
        "httpMethod": "POST",
        "actionGroup": "information",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }
    return lambda_handler(event, None)

def test_get_appointment_status():
    """Test get_appointment_status action"""
    sys.path.insert(0, 'information-actions')
    from handler import lambda_handler

    event = {
        "apiPath": "/get-appointment-status",
        "httpMethod": "POST",
        "actionGroup": "information",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }
    return lambda_handler(event, None)

def test_get_working_hours():
    """Test get_working_hours action"""
    sys.path.insert(0, 'information-actions')
    from handler import lambda_handler

    event = {
        "apiPath": "/get-working-hours",
        "httpMethod": "POST",
        "actionGroup": "information",
        "parameters": [
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }
    return lambda_handler(event, None)

def test_get_weather():
    """Test get_weather action"""
    sys.path.insert(0, 'information-actions')
    from handler import lambda_handler

    event = {
        "apiPath": "/get-weather",
        "httpMethod": "POST",
        "actionGroup": "information",
        "parameters": [
            {"name": "location", "value": "Tampa, FL"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }
    return lambda_handler(event, None)

# ============================================================================
# Notes Actions Tests (2 actions)
# ============================================================================

def test_add_note():
    """Test add_note action"""
    sys.path.insert(0, 'notes-actions')
    from handler import lambda_handler

    event = {
        "apiPath": "/add-note",
        "httpMethod": "POST",
        "actionGroup": "notes",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "note_text", "value": "Customer confirmed appointment for next week"},
            {"name": "author", "value": "Test Agent"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }
    return lambda_handler(event, None)

def test_list_notes():
    """Test list_notes action"""
    sys.path.insert(0, 'notes-actions')
    from handler import lambda_handler

    event = {
        "apiPath": "/list-notes",
        "httpMethod": "POST",
        "actionGroup": "notes",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }
    return lambda_handler(event, None)

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
    run_test("1. List Projects", test_list_projects)
    run_test("2. Get Available Dates", test_get_available_dates)
    run_test("3. Get Time Slots", test_get_time_slots)
    run_test("4. Confirm Appointment", test_confirm_appointment)
    run_test("5. Reschedule Appointment", test_reschedule_appointment)
    run_test("6. Cancel Appointment", test_cancel_appointment)

    # Information Actions (4 tests)
    print("\n" + "="*80)
    print("ℹ️  INFORMATION ACTIONS (4 actions)")
    print("="*80)
    run_test("7. Get Project Details", test_get_project_details)
    run_test("8. Get Appointment Status", test_get_appointment_status)
    run_test("9. Get Working Hours", test_get_working_hours)
    run_test("10. Get Weather", test_get_weather)

    # Notes Actions (2 tests)
    print("\n" + "="*80)
    print("📝 NOTES ACTIONS (2 actions)")
    print("="*80)
    run_test("11. Add Note", test_add_note)
    run_test("12. List Notes", test_list_notes)

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
    success = main()
    sys.exit(0 if success else 1)
