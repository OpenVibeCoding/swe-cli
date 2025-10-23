"""Layout management for SWE-CLI chat interface."""

from __future__ import annotations

import shutil
from typing import Tuple

from prompt_toolkit.layout.containers import (
    HSplit,
    VSplit,
    Window,
    WindowAlign,
    Float,
    FloatContainer,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.dimension import Dimension


class LayoutManager:
    """Manages the application layout and window arrangement."""

    def __init__(self, chat_app):
        """Initialize layout manager.

        Args:
            chat_app: The ChatApplication instance for callbacks
        """
        self.chat_app = chat_app
        self.conversation_control = None
        self.conversation_window = None
        self.input_control = None

    def create_layout(self) -> Layout:
        """Create and configure the application layout.

        Returns:
            Configured Layout instance
        """
        # Create conversation area
        self._create_conversation_area()

        # Create status bar
        status_window = self._create_status_bar()

        # Create input area
        input_container = self._create_input_area()

        # Create separator
        separator_window = self._create_separator()

        # Create main layout
        root_container = HSplit([
            self.conversation_window,
            separator_window,
            input_container,
            status_window,
        ])

        # Wrap in FloatContainer to support floating completion menu
        container_with_floats = FloatContainer(
            content=root_container,
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16),
                ),
            ],
        )

        return Layout(container_with_floats, focused_element=self.chat_app.input_buffer)

    def _create_conversation_area(self) -> None:
        """Create the conversation display area."""
        from swecli.ui.components.scrollable_formatted_text import ScrollableFormattedTextControl

        self.conversation_control = ScrollableFormattedTextControl(
            get_text=self.chat_app.conversation.get_plain_text,
        )

        # NO max height - allow conversation to grow infinitely for true unlimited scrollback
        # The terminal's native scrollback buffer will handle viewing older messages
        self.conversation_window = Window(
            content=self.conversation_control,
            wrap_lines=False,
            always_hide_cursor=True,
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )

    def _create_status_bar(self) -> Window:
        """Create the status bar component.

        Returns:
            Window containing the status bar
        """
        status_control = FormattedTextControl(
            text=self.chat_app._get_status_text,
        )

        return Window(
            content=status_control,
            height=2,  # Two lines: mode/context + models
            style="class:status-bar",
            align=WindowAlign.LEFT,
            wrap_lines=False,
            dont_extend_width=True,
        )

    def _create_input_area(self) -> VSplit:
        """Create the input area with prompt and input field.

        Returns:
            VSplit container with prompt and input
        """
        # Input field with prompt
        # Store reference so we can swap buffers during approval mode
        self.input_control = BufferControl(
            buffer=self.chat_app.input_buffer,
            focus_on_click=True,
        )

        # Prompt for input field
        prompt_window = Window(
            content=FormattedTextControl(text="┃ › "),
            width=4,
            style="class:input-prompt",
        )

        # Input window
        input_window = Window(
            content=self.input_control,
            height=Dimension(min=3, max=8, preferred=3),
            wrap_lines=True,
            style="class:input-field",
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )

        # Combine prompt and input
        return VSplit([
            prompt_window,
            input_window,
        ])

    def _create_separator(self) -> Window:
        """Create the separator line between conversation and input.

        Returns:
            Window containing the separator
        """
        return Window(
            height=1,
            char="─",
            style="class:input-separator",
        )

    def get_conversation_control(self):
        """Get the conversation display control.

        Returns:
            ScrollableFormattedTextControl instance
        """
        return self.conversation_control

    def get_input_control(self):
        """Get the input buffer control.

        Returns:
            BufferControl instance
        """
        return self.input_control

    def get_conversation_window(self):
        """Get the conversation window.

        Returns:
            Window instance
        """
        return self.conversation_window

    def update_status_text_callback(self) -> None:
        """Update status text callback when needed."""
        # This can be called to refresh the status bar
        if hasattr(self.chat_app, 'app'):
            self.chat_app.app.invalidate()