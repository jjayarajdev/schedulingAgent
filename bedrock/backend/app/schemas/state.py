"""
Agent state schema for LangGraph.

Defines the shared state structure that flows through all agents
in the multi-agent system.
"""

from typing import Any, TypedDict

from typing_extensions import Annotated


def add_messages(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Reducer function to append messages to conversation history.

    Args:
        left: Existing messages
        right: New messages to add

    Returns:
        list: Combined messages
    """
    return left + right


class AgentState(TypedDict):
    """
    Shared state across all agents in the LangGraph.

    This state is passed between agents and updated by each agent.
    Using TypedDict for better type checking and IDE support.

    State flow:
    1. Supervisor receives initial state
    2. Intent Classifier adds intent/confidence
    3. Clarifier adds clarifying_question (if needed)
    4. Tool Executor adds tool_results
    5. Response Generator creates final agent_response
    """

    # ============================================================================
    # Input (from ChatRequest)
    # ============================================================================

    session_id: str
    customer_id: str
    client_id: str
    client_name: str
    user_message: str

    # ============================================================================
    # Intent Classification
    # ============================================================================

    intent: str | None
    confidence: float | None
    intent_domain: str | None
    entities: dict[str, Any]

    # ============================================================================
    # Clarification
    # ============================================================================

    needs_clarification: bool
    clarifying_question: str | None
    clarification_count: int
    clarification_response: str | None

    # ============================================================================
    # Context & Memory
    # ============================================================================

    session_context: dict[str, Any]
    conversation_history: Annotated[list[dict[str, Any]], add_messages]

    # ============================================================================
    # Tool Execution
    # ============================================================================

    tools_to_execute: list[str]
    tool_results: dict[str, Any]
    tool_execution_errors: dict[str, str]

    # ============================================================================
    # Response Generation
    # ============================================================================

    agent_response: str | None
    next_expected_intent: str | None

    # ============================================================================
    # Metadata & Control Flow
    # ============================================================================

    current_agent: str
    processing_step: str
    error: str | None
    retry_count: int

    # ============================================================================
    # Performance Tracking
    # ============================================================================

    start_time: float | None
    end_time: float | None
    agent_timings: dict[str, float]


# ============================================================================
# Helper Functions for State Initialization
# ============================================================================


def create_initial_state(
    session_id: str,
    customer_id: str,
    client_id: str,
    client_name: str,
    user_message: str,
    session_context: dict[str, Any] | None = None,
) -> AgentState:
    """
    Create initial agent state from chat request.

    Args:
        session_id: Session ID
        customer_id: Customer ID
        client_id: Client ID
        client_name: Client name
        user_message: User message
        session_context: Existing session context (optional)

    Returns:
        AgentState: Initial state dictionary
    """
    import time

    return AgentState(
        # Input
        session_id=session_id,
        customer_id=customer_id,
        client_id=client_id,
        client_name=client_name,
        user_message=user_message,
        # Intent classification
        intent=None,
        confidence=None,
        intent_domain=None,
        entities={},
        # Clarification
        needs_clarification=False,
        clarifying_question=None,
        clarification_count=0,
        clarification_response=None,
        # Context & memory
        session_context=session_context or {},
        conversation_history=[],
        # Tool execution
        tools_to_execute=[],
        tool_results={},
        tool_execution_errors={},
        # Response generation
        agent_response=None,
        next_expected_intent=None,
        # Metadata
        current_agent="supervisor",
        processing_step="start",
        error=None,
        retry_count=0,
        # Performance
        start_time=time.time(),
        end_time=None,
        agent_timings={},
    )


def add_conversation_turn(
    state: AgentState,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a conversation turn entry.

    Args:
        state: Current agent state
        role: Role (user/assistant/system)
        content: Message content
        metadata: Additional metadata

    Returns:
        dict: Conversation turn entry
    """
    import time

    return {
        "role": role,
        "content": content,
        "timestamp": time.time(),
        "session_id": state["session_id"],
        "metadata": metadata or {},
    }
