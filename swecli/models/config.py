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

    # AI Provider settings
    model_provider: str = "fireworks"
    model: str = "accounts/fireworks/models/qwen3-235b-a22b-instruct-2507"
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    max_tokens: int = 16384
    temperature: float = 0.6

    # Session settings
    auto_save_interval: int = 5  # Save every N turns
    max_context_tokens: int = 100000

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
