"""
Configuration for Information Actions Lambda
Handles environment variables and API configuration
"""
import os
from typing import Dict

# ============================================================================
# Environment Variables
# ============================================================================

# Core Configuration
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

# Weather API (external)
WEATHER_API_URL = os.getenv("WEATHER_API_URL", "https://wttr.in")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================================================
# API Configuration Builder
# ============================================================================

def get_api_config(client_id: str = None, env: str = None) -> Dict[str, str]:
    """
    Generate API configuration based on environment and client

    Args:
        client_id: Client identifier (e.g., "09PF05VD")
        env: Environment override (default: uses ENVIRONMENT variable)

    Returns:
        Dict with API URLs and configuration
    """
    env = env or ENVIRONMENT
    if client_id is None:
        client_id = DEFAULT_CLIENT_ID

    base_url = API_BASE_URLS.get(env, API_BASE_URLS["dev"])

    return {
        "base_url": base_url,
        "dashboard_url": f"{base_url}/dashboard/get/{client_id}",
        "business_hours_url": f"{base_url}/business-hours/{client_id}",
        "weather_url": WEATHER_API_URL,
        "environment": env,
        "use_mock": USE_MOCK_API
    }

def get_auth_headers(authorization: str = None, client_id: str = None) -> Dict[str, str]:
    """
    Generate authentication headers for ProjectForce API calls
    Real API requires:
    - Authorization: Bearer TOKEN
    - Client_Id: 09PF05VD (note: capital C and I)

    Args:
        authorization: Bearer token or full authorization header
        client_id: Client identifier

    Returns:
        Dict with Authorization and Client_Id headers
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
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
