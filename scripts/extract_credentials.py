#!/usr/bin/env python3
"""
Extract ProjectForce API credentials from browser local storage
This script reads credentials stored by the browser for automated deployment
"""
import json
import os
import sys
from pathlib import Path

def find_chrome_local_storage():
    """Find Chrome's Local Storage location"""
    home = Path.home()

    # macOS Chrome location
    chrome_dir = home / "Library/Application Support/Google/Chrome"

    if not chrome_dir.exists():
        return None

    # Look for Local Storage files
    profiles = ["Default", "Profile 1", "Profile 2"]

    for profile in profiles:
        local_storage = chrome_dir / profile / "Local Storage/leveldb"
        if local_storage.exists():
            return local_storage

    return None

def extract_credentials_from_leveldb(leveldb_path):
    """Extract credentials from Chrome's LevelDB"""
    credentials = {
        'client_id': None,
        'user_id': None,
        'access_token': None,
        'refresh_token': None
    }

    # Try to read .ldb files
    for ldb_file in leveldb_path.glob("*.ldb"):
        try:
            with open(ldb_file, 'rb') as f:
                content = f.read()

                # Try to decode as UTF-8 with errors ignored
                text = content.decode('utf-8', errors='ignore')

                # Look for our keys
                if 'client_id' in text:
                    # Extract client_id value
                    idx = text.find('client_id')
                    if idx != -1:
                        # Look for value after the key
                        start = idx + len('client_id')
                        # Find next non-control character sequence
                        value_text = text[start:start+100]
                        # Extract alphanumeric value
                        import re
                        match = re.search(r'([A-Z0-9]{8,})', value_text)
                        if match:
                            credentials['client_id'] = match.group(1)

                if 'accesstoken' in text.lower():
                    idx = text.lower().find('accesstoken')
                    if idx != -1:
                        start = idx + 11
                        value_text = text[start:start+500]
                        # Extract Bearer token (typically starts with ey for JWT)
                        match = re.search(r'(ey[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)', value_text)
                        if match:
                            credentials['access_token'] = match.group(1)

                if 'refreshToken' in text:
                    idx = text.find('refreshToken')
                    if idx != -1:
                        start = idx + 12
                        value_text = text[start:start+500]
                        match = re.search(r'(ey[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)', value_text)
                        if match:
                            credentials['refresh_token'] = match.group(1)

                # Look for user id
                if '"id"' in text:
                    idx = text.find('"id"')
                    if idx != -1:
                        start = idx + 4
                        value_text = text[start:start+50]
                        match = re.search(r'(\d{7,})', value_text)
                        if match:
                            credentials['user_id'] = match.group(1)

        except Exception as e:
            continue

    return credentials

def read_from_env_file():
    """Read credentials from .env file if it exists"""
    env_file = Path("/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/.env")

    if not env_file.exists():
        return None

    credentials = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")

                    if key == 'CLIENT_ID':
                        credentials['client_id'] = value
                    elif key == 'USER_ID':
                        credentials['user_id'] = value
                    elif key == 'ACCESS_TOKEN':
                        credentials['access_token'] = value
                    elif key == 'REFRESH_TOKEN':
                        credentials['refresh_token'] = value

    return credentials if credentials else None

def main():
    print("🔍 Looking for ProjectForce API credentials...")
    print()

    # First try .env file
    credentials = read_from_env_file()

    if credentials and all(credentials.values()):
        print("✅ Found credentials in .env file")
    else:
        print("⚠️  Could not find complete credentials in .env file")
        print()
        print("Please create a .env file with the following format:")
        print()
        print("CLIENT_ID=09PF05VD")
        print("USER_ID=1646085")
        print("ACCESS_TOKEN=eyJ...")
        print("REFRESH_TOKEN=eyJ...")
        print()
        print("You can get these from Chrome DevTools:")
        print("1. Open https://projectsforce-validation.cx-portal.dev.projectsforce.com")
        print("2. Press F12 (DevTools)")
        print("3. Go to Application → Local Storage")
        print("4. Find: client_id, id, accesstoken, refreshToken")
        return 1

    # Print credentials for deployment script to read
    print()
    print("=" * 60)
    print("CREDENTIALS FOR DEPLOYMENT")
    print("=" * 60)
    print(f"CLIENT_ID={credentials.get('client_id', '')}")
    print(f"USER_ID={credentials.get('user_id', '')}")
    print(f"ACCESS_TOKEN={credentials.get('access_token', '')}")
    print(f"REFRESH_TOKEN={credentials.get('refresh_token', '')}")
    print("=" * 60)

    return 0

if __name__ == '__main__':
    sys.exit(main())
