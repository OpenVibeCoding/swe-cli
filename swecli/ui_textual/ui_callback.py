"""UI callback for real-time tool call display in Textual UI."""

from __future__ import annotations

import json
from typing import Any, Dict

from swecli.ui_textual.formatters.style_formatter import StyleFormatter
from swecli.ui_textual.utils.tool_display import build_tool_call_text


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
        self.formatter = StyleFormatter()
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

    def on_interrupt(self) -> None:
        """Called when execution is interrupted by user.

        Displays the interrupt message directly by replacing the blank line after user prompt.
        """
        # Stop spinner first - this removes spinner lines but leaves the blank line after user prompt
        if hasattr(self.conversation, 'stop_spinner'):
            self._run_on_ui(self.conversation.stop_spinner)
        if self.chat_app and hasattr(self.chat_app, "_stop_local_spinner"):
            self._run_on_ui(self.chat_app._stop_local_spinner)

        # The key insight: after user message, there's a blank line (added by add_user_message)
        # After stopping spinner, this blank line is the last line
        # We need to remove it using _truncate_from to properly update widget state
        def write_interrupt_replacing_blank_line():
            from rich.text import Text

            # Check if we have lines and last line is blank
            if hasattr(self.conversation, 'lines') and len(self.conversation.lines) > 0:
                # Check if last line is blank
                last_line = self.conversation.lines[-1]

                # RichLog stores lines as Strip objects, not Text objects
                # A blank line is a Strip with empty segments or a single empty Segment
                is_blank = False

                # Check if it's a Strip object with empty content
                if hasattr(last_line, '_segments'):
                    segments = last_line._segments
                    if len(segments) == 0:
                        is_blank = True
                    elif len(segments) == 1 and segments[0].text == '':
                        is_blank = True
                elif hasattr(last_line, 'plain'):
                    # Fallback for Text objects
                    if last_line.plain.strip() == "":
                        is_blank = True

                if is_blank:
                    # Use _truncate_from to properly remove the blank line and update widget state
                    if hasattr(self.conversation, '_truncate_from'):
                        self.conversation._truncate_from(len(self.conversation.lines) - 1)

            # Now write the interrupt message using shared utility
            from swecli.ui_textual.utils.interrupt_utils import create_interrupt_text, THINKING_INTERRUPT_MESSAGE
            interrupt_line = create_interrupt_text(THINKING_INTERRUPT_MESSAGE)
            self.conversation.write(interrupt_line)

        self._run_on_ui(write_interrupt_replacing_blank_line)

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

        # Display tool call (BLOCKING - ensure line is added)
        if hasattr(self.conversation, 'add_tool_call'):
            display_text = build_tool_call_text(tool_name, normalized_args)
            self._run_on_ui(self.conversation.add_tool_call, display_text)

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

        # Skip displaying "Operation cancelled by user" errors
        # These are already shown by the approval controller interrupt message
        if not result.get("success") and result.get("error") == "Operation cancelled by user":
            return

        # Format the result using the Claude-style formatter
        normalized_args = self._normalize_arguments(tool_args)
        formatted = self.formatter.format_tool_result(tool_name, normalized_args, result)

        # Extract the result line(s) from the formatted output
        summary_lines: list[str] = []
        collected_lines: list[str] = []
        if isinstance(formatted, str):
            lines = formatted.splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("⎿"):
                    # This is a result line
                    result_text = stripped.lstrip("⎿").strip()
                    if result_text:
                        summary_lines.append(result_text)
                        collected_lines.append(result_text)
        else:
            self._run_on_ui(self.conversation.write, formatted)
            if hasattr(formatted, "renderable") and hasattr(formatted, "title"):
                # Panels typically summarize tool output in title/body; try to capture text
                renderable = getattr(formatted, "renderable", None)
                if isinstance(renderable, str):
                    summary_lines.append(renderable.strip())

        if collected_lines:
            block = "\n".join(collected_lines)
            self._run_on_ui(self.conversation.add_tool_result, block)

        if summary_lines and self.chat_app and hasattr(self.chat_app, "record_tool_summary"):
            self._run_on_ui(self.chat_app.record_tool_summary, tool_name, normalized_args, summary_lines.copy())

        if self.chat_app and hasattr(self.chat_app, "resume_reasoning_spinner"):
            self._run_on_ui(self.chat_app.resume_reasoning_spinner)

    def _normalize_arguments(self, tool_args: Any) -> Dict[str, Any]:
        """Ensure tool arguments are represented as a dictionary and normalize URLs for display."""

        if isinstance(tool_args, dict):
            result = tool_args
        elif isinstance(tool_args, str):
            try:
                parsed = json.loads(tool_args)
                if isinstance(parsed, dict):
                    result = parsed
                else:
                    result = {"value": parsed}
            except json.JSONDecodeError:
                result = {"value": tool_args}
        else:
            result = {"value": tool_args}

        # Normalize URLs for display (fix common malformations)
        if "url" in result and isinstance(result["url"], str):
            url = result["url"].strip()
            # Fix: https:/domain.com → https://domain.com
            if url.startswith("https:/") and not url.startswith("https://"):
                result["url"] = url.replace("https:/", "https://", 1)
            elif url.startswith("http:/") and not url.startswith("http://"):
                result["url"] = url.replace("http:/", "http://", 1)
            # Add protocol if missing
            elif not url.startswith(("http://", "https://")):
                result["url"] = f"https://{url}"

        return result

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

    def _should_skip_due_to_interrupt(self) -> bool:
        """Check if we should skip UI operations due to interrupt.

        Returns:
            True if an interrupt is pending and we should skip UI updates
        """
        if self.chat_app and hasattr(self.chat_app, 'runner'):
            runner = self.chat_app.runner
            if hasattr(runner, 'query_processor'):
                query_processor = runner.query_processor
                if hasattr(query_processor, 'task_monitor'):
                    task_monitor = query_processor.task_monitor
                    if task_monitor and hasattr(task_monitor, 'should_interrupt'):
                        return task_monitor.should_interrupt()
        return False

    def on_debug(self, message: str, prefix: str = "DEBUG") -> None:
        """Called to display debug information about execution flow.

        Args:
            message: The debug message to display
            prefix: Optional prefix for categorizing debug messages
        """
        # Skip debug if interrupted
        if self._should_skip_due_to_interrupt():
            return

        # Display debug message in conversation (non-blocking)
        if hasattr(self.conversation, 'add_debug_message'):
            self._run_on_ui_non_blocking(self.conversation.add_debug_message, message, prefix)

    def _refresh_todo_panel(self) -> None:
        """Refresh the todo panel with latest state."""
        if not self.chat_app:
            return

        try:
            from swecli.ui_textual.widgets.todo_panel import TodoPanel
            panel = self.chat_app.query_one("#todo-panel", TodoPanel)
            self._run_on_ui(panel.refresh_display)
        except Exception:
            # Panel not found or not initialized yet
            pass
