"""Session management API endpoints."""

from typing import Dict, List, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from swecli.web.state import get_state

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionInfo(BaseModel):
    """Session information model."""
    id: str
    working_dir: str
    created_at: str
    updated_at: str
    message_count: int
    token_usage: Dict[str, Any]


@router.get("")
async def list_sessions() -> List[SessionInfo]:
    """List all available sessions.

    Returns:
        List of session information

    Raises:
        HTTPException: If listing fails
    """
    try:
        state = get_state()
        sessions = state.list_sessions()

        return [SessionInfo(**session) for session in sessions]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_session() -> Dict[str, Any]:
    """Get the current active session.

    Returns:
        Current session information

    Raises:
        HTTPException: If no session is active
    """
    try:
        state = get_state()

        # Ensure we have a session
        if not state.session_manager.get_current_session():
            from pathlib import Path
            state.session_manager.create_session(working_directory=str(Path.cwd()))

        session = state.session_manager.get_current_session()

        return {
            "id": session.id,
            "working_dir": session.working_dir,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": len(session.messages),
            "token_usage": session.token_usage,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/resume")
async def resume_session(session_id: str) -> Dict[str, str]:
    """Resume a specific session.

    Args:
        session_id: ID of the session to resume

    Returns:
        Status response

    Raises:
        HTTPException: If session not found or resume fails
    """
    try:
        state = get_state()
        success = state.resume_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        return {"status": "success", "message": f"Resumed session {session_id}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a specific session.

    Args:
        session_id: ID of the session to delete

    Returns:
        Status response

    Raises:
        HTTPException: If deletion fails
    """
    try:
        state = get_state()
        # TODO: Implement session deletion in SessionManager
        # For now, return not implemented

        return {"status": "not_implemented", "message": "Session deletion not yet implemented"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/export")
async def export_session(session_id: str) -> Dict[str, Any]:
    """Export a session as JSON.

    Args:
        session_id: ID of the session to export

    Returns:
        Session data

    Raises:
        HTTPException: If export fails
    """
    try:
        state = get_state()

        # Load the session
        original_session_id = state.get_current_session_id()
        state.resume_session(session_id)

        session = state.session_manager.get_current_session()

        # Restore original session
        if original_session_id:
            state.resume_session(original_session_id)

        return {
            "id": session.id,
            "working_dir": session.working_dir,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if hasattr(msg, 'timestamp') and msg.timestamp else None,
                }
                for msg in session.messages
            ],
            "token_usage": session.token_usage,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
