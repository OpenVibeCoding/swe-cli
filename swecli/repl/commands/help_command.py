"""Help command for REPL."""

from typing import TYPE_CHECKING

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from swecli.repl.commands.base import CommandHandler, CommandResult

if TYPE_CHECKING:
    from swecli.core.management import ModeManager


class HelpCommand(CommandHandler):
    """Handler for /help command."""

    def __init__(self, console: Console, mode_manager: "ModeManager"):
        """Initialize help command handler.

        Args:
            console: Rich console for output
            mode_manager: Mode manager for showing current mode
        """
        super().__init__(console)
        self.mode_manager = mode_manager

    def handle(self, args: str) -> CommandResult:
        """Show help message."""
        help_text = """
# Available Commands

## Operations
- `/run <command>` - Execute a bash command safely
- `/mode <name>` - Switch mode: normal or plan
- `/undo` - Undo the last operation
- `/init [path]` - Analyze codebase and generate AGENTS.md with repository guidelines
- `/history` - Show operation history

## File Operations
- `/tree [path]` - Show directory tree

## Session Management
- `/clear` - Clear current session context
- `/sessions` - List all saved sessions
- `/resume <id>` - Resume a previous session

## Configuration
- `/models` - Interactive model/provider selector (use ↑/↓ arrows to choose)

## MCP (Model Context Protocol)
- `/mcp list` - List configured MCP servers
- `/mcp connect <name>` - Connect to an MCP server
- `/mcp disconnect <name>` - Disconnect from a server
- `/mcp tools [<name>]` - Show available tools from server(s)
- `/mcp test <name>` - Test connection to a server

## General
- `/help` - Show this help message
- `/exit` - Exit SWE-CLI

**Current Mode:** {}
{}
        """.format(
            self.mode_manager.current_mode.value.upper(),
            self.mode_manager.get_mode_description()
        )

        self.console.print(Panel(Markdown(help_text), title="Help", border_style="green"))
        return CommandResult(success=True)
