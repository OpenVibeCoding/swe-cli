"""Agent specialized in context compaction and summarization."""

from __future__ import annotations

from typing import Dict, List

from swecli.core.providers import create_provider_adapter
from swecli.prompts import load_prompt


class CompactAgent:
    """Agent specialized in context compaction and summarization."""

    # Load system prompt from file
    SYSTEM_PROMPT = load_prompt("agent_compact")

    def __init__(self, config) -> None:
        self.config = config
        # Use provider adapter pattern
        self._provider_adapter = create_provider_adapter(config)

    def compact(self, messages: List[Dict]) -> str:
        """Compact conversation history into a summary.

        Args:
            messages: List of conversation messages

        Returns:
            Compacted summary as a string
        """
        compactor_messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self._format_history(messages)},
        ]

        # Use provider adapter for the request
        result = self._provider_adapter.completion(
            model=self.config.model,
            messages=compactor_messages,
            tools=None,  # No tools for compaction
            temperature=0.3,
            max_tokens=2000,
        )

        if not result.get("success", False):
            raise Exception(f"Compaction error: {result.get('error', 'Unknown error')}")

        return result.get("content", "")

    def _format_history(self, messages: List[Dict]) -> str:
        lines = ["# Conversation History to Compact\n"]
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "system":
                continue

            if role == "user":
                lines.append(f"\n**User:** {content[:1000]}")
            elif role == "assistant":
                if msg.get("tool_calls"):
                    tool_names = [tc["function"]["name"] for tc in msg["tool_calls"]]
                    lines.append(
                        f"\n**Assistant:** {content[:500]} [Tools: {', '.join(tool_names)}]"
                    )
                else:
                    lines.append(f"\n**Assistant:** {content[:1000]}")
            elif role == "tool":
                lines.append(f"\n**Tool Result:** {content[:200]}...")

        return "\n".join(lines)
