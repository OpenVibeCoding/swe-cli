"""Chat application layout management."""

import shutil
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


class ChatLayout:
    """Manages the chat application layout."""

    def __init__(self, conversation_control, input_buffer, input_control):
        """Initialize layout manager.

        Args:
            conversation_control: Control for conversation display
            input_buffer: Buffer for user input
            input_control: Control for input field
        """
        self.conversation_control = conversation_control
        self.input_buffer = input_buffer
        self.input_control = input_control
        self._conversation_window = None

    def create_layout(self) -> Layout:
        """Create the complete application layout."""
        # Create conversation area
        conversation_window = self._create_conversation_window()

        # Create status bar
        status_window = self._create_status_window()

        # Create input area
        input_container = self._create_input_container()

        # Create separator
        separator_window = self._create_separator()

        # Assemble main layout
        root_container = self._assemble_main_layout(
            conversation_window, separator_window, input_container, status_window
        )

        # Add floating completion menu
        container_with_floats = self._add_completion_menu_float(root_container)

        return Layout(container_with_floats, focused_element=self.input_buffer)

    def _create_conversation_window(self) -> Window:
        """Create the conversation display window."""
        # Calculate max height for conversation window
        # Must reserve space for: separator(1) + input(max=8) + status(1) + safety(2) = 12 lines
        terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        terminal_height = terminal_size.lines
        conversation_max_height = terminal_height - 12

        self._conversation_window = Window(
            content=self.conversation_control,
            height=Dimension(max=conversation_max_height),  # CRITICAL: enforce max height
            wrap_lines=False,
            always_hide_cursor=True,
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )
        return self._conversation_window

    def _create_status_window(self) -> Window:
        """Create the status bar window."""
        from swecli.ui.layout.status_bar import get_status_text

        status_control = FormattedTextControl(text=get_status_text)

        return Window(
            content=status_control,
            height=1,
            style="class:status-bar",
            align=WindowAlign.LEFT,
        )

    def _create_input_container(self) -> VSplit:
        """Create the input field with prompt."""
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
        return VSplit([prompt_window, input_window])

    def _create_separator(self) -> Window:
        """Create the separator line between conversation and input."""
        return Window(
            height=1,
            char="─",
            style="class:input-separator",
        )

    def _assemble_main_layout(self, conversation_window: Window,
                             separator_window: Window,
                             input_container: VSplit,
                             status_window: Window) -> HSplit:
        """Assemble the main layout components."""
        return HSplit([
            conversation_window,
            separator_window,
            input_container,
            status_window,
        ])

    def _add_completion_menu_float(self, root_container: HSplit) -> FloatContainer:
        """Wrap the layout with a completion menu float."""
        return FloatContainer(
            content=root_container,
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16),
                ),
            ],
        )