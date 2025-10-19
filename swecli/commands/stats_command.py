"""Stats command for displaying context usage statistics."""

from typing import Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from swecli.core.context import ContextTokenMonitor
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
        self.token_monitor = ContextTokenMonitor()

    def execute(self) -> dict[str, Any]:
        """Execute stats command.

        Returns:
            Result dictionary with success status
        """
        session = self.session_manager.get_current_session()

        if not session:
            self.console.print("[yellow]No active session[/yellow]")
            return {"success": False, "message": "No active session"}

        # Display context statistics
        self._display_context_stats(session)

        # Display session info
        self._display_session_info(session)

        return {"success": True, "message": "Stats displayed"}

    def _display_context_stats(self, session) -> None:
        """Display context usage statistics.

        Args:
            session: Current session
        """
        stats = session.get_token_stats()

        # Create main stats display
        title = Text("Context Usage", style="bold cyan")

        # Build content
        content = []

        # Current usage
        usage_pct = stats["usage_percent"]
        usage_color = self._get_usage_color(usage_pct)
        content.append(
            f"[bold]Current:[/bold] {stats['current_tokens']:,} tokens "
            f"([{usage_color}]{usage_pct:.1f}%[/{usage_color}])"
        )

        # Limit (dynamically set from model context length)
        content.append(
            f"[bold]Limit:[/bold] {stats['limit']:,} tokens"
        )

        # Available
        content.append(
            f"[bold]Available:[/bold] {stats['available']:,} tokens "
            f"({stats['until_compact_percent']:.1f}% until compact)"
        )

        # Status
        if stats["needs_compaction"]:
            status = "[yellow]⚠️  Compaction recommended[/yellow]"
        else:
            status = "[green]✓ Healthy[/green]"
        content.append(f"[bold]Status:[/bold] {status}")

        # Create panel
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
            table.add_row("System Messages", f"{system_msgs} (summaries)")

        self.console.print("\n")
        self.console.print(table)

    def _get_usage_color(self, usage_percent: float) -> str:
        """Get color based on usage percentage.

        Args:
            usage_percent: Usage percentage

        Returns:
            Color name for rich
        """
        if usage_percent < 50:
            return "green"
        elif usage_percent < 70:
            return "yellow"
        elif usage_percent < 80:
            return "orange"
        else:
            return "red"

    def display_compaction_history(self, session) -> None:
        """Display compaction history (if available).

        Args:
            session: Current session
        """
        # Count system messages (summaries)
        summaries = [m for m in session.messages if m.role.value == "system"
                     and m.metadata.get("type") == "compaction_summary"]

        if not summaries:
            return

        self.console.print("\n")
        table = Table(title="Compaction History", show_header=True, header_style="bold cyan")
        table.add_column("Time", style="dim")
        table.add_column("Messages", justify="right")
        table.add_column("Original Tokens", justify="right")
        table.add_column("Reduction", justify="right")

        for summary in summaries:
            metadata = summary.metadata
            compacted_at = metadata.get("compacted_at", "Unknown")
            msg_count = metadata.get("original_message_count", 0)
            original_tokens = metadata.get("original_token_count", 0)

            # Estimate reduction (current summary tokens vs original)
            summary_tokens = summary.tokens or len(summary.content) // 4
            if original_tokens > 0:
                reduction = ((original_tokens - summary_tokens) / original_tokens) * 100
                reduction_str = f"{reduction:.1f}%"
            else:
                reduction_str = "N/A"

            table.add_row(
                compacted_at.split("T")[1][:8] if "T" in compacted_at else compacted_at,
                str(msg_count),
                f"{original_tokens:,}",
                reduction_str,
            )

        self.console.print(table)
