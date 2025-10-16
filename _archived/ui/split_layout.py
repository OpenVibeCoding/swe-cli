"""Split-screen layout with scrollable conversation area and fixed input."""

from typing import Optional, List
from io import StringIO

from prompt_toolkit.application import Application
from prompt_toolkit.layout import (
    Layout,
    HSplit,
    VSplit,
    Window,
    FormattedTextControl,
    WindowAlign,
)
from prompt_toolkit.widgets import Frame
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import FormattedText
from rich.console import Console
from rich.text import Text

from opencli.ui.conversation_buffer import ConversationBuffer


class SplitScreenLayout:
    """Split-screen layout for chat interface.

    Provides:
    - Scrollable conversation area on top
    - Fixed input area at bottom
    - Auto-scrolling to latest messages
    """

    def __init__(self, buffer: ConversationBuffer, console_width: int = 80):
        """Initialize split-screen layout.

        Args:
            buffer: ConversationBuffer with chat history
            console_width: Width for rendering (default: 80)
        """
        self._buffer = buffer
        self._console_width = console_width
        self._scroll_offset = 0  # For manual scrolling
        self._auto_scroll = True  # Auto-scroll to bottom

        # Create formatted text control for conversation display
        self._conversation_control = FormattedTextControl(
            text=self._get_conversation_text,
            focusable=True,
        )

        # Create conversation window (scrollable)
        self._conversation_window = Window(
            content=self._conversation_control,
            wrap_lines=True,
            allow_scroll_beyond_bottom=False,
            always_hide_cursor=True,
        )

    def _get_conversation_text(self) -> FormattedText:
        """Get formatted text for conversation display.

        Renders all items in the buffer as formatted text.

        Returns:
            FormattedText for display
        """
        if self._buffer.is_empty():
            return FormattedText([("", "No messages yet...")])

        # Render each item in buffer to text
        lines = []

        for item in self._buffer.get_all():
            # Render Rich renderable to string
            rendered = self._render_rich_to_text(item)
            if rendered:
                lines.append(rendered)
                lines.append("")  # Add spacing between items

        # Combine all lines
        if lines:
            # Remove trailing empty line
            if lines and lines[-1] == "":
                lines = lines[:-1]
            return FormattedText([("", "\n".join(lines))])
        else:
            return FormattedText([("", "No content")])

    def _render_rich_to_text(self, renderable) -> str:
        """Render a Rich renderable to plain text.

        Args:
            renderable: Any Rich renderable object

        Returns:
            Plain text string
        """
        try:
            # Create a string buffer and console
            string_io = StringIO()
            temp_console = Console(
                file=string_io,
                width=self._console_width,
                force_terminal=False,
                legacy_windows=False,
            )

            # Render to the console
            temp_console.print(renderable, end="")

            # Get the rendered text
            result = string_io.getvalue()
            return result
        except Exception as e:
            # If rendering fails, return a safe fallback
            return f"[Error rendering: {str(e)}]"

    def get_layout_container(self) -> HSplit:
        """Get the layout container for the conversation area.

        This can be combined with an input area in an HSplit.

        Returns:
            HSplit container with conversation window
        """
        return HSplit([
            # Conversation area (takes all available space)
            self._conversation_window,
        ])

    def refresh(self) -> None:
        """Refresh the conversation display.

        Call this after adding new items to the buffer.
        """
        # Invalidate the control to force redraw
        if hasattr(self._conversation_control, '_invalidate'):
            self._conversation_control._invalidate()

    def scroll_to_bottom(self) -> None:
        """Scroll conversation to the bottom (latest messages)."""
        self._auto_scroll = True
        self._scroll_offset = 0
        self.refresh()

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll conversation up by N lines.

        Args:
            lines: Number of lines to scroll up
        """
        self._auto_scroll = False
        self._scroll_offset -= lines
        self.refresh()

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll conversation down by N lines.

        Args:
            lines: Number of lines to scroll down
        """
        self._scroll_offset += lines
        if self._scroll_offset >= 0:
            # At bottom, re-enable auto-scroll
            self._scroll_offset = 0
            self._auto_scroll = True
        self.refresh()

    @property
    def buffer(self) -> ConversationBuffer:
        """Get the conversation buffer.

        Returns:
            The ConversationBuffer instance
        """
        return self._buffer

    @property
    def conversation_window(self) -> Window:
        """Get the conversation window.

        Returns:
            The prompt_toolkit Window for the conversation
        """
        return self._conversation_window
