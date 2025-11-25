"""Query processing for REPL."""

import json
import os
import random
from datetime import datetime
from typing import TYPE_CHECKING, Iterable

from swecli.core.context_management import (
    Playbook,
    AgentResponse,
    Reflector,
    Curator,
    ReflectorOutput,
    CuratorOutput,
)
from swecli.ui_textual.utils.tool_display import format_tool_call

# Import refactored modules
from swecli.repl.query_enhancer import QueryEnhancer
from swecli.repl.llm_caller import LLMCaller
from swecli.repl.tool_executor import ToolExecutor
from swecli.repl.ace_integration import ACEIntegration
from swecli.repl.react_loop import ReActController
from swecli.repl.react_executor import ReActExecutor

if TYPE_CHECKING:
    from rich.console import Console
    from swecli.core.management import ModeManager, SessionManager
    from swecli.core.approval import ApprovalManager
    from swecli.core.management import UndoManager
    from swecli.tools.file_ops import FileOperations
    from swecli.ui_textual.formatters_internal.output_formatter import OutputFormatter
    from swecli.ui_textual.components import StatusLine
    from swecli.models.config import Config
    from swecli.core.management import ConfigManager
    from swecli.models.message import ToolCall


class QueryProcessor:
    """Processes user queries using ReAct pattern."""

    def __init__(
        self,
        console: "Console",
        session_manager: "SessionManager",
        config: "Config",
        config_manager: "ConfigManager",
        mode_manager: "ModeManager",
        file_ops: "FileOperations",
        output_formatter: "OutputFormatter",
        status_line: "StatusLine",
        message_printer_callback,
        todo_handler=None,
    ):
        """Initialize query processor.

        Args:
            console: Rich console for output
            session_manager: Session manager for message tracking
            config: Configuration
            config_manager: Configuration manager
            mode_manager: Mode manager for current mode
            file_ops: File operations for query enhancement
            output_formatter: Output formatter for tool results
            status_line: Status line renderer
            message_printer_callback: Callback to print markdown messages
            todo_handler: Optional todo handler for todo completion tracking
        """
        self.console = console
        self.session_manager = session_manager
        self.config = config
        self.config_manager = config_manager
        self.mode_manager = mode_manager
        self.file_ops = file_ops
        self.output_formatter = output_formatter
        self.status_line = status_line
        self._print_markdown_message = message_printer_callback
        self.todo_handler = todo_handler

        # Initialize refactored modules
        self.query_enhancer = QueryEnhancer(file_ops, session_manager, config, console)
        self.llm_caller = LLMCaller(console)
        self.tool_executor = ToolExecutor(console, output_formatter, mode_manager, session_manager)
        self.ace_integration = ACEIntegration()
        self.react_controller = ReActController(console)
        self.react_controller._print_markdown_message = message_printer_callback

        # Initialize ReAct executor for loop execution
        self.react_executor = ReActExecutor(
            console=console,
            session_manager=session_manager,
            config=config,
            mode_manager=mode_manager,
            llm_caller=self.llm_caller,
            tool_executor=self.tool_executor,
            react_controller=self.react_controller,
            message_printer_callback=message_printer_callback,
        )

        # UI state trackers
        self._last_latency_ms = None
        self._last_operation_summary = "—"
        self._last_error = None
        self._notification_center = None

        # Interrupt support - track current task monitor
        self._current_task_monitor: Optional[Any] = None

        # ACE Components - Initialize on first use (lazy loading)
        self._ace_reflector: Optional[Reflector] = None
        self._ace_curator: Optional[Curator] = None
        self._last_agent_response: Optional[AgentResponse] = None
        self._execution_count = 0

    def set_notification_center(self, notification_center):
        """Set notification center for status line rendering.

        Args:
            notification_center: Notification center instance
        """
        self._notification_center = notification_center

    def _format_messages_summary(self, messages: list, max_preview_len: int = 60) -> str:
        """Format a summary of messages for debug display.

        Args:
            messages: List of message dictionaries
            max_preview_len: Maximum length for content preview

        Returns:
            Formatted summary string
        """
        return QueryEnhancer.format_messages_summary(messages, max_preview_len)

    def request_interrupt(self) -> bool:
        """Request interrupt of currently running task (LLM call or tool execution).

        Returns:
            True if interrupt was requested, False if no task is running
        """
        # Try LLM caller first, then tool executor
        if self.llm_caller.request_interrupt():
            return True
        if self.tool_executor.request_interrupt():
            return True
        return False

    def _init_ace_components(self, agent):
        """Initialize ACE components lazily on first use.

        Args:
            agent: Agent with LLM client
        """
        if self._ace_reflector is None:
            # Initialize ACE components and update tool executor
            self._ace_reflector, self._ace_curator = self.ace_integration.initialize_components(agent)
            self.tool_executor.set_ace_components(self._ace_reflector, self._ace_curator)

    def enhance_query(self, query: str) -> str:
        """Enhance query with file contents if referenced.

        Root cause fix: ANY @file reference automatically triggers content injection.
        No keyword matching needed - deterministic and universal.

        Args:
            query: Original query

        Returns:
            Enhanced query with file contents or @ references stripped
        """
        return self.query_enhancer.enhance_query(query)

    def _prepare_messages(self, query: str, enhanced_query: str, agent) -> list:
        """Prepare messages for LLM API call.

        Args:
            query: Original query
            enhanced_query: Query with file contents or @ references processed
            agent: Agent with system prompt

        Returns:
            List of API messages
        """
        return self.query_enhancer.prepare_messages(query, enhanced_query, agent)

    def _call_llm_with_progress(self, agent, messages, task_monitor) -> tuple:
        """Call LLM with progress display.

        Args:
            agent: Agent to use
            messages: Message history
            task_monitor: Task monitor for tracking

        Returns:
            Tuple of (response, latency_ms)
        """
        return self.llm_caller.call_llm_with_progress(agent, messages, task_monitor)

    def _record_tool_learnings(
        self,
        query: str,
        tool_call_objects: Iterable["ToolCall"],
        outcome: str,
        agent,
    ) -> None:
        """Use ACE Reflector and Curator to evolve playbook from tool execution.

        This implements the full ACE workflow:
        1. Reflector analyzes what happened (LLM-powered)
        2. Curator decides playbook changes (delta operations)
        3. Apply deltas to evolve playbook

        Args:
            query: User's query
            tool_call_objects: Tool calls that were executed
            outcome: "success", "error", or "partial"
            agent: Agent with LLM client (for ACE initialization)
        """
        # Initialize ACE components if needed
        self._init_ace_components(agent)

        # Delegate to tool executor
        self.tool_executor.record_tool_learnings(query, tool_call_objects, outcome, agent)

    def _format_tool_feedback(self, tool_calls: list, outcome: str) -> str:
        """Format tool execution results as feedback string for ACE Reflector.

        Args:
            tool_calls: List of ToolCall objects with results
            outcome: "success", "error", or "partial"

        Returns:
            Formatted feedback string
        """
        return self.tool_executor._format_tool_feedback(tool_calls, outcome)

    def _execute_tool_call(self, tool_call: dict, tool_registry, approval_manager, undo_manager, tool_call_display: str = None) -> dict:
        """Execute a single tool call.

        Args:
            tool_call: Tool call specification
            tool_registry: Tool registry
            approval_manager: Approval manager
            undo_manager: Undo manager
            tool_call_display: Pre-formatted display string (optional, will format if not provided)

        Returns:
            Tool execution result
        """
        result = self.tool_executor.execute_tool_call(
            tool_call, tool_registry, approval_manager, undo_manager, tool_call_display
        )

        # Update local state for status line rendering
        import json
        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])
        if tool_call_display is None:
            tool_call_display = format_tool_call(tool_name, tool_args)

        self._last_operation_summary = tool_call_display
        if result.get("success"):
            self._last_error = None
        else:
            self._last_error = result.get("error", "Tool execution failed")

        return result

    def _handle_safety_limit(self, agent, messages: list):
        """Handle safety limit reached by requesting summary.

        Args:
            agent: Agent to use
            messages: Message history
        """
        self.react_controller.handle_safety_limit(agent, messages)

    def _should_nudge_agent(self, consecutive_reads: int, messages: list) -> bool:
        """Check if agent should be nudged to conclude.

        Args:
            consecutive_reads: Number of consecutive read operations
            messages: Message history

        Returns:
            True if nudge was added
        """
        return self.react_controller.should_nudge_agent(consecutive_reads, messages)

    def _render_status_line(self):
        """Render the status line with current context."""
        total_tokens = self.session_manager.current_session.total_tokens() if self.session_manager.current_session else 0
        self.status_line.render(
            model=self.config.model,
            working_dir=self.config_manager.working_dir,
            tokens_used=total_tokens,
            tokens_limit=self.config.max_context_tokens,
            mode=self.mode_manager.current_mode.value.upper(),
            latency_ms=self._last_latency_ms,
            key_hints=[
                ("Esc S", "Status detail"),
                ("Esc C", "Context"),
                ("Esc N", "Notifications"),
                ("/help", "Commands"),
            ],
            notifications=[note.summary() for note in self._notification_center.latest(2)] if self._notification_center and self._notification_center.has_items() else None,
        )

    def process_query(
        self,
        query: str,
        agent,
        tool_registry,
        approval_manager: "ApprovalManager",
        undo_manager: "UndoManager",
    ) -> tuple:
        """Process a user query with AI using ReAct pattern.

        Args:
            query: User query
            agent: Agent to use for LLM calls
            tool_registry: Tool registry for executing tools
            approval_manager: Approval manager for user confirmations
            undo_manager: Undo manager for operation history

        Returns:
            Tuple of (last_operation_summary, last_error, last_latency_ms)
        """
        from swecli.models.message import ChatMessage, Role

        # Add user message to session
        user_msg = ChatMessage(role=Role.USER, content=query)
        self.session_manager.add_message(user_msg, self.config.auto_save_interval)

        # Initialize ACE components if needed
        self._init_ace_components(agent)

        # Enhance query with file contents
        enhanced_query = self.enhance_query(query)

        # Prepare messages for API
        messages = self._prepare_messages(query, enhanced_query, agent)

        # Execute ReAct loop (non-callback mode)
        result = self.react_executor.execute_react_loop(
            messages=messages,
            agent=agent,
            tool_registry=tool_registry,
            approval_manager=approval_manager,
            undo_manager=undo_manager,
            query=query,
            ui_callback=None,  # Non-callback mode
        )

        # Update local state from executor
        self._last_operation_summary, self._last_error, self._last_latency_ms = result

        # Show status line
        self._render_status_line()

        return result

    def process_query_with_callback(
        self,
        query: str,
        agent,
        tool_registry,
        approval_manager: "ApprovalManager",
        undo_manager: "UndoManager",
        ui_callback,
    ) -> tuple:
        """Process a user query with AI using ReAct pattern with UI callback for real-time updates.

        Args:
            query: User query
            agent: Agent to use for LLM calls
            tool_registry: Tool registry for executing tools
            approval_manager: Approval manager for user confirmations
            undo_manager: Undo manager for operation history
            ui_callback: UI callback for real-time tool display

        Returns:
            Tuple of (last_operation_summary, last_error, last_latency_ms)
        """
        from swecli.models.message import ChatMessage, Role

        # Debug: Query processing started
        if ui_callback and hasattr(ui_callback, 'on_debug'):
            ui_callback.on_debug(f"Starting query processing: '{query[:50]}...'", "QUERY")

        # Add user message to session
        user_msg = ChatMessage(role=Role.USER, content=query)
        self.session_manager.add_message(user_msg, self.config.auto_save_interval)

        # Initialize ACE components if needed
        self._init_ace_components(agent)

        # Enhance query with file contents
        enhanced_query = self.enhance_query(query)
        if ui_callback and hasattr(ui_callback, 'on_debug'):
            ui_callback.on_debug("Query enhanced", "QUERY")

        # Prepare messages for API
        messages = self._prepare_messages(query, enhanced_query, agent)

        # Execute ReAct loop (callback mode)
        result = self.react_executor.execute_react_loop(
            messages=messages,
            agent=agent,
            tool_registry=tool_registry,
            approval_manager=approval_manager,
            undo_manager=undo_manager,
            query=query,
            ui_callback=ui_callback,
        )

        # Update local state from executor
        self._last_operation_summary, self._last_error, self._last_latency_ms = result

        # Show status line
        self._render_status_line()

        return result
