"""Conversation management for SWE-CLI chat interface."""

from __future__ import annotations

from typing import List, Tuple
from datetime import datetime
from prompt_toolkit.formatted_text import StyleAndTextTuples


class ConversationBuffer:
    """Manages conversation history and formatting."""

    def __init__(self):
        self.messages: List[tuple[str, str, str]] = []  # (role, content, timestamp)
        self.last_was_spinner = False  # Track if last message was a spinner

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(("user", content, timestamp))
        self.last_was_spinner = False  # Reset spinner flag

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(("assistant", content, timestamp))

    def add_system_message(self, content: str) -> None:
        """Add a system message (errors, notifications, etc.)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(("system", content, timestamp))

    def update_last_message(self, content: str) -> None:
        """Update the last message (useful for streaming/thinking indicators)."""
        if self.messages:
            role, _, timestamp = self.messages[-1]
            self.messages[-1] = (role, content, timestamp)

    def get_plain_text(self) -> str:
        """Get conversation as plain text with ANSI colors for buffer display."""
        # ANSI color codes
        CYAN = "\033[36m"
        CYAN_BOLD = "\033[1;36m"
        GREEN = "\033[32m"
        RED = "\033[31m"
        GRAY = "\033[90m"
        LIGHT_GREEN = "\033[92m"
        LIGHT_RED = "\033[91m"
        RESET = "\033[0m"

        lines = []

        for role, content, timestamp in self.messages:
            if role == "user":
                # User message: cyan › symbol + white text
                lines.append(f"{CYAN_BOLD}› {RESET}{content}")
            elif role == "assistant":
                # Detect message type and apply appropriate colors
                if content.startswith("┌") and "Tool Call" in content:
                    # Tool call box in cyan
                    lines.append(f"{CYAN}{content}{RESET}")
                elif content.startswith("┌") and "Result" in content:
                    # Result box in green
                    lines.append(f"{LIGHT_GREEN}{content}{RESET}")
                elif content.startswith("┌") and "Error" in content:
                    # Error box in red
                    lines.append(f"{LIGHT_RED}{content}{RESET}")
                elif content.startswith("⏺"):
                    # LLM response with ⏺ symbol
                    lines.append(content)
                else:
                    # Other assistant messages
                    lines.append(content)
            elif role == "system":
                # System message: gray/dimmed
                lines.append(f"{GRAY}{content}{RESET}")

            lines.append("")  # Empty line between messages

        return "\n".join(lines)

    def get_formatted_text(self) -> StyleAndTextTuples:
        """Get formatted text for display in conversation area."""
        result: StyleAndTextTuples = []

        for role, content, timestamp in self.messages:
            if role == "user":
                # User message: › content
                result.append(("class:user-prompt", "› "))
                result.append(("class:user-message", content))
                result.append(("", "\n"))
            elif role == "assistant":
                # Detect message type from content for styling
                if content.startswith("┌─ Tool Call"):
                    result.append(("class:tool-call", content))
                elif content.startswith("┌─ Result"):
                    result.append(("class:tool-result", content))
                elif content.startswith("┌─ Error"):
                    result.append(("class:tool-error", content))
                else:
                    result.append(("class:assistant-message", content))
                result.append(("", "\n"))
            elif role == "system":
                # System message: dimmed
                result.append(("class:system-message", content))
                result.append(("", "\n"))

            # Add spacing between messages
            result.append(("", "\n"))

        return result

    def clear(self) -> None:
        """Clear all messages from conversation."""
        self.messages.clear()
        self.last_was_spinner = False