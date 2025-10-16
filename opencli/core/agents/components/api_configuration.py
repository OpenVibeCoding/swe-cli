"""Helpers for resolving API endpoints and headers."""

from __future__ import annotations

from typing import Tuple

from opencli.models.config import AppConfig


def resolve_api_config(config: AppConfig) -> Tuple[str, dict[str, str]]:
    """Return the API URL and headers according to the configured provider."""
    api_key = config.get_api_key()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    if config.model_provider == "fireworks":
        api_url = "https://api.fireworks.ai/inference/v1/chat/completions"
    elif config.model_provider == "openai":
        api_url = "https://api.openai.com/v1/chat/completions"
    else:
        api_url = f"{config.api_base_url}/chat/completions"

    return api_url, headers
