"""
Configuration for Lex Fulfillment Lambda

Centralizes environment variable loading and configuration management.
"""

import os
from typing import Optional


class Config:
    """Application configuration"""

    # AWS Resources
    DYNAMODB_TABLE: str = os.environ.get('DYNAMODB_TABLE', 'pf-sessions-dev')
    SCHEDULING_LAMBDA: str = os.environ.get('SCHEDULING_LAMBDA', 'pf-scheduling-actions')
    INFORMATION_LAMBDA: str = os.environ.get('INFORMATION_LAMBDA', 'pf-information-actions')
    VOICE_BRIDGE_LAMBDA: str = os.environ.get('VOICE_BRIDGE_LAMBDA', 'pf-voice-bedrock-bridge-dev')
    CUSTOMER_LOOKUP_LAMBDA: str = os.environ.get('CUSTOMER_LOOKUP_LAMBDA', 'pf-customer-lookup-dev')

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
