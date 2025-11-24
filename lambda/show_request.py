#!/usr/bin/env python3
"""
Show Exact HTTP Request Details
Displays the complete request that would be sent to ProjectForce API
"""

import sys
import os
import json

# Add lambda directories to path
sys.path.insert(0, 'scheduling-actions')

# Set environment variables
os.environ['USE_MOCK_API'] = 'false'
os.environ['ENVIRONMENT'] = 'dev'
os.environ['BEARER_TOKEN'] = 'TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4JIl7HafKfQQ/5IXVFFOZGD24PcJ3isGqpYzN+uMG9LwX3zevOY4i7jfXVJeKhA83l8EAnSQoGAfs4Il2H1/nGJ0m6byLeLipcwspY3iEY/t73Ld7gz84ZCRnqeZMU7hl4PdkUTB1M4t0sdclTKLKOFzIhs4xI5CWyGn04695Fmnpw3+q1DgAPmM7/2/8FfnkGeXriWm2KcZrlhFxh5sT5ubAThM6CARNLZViQql3n+YXgWikkjEAPNVs39Ni1HnwvMfZGmFgN2N9P882uvs6z0NGR00bezih8ExTwvedFBAvgkzWuYnvunOUHDRz2EBfGT6WhhBmqDBSfMW4d87Z6SabKWjcSBrXVWQacRvDhtoyZ4mYK/7vwGAJmPVH0evFRyE5iPdMSkpUmEfzfRgP+9GcUqiJgGB1t4+79PRW7wd+cXBlMQr2HnEb4fbdaD2hY0nzZHCeHNnLLjTeV4hZowqcP601vtJt69Ymil4L2Vs5/57HMbP50hxpcxaffSeWbvo05239KLJdtt08GIKOv2OCryGP0PIaZY3i9uQzQlGMGsEhiRUQuW/z+7uVpNUyfuw93QPh+s9+0xA9hDX03nQ70RrH8hcIDtICwy9iY91y02GNqOUyqDpJILt2d4QKWixk5JECJgu22cW4ImJm275/KwWXo66oIfZS5XJQ03+Aw4arafjOuTGiY0UGc1u'
os.environ['DEFAULT_CLIENT_ID'] = '09PF05VD'

from config import get_api_config, get_auth_headers

def show_dashboard_request():
    """Show Dashboard API request details"""
    print("="*80)
    print("  DASHBOARD API REQUEST")
    print("="*80)

    client_id = "09PF05VD"
    customer_id = "1645869"

    config = get_api_config(client_id)
    headers = get_auth_headers(None, client_id)

    url = f"{config['dashboard_url']}/{customer_id}"

    print(f"\nURL: {url}")
    print(f"\nMethod: GET")
    print(f"\nHeaders:")
    for key, value in headers.items():
        if key == "Authorization":
            print(f"  {key}: Bearer [TOKEN - {len(value)-7} chars]")
        else:
            print(f"  {key}: {value}")

    # Show as curl command
    print(f"\n{'='*80}")
    print("  CURL COMMAND")
    print("="*80)
    print(f"\ncurl --location '{url}' \\")
    for key, value in headers.items():
        print(f"  --header '{key}: {value}' \\")
    print()

    # Show as JSON
    print(f"{'='*80}")
    print("  REQUEST AS JSON")
    print("="*80)
    request_json = {
        "method": "GET",
        "url": url,
        "headers": headers
    }
    print(json.dumps(request_json, indent=2))

def show_scheduler_request():
    """Show Scheduler API request details"""
    print("\n\n" + "="*80)
    print("  SCHEDULER API REQUEST (Get Available Dates)")
    print("="*80)

    client_id = "09PF05VD"
    project_id = "7750176"
    date = "2025-10-28"

    config = get_api_config(client_id)
    headers = get_auth_headers(None, client_id)

    url = f"{config['scheduler_base_url']}/project/{project_id}/date/{date}/selected/{date}/get-rescheduler-slots"

    print(f"\nURL: {url}")
    print(f"\nMethod: GET")
    print(f"\nHeaders:")
    for key, value in headers.items():
        if key == "Authorization":
            print(f"  {key}: Bearer [TOKEN - {len(value)-7} chars]")
        else:
            print(f"  {key}: {value}")

    # Show as curl command
    print(f"\n{'='*80}")
    print("  CURL COMMAND")
    print("="*80)
    print(f"\ncurl --location '{url}' \\")
    for key, value in headers.items():
        print(f"  --header '{key}: {value}' \\")
    print()

    # Show as JSON
    print(f"{'='*80}")
    print("  REQUEST AS JSON")
    print("="*80)
    request_json = {
        "method": "GET",
        "url": url,
        "headers": headers
    }
    print(json.dumps(request_json, indent=2))

def show_confirm_appointment_request():
    """Show Confirm Appointment API request details"""
    print("\n\n" + "="*80)
    print("  SCHEDULER API REQUEST (Confirm Appointment)")
    print("="*80)

    client_id = "09PF05VD"
    project_id = "7750176"

    config = get_api_config(client_id)
    headers = get_auth_headers(None, client_id)

    url = f"{config['scheduler_base_url']}/project/{project_id}/schedule"

    payload = {
        "created_at": "10-29-2025 18:00:00",
        "date": "2025-11-01",
        "time": "09:00",
        "request_id": 1619,
        "is_chatbot": "true"
    }

    print(f"\nURL: {url}")
    print(f"\nMethod: POST")
    print(f"\nHeaders:")
    for key, value in headers.items():
        if key == "Authorization":
            print(f"  {key}: Bearer [TOKEN - {len(value)-7} chars]")
        else:
            print(f"  {key}: {value}")

    print(f"\nBody:")
    print(json.dumps(payload, indent=2))

    # Show as curl command
    print(f"\n{'='*80}")
    print("  CURL COMMAND")
    print("="*80)
    print(f"\ncurl --location '{url}' \\")
    for key, value in headers.items():
        print(f"  --header '{key}: {value}' \\")
    print(f"  --data '{json.dumps(payload)}' \\")
    print()

    # Show as JSON
    print(f"{'='*80}")
    print("  REQUEST AS JSON")
    print("="*80)
    request_json = {
        "method": "POST",
        "url": url,
        "headers": headers,
        "body": payload
    }
    print(json.dumps(request_json, indent=2))

def main():
    print("\n" + "="*80)
    print("  PROJECTFORCE API - REQUEST DETAILS")
    print("  Environment: dev")
    print("  Base URL: https://api-cx-portal.dev.projectsforce.com")
    print("="*80)

    show_dashboard_request()
    show_scheduler_request()
    show_confirm_appointment_request()

    print("\n" + "="*80)
    print("  NOTES")
    print("="*80)
    print("""
1. Copy the CURL command and run it in your terminal to test manually
2. Copy the JSON to use in Postman or other API testing tools
3. The Bearer token shown above is truncated for display
4. All headers match the format from docs/api-calls.txt
    """)

if __name__ == "__main__":
    main()
