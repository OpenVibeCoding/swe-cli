"""Tests for provider adapter system."""

import pytest
from swecli.models.config import AppConfig
from swecli.core.providers import create_provider_adapter
from swecli.core.providers.base import ProviderAdapter
from swecli.core.providers.anyllm_adapter import AnyLLMAdapter


class TestProviderFactory:
    """Tests for provider factory."""

    def test_create_anyllm_adapter(self):
        """Test that AnyLLMAdapter is created."""
        config = AppConfig(
            model_provider="openai",
            model="gpt-4",
            api_key="test-key",
        )
        adapter = create_provider_adapter(config)
        assert isinstance(adapter, AnyLLMAdapter)
        assert isinstance(adapter, ProviderAdapter)

    def test_create_adapter_for_anthropic(self):
        """Test creating adapter for Anthropic."""
        config = AppConfig(
            model_provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
        )
        adapter = create_provider_adapter(config)
        assert isinstance(adapter, AnyLLMAdapter)

    def test_create_adapter_for_fireworks(self):
        """Test creating adapter for Fireworks."""
        config = AppConfig(
            model_provider="fireworks",
            model="accounts/fireworks/models/kimi-k2-instruct-0905",
            api_key="test-key",
        )
        adapter = create_provider_adapter(config)
        assert isinstance(adapter, AnyLLMAdapter)

    def test_adapter_implements_interface(self):
        """Test that created adapters implement the ProviderAdapter interface."""
        config = AppConfig(
            model_provider="openai",
            model="gpt-4",
            api_key="test-key",
        )
        adapter = create_provider_adapter(config)

        # Check interface methods exist
        assert hasattr(adapter, "completion")
        assert hasattr(adapter, "supports_streaming")
        assert hasattr(adapter, "get_provider_info")
        assert hasattr(adapter, "cleanup")

        # Check methods are callable
        assert callable(adapter.completion)
        assert callable(adapter.supports_streaming)
        assert callable(adapter.get_provider_info)
        assert callable(adapter.cleanup)


class TestAnyLLMProviderAdapter:
    """Tests for any-llm provider adapter."""

    def test_anyllm_adapter_initialization(self):
        """Test any-llm adapter initializes correctly."""
        config = AppConfig(
            model_provider="openai",
            model="gpt-4",
            api_key="test-key",
        )

        adapter = AnyLLMAdapter(config)
        assert adapter.config == config
        assert hasattr(adapter, "_provider_instance")

    def test_anyllm_adapter_supports_streaming(self):
        """Test checking streaming support."""
        config = AppConfig(
            model_provider="openai",
            model="gpt-4",
            api_key="test-key",
        )
        adapter = AnyLLMAdapter(config)

        # OpenAI supports streaming
        assert adapter.supports_streaming() is True

    def test_anyllm_adapter_get_provider_info(self):
        """Test getting provider info from any-llm adapter."""
        config = AppConfig(
            model_provider="openai",
            model="gpt-4",
            api_key="test-key",
        )

        adapter = AnyLLMAdapter(config)
        info = adapter.get_provider_info()

        assert info["adapter_type"] == "anyllm"
        assert info["available"] is True
        assert "supports_streaming" in info
        assert "supports_vision" in info

    def test_anyllm_adapter_cleanup(self):
        """Test that cleanup method works without errors."""
        config = AppConfig(
            model_provider="openai",
            model="gpt-4",
            api_key="test-key",
        )
        adapter = AnyLLMAdapter(config)

        # Should not raise any errors
        adapter.cleanup()


class TestProviderAdapterIntegration:
    """Integration tests for provider adapters."""

    def test_adapter_interface_consistency(self):
        """Test that adapters provide consistent interface."""
        config = AppConfig(
            model_provider="openai",
            model="gpt-4",
            api_key="test-key",
        )

        adapter = create_provider_adapter(config)
        info = adapter.get_provider_info()

        assert "adapter_type" in info
        assert info["adapter_type"] == "anyllm"

    def test_completion_signature_compatibility(self):
        """Test that completion method has the expected signature."""
        config = AppConfig(
            model_provider="openai",
            model="gpt-4",
            api_key="test-key",
        )

        adapter = create_provider_adapter(config)

        import inspect

        sig = inspect.signature(adapter.completion)
        params = list(sig.parameters.keys())

        # All adapters must have these core parameters
        assert "model" in params
        assert "messages" in params
        assert "tools" in params or "kwargs" in params

    def test_multiple_providers(self):
        """Test that we can create adapters for different providers."""
        providers_to_test = [
            ("openai", "gpt-4"),
            ("anthropic", "claude-3-5-sonnet-20241022"),
            ("fireworks", "accounts/fireworks/models/llama-v3p1-70b-instruct"),
            ("gemini", "gemini-1.5-pro"),
        ]

        for provider, model in providers_to_test:
            config = AppConfig(
                model_provider=provider,
                model=model,
                api_key="test-key",
            )
            adapter = create_provider_adapter(config)
            assert isinstance(adapter, AnyLLMAdapter)
            info = adapter.get_provider_info()
            assert info["name"] == provider
