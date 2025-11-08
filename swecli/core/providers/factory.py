"""Factory for creating provider adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swecli.models.config import AppConfig
    from swecli.core.providers.base import ProviderAdapter


def create_provider_adapter(config: "AppConfig") -> "ProviderAdapter":
    """Create a provider adapter using any-llm framework.

    Args:
        config: Application configuration

    Returns:
        AnyLLMAdapter instance configured for the specified provider

    Examples:
        >>> config = AppConfig(
        ...     model_provider="anthropic",
        ...     model="claude-3-5-sonnet-20241022"
        ... )
        >>> adapter = create_provider_adapter(config)
        >>> type(adapter).__name__
        'AnyLLMAdapter'
    """
    from swecli.core.providers.anyllm_adapter import AnyLLMAdapter

    return AnyLLMAdapter(config)


def get_available_providers() -> list[str]:
    """Get list of all available providers from any-llm (if installed).

    Returns:
        List of provider names, or empty list if any-llm not installed
    """
    try:
        from any_llm import AnyLLM

        return AnyLLM.get_supported_providers()
    except ImportError:
        return []


def get_provider_metadata() -> list[dict[str, any]]:
    """Get metadata for all available providers (if any-llm installed).

    Returns:
        List of provider metadata dicts, or empty list if any-llm not installed
    """
    try:
        from any_llm import AnyLLM

        providers = AnyLLM.get_all_provider_metadata()
        return [
            {
                "name": p.name,
                "env_key": p.env_key,
                "doc_url": p.doc_url,
                "supports_streaming": p.streaming,
                "supports_vision": p.image,
                "supports_reasoning": p.reasoning,
            }
            for p in providers
        ]
    except ImportError:
        return []
