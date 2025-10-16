"""Main output formatter that delegates to specialized formatters."""

from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel

from .formatter_base import TOOL_ICONS
from .file_formatters import FileFormatter
from .directory_formatter import DirectoryFormatter
from .plan_formatter import PlanFormatter
from .bash_formatter import BashFormatter
from .generic_formatter import GenericFormatter


class OutputFormatter:
    """Formats tool outputs with rich styling."""

    def __init__(self, console: Console):
        """Initialize output formatter.

        Args:
            console: Rich console for output
        """
        self.console = console

        # Initialize specialized formatters
        self.file_formatter = FileFormatter(console)
        self.directory_formatter = DirectoryFormatter(console)
        self.plan_formatter = PlanFormatter(console)
        self.bash_formatter = BashFormatter(console)
        self.generic_formatter = GenericFormatter(console)

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
        # Get tool icon
        icon = TOOL_ICONS.get(tool_name, "⏺")

        # Format based on tool type
        if result.get("plan_only"):
            return self.plan_formatter.format_plan_result(tool_name, tool_args, result)

        if tool_name == "write_file":
            return self.file_formatter.format_write_file(icon, tool_args, result)
        elif tool_name == "edit_file":
            return self.file_formatter.format_edit_file(icon, tool_args, result)
        elif tool_name == "read_file":
            return self.file_formatter.format_read_file(icon, tool_args, result)
        elif tool_name == "list_directory":
            return self.directory_formatter.format_list_directory(icon, tool_args, result)
        elif tool_name == "bash_execute":
            return self.bash_formatter.format_bash_execute(icon, tool_args, result)
        else:
            return self.generic_formatter.format_generic(icon, tool_name, tool_args, result)