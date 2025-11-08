"""Provider adapter using the any-llm framework."""

from __future__ import annotations

from typing import Any, Optional

from swecli.core.providers.base import ProviderAdapter
from swecli.models.config import AppConfig

# Try to import any-llm, but don't fail if not installed
try:
    from any_llm import AnyLLM, completion
    from any_llm.types.completion import ChatCompletion

    HAS_ANYLLM = True
except ImportError:
    HAS_ANYLLM = False
    AnyLLM = None  # type: ignore
    completion = None  # type: ignore
    ChatCompletion = None  # type: ignore


class AnyLLMAdapter(ProviderAdapter):
    """Adapter using the any-llm framework for multi-provider support.

    This adapter leverages Mozilla's any-llm SDK to support 35+ LLM providers
    with a unified interface. Requires installation: pip install 'swecli[llm-providers]'
    """

    def __init__(self, config: AppConfig):
        """Initialize the any-llm adapter.

        Args:
            config: Application configuration

        Raises:
            ImportError: If any-llm is not installed
        """
        if not HAS_ANYLLM:
            raise ImportError(
                "any-llm is not installed. Install with: pip install 'swecli[llm-providers]'"
            )

        self.config = config
        self._provider_instance: Optional[Any] = None
        self._response_cleaner = self._create_response_cleaner()

        # Create provider instance for reuse (connection pooling)
        self._create_provider_instance()

    def _create_response_cleaner(self) -> Any:
        """Create response cleaner for text processing."""
        from swecli.core.agents.components import ResponseCleaner

        return ResponseCleaner()

    def _create_provider_instance(self) -> None:
        """Create a reusable provider instance."""
        if not HAS_ANYLLM or AnyLLM is None:
            return

        try:
            self._provider_instance = AnyLLM.create(
                provider=self.config.model_provider,
                api_key=self.config.api_key or self.config.get_api_key(),
                api_base=self.config.api_base_url,
            )
        except Exception as e:
            # If creation fails, fall back to using direct completion API
            # (which creates a new client each time)
            self._provider_instance = None
            print(f"Warning: Could not create provider instance: {e}")
            print("Falling back to per-request client creation")

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
        """Make a completion request using any-llm.

        Args:
            model: Model identifier
            messages: Message history
            tools: Tool schemas for function calling
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            task_monitor: Optional task monitor (not supported by any-llm yet)
            **kwargs: Additional parameters

        Returns:
            Standardized response dict with success, message, content, etc.
        """
        if not HAS_ANYLLM:
            return {
                "success": False,
                "error": "any-llm not installed",
            }

        try:
            # Prepare parameters
            completion_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.config.temperature,
                "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            }

            # Add tools if provided
            if tools:
                completion_params["tools"] = tools
                completion_params["tool_choice"] = kwargs.get("tool_choice", "auto")

            # Add any additional kwargs
            for key, value in kwargs.items():
                if key not in ["tool_choice", "task_monitor"] and value is not None:
                    completion_params[key] = value

            # Make the request using either instance or direct API
            if self._provider_instance:
                response = self._provider_instance.completion(**completion_params)
            else:
                # Use direct completion API with provider parameter
                response = completion(
                    provider=self.config.model_provider,
                    api_key=self.config.api_key or self.config.get_api_key(),
                    api_base=self.config.api_base_url,
                    **completion_params,
                )

            # Convert any-llm response to our standard format
            return self._convert_response(response, task_monitor)

        except Exception as e:
            return {
                "success": False,
                "error": f"any-llm error: {str(e)}",
            }

    def _convert_response(
        self, response: Any, task_monitor: Optional[Any] = None
    ) -> dict[str, Any]:
        """Convert any-llm ChatCompletion response to our standard format.

        Args:
            response: ChatCompletion from any-llm
            task_monitor: Optional task monitor for token tracking

        Returns:
            Standardized response dict
        """
        try:
            choice = response.choices[0]
            message = choice.message

            # Build message dict
            message_data = {
                "role": message.role,
                "content": message.content,
            }

            # Add tool calls if present
            if hasattr(message, "tool_calls") and message.tool_calls:
                message_data["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]

            # Clean content
            raw_content = message.content
            cleaned_content = self._response_cleaner.clean(raw_content) if raw_content else None

            # Build usage dict
            usage_data = None
            if hasattr(response, "usage") and response.usage:
                usage_data = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

                # Update task monitor if provided
                if task_monitor and usage_data["total_tokens"] > 0:
                    task_monitor.update_tokens(usage_data["total_tokens"])

            return {
                "success": True,
                "message": message_data,
                "content": cleaned_content,
                "tool_calls": message_data.get("tool_calls"),
                "usage": usage_data,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Response conversion error: {str(e)}",
            }

    def supports_streaming(self) -> bool:
        """Check if the current provider supports streaming.

        Returns:
            True if provider supports streaming, False otherwise
        """
        if not HAS_ANYLLM or AnyLLM is None:
            return False

        try:
            provider_class = AnyLLM.get_provider_class(self.config.model_provider)
            return provider_class.SUPPORTS_COMPLETION_STREAMING
        except Exception:
            return False

    def get_provider_info(self) -> dict[str, Any]:
        """Get detailed information about the current provider's capabilities.

        Returns:
            Dict with provider metadata including supported features
        """
        if not HAS_ANYLLM or AnyLLM is None:
            return {
                "name": self.config.model_provider,
                "adapter_type": "anyllm",
                "available": False,
                "error": "any-llm not installed",
            }

        try:
            provider_class = AnyLLM.get_provider_class(self.config.model_provider)
            metadata = provider_class.get_provider_metadata()

            return {
                "name": metadata.name,
                "model": self.config.model,
                "adapter_type": "anyllm",
                "available": True,
                "supports_streaming": metadata.streaming,
                "supports_completion": metadata.completion,
                "supports_vision": metadata.image,
                "supports_pdf": metadata.pdf,
                "supports_reasoning": metadata.reasoning,
                "supports_embedding": metadata.embedding,
                "documentation_url": metadata.doc_url,
                "env_key": metadata.env_key,
            }
        except Exception as e:
            return {
                "name": self.config.model_provider,
                "adapter_type": "anyllm",
                "available": False,
                "error": str(e),
            }

    def get_available_models(self) -> list[str]:
        """Get list of available models from the provider (if supported).

        Returns:
            List of model identifiers, or empty list if not supported
        """
        if not HAS_ANYLLM or not self._provider_instance:
            return []

        try:
            if hasattr(self._provider_instance, "SUPPORTS_LIST_MODELS") and \
               self._provider_instance.SUPPORTS_LIST_MODELS:
                models = self._provider_instance.list_models()
                return [m.id for m in models]
        except Exception:
            pass

        return []

    def cleanup(self) -> None:
        """Clean up provider instance resources."""
        self._provider_instance = None
