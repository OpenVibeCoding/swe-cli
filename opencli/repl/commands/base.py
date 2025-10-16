"""Base command handler for REPL commands."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from rich.console import Console


@dataclass
class CommandResult:
    """Result of a command execution.

    Attributes:
        success: Whether the command executed successfully
        message: Optional message to display
        data: Optional data returned by the command
    """
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None


class CommandHandler(ABC):
    """Abstract base class for command handlers.

    Each command handler is responsible for executing a specific
    command or group of related commands.
    """

    def __init__(self, console: Console):
        """Initialize command handler.

        Args:
            console: Rich console for output
        """
        self.console = console

    @abstractmethod
    def handle(self, args: str) -> CommandResult:
        """Handle the command execution.

        Args:
            args: Command arguments (text after the command name)

        Returns:
            CommandResult with execution status and optional message
        """
        pass

    def print_success(self, message: str) -> None:
        """Print success message.

        Args:
            message: Message to display
        """
        self.console.print(f"[green]{message}[/green]")

    def print_error(self, message: str) -> None:
        """Print error message.

        Args:
            message: Error message to display
        """
        self.console.print(f"[red]{message}[/red]")

    def print_warning(self, message: str) -> None:
        """Print warning message.

        Args:
            message: Warning message to display
        """
        self.console.print(f"[yellow]{message}[/yellow]")

    def print_info(self, message: str) -> None:
        """Print info message.

        Args:
            message: Info message to display
        """
        self.console.print(f"[cyan]{message}[/cyan]")
