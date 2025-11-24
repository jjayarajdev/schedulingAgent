#!/usr/bin/env python3
"""
Simple proxy server to handle ProjectForce authentication
Avoids CORS issues by proxying requests from the browser
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import sys

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

AUTH_URL = "https://auth.dev.projectsforce.com"
PORTAL_URL = "https://projectsforce-validation.cx-portal.dev.projectsforce.com"
API_URL = "https://api-cx-portal.dev.projectsforce.com"

@app.route('/api/login', methods=['POST'])
def login():
    """Proxy login request to ProjectForce"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        print(f"Login request for: {email}")

        # Try portal login first
        print(f"Trying portal login: {PORTAL_URL}/api/login")
        response = requests.post(
            f"{PORTAL_URL}/api/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"Portal response status: {response.status_code}")
        print(f"Portal response text (first 200 chars): {response.text[:200]}")

        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('token'):
                    print("✓ Portal login successful")
                    return jsonify(data)
            except Exception as json_err:
                print(f"Portal returned non-JSON response: {json_err}")

        # Try auth server
        print(f"Trying auth server: {AUTH_URL}/check.v1")
        check_response = requests.post(
            f"{AUTH_URL}/check.v1",
            json={
                "username": email,
                "password": password,
                "reCaptcha": "",
                "method": "POST"
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"Auth check status: {check_response.status_code}")
        print(f"Auth check response (first 200 chars): {check_response.text[:200]}")

        if check_response.status_code == 200:
            # Try to get token
            print(f"Getting token from: {AUTH_URL}/token")
            token_response = requests.post(
                f"{AUTH_URL}/token",
                json={"username": email},
                headers={"Content-Type": "application/json"},
                cookies=check_response.cookies,
                timeout=10
            )

            print(f"Token response status: {token_response.status_code}")
            print(f"Token response (first 200 chars): {token_response.text[:200]}")

            if token_response.status_code == 200:
                try:
                    token_data = token_response.json()
                    if token_data.get('access_token'):
                        print("✓ Auth server login successful")
                        return jsonify(token_data)
                except Exception as token_err:
                    print(f"Token endpoint returned non-JSON: {token_err}")

        # Login failed
        print("✗ Login failed")
        return jsonify({
            "error": "Login failed",
            "portal_status": response.status_code,
            "auth_status": check_response.status_code if 'check_response' in locals() else None
        }), 401

    except Exception as e:
        import traceback
        print(f"✗ Error: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@app.route('/api/regenerate-token', methods=['POST'])
def regenerate_token():
    """Regenerate token using user_id and client_id (when already logged in)"""
    try:
        data = request.json
        user_id = data.get('user_id')
        client_id = data.get('client_id', '09PF05VD')

        print(f"Regenerating token for user: {user_id}")

        response = requests.post(
            f"{AUTH_URL}/regenerate-token",
            json={
                "client_id": client_id,
                "user_id": user_id,
                "login_via_password": False,
                "client_secret": "devappssecret",
                "device_type": "web",
                "grant_type": "authorization_code",
                "secret_client_id": "devapps"
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"Regenerate response status: {response.status_code}")

        if response.status_code == 200:
            token_data = response.json()
            print("✓ Token regenerated successfully")
            return jsonify(token_data)
        else:
            print(f"✗ Failed to regenerate token: {response.text[:200]}")
            return jsonify({"error": "Failed to regenerate token", "status": response.status_code}), response.status_code

    except Exception as e:
        print(f"✗ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-token', methods=['POST'])
def test_token():
    """Test a token against the API"""
    try:
        data = request.json
        token = data.get('token')
        client_id = data.get('client_id', '09PF05VD')
        customer_id = data.get('customer_id', '1645869')

        print(f"Testing token for client {client_id}")

        response = requests.get(
            f"{API_URL}/dashboard/get/{client_id}/{customer_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        print(f"API test status: {response.status_code}")

        if response.status_code == 200:
            print("✓ Token is valid")
            return jsonify(response.json())
        else:
            print("✗ Token is invalid or expired")
            return jsonify(response.json()), response.status_code

    except Exception as e:
        print(f"✗ Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("ProjectForce Authentication Proxy Server")
    print("=" * 60)
    print("Starting server on http://localhost:5002")
    print("This proxy will handle authentication and avoid CORS issues")
    print("=" * 60)
    print()

    app.run(host='0.0.0.0', port=5002, debug=True)
