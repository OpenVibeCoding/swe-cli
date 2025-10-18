"""Context compaction handler for chat interface."""

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swecli.core.context import ContextTokenMonitor
    from swecli.core.agents.compact_agent import CompactAgent


class ContextCompactor:
    """Handles context window compaction for chat sessions."""

    def __init__(
        self,
        context_monitor: "ContextTokenMonitor",
        compactor: "CompactAgent",
        repl,
        spinner_start_callback,
        spinner_stop_callback,
        add_message_callback,
    ):
        """Initialize context compactor.

        Args:
            context_monitor: Token counter and monitoring
            compactor: Compaction agent
            repl: REPL instance for agent and session access
            spinner_start_callback: Callback to start spinner
            spinner_stop_callback: Callback to stop spinner
            add_message_callback: Callback to add messages
        """
        self.context_monitor = context_monitor
        self.compactor = compactor
        self.repl = repl
        self._start_spinner = spinner_start_callback
        self._stop_spinner = spinner_stop_callback
        self._add_message = add_message_callback

    async def check_and_compact(self, messages: list) -> None:
        """Check if context compaction is needed and trigger it.

        Args:
            messages: Current message history
        """
        # Count EVERYTHING: baseline + conversation (same as status bar)
        baseline_tokens = 0
        conversation_tokens = 0

        # 1. Count system prompt (always sent)
        if hasattr(self.repl.agent, "system_prompt"):
            baseline_tokens += self.context_monitor.count_tokens(self.repl.agent.system_prompt)

        # 2. Count tool schemas (always sent)
        if hasattr(self.repl.agent, "tool_schemas"):
            import json

            tool_schemas_str = json.dumps(self.repl.agent.tool_schemas)
            baseline_tokens += self.context_monitor.count_tokens(tool_schemas_str)

        # 3. Count conversation messages
        for msg in messages:
            # Skip system message (already counted)
            if msg.get("role") == "system":
                continue

            # Count message content
            content = msg.get("content", "")
            if content:
                conversation_tokens += self.context_monitor.count_tokens(str(content))

            # Count tool calls (arguments can be large)
            if "tool_calls" in msg and msg["tool_calls"]:
                for tool_call in msg["tool_calls"]:
                    conversation_tokens += self.context_monitor.count_tokens(
                        tool_call.get("function", {}).get("name", "")
                    )
                    conversation_tokens += self.context_monitor.count_tokens(
                        str(tool_call.get("function", {}).get("arguments", ""))
                    )

        # Total tokens = baseline + conversation
        total_tokens = baseline_tokens + conversation_tokens

        # Check if compaction is needed
        if not self.context_monitor.needs_compaction(total_tokens):
            return

        # Trigger compaction
        try:
            # Show spinner
            self._start_spinner("Compacting Context")

            # Call compactor agent in thread (don't block UI)
            summary = await asyncio.to_thread(self.compactor.compact, messages)

            # Stop spinner
            self._stop_spinner()

            # Replace message buffer - keep only the most recent message to ensure we're under limit
            system_msg = messages[0] if messages and messages[0].get("role") == "system" else None

            # Start with just the last message, add more if we have room
            recent_msgs = []
            if len(messages) > 1:
                # Try last message first
                recent_msgs = [messages[-1]]

                # Calculate if we can afford to keep one more message
                test_tokens = baseline_tokens
                test_tokens += self.context_monitor.count_tokens(summary)
                for msg in recent_msgs:
                    content = msg.get("content", "")
                    if content:
                        test_tokens += self.context_monitor.count_tokens(str(content))

                # If under 60% with just last message, try adding second-to-last
                safe_limit = int(self.context_monitor.context_limit * 0.60)  # Target 60% usage
                if test_tokens < safe_limit and len(messages) > 2:
                    second_last = messages[-2]
                    second_last_content = second_last.get("content", "")
                    second_last_tokens = (
                        self.context_monitor.count_tokens(str(second_last_content))
                        if second_last_content
                        else 0
                    )

                    if test_tokens + second_last_tokens < safe_limit:
                        recent_msgs = [second_last, messages[-1]]

            # Create summary message
            summary_msg = {
                "role": "system",
                "content": f"# Previous Conversation Summary\n\n{summary}\n\n---\n\nContinue from here with full context.",
            }

            # Rebuild messages array
            new_messages = []
            if system_msg:
                new_messages.append(system_msg)
            new_messages.append(summary_msg)
            new_messages.extend(recent_msgs)

            # Replace the messages array in-place
            messages.clear()
            messages.extend(new_messages)

            # CRITICAL: Update the session with compacted messages
            # Convert API messages back to ChatMessage objects for session storage
            from swecli.models.message import ChatMessage, Role

            session = self.repl.session_manager.current_session
            if session:
                # Clear session messages and rebuild from compacted API messages
                session.messages.clear()
                for msg in new_messages:
                    # Skip the agent's system prompt (first system message)
                    if msg.get("role") == "system" and msg.get("content", "").startswith(
                        "You are SWE-CLI"
                    ):
                        continue

                    # Convert to ChatMessage with appropriate role
                    role_str = msg["role"]
                    if role_str == "system":
                        role = Role.SYSTEM  # Summary message
                    elif role_str == "user":
                        role = Role.USER
                    else:
                        role = Role.ASSISTANT

                    chat_msg = ChatMessage(role=role, content=msg.get("content", ""))
                    session.messages.append(chat_msg)

                # Save the compacted session
                self.repl.session_manager.save_session()

            # Calculate new token count after compaction
            new_total = baseline_tokens
            for msg in new_messages:
                if msg.get("role") == "system":
                    continue
                content = msg.get("content", "")
                if content:
                    new_total += self.context_monitor.count_tokens(str(content))

            # Show compaction result in a formatted box
            saved_tokens = total_tokens - new_total
            stats = self.context_monitor.get_usage_stats(new_total)

            # Create Rich panel with the summary
            from rich.panel import Panel
            from rich.console import Console
            from io import StringIO

            # Render panel to string
            string_io = StringIO()
            temp_console = Console(file=string_io, force_terminal=True, width=100)

            panel = Panel(
                summary,
                title="✓ Context Compacted",
                subtitle=f"Saved {saved_tokens} tokens • {stats['remaining_percent']:.0f}% remaining",
                border_style="green",
                padding=(0, 2),
            )
            temp_console.print(panel)

            # Get the rendered output
            rendered_output = string_io.getvalue()
            self._add_message(rendered_output)

        except Exception as e:
            # Stop spinner
            self._stop_spinner()

            # Show error - format as system message
            error_msg = f"✗ Compaction failed: {str(e)}"
            self._add_message(error_msg)
