"""Completion strategies for different types of autocomplete."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, List

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText

from .commands import SlashCommand, CommandRegistry
from .utils import FileFinder, FileSizeFormatter


class CompletionStrategy(ABC):
    """Abstract base class for completion strategies."""

    @abstractmethod
    def get_completions(
        self, word: str, document: Document
    ) -> Iterable[Completion]:
        """Get completions for the given word.

        Args:
            word: Current word to complete
            document: Current document

        Yields:
            Completion objects
        """
        pass


class SlashCommandStrategy(CompletionStrategy):
    """Completion strategy for slash commands."""

    def __init__(self, command_registry: CommandRegistry):
        """Initialize slash command strategy.

        Args:
            command_registry: Registry of available commands
        """
        self.command_registry = command_registry

    def get_completions(
        self, word: str, document: Document
    ) -> Iterable[Completion]:
        """Get slash command completions.

        Args:
            word: Current word (starts with /)
            document: Current document

        Yields:
            Completion objects for matching commands
        """
        query = word[1:].lower()  # Remove leading /

        commands = self.command_registry.find_matching(query)

        for cmd in commands:
            start_position = -len(word)

            display = FormattedText([
                ("cyan", f"/{cmd.name:<16}"),
                ("", " "),
                ("class:completion-menu.meta", cmd.description),
            ])

            yield Completion(
                text=f"/{cmd.name}",
                start_position=start_position,
                display=display,
            )


class FileMentionStrategy(CompletionStrategy):
    """Completion strategy for file mentions (@)."""

    def __init__(self, working_dir: Path, file_finder: FileFinder):
        """Initialize file mention strategy.

        Args:
            working_dir: Working directory for file mentions
            file_finder: File finder utility
        """
        self.working_dir = working_dir
        self.file_finder = file_finder

    def get_completions(
        self, word: str, document: Document
    ) -> Iterable[Completion]:
        """Get file mention completions.

        Args:
            word: Current word (starts with @)
            document: Current document

        Yields:
            Completion objects for matching files
        """
        query = word[1:]  # Remove leading @

        files = self.file_finder.find_files(query)

        for file_path in files:
            start_position = -len(word)

            # Display relative path
            try:
                rel_path = file_path.relative_to(self.working_dir)
            except ValueError:
                rel_path = file_path

            # Get file size for display
            size_str = FileSizeFormatter.get_file_size(file_path)

            # Elegant formatted display (no @ prefix, with file size)
            if size_str:
                display = FormattedText([
                    ("", f"{str(rel_path):<50}"),
                    ("class:completion-menu.meta", f"{size_str:>10}"),
                ])
            else:
                display = FormattedText([
                    ("", str(rel_path)),
                ])

            yield Completion(
                text=f"@{rel_path}",
                start_position=start_position,
                display=display,
            )