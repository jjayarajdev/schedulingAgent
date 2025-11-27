"""
Multi-Agent Intent Classification
Enhanced classifier that identifies queries requiring multiple agents
Uses Claude Haiku for fast, cost-effective classification
"""
import json
import logging
from typing import Dict, List, Optional
import boto3
from botocore.config import Config as BotoConfig

from config import get_config

logger = logging.getLogger()

# Boto3 client singleton
_bedrock_runtime_client = None


def get_bedrock_client():
    """Get or create Bedrock runtime client"""
    global _bedrock_runtime_client
    if _bedrock_runtime_client is None:
        config = get_config()
        boto_config = BotoConfig(
            region_name=config.region,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        _bedrock_runtime_client = boto3.client('bedrock-runtime', config=boto_config)
        logger.info("Bedrock runtime client created for multi-agent classifier")
    return _bedrock_runtime_client


def classify_multi_agent_intent(message: str, conversation_history: Optional[List[Dict]] = None) -> Dict:
    """
    Enhanced multi-agent classification using Claude Haiku

    Identifies:
    - Which agents are needed (scheduling, information, chitchat)
    - Orchestration type (sequential, parallel, conditional)
    - Dependencies between agent calls
    - Whether direct Lambda optimization is possible

    Args:
        message: Current user message
        conversation_history: Previous conversation for context

    Returns:
        Dictionary with:
        - intent: Primary intent (scheduling/information/chitchat/multi_agent)
        - agents_needed: List of agent names ['scheduling', 'information']
        - orchestration_type: 'single', 'parallel', 'sequential', 'conditional'
        - can_optimize: Boolean - whether fast path (direct Lambda) is possible
        - reasoning: Explanation of classification
        - dependencies: Optional dict describing agent dependencies

    Examples:
        >>> classify_multi_agent_intent("show my projects")
        {
            'intent': 'scheduling',
            'agents_needed': ['scheduling'],
            'orchestration_type': 'single',
            'can_optimize': True,
            'reasoning': 'Simple data retrieval'
        }

        >>> classify_multi_agent_intent("show my projects and the weather")
        {
            'intent': 'multi_agent',
            'agents_needed': ['scheduling', 'information'],
            'orchestration_type': 'parallel',
            'can_optimize': False,
            'reasoning': 'Multiple independent queries'
        }

        >>> classify_multi_agent_intent("check weather next week and if good, schedule project 123")
        {
            'intent': 'multi_agent',
            'agents_needed': ['information', 'scheduling'],
            'orchestration_type': 'sequential',
            'can_optimize': False,
            'reasoning': 'Conditional action based on weather',
            'dependencies': {'scheduling': ['information']}
        }
    """
    config = get_config()

    # Build conversation context
    context_str = ""
    if conversation_history and len(conversation_history) > 0:
        context_str = "\n\nRecent conversation:\n"
        for msg in conversation_history[-3:]:
            role = msg.get('role', 'user')
            content = msg.get('content', '')[:200]  # Truncate for efficiency
            context_str += f"{role}: {content}\n"

    prompt = f"""You are an intelligent routing classifier for a multi-agent system.

Analyze the user's message and determine which agents are needed and how to orchestrate them.

**Available Agents:**
1. **Scheduling Agent**: Project management, appointments, scheduling, dates, times
2. **Information Agent**: Weather queries, external data
3. **Chitchat Agent**: Greetings, casual conversation

**Your Task:**
Classify the message into one of these orchestration patterns:

1. **SINGLE AGENT** (orchestration_type: "single")
   - Query involves only ONE domain
   - Examples:
     * "show my projects"  scheduling agent only
     * "what's the weather"  information agent only
     * "hello"  chitchat agent only
   - can_optimize: TRUE if it's a simple query (show/list/get)
   - can_optimize: FALSE if it's an action (schedule/book/create)

2. **PARALLEL MULTI-AGENT** (orchestration_type: "parallel")
   - Query involves MULTIPLE INDEPENDENT domains
   - Agents can execute simultaneously
   - Examples:
     * "show my projects and the weather"  scheduling + information (parallel)
     * "tell me about projects and greet me"  scheduling + chitchat (parallel)
   - can_optimize: FALSE (always requires agents for coordination)

3. **SEQUENTIAL MULTI-AGENT** (orchestration_type: "sequential")
   - Query requires agents to execute IN ORDER
   - One agent's output feeds into the next
   - Examples:
     * "check weather next week and if good, schedule project"  information THEN scheduling
     * "show project details then check weather there"  scheduling THEN information
   - can_optimize: FALSE (complex orchestration)
   - Must include 'dependencies' field showing order

4. **CONDITIONAL MULTI-AGENT** (orchestration_type: "conditional")
   - Execution of one agent depends on another's result
   - Examples:
     * "if weather is good, show my outdoor projects"  information THEN conditionally scheduling
     * "schedule only if dates are available"  check availability THEN conditionally schedule
   - can_optimize: FALSE
   - Must include 'dependencies' field with conditions
{context_str}
Current message: "{message}"

**Response Format** (JSON only):
{{
  "intent": "scheduling | information | chitchat | multi_agent",
  "agents_needed": ["agent_name", ...],
  "orchestration_type": "single | parallel | sequential | conditional",
  "can_optimize": true | false,
  "reasoning": "Brief explanation",
  "dependencies": {{ }} or null
}}

**Rules:**
- If only ONE agent needed  orchestration_type = "single"
- If MULTIPLE agents with NO dependencies  orchestration_type = "parallel"
- If agents must run IN ORDER  orchestration_type = "sequential"
- If execution is CONDITIONAL  orchestration_type = "conditional"
- can_optimize = true ONLY for single-agent simple queries (show/list/get)
- can_optimize = false for actions (schedule/book) and all multi-agent queries

**Example Responses:**

Message: "show my projects"
{{
  "intent": "scheduling",
  "agents_needed": ["scheduling"],
  "orchestration_type": "single",
  "can_optimize": true,
  "reasoning": "Simple query - single agent, data retrieval",
  "dependencies": null
}}

Message: "show my projects and weather"
{{
  "intent": "multi_agent",
  "agents_needed": ["scheduling", "information"],
  "orchestration_type": "parallel",
  "can_optimize": false,
  "reasoning": "Two independent queries - can run simultaneously",
  "dependencies": null
}}

Message: "check weather next week then schedule project 123 if sunny"
{{
  "intent": "multi_agent",
  "agents_needed": ["information", "scheduling"],
  "orchestration_type": "conditional",
  "can_optimize": false,
  "reasoning": "Weather check must complete first, scheduling conditional on result",
  "dependencies": {{"scheduling": ["information"]}}
}}

Message: "schedule project 123"
{{
  "intent": "scheduling",
  "agents_needed": ["scheduling"],
  "orchestration_type": "single",
  "can_optimize": false,
  "reasoning": "Single agent but action (not query) - needs confirmation",
  "dependencies": null
}}

Analyze: "{message}"
Respond ONLY with valid JSON."""

    try:
        bedrock_runtime = get_bedrock_client()

        # Use Haiku for fast, cheap classification
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 400,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        classification_text = response_body['content'][0]['text'].strip()

        logger.info(f" Multi-agent classification: {classification_text}")

        # Parse JSON
        classification = json.loads(classification_text)

        # Validate and add defaults
        if 'intent' not in classification:
            classification['intent'] = 'chitchat'
        if 'agents_needed' not in classification:
            classification['agents_needed'] = ['chitchat']
        if 'orchestration_type' not in classification:
            classification['orchestration_type'] = 'single'
        if 'can_optimize' not in classification:
            classification['can_optimize'] = False
        if 'dependencies' not in classification:
            classification['dependencies'] = None

        logger.info(f" Multi-agent classification: {classification['orchestration_type']} with "
                   f"{len(classification['agents_needed'])} agent(s): {classification['agents_needed']}")

        return classification

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse multi-agent classification JSON: {e}")
        # Fallback to single chitchat
        return {
            'intent': 'chitchat',
            'agents_needed': ['chitchat'],
            'orchestration_type': 'single',
            'can_optimize': False,
            'reasoning': 'Classification failed, fallback to chitchat',
            'dependencies': None
        }
    except Exception as e:
        logger.error(f"Multi-agent classification error: {e}", exc_info=True)
        return {
            'intent': 'chitchat',
            'agents_needed': ['chitchat'],
            'orchestration_type': 'single',
            'can_optimize': False,
            'reasoning': f'Error: {str(e)}',
            'dependencies': None
        }
