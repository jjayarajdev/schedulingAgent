#!/usr/bin/env python3
"""
ProjectForce Authentication Script
Gets a fresh access token from auth.dev.projectsforce.com
"""

import requests
import json
import sys
from datetime import datetime, timedelta

AUTH_URL = "https://auth.dev.projectsforce.com"
API_URL = "https://api-cx-portal.dev.projectsforce.com"

EMAIL = "jay.jayakeerthy@syntegreti.com"
PASSWORD = "All0wj@y5677"

def get_token():
    """
    Attempt to get access token from the token endpoint
    Note: This may require the encrypted password format
    """
    print("=" * 60)
    print("ProjectForce Authentication")
    print("=" * 60)
    print(f"Auth URL: {AUTH_URL}")
    print(f"User: {EMAIL}")
    print()

    # Try Method 1: Direct token request (may work if session exists)
    print("Method 1: Requesting token directly...")
    print(f"POST {AUTH_URL}/token")
    print()

    try:
        response = requests.post(
            f"{AUTH_URL}/token",
            headers={"Content-Type": "application/json"},
            json={"username": EMAIL},
            timeout=10
        )

        print(f"HTTP Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✓ SUCCESS!")
            print()
            return data

        print(f"Response: {response.text[:200]}")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        print()

    # Try Method 2: Check with plain password
    print("Method 2: Authenticating with check.v1 (plain password)...")
    print(f"POST {AUTH_URL}/check.v1")
    print()

    try:
        response = requests.post(
            f"{AUTH_URL}/check.v1",
            headers={"Content-Type": "application/json"},
            json={
                "username": EMAIL,
                "password": PASSWORD,
                "reCaptcha": "",
                "method": "POST"
            },
            timeout=10
        )

        print(f"HTTP Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        print()

        if response.status_code == 200:
            # After successful check, try to get token
            print("Authentication check passed. Requesting token...")

            token_response = requests.post(
                f"{AUTH_URL}/token",
                headers={"Content-Type": "application/json"},
                cookies=response.cookies,
                json={"username": EMAIL},
                timeout=10
            )

            if token_response.status_code == 200:
                data = token_response.json()
                print("✓ SUCCESS!")
                print()
                return data

    except Exception as e:
        print(f"✗ Error: {e}")
        print()

    return None

def test_token(access_token, client_id):
    """Test the access token against the API"""
    print("=" * 60)
    print("Testing Access Token")
    print("=" * 60)
    print()

    customer_id = "1645869"  # Test customer
    url = f"{API_URL}/dashboard/get/{client_id}/{customer_id}"

    print(f"GET {url}")
    print(f"Authorization: Bearer {access_token[:40]}...")
    print()

    try:
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        print(f"HTTP Status: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()
            projects = data.get('data', [])
            print(f"✓ SUCCESS! Found {len(projects)} projects")
            print()

            if projects:
                project = projects[0]
                print("Sample Project:")
                print(f"  ID: {project.get('id')}")
                print(f"  Order Number: {project.get('order_number')}")
                print(f"  Category: {project.get('category')}")
                print(f"  Status: {project.get('status')}")
            print()

            # Save response
            with open('dashboard_api_response.json', 'w') as f:
                json.dump(data, f, indent=2)
            print("✓ Full response saved to: dashboard_api_response.json")

            return True
        else:
            print(f"✗ FAILED")
            print(f"Response: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    # Get token
    token_data = get_token()

    if not token_data:
        print()
        print("=" * 60)
        print("Authentication Failed")
        print("=" * 60)
        print()
        print("Unable to obtain access token programmatically.")
        print()
        print("MANUAL STEPS TO GET TOKEN:")
        print("1. Open browser and navigate to:")
        print("   https://pf.dev.projectsforce.com/")
        print()
        print("2. Log in with:")
        print(f"   Email: {EMAIL}")
        print(f"   Password: {PASSWORD}")
        print()
        print("3. Open Browser DevTools (F12) → Network tab")
        print()
        print("4. Look for a request to 'token' endpoint")
        print()
        print("5. In the Response, copy the 'access_token' value")
        print()
        print("6. Run this command to update Lambda:")
        print()
        print("   ./update_lambda_token.sh <YOUR_ACCESS_TOKEN>")
        print()
        sys.exit(1)

    # Display token info
    print()
    print("=" * 60)
    print("Token Information")
    print("=" * 60)
    print()

    access_token = token_data.get('access_token', '')
    client_id = token_data.get('client_id', '')
    expires_in = token_data.get('expires_in', 0)
    user_id = token_data.get('user_id', '')

    expiry_time = datetime.now() + timedelta(seconds=expires_in)

    print(f"Access Token: {access_token[:50]}...")
    print(f"Client ID: {client_id}")
    print(f"User ID: {user_id}")
    print(f"Expires In: {expires_in} seconds ({expires_in // 3600} hours)")
    print(f"Expiry Time: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Save token data
    with open('token_data.json', 'w') as f:
        json.dump(token_data, f, indent=2)
    print("✓ Token data saved to: token_data.json")
    print()

    # Test the token
    if test_token(access_token, client_id):
        print()
        print("=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print()
        print("To update Lambda function:")
        print()
        print(f"  aws lambda update-function-configuration \\")
        print(f"    --function-name pf-information-actions \\")
        print(f"    --environment 'Variables={{")
        print(f"      USE_MOCK_API=false,")
        print(f"      ENVIRONMENT=dev,")
        print(f"      BEARER_TOKEN={access_token},")
        print(f"      DEFAULT_CLIENT_ID={client_id},")
        print(f"      LOG_LEVEL=INFO,")
        print(f"      DYNAMODB_TABLE_PREFIX=pf")
        print(f"    }}'")
        print()

        # Create update script
        with open('update_lambda_token.sh', 'w') as f:
            f.write(f'''#!/bin/bash
# Update Lambda with fresh token
# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

aws lambda update-function-configuration \\
  --function-name pf-information-actions \\
  --environment 'Variables={{
    USE_MOCK_API=false,
    ENVIRONMENT=dev,
    BEARER_TOKEN={access_token},
    DEFAULT_CLIENT_ID={client_id},
    LOG_LEVEL=INFO,
    DYNAMODB_TABLE_PREFIX=pf
  }}'

echo ""
echo "Lambda function updated successfully!"
''')

        import os
        os.chmod('update_lambda_token.sh', 0o755)
        print("✓ Update script created: ./update_lambda_token.sh")
        print()

if __name__ == '__main__':
    main()
