"""Claude Code-style minimalist formatter for tool outputs."""

from pathlib import Path
from typing import Dict, Any, List
import time

from .formatter_base import STATUS_ICONS
from swecli.ui.utils.tool_display import get_tool_display_parts


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
        elif tool_name == "get_process_output":
            result_lines = self._format_process_output_result(tool_args, result)
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
        verb, label = get_tool_display_parts(tool_name)
        display_name = f"{verb}({label})" if label else verb

        if not tool_args:
            return display_name

        # Format arguments concisely
        arg_strs = []
        for key, value in tool_args.items():
            arg_str = self._format_argument(key, value)
            if arg_str:
                arg_strs.append(f"{key}={arg_str}")

        if arg_strs:
            return f"{self._highlight_function_name(display_name)}({', '.join(arg_strs)})"
        else:
            return self._highlight_function_name(display_name)

    def _highlight_function_name(self, function_name: str) -> str:
        """Add elegant color highlighting to function names."""
        # ANSI color codes for elegant highlighting
        # Using a nice cyan/blue color that's readable but distinctive
        COLOR = "\033[96m"  # Bright cyan
        BOLD = "\033[1m"
        RESET = "\033[0m"

        return f"{COLOR}{BOLD}{function_name}{RESET}"

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
        """Format edit_file result with side-by-side diff style."""
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

        # Calculate changes
        old_lines = old_content.splitlines() if old_content else []
        new_lines = new_content.splitlines() if new_content else []

        # Show summary
        additions = len(new_lines) - len([line for line in new_lines if line in old_lines])
        deletions = len(old_lines) - len([line for line in old_lines if line in new_lines])
        result_lines = [f"Updated {Path(file_path).name} with {additions} additions and {deletions} removals"]

        # ANSI color codes
        RED = "\033[91m"  # Bright red (lighter and more readable)
        GREEN = "\033[32m"
        RESET = "\033[0m"
        CYAN = "\033[36m"
        BOLD = "\033[1m"

        # Add border before diff
        result_lines.append(f"{CYAN}┌─ {Path(file_path).name} diff ─{RESET}")

        # Show actual diff with line numbers and +/- indicators
        max_lines = min(15, max(len(old_lines), len(new_lines)))  # Limit to 15 lines max

        for i in range(max_lines):
            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None

            if old_line == new_line:
                # No change - skip or show as context
                if i < 3:  # Show first few lines as context
                    result_lines.append(f"     {i+1:2d}    {old_line or ''}")
                continue

            if old_line is not None and new_line is None:
                # Line was deleted
                result_lines.append(f"{RED}{i+1:2d} -    {old_line}{RESET}")
            elif old_line is None and new_line is not None:
                # Line was added
                result_lines.append(f"{GREEN}{i+1:2d} +    {new_line}{RESET}")
            else:
                # Line was changed
                if old_line.strip():  # Show removed line
                    result_lines.append(f"{RED}{i+1:2d} -    {old_line}{RESET}")
                if new_line.strip():  # Show added line
                    result_lines.append(f"{GREEN}{i+1:2d} +    {new_line}{RESET}")

        # Add bottom border
        result_lines.append(f"{CYAN}└────────────────────────────{RESET}")

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
            # Show actual matches when there are few
            clean_matches = [m.strip() for m in matches if m.strip()]
            if clean_matches:
                return [f"Found in: {', '.join(clean_matches[:3])}"]
            else:
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

        # For other commands, show actual output content
        if output:
            lines = output.split('\n')
            if len(lines) == 1 and len(lines[0]) < 80:
                return [lines[0]]
            elif len(lines) > 1:
                # Show first line and line count for multi-line output
                first_line = lines[0][:70]
                if len(lines[0]) > 70:
                    first_line += "..."
                return [f"{first_line} ({len(lines)} lines)"]
            elif len(output) > 80:
                return [f"{output[:70]}..."]
            else:
                return [output]
        else:
            return [f"Command completed with no output"]

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
        return [f"Found {file_count} file(s)"]

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

    def _format_process_output_result(self, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format get_process_output result."""
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return [f"❌ {error}"]

        output = result.get("output", "")
        pid = tool_args.get("pid", "")

        if output:
            # Show actual output content, but concise
            lines = output.split('\n')
            if len(lines) == 1 and len(lines[0]) < 80:
                return [lines[0]]
            elif len(lines) > 1:
                # Show first line and line count
                first_line = lines[0][:70]
                if len(lines[0]) > 70:
                    first_line += "..."
                return [f"{first_line} ({len(lines)} lines)"]
            elif len(output) > 80:
                return [f"{output[:70]}..."]
            else:
                return [output]
        else:
            return [f"Process {pid} has no output"]

    def _format_generic_result(self, tool_name: str, tool_args: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """Format generic tool result."""
        if result.get("success"):
            # Try to extract meaningful info
            output = result.get("output", "")
            if output and isinstance(output, str):
                lines = output.split('\n')
                if len(lines) == 1 and len(lines[0]) < 80:
                    return [lines[0]]
                elif len(lines) > 1:
                    # Show first line and line count for multi-line output
                    first_line = lines[0][:70]
                    if len(lines[0]) > 70:
                        first_line += "..."
                    return [f"{first_line} ({len(lines)} lines)"]
                elif len(output) > 80:
                    return [f"{output[:70]}..."]
                else:
                    return [output]
            elif output:
                # For non-string outputs, show a meaningful representation
                return [f"Output: {str(output)[:100]}"]
            else:
                # Try to get meaningful info from tool name and args
                verb, label = get_tool_display_parts(tool_name)
                display_name = f"{verb}({label})" if label else verb
                if tool_args:
                    main_arg = next(iter(tool_args.values()), None)
                    if main_arg and isinstance(main_arg, str) and len(main_arg) < 50:
                        return [f"{display_name} on {main_arg}"]
                return [f"{display_name} completed"]
        else:
            error = result.get("error", "Unknown error")
            return [f"❌ {error}"]
