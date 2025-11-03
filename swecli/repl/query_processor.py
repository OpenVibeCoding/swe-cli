"""Query processing for REPL."""

import json
import os
import random
import time
from datetime import datetime
from typing import TYPE_CHECKING, Iterable

from swecli.core.context_management import ExecutionReflector, SessionPlaybook, Strategy
from swecli.ui_textual.utils.tool_display import format_tool_call

if TYPE_CHECKING:
    from rich.console import Console
    from swecli.core.management import ModeManager, SessionManager, OperationMode
    from swecli.core.monitoring import TaskMonitor
    from swecli.core.approval import ApprovalManager
    from swecli.core.management import UndoManager
    from swecli.tools.file_ops import FileOperations
    from swecli.ui.formatters_internal.output_formatter import OutputFormatter
    from swecli.ui.components.status_line import StatusLine
    from swecli.models.config import Config
    from swecli.core.management import ConfigManager
    from swecli.models.message import ToolCall


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

    REFLECTION_WINDOW_SIZE = 5
    MAX_PLAYBOOK_STRATEGIES = 30
    PLAYBOOK_DEBUG_PATH = "/tmp/swecli_debug/playbook_evolution.log"

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
        self.reflector = ExecutionReflector(min_tool_calls=2, min_confidence=0.65)

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
        session = self.session_manager.current_session
        messages: list[dict] = []

        if session:
            messages = session.to_api_messages(window_size=self.REFLECTION_WINDOW_SIZE)
            if enhanced_query != query:
                for entry in reversed(messages):
                    if entry.get("role") == "user":
                        entry["content"] = enhanced_query
                        break
        else:
            messages = []

        system_content = agent.system_prompt
        if session:
            try:
                playbook = session.get_playbook()
                playbook_context = playbook.as_context(max_strategies=self.MAX_PLAYBOOK_STRATEGIES)
                if playbook_context:
                    system_content = f"{system_content.rstrip()}\n\n{playbook_context}"
            except Exception:  # pragma: no cover
                pass

        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_content})
        else:
            messages[0]["content"] = system_content

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

    def _record_tool_learnings(
        self,
        query: str,
        tool_call_objects: Iterable["ToolCall"],
        outcome: str,
    ) -> None:
        """Use the reflector to learn strategies from executed tool calls."""
        session = self.session_manager.current_session
        if not session or not self.reflector:
            return

        tool_calls = list(tool_call_objects)
        if not tool_calls:
            return

        try:
            result = self.reflector.reflect(query=query, tool_calls=tool_calls, outcome=outcome)
        except Exception:  # pragma: no cover
            return

        if not result:
            return

        try:
            playbook: SessionPlaybook = session.get_playbook()
            before = len(playbook.strategies)
            strategy: Strategy = playbook.add_strategy(result.category, result.content)
            session.update_playbook(playbook)

            debug_dir = os.path.dirname(self.PLAYBOOK_DEBUG_PATH)
            os.makedirs(debug_dir, exist_ok=True)
            with open(self.PLAYBOOK_DEBUG_PATH, "a", encoding="utf-8") as log:
                timestamp = datetime.now().isoformat()
                log.write(f"\n{'=' * 60}\n")
                log.write(f"🧠 PLAYBOOK EVOLUTION - {timestamp}\n")
                log.write(f"{'=' * 60}\n")
                log.write(f"Query: {query}\n")
                log.write(f"Outcome: {outcome}\n")
                log.write(f"Strategy Count: {before} -> {len(playbook.strategies)}\n")
                log.write(f"New Strategy ID: {strategy.id}\n")
                log.write(f"Category: {result.category}\n")
                log.write(f"Content: {result.content}\n")
                log.write(f"Confidence: {result.confidence}\n")
                log.write(f"Reasoning: {result.reasoning}\n")
        except Exception:  # pragma: no cover
            return

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
        tool_call_display = format_tool_call(tool_name, tool_args)

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
                    error_text = response.get("error", "Unknown error")
                    self.console.print(f"[red]Error: {error_text}[/red]")
                    self._last_error = error_text
                    fallback = ChatMessage(role=Role.ASSISTANT, content=f"❌ {error_text}")
                    self.session_manager.add_message(fallback, self.config.auto_save_interval)
                    break

                # Get LLM description and tool calls
                llm_description = response.get("content", "")
                tool_calls = response.get("tool_calls")
                has_tool_calls = bool(tool_calls)
                normalized_description = (llm_description or "").strip()

                # If no tool calls, task is complete
                if not has_tool_calls:
                    if not normalized_description:
                        normalized_description = "Warning: model returned no reply."
                    self.console.print(f"\n[dim]{normalized_description}[/dim]")
                    assistant_msg = ChatMessage(role=Role.ASSISTANT, content=normalized_description)
                    self.session_manager.add_message(assistant_msg, self.config.auto_save_interval)
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

                # Persist assistant step with tool calls to session
                from swecli.models.message import ToolCall as ToolCallModel
                tool_call_objects = []
                for tc in tool_calls:
                    tool_result = None
                    tool_error = None
                    for msg in reversed(messages):
                        if msg.get("role") == "tool" and msg.get("tool_call_id") == tc["id"]:
                            content = msg.get("content", "")
                            if content.startswith("Error:"):
                                tool_error = content[6:].strip()
                            else:
                                tool_result = content
                            break

                    tool_call_objects.append(
                        ToolCallModel(
                            id=tc["id"],
                            name=tc["function"]["name"],
                            parameters=json.loads(tc["function"]["arguments"]),
                            result=tool_result,
                            error=tool_error,
                            approved=True,
                        )
                    )

                if normalized_description or tool_call_objects:
                    assistant_msg = ChatMessage(
                        role=Role.ASSISTANT,
                        content=normalized_description or "",
                        tool_calls=tool_call_objects,
                    )
                    self.session_manager.add_message(assistant_msg, self.config.auto_save_interval)

                if tool_call_objects:
                    outcome = "error" if any(tc.error for tc in tool_call_objects) else "success"
                    self._record_tool_learnings(query, tool_call_objects, outcome)

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
        from swecli.core.monitoring import TaskMonitor

        # Notify UI that thinking is starting
        if ui_callback and hasattr(ui_callback, 'on_thinking_start'):
            ui_callback.on_thinking_start()

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
                    error_text = response.get("error", "Unknown error")
                    self.console.print(f"[red]Error: {error_text}[/red]")
                    self._last_error = error_text
                    fallback = ChatMessage(role=Role.ASSISTANT, content=f"❌ {error_text}")
                    self.session_manager.add_message(fallback, self.config.auto_save_interval)
                    if ui_callback and hasattr(ui_callback, 'on_assistant_message'):
                        ui_callback.on_assistant_message(fallback.content)
                    break

                # Get LLM description and tool calls
                llm_description = response.get("content", "")
                tool_calls = response.get("tool_calls")
                has_tool_calls = bool(tool_calls)
                normalized_description = (llm_description or "").strip()

                # Notify UI that thinking is complete
                if ui_callback and hasattr(ui_callback, 'on_thinking_complete'):
                    ui_callback.on_thinking_complete()

                # If no tool calls, task is complete
                if not has_tool_calls:
                    if not normalized_description:
                        normalized_description = "Warning: model returned no reply."
                    if ui_callback and hasattr(ui_callback, 'on_assistant_message'):
                        ui_callback.on_assistant_message(normalized_description)
                    assistant_msg = ChatMessage(role=Role.ASSISTANT, content=normalized_description)
                    self.session_manager.add_message(assistant_msg, self.config.auto_save_interval)
                    break

                # Display assistant's thinking text BEFORE tool execution
                if llm_description and ui_callback and hasattr(ui_callback, 'on_assistant_message'):
                    ui_callback.on_assistant_message(llm_description)

                # Add assistant message with tool calls to history
                messages.append({
                    "role": "assistant",
                    "content": llm_description,
                    "tool_calls": tool_calls,
                })

                # Track read-only operations
                all_reads = all(tc["function"]["name"] in READ_OPERATIONS for tc in tool_calls)
                consecutive_reads = consecutive_reads + 1 if all_reads else 0

                # Execute tool calls with real-time display
                for tool_call in tool_calls:
                    # Notify UI about tool call
                    if ui_callback and hasattr(ui_callback, 'on_tool_call'):
                        ui_callback.on_tool_call(
                            tool_call["function"]["name"],
                            tool_call["function"]["arguments"]
                        )

                    result = self._execute_tool_call(tool_call, tool_registry, approval_manager, undo_manager)

                    # Notify UI about tool result
                    if ui_callback and hasattr(ui_callback, 'on_tool_result'):
                        ui_callback.on_tool_result(
                            tool_call["function"]["name"],
                            tool_call["function"]["arguments"],
                            result
                        )

                    # Add tool result to messages
                    tool_result = result.get("output", "") if result["success"] else f"Error: {result.get('error', 'Tool execution failed')}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result,
                    })

                # Persist assistant step with tool calls to session
                from swecli.models.message import ToolCall as ToolCallModel
                tool_call_objects = []
                for tc in tool_calls:
                    tool_result = None
                    tool_error = None
                    for msg in reversed(messages):
                        if msg.get("role") == "tool" and msg.get("tool_call_id") == tc["id"]:
                            content = msg.get("content", "")
                            if content.startswith("Error:"):
                                tool_error = content[6:].strip()
                            else:
                                tool_result = content
                            break

                    tool_call_objects.append(
                        ToolCallModel(
                            id=tc["id"],
                            name=tc["function"]["name"],
                            parameters=json.loads(tc["function"]["arguments"]),
                            result=tool_result,
                            error=tool_error,
                            approved=True,
                        )
                    )

                assistant_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content=normalized_description or "",
                    tool_calls=tool_call_objects,
                )
                self.session_manager.add_message(assistant_msg, self.config.auto_save_interval)

                if tool_call_objects:
                    outcome = "error" if any(tc.error for tc in tool_call_objects) else "success"
                    self._record_tool_learnings(query, tool_call_objects, outcome)

                # Break on excessive consecutive reads
                if consecutive_reads >= 5:
                    warning = "[yellow]AI is performing multiple read operations. Consider improving the query or providing more specific instructions.[/yellow]"
                    self.console.print(warning)
                    assistant_msg = ChatMessage(role=Role.ASSISTANT, content=warning)
                    self.session_manager.add_message(assistant_msg, self.config.auto_save_interval)
                    break

            # Update status line
            self._render_status_line()

        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/red]")
            import traceback
            traceback.print_exc()
            self._last_error = str(e)

        return (self._last_operation_summary, self._last_error, self._last_latency_ms)
