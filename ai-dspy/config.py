"""
DSPy Configuration for ProjectForce Orchestrator
"""
import os
import dspy
from dotenv import load_dotenv

load_dotenv()

def configure_dspy(model: str = "claude-sonnet-4-20250514"):
    """Configure DSPy with Claude as the LLM backend."""

    # Using Anthropic with correct model ID format
    lm = dspy.LM(
        model=f"anthropic/{model}",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=1000
    )

    dspy.configure(lm=lm)
    return lm


def configure_dspy_bedrock(model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"):
    """Configure DSPy with AWS Bedrock Claude."""
    import boto3

    lm = dspy.LM(
        model=f"bedrock/{model_id}",
        aws_region_name=os.getenv("AWS_REGION", "us-east-1")
    )

    dspy.configure(lm=lm)
    return lm
