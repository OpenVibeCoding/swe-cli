"""Stats command for displaying session and ACE context details."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from swecli.core.management import SessionManager


class StatsCommandHandler:
    """Handler for /stats command to display context statistics."""

    def __init__(self, session_manager: SessionManager, console: Console):
        """Initialize stats command handler.

        Args:
            session_manager: Session manager instance
            console: Rich console for output
        """
        self.session_manager = session_manager
        self.console = console

    def execute(self) -> dict[str, Any]:
        """Execute stats command.

        Returns:
            Result dictionary with success status
        """
        session = self.session_manager.get_current_session()

        if not session:
            self.console.print("[yellow]No active session[/yellow]")
            return {"success": False, "message": "No active session"}

        # Display high-level context strategy summary
        self._display_context_summary(session)

        # Display session info
        self._display_session_info(session)

        return {"success": True, "message": "Stats displayed"}

    def _display_context_summary(self, session) -> None:
        """Display how ACE manages context for the current session."""
        title = Text("Context Strategy", style="bold cyan")

        total_tokens = session.total_tokens()
        user_msgs = len([m for m in session.messages if m.role.value == "user"])
        assistant_msgs = len([m for m in session.messages if m.role.value == "assistant"])

        content = [
            f"[bold]Messages:[/bold] {len(session.messages)} "
            f"(users: {user_msgs}, assistant: {assistant_msgs})",
            f"[bold]Token usage:[/bold] {total_tokens:,}",
            "[bold]Active window:[/bold] Last interaction only (ACE reflection window)",
            "[bold]Long-term memory:[/bold] Stored in ACE playbook (no compaction)",
        ]

        panel = Panel(
            "\n".join(content),
            title=title,
            border_style="cyan",
            padding=(1, 2),
        )

        self.console.print(panel)

    def _display_session_info(self, session) -> None:
        """Display session information.

        Args:
            session: Current session
        """
        # Create table
        table = Table(title="Session Information", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        # Add rows
        table.add_row("Session ID", session.id)
        table.add_row("Messages", str(len(session.messages)))
        table.add_row(
            "Created",
            session.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        )
        table.add_row(
            "Updated",
            session.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Message breakdown
        user_msgs = len([m for m in session.messages if m.role.value == "user"])
        assistant_msgs = len([m for m in session.messages if m.role.value == "assistant"])
        system_msgs = len([m for m in session.messages if m.role.value == "system"])

        table.add_row("User Messages", str(user_msgs))
        table.add_row("Assistant Messages", str(assistant_msgs))
        if system_msgs > 0:
            table.add_row("System Messages", str(system_msgs))

        self.console.print("\n")
        self.console.print(table)
