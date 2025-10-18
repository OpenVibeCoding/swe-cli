"""Toolbar component for REPL bottom status bar."""

from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import FormattedText

if TYPE_CHECKING:
    from swecli.core.management import ModeManager, SessionManager, OperationMode
    from swecli.models.config import Config


class Toolbar:
    """Generates bottom toolbar showing mode, shortcuts, and context."""

    def __init__(
        self,
        mode_manager: "ModeManager",
        session_manager: "SessionManager",
        config: "Config",
    ):
        """Initialize toolbar.

        Args:
            mode_manager: Mode manager for current mode
            session_manager: Session manager for token tracking
            config: Configuration for token limits
        """
        self.mode_manager = mode_manager
        self.session_manager = session_manager
        self.config = config

    def build_tokens(self) -> FormattedText:
        """Generate bottom toolbar text showing mode and shortcuts.

        Returns:
            FormattedText for bottom toolbar
        """
        from swecli.core.management import OperationMode

        mode = self.mode_manager.current_mode.value.upper()
        limit = self.config.max_context_tokens or 1
        used = (
            self.session_manager.current_session.total_tokens()
            if self.session_manager.current_session
            else 0
        )
        remaining_pct = max(0.0, 100.0 - (used / limit * 100.0))

        mode_style = (
            'fg:#ff9f43 bold'
            if self.mode_manager.current_mode == OperationMode.NORMAL
            else 'fg:#2ecc71 bold'
        )

        # Extract readable model name (last part after /)
        model_name = self.config.model.split('/')[-1] if self.config.model else 'unknown'
        provider_name = self.config.model_provider.capitalize()

        return FormattedText(
            [
                (mode_style, f" {mode} "),
                (
                    'fg:#aaaaaa',
                    " • Shift+Tab: Toggle Mode • Ctrl+C: Exit • Context Left: ",
                ),
                ('fg:#aaaaaa', f"{remaining_pct:.0f}% "),
                ('fg:#aaaaaa', f"• {provider_name}: "),
                ('fg:#6c5ce7', f"{model_name} "),
            ]
        )
