"""
Orchestrator Lambda Configuration
Loads configuration from environment variables
"""
import os
import json
import logging

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


class Config:
    """Configuration for Orchestrator Lambda"""

    def __init__(self):
        # AWS Configuration
        self.region = os.environ.get('AWS_REGION', 'us-east-1')

        # Redis/ElastiCache Configuration
        self.redis_endpoint = os.environ.get('REDIS_ENDPOINT', '')
        self.redis_port = int(os.environ.get('REDIS_PORT', '6379'))
        self.redis_ssl = os.environ.get('REDIS_SSL', 'true').lower() == 'true'

        # Session Configuration
        self.session_timeout = int(os.environ.get('SESSION_TIMEOUT', '3600'))  # 1 hour
        self.max_history_messages = int(os.environ.get('MAX_HISTORY_MESSAGES', '20'))
        self.session_cleanup_threshold = int(os.environ.get('SESSION_CLEANUP_THRESHOLD', '1800'))  # 30 min

        # Agent Configuration
        self.supervisor_agent_id = os.environ.get('SUPERVISOR_AGENT_ID', '')
        self.supervisor_alias_id = os.environ.get('SUPERVISOR_ALIAS_ID', 'TSTALIASID')

        # Routing Configuration
        self.use_supervisor = os.environ.get('USE_SUPERVISOR', 'false').lower() == 'true'
        self.allow_direct_lambda = os.environ.get('ALLOW_DIRECT_LAMBDA', 'true').lower() == 'true'
        self.routing_method = os.environ.get('ROUTING_METHOD', 'hybrid')  # hybrid, supervisor, direct

        # Multi-Agent Orchestration Configuration
        self.enable_multi_agent_orchestration = os.environ.get('ENABLE_MULTI_AGENT_ORCHESTRATION', 'true').lower() == 'true'
        self.max_parallel_agents = int(os.environ.get('MAX_PARALLEL_AGENTS', '3'))

        # Classification Configuration
        self.classifier_model = os.environ.get('CLASSIFIER_MODEL', 'us.anthropic.claude-3-5-sonnet-20240620-v1:0')
        self.classification_cache_ttl = int(os.environ.get('CLASSIFICATION_CACHE_TTL', '300'))  # 5 min

        # Lambda Function Names (for direct invocation)
        self.scheduling_lambda = os.environ.get('SCHEDULING_LAMBDA_NAME', 'pf-scheduling-actions')
        self.information_lambda = os.environ.get('INFORMATION_LAMBDA_NAME', 'pf-information-actions')

        # Agent IDs (for direct routing without supervisor)
        self.agents = self._load_agent_config()

        # Performance Configuration
        self.enable_classification_cache = os.environ.get('ENABLE_CLASSIFICATION_CACHE', 'true').lower() == 'true'
        self.enable_connection_pooling = os.environ.get('ENABLE_CONNECTION_POOLING', 'true').lower() == 'true'

    def _load_agent_config(self):
        """Load agent configuration from environment or default structure"""
        agent_config_json = os.environ.get('AGENT_CONFIG_JSON', '')

        if agent_config_json:
            try:
                return json.loads(agent_config_json)
            except json.JSONDecodeError:
                logger.warning("Failed to parse AGENT_CONFIG_JSON, using defaults")

        # Default agent configuration
        return {
            'scheduling': {
                'agent_id': os.environ.get('SCHEDULING_AGENT_ID', 'MTZGUHW3FK'),
                'alias_id': os.environ.get('SCHEDULING_ALIAS_ID', 'TSTALIASID')
            },
            'information': {
                'agent_id': os.environ.get('INFORMATION_AGENT_ID', 'HQPYL61L5B'),
                'alias_id': os.environ.get('INFORMATION_ALIAS_ID', 'TSTALIASID')
            },
            'chitchat': {
                'agent_id': os.environ.get('CHITCHAT_AGENT_ID', 'SPE68WI5TY'),
                'alias_id': os.environ.get('CHITCHAT_ALIAS_ID', 'TSTALIASID')
            }
        }

    def validate(self):
        """Validate required configuration"""
        errors = []

        # Redis validation removed - now using DynamoDB for session management
        # if not self.redis_endpoint:
        #     errors.append("REDIS_ENDPOINT is required")

        if not self.supervisor_agent_id:
            errors.append("SUPERVISOR_AGENT_ID is required")

        if self.allow_direct_lambda:
            if not self.scheduling_lambda:
                errors.append("SCHEDULING_LAMBDA_NAME is required for direct calls")

        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

        logger.info(f"Configuration loaded: region={self.region}, routing={self.routing_method}")

        return True


# Singleton instance
_config = None

def get_config() -> Config:
    """Get or create configuration singleton"""
    global _config
    if _config is None:
        _config = Config()
        _config.validate()
    return _config
