"""Console wrapper that redirects output to chat conversation."""

import re
from typing import Optional, Any
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

from opencli.ui.chat_formatters import ChatBoxFormatter


class ChatConsole:
    """Console wrapper that outputs to chat conversation instead of terminal."""

    def __init__(self, chat_app, real_console: Console):
        """Initialize chat console wrapper.

        Args:
            chat_app: ChatApplication instance to output to
            real_console: Real Console instance (for internal use)
        """
        self.chat_app = chat_app
        self.real_console = real_console
        self._buffer = []
        self.formatter = ChatBoxFormatter()

    def print(self, *args, **kwargs) -> None:
        """Print to chat conversation."""
        # Handle Rich Panel specially
        if len(args) == 1 and isinstance(args[0], Panel):
            self._print_panel(args[0])
            return

        # Convert arguments to string
        text_parts = []
        for arg in args:
            if isinstance(arg, str):
                text_parts.append(arg)
            elif isinstance(arg, Text):
                text_parts.append(str(arg))
            elif isinstance(arg, Panel):
                panel_text = self._panel_to_text(arg)
                text_parts.append(panel_text)
            else:
                text_parts.append(str(arg))

        text = " ".join(text_parts)

        # Remove Rich markup
        text = self._strip_rich_markup(text)
        text = text.strip()

        if not text:
            return

        # Detect message type
        message_type = self._detect_message_type(text)

        if message_type == "tool_call":
            # Format tool call with elegant box
            tool_name, tool_args = self._parse_tool_call(text)
            formatted_text = self.formatter.tool_call_box(tool_name, tool_args)
            self.chat_app.add_assistant_message(formatted_text)
        elif message_type == "llm_response":
            # Regular LLM response - clean, no box
            # Check if text already starts with ⏺
            if text.startswith("⏺"):
                text = text[1:].strip()

            # Check if last message was a spinner
            if self.chat_app.conversation.last_was_spinner:
                formatted_text = f"⏺ {text}"
                self.chat_app.update_last_message(formatted_text)
                self.chat_app.conversation.last_was_spinner = False
            else:
                formatted_text = f"⏺ {text}"
                self.chat_app.add_assistant_message(formatted_text)
        else:
            # System/other message
            self.chat_app.add_system_message(text)

    def _print_panel(self, panel: Panel) -> None:
        """Handle Rich Panel printing with elegant formatting."""
        # Extract tool name and result from panel
        title = str(panel.title) if panel.title else ""
        content = panel.renderable

        if isinstance(content, str):
            text = content
        elif isinstance(content, Text):
            text = str(content)
        else:
            text = str(content)

        # Strip markup
        title = self._strip_rich_markup(title)
        text = self._strip_rich_markup(text)

        # Detect if this is a tool result
        tool_name, is_success = self._parse_tool_result_title(title)

        if tool_name:
            # Format as elegant result box
            if is_success:
                formatted_text = self.formatter.success_result_box(tool_name, text)
            else:
                formatted_text = self.formatter.error_result_box(tool_name, text)

            self.chat_app.add_assistant_message(formatted_text)
        else:
            # Generic panel - show with simple formatting
            if title:
                formatted_text = f"{title}\n{text}"
            else:
                formatted_text = text

            self.chat_app.add_assistant_message(formatted_text)

    def _detect_message_type(self, text: str) -> str:
        """Detect the type of message being printed.

        Returns:
            'tool_call', 'llm_response', or 'system'
        """
        # Check if it's a tool call (format: "⏺ tool_name(...)")
        if re.match(r'⏺\s*\w+\(', text):
            return "tool_call"

        # If it starts with ⏺, it's likely an LLM response
        if text.startswith("⏺"):
            return "llm_response"

        # Check for tool call patterns without ⏺
        if re.match(r'^\w+\(.*\)', text):
            return "tool_call"

        # Default to LLM response
        return "llm_response"

    def _parse_tool_call(self, text: str) -> tuple[str, dict]:
        """Parse tool call text to extract tool name and arguments.

        Returns:
            (tool_name, arguments_dict)
        """
        # Remove ⏺ if present
        text = text.replace("⏺", "").strip()

        # Try to parse: tool_name(arg1=val1, arg2=val2)
        match = re.match(r'(\w+)\((.*)\)', text)
        if match:
            tool_name = match.group(1)
            args_str = match.group(2)

            # Parse arguments (simple parsing)
            args = {}
            if args_str:
                # Try to extract key=value pairs
                arg_matches = re.findall(r'(\w+)=["\']([^"\']+)["\']', args_str)
                for key, value in arg_matches:
                    args[key] = value

            return tool_name, args

        # Fallback: use the whole text as tool name
        return text.split("(")[0] if "(" in text else text, {}

    def _parse_tool_result_title(self, title: str) -> tuple[Optional[str], bool]:
        """Parse tool result title to extract tool name and success status.

        Returns:
            (tool_name, is_success) or (None, False) if not a tool result
        """
        # Look for patterns like "⚡ bash_execute" or "📝 write_file"
        if any(icon in title for icon in ["⚡", "📝", "✏️", "📖", "📁", "🔍"]):
            # Extract tool name (usually the last word)
            parts = title.split()
            if parts:
                tool_name = parts[-1]
                # Check for success/error indicators
                is_success = "✗" not in title and "error" not in title.lower()
                return tool_name, is_success

        return None, False

    def _strip_rich_markup(self, text: str) -> str:
        """Strip Rich console markup from text."""
        import re
        # Remove [style]...[/style] markup
        text = re.sub(r'\[/?[^\]]+\]', '', text)
        # Remove ANSI escape codes
        text = re.sub(r'\x1b\[[0-9;]+m', '', text)
        return text

    def _panel_to_text(self, panel: Panel) -> str:
        """Convert Rich Panel to plain text for chat display."""
        # Get the panel's title and content
        title = str(panel.title) if panel.title else ""

        # Get the renderable content
        content = panel.renderable
        if isinstance(content, str):
            text = content
        elif isinstance(content, Text):
            text = str(content)
        else:
            # For other types (Syntax, Table, etc), convert to string
            text = str(content)

        # Strip Rich markup
        text = self._strip_rich_markup(text)
        title = self._strip_rich_markup(title)

        # Format for chat: show title if present
        if title:
            return f"{title}\n{text}"
        return text

    def __getattr__(self, name: str) -> Any:
        """Delegate other methods to real console."""
        return getattr(self.real_console, name)
