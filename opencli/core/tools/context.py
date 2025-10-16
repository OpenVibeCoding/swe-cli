"""Shared context objects for tool execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolExecutionContext:
    """Holds runtime managers supplied during tool execution."""

    mode_manager: Any | None = None
    approval_manager: Any | None = None
    undo_manager: Any | None = None
