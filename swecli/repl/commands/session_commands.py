"""Session management commands for REPL."""

from pathlib import Path
from typing import Optional, TYPE_CHECKING

from rich.console import Console

from swecli.repl.commands.base import CommandHandler, CommandResult

if TYPE_CHECKING:
    from swecli.core.management import SessionManager, ConfigManager


class SessionCommands(CommandHandler):
    """Handler for session-related commands: /clear, /sessions, /resume."""

    def __init__(
        self,
        console: Console,
        session_manager: "SessionManager",
        config_manager: "ConfigManager",
    ):
        """Initialize session commands handler.

        Args:
            console: Rich console for output
            session_manager: Session manager instance
            config_manager: Configuration manager instance
        """
        super().__init__(console)
        self.session_manager = session_manager
        self.config_manager = config_manager

    def handle(self, args: str) -> CommandResult:
        """Handle session command (not used, individual methods called directly)."""
        raise NotImplementedError("Use specific methods: clear(), list_sessions(), resume()")

    def clear(self) -> CommandResult:
        """Clear current session and create a new one.

        Returns:
            CommandResult indicating success
        """
        if self.session_manager.current_session:
            self.session_manager.save_session()
            self.session_manager.create_session(
                working_directory=str(self.config_manager.working_dir)
            )
            self.print_success("Session cleared. Previous session saved.")
            return CommandResult(success=True, message="Session cleared")
        else:
            self.print_warning("No active session to clear.")
            return CommandResult(success=False, message="No active session")

    def list_sessions(self) -> CommandResult:
        """List all saved sessions.

        Returns:
            CommandResult with list of sessions
        """
        sessions = self.session_manager.list_sessions()

        if not sessions:
            self.print_warning("No saved sessions found.")
            return CommandResult(success=True, message="No sessions found")

        self.console.print("\n[bold]Saved Sessions:[/bold]\n")
        for session in sessions:
            self.console.print(
                f"  [cyan]{session.id}[/cyan] - "
                f"{session.updated_at.strftime('%Y-%m-%d %H:%M')} - "
                f"{session.message_count} messages - "
                f"{session.total_tokens} tokens"
            )
        self.console.print()

        return CommandResult(success=True, data=sessions)

    def resume(self, session_id: Optional[str]) -> CommandResult:
        """Resume a previous session."""
        candidate = (session_id or "").strip()

        if not candidate:
            latest = self.session_manager.find_latest_session(self.config_manager.working_dir)
            if not latest:
                self.print_warning("No saved sessions for this repository.")
                return CommandResult(success=False, message="No sessions available")
            candidate = latest.id
            self.print_success(f"Resuming latest session {candidate}")

        try:
            session = self.session_manager.load_session(candidate)
            if session.working_directory:
                self.config_manager.working_dir = Path(session.working_directory)
            return CommandResult(success=True, message=f"Resumed {candidate}")
        except FileNotFoundError:
            self.print_error(f"Session {candidate} not found.")
            return CommandResult(success=False, message=f"Session {candidate} not found")
