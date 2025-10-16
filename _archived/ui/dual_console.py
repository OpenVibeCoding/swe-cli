"""Dual console that outputs to both terminal and conversation buffer."""

from typing import Any, Optional
from rich.console import Console, RenderableType
from opencli.ui.conversation_buffer import ConversationBuffer


class DualConsole:
    """Console wrapper that outputs to both terminal and conversation buffer.

    This is a drop-in replacement for Rich Console that mirrors all output
    to a conversation buffer for later display in split-screen mode.
    """

    def __init__(self, console: Optional[Console] = None, buffer: Optional[ConversationBuffer] = None, split_mode: bool = False):
        """Initialize dual console.

        Args:
            console: Rich Console instance (creates new one if None)
            buffer: ConversationBuffer instance (creates new one if None)
            split_mode: If True, only populate buffer (don't print to console)
        """
        self._console = console if console is not None else Console()
        self._buffer = buffer if buffer is not None else ConversationBuffer()
        self._capture_enabled = True  # Can disable buffer capture if needed
        self._split_mode = split_mode  # If True, buffer-only mode

    @property
    def console(self) -> Console:
        """Get the underlying Rich Console.

        Returns:
            The wrapped Console instance
        """
        return self._console

    @property
    def buffer(self) -> ConversationBuffer:
        """Get the conversation buffer.

        Returns:
            The ConversationBuffer instance
        """
        return self._buffer

    @property
    def width(self) -> int:
        """Get terminal width.

        Returns:
            Terminal width in characters
        """
        return self._console.width

    @property
    def height(self) -> int:
        """Get terminal height.

        Returns:
            Terminal height in lines
        """
        return self._console.height

    def print(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        style: Optional[str] = None,
        justify: Optional[str] = None,
        overflow: Optional[str] = None,
        no_wrap: Optional[bool] = None,
        emoji: Optional[bool] = None,
        markup: Optional[bool] = None,
        highlight: Optional[bool] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: bool = True,
        soft_wrap: bool = False,
        new_line_start: bool = False,
    ) -> None:
        """Print to both console and buffer.

        This mirrors the Rich Console.print() signature and forwards to
        both the real console and the conversation buffer.

        Args:
            objects: Objects to print
            sep: String inserted between objects (default: " ")
            end: String appended after last object (default: "\\n")
            style: Style to apply
            justify: Text justification
            overflow: Overflow method
            no_wrap: Disable word wrapping
            emoji: Enable emoji code
            markup: Enable console markup
            highlight: Enable automatic highlighting
            width: Width to render
            height: Height to render
            crop: Crop output to fit terminal
            soft_wrap: Enable soft wrapping
            new_line_start: Start on new line
        """
        # Print to real console (skip if in split mode - buffer only)
        if not self._split_mode:
            self._console.print(
                *objects,
                sep=sep,
                end=end,
                style=style,
                justify=justify,
                overflow=overflow,
                no_wrap=no_wrap,
                emoji=emoji,
                markup=markup,
                highlight=highlight,
                width=width,
                height=height,
                crop=crop,
                soft_wrap=soft_wrap,
                new_line_start=new_line_start,
            )

        # Add to buffer (if capture enabled)
        if self._capture_enabled and len(objects) > 0:
            # If single object and it's already a Rich renderable, use it directly
            # Check for __rich_console__ method which all Rich renderables have
            if len(objects) == 1 and (
                hasattr(objects[0], "__rich_console__") or
                hasattr(objects[0], "__rich__")
            ):
                self._buffer.add(objects[0])
            else:
                # For text/multiple objects, create a Text renderable
                from rich.text import Text
                # Combine objects into string
                text_str = sep.join(str(obj) for obj in objects)
                text = Text(text_str, style=style)
                self._buffer.add(text)

    def enable_buffer_capture(self) -> None:
        """Enable capturing output to buffer."""
        self._capture_enabled = True

    def disable_buffer_capture(self) -> None:
        """Disable capturing output to buffer.

        Useful for temporary output that shouldn't be in conversation history.
        """
        self._capture_enabled = False

    def enable_split_mode(self) -> None:
        """Enable split mode (buffer-only, no console output)."""
        self._split_mode = True

    def disable_split_mode(self) -> None:
        """Disable split mode (normal dual output)."""
        self._split_mode = False

    def clear_buffer(self) -> None:
        """Clear the conversation buffer."""
        self._buffer.clear()

    # Delegate other commonly used methods to the wrapped console

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the wrapped console.

        This allows DualConsole to act as a complete drop-in replacement
        for Console by forwarding any methods we haven't explicitly wrapped.

        Args:
            name: Attribute name

        Returns:
            The attribute from the wrapped console
        """
        return getattr(self._console, name)
