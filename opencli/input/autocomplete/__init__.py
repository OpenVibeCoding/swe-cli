"""Autocomplete system for OpenCLI."""

from .autocomplete_core import OpenCLIAutocompleteCore, FileMentionCompleter, SlashCommandCompleter
from .commands import SlashCommand, SlashCommandManager, DEFAULT_SLASH_COMMANDS
from .file_finder import FileFinder
from .completion_formatters import CompletionFormatter

__all__ = [
    "OpenCLIAutocompleteCore",
    "FileMentionCompleter",
    "SlashCommandCompleter",
    "SlashCommand",
    "SlashCommandManager",
    "DEFAULT_SLASH_COMMANDS",
    "FileFinder",
    "CompletionFormatter",
]