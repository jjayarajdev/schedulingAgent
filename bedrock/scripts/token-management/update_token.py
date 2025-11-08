#!/usr/bin/env python3
"""
Simple script to update Bearer token in Secrets Manager
Usage: python3 update_token.py <YOUR_BEARER_TOKEN>
"""
import boto3
import json
import sys
import requests

SECRET_NAME = "projectforce/api/dev/credentials"
REGION = "us-east-1"
CLIENT_ID = "09PF05VD"
API_URL = "https://api-cx-portal.dev.projectsforce.com"

def test_token(bearer_token):
    """Test the token against the API"""
    print("\nTesting token...")
    test_customer_id = "1646085"
    test_url = f"{API_URL}/dashboard/get/{CLIENT_ID}/{test_customer_id}"

    try:
        response = requests.get(
            test_url,
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Client_Id": CLIENT_ID,
                "Content-Type": "application/json"
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            projects = data.get('data', [])
            print(f"✅ Token is VALID! Found {len(projects)} projects\n")
            return True
        else:
            print(f"⚠️  Token test returned HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}\n")
            return False
    except Exception as e:
        print(f"⚠️  Token test failed: {e}\n")
        return False

def update_secret(bearer_token):
    """Update AWS Secrets Manager"""
    print("Updating Secrets Manager...")

    token_data = {
        "bearer_token": bearer_token,
        "client_id": CLIENT_ID,
        "api_base_url": API_URL
    }

    try:
        client = boto3.client('secretsmanager', region_name=REGION)
        response = client.update_secret(
            SecretId=SECRET_NAME,
            SecretString=json.dumps(token_data)
        )
        print(f"✅ Secret updated successfully!")
        print(f"Version: {response['VersionId']}\n")
        return True
    except Exception as e:
        print(f"❌ Failed to update secret: {e}\n")
        return False

def main():
    if len(sys.argv) != 2:
        print("\n" + "=" * 70)
        print("Bearer Token Updater")
        print("=" * 70)
        print("\nUsage: python3 update_token.py <YOUR_BEARER_TOKEN>")
        print("\nHow to get your Bearer token:")
        print("1. Open https://pf.dev.projectsforce.com in browser")
        print("2. Login with your credentials")
        print("3. Open DevTools (F12) → Network tab")
        print("4. Look for any API request (e.g., dashboard/get)")
        print("5. In Request Headers, find 'authorization: Bearer <TOKEN>'")
        print("6. Copy the token (the long string after 'Bearer ')")
        print("\nThen run:")
        print("  python3 update_token.py 'YOUR_TOKEN_HERE'")
        print()
        sys.exit(1)

    bearer_token = sys.argv[1].strip()

    print("\n" + "=" * 70)
    print("Bearer Token Updater")
    print("=" * 70)
    print(f"\nToken length: {len(bearer_token)} characters")
    print(f"Token preview: {bearer_token[:50]}...\n")

    # Test the token
    token_valid = test_token(bearer_token)

    # Update secret even if test fails (user might want to proceed)
    if not token_valid:
        response = input("Token test failed. Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(1)

    # Update Secrets Manager
    if update_secret(bearer_token):
        print("=" * 70)
        print("SUCCESS! Token updated in Secrets Manager")
        print("=" * 70)
        print("\nThe Lambda functions will now use this token automatically.")
        print("\nRun tests to verify:")
        print("  python3 scripts/test_and_report.py")
        print()
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
