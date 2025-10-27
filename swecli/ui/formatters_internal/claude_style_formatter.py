"""Claude Code-style minimalist formatter for tool outputs."""

from pathlib import Path
from typing import Dict, Any, List
import time

from .formatter_base import STATUS_ICONS
from swecli.ui.utils.tool_display import get_tool_display_name


class ClaudeStyleFormatter:
    """Minimalist formatter inspired by Claude Code's display style."""

    def __init__(self):
        """Initialize the Claude-style formatter."""
        pass

    def format_tool_result(self, tool_name: str, tool_args: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Format any tool result in Claude Code style.

        Args:
            tool_name: Name of the tool
            tool_args: Tool arguments
            result: Tool execution result

        Returns:
            Formatted string in Claude Code style
        """
        # Get tool display name and format tool call
        tool_display = self._format_tool_call(tool_name, tool_args)

        # Format result based on tool type
        if tool_name == "read_file":
            result_lines = self._format_read_file_result(tool_args, result)
        elif tool_name == "write_file":
            result_lines = self._format_write_file_result(tool_args, result)
        elif tool_name == "edit_file":
            result_lines = self._format_edit_file_result(tool_args, result)
        elif tool_name == "search":
            result_lines = self._format_search_result(tool_args, result)
        elif tool_name in ["run_command", "bash_execute"]:
            result_lines = self._format_shell_result(tool_args, result)
        elif tool_name == "list_files":
            result_lines = self._format_list_files_result(tool_args, result)
        elif tool_name == "fetch_url":
            result_lines = self._format_fetch_url_result(tool_args, result)
        elif tool_name == "analyze_image":
            result_lines = self._format_analyze_image_result(tool_args, result)
        else:
            result_lines = self._format_generic_result(tool_name, tool_args, result)

        # Combine tool call with results
        if result_lines:
            return f"⏺ {tool_display}\n" + "\n".join(f"  ⎿ {line}" for line in result_lines)
        else:
            return f"⏺ {tool_display}"

    def _format_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Format tool call in Claude Code style."""
        # Use centralized tool display name mapping for consistency
        display_name = get_tool_display_name(tool_name)

        if not tool_args:
            return display_name

        # Format arguments concisely
        arg_strs = []
        for key, value in tool_args.items():
            arg_str = self._format_argument(key, value)
            if arg_str:
                arg_strs.append(f"{key}={arg_str}")

        if arg_strs:
            return f"{display_name}({', '.join(arg_strs)})"
        else:
            return display_name

    def _format_argument(self, key: str, value: Any) -> str:
        """Format a single argument concisely."""
        if value is None:
            return ""

        # For string content, show size instead of full content
        if isinstance(value, str):
            if key in {"content", "new_string", "old_string", "text", "command"}:
                if len(value) > 80:
                    lines = value.count("\n") + 1
                    return f"<{len(value)} chars, {lines} lines>"
                first_line = value.split("\n", 1)[0]
                if len(first_line) > 50:
                    return repr(first_line[:47] + "...")
                return repr(first_line)

            # For file paths, just show the path
            if key in {"file_path", "path", "image_path"}:
                return repr(value)

            # For patterns, show as is
            if key in {"pattern"}:
                return repr(value)

            # For edit operations, be more aggressive about truncating
            if key in {"old_content", "new_content"}:
                if len(value) > 50:
                    return repr(value[:47] + "...")
                return repr(value)

        # For other types, use standard repr but limit length
        value_repr = repr(value)
        if len(value_repr) > 100:
            return value_repr[:97] + "..."
        return value_repr

    def _format_read_file_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format read_file result."""
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return [f"❌ {error}"]

        output = result.get("output", "")
        file_path = tool_args.get("file_path", "unknown")

        # Calculate file stats
        size_bytes = len(output)
        size_kb = size_bytes / 1024
        lines = output.count("\n") + 1 if output else 0

        # Format size display
        if size_kb >= 1:
            size_display = f"{size_kb:.1f} KB"
        else:
            size_display = f"{size_bytes} B"

        return [f"Read {lines} lines • {size_display}"]

    def _format_write_file_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format write_file result."""
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return [f"❌ {error}"]

        file_path = tool_args.get("file_path", "unknown")
        content = tool_args.get("content", "")

        # Calculate file stats
        size_bytes = len(content)
        size_kb = size_bytes / 1024
        lines = content.count("\n") + 1 if content else 0

        # Format size display
        if size_kb >= 1:
            size_display = f"{size_kb:.1f} KB"
        else:
            size_display = f"{size_bytes} B"

        return [f"Created {Path(file_path).name} • {size_display} • {lines} lines"]

    def _format_edit_file_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format edit_file result."""
        file_path = tool_args.get("file_path", "unknown")
        old_content = tool_args.get("old_content", "")
        new_content = tool_args.get("new_content", "")

        # Handle error cases
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            # Special handling for ambiguous content error
            if "appears" in error and "times" in error:
                return [f"❌ {error}"]
            return [f"❌ {error}"]

        # Show the diff format for successful edits
        result_lines = [f"Updated {Path(file_path).name}"]

        # Calculate approximate line numbers (simplified)
        old_lines = old_content.split('\n') if old_content else ['']
        new_lines = new_content.split('\n') if new_content else ['']

        # Find the line where change occurred (simplified - assume first different line)
        change_line = 1  # This would be more sophisticated in real implementation

        # Show old line (removed) with red indicator
        if old_lines and old_lines[0]:
            result_lines.append(f"❌-{change_line}                {old_lines[0]}")

        # Show new line (added) with green indicator
        if new_lines and new_lines[0]:
            result_lines.append(f"✅+{change_line}                {new_lines[0]}")

        # Show additional context lines if present
        if len(new_lines) > 1:
            for i, line in enumerate(new_lines[1:], 1):
                if line.strip():  # Only show non-empty lines
                    result_lines.append(f"✅+{change_line + i}                {line}")

        return result_lines

    def _format_search_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format search result."""
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return [f"❌ {error}"]

        output = result.get("output", "")
        if isinstance(output, list):
            matches = output
        else:
            # Parse output to count matches
            matches = output.split("\n") if output else []

        match_count = len(matches)
        if match_count == 0:
            return ["No matches found"]
        elif match_count <= 3:
            return [f"Found {match_count} file(s)"]
        else:
            return [f"Found {match_count} files (ctrl+o to expand)"]

    def _format_shell_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format shell command result."""
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return [f"❌ {error}"]

        output = result.get("output", "")
        command = tool_args.get("command", "")

        # Try to extract meaningful info from output
        if "npm install" in command:
            # Look for package count
            if "added" in output.lower() and "package" in output.lower():
                return ["Packages installed successfully"]
            return ["npm install completed"]

        elif "git " in command:
            if "push" in command:
                return ["Changes pushed to remote"]
            elif "commit" in command:
                return ["Changes committed"]
            elif "pull" in command:
                return ["Changes pulled from remote"]
            else:
                return ["Git command completed"]

        # For other commands, show first line or a summary
        first_line = output.split("\n", 1)[0] if output else ""
        if first_line and len(first_line) < 80:
            return [first_line]
        elif output:
            # Show line count instead of full output
            lines = output.count("\n") + 1
            return [f"Command completed • {lines} lines output"]
        else:
            return ["Command completed"]

    def _format_list_files_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format list_files result."""
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return [f"❌ {error}"]

        output = result.get("output", "")
        if isinstance(output, list):
            files = output
        else:
            files = output.split("\n") if output else []

        # Filter out empty strings
        files = [f for f in files if f.strip()]
        file_count = len(files)

        if file_count == 0:
            return ["No files found"]
        elif file_count <= 5:
            return [f"Found {file_count} file(s): {', '.join(files[:3])}" + ("..." if file_count > 3 else "")]
        else:
            return [f"Found {file_count} files"]

    def _format_fetch_url_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format fetch_url result."""
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return [f"❌ {error}"]

        url = tool_args.get("url", "")
        output = result.get("output", "")

        if output:
            # Count characters in fetched content
            char_count = len(output)
            if char_count >= 1000:
                content_size = f"{char_count // 1000}k chars"
            else:
                content_size = f"{char_count} chars"
            return [f"Fetched {content_size} from {Path(url).name}"]
        else:
            return [f"Fetched {Path(url).name}"]

    def _format_analyze_image_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format analyze_image result."""
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return [f"❌ {error}"]

        content = result.get("content", "")
        model = result.get("model", "")
        provider = result.get("provider", "")

        if content:
            # For image analysis, we want to show a meaningful summary
            if len(content) > 100:
                # Truncate long analyses but show they were substantial
                first_sentence = content.split('.')[0] + '.'
                if len(first_sentence) > 80:
                    first_sentence = first_sentence[:77] + "..."
                return [f"Image analyzed ({provider}•{model}): {first_sentence}"]
            else:
                # Show full content for shorter analyses
                return [f"Image analyzed ({provider}•{model}): {content}"]
        else:
            return [f"Image analyzed ({provider}•{model})"]

    def _format_generic_result(self, tool_name: str, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format generic tool result."""
        if result.get("success"):
            # Try to extract meaningful info
            output = result.get("output", "")
            if output and isinstance(output, str) and len(output) < 100:
                return [output]
            elif output:
                return [f"{tool_name.replace('_', ' ').title()} completed"]
            else:
                return [f"{tool_name.replace('_', ' ').title()} completed"]
        else:
            error = result.get("error", "Unknown error")
            return [f"❌ {error}"]