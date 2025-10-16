"""Elegant box formatters for chat interface."""

from typing import Optional


class ChatBoxFormatter:
    """Create elegant ASCII boxes for chat messages."""

    # Box drawing characters
    TOP_LEFT = "┌"
    TOP_RIGHT = "┐"
    BOTTOM_LEFT = "└"
    BOTTOM_RIGHT = "┘"
    HORIZONTAL = "─"
    VERTICAL = "│"

    # Status symbols
    SUCCESS = "✓"
    ERROR = "✗"
    RUNNING = "⚡"
    INFO = "ℹ"

    # Tool icons
    TOOL_ICONS = {
        "write_file": "📝",
        "edit_file": "✏️",
        "read_file": "📖",
        "list_files": "📁",
        "search_code": "🔍",
        "run_command": "⚡",
        "bash_execute": "⚡",
    }

    @staticmethod
    def _wrap_text(text: str, width: int) -> list[str]:
        """Wrap text to fit within width."""
        if not text:
            return [""]

        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_len = len(word)
            if current_length + word_len + len(current_line) <= width:
                current_line.append(word)
                current_length += word_len
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_len

        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [""]

    @staticmethod
    def tool_call_box(tool_name: str, args: dict, width: int = 50) -> str:
        """Format a tool call in an elegant box.

        Args:
            tool_name: Name of the tool being called
            args: Tool arguments dictionary
            width: Box width (default 50)

        Returns:
            Formatted box string
        """
        icon = ChatBoxFormatter.TOOL_ICONS.get(tool_name, "⏺")

        # Build content lines
        lines = []

        # Title line
        title = f"{icon} {tool_name}"
        lines.append(title)

        # Add key arguments (limit to most important ones)
        important_args = []
        if "file_path" in args:
            important_args.append(f"file: {args['file_path']}")
        elif "path" in args:
            important_args.append(f"path: {args['path']}")
        if "command" in args:
            cmd = args['command']
            if len(cmd) > width - 10:
                cmd = cmd[:width - 13] + "..."
            important_args.append(f"$ {cmd}")

        for arg in important_args:
            lines.append(arg)

        # Build the box
        inner_width = width - 4  # Account for borders and padding
        result = []

        # Top border
        result.append(f"{ChatBoxFormatter.TOP_LEFT}{ChatBoxFormatter.HORIZONTAL * 2} Tool Call {ChatBoxFormatter.HORIZONTAL * (width - 14)}{ChatBoxFormatter.TOP_RIGHT}")

        # Content lines
        for line in lines:
            if len(line) > inner_width:
                # Wrap long lines
                wrapped = ChatBoxFormatter._wrap_text(line, inner_width)
                for wrapped_line in wrapped:
                    padding = " " * (inner_width - len(wrapped_line))
                    result.append(f"{ChatBoxFormatter.VERTICAL} {wrapped_line}{padding} {ChatBoxFormatter.VERTICAL}")
            else:
                padding = " " * (inner_width - len(line))
                result.append(f"{ChatBoxFormatter.VERTICAL} {line}{padding} {ChatBoxFormatter.VERTICAL}")

        # Bottom border
        result.append(f"{ChatBoxFormatter.BOTTOM_LEFT}{ChatBoxFormatter.HORIZONTAL * (width - 2)}{ChatBoxFormatter.BOTTOM_RIGHT}")

        return "\n".join(result)

    @staticmethod
    def success_result_box(tool_name: str, output: str, width: int = 50) -> str:
        """Format a successful tool result in an elegant box.

        Args:
            tool_name: Name of the tool that executed
            output: Tool output/result
            width: Box width (default 50)

        Returns:
            Formatted box string
        """
        icon = ChatBoxFormatter.TOOL_ICONS.get(tool_name, "⏺")

        # Build content lines
        lines = []

        # Title line with success indicator
        title = f"{ChatBoxFormatter.SUCCESS} {icon} {tool_name}"
        lines.append(title)

        # Add output (truncate if too long)
        if output:
            output_lines = output.split("\n")
            # Show first few lines of output
            for line in output_lines[:3]:
                if len(line) > width - 6:
                    line = line[:width - 9] + "..."
                lines.append(line)

            if len(output_lines) > 3:
                lines.append(f"... ({len(output_lines) - 3} more lines)")

        # Build the box
        inner_width = width - 4
        result = []

        # Top border (green-ish)
        result.append(f"{ChatBoxFormatter.TOP_LEFT}{ChatBoxFormatter.HORIZONTAL * 2} Result {ChatBoxFormatter.HORIZONTAL * (width - 11)}{ChatBoxFormatter.TOP_RIGHT}")

        # Content lines
        for line in lines:
            if len(line) > inner_width:
                wrapped = ChatBoxFormatter._wrap_text(line, inner_width)
                for wrapped_line in wrapped:
                    padding = " " * (inner_width - len(wrapped_line))
                    result.append(f"{ChatBoxFormatter.VERTICAL} {wrapped_line}{padding} {ChatBoxFormatter.VERTICAL}")
            else:
                padding = " " * (inner_width - len(line))
                result.append(f"{ChatBoxFormatter.VERTICAL} {line}{padding} {ChatBoxFormatter.VERTICAL}")

        # Bottom border
        result.append(f"{ChatBoxFormatter.BOTTOM_LEFT}{ChatBoxFormatter.HORIZONTAL * (width - 2)}{ChatBoxFormatter.BOTTOM_RIGHT}")

        return "\n".join(result)

    @staticmethod
    def error_result_box(tool_name: str, error: str, width: int = 50) -> str:
        """Format an error result in an elegant box.

        Args:
            tool_name: Name of the tool that failed
            error: Error message
            width: Box width (default 50)

        Returns:
            Formatted box string
        """
        icon = ChatBoxFormatter.TOOL_ICONS.get(tool_name, "⏺")

        # Build content lines
        lines = []

        # Title line with error indicator
        title = f"{ChatBoxFormatter.ERROR} {icon} {tool_name}"
        lines.append(title)

        # Add error message (wrap if needed)
        if error:
            error_lines = error.split("\n")
            for line in error_lines[:5]:  # Show first 5 lines
                if len(line) > width - 6:
                    line = line[:width - 9] + "..."
                lines.append(line)

            if len(error_lines) > 5:
                lines.append(f"... ({len(error_lines) - 5} more lines)")

        # Build the box
        inner_width = width - 4
        result = []

        # Top border (red-ish)
        result.append(f"{ChatBoxFormatter.TOP_LEFT}{ChatBoxFormatter.HORIZONTAL * 2} Error {ChatBoxFormatter.HORIZONTAL * (width - 10)}{ChatBoxFormatter.TOP_RIGHT}")

        # Content lines
        for line in lines:
            if len(line) > inner_width:
                wrapped = ChatBoxFormatter._wrap_text(line, inner_width)
                for wrapped_line in wrapped:
                    padding = " " * (inner_width - len(wrapped_line))
                    result.append(f"{ChatBoxFormatter.VERTICAL} {wrapped_line}{padding} {ChatBoxFormatter.VERTICAL}")
            else:
                padding = " " * (inner_width - len(line))
                result.append(f"{ChatBoxFormatter.VERTICAL} {line}{padding} {ChatBoxFormatter.VERTICAL}")

        # Bottom border
        result.append(f"{ChatBoxFormatter.BOTTOM_LEFT}{ChatBoxFormatter.HORIZONTAL * (width - 2)}{ChatBoxFormatter.BOTTOM_RIGHT}")

        return "\n".join(result)

    @staticmethod
    def system_message_box(message: str, width: int = 50) -> str:
        """Format a system message in a simple box.

        Args:
            message: System message text
            width: Box width (default 50)

        Returns:
            Formatted box string
        """
        lines = ChatBoxFormatter._wrap_text(message, width - 6)

        inner_width = width - 4
        result = []

        # Top border
        result.append(f"{ChatBoxFormatter.TOP_LEFT}{ChatBoxFormatter.HORIZONTAL * 2} System {ChatBoxFormatter.HORIZONTAL * (width - 11)}{ChatBoxFormatter.TOP_RIGHT}")

        # Content lines
        for line in lines:
            padding = " " * (inner_width - len(line))
            result.append(f"{ChatBoxFormatter.VERTICAL} {line}{padding} {ChatBoxFormatter.VERTICAL}")

        # Bottom border
        result.append(f"{ChatBoxFormatter.BOTTOM_LEFT}{ChatBoxFormatter.HORIZONTAL * (width - 2)}{ChatBoxFormatter.BOTTOM_RIGHT}")

        return "\n".join(result)
