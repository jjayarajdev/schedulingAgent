#!/usr/bin/env python3
"""
Get fresh Bearer token from ProjectForce API and update Secrets Manager
"""
import requests
import json
import boto3
import sys

# API Configuration
API_URL = "https://api-cx-portal.dev.projectsforce.com"
AUTH_URL = f"{API_URL}/authentication/login?identifier=projectsforce-validation"

# Credentials (from user's browser login)
EMAIL = "jay@mailinator.com"
PASSWORD = "U2FsdGVkX1/ZiR9CNgR3SeEgf5MHKaC1npGOA+P5PTY="  # Encrypted password
DEVICE_TYPE = 1

# AWS Configuration
SECRET_NAME = "projectforce/api/dev/credentials"
REGION = "us-east-1"
CLIENT_ID = "09PF05VD"

def get_fresh_token():
    """Get fresh access token from ProjectForce API"""
    print("=" * 60)
    print("Getting Fresh Bearer Token")
    print("=" * 60)
    print(f"Auth URL: {AUTH_URL}")
    print(f"Email: {EMAIL}")
    print()

    try:
        # Make authentication request
        print(f"POST {AUTH_URL}")

        payload = {
            "email": EMAIL,
            "password": PASSWORD,
            "device_type": DEVICE_TYPE
        }

        headers = {
            "Content-Type": "application/json",
            "Origin": "https://pf.dev.projectsforce.com",
            "Referer": "https://pf.dev.projectsforce.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }

        response = requests.post(
            AUTH_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        print(f"HTTP Status: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()

            access_token = data.get('accesstoken')
            refresh_token = data.get('refrestoken')  # Note: API typo "refres"

            if not access_token:
                print("✗ No access token in response")
                print(f"Response: {json.dumps(data, indent=2)}")
                return None

            print("✅ SUCCESS! Got fresh token")
            print(f"Access Token: {access_token[:50]}...")
            print(f"Token Length: {len(access_token)} chars")
            if refresh_token:
                print(f"Refresh Token: {refresh_token[:50]}...")
            print()

            return {
                "bearer_token": access_token,
                "refresh_token": refresh_token if refresh_token else "",
                "client_id": CLIENT_ID,
                "api_base_url": API_URL
            }
        else:
            print(f"✗ Authentication failed")
            print(f"Response: {response.text[:500]}")
            return None

    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def test_token(bearer_token):
    """Test the token against the API"""
    print("=" * 60)
    print("Testing Bearer Token")
    print("=" * 60)

    test_customer_id = "1646085"
    test_url = f"{API_URL}/dashboard/get/{CLIENT_ID}/{test_customer_id}"

    print(f"GET {test_url}")
    print(f"Authorization: Bearer {bearer_token[:40]}...")
    print()

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

        print(f"HTTP Status: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()
            projects = data.get('data', [])
            print(f"✅ SUCCESS! Found {len(projects)} projects")
            print()
            return True
        else:
            print(f"✗ FAILED")
            print(f"Response: {response.text[:300]}")
            print()
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def update_secrets_manager(token_data):
    """Update AWS Secrets Manager with new token"""
    print("=" * 60)
    print("Updating AWS Secrets Manager")
    print("=" * 60)
    print(f"Secret: {SECRET_NAME}")
    print(f"Region: {REGION}")
    print()

    try:
        client = boto3.client('secretsmanager', region_name=REGION)

        # Update secret
        response = client.update_secret(
            SecretId=SECRET_NAME,
            SecretString=json.dumps(token_data)
        )

        print("✅ SUCCESS! Secret updated")
        print(f"ARN: {response['ARN']}")
        print(f"Version: {response['VersionId']}")
        print()
        return True

    except Exception as e:
        print(f"✗ Error updating secret: {e}")
        return False

def main():
    print()

    # Get fresh token
    token_data = get_fresh_token()

    if not token_data:
        print()
        print("=" * 60)
        print("FAILED: Could not get fresh token")
        print("=" * 60)
        print()
        print("Please check:")
        print("1. Email and password are correct")
        print("2. API endpoint is accessible")
        print("3. Network connectivity")
        print()
        sys.exit(1)

    # Test the token
    if not test_token(token_data['bearer_token']):
        print()
        print("=" * 60)
        print("WARNING: Token obtained but not working")
        print("=" * 60)
        print()
        print("Proceeding to update Secrets Manager anyway...")
        print()

    # Update Secrets Manager
    if update_secrets_manager(token_data):
        print()
        print("=" * 60)
        print("ALL DONE! ✅")
        print("=" * 60)
        print()
        print("The Lambda functions will now use the fresh token")
        print("from Secrets Manager automatically.")
        print()
        print("Run tests to verify:")
        print("  python3 scripts/test_and_report.py")
        print()
    else:
        print()
        print("=" * 60)
        print("FAILED: Could not update Secrets Manager")
        print("=" * 60)
        print()
        print("You can manually update with:")
        print()
        print(f'  aws secretsmanager update-secret \\')
        print(f'    --secret-id {SECRET_NAME} \\')
        print(f'    --secret-string \'{{')
        print(f'      "bearer_token": "{token_data["bearer_token"]}",')
        print(f'      "client_id": "{token_data["client_id"]}",')
        print(f'      "api_base_url": "{token_data["api_base_url"]}"')
        print(f'    }}\' \\')
        print(f'    --region {REGION}')
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()
