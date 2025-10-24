"""
Chat API endpoints for web interface.

Provides:
- POST /chat - Send message and get response
- GET /health - Health check
- WebSocket /ws (future) - Real-time chat
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.bedrock_agent import invoke_agent
from app.core.database import get_session
from app.core.logging import get_logger
from app.schemas.chat import ChatRequest, ChatResponse, ChatMetadata, HealthCheckResponse
from app.models.session import Session
from app.models.conversation import Message

logger = get_logger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Chat Endpoint
# ============================================================================


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process chat message and return agent response.

    Args:
        request: Chat request with message and session info

    Returns:
        ChatResponse: Agent response with metadata

    Raises:
        HTTPException: If agent invocation fails
    """
    start_time = datetime.utcnow()

    logger.info(
        "chat_request_received",
        session_id=request.session_id,
        customer_id=request.customer_id,
        client_id=request.client_id,
        customer_type=request.customer_type,
        message_length=len(request.message),
    )

    try:
        # Validate session_id format
        try:
            # Ensure it's a valid UUID string
            session_id = str(request.session_id)
        except Exception:
            session_id = str(uuid.uuid4())
            logger.warning("invalid_session_id_regenerated", new_session_id=session_id)

        # Store user message in database (async)
        try:
            async with get_session() as db_session:
                # Get or create session
                db_session_record = await db_session.get(Session, session_id)
                if not db_session_record:
                    # Build context for B2C/B2B
                    context = {
                        "client_name": request.client_name,
                        "customer_type": request.customer_type,
                    }

                    # Add B2B context
                    if request.client_id:
                        context["client_id"] = request.client_id

                    if request.available_clients:
                        context["available_clients"] = [
                            {
                                "client_id": c.client_id,
                                "client_name": c.client_name,
                                "is_primary": c.is_primary
                            }
                            for c in request.available_clients
                        ]
                        context["total_clients"] = len(request.available_clients)

                    db_session_record = Session(
                        id=session_id,
                        customer_id=request.customer_id,
                        channel="chat",
                        status="active",
                        context=context,
                    )
                    db_session.add(db_session_record)

                # Store user message
                user_message = Message(
                    session_id=session_id,
                    role="user",
                    content=request.message,
                    content_type="text",
                )
                db_session.add(user_message)
                await db_session.commit()

                logger.debug("user_message_stored", session_id=session_id)

        except Exception as e:
            # Don't fail the request if database fails
            logger.error("database_storage_failed", error=str(e))

        # Prepare available_clients for Bedrock
        available_clients = None
        if request.available_clients:
            available_clients = [
                {
                    "client_id": c.client_id,
                    "client_name": c.client_name,
                    "is_primary": c.is_primary
                }
                for c in request.available_clients
            ]

        # Invoke Bedrock Agent with B2C/B2B context
        agent_response = await invoke_agent(
            input_text=request.message,
            session_id=session_id,
            enable_trace=False,  # Set to True for debugging
            customer_id=request.customer_id,
            client_id=request.client_id,
            available_clients=available_clients,
            customer_type=request.customer_type,
        )

        # Extract response text
        response_text = agent_response.get("output", "")
        if not response_text:
            response_text = "I apologize, but I'm having trouble processing your request. Please try again."

        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Store agent response in database
        try:
            async with get_session() as db_session:
                assistant_message = Message(
                    session_id=session_id,
                    role="assistant",
                    content=response_text,
                    content_type="text",
                    agent_id=agent_response.get("agent_id"),
                    latency_ms=agent_response.get("latency_ms"),
                )
                db_session.add(assistant_message)
                await db_session.commit()

                logger.debug("assistant_message_stored", session_id=session_id)

        except Exception as e:
            logger.error("database_storage_failed", error=str(e))

        # Build response
        response = ChatResponse(
            response=response_text,
            session_id=session_id,
            intent=None,  # Could be extracted from trace if needed
            confidence=None,
            metadata=ChatMetadata(
                tools_executed=[],  # Could be extracted from trace
                clarification_needed=False,
                processing_time_ms=processing_time_ms,
            ),
        )

        logger.info(
            "chat_response_sent",
            session_id=session_id,
            response_length=len(response_text),
            processing_time_ms=processing_time_ms,
        )

        return response

    except Exception as e:
        logger.error(
            "chat_request_failed",
            session_id=request.session_id,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}",
        )


# ============================================================================
# Health Check Endpoint
# ============================================================================


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns:
        HealthCheckResponse: Service health status
    """
    checks: dict[str, Any] = {}

    # Check database
    try:
        from sqlalchemy import text
        async with get_session() as db_session:
            await db_session.execute(text("SELECT 1"))
            checks["database"] = "healthy"
    except Exception:
        checks["database"] = "unhealthy"

    # Check Bedrock Agent (optional - can be slow)
    # checks["bedrock_agent"] = "healthy"  # Assume healthy for now

    # Overall status
    all_healthy = all(v == "healthy" for v in checks.values())
    overall_status = "ok" if all_healthy else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        checks=checks,
    )


# ============================================================================
# Session Management
# ============================================================================


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    """
    Get session information.

    Args:
        session_id: Session ID

    Returns:
        dict: Session data
    """
    try:
        async with get_session() as db_session:
            session_record = await db_session.get(Session, session_id)

            if not session_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found",
                )

            return {
                "session_id": session_record.id,
                "customer_id": session_record.customer_id,
                "channel": session_record.channel,
                "status": session_record.status,
                "created_at": session_record.created_at.isoformat(),
                "updated_at": session_record.updated_at.isoformat(),
                "expires_at": session_record.expires_at.isoformat() if session_record.expires_at else None,
                "context": session_record.context,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_session_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str) -> dict[str, Any]:
    """
    Get all messages in a session.

    Args:
        session_id: Session ID

    Returns:
        dict: List of messages
    """
    try:
        async with get_session() as db_session:
            # Get session
            session_record = await db_session.get(Session, session_id)
            if not session_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found",
                )

            # Get messages
            from sqlalchemy import select
            stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
            result = await db_session.execute(stmt)
            messages = result.scalars().all()

            return {
                "session_id": session_id,
                "message_count": len(messages),
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                        "agent_name": msg.agent_name,
                        "action_invoked": msg.action_invoked,
                    }
                    for msg in messages
                ],
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_session_messages_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
