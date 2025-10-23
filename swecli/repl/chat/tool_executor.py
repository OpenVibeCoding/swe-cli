"""Tool execution handler for chat interface."""

import asyncio
import json
from typing import TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from swecli.repl.repl import REPL
    from swecli.repl.repl_chat import REPLChatApplication


class ToolExecutor:
    """Handles tool execution with approval and UI feedback."""

    def __init__(
        self,
        repl: "REPL",
        chat_app: "REPLChatApplication",
    ):
        """Initialize tool executor.

        Args:
            repl: REPL instance for tool registry access
            chat_app: Chat application for UI callbacks
        """
        self.repl = repl
        self.chat_app = chat_app

    async def handle_tool_calls(self, tool_calls: list, messages: list) -> None:
        """Handle tool calls from LLM with approval flow.

        Implements post-approval execution:
        1. Identify bash commands that need approval
        2. Show approval prompts cleanly
        3. Execute all tools with approved commands

        Args:
            tool_calls: List of tool calls
            messages: Message history
        """
        from swecli.ui.utils.rich_to_text import rich_to_text_box
        from swecli.models.operation import Operation, OperationType

        # Phase 1: Collect bash commands and get approvals
        bash_approvals = {}  # tool_call_id -> approved (bool)
        bash_edited_commands = {}  # tool_call_id -> edited_command (str)

        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])

            # Check if this is a bash command
            if tool_name == "run_command":
                command = tool_args.get("command", "")

                # Create operation for approval
                operation = Operation(
                    id=str(hash(f"{command}{datetime.now()}")),
                    type=OperationType.BASH_EXECUTE,
                    target=command,
                    parameters={"command": command},
                    created_at=datetime.now(),
                )

                # Request approval
                from pathlib import Path

                working_dir = (
                    str(self.repl.tool_registry.bash_tool.working_dir)
                    if self.repl.tool_registry.bash_tool
                    else "."
                )

                # Call approval - async to work with event loop
                approval_result = await self.repl.approval_manager.request_approval(
                    operation=operation,
                    preview=f"Execute: {command}",
                    command=command,
                    working_dir=working_dir,
                    force_prompt=True,
                )

                # Store approval decision
                bash_approvals[tool_call["id"]] = approval_result.approved

                # Store edited command if user edited it
                if approval_result.edited_content:
                    bash_edited_commands[tool_call["id"]] = approval_result.edited_content
                    final_command = approval_result.edited_content
                else:
                    final_command = command

                # If user cancelled, stop processing
                if not approval_result.approved:
                    self.chat_app.add_assistant_message("\033[31m⏺ Interrupted by user (ESC)\033[0m")
                    # Set interrupt flag to stop the main loop
                    self.chat_app._interrupt_requested = True
                    self.chat_app._interrupt_shown = True  # We already showed the interrupted message
                    return
                else:
                    # Add to pre-approved set so execution doesn't prompt again
                    self.repl.approval_manager.pre_approved_commands.add(final_command)

        # Phase 2: Execute all tools
        for tool_call in tool_calls:
            # Check for interrupt before starting each tool
            if self.chat_app._interrupt_requested:
                if not self.chat_app._interrupt_shown:
                    tool_call_display = self._format_tool_call(
                        tool_call["function"]["name"],
                        json.loads(tool_call["function"]["arguments"])
                    )
                    self._show_interrupted_message(tool_call_display)
                    self.chat_app._interrupt_shown = True  # Mark as shown
                return

            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])

            # Override command with edited version if user edited it
            if tool_call["id"] in bash_edited_commands:
                tool_args["command"] = bash_edited_commands[tool_call["id"]]

            # Format tool call display
            tool_call_display = self._format_tool_call(tool_name, tool_args)

            # Show animated spinner during tool execution
            self.chat_app._execution_state = "executing_tool"
            self.chat_app._current_tool_display = tool_call_display
            self.chat_app._start_spinner(tool_call_display)

            # Execute tool (in thread to not block UI) with interrupt checking
            try:
                # Create a wrapper that checks for interrupts during execution
                def execute_with_interrupt_check():
                    # Check if interrupt was requested before starting
                    if self.chat_app._interrupt_requested:
                        return {"success": False, "error": "Interrupted by user"}

                    # Execute the tool
                    result = self.repl.tool_registry.execute_tool(
                        tool_name,
                        tool_args,
                        mode_manager=self.repl.mode_manager,
                        approval_manager=self.repl.approval_manager,
                        undo_manager=self.repl.undo_manager,
                    )

                    return result

                # Create the tool execution task
                tool_task = asyncio.create_task(asyncio.to_thread(execute_with_interrupt_check))

                # Poll for interrupts while tool is running (check every 50ms for fast response)
                while not tool_task.done():
                    if self.chat_app._interrupt_requested:
                        # Cancel the tool task
                        tool_task.cancel()
                        try:
                            await tool_task
                        except asyncio.CancelledError:
                            pass
                        return
                    # Short sleep to not consume CPU
                    await asyncio.sleep(0.05)  # 50ms polling for very responsive interrupts

                # Get the result
                result = await tool_task

                # Stop spinner
                self.chat_app._stop_spinner()

                # Check if tool was interrupted during execution
                if (not result.get("success") and
                    result.get("error") == "Interrupted by user"):
                    if not self.chat_app._interrupt_shown:
                        self._show_interrupted_message(tool_call_display)
                        self.chat_app._interrupt_shown = True  # Mark as shown
                    self.chat_app._execution_state = None
                    self.chat_app._current_tool_display = None
                    return

                # Check if interrupted right after tool completes
                if self.chat_app._interrupt_requested:
                    if not self.chat_app._interrupt_shown:
                        self._show_interrupted_message(tool_call_display)
                        self.chat_app._interrupt_shown = True  # Mark as shown
                    self.chat_app._execution_state = None
                    self.chat_app._current_tool_display = None
                    return

                self.chat_app._execution_state = None
                self.chat_app._current_tool_display = None

                # Display tool result
                self._display_tool_result(tool_call_display, tool_name, tool_args, result)

                # Add tool result to messages (for LLM context)
                tool_result = (
                    result.get("output", "")
                    if result["success"]
                    else f"Error: {result.get('error', 'Tool execution failed')}"
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result,
                    }
                )

            except Exception as e:
                # Stop spinner if running
                self.chat_app._stop_spinner()
                self.chat_app._execution_state = None
                self.chat_app._current_tool_display = None

                error_box = f"┌─ Error ──────────────────────\n"
                error_box += f"│ ❌ Exception: {str(e)}\n"
                error_box += f"└──────────────────────────────"

                self.chat_app.add_assistant_message(error_box)

    def _format_tool_call(self, tool_name: str, tool_args: dict) -> str:
        """Format tool call display with arguments.

        Args:
            tool_name: Name of the tool
            tool_args: Tool arguments

        Returns:
            Formatted tool call string
        """
        def format_arg_value(k, v):
            """Format argument value elegantly."""
            # For content parameters (long strings), show summary
            if k in ("content", "new_string", "old_string", "text") and isinstance(v, str):
                line_count = v.count("\n") + 1
                char_count = len(v)
                if char_count > 80:
                    return f"<{char_count} chars, {line_count} lines>"
                # For shorter content, show first line
                first_line = v.split("\n")[0][:50]
                if len(v) > 50:
                    return f"'{first_line}...'"
                return repr(v)

            # For other values, use repr but truncate if too long
            v_str = repr(v)
            if len(v_str) > 100:
                return v_str[:97] + "..."
            return v_str

        if tool_args:
            args_str = ", ".join(f"{k}={format_arg_value(k, v)}" for k, v in tool_args.items())
            return f"{tool_name}({args_str})"
        else:
            return f"{tool_name}()"

    def _show_interrupted_message(self, tool_call_display: str):
        """Show interrupted message for tool execution.

        Args:
            tool_call_display: Formatted tool call string
        """
        from rich.console import Console
        from io import StringIO

        # Show the tool call that was interrupted
        string_io = StringIO()
        temp_console = Console(
            file=string_io, force_terminal=True, legacy_windows=False
        )
        temp_console.print(f"[green]⏺[/green] [cyan]{tool_call_display}[/cyan]", end="")
        colored_tool_call = string_io.getvalue()

        # Create interrupted box
        interrupted_box = "┌─ Interrupted ────────────────\n"
        interrupted_box += "│ \033[31m⏺ Interrupted by user (ESC)\033[0m\n"
        interrupted_box += "└──────────────────────────────"

        combined_message = f"{colored_tool_call}\n{interrupted_box}"
        self.chat_app.add_assistant_message(combined_message)

    def _display_tool_result(self, tool_call_display: str, tool_name: str, tool_args: dict, result: dict):
        """Display tool execution result.

        Args:
            tool_call_display: Formatted tool call string
            tool_name: Name of the tool
            tool_args: Tool arguments
            result: Tool execution result
        """
        from rich.console import Console
        from io import StringIO
        from swecli.ui.utils.rich_to_text import rich_to_text_box

        # Add tool call display with green ⏺ and cyan tool name
        string_io = StringIO()
        temp_console = Console(file=string_io, force_terminal=True, legacy_windows=False)
        temp_console.print(f"[green]⏺[/green] [cyan]{tool_call_display}[/cyan]", end="")
        colored_tool_call = string_io.getvalue()

        # Format tool result using existing OutputFormatter
        panel = self.repl.output_formatter.format_tool_result(
            tool_name=tool_name, tool_args=tool_args, result=result
        )

        # Convert Rich Panel to plain text box for chat display
        content_width = self.chat_app._get_content_width()
        tool_text = rich_to_text_box(panel, width=content_width)

        # Combine tool call and result
        combined_message = f"{colored_tool_call}\n{tool_text}"
        self.chat_app.add_assistant_message(combined_message)
