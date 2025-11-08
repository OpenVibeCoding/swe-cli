"""Shared components used across the Textual UI."""

from .box_styles import BoxStyles
from .console_animations import Spinner, FlashingSymbol, ProgressIndicator
from .tips import TipsManager
from .welcome import WelcomeMessage

__all__ = [
    "BoxStyles",
    "TipsManager",
    "WelcomeMessage",
    "Spinner",
    "FlashingSymbol",
    "ProgressIndicator",
]
