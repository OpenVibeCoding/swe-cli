"""Configuration commands for REPL."""

import asyncio
from typing import TYPE_CHECKING

from rich.console import Console

from swecli.config import get_model_registry
from swecli.repl.commands.base import CommandHandler, CommandResult

if TYPE_CHECKING:
    from swecli.core.management import ConfigManager


class ConfigCommands(CommandHandler):
    """Handler for configuration-related commands: /models."""

    def __init__(
        self,
        console: Console,
        config_manager: "ConfigManager",
        chat_app=None,
    ):
        """Initialize config commands handler.

        Args:
            console: Rich console for output
            config_manager: Config manager instance
            chat_app: Chat application instance (for interactive modal)
        """
        super().__init__(console)
        self.config_manager = config_manager
        self.chat_app = chat_app

    def handle(self, args: str) -> CommandResult:
        """Handle config command (not used, individual methods called directly)."""
        raise NotImplementedError("Use specific methods: show_model_selector()")

    async def show_model_selector_async(self) -> CommandResult:
        """Show interactive model selector modal (async version).

        Returns:
            CommandResult indicating success or failure
        """
        if not self.chat_app:
            self.print_error("Interactive model selector not available in this mode")
            return CommandResult(success=False, message="Chat app not available")

        # Show the modal
        selected, item = await self.chat_app.model_selector_modal_manager.show_model_selector()

        if not selected or not item:
            self.print_warning("Model selection cancelled")
            return CommandResult(success=False, message="Selection cancelled")

        # Extract selection info
        provider_id = item["provider_id"]
        model_id = item["model_id"]

        # Switch to the selected model
        return self._switch_to_model(provider_id, model_id)

    def show_model_selector(self) -> CommandResult:
        """Show interactive model selector modal (sync wrapper).

        Returns:
            CommandResult indicating success or failure
        """
        # Run the async version
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.show_model_selector_async())

    def _switch_to_model(self, provider_id: str, model_id: str) -> CommandResult:
        """Switch to a specific model.

        Args:
            provider_id: Provider ID
            model_id: Model ID

        Returns:
            CommandResult indicating success or failure
        """
        registry = get_model_registry()
        config = self.config_manager.get_config()

        # Find the model
        result = registry.find_model_by_id(model_id)
        if not result:
            self.print_error(f"Model '{model_id}' not found")
            return CommandResult(success=False, message="Model not found")

        found_provider_id, _, model_info = result

        # Verify provider matches
        if found_provider_id != provider_id:
            self.print_error(f"Model provider mismatch")
            return CommandResult(success=False, message="Provider mismatch")

        # Check API key for new provider (silently - user will get error when they try to use it)
        if provider_id != config.model_provider:
            import os
            provider_info = registry.get_provider(provider_id)
            env_var = provider_info.api_key_env
            # Skip warning - let them discover missing API key when they try to use it

        # Update configuration
        old_max_context = config.max_context_tokens

        config.model_provider = provider_id
        config.model = model_info.id

        # Recalculate max_context_tokens based on new model
        config.max_context_tokens = int(model_info.context_length * 0.8)

        # Save configuration
        try:
            self.config_manager.save_config(config, global_config=True)

            # Update chat app context monitor if available
            if self.chat_app and hasattr(self.chat_app, 'context_monitor'):
                self.chat_app.context_monitor.context_limit = config.max_context_tokens

            # Refresh the UI (footer will show new model)
            if self.chat_app and hasattr(self.chat_app, 'app'):
                self.chat_app.app.invalidate()

            return CommandResult(
                success=True,
                message=f"Switched to {model_info.name}",
                data={"model": model_info, "provider": provider_id}
            )

        except Exception as e:
            self.print_error(f"Failed to save configuration: {e}")
            return CommandResult(success=False, message=str(e))
