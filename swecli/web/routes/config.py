"""Configuration API endpoints."""

from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from swecli.web.state import get_state
from swecli.setup.providers import PROVIDERS

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdate(BaseModel):
    """Configuration update model."""
    model_provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@router.get("")
async def get_config() -> Dict[str, Any]:
    """Get current configuration.

    Returns:
        Current configuration (with masked API keys)

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        state = get_state()
        config = state.config_manager.get_config()

        # Mask API key
        api_key = config.api_key
        masked_key = None
        if api_key:
            if len(api_key) > 8:
                masked_key = f"{api_key[:4]}...{api_key[-4:]}"
            else:
                masked_key = "***"

        return {
            "model_provider": config.model_provider,
            "model": config.model,
            "api_key": masked_key,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "enable_bash": config.enable_bash,
            "working_directory": config.working_directory,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("")
async def update_config(update: ConfigUpdate) -> Dict[str, str]:
    """Update configuration.

    Args:
        update: Configuration updates

    Returns:
        Status response

    Raises:
        HTTPException: If update fails
    """
    try:
        state = get_state()
        config = state.config_manager.get_config()

        # Update fields if provided
        if update.model_provider is not None:
            config.model_provider = update.model_provider
        if update.model is not None:
            config.model = update.model
        if update.temperature is not None:
            config.temperature = update.temperature
        if update.max_tokens is not None:
            config.max_tokens = update.max_tokens

        # Save configuration
        state.config_manager.save_config()

        return {"status": "success", "message": "Configuration updated"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_providers() -> List[Dict[str, Any]]:
    """List all available AI providers.

    Returns:
        List of provider information

    Raises:
        HTTPException: If listing fails
    """
    try:
        providers = []
        for provider_id, provider_info in PROVIDERS.items():
            providers.append({
                "id": provider_id,
                "name": provider_info["name"],
                "description": provider_info["description"],
                "models": [
                    {
                        "id": model["id"],
                        "name": model["name"],
                        "description": model.get("description", ""),
                    }
                    for model in provider_info["models"]
                ]
            })

        return providers

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
