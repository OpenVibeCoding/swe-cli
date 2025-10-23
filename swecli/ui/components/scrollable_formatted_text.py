"""Scrollable formatted text control with ANSI support."""

from typing import Callable
from prompt_toolkit.layout.controls import UIControl, UIContent
from prompt_toolkit.formatted_text import FormattedText, ANSI, StyleAndTextTuples
from prompt_toolkit.layout.screen import WritePosition
from prompt_toolkit.mouse_events import MouseEvent


class ScrollableFormattedTextControl(UIControl):
    """A UIControl that displays formatted text with ANSI support and proper scrolling."""

    def __init__(self, get_text: Callable[[], str]):
        """
        Initialize scrollable formatted text control.

        Args:
            get_text: Callable that returns text with ANSI codes
        """
        self.get_text = get_text
        self.scroll_offset = 0
        self._auto_scroll = True  # Auto-scroll to bottom on new content

    def create_content(self, width: int, height: int) -> UIContent:
        """Create the UI content for this control."""
        # Get text with ANSI codes
        text = self.get_text()

        # Parse ANSI codes
        formatted_text = ANSI(text)

        # Convert to list of (style, text) tuples
        fragments = list(formatted_text.__pt_formatted_text__())

        # Split into lines
        lines = []
        current_line = []

        for style, text in fragments:
            if '\n' in text:
                # Split by newlines
                parts = text.split('\n')
                for i, part in enumerate(parts):
                    if part:
                        current_line.append((style, part))
                    if i < len(parts) - 1:  # Not the last part
                        lines.append(current_line)
                        current_line = []
            else:
                current_line.append((style, text))

        # Add remaining line
        if current_line:
            lines.append(current_line)

        # Handle empty content
        if not lines:
            lines = [[("", "")]]

        # Calculate scrolling
        total_lines = len(lines)

        # CRITICAL FIX: Reserve bottom padding to prevent visual overlap with separator
        # Always keep 2 blank lines at the bottom as a visual buffer
        BOTTOM_PADDING = 2
        effective_height = max(1, height - BOTTOM_PADDING)

        # Auto-scroll to bottom if enabled - use effective_height
        if self._auto_scroll:
            max_scroll = max(0, total_lines - effective_height)
            self.scroll_offset = max_scroll

        # Clamp scroll offset - adjust for padding
        max_scroll = max(0, total_lines - effective_height)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        # Get visible lines - only use effective_height, leaving room for padding
        start_line = self.scroll_offset
        end_line = min(start_line + effective_height, total_lines)
        visible_lines = lines[start_line:end_line]

        # Pad with empty lines to reach effective height
        while len(visible_lines) < effective_height:
            visible_lines.append([("", "")])

        # Add bottom padding (blank lines at the end)
        for _ in range(BOTTOM_PADDING):
            visible_lines.append([("", "")])

        # Create line list for UIContent
        def get_line(i):
            if i < len(visible_lines):
                return visible_lines[i]
            return [("", "")]

        return UIContent(
            get_line=get_line,
            line_count=height,  # Always return full height
            show_cursor=False,
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> "NotImplementedOrNone":
        """Handle mouse events for scrolling."""
        return NotImplemented

    def move_cursor_down(self) -> None:
        """Scroll down one line."""
        self._auto_scroll = False  # Disable auto-scroll when manually scrolling
        self.scroll_offset += 1

    def move_cursor_up(self) -> None:
        """Scroll up one line."""
        self._auto_scroll = False  # Disable auto-scroll when manually scrolling
        self.scroll_offset = max(0, self.scroll_offset - 1)

    def scroll_page_down(self, height: int) -> None:
        """Scroll down one page.

        If already near bottom, jump to bottom and re-enable auto-scroll.
        """
        # Calculate if we're scrolling near the bottom
        # Get current text to calculate total lines
        text = self.get_text()
        formatted_text = ANSI(text)
        fragments = list(formatted_text.__pt_formatted_text__())

        # Count total lines
        lines = []
        current_line = []
        for style, text_part in fragments:
            if '\n' in text_part:
                parts = text_part.split('\n')
                for i, part in enumerate(parts):
                    if part:
                        current_line.append((style, part))
                    if i < len(parts) - 1:
                        lines.append(current_line)
                        current_line = []
            else:
                current_line.append((style, text_part))
        if current_line:
            lines.append(current_line)

        total_lines = len(lines)
        BOTTOM_PADDING = 2
        effective_height = max(1, height - BOTTOM_PADDING)
        max_scroll = max(0, total_lines - effective_height)

        # If scrolling down would go past max, or we're close to bottom, jump to bottom
        if self.scroll_offset + height >= max_scroll:
            # Jump to bottom and re-enable auto-scroll
            self._auto_scroll = True
            self.scroll_offset = max_scroll
        else:
            # Normal page down
            self._auto_scroll = False
            self.scroll_offset += height

    def scroll_page_up(self, height: int) -> None:
        """Scroll up one page."""
        self._auto_scroll = False  # Disable auto-scroll when manually scrolling
        self.scroll_offset = max(0, self.scroll_offset - height)

    def scroll_to_bottom(self, total_height: int = None) -> None:
        """Scroll to the bottom and enable auto-scroll."""
        self._auto_scroll = True  # Re-enable auto-scroll
        # scroll_offset will be set automatically in create_content

    def is_focusable(self) -> bool:
        """This control can receive focus."""
        return True
