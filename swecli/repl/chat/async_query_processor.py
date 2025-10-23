"""Async query processor for chat interface."""

import asyncio
import json
import random
from typing import TYPE_CHECKING

from swecli.core.context_management import ExecutionReflector

if TYPE_CHECKING:
    from swecli.repl.repl import REPL
    from swecli.repl.repl_chat import REPLChatApplication


class AsyncQueryProcessor:
    """Handles async query processing with ReAct loop for chat interface."""

    def __init__(
        self,
        repl: "REPL",
        chat_app: "REPLChatApplication",
    ):
        """Initialize async query processor.

        Args:
            repl: REPL instance for agent access
            chat_app: Chat application for UI callbacks
        """
        self.repl = repl
        self.chat_app = chat_app
        self.reflector = ExecutionReflector(min_tool_calls=2, min_confidence=0.65)

    def _initialize_processing_state(self):
        """Initialize processing state flags."""
        self.chat_app._is_processing = True
        self.chat_app._interrupt_requested = False
        self.chat_app._execution_state = None
        self.chat_app._current_tool_display = None

    def _reset_processing_state(self):
        """Reset processing state flags."""
        self.chat_app._current_messages = []
        self.chat_app._is_processing = False
        self.chat_app._interrupt_requested = False
        self.chat_app._interrupt_shown = False
        self.chat_app._execution_state = None
        self.chat_app._current_tool_display = None

    def _prepare_messages(self, query: str, enhanced_query: str) -> list:
        """Prepare messages for LLM API call with playbook context.

        Following ACE architecture: uses reflection window (last 5 interactions)
        instead of full conversation history to prevent context pollution.

        Args:
            query: Original query
            enhanced_query: Enhanced query with file contents

        Returns:
            List of API messages with learned strategies
        """
        # ACE-inspired: Use reflection window instead of full history
        # This limits context to recent interactions (default: 5)
        REFLECTION_WINDOW_SIZE = 5

        messages = (
            self.repl.session_manager.current_session.to_api_messages(
                window_size=REFLECTION_WINDOW_SIZE
            )
            if self.repl.session_manager.current_session
            else []
        )
        if enhanced_query != query:
            messages[-1]["content"] = enhanced_query

        # Build system prompt with playbook strategies
        system_content = self.repl.agent.system_prompt
        if self.repl.session_manager.current_session:
            try:
                playbook = self.repl.session_manager.current_session.get_playbook()
                playbook_context = playbook.as_context(max_strategies=30)
                if playbook_context:
                    system_content += playbook_context
            except Exception:
                pass  # Use base prompt if playbook fails

        # Add system prompt
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_content})

        return messages

    def _handle_interrupt_display(self):
        """Handle interrupt display based on execution state."""
        from rich.console import Console
        from io import StringIO

        if self.chat_app._execution_state == "executing_tool":
            # During tool execution: show tool call with interrupted message
            string_io = StringIO()
            temp_console = Console(file=string_io, force_terminal=True, legacy_windows=False)
            temp_console.print(
                f"[green]⏺[/green] [cyan]{self.chat_app._current_tool_display}[/cyan]", end=""
            )
            colored_tool_call = string_io.getvalue()

            interrupted_box = "┌─ Interrupted ────────────────\n"
            interrupted_box += "│ \033[31m⏺ Interrupted by user (ESC)\033[0m\n"
            interrupted_box += "└──────────────────────────────"

            combined_message = f"{colored_tool_call}\n{interrupted_box}"
            self.chat_app.add_assistant_message(combined_message)
        else:
            # During thinking/spinner: replace spinner line with red interrupted message
            self.chat_app.add_assistant_message("\033[31m⏺ Interrupted by user (ESC)\033[0m")

    def _check_interrupt(self, messages: list = None) -> bool:
        """Check if interrupt was requested and handle it.

        Args:
            messages: Current message history to clean up

        Returns:
            True if interrupted, False otherwise
        """
        if not self.chat_app._interrupt_requested:
            return False

        self.chat_app._stop_spinner()

        # Show interrupt message only if not already shown
        if not self.chat_app._interrupt_shown:
            self._handle_interrupt_display()
            self.chat_app._interrupt_shown = True  # Mark as shown

        # Clean up incomplete assistant message from message history
        if messages and len(messages) > 0:
            # Remove the last assistant message with tool calls that was interrupted
            last_message = messages[-1]
            if last_message.get("role") == "assistant" and "tool_calls" in last_message:
                messages.pop()
                # Also remove from session messages if they were added there
                if self.repl.session_manager.current_session:
                    session = self.repl.session_manager.current_session
                    if session.messages and len(session.messages) > 0:
                        last_session_msg = session.messages[-1]
                        if (hasattr(last_session_msg, 'content') and
                            last_session_msg.content == last_message.get("content", "") and
                            hasattr(last_session_msg, 'tool_calls') and
                            last_session_msg.tool_calls):
                            session.messages.pop()

        self._reset_processing_state()
        return True

    async def _handle_safety_limit(self, messages: list):
        """Handle safety limit by requesting summary.

        Args:
            messages: Message history
        """
        self.chat_app.conversation.messages.pop()  # Remove thinking indicator
        self.chat_app.add_assistant_message("⚠ Safety limit reached. Requesting summary...")
        messages.append({
            "role": "user",
            "content": "Please provide a summary of what you've found and what needs to be done.",
        })
        response = await asyncio.to_thread(self.repl.agent.call_llm, messages)
        if response.get("content"):
            formatted = self.chat_app._render_markdown_message(response["content"])
            if formatted:
                self.chat_app.add_assistant_message(formatted)

    async def _call_llm_with_spinner(self, messages: list) -> dict:
        """Call LLM with animated spinner.

        Args:
            messages: Message history

        Returns:
            LLM response
        """
        from swecli.repl.query_processor import QueryProcessor

        # Check for interrupt before starting LLM call
        if self._check_interrupt(messages):
            return {"success": False, "error": "Interrupted by user"}

        # Use random thinking verb
        thinking_verb = random.choice(QueryProcessor.THINKING_VERBS)

        # Start animated spinner
        self.chat_app._execution_state = "thinking"
        self.chat_app._start_spinner(f"{thinking_verb}...")

        # Create the LLM call task
        llm_task = asyncio.create_task(
            asyncio.to_thread(self.repl.agent.call_llm, messages)
        )

        # Store the task so it can be cancelled
        self.chat_app._current_llm_task = llm_task

        try:
            # Wait for the LLM call to complete, but check for interrupts
            while not llm_task.done():
                # Check for interrupt
                if self._check_interrupt(messages):
                    llm_task.cancel()
                    try:
                        await llm_task
                    except asyncio.CancelledError:
                        pass
                    return {"success": False, "error": "Interrupted by user"}

                # Wait a short time before checking again (50ms for fast response)
                await asyncio.sleep(0.05)

            # Get the result
            response = await llm_task

        except asyncio.CancelledError:
            # Task was cancelled
            return {"success": False, "error": "Interrupted by user"}
        finally:
            # Clear the task reference
            self.chat_app._current_llm_task = None

        # Check for interrupt after LLM call completes
        if self._check_interrupt(messages):
            return {"success": False, "error": "Interrupted by user"}

        # Get LLM description
        llm_description = response.get("content", "")

        # Stop spinner and show LLM response
        self.chat_app._stop_spinner()
        self.chat_app._execution_state = None
        if llm_description:
            formatted = self.chat_app._render_markdown_message(llm_description)
            if formatted:
                self.chat_app.add_assistant_message(formatted)

        return response

    def _should_nudge_agent(self, consecutive_reads: int, messages: list) -> bool:
        """Check if agent should be nudged to conclude.

        Args:
            consecutive_reads: Number of consecutive read operations
            messages: Message history

        Returns:
            True if nudged
        """
        if consecutive_reads >= 5:
            # Silently nudge the agent without displaying a message
            messages.append({
                "role": "user",
                "content": "Based on what you've seen, please summarize your findings and explain what needs to be done next.",
            })
            return True
        return False

    async def _reflect_and_learn(self, query: str, tool_call_objects: list) -> None:
        """Extract learnings from tool execution and add to playbook.

        Args:
            query: Original user query
            tool_call_objects: Executed tool calls with results
        """
        has_errors = any(tc.error for tc in tool_call_objects)
        outcome = "error" if has_errors else "success"

        result = self.reflector.reflect(query=query, tool_calls=tool_call_objects, outcome=outcome)
        if result:
            session = self.repl.session_manager.current_session
            playbook = session.get_playbook()

            # Track playbook size before
            before_count = len(playbook.strategies)

            # Add strategy
            strategy = playbook.add_strategy(category=result.category, content=result.content)
            session.update_playbook(playbook)

            # Track playbook size after
            after_count = len(playbook.strategies)

            # Log the evolution
            import os
            debug_dir = "/tmp/swecli_debug"
            os.makedirs(debug_dir, exist_ok=True)

            with open(f"{debug_dir}/playbook_evolution.log", "a") as f:
                from datetime import datetime
                timestamp = datetime.now().isoformat()
                f.write(f"\n{'='*60}\n")
                f.write(f"🧠 PLAYBOOK EVOLUTION - {timestamp}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Query: {query}\n")
                f.write(f"Outcome: {outcome}\n")
                f.write(f"Category: {result.category}\n")
                f.write(f"Strategy ID: {strategy.id}\n")
                f.write(f"Content: {result.content}\n")
                f.write(f"Confidence: {result.confidence}\n")
                f.write(f"Reasoning: {result.reasoning}\n")
                f.write(f"\nPlaybook size: {before_count} → {after_count} strategies\n")
                f.write(f"Session: {session.id}\n")
                f.write(f"\nCurrent playbook strategies:\n")
                for sid, strat in playbook.strategies.items():
                    f.write(f"  [{sid}] {strat.category}: {strat.content}\n")
                    f.write(f"       (+{strat.helpful_count}/-{strat.harmful_count}/~{strat.neutral_count})\n")

    async def process_query(self, query: str) -> None:
        """Process query asynchronously with full ReAct loop.

        Args:
            query: User query
        """
        from swecli.models.message import ChatMessage, Role

        # Initialize processing state
        self._initialize_processing_state()

        try:
            # Get enhanced query and prepare messages
            enhanced_query = self.repl.query_processor.enhance_query(query)
            messages = self._prepare_messages(query, enhanced_query)

            # Store reference for real-time token counting
            self.chat_app._current_messages = messages

            # ReAct loop
            consecutive_reads = 0
            iteration = 0
            SAFETY_LIMIT = 30
            READ_OPERATIONS = {"read_file", "list_files", "search"}

            while True:
                iteration += 1

                # Check for interrupt
                if self._check_interrupt(messages):
                    return

                # Check context compaction
                if iteration > 1:
                    await self.chat_app._check_and_compact_context(messages)

                # Safety limit check
                if iteration > SAFETY_LIMIT:
                    await self._handle_safety_limit(messages)
                    break

                # Call LLM with spinner
                response = await self._call_llm_with_spinner(messages)
                llm_description = response.get("content", "")

                if not response.get("success"):
                    # Check if it was interrupted (already handled by _check_interrupt)
                    if response.get("error") == "Interrupted by user":
                        break
                    # Otherwise it's a real error
                    self.chat_app.add_assistant_message(
                        f"❌ Error: {response.get('error', 'Unknown error')}"
                    )
                    break

                # Check for tool calls
                tool_calls = response.get("tool_calls")
                if not tool_calls:
                    # Task complete
                    if llm_description:
                        assistant_msg = ChatMessage(role=Role.ASSISTANT, content=llm_description)
                        self.repl.session_manager.add_message(
                            assistant_msg, self.repl.config.auto_save_interval
                        )

                    await self.chat_app._check_and_compact_context(messages)
                    self.chat_app._current_messages = []
                    break

                # Add assistant message to history
                messages.append({
                    "role": "assistant",
                    "content": llm_description,
                    "tool_calls": tool_calls,
                })

                # Track read-only operations
                all_reads = all(tc["function"]["name"] in READ_OPERATIONS for tc in tool_calls)
                consecutive_reads = consecutive_reads + 1 if all_reads else 0

                # Execute tool calls
                await self.chat_app._handle_tool_calls(tool_calls, messages)

                # Save assistant message with tool calls to session
                from swecli.models.message import ToolCall as ToolCallModel
                tool_call_objects = []
                for tc in tool_calls:
                    # Find the corresponding tool result in messages
                    tool_result = None
                    tool_error = None
                    for msg in reversed(messages):
                        if msg.get("role") == "tool" and msg.get("tool_call_id") == tc["id"]:
                            content = msg.get("content", "")
                            if content.startswith("Error:"):
                                tool_error = content[6:].strip()  # Remove "Error: " prefix
                            else:
                                tool_result = content
                            break

                    tool_call_obj = ToolCallModel(
                        id=tc["id"],
                        name=tc["function"]["name"],
                        parameters=json.loads(tc["function"]["arguments"]),
                        result=tool_result,
                        error=tool_error,
                        approved=True  # If we got here, it was approved
                    )
                    tool_call_objects.append(tool_call_obj)

                # Create and save assistant message with tool calls
                if llm_description or tool_call_objects:
                    assistant_msg = ChatMessage(
                        role=Role.ASSISTANT,
                        content=llm_description or "",
                        tool_calls=tool_call_objects
                    )
                    self.repl.session_manager.add_message(
                        assistant_msg, self.repl.config.auto_save_interval
                    )

                # Reflect and learn from tool execution
                if tool_call_objects and self.repl.session_manager.current_session:
                    try:
                        await self._reflect_and_learn(query, tool_call_objects)
                    except Exception:
                        pass  # Don't break on reflection errors

                # Check for interrupt immediately after tool execution
                if self._check_interrupt(messages):
                    return

                # Check if agent needs nudge
                if self._should_nudge_agent(consecutive_reads, messages):
                    consecutive_reads = 0

        except Exception as e:
            self.chat_app._stop_spinner()
            self.chat_app._current_messages = []
            self.chat_app.add_assistant_message(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Reset processing flags
            self.chat_app._is_processing = False
            self.chat_app._interrupt_requested = False
            self.chat_app._interrupt_shown = False
