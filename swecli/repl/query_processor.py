"""Query processing for REPL."""

import json
import random
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console
    from swecli.core.management import ModeManager, SessionManager, OperationMode
    from swecli.core.monitoring import TaskMonitor
    from swecli.core.approval import ApprovalManager
    from swecli.core.management import UndoManager
    from swecli.tools.file_ops import FileOperations
    from swecli.ui.formatters import OutputFormatter
    from swecli.ui.components.status_line import StatusLine
    from swecli.models.config import Config
    from swecli.core.management import ConfigManager


class QueryProcessor:
    """Processes user queries using ReAct pattern."""

    # Fancy verbs for the thinking spinner - randomly selected for variety (100 verbs!)
    THINKING_VERBS = [
        "Thinking",
        "Processing",
        "Analyzing",
        "Computing",
        "Synthesizing",
        "Orchestrating",
        "Crafting",
        "Brewing",
        "Composing",
        "Contemplating",
        "Formulating",
        "Strategizing",
        "Architecting",
        "Designing",
        "Manifesting",
        "Conjuring",
        "Weaving",
        "Pondering",
        "Calculating",
        "Deliberating",
        "Ruminating",
        "Meditating",
        "Scheming",
        "Envisioning",
        "Imagining",
        "Conceptualizing",
        "Ideating",
        "Brainstorming",
        "Innovating",
        "Engineering",
        "Assembling",
        "Constructing",
        "Building",
        "Forging",
        "Molding",
        "Sculpting",
        "Fashioning",
        "Shaping",
        "Rendering",
        "Materializing",
        "Realizing",
        "Actualizing",
        "Executing",
        "Implementing",
        "Deploying",
        "Launching",
        "Initiating",
        "Activating",
        "Energizing",
        "Catalyzing",
        "Accelerating",
        "Optimizing",
        "Refining",
        "Polishing",
        "Perfecting",
        "Enhancing",
        "Augmenting",
        "Amplifying",
        "Boosting",
        "Elevating",
        "Transcending",
        "Transforming",
        "Evolving",
        "Adapting",
        "Morphing",
        "Mutating",
        "Iterating",
        "Recursing",
        "Traversing",
        "Navigating",
        "Exploring",
        "Discovering",
        "Uncovering",
        "Revealing",
        "Illuminating",
        "Deciphering",
        "Decoding",
        "Parsing",
        "Interpreting",
        "Translating",
        "Compiling",
        "Rendering",
        "Generating",
        "Producing",
        "Yielding",
        "Outputting",
        "Emitting",
        "Transmitting",
        "Broadcasting",
        "Propagating",
        "Disseminating",
        "Distributing",
        "Allocating",
        "Assigning",
        "Delegating",
        "Coordinating",
        "Synchronizing",
        "Harmonizing",
        "Balancing",
        "Calibrating",
        "Tuning",
        "Adjusting",
    ]

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

        # UI state trackers
        self._last_latency_ms = None
        self._last_operation_summary = "—"
        self._last_error = None
        self._notification_center = None

    def set_notification_center(self, notification_center):
        """Set notification center for status line rendering.

        Args:
            notification_center: Notification center instance
        """
        self._notification_center = notification_center

    def enhance_query(self, query: str) -> str:
        """Enhance query with file contents if referenced.

        Args:
            query: Original query

        Returns:
            Enhanced query with file contents or @ references stripped
        """
        import re

        # Handle @file references - strip @ prefix so agent understands
        # Pattern: @filename or @path/to/filename (with or without extension)
        # This makes "@app.py" become "app.py" in the query
        enhanced = re.sub(r'@([a-zA-Z0-9_./\-]+)', r'\1', query)

        # Simple heuristic: look for file references and include content
        lower_query = enhanced.lower()
        if any(keyword in lower_query for keyword in ["explain", "what does", "show me"]):
            # Try to extract file paths
            words = enhanced.split()
            for word in words:
                if any(word.endswith(ext) for ext in [".py", ".js", ".ts", ".java", ".go", ".rs"]):
                    try:
                        content = self.file_ops.read_file(word)
                        return f"{enhanced}\n\nFile contents of {word}:\n```\n{content}\n```"
                    except Exception:
                        pass

        return enhanced

    def _prepare_messages(self, query: str, enhanced_query: str, agent) -> list:
        """Prepare messages for LLM API call.

        Args:
            query: Original query
            enhanced_query: Query with file contents or @ references processed
            agent: Agent with system prompt

        Returns:
            List of API messages
        """
        # Get messages for API
        messages = self.session_manager.current_session.to_api_messages() if self.session_manager.current_session else []
        if enhanced_query != query:
            messages[-1]["content"] = enhanced_query

        # Add system prompt if not present
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": agent.system_prompt})

        return messages

    def _call_llm_with_progress(self, agent, messages, task_monitor) -> tuple:
        """Call LLM with progress display.

        Args:
            agent: Agent to use
            messages: Message history
            task_monitor: Task monitor for tracking

        Returns:
            Tuple of (response, latency_ms)
        """
        from swecli.ui.components.task_progress import TaskProgressDisplay
        import time

        # Get random thinking verb
        thinking_verb = random.choice(self.THINKING_VERBS)
        task_monitor.start(thinking_verb, initial_tokens=0)

        # Create progress display with live updates
        progress = TaskProgressDisplay(self.console, task_monitor)
        progress.start()

        # Give display a moment to render before HTTP call
        time.sleep(0.05)

        # Call LLM
        started = time.perf_counter()
        response = agent.call_llm(messages, task_monitor=task_monitor)
        latency_ms = int((time.perf_counter() - started) * 1000)

        # Get LLM description
        llm_description = response.get("content", "")

        # Stop progress and show final status
        progress.stop()
        progress.print_final_status(replacement_message=llm_description)

        return response, latency_ms

    def _execute_tool_call(self, tool_call: dict, tool_registry, approval_manager, undo_manager) -> dict:
        """Execute a single tool call.

        Args:
            tool_call: Tool call specification
            tool_registry: Tool registry
            approval_manager: Approval manager
            undo_manager: Undo manager

        Returns:
            Tool execution result
        """
        from swecli.core.monitoring import TaskMonitor
        from swecli.ui.components.task_progress import TaskProgressDisplay
        from swecli.core.management import OperationMode
        import json

        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])

        # Format tool call display
        tool_call_display = f"{tool_name}({', '.join(f'{k}={repr(v)[:50]}' for k, v in tool_args.items())})"

        # Show progress in PLAN mode
        if self.mode_manager.current_mode == OperationMode.PLAN:
            tool_monitor = TaskMonitor()
            tool_monitor.start(tool_call_display, initial_tokens=0)
            tool_progress = TaskProgressDisplay(self.console, tool_monitor)
            tool_progress.start()
        else:
            # In NORMAL mode, show static symbol before approval
            self.console.print(f"\n⏺ [cyan]{tool_call_display}[/cyan]")
            tool_progress = None

        # Execute tool
        result = tool_registry.execute_tool(
            tool_name,
            tool_args,
            mode_manager=self.mode_manager,
            approval_manager=approval_manager,
            undo_manager=undo_manager,
        )

        # Update state
        self._last_operation_summary = tool_call_display
        if result.get("success"):
            self._last_error = None
        else:
            self._last_error = result.get("error", "Tool execution failed")

        # Stop progress if it was started
        if tool_progress:
            tool_progress.stop()

        # Display result
        panel = self.output_formatter.format_tool_result(tool_name, tool_args, result)
        self.console.print(panel)

        return result

    def _handle_safety_limit(self, agent, messages: list):
        """Handle safety limit reached by requesting summary.

        Args:
            agent: Agent to use
            messages: Message history
        """
        self.console.print(f"\n[yellow]⚠ Safety limit reached. Requesting summary...[/yellow]")
        messages.append({
            "role": "user",
            "content": "Please provide a summary of what you've found and what needs to be done."
        })
        response = agent.call_llm(messages)
        if response.get("content"):
            self.console.print()
            self._print_markdown_message(response["content"])

    def _should_nudge_agent(self, consecutive_reads: int, messages: list) -> bool:
        """Check if agent should be nudged to conclude.

        Args:
            consecutive_reads: Number of consecutive read operations
            messages: Message history

        Returns:
            True if nudge was added
        """
        if consecutive_reads >= 5:
            # Silently nudge the agent without displaying a message
            messages.append({
                "role": "user",
                "content": "Based on what you've seen, please summarize your findings and explain what needs to be done next."
            })
            return True
        return False

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
        from swecli.core.monitoring import TaskMonitor

        # Add user message to session
        user_msg = ChatMessage(role=Role.USER, content=query)
        self.session_manager.add_message(user_msg, self.config.auto_save_interval)

        # Enhance query with file contents
        enhanced_query = self.enhance_query(query)

        # Prepare messages for API
        messages = self._prepare_messages(query, enhanced_query, agent)

        try:
            # ReAct loop: Reasoning → Acting → Observing
            consecutive_reads = 0
            iteration = 0
            SAFETY_LIMIT = 30
            READ_OPERATIONS = {"read_file", "list_files", "search_code"}

            while True:
                iteration += 1

                # Safety check
                if iteration > SAFETY_LIMIT:
                    self._handle_safety_limit(agent, messages)
                    break

                # Call LLM
                task_monitor = TaskMonitor()
                response, latency_ms = self._call_llm_with_progress(agent, messages, task_monitor)
                self._last_latency_ms = latency_ms

                if not response["success"]:
                    self.console.print(f"[red]Error: {response.get('error', 'Unknown error')}[/red]")
                    break

                # Get LLM description and tool calls
                llm_description = response.get("content", "")
                tool_calls = response.get("tool_calls")

                # If no tool calls, task is complete
                if not tool_calls:
                    if llm_description:
                        assistant_msg = ChatMessage(role=Role.ASSISTANT, content=llm_description)
                        self.session_manager.add_message(assistant_msg, self.config.auto_save_interval)
                    else:
                        self.console.print("\n[dim](Task completed)[/dim]")
                    break

                # Add assistant message with tool calls to history
                messages.append({
                    "role": "assistant",
                    "content": llm_description,
                    "tool_calls": tool_calls,
                })

                # Track read-only operations
                all_reads = all(tc["function"]["name"] in READ_OPERATIONS for tc in tool_calls)
                consecutive_reads = consecutive_reads + 1 if all_reads else 0

                # Execute tool calls
                for tool_call in tool_calls:
                    result = self._execute_tool_call(tool_call, tool_registry, approval_manager, undo_manager)

                    # Add tool result to messages
                    tool_result = result.get("output", "") if result["success"] else f"Error: {result.get('error', 'Tool execution failed')}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result,
                    })

                # Check if agent needs nudge
                if self._should_nudge_agent(consecutive_reads, messages):
                    consecutive_reads = 0

            # Show status line
            self._render_status_line()

        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/red]")
            import traceback
            traceback.print_exc()
            self._last_error = str(e)

        return (self._last_operation_summary, self._last_error, self._last_latency_ms)
