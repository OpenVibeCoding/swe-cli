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

    def changed_files(self) -> CommandResult:
        """Display all file changes made in the current session.

        Returns:
            CommandResult with file changes data
        """
        session = self.session_manager.get_current_session()

        if not session:
            self.print_warning("No active session.")
            return CommandResult(success=False, message="No active session")

        if not session.file_changes:
            self.console.print("\n[dim]No file changes recorded in this session yet.[/dim]\n")
            return CommandResult(success=True, message="No file changes")

        # Get summary
        summary = session.get_file_changes_summary()

        # Display header with summary
        self.console.print("\n[bold]File Changes in Current Session[/bold]\n")
        self.console.print(
            f"  [green]+{summary['total_lines_added']}[/green] / "
            f"[red]-{summary['total_lines_removed']}[/red] / "
            f"[dim]net: {summary['net_lines']:+d}[/dim]\n"
        )

        # Display each file change
        for change in sorted(session.file_changes, key=lambda c: c.timestamp, reverse=True):
            icon = change.get_file_icon()
            color = change.get_status_color()
            file_name = Path(change.file_path).name

            # Format time ago
            from datetime import datetime
            now = datetime.now()
            diff = now - change.timestamp
            if diff.seconds < 60:
                time_ago = "just now"
            elif diff.seconds < 3600:
                time_ago = f"{diff.seconds // 60}m ago"
            elif diff.days == 0:
                time_ago = f"{diff.seconds // 3600}h ago"
            else:
                time_ago = f"{diff.days}d ago"

            # Build status line
            status_parts = [f"[{color}]{change.type.value}[/{color}]"]
            if change.lines_added or change.lines_removed:
                status_parts.append(
                    f"[green]+{change.lines_added}[/green] "
                    f"[red]-{change.lines_removed}[/red]"
                )
            status_parts.append(f"[dim]{time_ago}[/dim]")

            self.console.print(
                f"  {icon} [bold]{file_name}[/bold] "
                f"[dim]{change.file_path}[/dim]\n"
                f"     {' · '.join(status_parts)}"
            )

        self.console.print(
            f"\n[dim]Total: {summary['total']} files changed[/dim]\n"
        )

        return CommandResult(success=True, data=summary)
