"""
Configuration for Information Actions Lambda
Handles environment variables and API configuration
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

# ============================================================================
# Environment Variables
# ============================================================================

# Core Configuration
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
        "dashboard_url": f"{base_url}/cx-scheduled/projects",
        "business_hours_url": f"{base_url}/system/client-details",
        "weather_url": WEATHER_API_URL,
        "environment": env,
        "use_mock": USE_MOCK_API
    }

def get_auth_headers(authorization: str = None, client_id: str = None) -> Dict[str, str]:
    """
    Generate authentication headers for ProjectForce API calls
    Uses dynamic token management via TokenManager when available,
    falls back to static BEARER_TOKEN from environment variables.

    Real API requires:
    - Authorization: Bearer TOKEN

    Args:
        authorization: Bearer token or full authorization header (optional override)
        client_id: Client identifier (not used in headers currently)

    Returns:
        Dict with Authorization header
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
        "Content-Type": "application/json",
        "Client_Id": client_id
    }
