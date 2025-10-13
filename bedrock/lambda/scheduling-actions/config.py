"""
Configuration for Scheduling Actions Lambda
Supports both mock and real API modes
"""
import os
from typing import Dict

# Environment variables
USE_MOCK_API = os.getenv("USE_MOCK_API", "true").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
CUSTOMER_SCHEDULER_BASE_API_URL = os.getenv("CUSTOMER_SCHEDULER_API_URL", "https://api.projectsforce.com")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# DynamoDB table for session management
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "scheduling-agent-sessions-dev")

# Feature flags (for gradual rollout)
ENABLE_REAL_CONFIRM = os.getenv("ENABLE_REAL_CONFIRM", "false").lower() == "true"
ENABLE_REAL_CANCEL = os.getenv("ENABLE_REAL_CANCEL", "false").lower() == "true"

def get_api_config(client_id: str, env: str = None) -> Dict[str, str]:
    """
    Generate API configuration based on environment and client
    """
    if env is None:
        env = ENVIRONMENT

    # Map environment to URL subdomain
    env_map = {
        "dev": "dev",
        "qa": "qa",
        "staging": "staging",
        "prod": "apps"
    }
    env_url = env_map.get(env, "dev")

    return {
        "dashboard_url": f"{CUSTOMER_SCHEDULER_BASE_API_URL}/dashboard/get/{client_id}",
        "scheduler_base_url": f"{CUSTOMER_SCHEDULER_BASE_API_URL}/scheduler/client/{client_id}",
        "notes_url": f"{CUSTOMER_SCHEDULER_BASE_API_URL}/project-notes/add/{client_id}",
        "use_mock": USE_MOCK_API
    }

def get_auth_headers(authorization: str, client_id: str) -> Dict[str, str]:
    """
    Generate authentication headers for PF360 API
    """
    return {
        "authorization": authorization,
        "client_id": client_id,
        "Content-Type": "application/json",
        "charset": "utf-8"
    }

# Mock mode notification
if USE_MOCK_API:
    print(f"⚠️ MOCK API MODE ENABLED (USE_MOCK_API=true)")
    print(f"   To enable real API calls, set USE_MOCK_API=false")
else:
    print(f"✅ REAL API MODE ENABLED (USE_MOCK_API=false)")
    print(f"   API Base URL: {CUSTOMER_SCHEDULER_BASE_API_URL}")
