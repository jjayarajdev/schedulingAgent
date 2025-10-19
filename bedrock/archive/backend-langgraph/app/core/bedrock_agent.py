"""
AWS Bedrock Agent client for invoking multi-agent system.

Provides:
- Agent invocation with session management
- Streaming responses support
- Error handling and retries
- Session state management
"""

import json
from typing import Any, AsyncIterator
from datetime import datetime

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
# Bedrock Agent Client Creation
# ============================================================================


def create_bedrock_agent_client(region: str | None = None) -> Any:
    """
    Create AWS Bedrock Agent Runtime client.

    Args:
        region: AWS region (defaults to settings.aws_region)

    Returns:
        boto3.client: Bedrock Agent Runtime client
    """
    region = region or settings.aws_region

    logger.info("creating_bedrock_agent_client", region=region)

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
            "bedrock-agent-runtime",
            config=config,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
    else:
        # Use default credentials (IAM role, environment variables, etc.)
        return boto3.client("bedrock-agent-runtime", config=config)


# Global Bedrock Agent client
bedrock_agent_client = create_bedrock_agent_client()


# ============================================================================
# Bedrock Agent Invocation
# ============================================================================


class BedrockAgentClient:
    """
    Client for invoking Bedrock Agents (multi-agent system).

    Provides methods for:
    - Agent invocation with session management
    - Streaming responses
    - Session state tracking
    """

    def __init__(
        self,
        client: Any | None = None,
        agent_id: str | None = None,
        agent_alias_id: str | None = None,
    ):
        """
        Initialize Bedrock Agent client.

        Args:
            client: Bedrock Agent Runtime client (defaults to global)
            agent_id: Agent ID (defaults to settings.bedrock_agent_id)
            agent_alias_id: Agent alias ID (defaults to settings.bedrock_agent_alias_id)
        """
        self.client = client or bedrock_agent_client
        self.agent_id = agent_id or settings.bedrock_agent_id
        self.agent_alias_id = agent_alias_id or settings.bedrock_agent_alias_id

        if not self.agent_id:
            raise ValueError("bedrock_agent_id must be set in settings or passed to constructor")
        if not self.agent_alias_id:
            raise ValueError("bedrock_agent_alias_id must be set in settings or passed to constructor")

    @retry(
        retry=retry_if_exception_type((BotoCoreError, ClientError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def invoke(
        self,
        input_text: str,
        session_id: str,
        enable_trace: bool = False,
        end_session: bool = False,
        session_state: dict[str, Any] | None = None,
        customer_id: str | None = None,
        client_id: str | None = None,
        available_clients: list[dict[str, Any]] | None = None,
        customer_type: str = "B2C",
    ) -> dict[str, Any]:
        """
        Invoke Bedrock Agent with input text and B2C/B2B context.

        Args:
            input_text: User input text
            session_id: Session ID for conversation continuity
            enable_trace: Enable trace for debugging (default False)
            end_session: End the session after this invocation (default False)
            session_state: Session state attributes (optional, will be merged with B2B context)
            customer_id: Customer ID from authentication (B2C and B2B)
            client_id: Client ID for B2B default location (optional)
            available_clients: List of available client locations for B2B (optional)
            customer_type: Customer type: B2C or B2B (default B2C)

        Returns:
            dict: Agent response with text, session_id, trace, etc.

        Raises:
            ClientError: If Bedrock Agent API call fails
        """
        logger.debug(
            "invoking_bedrock_agent",
            agent_id=self.agent_id,
            session_id=session_id,
            input_length=len(input_text),
            enable_trace=enable_trace,
            customer_id=customer_id,
            client_id=client_id,
            customer_type=customer_type,
        )

        # Build session attributes with B2C/B2B context
        session_attributes = session_state.get("sessionAttributes", {}) if session_state else {}

        # Add customer context
        if customer_id:
            session_attributes["customer_id"] = customer_id
            session_attributes["user_authenticated"] = "true"

        if client_id:
            session_attributes["client_id"] = client_id
            session_attributes["default_client_id"] = client_id
        else:
            session_attributes["client_id"] = ""

        session_attributes["customer_type"] = customer_type

        # For B2B, add available clients information
        if customer_type == "B2B" and available_clients:
            session_attributes["total_clients"] = str(len(available_clients))
            session_attributes["available_clients"] = json.dumps(available_clients)

            # Extract client names for easy reference
            client_names = [c.get("client_name", "") for c in available_clients]
            session_attributes["client_names"] = ", ".join(client_names)

        # Build request parameters
        request_params = {
            "agentId": self.agent_id,
            "agentAliasId": self.agent_alias_id,
            "sessionId": session_id,
            "inputText": input_text,
            "enableTrace": enable_trace,
            "endSession": end_session,
        }

        # Add session state with attributes
        request_params["sessionState"] = {
            "sessionAttributes": session_attributes
        }

        # Merge any additional session state
        if session_state:
            if "promptSessionAttributes" in session_state:
                request_params["sessionState"]["promptSessionAttributes"] = session_state["promptSessionAttributes"]

        try:
            start_time = datetime.utcnow()

            # Invoke agent
            response = self.client.invoke_agent(**request_params)

            # Parse response stream
            result = self._parse_agent_response(response)

            # Calculate latency
            end_time = datetime.utcnow()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)

            result["latency_ms"] = latency_ms
            result["session_id"] = session_id
            result["agent_id"] = self.agent_id

            logger.info(
                "bedrock_agent_invocation_success",
                agent_id=self.agent_id,
                session_id=session_id,
                customer_type=customer_type,
                output_length=len(result.get("output", "")),
                latency_ms=latency_ms,
                trace_enabled=enable_trace,
            )

            return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                "bedrock_agent_invocation_failed",
                agent_id=self.agent_id,
                session_id=session_id,
                error_code=error_code,
                error_message=error_message,
            )

            raise

    def _parse_agent_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """
        Parse agent response from event stream.

        Args:
            response: Response from invoke_agent API

        Returns:
            dict: Parsed response with output text, trace, etc.
        """
        output_text = ""
        trace_data = []
        completion_reason = None

        # Get event stream
        event_stream = response.get("completion", [])

        try:
            # Process event stream
            for event in event_stream:
                # Extract chunk text
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        chunk_text = chunk["bytes"].decode("utf-8")
                        output_text += chunk_text

                # Extract trace information
                if "trace" in event:
                    trace = event["trace"]
                    trace_data.append(trace)

                # Extract return control
                if "returnControl" in event:
                    # Handle action group invocations
                    return_control = event["returnControl"]
                    logger.debug("agent_return_control", data=return_control)

                # Extract completion
                if "completion" in event and "completionReason" in event:
                    completion_reason = event.get("completionReason")

        except Exception as e:
            logger.error("error_parsing_agent_response", error=str(e))
            # Continue with partial output
            pass

        return {
            "output": output_text.strip(),
            "trace": trace_data if trace_data else None,
            "completion_reason": completion_reason,
        }

    async def invoke_streaming(
        self,
        input_text: str,
        session_id: str,
        enable_trace: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Invoke agent with streaming response.

        Args:
            input_text: User input text
            session_id: Session ID
            enable_trace: Enable trace

        Yields:
            dict: Streaming events (chunk, trace, etc.)
        """
        logger.debug(
            "invoking_bedrock_agent_streaming",
            agent_id=self.agent_id,
            session_id=session_id,
        )

        try:
            # Invoke agent
            response = self.client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=input_text,
                enableTrace=enable_trace,
            )

            # Stream events
            event_stream = response.get("completion", [])

            for event in event_stream:
                # Yield chunk events
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        chunk_text = chunk["bytes"].decode("utf-8")
                        yield {
                            "type": "chunk",
                            "text": chunk_text,
                        }

                # Yield trace events
                if "trace" in event and enable_trace:
                    yield {
                        "type": "trace",
                        "trace": event["trace"],
                    }

        except ClientError as e:
            logger.error(
                "bedrock_agent_streaming_failed",
                agent_id=self.agent_id,
                session_id=session_id,
                error=str(e),
            )
            raise


# Global Bedrock Agent client
bedrock_agent = BedrockAgentClient()


# ============================================================================
# Convenience Functions
# ============================================================================


async def invoke_agent(
    input_text: str,
    session_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Convenience function to invoke Bedrock Agent.

    Args:
        input_text: User input
        session_id: Session ID
        **kwargs: Additional arguments

    Returns:
        dict: Agent response
    """
    return await bedrock_agent.invoke(input_text, session_id, **kwargs)


async def invoke_agent_streaming(
    input_text: str,
    session_id: str,
    **kwargs: Any,
) -> AsyncIterator[dict[str, Any]]:
    """
    Convenience function to invoke agent with streaming.

    Args:
        input_text: User input
        session_id: Session ID
        **kwargs: Additional arguments

    Yields:
        dict: Streaming events
    """
    async for event in bedrock_agent.invoke_streaming(input_text, session_id, **kwargs):
        yield event


# ============================================================================
# Health Check
# ============================================================================


async def check_bedrock_agent_health() -> bool:
    """
    Check Bedrock Agent access and availability.

    Returns:
        bool: True if agent is accessible, False otherwise
    """
    try:
        # Try simple invocation
        test_session_id = f"health-check-{datetime.utcnow().timestamp()}"

        response = await bedrock_agent.invoke(
            input_text="Hello",
            session_id=test_session_id,
            end_session=True,
        )

        if response and response.get("output"):
            logger.info("bedrock_agent_health_check", status="healthy")
            return True
        else:
            logger.warning(
                "bedrock_agent_health_check",
                status="unhealthy",
                reason="empty_response",
            )
            return False

    except Exception as e:
        logger.error("bedrock_agent_health_check", status="unhealthy", error=str(e))
        return False
