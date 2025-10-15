"""
Configuration for Load Tests
Centralized configuration for all load testing scenarios
"""

import os
from typing import Dict, List, Tuple

# ============================================================================
# AWS Configuration
# ============================================================================

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = "618048437522"

# ============================================================================
# Bedrock Agent Configuration
# ============================================================================

# Agent IDs
SUPERVISOR_AGENT_ID = "5VTIWONUMO"
SUPERVISOR_ALIAS_ID = "HH2U7EZXMW"

SCHEDULING_AGENT_ID = "IX24FSMTQH"
SCHEDULING_ALIAS_ID = "TYJRF3CJ7F"

INFORMATION_AGENT_ID = "C9ANXRIO8Y"
INFORMATION_ALIAS_ID = "YVNFXEKPWO"

NOTES_AGENT_ID = "G5BVBYEPUM"
NOTES_ALIAS_ID = "F9QQNLZUW8"

CHITCHAT_AGENT_ID = "BIUW1ARHGL"
CHITCHAT_ALIAS_ID = "THIPMPJCPI"

COORDINATOR_AGENT_ID = "QHUR9JP4GT"

# ============================================================================
# Lambda Function Configuration
# ============================================================================

LAMBDA_FUNCTIONS = {
    "bulk_ops": "scheduling-agent-bulk-ops-dev",
    "scheduling": "scheduling-actions-dev",  # If deployed
    "information": "information-actions-dev",  # If deployed
    "notes": "notes-actions-dev",  # If deployed
}

# ============================================================================
# Test Message Templates
# ============================================================================

CHITCHAT_MESSAGES: List[str] = [
    "Hello!",
    "Hi there!",
    "How are you today?",
    "Good morning!",
    "Hey! How's it going?",
    "Thanks for your help!",
    "That's great, thank you!",
    "Goodbye!",
]

SCHEDULING_MESSAGES: List[str] = [
    "I want to schedule an appointment",
    "I need to book a meeting",
    "Can I schedule something?",
    "I'd like to make an appointment",
    "Help me reschedule my appointment",
    "I need to cancel my appointment",
    "When can I schedule an appointment?",
    "Show me my appointments",
]

INFORMATION_MESSAGES: List[str] = [
    "What are your working hours?",
    "When are you open?",
    "What time do you close?",
    "Tell me about business hours",
    "What's the status of my project?",
    "Can you give me information about my order?",
    "What's the weather like?",
]

NOTES_MESSAGES: List[str] = [
    "Add a note that I prefer morning appointments",
    "Can you add a note?",
    "I want to leave a note",
    "Please note that I need parking",
    "List my notes",
    "Show me all notes",
]

MULTI_TURN_CONVERSATION: List[Tuple[str, str]] = [
    ("Hello!", "chitchat"),
    ("I want to schedule an appointment", "scheduling"),
    ("What are your working hours?", "information"),
    ("Add a note about parking", "notes"),
    ("Thanks!", "chitchat"),
]

# ============================================================================
# Lambda Test Payloads
# ============================================================================

BULK_OPS_PAYLOADS: Dict[str, Dict] = {
    "optimize_route": {
        "body": {
            "operation": "optimize_route",
            "project_ids": ["12345", "12346", "12347"],
            "date": "2025-10-20",
        }
    },
    "bulk_assign": {
        "body": {
            "operation": "bulk_assign_teams",
            "project_ids": ["12345", "12346"],
            "team_id": "team_001",
        }
    },
    "validate_projects": {
        "body": {
            "operation": "validate_projects",
            "project_ids": ["12345", "12346", "12347", "12348"],
        }
    },
    "detect_conflicts": {
        "body": {
            "operation": "detect_conflicts",
            "date": "2025-10-20",
        }
    },
}

SCHEDULING_PAYLOADS: Dict[str, Dict] = {
    "list_projects": {
        "apiPath": "/list-projects",
        "httpMethod": "POST",
        "parameters": [
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"},
        ],
    },
    "get_available_dates": {
        "apiPath": "/get-available-dates",
        "httpMethod": "POST",
        "parameters": [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"},
        ],
    },
}

# ============================================================================
# Performance Targets
# ============================================================================

PERFORMANCE_TARGETS = {
    "bedrock_agent": {
        "p50_latency_ms": 2000,  # 2 seconds
        "p95_latency_ms": 5000,  # 5 seconds
        "p99_latency_ms": 10000,  # 10 seconds
        "error_rate_pct": 1.0,  # 1%
        "throughput_rps": 100,  # requests per second
    },
    "lambda": {
        "p50_latency_ms": 1000,  # 1 second
        "p95_latency_ms": 3000,  # 3 seconds
        "p99_latency_ms": 5000,  # 5 seconds
        "error_rate_pct": 0.5,  # 0.5%
        "throughput_rps": 500,  # requests per second
    },
}

# ============================================================================
# Test Duration Configuration
# ============================================================================

TEST_DURATIONS = {
    "smoke": 60,  # 1 minute
    "quick": 300,  # 5 minutes
    "standard": 600,  # 10 minutes
    "extended": 1800,  # 30 minutes
    "stress": 3600,  # 1 hour
}

# ============================================================================
# User Load Profiles
# ============================================================================

LOAD_PROFILES = {
    "smoke": {"users": 1, "spawn_rate": 1},
    "light": {"users": 10, "spawn_rate": 1},
    "medium": {"users": 50, "spawn_rate": 5},
    "heavy": {"users": 100, "spawn_rate": 10},
    "stress": {"users": 500, "spawn_rate": 50},
    "spike": {"users": 1000, "spawn_rate": 1000},  # Instant spike
}

# ============================================================================
# Monitoring Configuration
# ============================================================================

CLOUDWATCH_METRICS = {
    "bedrock": {
        "namespace": "AWS/Bedrock",
        "metrics": ["Invocations", "Latency", "ClientErrors", "ServerErrors"],
    },
    "lambda": {
        "namespace": "AWS/Lambda",
        "metrics": [
            "Invocations",
            "Duration",
            "Errors",
            "Throttles",
            "ConcurrentExecutions",
        ],
    },
}

# ============================================================================
# Reporting Configuration
# ============================================================================

REPORT_CONFIG = {
    "html_report": True,
    "csv_stats": True,
    "percentiles": [0.50, 0.75, 0.90, 0.95, 0.99],
    "output_dir": "./load_test_results",
}
