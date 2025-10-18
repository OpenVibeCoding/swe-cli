"""File operation commands for REPL."""

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel

from swecli.repl.commands.base import CommandHandler, CommandResult

if TYPE_CHECKING:
    from swecli.tools.file_ops import FileOperations


class FileCommands(CommandHandler):
    """Handler for file-related commands: /tree."""

    def __init__(
        self,
        console: Console,
        file_ops: "FileOperations",
    ):
        """Initialize file commands handler.

        Args:
            console: Rich console for output
            file_ops: File operations tool
        """
        super().__init__(console)
        self.file_ops = file_ops

    def handle(self, args: str) -> CommandResult:
        """Handle file command (not used, individual methods called directly)."""
        raise NotImplementedError("Use specific methods: show_tree()")

    def show_tree(self, path: str) -> CommandResult:
        """Show directory tree.

        Args:
            path: Directory path (defaults to current directory if empty)

        Returns:
            CommandResult with tree output
        """
        tree_path = path or "."

        try:
            tree = self.file_ops.list_directory(tree_path)
            self.console.print(Panel(tree, title="Directory Tree", border_style="cyan"))
            return CommandResult(success=True, data=tree)
        except Exception as e:
            self.print_error(f"Error displaying tree: {e}")
            return CommandResult(success=False, message=str(e))
