"""
AWS Bedrock client for invoking Claude models.

Provides:
- Sync and async Claude invocation
- Streaming support (optional)
- Error handling and retries
- Token counting and cost tracking
"""

import json
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


# ============================================================================
# Bedrock Client Creation
# ============================================================================


def create_bedrock_client(region: str | None = None) -> Any:
    """
    Create AWS Bedrock Runtime client.

    Args:
        region: AWS region (defaults to settings.aws_region)

    Returns:
        boto3.client: Bedrock Runtime client
    """
    region = region or settings.aws_region

    logger.info("creating_bedrock_client", region=region)

    # Configure boto3 with retries
    config = Config(
        region_name=region,
        retries={
            "max_attempts": settings.llm_max_retries,
            "mode": "adaptive",
        },
        read_timeout=60,
        connect_timeout=10,
    )

    # Create client
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        return boto3.client(
            "bedrock-runtime",
            config=config,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
    else:
        # Use default credentials (IAM role, environment variables, etc.)
        return boto3.client("bedrock-runtime", config=config)


# Global Bedrock client
bedrock_client = create_bedrock_client()


# ============================================================================
# Claude Invocation
# ============================================================================


class ClaudeClient:
    """
    Client for invoking Claude models via AWS Bedrock.

    Provides methods for:
    - Text generation
    - Streaming responses
    - Structured output
    """

    def __init__(
        self,
        client: Any | None = None,
        model_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        """
        Initialize Claude client.

        Args:
            client: Bedrock client (defaults to global bedrock_client)
            model_id: Model ID (defaults to settings.bedrock_model_id)
            max_tokens: Max tokens (defaults to settings.max_tokens)
            temperature: Temperature (defaults to settings.llm_temperature)
        """
        self.client = client or bedrock_client
        self.model_id = model_id or settings.bedrock_model_id
        self.max_tokens = max_tokens or settings.max_tokens
        self.temperature = temperature or settings.llm_temperature

    @retry(
        retry=retry_if_exception_type((BotoCoreError, ClientError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def invoke(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        stop_sequences: list[str] | None = None,
    ) -> str:
        """
        Invoke Claude model with a prompt.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            max_tokens: Max tokens to generate
            temperature: Temperature (0.0-2.0)
            top_p: Top-p sampling
            stop_sequences: Stop sequences

        Returns:
            str: Generated text

        Raises:
            ClientError: If Bedrock API call fails
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        top_p = top_p or settings.llm_top_p

        # Build request body
        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        # Add system prompt if provided
        if system_prompt:
            body["system"] = system_prompt

        # Add stop sequences if provided
        if stop_sequences:
            body["stop_sequences"] = stop_sequences

        logger.debug(
            "invoking_claude",
            model_id=self.model_id,
            prompt_length=len(prompt),
            max_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            # Invoke model
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())

            # Extract text from response
            text = response_body["content"][0]["text"]

            # Log token usage
            input_tokens = response_body.get("usage", {}).get("input_tokens", 0)
            output_tokens = response_body.get("usage", {}).get("output_tokens", 0)

            logger.info(
                "claude_invocation_success",
                model_id=self.model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                output_length=len(text),
            )

            return text

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                "claude_invocation_failed",
                model_id=self.model_id,
                error_code=error_code,
                error_message=error_message,
            )

            raise

    async def invoke_with_json_output(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Invoke Claude and parse JSON output.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            **kwargs: Additional arguments for invoke()

        Returns:
            dict: Parsed JSON output

        Raises:
            json.JSONDecodeError: If output is not valid JSON
        """
        # Add instruction to output JSON
        json_prompt = f"{prompt}\n\nRespond with valid JSON only (no markdown, no explanation)."

        text = await self.invoke(
            prompt=json_prompt,
            system_prompt=system_prompt,
            stop_sequences=["\n\n"],  # Stop at double newline
            **kwargs,
        )

        # Clean up potential markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(
                "json_parsing_failed",
                text=text[:200],
                error=str(e),
            )
            raise


# Global Claude client
claude_client = ClaudeClient()


# ============================================================================
# Convenience Functions
# ============================================================================


async def invoke_claude(
    prompt: str,
    system_prompt: str | None = None,
    **kwargs: Any,
) -> str:
    """
    Convenience function to invoke Claude.

    Args:
        prompt: User prompt
        system_prompt: System prompt
        **kwargs: Additional arguments

    Returns:
        str: Generated text
    """
    return await claude_client.invoke(prompt, system_prompt, **kwargs)


async def invoke_claude_json(
    prompt: str,
    system_prompt: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Convenience function to invoke Claude with JSON output.

    Args:
        prompt: User prompt
        system_prompt: System prompt
        **kwargs: Additional arguments

    Returns:
        dict: Parsed JSON output
    """
    return await claude_client.invoke_with_json_output(prompt, system_prompt, **kwargs)


# ============================================================================
# Health Check
# ============================================================================


async def check_bedrock_health() -> bool:
    """
    Check Bedrock access and model availability.

    Returns:
        bool: True if Bedrock is accessible, False otherwise
    """
    try:
        # Try simple invocation
        response = await claude_client.invoke(
            prompt="Say 'OK' if you can read this.",
            max_tokens=10,
            temperature=0.0,
        )

        if response and len(response) > 0:
            logger.info("bedrock_health_check", status="healthy")
            return True
        else:
            logger.warning("bedrock_health_check", status="unhealthy", reason="empty_response")
            return False

    except Exception as e:
        logger.error("bedrock_health_check", status="unhealthy", error=str(e))
        return False
