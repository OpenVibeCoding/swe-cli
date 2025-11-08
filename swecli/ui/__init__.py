"""UI components for SWE-CLI."""

from swecli.ui_textual.components.console_animations import Spinner, FlashingSymbol, ProgressIndicator
from swecli.ui_textual.components.status_line import StatusLine
from swecli.ui_textual.components import NotificationCenter, Notification
from swecli.ui_textual.autocomplete import (
    SwecliCompleter,
    FileMentionCompleter,
    SlashCommandCompleter,
    SlashCommand,
    SLASH_COMMANDS,
)

__all__ = [
    "Spinner",
    "FlashingSymbol",
    "ProgressIndicator",
    "StatusLine",
    "NotificationCenter",
    "Notification",
    "SwecliCompleter",
    "FileMentionCompleter",
    "SlashCommandCompleter",
    "SlashCommand",
    "SLASH_COMMANDS",
]
