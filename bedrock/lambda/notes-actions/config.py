"""
Configuration for Notes Actions Lambda
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
CUSTOMER_SCHEDULER_BASE_API_URL = os.getenv(
    "CUSTOMER_SCHEDULER_API_URL",
    "https://api.projectsforce.com"
)

# DynamoDB Configuration (for storing notes if no API available)
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "scheduling-agent-notes-dev")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

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
