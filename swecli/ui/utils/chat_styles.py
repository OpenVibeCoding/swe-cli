"""Chat application styling and theme management."""

from prompt_toolkit.styles import Style


class ChatStyles:
    """Manages chat application styles and themes."""

    @staticmethod
    def create_style() -> Style:
        """Create the application style."""
        return Style.from_dict({
            # Conversation area
            "user-prompt": "#00FFFF bold",  # Cyan › symbol
            "user-message": "#FFFFFF",  # White user text
            "assistant-message": "#AAAAAA",  # Gray assistant text
            "tool-call": "#00CED1",  # Cyan for tool calls
            "tool-result": "#90EE90",  # Light green for results
            "tool-error": "#FF6B6B",  # Red for errors
            "system-message": "#888888 italic",  # Dimmed system messages

            # Status bar - clean, no background (like Claude Code)
            "status-bar": "#888888",
            "mode-normal": "#FFA500",  # Orange for normal mode
            "mode-plan": "#90EE90",  # Light green for plan mode
            "context-info": "#888888",  # Gray for context percentage

            # Input area - clean, no gray background
            "input-prompt": "#00FFFF bold",  # Cyan › symbol with bar
            "input-field": "#FFFFFF",  # White text, no background
            "input-frame": "#00FFFF bold",  # Cyan border for visibility
            "input-separator": "#1f2933",  # Subtle divider line

            # Autocomplete menu - elegant and minimalist
            "completion-menu": "bg:#000000",  # Black background
            "completion-menu.completion": "#FFFFFF",  # White text
            "completion-menu.completion.current": "bg:#1f2933 #00FFFF",  # Cyan text on dark gray
            "completion-menu.meta": "#888888",  # Gray metadata
        })

    @staticmethod
    def get_interrupted_message_content() -> str:
        """Get the interrupted message content with formatting."""
        return "\033[31m⏺ Interrupted by user\033[0m"

    @staticmethod
    def create_interrupted_box() -> str:
        """Create the interrupted message box formatting."""
        return "┌─ Interrupted ────────────────\n│ \033[31m⏺ Interrupted by user\033[0m\n└──────────────────────────────"