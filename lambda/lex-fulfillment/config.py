"""
Configuration for Lex Fulfillment Lambda

Centralizes environment variable loading and configuration management.
"""

import os
from typing import Optional

# Dynamic resource naming
RESOURCE_PREFIX = os.environ.get('RESOURCE_PREFIX', 'pf')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')


class Config:
    """Application configuration"""

    # AWS Resources (with dynamic defaults)
    DYNAMODB_TABLE: str = os.environ.get('DYNAMODB_TABLE', f'{RESOURCE_PREFIX}-sessions-{ENVIRONMENT}')
    SCHEDULING_LAMBDA: str = os.environ.get('SCHEDULING_LAMBDA', f'{RESOURCE_PREFIX}-scheduling-actions-{ENVIRONMENT}')
    INFORMATION_LAMBDA: str = os.environ.get('INFORMATION_LAMBDA', f'{RESOURCE_PREFIX}-information-actions-{ENVIRONMENT}')
    VOICE_BRIDGE_LAMBDA: str = os.environ.get('VOICE_BRIDGE_LAMBDA', f'{RESOURCE_PREFIX}-voice-bedrock-bridge-{ENVIRONMENT}')
    CUSTOMER_LOOKUP_LAMBDA: str = os.environ.get('CUSTOMER_LOOKUP_LAMBDA', f'{RESOURCE_PREFIX}-customer-lookup-{ENVIRONMENT}')

    # Voice Configuration
    MAX_VOICE_RESPONSE_LENGTH: int = int(os.environ.get('MAX_VOICE_RESPONSE_LENGTH', '500'))
    ENABLE_SSML: bool = os.environ.get('ENABLE_SSML', 'false').lower() == 'true'

    # Logging
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    ENABLE_DETAILED_LOGGING: bool = os.environ.get('ENABLE_DETAILED_LOGGING', 'false').lower() == 'true'

    # Session
    SESSION_TTL_SECONDS: int = int(os.environ.get('SESSION_TTL_SECONDS', '3600'))

    # Features
    ENABLE_CUSTOMER_LOOKUP: bool = os.environ.get('ENABLE_CUSTOMER_LOOKUP', 'true').lower() == 'true'

    @classmethod
    def validate(cls) -> None:
        """Validate configuration at startup"""
        required_vars = [
            'DYNAMODB_TABLE',
            'SCHEDULING_LAMBDA',
            'VOICE_BRIDGE_LAMBDA'
        ]

        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


# Validate configuration on import
Config.validate()
