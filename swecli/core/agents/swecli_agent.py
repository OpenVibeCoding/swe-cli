"""Primary agent implementation for interactive sessions."""

from __future__ import annotations

import json
from typing import Any, Optional

from swecli.core.abstract import BaseAgent
from swecli.core.agents.components import (
    SystemPromptBuilder,
    ToolSchemaBuilder,
)
from swecli.core.providers import create_provider_adapter
from swecli.models.config import AppConfig


class WebInterruptMonitor:
    """Monitor for checking web interrupt requests."""

    def __init__(self, web_state: Any):
        self.web_state = web_state

    def should_interrupt(self) -> bool:
        """Check if interrupt has been requested."""
        return self.web_state.is_interrupt_requested()


class SwecliAgent(BaseAgent):
    """Custom agent that coordinates LLM interactions via provider adapters."""

    def __init__(
        self,
        config: AppConfig,
        tool_registry: Any,
        mode_manager: Any,
        working_dir: Any = None,
    ) -> None:
        # Use provider adapter pattern instead of direct HTTP client
        self._provider_adapter = create_provider_adapter(config)
        self._working_dir = working_dir
        super().__init__(config, tool_registry, mode_manager)

    def build_system_prompt(self) -> str:
        return SystemPromptBuilder(self.tool_registry, self._working_dir).build()

    def build_tool_schemas(self) -> list[dict[str, Any]]:
        return ToolSchemaBuilder(self.tool_registry).build()

    def call_llm(self, messages: list[dict], task_monitor: Optional[Any] = None) -> dict:
        """Call LLM using the provider adapter.

        Args:
            messages: Message history
            task_monitor: Optional task monitor for interrupt handling

        Returns:
            Dict with success, message, content, tool_calls, usage, etc.
        """
        try:
            result = self._provider_adapter.completion(
                model=self.config.model,
                messages=messages,
                tools=self.tool_schemas,
                tool_choice="auto",
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                task_monitor=task_monitor,
            )
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"Provider error: {str(e)}",
            }

    def run_sync(
        self,
        message: str,
        deps: Any,
        message_history: Optional[list[dict]] = None,
    ) -> dict:
        messages = message_history or []

        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": self.system_prompt})

        messages.append({"role": "user", "content": message})

        max_iterations = 10
        for _ in range(max_iterations):
            # Check for interrupt request (for web UI)
            if hasattr(self, 'web_state') and self.web_state.is_interrupt_requested():
                self.web_state.clear_interrupt()
                return {
                    "content": "Task interrupted by user",
                    "messages": messages,
                    "success": False,
                    "interrupted": True,
                }

            # Create interrupt monitor if web_state is available
            monitor = None
            if hasattr(self, 'web_state'):
                monitor = WebInterruptMonitor(self.web_state)

            # Use provider adapter instead of direct HTTP client
            result = self._provider_adapter.completion(
                model=self.config.model,
                messages=messages,
                tools=self.tool_schemas,
                tool_choice="auto",
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                task_monitor=monitor,
            )

            if not result.get("success", False):
                error_msg = result.get("error", "Unknown error")
                return {
                    "content": error_msg,
                    "messages": messages,
                    "success": False,
                }

            message_data = result["message"]
            raw_content = message_data.get("content", "") or ""
            cleaned_content = result.get("content", raw_content)

            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": raw_content,
            }
            if "tool_calls" in message_data and message_data["tool_calls"]:
                assistant_msg["tool_calls"] = message_data["tool_calls"]
            messages.append(assistant_msg)

            if "tool_calls" not in message_data or not message_data["tool_calls"]:
                return {
                    "content": cleaned_content or "",
                    "messages": messages,
                    "success": True,
                }

            for tool_call in message_data["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])

                result = self.tool_registry.execute_tool(
                    tool_name,
                    tool_args,
                    mode_manager=deps.mode_manager,
                    approval_manager=deps.approval_manager,
                    undo_manager=deps.undo_manager,
                )

                tool_result = (
                    result.get("output", "")
                    if result["success"]
                    else f"Error: {result.get('error', 'Tool execution failed')}"
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result,
                    }
                )

        return {
            "content": "Max iterations reached without completion",
            "messages": messages,
            "success": False,
        }
