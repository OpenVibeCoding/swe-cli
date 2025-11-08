"""Autocomplete popup controller for the Textual chat app."""

from __future__ import annotations

from typing import Optional, Tuple

from rich.text import Text
from textual.widgets import Static

from swecli.ui_textual.utils.file_type_colors import FileTypeColors

StateType = Tuple[Tuple[Tuple[str, str], ...], int]


class AutocompletePopupController:
    """Encapsulates autocomplete popup rendering and deduplication."""

    def __init__(self, popup: Static) -> None:
        self.popup = popup
        self._last_state: StateType | None = None

    def reset(self) -> None:
        """Hide the popup and clear cached state."""
        self._last_state = None
        self.hide()

    def hide(self) -> None:
        """Hide the popup without clearing cached state."""
        self.popup.update("")
        self.popup.styles.display = "none"

    def render(
        self,
        entries: list[tuple[str, str]],
        selected_index: Optional[int] = None,
    ) -> None:
        """Render autocomplete suggestions."""

        if not entries:
            self.reset()
            return

        total = len(entries)
        limit = min(total, 5)
        active = selected_index if selected_index is not None else 0
        active = max(0, min(active, total - 1))

        window_start = 0
        if total > limit:
            window_start = max(0, active - limit + 1)
            window_start = min(window_start, total - limit)
        window_end = window_start + limit

        rows = [
            (label or "", meta or "")
            for label, meta in entries[window_start:window_end]
        ]

        window_active = active - window_start
        state: StateType = (tuple(rows), window_active)

        if state == self._last_state:
            self.popup.styles.display = "block"
            return

        text = Text()
        for index, (label, meta) in enumerate(rows):
            is_active = index == window_active

            # Detect if this is a directory
            is_dir = "📁" in label or label.endswith("/")

            # Get appropriate color for this file type
            file_color = FileTypeColors.get_color_from_icon_label(label)

            # Enhanced pointer styling
            pointer = "▸ " if is_active else "  "
            pointer_style = f"bold {file_color}" if is_active else "dim"

            # Apply file-type-specific colors
            if is_active:
                # Selected item: bold + file-type color
                label_style = f"bold {file_color}"
            else:
                # Non-selected: file-type color with slight dim
                label_style = file_color

            text.append(pointer, style=pointer_style)
            text.append(label, style=label_style)

            # Meta info (file size, description)
            if meta:
                text.append("  ")
                meta_style = "white" if is_active else "grey70"
                text.append(meta, style=meta_style)

            if index < len(rows) - 1:
                text.append("\n")

        self.popup.update(text)
        self.popup.styles.display = "block"
        self._last_state = state
