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
USE_MOCK_API = os.getenv("USE_MOCK_API", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
RESOURCE_PREFIX = os.getenv("RESOURCE_PREFIX", "pf")

# Real ProjectForce API endpoints (CX Portal API)
API_BASE_URLS = {
    "dev": "https://api-cx-portal.dev.projectsforce.com",
    "staging": "https://api-cx-portal.staging.projectsforce.com",
    "prod": "https://api-cx-portal.apps.projectsforce.com"
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

# DynamoDB tables (with dynamic defaults)
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", f"{RESOURCE_PREFIX}-sessions-{ENVIRONMENT}")
DYNAMODB_NOTES_TABLE = os.getenv("DYNAMODB_NOTES_TABLE", f"{RESOURCE_PREFIX}-notes-{ENVIRONMENT}")

# Feature flags (for gradual rollout)
# Changed defaults to "true" to enable real API calls for cancel/reschedule
ENABLE_REAL_CONFIRM = os.getenv("ENABLE_REAL_CONFIRM", "true").lower() == "true"
ENABLE_REAL_CANCEL = os.getenv("ENABLE_REAL_CANCEL", "true").lower() == "true"

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
        "dashboard_url": f"{base_url}/dashboard/get",  # Portal API format: /dashboard/get/{client_id}/{customer_id}
        "scheduler_business_hours_url": f"{base_url}/scheduler/client/{client_id}/business-hours",  # Matches HAR file
        "scheduler_base_url": base_url,  # Base URL for scheduler endpoints
        "notes_url": f"{base_url}/project-notes/add/{client_id}",
        "weather_url": "https://wttr.in",
        "use_mock": USE_MOCK_API
    }

def get_auth_headers(authorization: str = None, client_id: str = None) -> Dict[str, str]:
    """
    Generate authentication headers for ProjectForce API
    Uses provided authorization token OR reads from AWS Secrets Manager

    Architecture:
    - If valid authorization provided, use it (from session attributes)
    - Otherwise, use TokenManager to read from Secrets Manager

    Args:
        authorization: Optional Bearer token (if provided, skips Secrets Manager)
        client_id: ProjectForce client ID

    Real API requires:
    - Authorization: Bearer TOKEN
    - client_id: 09PF05VD (lowercase to match portal headers)
    """
    if client_id is None:
        client_id = DEFAULT_CLIENT_ID

    # Use provided authorization if valid, otherwise fetch from Secrets Manager
    auth_header = ""

    if authorization and len(authorization) > 100:
        # Valid token provided - use it directly
        if not authorization.startswith("Bearer "):
            auth_header = f"Bearer {authorization}"
        else:
            auth_header = authorization
        logging.info(f" Using provided authorization token")
    elif TOKEN_MANAGER_AVAILABLE:
        # No valid token provided - fetch from Secrets Manager
        try:
            token = get_bearer_token()
            auth_header = f"Bearer {token}"
            logging.info(f" Using token from AWS Secrets Manager (single source of truth)")
        except Exception as e:
            logging.error(f" Failed to get token from Secrets Manager: {e}")
            # NO fallback - if Secrets Manager fails, request should fail
            raise Exception(f"Cannot retrieve token from AWS Secrets Manager: {e}")
    else:
        # TokenManager not available - this is a critical error
        error_msg = "TokenManager not available - cannot proceed without Secrets Manager access"
        logging.error(f" {error_msg}")
        raise Exception(error_msg)

    return {
        "Authorization": auth_header,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "client_id": client_id  # Lowercase to match real portal headers
    }

# Mock mode notification
if USE_MOCK_API:
    print(f" MOCK API MODE ENABLED (USE_MOCK_API=true)")
    print(f"   To enable real API calls, set USE_MOCK_API=false")
else:
    print(f" REAL API MODE ENABLED (USE_MOCK_API=false)")
    print(f"   API Base URL: {CUSTOMER_SCHEDULER_BASE_API_URL}")
