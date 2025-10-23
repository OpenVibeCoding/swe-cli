"""Welcome banner and session info for SWE-CLI."""

from __future__ import annotations

import os
from itertools import zip_longest
from pathlib import Path
from typing import List, Optional, Tuple

from swecli.core.management import OperationMode
from swecli.ui.components.box_styles import BoxStyles


class WelcomeMessage:
    """Generate welcome banner and session information."""

    TOTAL_WIDTH = 110
    LEFT_WIDTH = 42
    RIGHT_WIDTH = TOTAL_WIDTH - 2 - LEFT_WIDTH - 1  # account for interior divider

    @staticmethod
    def get_version() -> str:
        """Get SWE-CLI version."""
        try:
            from importlib.metadata import version

            return f"v{version('swecli')}"
        except Exception:
            return "v0.3.0"  # Fallback version when metadata unavailable

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _inner_width(cls) -> int:
        return cls.TOTAL_WIDTH - 2

    @classmethod
    def _fit(cls, text: str, width: int) -> str:
        """Truncate text neatly to fit within the target width."""
        if len(text) <= width:
            return text.ljust(width)
        if width <= 1:
            return text[:width]
        return f"{text[: width - 1]}…"

    @classmethod
    def _format(cls, text: str, width: int, align: str = "left") -> str:
        """Format text with alignment while respecting width constraints."""
        if not text:
            base = "".ljust(width)
        else:
            truncated = text if len(text) <= width else cls._fit(text, width)
            if len(truncated) < width:
                if align == "center":
                    base = truncated.center(width)
                elif align == "right":
                    base = truncated.rjust(width)
                else:
                    base = truncated.ljust(width)
            else:
                base = truncated
        return base

    @classmethod
    def _two_column(
        cls,
        left: str,
        right: str,
        *,
        left_align: str = "left",
        right_align: str = "left",
    ) -> str:
        left_block = cls._format(left, cls.LEFT_WIDTH, align=left_align)
        right_block = cls._format(right, cls.RIGHT_WIDTH, align=right_align)
        # Use BoxStyles colors for consistent border styling
        return f"{BoxStyles.BORDER_COLOR}{BoxStyles.VERTICAL}{BoxStyles.RESET}{left_block}{BoxStyles.BORDER_COLOR}{BoxStyles.VERTICAL}{BoxStyles.RESET}{right_block}{BoxStyles.BORDER_COLOR}{BoxStyles.VERTICAL}{BoxStyles.RESET}"

    @classmethod
    def _header_line(cls, title: str) -> str:
        return BoxStyles.top_border(cls.TOTAL_WIDTH, title=title)

    @classmethod
    def _footer_line(cls) -> str:
        return BoxStyles.bottom_border(cls.TOTAL_WIDTH)

    @staticmethod
    def _shorten_path(path: Path, width: int) -> str:
        text = str(path.expanduser())
        if len(text) <= width:
            return text
        return f"…{text[-(width - 1):]}" if width > 1 else text[:width]

    # ------------------------------------------------------------------
    # Public generators
    # ------------------------------------------------------------------
    @classmethod
    def generate_banner(cls) -> List[str]:
        """Generate the top banner without session details."""
        version = cls.get_version()
        header = cls._header_line(f"SWE-CLI {version}")
        welcome_line = cls._two_column(
            "Welcome to your coding assistant",
            "Launch commands: /help · /mode plan · /mode normal",
            left_align="center",
        )
        footer = cls._footer_line()
        return [header, welcome_line, footer]

    @staticmethod
    def generate_commands_section() -> List[str]:
        """Provide quick command hints."""
        return [
            "Quick Commands",
            " • /help           Show available commands",
            " • /tree           Explore the project tree",
            " • /mode normal    Run with approvals",
            " • /mode plan      Plan without execution",
        ]

    @staticmethod
    def generate_shortcuts_section() -> List[str]:
        """Provide keyboard shortcut hints."""
        return [
            "Keyboard Shortcuts",
            " • Shift+Tab       Toggle plan/normal mode",
            " • @file           Mention a file for context",
            " • ↑ / ↓           Navigate command history",
            " • esc + c         Open the context panel",
        ]

    @staticmethod
    def generate_session_info(
        current_mode: OperationMode,
        working_dir: Optional[Path] = None,
        username: Optional[str] = None,
    ) -> List[str]:
        """Generate current session information."""

        cwd_path = working_dir or Path.cwd()
        cwd_display = WelcomeMessage._shorten_path(cwd_path, WelcomeMessage.LEFT_WIDTH)

        user = username or os.getenv("USER", "Developer")
        user_display = user.strip() or "Developer"

        mode = current_mode.value.upper()
        mode_desc = (
            "Plan mode · explore safely"
            if current_mode == OperationMode.PLAN
            else "Normal mode · approvals required"
        )

        return [
            "Workspace",
            cwd_display,
            "",
            f"Mode: {mode}",
            mode_desc,
            "",
            f"Signed in as {user_display}",
        ]

    @classmethod
    def generate_full_welcome(
        cls,
        current_mode: OperationMode,
        working_dir: Optional[Path] = None,
        username: Optional[str] = None,
    ) -> List[str]:
        """Generate a full welcome banner inspired by Claude Code."""

        version = cls.get_version()
        working_dir = working_dir or Path.cwd()
        user = username or os.getenv("USER", "Developer")
        user_display = user.strip() or "Developer"

        left_entries: List[Tuple[str, str]] = [
            ("", "left"),
            (f"Welcome back {user_display}!", "center"),
            ("", "left"),
            ("▐▛███▜▌", "center"),
            ("▝▜█████▛▘", "center"),
            ("▘▘ ▝▝", "center"),
            ("", "left"),
            ("Workspace", "left"),
            (cls._shorten_path(working_dir, cls.LEFT_WIDTH), "left"),
            ("", "left"),
            (f"Mode: {current_mode.value.upper()}", "left"),
            (
                "Plan mode · explore safely"
                if current_mode == OperationMode.PLAN
                else "Normal mode · approvals required",
                "left",
            ),
            ("", "left"),
            (f"Version {version}", "left"),
            ("SWE-CLI ready for your next prompt.", "left"),
        ]

        right_entries: List[Tuple[str, str]] = [
            ("", "left"),
            ("Quick Commands", "left"),
            (" • /help           Show available commands", "left"),
            (" • /tree           Explore the project tree", "left"),
            (" • /mode normal    Run with approvals", "left"),
            (" • /mode plan      Plan without execution", "left"),
            ("", "left"),
            ("Keyboard Shortcuts", "left"),
            (" • Shift+Tab       Toggle plan/normal mode", "left"),
            (" • @file           Mention a file for context", "left"),
            (" • ↑ / ↓           Navigate command history", "left"),
            (" • esc + c         Open the context panel", "left"),
            ("", "left"),
            ("Pro Tips", "left"),
            (" • /save session   Capture the current transcript", "left"),
            (" • esc + n         Notification shortcuts", "left"),
        ]

        rows: List[str] = []
        for (left_text, left_align), (right_text, right_align) in zip_longest(
            left_entries,
            right_entries,
            fillvalue=("", "left"),
        ):
            rows.append(
                cls._two_column(
                    left_text,
                    right_text,
                    left_align=left_align,
                    right_align=right_align,
                )
            )

        return [
            "",
            cls._header_line(f"SWE-CLI {version}"),
            *rows,
            cls._footer_line(),
        ]
