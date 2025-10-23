"""Configuration models."""

import re
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ToolPermission(BaseModel):
    """Permission settings for a specific tool."""

    enabled: bool = True
    always_allow: bool = False
    deny_patterns: list[str] = Field(default_factory=list)
    compiled_patterns: list[re.Pattern[str]] = Field(default_factory=list, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """Compile regex patterns after initialization."""
        self.compiled_patterns = [re.compile(pattern) for pattern in self.deny_patterns]

    def is_allowed(self, target: str) -> bool:
        """Check if a target (file path, command, etc.) is allowed."""
        if not self.enabled:
            return False
        if self.always_allow:
            return True
        return not any(pattern.match(target) for pattern in self.compiled_patterns)


class PermissionConfig(BaseModel):
    """Global permission configuration."""

    file_write: ToolPermission = Field(default_factory=ToolPermission)
    file_read: ToolPermission = Field(default_factory=ToolPermission)
    bash: ToolPermission = Field(
        default_factory=lambda: ToolPermission(
            enabled=False,  # Disabled by default for safety
            always_allow=False,
            deny_patterns=["rm -rf /", "sudo *", "chmod -R 777"],
        )
    )
    git: ToolPermission = Field(default_factory=ToolPermission)
    web_fetch: ToolPermission = Field(default_factory=ToolPermission)


class AutoModeConfig(BaseModel):
    """Auto mode configuration."""

    enabled: bool = False
    max_operations: int = 10  # Max operations before requiring approval
    require_confirmation_after: int = 5  # Ask for confirmation after N operations
    dangerous_operations_require_approval: bool = True


class OperationConfig(BaseModel):
    """Operation-specific settings."""

    show_diffs: bool = True
    backup_before_edit: bool = True
    max_file_size: int = 1_000_000  # 1MB max file size
    allowed_extensions: list[str] = Field(default_factory=list)  # Empty = all allowed


class AppConfig(BaseModel):
    """Application configuration."""

    model_config = {"protected_namespaces": ()}

    # AI Provider settings - Three model system
    # Normal model: For standard coding tasks
    model_provider: str = "fireworks"
    model: str = "accounts/fireworks/models/qwen3-235b-a22b-instruct-2507"

    # Thinking model: For complex reasoning tasks (optional, falls back to normal if not set)
    model_thinking: Optional[str] = None
    model_thinking_provider: Optional[str] = None

    # Vision/Multi-modal model: For image processing tasks (optional, falls back to normal if not set)
    model_vlm: Optional[str] = None
    model_vlm_provider: Optional[str] = None

    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    max_tokens: int = 16384
    temperature: float = 0.6

    # Session settings
    auto_save_interval: int = 5  # Save every N turns
    max_context_tokens: int = 100000  # Dynamically set from model context_length (80%)

    # UI settings
    verbose: bool = False
    color_scheme: str = "monokai"
    show_token_count: bool = True

    # Permissions
    permissions: PermissionConfig = Field(default_factory=PermissionConfig)

    # Phase 2: Operation settings
    enable_bash: bool = False  # Require explicit enable for bash execution
    bash_timeout: int = 30  # Timeout in seconds for bash commands
    auto_mode: AutoModeConfig = Field(default_factory=AutoModeConfig)
    operation: OperationConfig = Field(default_factory=OperationConfig)
    max_undo_history: int = 50  # Maximum operations to track for undo

    # Paths
    swecli_dir: str = "~/.swecli"
    session_dir: str = "~/.swecli/sessions"
    log_dir: str = "~/.swecli/logs"
    command_dir: str = ".swecli/commands"

    @field_validator("model_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate model provider."""
        allowed = ["fireworks", "anthropic", "openai"]
        if v not in allowed:
            raise ValueError(f"model_provider must be one of {allowed}")
        return v

    def get_api_key(self) -> str:
        """Get API key from config or environment."""
        import os

        if self.api_key:
            return self.api_key

        if self.model_provider == "fireworks":
            key = os.getenv("FIREWORKS_API_KEY")
        elif self.model_provider == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY")
        else:
            key = os.getenv("OPENAI_API_KEY")

        if not key:
            raise ValueError(
                f"No API key found. Set {self.model_provider.upper()}_API_KEY environment variable"
            )
        return key

    def get_model_info(self):
        """Get model information from the registry.

        Returns:
            ModelInfo object or None if model not found
        """
        from swecli.config import get_model_registry

        registry = get_model_registry()
        result = registry.find_model_by_id(self.model)
        if result:
            return result[2]  # Return ModelInfo
        return None

    def get_provider_info(self):
        """Get provider information from the registry.

        Returns:
            ProviderInfo object or None if provider not found
        """
        from swecli.config import get_model_registry

        registry = get_model_registry()
        return registry.get_provider(self.model_provider)

    def get_thinking_model_info(self):
        """Get thinking model information, fallback to normal if not set.

        Returns:
            Tuple of (provider_id, model_id, ModelInfo) or None
        """
        from swecli.config import get_model_registry

        registry = get_model_registry()

        # Use thinking model if configured
        if self.model_thinking and self.model_thinking_provider:
            result = registry.find_model_by_id(self.model_thinking)
            if result:
                return result

        # Fallback to normal model
        result = registry.find_model_by_id(self.model)
        return result

    def get_vlm_model_info(self):
        """Get VLM model information, fallback to normal if not set.

        Returns:
            Tuple of (provider_id, model_id, ModelInfo) or None
        """
        from swecli.config import get_model_registry

        registry = get_model_registry()

        # Use VLM model if configured
        if self.model_vlm and self.model_vlm_provider:
            result = registry.find_model_by_id(self.model_vlm)
            if result:
                return result

        # Fallback to normal model if it has vision capability
        result = registry.find_model_by_id(self.model)
        if result:
            _, _, model_info = result
            if "vision" in model_info.capabilities:
                return result

        # No vision model available
        return None

    def should_use_provider_for_all(self, provider_id: str) -> bool:
        """Check if provider supports all capabilities in all models (OpenAI/Anthropic).

        For OpenAI and Anthropic, all models support text, vision, and code.
        For other providers (Fireworks), models have specific capabilities.

        Args:
            provider_id: Provider ID to check

        Returns:
            True if all models from this provider support all capabilities
        """
        return provider_id in ["openai", "anthropic"]
