"""Chat and query API endpoints."""

from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from swecli.web.state import get_state
from swecli.models.message import ChatMessage, Role

router = APIRouter(prefix="/api/chat", tags=["chat"])


class QueryRequest(BaseModel):
    """Request model for sending a query."""
    message: str
    sessionId: str | None = None


class MessageResponse(BaseModel):
    """Response model for a chat message."""
    role: str
    content: str
    timestamp: str | None = None


@router.post("/query")
async def send_query(request: QueryRequest) -> Dict[str, str]:
    """Send a query to the AI agent.

    Args:
        request: Query request with message and optional session ID

    Returns:
        Status response

    Raises:
        HTTPException: If query fails
    """
    try:
        state = get_state()

        # Add user message to session
        user_msg = ChatMessage(role=Role.USER, content=request.message)
        state.add_message(user_msg)

        # TODO: Trigger agent processing in background
        # For now, just acknowledge receipt

        return {
            "status": "received",
            "message": "Query processing will be implemented in next phase"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages")
async def get_messages() -> List[MessageResponse]:
    """Get all messages in the current session.

    Returns:
        List of messages

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        state = get_state()

        # Ensure we have a session
        if not state.session_manager.get_current_session():
            from pathlib import Path
            state.session_manager.create_session(working_directory=str(Path.cwd()))

        messages = state.get_messages()

        return [
            MessageResponse(
                role=msg.role.value,
                content=msg.content,
                timestamp=msg.timestamp.isoformat() if hasattr(msg, 'timestamp') and msg.timestamp else None
            )
            for msg in messages
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_chat() -> Dict[str, str]:
    """Clear the current chat session.

    Returns:
        Status response

    Raises:
        HTTPException: If clearing fails
    """
    try:
        state = get_state()
        # Create a new session (effectively clearing current one)
        state.session_manager.create_session()

        return {"status": "success", "message": "Chat cleared"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
