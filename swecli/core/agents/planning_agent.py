"""Agent dedicated to PLAN mode interactions."""

from __future__ import annotations

from typing import Any, Optional

from swecli.core.abstract import BaseAgent
from swecli.core.agents.components import PlanningPromptBuilder
from swecli.core.agents.deep_langchain_agent import DeepLangChainAgent
from swecli.models.config import AppConfig


class PlanningAgent(BaseAgent):
    """Planning agent that analyzes and plans without executing changes.

    Uses DeepLangChainAgent internally but with a custom planning prompt.
    """

    def __init__(
        self,
        config: AppConfig,
        tool_registry: Any,
        mode_manager: Any,
        working_dir: Any = None,
    ) -> None:
        self._working_dir = working_dir
        # Create a DeepLangChainAgent instance to handle LLM calls
        self._deep_agent = DeepLangChainAgent(
            config, tool_registry, mode_manager, working_dir
        )
        super().__init__(config, tool_registry, mode_manager)

    def build_system_prompt(self) -> str:
        """Use planning-specific system prompt."""
        return PlanningPromptBuilder().build()

    def build_tool_schemas(self) -> list[dict[str, Any]]:
        """Planning agent doesn't use tools."""
        return []

    def call_llm(self, messages: list[dict], task_monitor: Optional[Any] = None) -> dict:
        """Call LLM using DeepLangChainAgent with planning-specific prompt.

        Replaces the system prompt with planning prompt before delegating to DeepLangChainAgent.
        """
        # Make a copy of messages to avoid modifying the original
        messages_copy = messages.copy()

        # Replace system prompt with planning prompt
        planning_prompt = self.build_system_prompt()
        if messages_copy and messages_copy[0].get("role") == "system":
            messages_copy[0] = {"role": "system", "content": planning_prompt}
        else:
            messages_copy.insert(0, {"role": "system", "content": planning_prompt})

        # Delegate to DeepLangChainAgent
        return self._deep_agent.call_llm(messages_copy, task_monitor=task_monitor)

    def run_sync(
        self,
        message: str,
        deps: Any,
        message_history: Optional[list[dict]] = None,
        ui_callback: Optional[Any] = None,
    ) -> dict:
        """Run planning agent synchronously using DeepLangChainAgent."""
        del deps  # Planning agent does not execute tools.

        messages = message_history or []
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": self.system_prompt})

        messages.append({"role": "user", "content": message})

        # Use call_llm which delegates to DeepLangChainAgent
        result = self.call_llm(messages)

        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            return {
                "content": error_msg,
                "messages": messages,
                "success": False,
            }

        # Extract content from result
        content = result.get("content", "")

        # Add assistant response to messages
        messages.append(
            {
                "role": "assistant",
                "content": content or "",
            }
        )

        return {
            "content": content,
            "messages": messages,
            "success": True,
        }
