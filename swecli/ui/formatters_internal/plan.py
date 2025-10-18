"""Formatter for plan-only tool responses."""

from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .base import BaseToolFormatter
from .utils import ValueSummarizer


# Tool icons
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


class PlanFormatter(BaseToolFormatter):
    """Formatter for plan-only tool responses."""

    def format(self, tool_name: str, tool_args: Dict[str, Any], result: Dict[str, Any]) -> Panel:
        """Format plan-only tool response."""
        icon = TOOL_ICONS.get(tool_name, "🛠️")
        summary = result.get("plan_summary") or result.get("output") or "Execution skipped in plan mode."
        arguments = result.get("arguments") or tool_args or {}

        body = Text()
        body.append(f"{icon} Plan({tool_name})\n", style="bold")

        if result.get("success", True):
            body.append("  ⎿  Execution skipped (plan-only mode)\n", style="dim")
        else:
            error_message = result.get("error") or "Execution blocked in plan-only mode."
            body.append("  ⎿  Execution blocked in plan-only mode\n", style="yellow")
            if error_message:
                body.append(f"    {error_message}\n", style="dim")

        if summary and result.get("success", True):
            filtered_lines = []
            for line in summary.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("•"):
                    continue
                if stripped.startswith("-"):
                    continue
                if stripped.lower().startswith("arguments:"):
                    continue
                filtered_lines.append(line)

            if filtered_lines:
                body.append("\n")
                for line in filtered_lines:
                    body.append(f"  {line}\n", style="dim")

        if arguments:
            body.append("\n")
            body.append("  Arguments:\n", style="dim")
            for key, value in arguments.items():
                body.append(
                    f"  • {key}: {ValueSummarizer.summarize(value)}\n"
                )
        else:
            body.append("\n  • (no arguments)\n")

        border = "cyan" if result.get("success", True) else "yellow"
        return Panel(body, title="PLAN", title_align="left", border_style=border)