"""Model and provider configuration management."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ModelInfo:
    """Information about a specific model."""

    id: str
    name: str
    provider: str
    pricing_input: float
    pricing_output: float
    pricing_unit: str
    context_length: int
    capabilities: List[str]
    serverless: bool = False
    tunable: bool = False
    recommended: bool = False

    def __str__(self) -> str:
        """String representation of model."""
        caps = ", ".join(self.capabilities)
        return (
            f"{self.name}\n"
            f"  Provider: {self.provider}\n"
            f"  Context: {self.context_length:,} tokens\n"
            f"  Pricing: ${self.pricing_input:.2f}/$  {self.pricing_output:.2f} {self.pricing_unit}\n"
            f"  Capabilities: {caps}"
        )

    def format_pricing(self) -> str:
        """Format pricing for display."""
        return f"${self.pricing_input:.2f} in / ${self.pricing_output:.2f} out {self.pricing_unit}"


@dataclass
class ProviderInfo:
    """Information about a provider."""

    id: str
    name: str
    description: str
    api_key_env: str
    api_base_url: str
    models: Dict[str, ModelInfo]

    def list_models(self, capability: Optional[str] = None) -> List[ModelInfo]:
        """List all models, optionally filtered by capability."""
        models = list(self.models.values())
        if capability:
            models = [m for m in models if capability in m.capabilities]
        return sorted(models, key=lambda m: m.context_length, reverse=True)

    def get_recommended_model(self) -> Optional[ModelInfo]:
        """Get the recommended model for this provider."""
        for model in self.models.values():
            if model.recommended:
                return model
        # If no recommended, return first model
        return list(self.models.values())[0] if self.models else None


class ModelRegistry:
    """Registry for managing model and provider configurations."""

    def __init__(self, providers_dir: Optional[Path] = None):
        """Initialize model registry.

        Args:
            providers_dir: Path to providers directory containing JSON files
        """
        if providers_dir is None:
            providers_dir = Path(__file__).parent / "providers"

        self.providers_dir = providers_dir
        self.providers: Dict[str, ProviderInfo] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load model configuration from provider JSON files."""
        # Load all .json files from providers directory
        if not self.providers_dir.exists():
            # Fallback to legacy models.json if providers dir doesn't exist
            legacy_config = self.providers_dir.parent / "models.json"
            if legacy_config.exists():
                self._load_legacy_config(legacy_config)
            return

        for provider_file in self.providers_dir.glob("*.json"):
            with open(provider_file) as f:
                provider_data = json.load(f)

            provider_id = provider_data["id"]
            models = {}

            for model_key, model_data in provider_data["models"].items():
                models[model_key] = ModelInfo(
                    id=model_data["id"],
                    name=model_data["name"],
                    provider=model_data["provider"],
                    pricing_input=model_data["pricing"]["input"],
                    pricing_output=model_data["pricing"]["output"],
                    pricing_unit=model_data["pricing"]["unit"],
                    context_length=model_data["context_length"],
                    capabilities=model_data["capabilities"],
                    serverless=model_data.get("serverless", False),
                    tunable=model_data.get("tunable", False),
                    recommended=model_data.get("recommended", False),
                )

            self.providers[provider_id] = ProviderInfo(
                id=provider_id,
                name=provider_data["name"],
                description=provider_data["description"],
                api_key_env=provider_data["api_key_env"],
                api_base_url=provider_data["api_base_url"],
                models=models,
            )

    def _load_legacy_config(self, config_path: Path) -> None:
        """Load legacy models.json format for backward compatibility."""
        with open(config_path) as f:
            data = json.load(f)

        for provider_id, provider_data in data["providers"].items():
            models = {}
            for model_key, model_data in provider_data["models"].items():
                models[model_key] = ModelInfo(
                    id=model_data["id"],
                    name=model_data["name"],
                    provider=model_data["provider"],
                    pricing_input=model_data["pricing"]["input"],
                    pricing_output=model_data["pricing"]["output"],
                    pricing_unit=model_data["pricing"]["unit"],
                    context_length=model_data["context_length"],
                    capabilities=model_data["capabilities"],
                    serverless=model_data.get("serverless", False),
                    tunable=model_data.get("tunable", False),
                    recommended=model_data.get("recommended", False),
                )

            self.providers[provider_id] = ProviderInfo(
                id=provider_id,
                name=provider_data["name"],
                description=provider_data["description"],
                api_key_env=provider_data["api_key_env"],
                api_base_url=provider_data["api_base_url"],
                models=models,
            )

    def get_provider(self, provider_id: str) -> Optional[ProviderInfo]:
        """Get provider information by ID."""
        return self.providers.get(provider_id)

    def list_providers(self) -> List[ProviderInfo]:
        """List all available providers."""
        return list(self.providers.values())

    def get_model(self, provider_id: str, model_key: str) -> Optional[ModelInfo]:
        """Get model information by provider and model key."""
        provider = self.get_provider(provider_id)
        if provider:
            return provider.models.get(model_key)
        return None

    def find_model_by_id(self, model_id: str) -> Optional[tuple[str, str, ModelInfo]]:
        """Find a model by its full ID.

        Returns:
            Tuple of (provider_id, model_key, ModelInfo) or None
        """
        for provider_id, provider in self.providers.items():
            for model_key, model in provider.models.items():
                if model.id == model_id:
                    return (provider_id, model_key, model)
        return None

    def list_all_models(
        self,
        capability: Optional[str] = None,
        max_price: Optional[float] = None,
    ) -> List[tuple[str, ModelInfo]]:
        """List all models across all providers.

        Args:
            capability: Filter by capability (e.g., "vision", "code")
            max_price: Maximum output price per million tokens

        Returns:
            List of (provider_id, ModelInfo) tuples
        """
        models = []
        for provider_id, provider in self.providers.items():
            for model in provider.models.values():
                # Apply filters
                if capability and capability not in model.capabilities:
                    continue
                if max_price is not None and model.pricing_output > max_price:
                    continue
                models.append((provider_id, model))

        # Sort by price (output tokens)
        return sorted(models, key=lambda x: x[1].pricing_output)


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get the global model registry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
