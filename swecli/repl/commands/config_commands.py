"""Configuration commands for REPL."""

from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

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
    ):
        """Initialize config commands handler.

        Args:
            console: Rich console for output
            config_manager: Config manager instance
        """
        super().__init__(console)
        self.config_manager = config_manager

    def handle(self, args: str) -> CommandResult:
        """Handle config command (not used, individual methods called directly)."""
        raise NotImplementedError("Use specific methods: switch_model()")

    def switch_model(self, args: str) -> CommandResult:
        """Switch AI model/provider.

        Args:
            args: Arguments - empty shows current, provider shows models, provider+model switches

        Returns:
            CommandResult indicating success or failure
        """
        registry = get_model_registry()
        config = self.config_manager.get_config()

        # Parse arguments
        parts = args.strip().split() if args.strip() else []

        # Case 1: No args - show current model and list providers
        if not parts:
            return self._show_current_and_providers(config, registry)

        # Case 2: Provider only - list models for that provider
        if len(parts) == 1:
            provider_id = parts[0].lower()
            return self._list_provider_models(provider_id, registry)

        # Case 3: Provider + model - switch to that model
        if len(parts) >= 2:
            provider_id = parts[0].lower()
            model_id = " ".join(parts[1:])  # Handle multi-word model IDs
            return self._switch_to_model(provider_id, model_id, config, registry)

        return CommandResult(success=False, message="Invalid arguments")

    def _show_current_and_providers(self, config, registry) -> CommandResult:
        """Show current model and list all providers."""
        # Show current model
        model_info = config.get_model_info()
        if model_info:
            self.console.print("\n[bold cyan]Current Model:[/bold cyan]")
            self.console.print(f"  Provider: [yellow]{config.model_provider}[/yellow]")
            self.console.print(f"  Model: [green]{model_info.name}[/green]")
            self.console.print(f"  Context: [blue]{model_info.context_length:,}[/blue] tokens")
            self.console.print(f"  Pricing: {model_info.format_pricing()}")
            self.console.print(f"  Max context: [blue]{config.max_context_tokens:,}[/blue] tokens (80%)")
        else:
            self.print_warning("Current model not found in registry")

        # List all providers
        self.console.print("\n[bold cyan]Available Providers:[/bold cyan]")

        table = Table(show_header=True, header_style="bold cyan", border_style="dim")
        table.add_column("Provider", style="yellow")
        table.add_column("Models", style="dim")
        table.add_column("Description")

        for provider_info in registry.list_providers():
            table.add_row(
                provider_info.id,
                str(len(provider_info.models)),
                provider_info.description,
            )

        self.console.print(table)
        self.console.print("\n[dim]Usage:[/dim]")
        self.console.print("  [cyan]/models <provider>[/cyan] - List models for a provider")
        self.console.print("  [cyan]/models <provider> <model_id>[/cyan] - Switch to a model")

        return CommandResult(success=True)

    def _list_provider_models(self, provider_id: str, registry) -> CommandResult:
        """List all models for a specific provider."""
        provider_info = registry.get_provider(provider_id)

        if not provider_info:
            self.print_error(f"Provider '{provider_id}' not found")
            self.console.print("\n[dim]Available providers: fireworks, anthropic, openai[/dim]")
            return CommandResult(success=False, message=f"Provider not found: {provider_id}")

        self.console.print(f"\n[bold cyan]Models for {provider_info.name}:[/bold cyan]\n")

        # Create table with model details
        table = Table(show_header=True, header_style="bold cyan", border_style="dim", expand=True)
        table.add_column("Model ID", style="green", no_wrap=False)
        table.add_column("Name", style="yellow")
        table.add_column("Context", justify="right", style="blue")
        table.add_column("Pricing", style="dim")
        table.add_column("Features", style="magenta")

        for model_info in provider_info.list_models():
            # Format capabilities
            caps = ", ".join(model_info.capabilities)

            # Add recommended marker
            name = model_info.name
            if model_info.recommended:
                name = f"⭐ {name}"

            table.add_row(
                model_info.id,
                name,
                f"{model_info.context_length // 1000}k",
                model_info.format_pricing(),
                caps,
            )

        self.console.print(table)
        self.console.print(f"\n[dim]Usage:[/dim]")
        self.console.print(f"  [cyan]/models {provider_id} <model_id>[/cyan] - Switch to a model")

        return CommandResult(success=True)

    def _switch_to_model(
        self, provider_id: str, model_id: str, config, registry
    ) -> CommandResult:
        """Switch to a specific model."""
        # Validate provider
        provider_info = registry.get_provider(provider_id)
        if not provider_info:
            self.print_error(f"Provider '{provider_id}' not found")
            return CommandResult(success=False, message=f"Provider not found: {provider_id}")

        # Find the model - try exact match first, then fuzzy match
        model_info = None

        # Try direct lookup by model key
        if model_id in provider_info.models:
            model_info = provider_info.models[model_id]
        else:
            # Try to find by full model ID
            result = registry.find_model_by_id(model_id)
            if result:
                found_provider_id, _, found_model = result
                if found_provider_id == provider_id:
                    model_info = found_model
                else:
                    self.print_error(
                        f"Model '{model_id}' belongs to provider '{found_provider_id}', not '{provider_id}'"
                    )
                    return CommandResult(success=False, message="Model provider mismatch")

        if not model_info:
            self.print_error(f"Model '{model_id}' not found in provider '{provider_id}'")
            self.console.print(f"\n[dim]Use:[/dim] [cyan]/models {provider_id}[/cyan] to see available models")
            return CommandResult(success=False, message=f"Model not found: {model_id}")

        # Check API key for new provider
        if provider_id != config.model_provider:
            try:
                # Test if API key is available for the new provider
                import os
                env_var = provider_info.api_key_env
                if not os.getenv(env_var) and not config.api_key:
                    self.print_warning(
                        f"No API key found for {provider_info.name}. "
                        f"Set ${env_var} environment variable."
                    )
            except Exception:
                pass

        # Update configuration
        old_model = config.model
        old_provider = config.model_provider
        old_max_context = config.max_context_tokens

        config.model_provider = provider_id
        config.model = model_info.id

        # Recalculate max_context_tokens based on new model
        config.max_context_tokens = int(model_info.context_length * 0.8)

        # Save configuration
        try:
            self.config_manager.save_config(config, global_config=True)

            self.print_success(f"✓ Switched to {model_info.name}")
            self.console.print(f"  Provider: [yellow]{provider_id}[/yellow]")
            self.console.print(f"  Model: [green]{model_info.name}[/green]")
            self.console.print(f"  Context: [blue]{model_info.context_length:,}[/blue] tokens")
            self.console.print(f"  Max context: [blue]{config.max_context_tokens:,}[/blue] tokens (80%)")
            self.console.print(f"  Pricing: {model_info.format_pricing()}")

            if config.max_context_tokens != old_max_context:
                change = "increased" if config.max_context_tokens > old_max_context else "decreased"
                self.console.print(
                    f"\n[dim]Note: Max context {change} from "
                    f"{old_max_context:,} to {config.max_context_tokens:,} tokens[/dim]"
                )

            return CommandResult(
                success=True,
                message=f"Switched to {model_info.name}",
                data={"model": model_info, "provider": provider_id}
            )

        except Exception as e:
            # Rollback on error
            config.model = old_model
            config.model_provider = old_provider
            config.max_context_tokens = old_max_context

            self.print_error(f"Failed to save configuration: {e}")
            return CommandResult(success=False, message=str(e))
