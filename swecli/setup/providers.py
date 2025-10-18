"""Provider definitions and model configurations."""

from typing import Dict, List, Any, Optional

# Provider configuration
PROVIDERS: Dict[str, Dict[str, Any]] = {
    "fireworks": {
        "name": "Fireworks AI",
        "description": "Fast, cost-effective (recommended)",
        "env_var": "FIREWORKS_API_KEY",
        "api_url": "https://api.fireworks.ai/inference/v1/chat/completions",
        "api_format": "openai",
        "models": [
            {
                "id": "accounts/fireworks/models/qwen3-235b-a22b-instruct-2507",
                "name": "Qwen 3 235B",
                "description": "Recommended - Fast & Smart",
            },
            {
                "id": "accounts/fireworks/models/llama-v3p3-70b-instruct",
                "name": "Llama 3.3 70B",
                "description": "Meta's latest",
            },
            {
                "id": "accounts/fireworks/models/glm-4p5",
                "name": "GLM 4.5",
                "description": "Chinese language optimized",
            },
            {
                "id": "accounts/fireworks/models/qwen2p5-72b-instruct",
                "name": "Qwen 2.5 72B",
                "description": "Balanced performance",
            },
        ],
    },
    "openai": {
        "name": "OpenAI",
        "description": "GPT-4, GPT-3.5-turbo",
        "env_var": "OPENAI_API_KEY",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "api_format": "openai",
        "models": [
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "description": "Most capable, 128K context",
            },
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "description": "High quality reasoning",
            },
            {
                "id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "description": "Fast & affordable",
            },
        ],
    },
    "anthropic": {
        "name": "Anthropic",
        "description": "Claude 3.5 Sonnet, Opus",
        "env_var": "ANTHROPIC_API_KEY",
        "api_url": "https://api.anthropic.com/v1/messages",
        "api_format": "anthropic",
        "models": [
            {
                "id": "claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet",
                "description": "Best balance of speed & intelligence",
            },
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "description": "Most capable, deep reasoning",
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "description": "Fast & affordable",
            },
        ],
    },
}


def get_provider_config(provider_id: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific provider."""
    return PROVIDERS.get(provider_id)


def get_provider_models(provider_id: str) -> List[Dict[str, str]]:
    """Get available models for a provider."""
    provider = PROVIDERS.get(provider_id)
    if not provider:
        return []
    return provider.get("models", [])


def get_provider_choices() -> List[tuple[str, str, str]]:
    """Get provider choices for the wizard menu.

    Returns:
        List of (id, name, description) tuples
    """
    return [
        (key, config["name"], config["description"])
        for key, config in PROVIDERS.items()
    ]
