"""Base provider adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class ProviderAdapter(ABC):
    """Abstract base class for LLM provider adapters.

    This interface allows SWE-CLI to support multiple provider implementations
    (legacy HTTP client, any-llm framework, etc.) without changing core agent logic.
    """

    @abstractmethod
    def completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_monitor: Optional[Any] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make a completion request to the LLM provider.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-5-sonnet")
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool schemas for function calling
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            task_monitor: Optional monitor for interrupt/progress tracking
            **kwargs: Additional provider-specific parameters

        Returns:
            Dict with keys:
                - success (bool): Whether request succeeded
                - message (dict): Assistant message with role, content, tool_calls
                - content (str): Cleaned text content
                - tool_calls (list): Tool calls from the model
                - usage (dict): Token usage statistics
                - error (str, optional): Error message if success=False
                - interrupted (bool, optional): Whether request was interrupted
        """
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if this provider adapter supports streaming responses.

        Returns:
            True if streaming is supported, False otherwise
        """
        pass

    def get_provider_info(self) -> dict[str, Any]:
        """Get metadata about this provider's capabilities.

        Returns:
            Dict with provider information (name, features, etc.)
            Default implementation returns empty dict.
        """
        return {}

    def cleanup(self) -> None:
        """Clean up any resources (connections, sessions, etc.).

        Called when the adapter is no longer needed.
        Default implementation does nothing.
        """
        pass
