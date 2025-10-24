"""Utilities for presenting human-friendly tool call information."""

from __future__ import annotations

from typing import Any, Mapping

# Central mapping from internal tool identifiers to user-facing labels
_TOOL_DISPLAY_NAMES: dict[str, str] = {
    "write_file": "Write",
    "edit_file": "Edit",
    "read_file": "Read",
    "list_files": "List",
    "list_directory": "Directory",
    "delete_file": "Delete",
    "search": "Search",
    "run_command": "Shell",
    "bash_execute": "Shell",
    "list_processes": "Processes",
    "get_process_output": "Process_Output",
    "kill_process": "Stop_Process",
    "fetch_url": "Fetch",
    "open_browser": "Browser",
    "capture_screenshot": "Screenshot",
    "list_screenshots": "Screenshot_List",
    "clear_screenshots": "Screenshot_Clear",
    "capture_web_screenshot": "Web_Screenshot",
    "list_web_screenshots": "Web_Screenshot_List",
    "clear_web_screenshots": "Web_Screenshot_Clear",
    "analyze_image": "Analyze_Image",
    "git_commit": "Commit",
    "git_branch": "Branch",
}


def get_tool_display_name(tool_name: str) -> str:
    """Return a user-friendly display name for a tool."""
    if tool_name.startswith("mcp__"):
        # mcp__server__tool_name → MCP Tool: server/tool_name
        parts = tool_name.split("__", 2)
        if len(parts) == 3:
            return f"MCP • {parts[1]}/{parts[2]}".strip()
        if len(parts) == 2:
            return f"MCP • {parts[1]}"
        return "MCP Tool"

    if tool_name in _TOOL_DISPLAY_NAMES:
        return _TOOL_DISPLAY_NAMES[tool_name]

    # Fallback: transform snake_case into underscored title casing
    cleaned = tool_name.replace("-", "_")
    parts = [part for part in cleaned.split("_") if part]
    if not parts:
        return tool_name
    capitalized = [part.capitalize() for part in parts]
    return "_".join(capitalized) if len(capitalized) > 1 else capitalized[0]


def format_tool_call(tool_name: str, tool_args: Mapping[str, Any]) -> str:
    """Format a tool call using the friendly display name and summarized arguments."""

    def _summarize_arg(key: str, value: Any) -> str:
        if isinstance(value, str) and key in {"content", "new_string", "old_string", "text"}:
            line_count = value.count("\n") + 1
            char_count = len(value)
            if char_count > 80:
                return f"<{char_count} chars, {line_count} lines>"
            first_line = value.split("\n", 1)[0][:50]
            if len(value) > 50:
                return f"'{first_line}...'"
            return repr(value)

        value_repr = repr(value)
        if len(value_repr) > 100:
            return value_repr[:97] + "..."
        return value_repr

    display_name = get_tool_display_name(tool_name)

    if tool_args:
        args_str = ", ".join(f"{key}={_summarize_arg(key, value)}" for key, value in tool_args.items())
        return f"{display_name}({args_str})"
    return display_name
