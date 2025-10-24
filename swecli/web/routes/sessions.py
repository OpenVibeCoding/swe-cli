"""Session management API endpoints."""

import os
from pathlib import Path
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
    total_tokens: int


class CreateSessionRequest(BaseModel):
    """Request model for creating a new session."""
    workspace: str


@router.post("/create")
async def create_session(request: CreateSessionRequest) -> Dict[str, Any]:
    """Create a new session with specified workspace.

    Args:
        request: Request containing workspace path

    Returns:
        New session information

    Raises:
        HTTPException: If creation fails
    """
    try:
        print(f"[DEBUG] Creating session with workspace: {request.workspace}")
        state = get_state()
        print(f"[DEBUG] Got state: {state}")

        # Create new session with specified workspace
        state.session_manager.create_session(working_directory=request.workspace)
        print("[DEBUG] Session created")

        # Save the session to disk
        state.session_manager.save_session()
        print("[DEBUG] Session saved to disk")

        session = state.session_manager.get_current_session()
        print(f"[DEBUG] Got current session: {session.id}")

        return {
            "status": "success",
            "message": "Session created",
            "session": {
                "id": session.id,
                "working_dir": session.working_directory or "",
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": len(session.messages),
                "total_tokens": session.total_tokens(),
            }
        }

    except Exception as e:
        print(f"[ERROR] Failed to create session: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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

        # Return error if no session exists
        session = state.session_manager.get_current_session()
        if not session:
            raise HTTPException(status_code=404, detail="No active session")

        return {
            "id": session.id,
            "working_dir": session.working_directory or "",
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": len(session.messages),
            "total_tokens": session.total_tokens(),
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
        print(f"[DEBUG] Resuming session {session_id}")
        state = get_state()
        success = state.resume_session(session_id)

        if not success:
            print(f"[DEBUG] Session {session_id} not found")
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Verify session was loaded
        current = state.session_manager.get_current_session()
        if current:
            print(f"[DEBUG] Session {session_id} loaded with {len(current.messages)} messages")
        else:
            print(f"[DEBUG] WARNING: Session loaded but current_session is None")

        return {"status": "success", "message": f"Resumed session {session_id}"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to resume session: {e}")
        import traceback
        traceback.print_exc()
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

        # Delete the session file from disk
        session_file = state.session_manager.session_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

            # If this was the current session, clear it
            current_session = state.session_manager.get_current_session()
            if current_session and current_session.id == session_id:
                state.session_manager.current_session = None

            return {"status": "success", "message": f"Session {session_id} deleted"}
        else:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    except HTTPException:
        raise
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
            "working_dir": session.working_directory or "",
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


@router.post("/verify-path")
async def verify_path(path_data: Dict[str, str]) -> Dict[str, Any]:
    """Verify if a directory path exists and is accessible.

    Args:
        path_data: Dictionary with 'path' key

    Returns:
        Dictionary with exists, is_directory, and error fields

    Raises:
        HTTPException: If verification fails
    """
    try:
        path = path_data.get("path", "").strip()

        if not path:
            return {
                "exists": False,
                "is_directory": False,
                "error": "Path cannot be empty"
            }

        path_obj = Path(path).expanduser().resolve()

        if not path_obj.exists():
            return {
                "exists": False,
                "is_directory": False,
                "error": "Path does not exist"
            }

        if not path_obj.is_dir():
            return {
                "exists": True,
                "is_directory": False,
                "error": "Path is not a directory"
            }

        # Check if we have read access
        if not os.access(path_obj, os.R_OK):
            return {
                "exists": True,
                "is_directory": True,
                "error": "No read access to directory"
            }

        return {
            "exists": True,
            "is_directory": True,
            "path": str(path_obj),
            "error": None
        }

    except Exception as e:
        return {
            "exists": False,
            "is_directory": False,
            "error": f"Failed to verify path: {str(e)}"
        }
