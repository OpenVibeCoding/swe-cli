"""Agent dedicated to PLAN mode interactions."""

from __future__ import annotations

from typing import Any, Optional

from swecli.core.abstract import BaseAgent
from swecli.core.agents.components import (
    AgentHttpClient,
    PlanningPromptBuilder,
    ResponseCleaner,
    resolve_api_config,
)
from swecli.models.config import AppConfig


class PlanningAgent(BaseAgent):
    """Planning agent that analyzes and plans without executing changes."""

    def __init__(
        self,
        config: AppConfig,
        tool_registry: Any,
        mode_manager: Any,
    ) -> None:
        self.api_url, self.headers = resolve_api_config(config)
        self._http_client = AgentHttpClient(self.api_url, self.headers)
        self._response_cleaner = ResponseCleaner()
        super().__init__(config, tool_registry, mode_manager)

    def build_system_prompt(self) -> str:
        return PlanningPromptBuilder().build()

    def build_tool_schemas(self) -> list[dict[str, Any]]:
        return []

    def call_llm(self, messages: list[dict], task_monitor: Optional[Any] = None) -> dict:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        result = self._http_client.post_json(payload, task_monitor=task_monitor)
        if not result.success or result.response is None:
            return {
                "success": False,
                "error": result.error or "Unknown error",
                "interrupted": result.interrupted,
            }

        response = result.response
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API Error {response.status_code}: {response.text}",
            }

        response_data = response.json()
        choice = response_data["choices"][0]
        message_data = choice["message"]

        raw_content = message_data.get("content")
        cleaned_content = self._response_cleaner.clean(raw_content)

        if task_monitor and "usage" in response_data:
            usage = response_data["usage"]
            total_tokens = usage.get("total_tokens", 0)
            if total_tokens > 0:
                task_monitor.update_tokens(total_tokens)

        return {
            "success": True,
            "message": message_data,
            "content": cleaned_content,
            "tool_calls": message_data.get("tool_calls"),
            "usage": response_data.get("usage"),
        }

    def run_sync(
        self,
        message: str,
        deps: Any,
        message_history: Optional[list[dict]] = None,
    ) -> dict:
        del deps  # Planning agent does not execute tools.

        messages = message_history or []
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": self.system_prompt})

        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        result = self._http_client.post_json(payload)
        if not result.success or result.response is None:
            error_msg = result.error or "Unknown error"
            return {
                "content": error_msg,
                "messages": messages,
                "success": False,
            }

        response = result.response
        if response.status_code != 200:
            error_msg = f"API Error {response.status_code}: {response.text}"
            return {
                "content": error_msg,
                "messages": messages,
                "success": False,
            }

        response_data = response.json()
        choice = response_data["choices"][0]
        message_data = choice["message"]

        raw_content = message_data.get("content")
        cleaned_content = self._response_cleaner.clean(raw_content)

        messages.append(
            {
                "role": "assistant",
                "content": cleaned_content,
            }
        )

        return {
            "content": cleaned_content or "",
            "messages": messages,
            "success": True,
        }
