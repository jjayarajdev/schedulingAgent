"""
Configuration for Scheduling Actions Lambda
Supports both mock and real API modes
"""
import os
from typing import Dict

# Environment variables
USE_MOCK_API = os.getenv("USE_MOCK_API", "true").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Real ProjectForce API endpoints
API_BASE_URLS = {
    "dev": "https://api-cx-portal.dev.projectsforce.com",
    "staging": "https://api-cx-portal.staging.projectsforce.com",
    "prod": "https://api-cx-portal.projectsforce.com"
}
CUSTOMER_SCHEDULER_BASE_API_URL = os.getenv(
    "CUSTOMER_SCHEDULER_API_URL",
    API_BASE_URLS.get(ENVIRONMENT, API_BASE_URLS["dev"])
)

# Authentication
BEARER_TOKEN = os.getenv("BEARER_TOKEN", "")
DEFAULT_CLIENT_ID = os.getenv("DEFAULT_CLIENT_ID", "09PF05VD")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# DynamoDB table for session management
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "scheduling-agent-sessions-dev")

# Feature flags (for gradual rollout)
ENABLE_REAL_CONFIRM = os.getenv("ENABLE_REAL_CONFIRM", "false").lower() == "true"
ENABLE_REAL_CANCEL = os.getenv("ENABLE_REAL_CANCEL", "false").lower() == "true"

def get_api_config(client_id: str = None, env: str = None) -> Dict[str, str]:
    """
    Generate API configuration based on environment and client
    """
    if env is None:
        env = ENVIRONMENT
    if client_id is None:
        client_id = DEFAULT_CLIENT_ID

    base_url = API_BASE_URLS.get(env, API_BASE_URLS["dev"])

    return {
        "base_url": base_url,
        "dashboard_url": f"{base_url}/dashboard/get/{client_id}",
        "scheduler_base_url": f"{base_url}/scheduler/client/{client_id}",
        "notes_url": f"{base_url}/project-notes/add/{client_id}",
        "weather_url": "https://wttr.in",
        "business_hours_url": f"{base_url}/business-hours/{client_id}",
        "use_mock": USE_MOCK_API
    }

def get_auth_headers(authorization: str = None, client_id: str = None) -> Dict[str, str]:
    """
    Generate authentication headers for ProjectForce API
    Real API requires:
    - Authorization: Bearer TOKEN
    - Client_Id: 09PF05VD (note: capital C and I)
    """
    if client_id is None:
        client_id = DEFAULT_CLIENT_ID

    # Use provided authorization or fall back to environment variable
    if not authorization:
        authorization = f"Bearer {BEARER_TOKEN}" if BEARER_TOKEN else ""
    elif not authorization.startswith("Bearer "):
        authorization = f"Bearer {authorization}"

    return {
        "Authorization": authorization,  # Capital A
        "Client_Id": client_id,  # Capital C and I (as per real API)
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Origin": "https://projectsforce-validation.cx-portal.dev.projectsforce.com",
        "Referer": "https://projectsforce-validation.cx-portal.dev.projectsforce.com/",
        "User-Agent": "Mozilla/5.0 (compatible; ProjectForce-Agent/1.0)"
    }

# Mock mode notification
if USE_MOCK_API:
    print(f"⚠️ MOCK API MODE ENABLED (USE_MOCK_API=true)")
    print(f"   To enable real API calls, set USE_MOCK_API=false")
else:
    print(f"✅ REAL API MODE ENABLED (USE_MOCK_API=false)")
    print(f"   API Base URL: {CUSTOMER_SCHEDULER_BASE_API_URL}")
