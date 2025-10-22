"""Terminal-native message printer for unlimited scrollback."""

import sys
from typing import Optional


class TerminalMessagePrinter:
    """Prints messages directly to terminal for native scrollback support."""

    # ANSI color codes
    CYAN = "\033[36m"
    CYAN_BOLD = "\033[1;36m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    GRAY = "\033[90m"
    LIGHT_GREEN = "\033[92m"
    LIGHT_RED = "\033[91m"
    YELLOW = "\033[33m"
    WHITE = "\033[97m"
    RESET = "\033[0m"

    def __init__(self):
        """Initialize printer."""
        self.last_was_spinner = False

    def print_user_message(self, content: str) -> None:
        """Print user message with cyan prompt."""
        sys.stdout.write(f"\n{self.CYAN_BOLD}› {self.RESET}{content}\n")
        sys.stdout.flush()

    def print_assistant_message(self, content: str) -> None:
        """Print assistant message."""
        # Detect message type for appropriate styling
        if content.startswith("╭") or content.startswith("┌"):
            # Box formatting - keep as-is with colors
            if "✓" in content or "Result" in content:
                sys.stdout.write(f"\n{self.LIGHT_GREEN}{content}{self.RESET}\n")
            elif "Error" in content or "✗" in content:
                sys.stdout.write(f"\n{self.LIGHT_RED}{content}{self.RESET}\n")
            else:
                sys.stdout.write(f"\n{self.CYAN}{content}{self.RESET}\n")
        elif content.startswith("⏺"):
            # LLM response with ⏺ symbol
            sys.stdout.write(f"\n{content}\n")
        else:
            # Regular assistant message
            sys.stdout.write(f"\n{content}\n")

        sys.stdout.flush()

    def print_system_message(self, content: str) -> None:
        """Print system message in gray."""
        sys.stdout.write(f"\n{self.GRAY}{content}{self.RESET}\n")
        sys.stdout.flush()

    def print_spinner(self, text: str) -> None:
        """Print spinner message (inline, no newline)."""
        # Move to start of line and clear it
        sys.stdout.write(f"\r\033[K{text}")
        sys.stdout.flush()
        self.last_was_spinner = True

    def clear_spinner(self) -> None:
        """Clear the spinner line."""
        if self.last_was_spinner:
            sys.stdout.write("\r\033[K")  # Clear line
            sys.stdout.flush()
            self.last_was_spinner = False

    def print_welcome(self, lines: list[str]) -> None:
        """Print welcome banner."""
        sys.stdout.write("\n")
        for line in lines:
            sys.stdout.write(f"{line}\n")
        sys.stdout.write("\n")
        sys.stdout.flush()
