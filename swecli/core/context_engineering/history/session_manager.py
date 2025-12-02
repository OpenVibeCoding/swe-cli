"""Session persistence and management."""

import json
from pathlib import Path
from typing import Optional, Union

from swecli.models.message import ChatMessage
from swecli.models.session import Session, SessionMetadata


class SessionManager:
    """Manages session persistence and retrieval."""

    def __init__(self, session_dir: Path):
        """Initialize session manager.

        Args:
            session_dir: Directory to store session files
        """
        self.session_dir = Path(session_dir).expanduser()
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[Session] = None
        self.turn_count = 0

    def create_session(self, working_directory: Optional[str] = None) -> Session:
        """Create a new session.

        Args:
            working_directory: Working directory for the session

        Returns:
            New session instance
        """
        session = Session(working_directory=working_directory)
        self.current_session = session
        self.turn_count = 0
        return session

    def load_session(self, session_id: str) -> Session:
        """Load a session from disk.

        Args:
            session_id: Session ID to load

        Returns:
            Loaded session

        Raises:
            FileNotFoundError: If session file doesn't exist
        """
        session_file = self.session_dir / f"{session_id}.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        with open(session_file) as f:
            data = json.load(f)

        session = Session(**data)
        self.current_session = session
        self.turn_count = len(session.messages)
        return session

    def save_session(self, session: Optional[Session] = None) -> None:
        """Save session to disk.

        Only saves sessions that have at least one message to avoid
        cluttering the session list with empty test sessions.

        Args:
            session: Session to save (defaults to current session)
        """
        session = session or self.current_session
        if not session:
            return

        # Only save sessions with at least one message
        if len(session.messages) == 0:
            return

        session_file = self.session_dir / f"{session.id}.json"

        with open(session_file, "w") as f:
            json.dump(session.model_dump(), f, indent=2, default=str)

    def add_message(self, message: ChatMessage, auto_save_interval: int = 5) -> None:
        """Add a message to the current session and auto-save if needed.

        Args:
            message: Message to add
            auto_save_interval: Save every N turns
        """
        if not self.current_session:
            raise ValueError("No active session")

        self.current_session.add_message(message)
        self.turn_count += 1

        # Auto-save
        if self.turn_count % auto_save_interval == 0:
            self.save_session()

    def list_sessions(self) -> list[SessionMetadata]:
        """List all saved sessions.

        Returns:
            List of session metadata, sorted by update time (newest first)
            Filters out empty sessions (sessions with no messages)
        """
        sessions = []
        for session_file in self.session_dir.glob("*.json"):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                session = Session(**data)

                # Skip empty sessions (no messages)
                if len(session.messages) == 0:
                    # Optionally clean up empty session files
                    try:
                        session_file.unlink()
                    except Exception:
                        pass
                    continue

                sessions.append(session.get_metadata())
            except Exception:
                continue  # Skip corrupted files

        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)

    def find_latest_session(self, working_directory: Union[Path, str]) -> Optional[SessionMetadata]:
        """Find the most recently updated session for the given working directory."""
        target = Path(working_directory).expanduser().resolve()
        for metadata in self.list_sessions():
            if not metadata.working_directory:
                continue
            try:
                candidate = Path(metadata.working_directory).expanduser().resolve()
            except Exception:
                continue
            if candidate == target:
                return metadata
        return None

    def load_latest_session(self, working_directory: Union[Path, str]) -> Optional[Session]:
        """Load the most recent session for a working directory."""
        metadata = self.find_latest_session(working_directory)
        if not metadata:
            return None
        return self.load_session(metadata.id)

    def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session ID to delete
        """
        session_file = self.session_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

    def get_current_session(self) -> Optional[Session]:
        """Get the current active session."""
        return self.current_session
