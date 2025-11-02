"""UI callback for real-time tool call display in Textual UI."""

from __future__ import annotations

import json
from typing import Any, Dict

from swecli.ui.formatters_internal.claude_style_formatter import ClaudeStyleFormatter


class TextualUICallback:
    """Callback for real-time display of agent actions in Textual UI."""

    def __init__(self, conversation_log, chat_app=None):
        """Initialize the UI callback.

        Args:
            conversation_log: The ConversationLog widget to display messages
            chat_app: The main chat app (SWECLIChatApp instance) for controlling processing state
        """
        self.conversation = conversation_log
        self.chat_app = chat_app
        # chat_app IS the Textual App instance itself, not a wrapper
        self._app = chat_app
        self.formatter = ClaudeStyleFormatter()
        self._current_thinking = False

    def on_thinking_start(self) -> None:
        """Called when the agent starts thinking."""
        self._current_thinking = True

        # The app's built-in spinner should already be running with our custom message
        # We don't need to start another spinner, just note that thinking has started

    def on_thinking_complete(self) -> None:
        """Called when the agent completes thinking."""
        if self._current_thinking:
            # Don't stop the spinner here - let it continue during tool execution
            # The app will stop it when the entire process is complete
            self._current_thinking = False

    def on_assistant_message(self, content: str) -> None:
        """Called when assistant provides a message before tool execution.

        Args:
            content: The assistant's message/thinking
        """
        if content and content.strip():
            # Stop spinner before showing assistant message
            if hasattr(self.conversation, 'stop_spinner'):
                self._run_on_ui(self.conversation.stop_spinner)
            if self.chat_app and hasattr(self.chat_app, "_stop_local_spinner"):
                self._run_on_ui(self.chat_app._stop_local_spinner)

            # Display the assistant's thinking/message
            if hasattr(self.conversation, 'add_assistant_message'):
                self._run_on_ui(self.conversation.add_assistant_message, content)

    def on_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> None:
        """Called when a tool call is about to be executed.

        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments for the tool call
        """
        # Stop thinking spinner if still active
        if self._current_thinking:
            self._run_on_ui(self.conversation.stop_spinner)
            self._current_thinking = False

        if self.chat_app and hasattr(self.chat_app, "_stop_local_spinner"):
            self._run_on_ui(self.chat_app._stop_local_spinner)

        normalized_args = self._normalize_arguments(tool_args)
        args_display = ", ".join(
            f"{key}={self._format_arg_for_display(value)}"
            for key, value in sorted(normalized_args.items())
        )

        # Display tool call (BLOCKING - ensure line is added)
        if hasattr(self.conversation, 'add_tool_call'):
            self._run_on_ui(self.conversation.add_tool_call, tool_name, args_display)

        # Start spinner animation (BLOCKING - ensure timer is created before tool executes)
        if hasattr(self.conversation, 'start_tool_execution'):
            self._run_on_ui(self.conversation.start_tool_execution)

    def on_tool_result(self, tool_name: str, tool_args: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Called when a tool execution completes.

        Args:
            tool_name: Name of the tool that was executed
            tool_args: Arguments that were used
            result: Result of the tool execution
        """
        # Stop spinner animation (blocking so the bullet restores before results render)
        if hasattr(self.conversation, 'stop_tool_execution'):
            self._run_on_ui(self.conversation.stop_tool_execution)

        # Format the result using the Claude-style formatter
        normalized_args = self._normalize_arguments(tool_args)
        formatted = self.formatter.format_tool_result(tool_name, normalized_args, result)

        # Extract the result line(s) from the formatted output
        summary_lines: list[str] = []
        if isinstance(formatted, str):
            lines = formatted.splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("⎿"):
                    # This is a result line
                    result_text = stripped.lstrip("⎿").strip()
                    if result_text:
                        summary_lines.append(result_text)
                        self._run_on_ui(self.conversation.add_tool_result, result_text)
        else:
            self._run_on_ui(self.conversation.write, formatted)
            if hasattr(formatted, "renderable") and hasattr(formatted, "title"):
                # Panels typically summarize tool output in title/body; try to capture text
                renderable = getattr(formatted, "renderable", None)
                if isinstance(renderable, str):
                    summary_lines.append(renderable.strip())

        if summary_lines and self.chat_app and hasattr(self.chat_app, "record_tool_summary"):
            self._run_on_ui(self.chat_app.record_tool_summary, tool_name, normalized_args, summary_lines.copy())

        if self.chat_app and hasattr(self.chat_app, "resume_reasoning_spinner"):
            self._run_on_ui(self.chat_app.resume_reasoning_spinner)

    def _normalize_arguments(self, tool_args: Any) -> Dict[str, Any]:
        """Ensure tool arguments are represented as a dictionary."""

        if isinstance(tool_args, dict):
            return tool_args

        if isinstance(tool_args, str):
            try:
                parsed = json.loads(tool_args)
                if isinstance(parsed, dict):
                    return parsed
                return {"value": parsed}
            except json.JSONDecodeError:
                return {"value": tool_args}

        return {"value": tool_args}

    def _format_arg_for_display(self, value: Any) -> str:
        """Format a single argument for display in tool call.
        
        Args:
            value: The argument value
            
        Returns:
            Formatted string representation
        """
        if value is None:
            return "None"
        
        if isinstance(value, str):
            # For strings, show a preview if long
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return repr(value)
        
        # For other types, use standard repr but limit length
        value_repr = repr(value)
        if len(value_repr) > 80:
            return value_repr[:77] + "..."
        return value_repr

    def _run_on_ui(self, func, *args, **kwargs) -> None:
        """Execute a function on the Textual UI thread and WAIT for completion."""
        from concurrent.futures import Future

        if self._app is not None:
            # Create a future to wait for completion
            future = Future()

            def wrapper():
                try:
                    result = func(*args, **kwargs)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)

            # Schedule on UI thread
            self._app.call_from_thread(wrapper)

            # BLOCK until UI update completes (max 5 seconds timeout)
            try:
                future.result(timeout=5.0)
            except Exception:
                pass  # Timeout or error - continue anyway
        else:
            func(*args, **kwargs)

    def _run_on_ui_non_blocking(self, func, *args, **kwargs) -> None:
        """Execute a function on the Textual UI thread WITHOUT waiting."""
        if self._app is not None:
            # Schedule on UI thread but don't wait
            self._app.call_from_thread(func, *args, **kwargs)
        else:
            func(*args, **kwargs)
