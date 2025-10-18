"""REPL with integrated ChatApplication for split-screen UI."""

import asyncio
import time
from pathlib import Path
from typing import Optional

from swecli.core.management import ConfigManager, ModeManager, OperationMode, SessionManager
from swecli.core.agents.compact_agent import CompactAgent
from swecli.core.context import ContextTokenMonitor
from swecli.ui.chat_app import ChatApplication
from swecli.ui.utils.rich_to_text import rich_to_text_box
from swecli.models.message import ChatMessage, Role
from swecli.repl.repl import REPL  # Import existing REPL for all the logic
from swecli.repl.chat.spinner import ChatSpinner
from swecli.repl.chat.ui_helpers import ChatUIHelpers
from swecli.repl.chat.context_compactor import ContextCompactor
from swecli.repl.chat.approval_manager import ChatApprovalManager
from swecli.repl.chat.async_query_processor import AsyncQueryProcessor
from swecli.repl.chat.tool_executor import ToolExecutor


class REPLChatApplication(ChatApplication):
    """Chat application customized for REPL with split-screen UI."""

    def __init__(self, repl: REPL):
        """Initialize REPL chat application.

        Args:
            repl: The REPL instance containing all the logic
        """
        self.repl = repl

        # Track current working messages for real-time token counting
        self._current_messages: list = []

        # Context monitoring and compaction
        self.context_monitor = ContextTokenMonitor(
            model=repl.config.model,
            context_limit=256000,  # Full context budget (256k tokens)
            compaction_threshold=0.80,  # Trigger at 80% usage (204.8k tokens) - leaves buffer room
        )
        self.compactor = CompactAgent(repl.config)

        # Initialize parent with autocomplete support
        super().__init__(
            on_message=self._handle_user_message,
            on_exit=self._handle_exit,
            completer=repl.completer,
        )

        # AFTER parent init, add mode switching key binding
        self._add_mode_switching_binding()

        # Initialize spinner (needs conversation and invalidate callback from parent)
        self._spinner = ChatSpinner(
            self.conversation,
            self.safe_invalidate,
            self._update_conversation_buffer
        )

        # Initialize context compactor
        self._context_compactor = ContextCompactor(
            self.context_monitor,
            self.compactor,
            self.repl,
            self._start_spinner,
            self._stop_spinner,
            self.add_assistant_message,
        )

        # Initialize async query processor
        self._async_query_processor = AsyncQueryProcessor(self.repl, self)

        # Initialize tool executor
        self._tool_executor = ToolExecutor(self.repl, self)

        # Show welcome message
        self._show_welcome()

    def _add_mode_switching_binding(self):
        """Add Shift+Tab binding for mode switching."""
        @self.key_bindings.add("s-tab", eager=True)
        def toggle_mode(event):
            """Toggle between PLAN and NORMAL mode."""
            current_mode = self.repl.mode_manager.current_mode

            # Toggle mode
            if current_mode == OperationMode.PLAN:
                new_mode = OperationMode.NORMAL
            else:
                new_mode = OperationMode.PLAN

            self.repl.mode_manager.set_mode(new_mode)

            # Reset automatic approvals when switching modes
            if hasattr(self.repl, "approval_manager") and hasattr(
                self.repl.approval_manager, "reset_auto_approve"
            ):
                self.repl.approval_manager.reset_auto_approve()

            # Keep REPL agent in sync with mode
            if new_mode == OperationMode.PLAN:
                self.repl.agent = self.repl.planning_agent
            else:
                self.repl.agent = self.repl.normal_agent

            # Update status bar (it will refresh on next render)
            self.app.invalidate()

            # Show mode change notification in conversation
            mode_name = new_mode.value.upper()
            mode_desc = self.repl.mode_manager.get_mode_description()
            self.conversation.add_system_message(f"Switched to {mode_name} mode: {mode_desc}")

    def _get_status_text(self):
        """Override to show actual mode with color coding and context percentage.

        This method is called on each render by FormattedTextControl,
        ensuring the mode color and context updates dynamically.
        """
        # Check if we're in exit confirmation mode
        if hasattr(self, '_exit_confirmation_mode') and self._exit_confirmation_mode:
            return [
                ("class:exit-confirmation", "Ctrl + C again to exit"),
            ]

        current_mode = self.repl.mode_manager.current_mode
        mode_name = current_mode.value

        # Choose style and symbol based on mode (Claude Code style)
        if current_mode == OperationMode.PLAN:
            mode_style = "class:mode-plan"
            mode_symbol = "⏸"
        else:
            mode_style = "class:mode-normal"
            mode_symbol = "▶"

        # Calculate context left percentage using accurate token counting
        # Count EVERYTHING sent to API: system prompt + tool schemas + all messages
        # This shows the TRUE token cost to the user
        if self._current_messages or self.repl.session_manager.current_session:
            conversation_tokens = 0

            # 1. Count conversation messages first
            # Count from working messages if available (real-time during agent turn)
            messages_to_count = self._current_messages if self._current_messages else []

            # If no working messages, fall back to session messages
            if not messages_to_count and self.repl.session_manager.current_session:
                session = self.repl.session_manager.current_session
                for msg in session.messages:
                    if hasattr(msg, "content") and msg.content:
                        conversation_tokens += self.context_monitor.count_tokens(msg.content)
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            if hasattr(tool_call, "name"):
                                conversation_tokens += self.context_monitor.count_tokens(
                                    tool_call.name
                                )
                            if hasattr(tool_call, "parameters"):
                                conversation_tokens += self.context_monitor.count_tokens(
                                    str(tool_call.parameters)
                                )
                            if hasattr(tool_call, "result"):
                                conversation_tokens += self.context_monitor.count_tokens(
                                    str(tool_call.result)
                                )
            else:
                # Count from working messages (API format)
                for msg in messages_to_count:
                    # Skip system message (already counted above)
                    if msg.get("role") == "system":
                        continue

                    # Count message content
                    content = msg.get("content", "")
                    if content:
                        conversation_tokens += self.context_monitor.count_tokens(str(content))

                    # Count tool calls
                    if "tool_calls" in msg and msg["tool_calls"]:
                        for tool_call in msg["tool_calls"]:
                            func = tool_call.get("function", {})
                            conversation_tokens += self.context_monitor.count_tokens(
                                func.get("name", "")
                            )
                            conversation_tokens += self.context_monitor.count_tokens(
                                str(func.get("arguments", ""))
                            )

            # Only count baseline if there are actual conversation messages
            # (baseline is only sent to API when we make a call, not at startup)
            if conversation_tokens > 0:
                baseline_tokens = 0

                # Count system prompt (sent with every API call)
                if hasattr(self.repl.agent, "system_prompt"):
                    baseline_tokens += self.context_monitor.count_tokens(
                        self.repl.agent.system_prompt
                    )

                # Count tool schemas (sent with every API call)
                if hasattr(self.repl.agent, "tool_schemas"):
                    import json

                    tool_schemas_str = json.dumps(self.repl.agent.tool_schemas)
                    baseline_tokens += self.context_monitor.count_tokens(tool_schemas_str)

                # Calculate total tokens (baseline + conversation)
                total_tokens = baseline_tokens + conversation_tokens

                # Calculate percentage based on full context limit
                context_limit = self.context_monitor.context_limit
                remaining_tokens = context_limit - total_tokens
                remaining_pct = (remaining_tokens / context_limit * 100) if context_limit > 0 else 0

                # Display full budget usage
                context_display = (
                    f"Context Left: {remaining_pct:.0f}% ({total_tokens}/{context_limit})"
                )
            else:
                # No messages yet - show 100%
                context_limit = self.context_monitor.context_limit
                context_display = f"Context Left: 100% (0/{context_limit})"
        else:
            # No session yet - show 100% with full budget
            context_limit = self.context_monitor.context_limit
            context_display = f"Context Left: 100% (0/{context_limit})"

        # Build status text - elegant Claude Code style with context info
        return [
            ("", f"{mode_symbol} "),
            (mode_style, f"{mode_name} mode"),
            ("", " (shift+tab to cycle) • "),
            ("class:context-info", context_display),
        ]

    def _get_content_width(self) -> int:
        """Get the current terminal width for content rendering."""
        return ChatUIHelpers.get_content_width()

    def _wrap_text(self, text: str, width: int = 76) -> str:
        """Wrap text to specified width, preserving intentional line breaks."""
        return ChatUIHelpers.wrap_text(text, width)

    def _render_markdown_message(self, content: str) -> Optional[str]:
        """Render Markdown output as wrapped plain text for the chat window."""
        return ChatUIHelpers.render_markdown_message(content, self._get_content_width())

    def _start_spinner(self, text: str) -> None:
        """Start animated spinner with given text.

        Args:
            text: Text to display after spinner
        """
        self._spinner.start(text, self.add_assistant_message)

    def _stop_spinner(self) -> None:
        """Stop the animated spinner."""
        self._spinner.stop()

    def _reset_processing_state(self) -> None:
        """Reset processing state flags and cancel any running tasks."""
        # Cancel any running LLM task
        if hasattr(self, "_current_llm_task"):
            task = self._current_llm_task
            if task and not task.done():
                task.cancel()
            self._current_llm_task = None

        # Reset processing flags
        self._current_messages = []
        self._is_processing = False
        self._interrupt_requested = False
        self._interrupt_shown = False
        self._execution_state = None
        self._current_tool_display = None

    def add_assistant_message(self, content: str) -> None:
        """Override to wrap text before adding (but not Rich panels)."""
        # Check if content is a Rich panel (contains box drawing chars)
        # Include ALL Unicode box drawing characters
        box_chars = [
            "╭",
            "╰",
            "╯",
            "╮",  # Rounded corners
            "┌",
            "┐",
            "└",
            "┘",  # Light corners
            "╔",
            "╗",
            "╚",
            "╝",  # Double corners
            "┏",
            "┓",
            "┗",
            "┛",  # Heavy corners
            "│",
            "║",
            "┃",  # Vertical lines
            "─",
            "═",
            "━",  # Horizontal lines
            "├",
            "┤",
            "┬",
            "┴",
            "┼",  # Light connectors
            "╠",
            "╣",
            "╦",
            "╩",
            "╬",  # Double connectors
        ]
        is_rich_panel = any(char in content for char in box_chars)

        if is_rich_panel:
            # Don't wrap Rich panels - they're already formatted
            super().add_assistant_message(content)
        else:
            # Wrap plain text content to terminal width
            content_width = self._get_content_width()
            wrapped_content = self._wrap_text(content, width=content_width)
            super().add_assistant_message(wrapped_content)

    def _show_welcome(self) -> None:
        """Show compact welcome banner using shared welcome module."""
        from rich.console import Console
        from io import StringIO
        from swecli.ui.components.welcome import WelcomeMessage

        # Helper to render Rich markup to ANSI
        def rich_markup_to_ansi(markup: str) -> str:
            string_io = StringIO()
            temp_console = Console(
                file=string_io, width=200, force_terminal=True, legacy_windows=False
            )
            temp_console.print(markup, end="")
            return string_io.getvalue()

        # Get current mode for color coding
        mode = self.repl.mode_manager.current_mode.value.upper()
        mode_color = "green" if mode == "PLAN" else "yellow"

        # Generate welcome content using shared module
        welcome_lines = WelcomeMessage.generate_full_welcome(
            current_mode=self.repl.mode_manager.current_mode,
            working_dir=Path.cwd(),
        )

        # Apply Rich styling and add to conversation
        for line in welcome_lines:
            # Apply styling based on content
            if line.startswith("╔") or line.startswith("║") or line.startswith("╚"):
                styled_line = f"[white]{line}[/white]"
            elif "Essential Commands:" in line:
                styled_line = f"[bold white]{line}[/bold white]"
            elif "/help" in line or "/tree" in line or "/mode" in line:
                # Highlight commands
                styled_line = line.replace("/help", "[cyan]/help[/cyan]")
                styled_line = styled_line.replace("/tree", "[cyan]/tree[/cyan]")
                styled_line = styled_line.replace("/mode plan", "[cyan]/mode plan[/cyan]")
                styled_line = styled_line.replace("/mode normal", "[cyan]/mode normal[/cyan]")
            elif "Shortcuts:" in line:
                styled_line = f"[bold white]{line.split(':')[0]}:[/bold white]"
                rest = line.split(":", 1)[1] if ":" in line else ""
                styled_line += rest.replace("Shift+Tab", "[yellow]Shift+Tab[/yellow]")
                styled_line = styled_line.replace("@file", "[yellow]@file[/yellow]")
                styled_line = styled_line.replace("↑↓", "[yellow]↑↓[/yellow]")
            elif "Session:" in line:
                styled_line = f"[bold white]{line.split(':')[0]}:[/bold white]"
                rest = line.split(":", 1)[1] if ":" in line else ""
                # Color the mode
                if mode in rest:
                    rest = rest.replace(mode, f"[{mode_color}]{mode}[/{mode_color}]")
                styled_line += rest
            else:
                styled_line = line

            self.conversation.add_system_message(rich_markup_to_ansi(styled_line))

        self._update_conversation_buffer()
        # Don't lock input for welcome message - it happens before app.run()
        self.app.invalidate()

    def _handle_user_message(self, text: str) -> None:
        """Handle user message - process through REPL logic.

        Args:
            text: User input text
        """
        # Check for slash commands
        if text.startswith("/"):
            # The user message is already added to conversation by the key binding
            # So we just need to execute the command
            self._handle_command(text)
            return

        # Process as regular query
        self._process_query(text)

    def _handle_command(self, command: str) -> None:
        """Handle slash commands.

        Args:
            command: Command string (e.g. "/help")
        """
        # Delegate to REPL's command handler
        try:
            # More comprehensive output capture - redirect both stdout and stderr
            import sys
            from contextlib import redirect_stdout, redirect_stderr
            from rich.console import Console
            from io import StringIO

            # Create buffers to capture all output
            stdout_buffer = StringIO()
            stderr_buffer = StringIO()
            rich_buffer = StringIO()

            # Create a temporary Rich console with full terminal width
            # Get actual terminal width for console
            import shutil
            terminal_size = shutil.get_terminal_size(fallback=(80, 24))
            console_width = max(terminal_size.columns - 2, 78)  # Reserve space for scrollbar only

            temp_console = Console(
                file=rich_buffer, width=console_width, force_terminal=True
            )

            # Store original outputs
            original_console = self.repl.console
            original_stdout = sys.stdout
            original_stderr = sys.stderr

            # Store original console in command handlers too
            original_mcp_console = getattr(self.repl.mcp_commands, 'console', None)
            original_help_console = getattr(self.repl.help_command, 'console', None)
            original_session_console = getattr(self.repl.session_commands, 'console', None)
            original_file_console = getattr(self.repl.file_commands, 'console', None)
            original_mode_console = getattr(self.repl.mode_commands, 'console', None)

            try:
                # Redirect all outputs
                sys.stdout = stdout_buffer
                sys.stderr = stderr_buffer
                self.repl.console = temp_console

                # Also replace console in command handlers
                if hasattr(self.repl, 'mcp_commands') and hasattr(self.repl.mcp_commands, 'console'):
                    self.repl.mcp_commands.console = temp_console
                if hasattr(self.repl, 'help_command') and hasattr(self.repl.help_command, 'console'):
                    self.repl.help_command.console = temp_console
                if hasattr(self.repl, 'session_commands') and hasattr(self.repl.session_commands, 'console'):
                    self.repl.session_commands.console = temp_console
                if hasattr(self.repl, 'file_commands') and hasattr(self.repl.file_commands, 'console'):
                    self.repl.file_commands.console = temp_console
                if hasattr(self.repl, 'mode_commands') and hasattr(self.repl.mode_commands, 'console'):
                    self.repl.mode_commands.console = temp_console

                # Execute the command through REPL
                self.repl._handle_command(command)

                # Collect output from all sources
                stdout_output = stdout_buffer.getvalue()
                stderr_output = stderr_buffer.getvalue()
                rich_output = rich_buffer.getvalue()

                # Combine all captured output
                all_output = ""
                if stdout_output.strip():
                    all_output += stdout_output
                if stderr_output.strip():
                    all_output += stderr_output
                if rich_output.strip():
                    all_output += rich_output

                # Add to chat if there's output - use system message for commands
                if all_output.strip():
                    self.conversation.add_system_message(all_output)
                    self._update_conversation_buffer()
                    self.app.invalidate()

            finally:
                # Restore all original outputs
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                self.repl.console = original_console

                # Restore original consoles in command handlers
                if hasattr(self.repl, 'mcp_commands') and original_mcp_console is not None:
                    self.repl.mcp_commands.console = original_mcp_console
                if hasattr(self.repl, 'help_command') and original_help_console is not None:
                    self.repl.help_command.console = original_help_console
                if hasattr(self.repl, 'session_commands') and original_session_console is not None:
                    self.repl.session_commands.console = original_session_console
                if hasattr(self.repl, 'file_commands') and original_file_console is not None:
                    self.repl.file_commands.console = original_file_console
                if hasattr(self.repl, 'mode_commands') and original_mode_console is not None:
                    self.repl.mode_commands.console = original_mode_console

                # Force a UI refresh and brief pause to catch any delayed output
                import time
                self.app.invalidate()
                time.sleep(0.1)  # Small delay to catch any immediate async output

        except Exception as e:
            # Show error as system message too
            self.conversation.add_system_message(f"❌ Error executing command: {e}")
            self._update_conversation_buffer()
            self.app.invalidate()

    def _process_query(self, query: str) -> None:
        """Process user query through AI.

        Args:
            query: User query text
        """
        # Add user message to session
        user_msg = ChatMessage(role=Role.USER, content=query)
        self.repl.session_manager.add_message(user_msg, self.repl.config.auto_save_interval)

        # Process asynchronously to not block UI
        asyncio.create_task(self._async_process_query(query))

    async def _async_process_query(self, query: str) -> None:
        """Process query asynchronously - delegates to AsyncQueryProcessor.

        Args:
            query: User query
        """
        await self._async_query_processor.process_query(query)

    async def _handle_tool_calls(self, tool_calls: list, messages: list) -> None:
        """Handle tool calls - delegates to ToolExecutor.

        Args:
            tool_calls: List of tool calls
            messages: Message history
        """
        await self._tool_executor.handle_tool_calls(tool_calls, messages)

    async def _check_and_compact_context(self, messages: list) -> None:
        """Check if context compaction is needed and trigger it.

        Args:
            messages: Current message history
        """
        await self._context_compactor.check_and_compact(messages)
        # Update conversation buffer and invalidate UI after compaction
        self._update_conversation_buffer()
        self.safe_invalidate()

    def _handle_exit(self) -> None:
        """Handle application exit."""
        self.repl._cleanup()


def create_repl_chat(
    config_manager: ConfigManager, session_manager: SessionManager
) -> REPLChatApplication:
    """Create REPL with chat interface.

    Args:
        config_manager: Configuration manager
        session_manager: Session manager

    Returns:
        REPLChatApplication instance
    """
    from swecli.core.management import OperationMode

    # Create standard REPL instance (for all the logic)
    repl = REPL(config_manager, session_manager)

    # Enable bash execution for chat interface
    if hasattr(repl.config, "permissions") and hasattr(repl.config.permissions, "bash"):
        repl.config.permissions.bash.enabled = True
    elif hasattr(repl.config, "enable_bash"):
        repl.config.enable_bash = True

    # Default to NORMAL mode so footer reflects interactive execution semantics
    repl.mode_manager.set_mode(OperationMode.NORMAL)

    # Replace approval manager with chat-friendly one that prompts for bash commands
    repl.approval_manager = ChatApprovalManager(repl.console)

    # Connect to MCP servers (normally done in start() but chat app doesn't call start())
    repl._connect_mcp_servers()

    # Create chat application wrapper
    chat_app = REPLChatApplication(repl)

    # Set chat app reference in approval manager for modal dialogs
    repl.approval_manager.chat_app = chat_app

    return chat_app
