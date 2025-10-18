"""Accurate token counting utilities for session context management."""

from __future__ import annotations

from typing import Any, Dict, List

import tiktoken

from swecli.models.message import ChatMessage, ToolCall


class ContextTokenMonitor:
    """Monitor and count tokens using tiktoken for session context."""

    def __init__(
        self,
        model: str = "gpt-4",
        context_limit: Union[int, None] = None,
        compaction_threshold: Union[float, None] = None,
    ) -> None:
        """Initialize with tiktoken encoding."""
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

        self.context_limit = context_limit if context_limit is not None else 256000
        self.compaction_threshold = (
            compaction_threshold if compaction_threshold is not None else 0.99
        )

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    def count_message_tokens(self, message: ChatMessage) -> int:
        """Count tokens in a complete message, including tool calls."""
        total = self.count_tokens(message.content)
        for tool_call in message.tool_calls:
            total += self._count_tool_call_tokens(tool_call)
        return total

    def _count_tool_call_tokens(self, tool_call: ToolCall) -> int:
        """Count tokens in a tool call."""
        total = self.count_tokens(tool_call.name)
        total += self.count_tokens(str(tool_call.parameters))
        if tool_call.result:
            total += self.count_tokens(str(tool_call.result))
        return total

    def count_messages_total(self, messages: List[ChatMessage]) -> int:
        """Count total tokens across all messages."""
        return sum(self.count_message_tokens(msg) for msg in messages)

    def needs_compaction(self, current_tokens: int) -> bool:
        """Return True when token usage exceeds the configured threshold."""
        return current_tokens >= (self.context_limit * self.compaction_threshold)

    def get_usage_stats(self, current_tokens: int) -> Dict[str, Any]:
        """Return usage statistics for display."""
        usage_percent = (current_tokens / self.context_limit) * 100
        remaining_percent = 100 - usage_percent
        return {
            "current_tokens": current_tokens,
            "limit": self.context_limit,
            "available": self.context_limit - current_tokens,
            "usage_percent": usage_percent,
            "remaining_percent": remaining_percent,
            "needs_compaction": self.needs_compaction(current_tokens),
        }

    @staticmethod
    def format_tokens(count: int) -> str:
        """Format token count for display."""
        abs_count = abs(count)
        if abs_count >= 1000:
            return f"{abs_count / 1000:.1f}k"
        return str(abs_count)
