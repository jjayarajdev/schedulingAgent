"""
Utility functions for load testing
Helper functions for AWS interactions, metrics collection, and reporting
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, Generator, Optional

import boto3
from botocore.exceptions import ClientError


# ============================================================================
# AWS Bedrock Helpers
# ============================================================================


def invoke_bedrock_agent(
    agent_id: str,
    agent_alias_id: str,
    session_id: str,
    input_text: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    Invoke Bedrock Agent and return response with timing

    Args:
        agent_id: Bedrock agent ID
        agent_alias_id: Agent alias ID
        session_id: Session ID for conversation
        input_text: User input text
        region: AWS region

    Returns:
        Dict with response text and metadata
    """
    client = boto3.client("bedrock-agent-runtime", region_name=region)

    start_time = time.time()

    try:
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=input_text,
        )

        # Process event stream
        agent_response = extract_agent_response(response["completion"])

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "success": True,
            "response": agent_response,
            "elapsed_ms": elapsed_ms,
            "error": None,
        }

    except ClientError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))

        return {
            "success": False,
            "response": None,
            "elapsed_ms": elapsed_ms,
            "error": f"{error_code}: {error_msg}",
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "success": False,
            "response": None,
            "elapsed_ms": elapsed_ms,
            "error": str(e),
        }


def extract_agent_response(event_stream: Generator) -> str:
    """
    Extract text response from Bedrock agent event stream

    Args:
        event_stream: Event stream from invoke_agent

    Returns:
        Concatenated response text
    """
    agent_response = ""

    for event in event_stream:
        if "chunk" in event:
            chunk = event["chunk"]
            if "bytes" in chunk:
                agent_response += chunk["bytes"].decode("utf-8")

    return agent_response


# ============================================================================
# AWS Lambda Helpers
# ============================================================================


def invoke_lambda(
    function_name: str, payload: Dict[str, Any], region: str = "us-east-1"
) -> Dict[str, Any]:
    """
    Invoke AWS Lambda function and return response with timing

    Args:
        function_name: Lambda function name
        payload: Request payload
        region: AWS region

    Returns:
        Dict with response and metadata
    """
    client = boto3.client("lambda", region_name=region)

    start_time = time.time()

    try:
        response = client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",  # Synchronous
            Payload=json.dumps(payload),
        )

        elapsed_ms = (time.time() - start_time) * 1000

        # Parse response
        response_payload = json.loads(response["Payload"].read())

        # Check for function errors
        if "FunctionError" in response:
            return {
                "success": False,
                "response": response_payload,
                "elapsed_ms": elapsed_ms,
                "error": f"FunctionError: {response.get('FunctionError')}",
                "status_code": response.get("StatusCode", 500),
            }

        return {
            "success": True,
            "response": response_payload,
            "elapsed_ms": elapsed_ms,
            "error": None,
            "status_code": response.get("StatusCode", 200),
        }

    except ClientError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))

        return {
            "success": False,
            "response": None,
            "elapsed_ms": elapsed_ms,
            "error": f"{error_code}: {error_msg}",
            "status_code": 500,
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "success": False,
            "response": None,
            "elapsed_ms": elapsed_ms,
            "error": str(e),
            "status_code": 500,
        }


# ============================================================================
# CloudWatch Metrics Helpers
# ============================================================================


def get_cloudwatch_metrics(
    namespace: str,
    metric_name: str,
    dimensions: Dict[str, str],
    start_time: datetime,
    end_time: datetime,
    period: int = 60,
    statistic: str = "Average",
    region: str = "us-east-1",
) -> Optional[float]:
    """
    Fetch CloudWatch metric value

    Args:
        namespace: CloudWatch namespace
        metric_name: Metric name
        dimensions: Metric dimensions
        start_time: Start datetime
        end_time: End datetime
        period: Period in seconds
        statistic: Statistic type
        region: AWS region

    Returns:
        Metric value or None
    """
    client = boto3.client("cloudwatch", region_name=region)

    try:
        dimension_list = [{"Name": k, "Value": v} for k, v in dimensions.items()]

        response = client.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimension_list,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[statistic],
        )

        datapoints = response.get("Datapoints", [])

        if datapoints:
            # Sort by timestamp and get latest
            latest = sorted(datapoints, key=lambda x: x["Timestamp"])[-1]
            return latest.get(statistic)

        return None

    except Exception as e:
        print(f"Error fetching CloudWatch metric: {e}")
        return None


# ============================================================================
# Session Management
# ============================================================================


def generate_session_id(user_id: int, timestamp: Optional[float] = None) -> str:
    """
    Generate unique session ID for load test user

    Args:
        user_id: Locust user ID
        timestamp: Optional timestamp (uses current if not provided)

    Returns:
        Session ID string
    """
    if timestamp is None:
        timestamp = time.time()

    return f"loadtest-user{user_id}-{int(timestamp)}"


# ============================================================================
# Response Validation
# ============================================================================


def validate_agent_routing(
    response: str, expected_collaborator: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate that agent response indicates correct routing

    Args:
        response: Agent response text
        expected_collaborator: Expected collaborator name (optional)

    Returns:
        Dict with validation results
    """
    response_lower = response.lower()

    # Detect which collaborator likely responded
    collaborator_indicators = {
        "scheduling": ["appointment", "schedule", "book", "meeting", "calendar"],
        "information": ["hours", "working", "status", "weather", "information"],
        "notes": ["note", "added", "preference", "list"],
        "chitchat": ["hello", "hi", "how are", "thanks", "goodbye"],
    }

    detected_collaborator = None
    max_matches = 0

    for collaborator, keywords in collaborator_indicators.items():
        matches = sum(1 for keyword in keywords if keyword in response_lower)
        if matches > max_matches:
            max_matches = matches
            detected_collaborator = collaborator

    routing_correct = (
        detected_collaborator == expected_collaborator
        if expected_collaborator
        else True
    )

    return {
        "routing_correct": routing_correct,
        "detected_collaborator": detected_collaborator,
        "expected_collaborator": expected_collaborator,
        "confidence": max_matches,
    }


# ============================================================================
# Performance Metrics
# ============================================================================


def calculate_percentile(values: list, percentile: float) -> float:
    """
    Calculate percentile from list of values

    Args:
        values: List of numeric values
        percentile: Percentile (0.0 to 1.0)

    Returns:
        Percentile value
    """
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile)
    return sorted_values[min(index, len(sorted_values) - 1)]


def analyze_response_times(response_times: list) -> Dict[str, float]:
    """
    Analyze response time distribution

    Args:
        response_times: List of response times in ms

    Returns:
        Dict with percentile analysis
    """
    if not response_times:
        return {
            "p50": 0.0,
            "p75": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
        }

    return {
        "p50": calculate_percentile(response_times, 0.50),
        "p75": calculate_percentile(response_times, 0.75),
        "p90": calculate_percentile(response_times, 0.90),
        "p95": calculate_percentile(response_times, 0.95),
        "p99": calculate_percentile(response_times, 0.99),
        "avg": sum(response_times) / len(response_times),
        "min": min(response_times),
        "max": max(response_times),
    }


# ============================================================================
# Cost Calculation
# ============================================================================


def estimate_test_cost(
    num_invocations: int, avg_input_tokens: int = 200, avg_output_tokens: int = 500
) -> Dict[str, float]:
    """
    Estimate cost of load test for Bedrock

    Claude Sonnet 4.5 pricing (as of Oct 2025):
    - Input: $3 per 1M tokens
    - Output: $15 per 1M tokens

    Args:
        num_invocations: Number of agent invocations
        avg_input_tokens: Average input tokens per invocation
        avg_output_tokens: Average output tokens per invocation

    Returns:
        Dict with cost breakdown
    """
    INPUT_COST_PER_1M = 3.0
    OUTPUT_COST_PER_1M = 15.0

    total_input_tokens = num_invocations * avg_input_tokens
    total_output_tokens = num_invocations * avg_output_tokens

    input_cost = (total_input_tokens / 1_000_000) * INPUT_COST_PER_1M
    output_cost = (total_output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
    total_cost = input_cost + output_cost

    return {
        "num_invocations": num_invocations,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "input_cost_usd": round(input_cost, 4),
        "output_cost_usd": round(output_cost, 4),
        "total_cost_usd": round(total_cost, 4),
    }
