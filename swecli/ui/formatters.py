"""Output formatters for rich tool displays."""

from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel

from .formatters_internal.factory import FormatterFactory
from .formatters_internal.base import STATUS_ICONS, ACTION_HINTS


# Tool icons (for backward compatibility)
TOOL_ICONS = {
    "write_file": "📝",
    "edit_file": "✏️",
    "read_file": "📖",
    "list_directory": "📁",
    "delete_file": "🗑️",
    "bash_execute": "⚡",
    "git_commit": "💾",
    "git_branch": "🌿",
}


# Backward compatibility - keep original class name but use refactored implementation
class OutputFormatter:
    """Formats tool outputs with rich styling using modular formatters."""

    def __init__(self, console: Console):
        """Initialize output formatter.

        Args:
            console: Rich console for output
        """
        self.console = console
        self.factory = FormatterFactory(console)

    def format_tool_result(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Dict[str, Any],
    ) -> Panel:
        """Format a tool result as a rich panel.

        Args:
            tool_name: Name of the tool
            tool_args: Tool arguments
            result: Tool execution result

        Returns:
            Formatted panel
        """
        return self.factory.format_tool_result(tool_name, tool_args, result)

    def register_formatter(self, tool_name: str, formatter) -> None:
        """Register a custom formatter for a tool.

        Args:
            tool_name: Name of the tool
            formatter: Custom formatter instance
        """
        self.factory.register_formatter(tool_name, formatter)