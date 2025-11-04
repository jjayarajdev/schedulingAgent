"""
Configuration for Scheduling Actions Lambda
Supports both mock and real API modes
"""
import os
import logging
from typing import Dict

# Import TokenManager for dynamic token management
try:
    from token_manager import get_bearer_token
    TOKEN_MANAGER_AVAILABLE = True
except ImportError:
    TOKEN_MANAGER_AVAILABLE = False
    logging.warning("TokenManager not available, falling back to static token")

# Environment variables
USE_MOCK_API = os.getenv("USE_MOCK_API", "true").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Real ProjectForce API endpoints (CX Portal API)
API_BASE_URLS = {
    "dev": "https://api-cx-portal.dev.projectsforce.com",
    "staging": "https://api-cx-portal.staging.projectsforce.com",
    "prod": "https://api-cx-portal.projectsforce.com"
}
CUSTOMER_SCHEDULER_BASE_API_URL = os.getenv(
    "CUSTOMER_SCHEDULER_API_URL",
    API_BASE_URLS.get(ENVIRONMENT, API_BASE_URLS["dev"])
)

# Authentication - Static token fallback (deprecated)
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
        "dashboard_url": f"{base_url}/dashboard/get",  # OLD Portal API format: /dashboard/get/{client_id}/{customer_id}
        "scheduler_url": f"{base_url}/system/client-details",
        "scheduler_base_url": base_url,  # Base URL for scheduler endpoints
        "notes_url": f"{base_url}/project-notes/add/{client_id}",
        "weather_url": "https://wttr.in",
        "use_mock": USE_MOCK_API
    }

def get_auth_headers(authorization: str = None, client_id: str = None) -> Dict[str, str]:
    """
    Generate authentication headers for ProjectForce API
    Uses dynamic token management via TokenManager when available,
    falls back to static BEARER_TOKEN from environment variables.

    Real API requires:
    - Authorization: Bearer TOKEN
    - Client_Id: 09PF05VD (note: capital C and I)
    """
    if client_id is None:
        client_id = DEFAULT_CLIENT_ID

    # Use provided authorization or get token dynamically
    if not authorization:
        # Try to use TokenManager for dynamic token retrieval
        if TOKEN_MANAGER_AVAILABLE:
            try:
                token = get_bearer_token()
                authorization = f"Bearer {token}"
                logging.info("Using dynamic token from TokenManager")
            except Exception as e:
                logging.warning(f"Failed to get token from TokenManager: {e}")
                # Fall back to static token
                authorization = f"Bearer {BEARER_TOKEN}" if BEARER_TOKEN else ""
                if BEARER_TOKEN:
                    logging.info("Falling back to static BEARER_TOKEN")
        else:
            # Fall back to static token if TokenManager not available
            authorization = f"Bearer {BEARER_TOKEN}" if BEARER_TOKEN else ""
    elif not authorization.startswith("Bearer "):
        authorization = f"Bearer {authorization}"

    return {
        "Authorization": authorization,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Client_Id": client_id
    }

# Mock mode notification
if USE_MOCK_API:
    print(f"⚠️ MOCK API MODE ENABLED (USE_MOCK_API=true)")
    print(f"   To enable real API calls, set USE_MOCK_API=false")
else:
    print(f"✅ REAL API MODE ENABLED (USE_MOCK_API=false)")
    print(f"   API Base URL: {CUSTOMER_SCHEDULER_BASE_API_URL}")
