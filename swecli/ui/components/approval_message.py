"""Approval modal integrated as a conversation message."""

from typing import Tuple
from prompt_toolkit.formatted_text import FormattedText
import re


def create_approval_message(command: str, selected_index: int = 0) -> str:
    """Create approval message with elegant styling and selection indicator.

    Returns formatted text that can be added to conversation.
    """
    # Extract command type
    command_parts = command.split()
    command_type = command_parts[0] if command_parts else "this type of"

    # Truncate long commands for display
    display_command = command if len(command) <= 68 else command[:65] + "..."

    # ANSI color codes for elegant styling
    BORDER_COLOR = "\033[38;5;240m"  # Dim gray for borders
    TITLE_COLOR = "\033[1;36m"       # Bold cyan for title
    COMMAND_COLOR = "\033[38;5;147m" # Light purple for command
    SELECTED_COLOR = "\033[1;32m"    # Bold green for selected
    NORMAL_COLOR = "\033[38;5;250m"  # Light gray for options
    RESET = "\033[0m"

    # Box drawing characters - elegant rounded corners
    TOP_LEFT = "╭"
    TOP_RIGHT = "╮"
    BOTTOM_LEFT = "╰"
    BOTTOM_RIGHT = "╯"
    HORIZONTAL = "─"
    VERTICAL = "│"
    LEFT_T = "├"
    RIGHT_T = "┤"

    BOX_WIDTH = 80
    INNER_WIDTH = BOX_WIDTH - 4  # Account for borders and padding

    lines = []

    # Top border with elegant styling
    lines.append(f"{BORDER_COLOR}{TOP_LEFT}{HORIZONTAL * (BOX_WIDTH - 2)}{TOP_RIGHT}{RESET}")

    # Title - centered and prominent
    title = "⚠  Approval Required"
    title_padding = (INNER_WIDTH - len(title)) // 2
    lines.append(
        f"{BORDER_COLOR}{VERTICAL}{RESET} "
        f"{' ' * title_padding}{TITLE_COLOR}{title}{RESET}"
        f"{' ' * (INNER_WIDTH - len(title) - title_padding)} "
        f"{BORDER_COLOR}{VERTICAL}{RESET}"
    )

    # Separator
    lines.append(f"{BORDER_COLOR}{LEFT_T}{HORIZONTAL * (BOX_WIDTH - 2)}{RIGHT_T}{RESET}")

    # Command display - with subtle background effect
    command_label = "Command:"
    lines.append(
        f"{BORDER_COLOR}{VERTICAL}{RESET} "
        f"{NORMAL_COLOR}{command_label}{RESET} {COMMAND_COLOR}{display_command}{RESET}"
        f"{' ' * (INNER_WIDTH - len(command_label) - 1 - len(display_command))} "
        f"{BORDER_COLOR}{VERTICAL}{RESET}"
    )

    # Separator before options
    lines.append(f"{BORDER_COLOR}{LEFT_T}{HORIZONTAL * (BOX_WIDTH - 2)}{RIGHT_T}{RESET}")

    # Empty line for spacing
    lines.append(f"{BORDER_COLOR}{VERTICAL}{RESET} {' ' * INNER_WIDTH} {BORDER_COLOR}{VERTICAL}{RESET}")

    # Options with elegant indicator
    options = [
        ("1", "Yes, run this command"),
        ("2", f"Yes, and auto-approve all {command_type} commands"),
        ("3", "No, cancel and provide feedback"),
    ]

    for idx, (num, text) in enumerate(options):
        if idx == selected_index:
            # Selected option - bold green with arrow indicator
            indicator = f"{SELECTED_COLOR}❯{RESET}"
            num_display = f"{SELECTED_COLOR}{num}.{RESET}"
            text_display = f"{SELECTED_COLOR}{text}{RESET}"
            # Calculate actual display length (without ANSI codes)
            display_len = len(f"❯ {num}. {text}")
        else:
            # Unselected option - subtle gray
            indicator = " "
            num_display = f"{NORMAL_COLOR}{num}.{RESET}"
            text_display = f"{NORMAL_COLOR}{text}{RESET}"
            display_len = len(f"  {num}. {text}")

        content = f"{indicator} {num_display} {text_display}"
        padding = INNER_WIDTH - display_len
        lines.append(
            f"{BORDER_COLOR}{VERTICAL}{RESET} "
            f"{content}{' ' * padding} "
            f"{BORDER_COLOR}{VERTICAL}{RESET}"
        )

    # Empty line for spacing
    lines.append(f"{BORDER_COLOR}{VERTICAL}{RESET} {' ' * INNER_WIDTH} {BORDER_COLOR}{VERTICAL}{RESET}")

    # Helper text - subtle hint
    helper = "Use ↑↓ arrows or number keys to select, Enter to confirm, Esc to cancel"
    helper_padding = (INNER_WIDTH - len(helper)) // 2
    lines.append(
        f"{BORDER_COLOR}{VERTICAL}{RESET} "
        f"{' ' * helper_padding}{BORDER_COLOR}{helper}{RESET}"
        f"{' ' * (INNER_WIDTH - len(helper) - helper_padding)} "
        f"{BORDER_COLOR}{VERTICAL}{RESET}"
    )

    # Bottom border
    lines.append(f"{BORDER_COLOR}{BOTTOM_LEFT}{HORIZONTAL * (BOX_WIDTH - 2)}{BOTTOM_RIGHT}{RESET}")

    return "\n".join(lines)
