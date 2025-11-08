"""UI components for SWE-CLI."""

from swecli.ui_textual.components.console_animations import Spinner, FlashingSymbol, ProgressIndicator
from swecli.ui.components.status_line import StatusLine
from swecli.ui.components.notifications import NotificationCenter, Notification
from swecli.ui.autocomplete import (
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
