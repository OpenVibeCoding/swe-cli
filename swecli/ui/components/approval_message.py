"""Approval modal integrated as a conversation message."""

from typing import Tuple
from prompt_toolkit.formatted_text import FormattedText
import re

from swecli.ui.components.box_styles import BoxStyles


def create_approval_message(command: str, selected_index: int = 0) -> str:
    """Create approval message with elegant styling and selection indicator.

    Returns formatted text that can be added to conversation.
    """
    # Extract command type
    command_parts = command.split()
    command_type = command_parts[0] if command_parts else "this type of"

    # Truncate long commands for display
    display_command = command if len(command) <= 68 else command[:65] + "..."

    BOX_WIDTH = BoxStyles.STANDARD_WIDTH
    INNER_WIDTH = BOX_WIDTH - 4  # Account for borders and padding

    lines = []

    # Top border
    lines.append(BoxStyles.top_border(BOX_WIDTH))

    # Title - centered and prominent
    title = "⚠  Approval Required"
    lines.append(BoxStyles.title_line(title, BOX_WIDTH, centered=True))

    # Separator
    lines.append(BoxStyles.separator(BOX_WIDTH))

    # Command display - with accent color
    command_label = "Command:"
    command_content = f"{BoxStyles.NORMAL_COLOR}{command_label}{BoxStyles.RESET} {BoxStyles.ACCENT_COLOR}{display_command}{BoxStyles.RESET}"
    lines.append(BoxStyles.content_line(command_content, BOX_WIDTH))

    # Separator before options
    lines.append(BoxStyles.separator(BOX_WIDTH))

    # Empty line for spacing
    lines.append(BoxStyles.empty_line(BOX_WIDTH))

    # Options with elegant indicator
    options = [
        ("1", "Yes, run this command"),
        ("2", f"Yes, and auto-approve all {command_type} commands"),
        ("3", "No, cancel and provide feedback"),
    ]

    for idx, (num, text) in enumerate(options):
        if idx == selected_index:
            # Selected option - bold green with arrow indicator
            option_content = f"{BoxStyles.SUCCESS_COLOR}❯ {num}. {text}{BoxStyles.RESET}"
        else:
            # Unselected option - subtle gray
            option_content = f"  {BoxStyles.NORMAL_COLOR}{num}. {text}{BoxStyles.RESET}"

        lines.append(BoxStyles.content_line(option_content, BOX_WIDTH))

    # Empty line for spacing
    lines.append(BoxStyles.empty_line(BOX_WIDTH))

    # Helper text - subtle hint centered
    helper = "Use ↑↓ arrows or number keys to select, Enter to confirm, Esc to cancel"
    helper_content = f"{BoxStyles.DIM_COLOR}{helper}{BoxStyles.RESET}"
    lines.append(BoxStyles.content_line(helper_content, BOX_WIDTH))

    # Bottom border
    lines.append(BoxStyles.bottom_border(BOX_WIDTH))

    return "\n".join(lines)
