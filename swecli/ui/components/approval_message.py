"""Approval modal integrated as a conversation message."""

from typing import Tuple
from prompt_toolkit.formatted_text import FormattedText


def create_approval_message(command: str, selected_index: int = 0) -> str:
    """Create approval message with selection indicator.

    Returns formatted text that can be added to conversation.
    """
    # Extract command type
    command_parts = command.split()
    command_type = command_parts[0] if command_parts else "this type of"

    # Truncate long commands
    display_command = command if len(command) <= 70 else command[:67] + "..."

    lines = []
    lines.append("╭" + "─" * 78 + "╮")
    lines.append("│ Do you want to proceed?" + " " * 54 + "│")
    lines.append("├" + "─" * 78 + "┤")
    lines.append(f"│ Command: {display_command}" + " " * (68 - len(display_command)) + "│")
    lines.append("├" + "─" * 78 + "┤")

    # Options with indicator
    options = [
        "1. Yes",
        f"2. Yes, and don't ask again for {command_type} commands",
        "3. No, and tell Claude what to do differently (esc)",
    ]

    for idx, option in enumerate(options):
        if idx == selected_index:
            indicator = "\033[1;32m❯\033[0m "
            text = f"\033[1;32m{option}\033[0m"
        else:
            indicator = "  "
            text = option

        content = f"{indicator}{text}"
        # Calculate padding (accounting for ANSI codes)
        import re
        content_len = len(re.sub(r'\033\[[0-9;]+m', '', content))
        padding = 78 - content_len - 2
        lines.append(f"│ {content}{' ' * padding}│")

    lines.append("╰" + "─" * 78 + "╯")

    return "\n".join(lines)
