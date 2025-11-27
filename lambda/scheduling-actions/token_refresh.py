"""
Token Refresh Module
Handles automatic token refresh when API calls fail with 401/403
Reads REFRESH_TOKEN flag from AWS Secrets Manager for modular control
"""
import json
import logging
import requests
import boto3
from typing import Dict, Optional, Tuple
import time

logger = logging.getLogger()

class TokenRefreshManager:
    """
    Manages automatic token refresh with configurable behavior

    Architecture:
    - Reads REFRESH_TOKEN flag from Secrets Manager
    - Calls ProjectForce regenerate-token API
    - Updates Secrets Manager with fresh token
    - Thread-safe with error handling
    """

    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize Token Refresh Manager

        Args:
            region: AWS region for Secrets Manager
        """
        self.region = region
        self.secrets_client = boto3.client('secretsmanager', region_name=region)
        self.secret_name = 'projectforce/api/credentials'

        # Regenerate token API endpoints by environment
        self.regenerate_api_urls = {
            'dev': 'https://auth.dev.projectsforce.com/regenerate-token',
            'staging': 'https://auth.staging.projectsforce.com/regenerate-token',
            'prod': 'https://auth.projectsforce.com/regenerate-token'
        }

    def is_refresh_enabled(self, credentials: Dict) -> bool:
        """
        Check if automatic token refresh is enabled

        Args:
            credentials: Credentials dict from Secrets Manager

        Returns:
            True if REFRESH_TOKEN is enabled, False otherwise
        """
        # Default to True if not specified (production-ready default)
        refresh_enabled = credentials.get('REFRESH_TOKEN', 'true')

        if isinstance(refresh_enabled, str):
            return refresh_enabled.lower() == 'true'
        elif isinstance(refresh_enabled, bool):
            return refresh_enabled

        # Default to True for safety
        return True

    def refresh_token(
        self,
        client_id: str,
        user_id: str,
        environment: str = 'dev'
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Refresh token by calling ProjectForce regenerate-token API

        Args:
            client_id: ProjectForce client ID
            user_id: ProjectForce user/customer ID
            environment: Environment (dev/staging/prod)

        Returns:
            Tuple of (success, new_token, error_message)
        """
        try:
            logger.info(f" Refreshing token for client={client_id}, user={user_id}, env={environment}")

            # Get regenerate API URL for environment
            regenerate_url = self.regenerate_api_urls.get(
                environment,
                self.regenerate_api_urls['dev']
            )

            # Call regenerate-token API
            # Reference: testing/ui/pf_proxy.py:832-845
            response = requests.post(
                regenerate_url,
                json={
                    "client_id": client_id,
                    "user_id": user_id,
                    "login_via_password": False,
                    "client_secret": "devappssecret",  # Environment-specific secret
                    "device_type": "web",
                    "grant_type": "authorization_code",
                    "secret_client_id": "devapps"
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            logger.info(f"Regenerate token API response status: {response.status_code}")

            if response.status_code == 200:
                token_data = response.json()
                new_token = token_data.get('access_token', token_data.get('token', ''))

                if not new_token or len(new_token) < 100:
                    error = "Regenerate API returned invalid token"
                    logger.error(f" {error}: {token_data}")
                    return False, None, error

                logger.info(f" Token refreshed successfully (length: {len(new_token)})")
                return True, new_token, None

            else:
                error = f"Regenerate API failed: {response.status_code}"
                logger.error(f" {error}")
                logger.error(f"Response: {response.text[:500]}")
                return False, None, error

        except Exception as e:
            error = f"Token refresh exception: {str(e)}"
            logger.error(f" {error}", exc_info=True)
            return False, None, error

    def update_secrets_manager(
        self,
        new_token: str,
        client_id: str,
        user_id: str,
        environment: str = 'dev'
    ) -> bool:
        """
        Update Secrets Manager with new token

        Args:
            new_token: Fresh bearer token
            client_id: ProjectForce client ID
            user_id: ProjectForce user/customer ID
            environment: Environment (dev/staging/prod)

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Get current credentials to preserve other fields
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            current_credentials = json.loads(response['SecretString'])

            # Update token and metadata
            current_credentials['bearer_token'] = new_token
            current_credentials['client_id'] = client_id
            current_credentials['user_id'] = str(user_id)
            current_credentials['updated_at'] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            current_credentials['updated_by'] = 'token_refresh.py (auto-refresh)'
            current_credentials['environment'] = environment

            # Preserve REFRESH_TOKEN flag (don't overwrite)
            if 'REFRESH_TOKEN' not in current_credentials:
                current_credentials['REFRESH_TOKEN'] = 'true'  # Default

            # Update Secrets Manager
            self.secrets_client.put_secret_value(
                SecretId=self.secret_name,
                SecretString=json.dumps(current_credentials)
            )

            logger.info(" Secrets Manager updated with fresh token")
            return True

        except Exception as e:
            logger.error(f" Failed to update Secrets Manager: {e}", exc_info=True)
            return False

    def auto_refresh_on_failure(
        self,
        client_id: str,
        user_id: str,
        environment: str = 'dev'
    ) -> Tuple[bool, Optional[str]]:
        """
        Automatically refresh token on API failure (401/403)

        This is the main entry point for auto-refresh functionality

        Args:
            client_id: ProjectForce client ID
            user_id: ProjectForce user/customer ID
            environment: Environment (dev/staging/prod)

        Returns:
            Tuple of (success, new_token)
        """
        try:
            # First check if refresh is enabled
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            credentials = json.loads(response['SecretString'])

            if not self.is_refresh_enabled(credentials):
                logger.warning(" REFRESH_TOKEN is disabled in Secrets Manager")
                return False, None

            logger.info(" REFRESH_TOKEN enabled - proceeding with auto-refresh")

            # Refresh token
            success, new_token, error = self.refresh_token(client_id, user_id, environment)

            if not success:
                logger.error(f" Token refresh failed: {error}")
                return False, None

            # Update Secrets Manager
            update_success = self.update_secrets_manager(
                new_token,
                client_id,
                user_id,
                environment
            )

            if not update_success:
                logger.error(" Failed to update Secrets Manager with new token")
                return False, None

            logger.info(" Auto-refresh completed successfully")
            return True, new_token

        except Exception as e:
            logger.error(f" Auto-refresh exception: {e}", exc_info=True)
            return False, None


# Singleton instance for reuse across Lambda invocations
_refresh_manager = None

def get_refresh_manager() -> TokenRefreshManager:
    """Get or create singleton TokenRefreshManager instance"""
    global _refresh_manager
    if _refresh_manager is None:
        _refresh_manager = TokenRefreshManager()
        logger.info("TokenRefreshManager initialized")
    return _refresh_manager
