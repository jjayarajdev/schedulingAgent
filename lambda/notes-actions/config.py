"""
Configuration for Notes Actions Lambda
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
RESOURCE_PREFIX = os.getenv("RESOURCE_PREFIX", "pf-syn")

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

# DynamoDB Configuration (for storing notes if no API available)
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", f"{RESOURCE_PREFIX}-project-notes-{ENVIRONMENT}")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def get_bearer_token_with_fallback() -> str:
    """
    Get Bearer token using TokenManager or fallback to environment variable

    Returns:
        Bearer token string
    """
    if TOKEN_MANAGER_AVAILABLE:
        try:
            token = get_bearer_token()
            logging.info("Using dynamic token from TokenManager")
            return token
        except Exception as e:
            logging.warning(f"Failed to get token from TokenManager: {e}")

    # Fall back to static token
    if BEARER_TOKEN:
        logging.info("Using static BEARER_TOKEN from environment")
        return BEARER_TOKEN

    raise ValueError("No bearer token available")

# ============================================================================
# API Configuration Builder
# ============================================================================

def get_api_config(client_id: str, env: str = None) -> Dict[str, str]:
    """
    Generate API configuration based on environment and client

    Args:
        client_id: Client identifier (e.g., "09PF05VD")
        env: Environment override (default: uses ENVIRONMENT variable)

    Returns:
        Dict with API URLs and configuration
    """
    env = env or ENVIRONMENT

    return {
        "add_note_url": f"{CUSTOMER_SCHEDULER_BASE_API_URL}/project-notes/add/{client_id}",
        "list_notes_url": f"{CUSTOMER_SCHEDULER_BASE_API_URL}/project-notes/list/{client_id}",
        "dynamodb_table": DYNAMODB_TABLE,
        "environment": env,
        "use_mock": USE_MOCK_API
    }

def get_auth_headers(authorization: str, client_id: str) -> Dict[str, str]:
    """
    Generate authentication headers for PF360 API calls

    Args:
        authorization: Bearer token or full authorization header
        client_id: Client identifier

    Returns:
        Dict with authorization and client_id headers
    """
    # Ensure authorization has Bearer prefix
    if authorization and not authorization.startswith("Bearer "):
        authorization = f"Bearer {authorization}"

    return {
        "authorization": authorization,
        "client_id": client_id,
        "Content-Type": "application/json"
    }
