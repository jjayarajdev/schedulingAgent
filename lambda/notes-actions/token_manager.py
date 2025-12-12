"""
Dynamic Token Manager for ProjectForce API
Handles token retrieval, caching, and automatic refresh using AWS Secrets Manager
"""
import os
import json
import time
import logging
import requests
import boto3
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Environment-specific API URLs
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
API_BASE_URLS = {
    "dev": "https://api-cx-portal.dev.projectsforce.com",
    "staging": "https://api-cx-portal.staging.projectsforce.com",
    "prod": "https://api-cx-portal.projectsforce.com"
}

def get_api_base_url():
    """Get the API base URL for the current environment"""
    return API_BASE_URLS.get(ENVIRONMENT, API_BASE_URLS["dev"])

class TokenManager:
    """
    Manages Bearer tokens for ProjectForce API with automatic refresh and caching.

    Features:
    - Fetches tokens from AWS Secrets Manager
    - Caches tokens in memory to reduce API calls
    - Automatically refreshes expired tokens
    - Falls back to authentication if refresh fails
    """

    def __init__(
        self,
        secret_name: str = None,
        region: str = None,
        cache_ttl: int = 3600  # 1 hour default cache
    ):
        """
        Initialize Token Manager

        Args:
            secret_name: AWS Secrets Manager secret name (default: from env)
            region: AWS region (default: from env)
            cache_ttl: Token cache time-to-live in seconds
        """
        self.secret_name = secret_name or os.getenv('TOKEN_SECRET_NAME', 'projectforce/api/credentials')
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.cache_ttl = cache_ttl

        # In-memory cache
        self._cached_token = None
        self._cache_expiry = None

        # AWS clients
        self.secrets_client = boto3.client('secretsmanager', region_name=self.region)

        logger.info(f"TokenManager initialized with secret: {self.secret_name}")

    def get_token(self, force_refresh: bool = False) -> str:
        """
        Get valid Bearer token (from cache or fresh)

        Args:
            force_refresh: Force token refresh even if cached token is valid

        Returns:
            Valid Bearer token string

        Raises:
            Exception: If token cannot be retrieved
        """
        # Check cache first
        if not force_refresh and self._is_cache_valid():
            logger.info("Returning cached token")
            return self._cached_token

        logger.info("Fetching fresh token...")

        try:
            # Get credentials from Secrets Manager
            credentials = self._get_credentials_from_secrets()

            # Check if secret contains a cached bearer token
            if credentials.get('bearer_token'):
                logger.info("Using bearer token from Secrets Manager")
                return self._cache_token(credentials['bearer_token'])

            # Try to use refresh token if available
            if credentials.get('refresh_token'):
                try:
                    token = self._refresh_token(credentials['refresh_token'])
                    logger.info("Token refreshed successfully")
                    return self._cache_token(token)
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}. Attempting full authentication...")

            # Fall back to full authentication
            token = self._authenticate(credentials)
            logger.info("New token obtained via authentication")
            return self._cache_token(token)

        except Exception as e:
            logger.error(f"Failed to get token: {e}")
            # If we have a cached token, return it even if expired (better than nothing)
            if self._cached_token:
                logger.warning("Returning expired cached token as fallback")
                return self._cached_token
            raise

    def _get_credentials_from_secrets(self) -> Dict:
        """
        Retrieve credentials from AWS Secrets Manager

        Returns:
            Dictionary with email, password, and optionally refresh_token
        """
        try:
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            secret = json.loads(response['SecretString'])

            required_keys = ['email', 'encrypted_password']
            if not all(key in secret for key in required_keys):
                raise ValueError(f"Secret must contain: {required_keys}")

            return secret

        except self.secrets_client.exceptions.ResourceNotFoundException:
            raise Exception(f"Secret {self.secret_name} not found in Secrets Manager")
        except Exception as e:
            raise Exception(f"Failed to retrieve credentials: {e}")

    def _authenticate(self, credentials: Dict) -> str:
        """
        Authenticate with ProjectForce API to get new token

        Args:
            credentials: Dictionary with email and encrypted_password

        Returns:
            New Bearer token string
        """
        auth_url = os.getenv(
            'AUTH_API_URL',
            f'{get_api_base_url()}/authentication/login'
        )
        identifier = os.getenv('AUTH_IDENTIFIER', 'projectforce-validation')

        payload = {
            'email': credentials['email'],
            'password': credentials['encrypted_password'],
            'device_type': 1
        }

        try:
            response = requests.post(
                f"{auth_url}?identifier={identifier}",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            token = data.get('accesstoken')
            if not token:
                raise ValueError("No access token in response")

            # Store refresh token for future use
            refresh_token = data.get('refrestoken')
            if refresh_token:
                self._update_refresh_token(refresh_token)

            return token

        except requests.exceptions.RequestException as e:
            raise Exception(f"Authentication failed: {e}")

    def _refresh_token(self, refresh_token: str) -> str:
        """
        Refresh token using refresh token

        Args:
            refresh_token: Refresh token from previous authentication

        Returns:
            New Bearer token string
        """
        refresh_url = os.getenv(
            'AUTH_API_URL',
            f'{get_api_base_url()}/authentication/refresh'
        )

        payload = {'refresh_token': refresh_token}

        try:
            response = requests.post(
                refresh_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            token = data.get('accesstoken') or data.get('access_token')
            if not token:
                raise ValueError("No access token in refresh response")

            return token

        except requests.exceptions.RequestException as e:
            raise Exception(f"Token refresh failed: {e}")

    def _cache_token(self, token: str) -> str:
        """
        Cache token in memory

        Args:
            token: Bearer token to cache

        Returns:
            The same token (for chaining)
        """
        self._cached_token = token
        self._cache_expiry = time.time() + self.cache_ttl
        logger.info(f"Token cached until {datetime.fromtimestamp(self._cache_expiry)}")
        return token

    def _is_cache_valid(self) -> bool:
        """Check if cached token is still valid"""
        if not self._cached_token or not self._cache_expiry:
            return False
        return time.time() < self._cache_expiry

    def _update_refresh_token(self, refresh_token: str) -> None:
        """
        Update refresh token in Secrets Manager for future use

        Args:
            refresh_token: New refresh token to store
        """
        try:
            # Get current secret
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            secret = json.loads(response['SecretString'])

            # Update refresh token
            secret['refresh_token'] = refresh_token
            secret['refresh_token_updated_at'] = datetime.utcnow().isoformat()

            # Save back to Secrets Manager
            self.secrets_client.put_secret_value(
                SecretId=self.secret_name,
                SecretString=json.dumps(secret)
            )

            logger.info("Refresh token updated in Secrets Manager")

        except Exception as e:
            logger.warning(f"Failed to update refresh token: {e}")

    def invalidate_cache(self) -> None:
        """Invalidate cached token (force refresh on next get_token call)"""
        self._cached_token = None
        self._cache_expiry = None
        logger.info("Token cache invalidated")


# Global token manager instance (reused across Lambda invocations)
_token_manager_instance = None

def get_token_manager() -> TokenManager:
    """
    Get singleton TokenManager instance

    Returns:
        Shared TokenManager instance
    """
    global _token_manager_instance

    if _token_manager_instance is None:
        _token_manager_instance = TokenManager()

    return _token_manager_instance


def get_bearer_token(force_refresh: bool = False) -> str:
    """
    Convenience function to get Bearer token

    Args:
        force_refresh: Force token refresh

    Returns:
        Valid Bearer token string
    """
    manager = get_token_manager()
    return manager.get_token(force_refresh=force_refresh)
