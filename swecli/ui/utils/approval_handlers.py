"""Approval mode handlers for keyboard navigation."""

from swecli.ui.components.approval_message import create_approval_message


class ApprovalHandlers:
    """Handles approval mode keyboard navigation and selection."""

    def __init__(self, app):
        """Initialize approval handlers.

        Args:
            app: The chat application instance
        """
        self.app = app

    def handle_approval_up(self) -> bool:
        """Handle up arrow in approval mode."""
        if hasattr(self.app, "_approval_mode") and self.app._approval_mode:
            if self.app._approval_selected_index > 0:
                self.app._approval_selected_index -= 1
                self._update_approval_message()
            return True
        return False

    def handle_approval_down(self) -> bool:
        """Handle down arrow in approval mode."""
        if hasattr(self.app, "_approval_mode") and self.app._approval_mode:
            if self.app._approval_selected_index < 2:
                self.app._approval_selected_index += 1
                self._update_approval_message()
            return True
        return False

    def handle_approval_enter(self) -> bool:
        """Handle enter in approval mode."""
        if hasattr(self.app, "_approval_mode") and self.app._approval_mode:
            if self.app._approval_selected_index == 0:
                self.app._approval_result["approved"] = True
                self.app._approval_result["choice"] = "1"
            elif self.app._approval_selected_index == 1:
                self.app._approval_result["approved"] = True
                self.app._approval_result["choice"] = "2"
            else:
                self.app._approval_result["approved"] = False
                self.app._approval_result["choice"] = "3"
            self.app._approval_result["done"] = True
            return True
        return False

    def handle_approval_key(self, key: str) -> bool:
        """Handle number keys and escape in approval mode."""
        if hasattr(self.app, "_approval_mode") and self.app._approval_mode:
            if key == "1":
                self.app._approval_result["approved"] = True
                self.app._approval_result["choice"] = "1"
                self.app._approval_result["done"] = True
            elif key == "2":
                self.app._approval_result["approved"] = True
                self.app._approval_result["choice"] = "2"
                self.app._approval_result["done"] = True
            elif key in ("3", "escape"):
                self.app._approval_result["approved"] = False
                self.app._approval_result["choice"] = "3"
                self.app._approval_result["done"] = True
            else:
                return False
            return True
        return False

    def _update_approval_message(self) -> None:
        """Update the approval message with new selection."""
        approval_msg = create_approval_message(
            self.app._approval_command, self.app._approval_selected_index
        )
        self.app.conversation.messages[-1] = (
            "assistant",
            approval_msg,
            self.app.conversation.messages[-1][2],
        )
        self.app._update_conversation_buffer()
        # Don't re-enable auto-scroll during approval navigation
        self.app.app.invalidate()