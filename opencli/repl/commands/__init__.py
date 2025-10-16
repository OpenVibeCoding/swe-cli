"""Command handlers for REPL.

This package contains all command handlers extracted from the main REPL class.
Each handler is responsible for a specific group of related commands.
"""

from opencli.repl.commands.base import CommandHandler, CommandResult
from opencli.repl.commands.session_commands import SessionCommands
from opencli.repl.commands.file_commands import FileCommands
from opencli.repl.commands.mode_commands import ModeCommands
from opencli.repl.commands.mcp_commands import MCPCommands
from opencli.repl.commands.help_command import HelpCommand

__all__ = [
    "CommandHandler",
    "CommandResult",
    "SessionCommands",
    "FileCommands",
    "ModeCommands",
    "MCPCommands",
    "HelpCommand",
]
