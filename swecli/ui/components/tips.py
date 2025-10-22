"""Tips system for displaying helpful hints below spinners."""

import random
from typing import List


class TipsManager:
    """Manages rotating tips displayed during processing."""

    # Collection of helpful tips about swecli features
    TIPS: List[str] = [
        "Create custom slash commands by adding .md files to .swecli/commands/",
        "Use @ to mention files and add them to context (e.g., @README.md)",
        "Press Shift+Tab to toggle between NORMAL and PLAN modes",
        "Use ↑↓ arrow keys to navigate through command history",
        "Use /help to see all available commands",
        "Use /tree to visualize your project structure",
        "Use /sessions to list all previous sessions",
        "Use /models to switch between different AI models",
        "Page Up/Page Down scroll through long conversations",
        "Press Esc to interrupt long-running operations",
        "Use /mode plan for read-only analysis and planning",
        "Use /mode normal for full execution with file writes",
        "Context compaction automatically manages long conversations",
        "MCP servers extend swecli with custom tools and capabilities",
        "Use /mcp list to see all available MCP servers",
        "Session auto-save preserves your work automatically",
        "Use /continue to resume your most recent session",
        "Use /clear to start a fresh conversation",
        "Approval rules can be customized for different operations",
        "Use /undo to revert the last operation",
    ]

    def __init__(self):
        """Initialize tips manager."""
        self._current_tip_index = 0
        self._random_mode = True  # Use random tips by default

    def get_next_tip(self) -> str:
        """Get the next tip to display.

        Returns:
            A tip string
        """
        if self._random_mode:
            return random.choice(self.TIPS)
        else:
            # Sequential mode (for testing or predictable behavior)
            tip = self.TIPS[self._current_tip_index]
            self._current_tip_index = (self._current_tip_index + 1) % len(self.TIPS)
            return tip

    def format_tip(self, tip: str, color: str = "\033[38;5;240m") -> str:
        """Format a tip with proper styling.

        Args:
            tip: The tip text
            color: ANSI color code for the tip (default: dim gray)

        Returns:
            Formatted tip string with prefix and styling
        """
        reset = "\033[0m"
        # Use Claude Code style: "⎿ Tip: ..." with indentation
        return f"{color}  ⎿ Tip: {tip}{reset}"
