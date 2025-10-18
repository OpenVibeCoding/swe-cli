"""Status bar management for chat application."""

from prompt_toolkit.formatted_text import StyleAndTextTuples


def get_status_text() -> StyleAndTextTuples:
    """Get default status bar text."""
    # TODO: Connect to actual mode and context info
    return [
        ("", "⏵⏵ normal mode  •  Context: 95%  •  Ctrl+C to exit"),
    ]


class StatusBarManager:
    """Manages status bar content and formatting."""

    def __init__(self):
        """Initialize status bar manager."""
        self.mode = "normal"
        self.context_pct = 95.0
        self.custom_message = ""

    def set_mode(self, mode: str) -> None:
        """Set the current mode."""
        self.mode = mode

    def set_context_percentage(self, pct: float) -> None:
        """Set context usage percentage."""
        self.context_pct = pct

    def set_custom_message(self, message: str) -> None:
        """Set a custom status message."""
        self.custom_message = message

    def get_status_text(self) -> StyleAndTextTuples:
        """Get formatted status bar text."""
        if self.custom_message:
            return [("", self.custom_message)]

        mode_indicator = self._get_mode_indicator()
        context_info = f"Context: {self.context_pct:.0f}%"

        return [
            ("", f"⏵⏵ {mode_indicator} mode  •  {context_info}  •  Ctrl+C to exit"),
        ]

    def _get_mode_indicator(self) -> str:
        """Get mode indicator with color."""
        mode_colors = {
            "normal": "normal",
            "plan": "plan",
            "approval": "normal",
        }
        return self.mode