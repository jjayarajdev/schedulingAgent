#!/usr/bin/env python3
"""
Test Real ProjectForce API Integration
Tests the Lambda handlers with real API calls
"""

import sys
import os
import json

# Add lambda directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scheduling-actions'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'information-actions'))

# Set environment variables for testing
os.environ['USE_MOCK_API'] = 'false'
os.environ['ENVIRONMENT'] = 'dev'
os.environ['BEARER_TOKEN'] = 'TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4JIl7HafKfQQ/5LsVFFOZGD24DEJC28GMyszZP2MG/Qw0SE671I4y0BVXQk99DQxvgSrfBN2b5LlkPkMW9Ur6w76iPS2iRAFp42buydSNFiFxopFSw7jenDA+CnW1dpVVCwq8MPuGWPUuME0OsSp0HUKl6nq5ma6lKe2Mavvj+1arCjC7LvZ4WngVYwloD/Q+eZ8RJ6VABdKHizCsZhe3b1hvPTC7TbXvAN1kgyXIDKmVsw8zgW+HDUyaUbLcVgKHAQbdV3R+s9vez0hBhLp+ssIECoHUsjHsu0pFlMvvcpG+yxgkhOnf5u22jflQzdYyTPkluhwUZoWnYU0DGWbWmCttPsUijVL2qRluhgzP/Kt6aSN2pi2VnlAS6La6ABdQd0BUOr3O8bXTw7w3mwRlJIkfwOGEO8BBnXtCj2IOHjhUiJSQnY8UgXI+n/1+1YnJHunUH1g9/CagTvARvH72PUFgxSilKf5zpD4E5396lZ5uwsziz5z97tg9EZB0N1/1kyVonjtVmcdKkNsNpv32JQZR2DHf4FgKZgNslqAfZYkK9YkCg7x0dqbmqsmvM4dhM9VjwmhmaA9mShiOCEI4XBVAFyqLlDZnzlDEbEKVPrD+2+9pjNye5US2NPe63vaDDgTxIb11HB0ZjAxJNytIgL0sYVLdQOMcoEmFZ1/STB/+tGW0ucp3SbaeJlGeAXK'
os.environ['DEFAULT_CLIENT_ID'] = '09PF05VD'
os.environ['LOG_LEVEL'] = 'INFO'

# Import handlers after setting environment
sys.path.insert(0, 'scheduling-actions')
sys.path.insert(0, 'information-actions')
from handler import lambda_handler as scheduling_handler
sys.path.pop(0)
from handler import lambda_handler as information_handler

def print_test_header(test_name):
    print("\n" + "="*80)
    print(f"  TEST: {test_name}")
    print("="*80)

def print_result(success, message, details=None):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n{status}: {message}")
    if details:
        print(f"Details: {json.dumps(details, indent=2)}")

def test_dashboard_api():
    """Test 1: Get customer projects from Dashboard API"""
    print_test_header("Dashboard API - Get Customer Projects")

    # Test customer from docs/api-calls.txt
    test_event = {
        "apiPath": "/get-projects",
        "httpMethod": "POST",
        "actionGroup": "information",
        "parameters": [
            {"name": "customer_id", "value": "1645869"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }

    try:
        response = information_handler(test_event, None)

        # Parse response
        status_code = response['response']['httpStatusCode']
        body = json.loads(response['response']['responseBody']['application/json']['body'])

        if status_code == 200:
            projects = body.get('projects', [])
            print_result(
                True,
                f"Successfully fetched {body.get('total_projects', 0)} projects",
                {
                    "customer_id": body.get('customer_id'),
                    "total_projects": body.get('total_projects'),
                    "mock_mode": body.get('mock_mode'),
                    "sample_project": projects[0] if projects else None
                }
            )
            return True, projects
        else:
            print_result(False, f"API returned status {status_code}", body)
            return False, None

    except Exception as e:
        print_result(False, f"Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def test_get_available_dates():
    """Test 2: Get available scheduling dates"""
    print_test_header("Scheduler API - Get Available Dates")

    # Test project from docs/api-calls.txt
    test_event = {
        "apiPath": "/get-available-dates",
        "httpMethod": "POST",
        "actionGroup": "scheduling",
        "parameters": [
            {"name": "project_id", "value": "7750176"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }

    try:
        response = scheduling_handler(test_event, None)

        # Parse response
        status_code = response['response']['httpStatusCode']
        body = json.loads(response['response']['responseBody']['application/json']['body'])

        if status_code == 200:
            dates = body.get('available_dates', [])
            print_result(
                True,
                f"Successfully fetched {len(dates)} available dates",
                {
                    "project_id": body.get('project_id'),
                    "available_dates": dates[:5],  # Show first 5
                    "request_id": body.get('request_id'),
                    "mock_mode": body.get('mock_mode')
                }
            )
            return True, body.get('request_id')
        else:
            print_result(False, f"API returned status {status_code}", body)
            return False, None

    except Exception as e:
        print_result(False, f"Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def test_get_project_details():
    """Test 3: Get detailed project information"""
    print_test_header("Dashboard API - Get Project Details")

    test_event = {
        "apiPath": "/get-project-details",
        "httpMethod": "POST",
        "actionGroup": "information",
        "parameters": [
            {"name": "project_id", "value": "2109511"},
            {"name": "customer_id", "value": "1645869"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }

    try:
        response = information_handler(test_event, None)

        # Parse response
        status_code = response['response']['httpStatusCode']
        body = json.loads(response['response']['responseBody']['application/json']['body'])

        if status_code == 200:
            details = body.get('project_details', {})
            print_result(
                True,
                "Successfully fetched project details",
                {
                    "project_id": details.get('project_id'),
                    "order_number": details.get('order_number'),
                    "status": details.get('status'),
                    "category": details.get('category'),
                    "mock_mode": body.get('mock_mode')
                }
            )
            return True
        else:
            print_result(False, f"API returned status {status_code}", body)
            return False

    except Exception as e:
        print_result(False, f"Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_authentication_headers():
    """Test 4: Verify authentication headers are correct"""
    print_test_header("Authentication Configuration")

    # Import config modules
    sys.path.insert(0, 'scheduling-actions')
    from config import get_auth_headers, get_api_config, API_BASE_URLS, DEFAULT_CLIENT_ID

    # Test config
    config = get_api_config()
    headers = get_auth_headers()

    print("\n📋 Configuration:")
    print(f"  Base URL: {config['base_url']}")
    print(f"  Environment: dev")
    print(f"  Client ID: {DEFAULT_CLIENT_ID}")

    print("\n📋 Authentication Headers:")
    for key, value in headers.items():
        if key == "Authorization":
            print(f"  {key}: Bearer [TOKEN_SET - {len(value)-7} chars]")
        else:
            print(f"  {key}: {value}")

    # Verify correct header format
    checks = [
        ("Authorization header exists", "Authorization" in headers),
        ("Authorization starts with Bearer", headers.get("Authorization", "").startswith("Bearer ")),
        ("Client_Id header exists", "Client_Id" in headers),
        ("Client_Id is correct", headers.get("Client_Id") == "09PF05VD"),
        ("Base URL is dev", config['base_url'] == API_BASE_URLS['dev'])
    ]

    all_passed = True
    print("\n🔍 Validation Checks:")
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    return all_passed

def main():
    """Run all API integration tests"""
    print("\n" + "="*80)
    print("  PROJECTFORCE API INTEGRATION TEST SUITE")
    print("  Testing against: https://api-cx-portal.dev.projectsforce.com")
    print("="*80)

    results = {}

    # Test 1: Authentication configuration
    results['auth_config'] = test_authentication_headers()

    # Test 2: Dashboard API - Get projects
    success, projects = test_dashboard_api()
    results['dashboard_api'] = success

    # Test 3: Scheduler API - Get available dates
    if success and projects:
        # Try with first project if available
        success, request_id = test_get_available_dates()
        results['scheduler_api'] = success
    else:
        print("\n⚠️  Skipping scheduler test (no projects available)")
        results['scheduler_api'] = None

    # Test 4: Project details
    results['project_details'] = test_get_project_details()

    # Summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)

    for test_name, result in results.items():
        if result is None:
            status = "⏭️  SKIPPED"
        elif result:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        print(f"  {status}: {test_name}")

    total_tests = sum(1 for r in results.values() if r is not None)
    passed_tests = sum(1 for r in results.values() if r is True)

    print(f"\n  Total: {passed_tests}/{total_tests} tests passed")
    print("="*80 + "\n")

    return all(r is not False for r in results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
