"""Shared state manager for web UI and terminal REPL."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from threading import Lock

from swecli.core.management import (
    ConfigManager,
    SessionManager,
    ModeManager,
    UndoManager,
)
from swecli.core.approval import ApprovalManager
from swecli.models.message import ChatMessage


class WebState:
    """Shared state between CLI and web UI.

    This class maintains a single source of truth for:
    - Current session
    - Configuration
    - Message history
    - Agent state

    Thread-safe for concurrent access from REPL and web server.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        mode_manager: ModeManager,
        approval_manager: ApprovalManager,
        undo_manager: UndoManager,
    ):
        self.config_manager = config_manager
        self.session_manager = session_manager
        self.mode_manager = mode_manager
        self.approval_manager = approval_manager
        self.undo_manager = undo_manager

        # Thread safety
        self._lock = Lock()

        # Connected WebSocket clients
        self._ws_clients: List[Any] = []

        # Pending approval requests
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}

    def add_ws_client(self, client: Any) -> None:
        """Add a WebSocket client."""
        with self._lock:
            if client not in self._ws_clients:
                self._ws_clients.append(client)

    def remove_ws_client(self, client: Any) -> None:
        """Remove a WebSocket client."""
        with self._lock:
            if client in self._ws_clients:
                self._ws_clients.remove(client)

    def get_ws_clients(self) -> List[Any]:
        """Get all connected WebSocket clients."""
        with self._lock:
            return self._ws_clients.copy()

    def get_messages(self) -> List[ChatMessage]:
        """Get current session messages."""
        session = self.session_manager.get_current_session()
        if session:
            return session.messages
        return []

    def add_message(self, message: ChatMessage) -> None:
        """Add a message to current session."""
        self.session_manager.add_message(message)

    def get_current_session_id(self) -> Optional[str]:
        """Get current session ID."""
        session = self.session_manager.get_current_session()
        return session.id if session else None

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions."""
        return [
            {
                "id": s.id,
                "working_dir": s.working_dir,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "message_count": len(s.messages),
                "token_usage": s.token_usage,
            }
            for s in self.session_manager.list_sessions()
        ]

    def resume_session(self, session_id: str) -> bool:
        """Resume a specific session."""
        try:
            self.session_manager.load_session(session_id)
            return True
        except Exception:
            return False

    def add_pending_approval(
        self,
        approval_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> None:
        """Add a pending approval request."""
        with self._lock:
            self._pending_approvals[approval_id] = {
                "tool_name": tool_name,
                "arguments": arguments,
                "resolved": False,
                "approved": None,
            }

    def resolve_approval(self, approval_id: str, approved: bool) -> bool:
        """Resolve a pending approval request."""
        with self._lock:
            if approval_id in self._pending_approvals:
                self._pending_approvals[approval_id]["resolved"] = True
                self._pending_approvals[approval_id]["approved"] = approved
                return True
            return False

    def get_pending_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Get a pending approval request."""
        with self._lock:
            return self._pending_approvals.get(approval_id)

    def clear_approval(self, approval_id: str) -> None:
        """Clear a resolved approval."""
        with self._lock:
            self._pending_approvals.pop(approval_id, None)


# Global state instance (will be initialized when web server starts)
_state: Optional[WebState] = None


def init_state(
    config_manager: ConfigManager,
    session_manager: SessionManager,
    mode_manager: ModeManager,
    approval_manager: ApprovalManager,
    undo_manager: UndoManager,
) -> WebState:
    """Initialize the global state instance."""
    global _state
    _state = WebState(
        config_manager,
        session_manager,
        mode_manager,
        approval_manager,
        undo_manager,
    )
    return _state


def get_state() -> WebState:
    """Get the global state instance."""
    if _state is None:
        # Auto-initialize with default managers for standalone server
        from pathlib import Path
        from swecli.core.management import ConfigManager, SessionManager, ModeManager, UndoManager
        from swecli.core.approval import ApprovalManager
        from rich.console import Console

        console = Console()
        working_dir = Path.cwd()

        config_manager = ConfigManager(working_dir)
        session_manager = SessionManager(Path.home() / ".swecli" / "sessions")
        mode_manager = ModeManager()
        approval_manager = ApprovalManager(console)
        undo_manager = UndoManager(50)

        # Create session if none exists
        if not session_manager.get_current_session():
            session_manager.create_session(working_directory=str(working_dir))

        return init_state(
            config_manager,
            session_manager,
            mode_manager,
            approval_manager,
            undo_manager,
        )
    return _state
