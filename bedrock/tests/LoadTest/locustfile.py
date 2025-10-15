"""
Main Locust Load Test File for AWS Bedrock Multi-Agent System
Tests supervisor agent routing, collaborator responses, and multi-turn conversations

Usage:
    # Basic test with web UI
    locust -f locustfile.py

    # Headless mode with 50 users for 5 minutes
    locust -f locustfile.py --headless -u 50 -r 5 -t 5m --html report.html

    # Distributed mode (master)
    locust -f locustfile.py --master

    # Distributed mode (worker)
    locust -f locustfile.py --worker --master-host=<master-ip>
"""

import random
import time
import uuid
from typing import Any, Dict

from locust import HttpUser, TaskSet, between, events, task

from config import (
    CHITCHAT_MESSAGES,
    INFORMATION_MESSAGES,
    MULTI_TURN_CONVERSATION,
    NOTES_MESSAGES,
    SCHEDULING_MESSAGES,
    SUPERVISOR_AGENT_ID,
    SUPERVISOR_ALIAS_ID,
)
from utils import generate_session_id, invoke_bedrock_agent, validate_agent_routing


# ============================================================================
# Task Sets - Define User Behaviors
# ============================================================================


class AgentInteractionTasks(TaskSet):
    """Task set for general agent interactions"""

    def on_start(self):
        """Initialize user session"""
        self.session_id = generate_session_id(self.user.user_id)
        self.conversation_turns = 0
        self.response_times = []

    @task(3)
    def send_chitchat(self):
        """Test chitchat routing (30% of requests)"""
        message = random.choice(CHITCHAT_MESSAGES)

        start_time = time.time()
        request_name = "bedrock_agent:chitchat"

        try:
            result = invoke_bedrock_agent(
                agent_id=SUPERVISOR_AGENT_ID,
                agent_alias_id=SUPERVISOR_ALIAS_ID,
                session_id=self.session_id,
                input_text=message,
            )

            elapsed_ms = result["elapsed_ms"]
            self.response_times.append(elapsed_ms)

            if result["success"]:
                # Validate routing
                validation = validate_agent_routing(
                    result["response"], expected_collaborator="chitchat"
                )

                # Report success
                events.request.fire(
                    request_type="bedrock_agent",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=len(result["response"]),
                    exception=None,
                    context={
                        "routing_correct": validation["routing_correct"],
                        "detected_collaborator": validation["detected_collaborator"],
                    },
                )
            else:
                # Report failure
                events.request.fire(
                    request_type="bedrock_agent",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=0,
                    exception=Exception(result["error"]),
                    context={},
                )

            self.conversation_turns += 1

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="bedrock_agent",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )

    @task(5)
    def send_scheduling_request(self):
        """Test scheduling routing (50% of requests)"""
        message = random.choice(SCHEDULING_MESSAGES)

        start_time = time.time()
        request_name = "bedrock_agent:scheduling"

        try:
            result = invoke_bedrock_agent(
                agent_id=SUPERVISOR_AGENT_ID,
                agent_alias_id=SUPERVISOR_ALIAS_ID,
                session_id=self.session_id,
                input_text=message,
            )

            elapsed_ms = result["elapsed_ms"]
            self.response_times.append(elapsed_ms)

            if result["success"]:
                validation = validate_agent_routing(
                    result["response"], expected_collaborator="scheduling"
                )

                events.request.fire(
                    request_type="bedrock_agent",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=len(result["response"]),
                    exception=None,
                    context={
                        "routing_correct": validation["routing_correct"],
                        "detected_collaborator": validation["detected_collaborator"],
                    },
                )
            else:
                events.request.fire(
                    request_type="bedrock_agent",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=0,
                    exception=Exception(result["error"]),
                    context={},
                )

            self.conversation_turns += 1

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="bedrock_agent",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )

    @task(1)
    def send_information_query(self):
        """Test information routing (10% of requests)"""
        message = random.choice(INFORMATION_MESSAGES)

        start_time = time.time()
        request_name = "bedrock_agent:information"

        try:
            result = invoke_bedrock_agent(
                agent_id=SUPERVISOR_AGENT_ID,
                agent_alias_id=SUPERVISOR_ALIAS_ID,
                session_id=self.session_id,
                input_text=message,
            )

            elapsed_ms = result["elapsed_ms"]
            self.response_times.append(elapsed_ms)

            if result["success"]:
                validation = validate_agent_routing(
                    result["response"], expected_collaborator="information"
                )

                events.request.fire(
                    request_type="bedrock_agent",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=len(result["response"]),
                    exception=None,
                    context={
                        "routing_correct": validation["routing_correct"],
                        "detected_collaborator": validation["detected_collaborator"],
                    },
                )
            else:
                events.request.fire(
                    request_type="bedrock_agent",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=0,
                    exception=Exception(result["error"]),
                    context={},
                )

            self.conversation_turns += 1

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="bedrock_agent",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )

    @task(1)
    def send_notes_request(self):
        """Test notes routing (10% of requests)"""
        message = random.choice(NOTES_MESSAGES)

        start_time = time.time()
        request_name = "bedrock_agent:notes"

        try:
            result = invoke_bedrock_agent(
                agent_id=SUPERVISOR_AGENT_ID,
                agent_alias_id=SUPERVISOR_ALIAS_ID,
                session_id=self.session_id,
                input_text=message,
            )

            elapsed_ms = result["elapsed_ms"]
            self.response_times.append(elapsed_ms)

            if result["success"]:
                validation = validate_agent_routing(
                    result["response"], expected_collaborator="notes"
                )

                events.request.fire(
                    request_type="bedrock_agent",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=len(result["response"]),
                    exception=None,
                    context={
                        "routing_correct": validation["routing_correct"],
                        "detected_collaborator": validation["detected_collaborator"],
                    },
                )
            else:
                events.request.fire(
                    request_type="bedrock_agent",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=0,
                    exception=Exception(result["error"]),
                    context={},
                )

            self.conversation_turns += 1

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="bedrock_agent",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )


class MultiTurnConversationTasks(TaskSet):
    """Task set for multi-turn conversations"""

    def on_start(self):
        """Initialize user session"""
        self.session_id = generate_session_id(self.user.user_id)
        self.response_times = []

    @task(1)
    def complete_conversation(self):
        """Execute a complete multi-turn conversation"""
        request_name = "bedrock_agent:multi_turn_conversation"

        start_time = time.time()
        successful_turns = 0
        total_turns = len(MULTI_TURN_CONVERSATION)

        try:
            for i, (message, expected_collaborator) in enumerate(
                MULTI_TURN_CONVERSATION
            ):
                result = invoke_bedrock_agent(
                    agent_id=SUPERVISOR_AGENT_ID,
                    agent_alias_id=SUPERVISOR_ALIAS_ID,
                    session_id=self.session_id,
                    input_text=message,
                )

                if result["success"]:
                    validation = validate_agent_routing(
                        result["response"], expected_collaborator=expected_collaborator
                    )
                    if validation["routing_correct"]:
                        successful_turns += 1

                # Small delay between turns (simulate realistic user)
                if i < total_turns - 1:
                    time.sleep(random.uniform(0.5, 2.0))

            elapsed_ms = (time.time() - start_time) * 1000

            # Report success if all turns completed
            if successful_turns == total_turns:
                events.request.fire(
                    request_type="bedrock_agent",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=total_turns,
                    exception=None,
                    context={"successful_turns": successful_turns},
                )
            else:
                events.request.fire(
                    request_type="bedrock_agent",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=successful_turns,
                    exception=Exception(
                        f"Only {successful_turns}/{total_turns} turns successful"
                    ),
                    context={"successful_turns": successful_turns},
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="bedrock_agent",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )


# ============================================================================
# User Classes - Define User Behaviors
# ============================================================================


class BedrockAgentUser(HttpUser):
    """
    Simulates a customer interacting with Bedrock Agent

    This user randomly chooses between single requests and multi-turn conversations
    """

    # Wait 1-5 seconds between requests
    wait_time = between(1, 5)

    # Assign tasks with weights
    tasks = {AgentInteractionTasks: 9, MultiTurnConversationTasks: 1}

    # Unique user ID for session management
    user_id = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        BedrockAgentUser.user_id += 1
        self.user_id = BedrockAgentUser.user_id


class SchedulingFocusedUser(HttpUser):
    """
    User that primarily focuses on scheduling tasks (80%)
    Simulates heavy scheduling load
    """

    wait_time = between(2, 6)

    tasks = {AgentInteractionTasks: 1}

    user_id = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        SchedulingFocusedUser.user_id += 1
        self.user_id = SchedulingFocusedUser.user_id

    @task(8)
    def scheduling_heavy(self):
        """80% scheduling requests"""
        message = random.choice(SCHEDULING_MESSAGES)
        session_id = generate_session_id(self.user_id)

        start_time = time.time()

        try:
            result = invoke_bedrock_agent(
                agent_id=SUPERVISOR_AGENT_ID,
                agent_alias_id=SUPERVISOR_ALIAS_ID,
                session_id=session_id,
                input_text=message,
            )

            elapsed_ms = result["elapsed_ms"]

            if result["success"]:
                events.request.fire(
                    request_type="bedrock_agent",
                    name="bedrock_agent:scheduling_heavy",
                    response_time=elapsed_ms,
                    response_length=len(result["response"]),
                    exception=None,
                    context={},
                )
            else:
                events.request.fire(
                    request_type="bedrock_agent",
                    name="bedrock_agent:scheduling_heavy",
                    response_time=elapsed_ms,
                    response_length=0,
                    exception=Exception(result["error"]),
                    context={},
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="bedrock_agent",
                name="bedrock_agent:scheduling_heavy",
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )


# ============================================================================
# Event Handlers - Custom Metrics and Reporting
# ============================================================================


# Track custom metrics
test_stats = {"routing_correct": 0, "routing_incorrect": 0, "total_requests": 0}


@events.request.add_listener
def on_request(
    request_type, name, response_time, response_length, exception, context, **kwargs
):
    """Track routing accuracy"""
    if request_type == "bedrock_agent":
        test_stats["total_requests"] += 1

        if context and "routing_correct" in context:
            if context["routing_correct"]:
                test_stats["routing_correct"] += 1
            else:
                test_stats["routing_incorrect"] += 1


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary statistics when test stops"""
    print("\n" + "=" * 80)
    print("BEDROCK AGENT LOAD TEST SUMMARY")
    print("=" * 80)

    print(f"\nTotal Requests: {test_stats['total_requests']}")
    print(f"Routing Correct: {test_stats['routing_correct']}")
    print(f"Routing Incorrect: {test_stats['routing_incorrect']}")

    if test_stats["total_requests"] > 0:
        accuracy = (
            test_stats["routing_correct"] / test_stats["total_requests"]
        ) * 100
        print(f"Routing Accuracy: {accuracy:.2f}%")

    print("\n" + "=" * 80)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import os

    os.system(
        "locust -f locustfile.py --host=https://bedrock-agent.us-east-1.amazonaws.com"
    )
