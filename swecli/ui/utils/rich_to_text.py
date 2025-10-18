"""Convert Rich renderables to plain text boxes for chat display."""

from io import StringIO
from rich.console import Console
from rich.panel import Panel
from typing import Any
import re


def rich_to_text_box(renderable: Any, width: int = 78) -> str:
    """
    Convert a Rich renderable (Panel, Table, etc.) to text with ANSI codes.

    Args:
        renderable: Any Rich renderable object
        width: Terminal width for rendering (default 78 for margin)

    Returns:
        Text representation with ANSI color codes preserved
    """
    # Create a console that renders to string WITH ANSI codes
    string_io = StringIO()
    temp_console = Console(
        file=string_io,
        width=width,
        force_terminal=True,  # Keep ANSI codes
        force_interactive=False,
        legacy_windows=False,
        markup=True,
        emoji=True,
        highlight=True,
        color_system="truecolor"
    )

    # Render the Rich object
    temp_console.print(renderable)

    # Get the output
    output = string_io.getvalue()

    # Remove trailing newline only
    if output.endswith('\n'):
        output = output[:-1]

    # DO NOT remove ANSI codes - they're needed for ScrollableFormattedTextControl
    return output


def _remove_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def panel_to_text_box(
    content: str,
    title: str = "",
    border_style: str = "blue",
    width: int = 80
) -> str:
    """
    Convert panel-style content to a text box with Unicode box drawing.

    Args:
        content: Content to display
        title: Optional title
        border_style: Color hint (not used in plain text, kept for API compat)
        width: Box width

    Returns:
        Text box with Unicode box drawing characters
    """
    # Calculate content width (account for borders and padding)
    content_width = width - 4  # 2 for borders, 2 for padding

    # Split content into lines and wrap if needed
    lines = []
    for line in content.split('\n'):
        if len(line) <= content_width:
            lines.append(line)
        else:
            # Simple wrapping
            while line:
                lines.append(line[:content_width])
                line = line[content_width:]

    # Build the box
    result = []

    # Top border
    if title:
        title_part = f"─ {title} "
        remaining = width - len(title_part) - 1
        result.append(f"┌{title_part}{'─' * remaining}┐")
    else:
        result.append(f"┌{'─' * (width - 2)}┐")

    # Content lines
    for line in lines:
        padding = width - len(line) - 4
        result.append(f"│ {line}{' ' * padding} │")

    # Bottom border
    result.append(f"└{'─' * (width - 2)}┘")

    return '\n'.join(result)
