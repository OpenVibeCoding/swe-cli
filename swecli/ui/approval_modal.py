"""Approval modal management for SWE-CLI chat interface."""

from __future__ import annotations

import asyncio
from typing import Tuple, Dict, Any


class ApprovalModalManager:
    """Manages approval modal state, display, and user interactions."""

    def __init__(self, chat_app):
        """Initialize approval modal manager.

        Args:
            chat_app: The ChatApplication instance for callbacks
        """
        self.chat_app = chat_app
        self.reset_state()

    def reset_state(self) -> None:
        """Reset approval modal state to defaults."""
        self._approval_mode = False
        self._approval_selected_index = 0
        self._approval_command = ""
        self._approval_result = {"done": False, "approved": False, "choice": "3"}

    def is_in_approval_mode(self) -> bool:
        """Check if approval mode is currently active."""
        return self._approval_mode

    async def show_approval_modal(self, command: str, working_dir: str) -> Tuple[bool, str, str]:
        """Show approval modal as a conversation message with arrow key selection.

        Args:
            command: Command to request approval for
            working_dir: Current working directory

        Returns:
            Tuple of (approved: bool, choice: str, command: str)
        """
        from swecli.ui.components.approval_message import create_approval_message

        # Reset state for new approval
        self.reset_state()
        self._approval_command = command

        # CRITICAL: Unlock input buffer before clearing it
        # It may still be locked from a previous render cycle
        self.chat_app._input_locked = False

        # Clear input buffer
        self.chat_app.input_buffer.text = ""
        self.chat_app.input_buffer.cursor_position = 0

        # Set up approval mode state (activates catch-all key blocker)
        self._approval_mode = True

        # Add initial approval message to conversation
        approval_msg = create_approval_message(command, self._approval_selected_index)
        self.chat_app.conversation.add_assistant_message(approval_msg)
        self.chat_app._update_conversation_buffer()

        # Position conversation for approval visibility
        self._position_conversation_for_approval()

        self.chat_app.app.invalidate()

        try:
            # Wait for user to make a selection
            # Note: Buffer is read-only during approval via Condition
            result = await self._wait_for_user_selection()

        finally:
            # Clean up approval mode
            await self._cleanup_approval_mode()

        # Remove the approval message from conversation
        self._remove_approval_message()

        # Re-enable auto-scroll after approval is done
        if (hasattr(self.chat_app, 'layout_manager') and
            hasattr(self.chat_app.layout_manager, 'get_conversation_control')):
            conversation_control = self.chat_app.layout_manager.get_conversation_control()
            conversation_control._auto_scroll = True

        self.chat_app.app.invalidate()

        return (result["approved"], result["choice"], command)

    def _position_conversation_for_approval(self) -> None:
        """Position conversation to show approval message properly."""
        # CRITICAL: Disable auto-scroll and manually position with buffer
        # Don't scroll to absolute bottom - leave space to prevent overlap
        if (hasattr(self.chat_app, 'layout_manager') and
            hasattr(self.chat_app.layout_manager, 'get_conversation_control')):
            conversation_control = self.chat_app.layout_manager.get_conversation_control()
            conversation_control._auto_scroll = False
            # Scroll to show the approval message but leave 3 lines of space below
            text = self.chat_app.conversation.get_plain_text()
            total_lines = len(text.split("\n"))
            # Position scroll so approval is visible with buffer space below
            conversation_control.scroll_offset = max(0, total_lines - 15)  # Show last 15 lines

    async def _wait_for_user_selection(self) -> Dict[str, Any]:
        """Wait for user to make a selection in the approval modal.

        Returns:
            The approval result dictionary
        """
        while not self._approval_result["done"]:
            await asyncio.sleep(0.05)
            if self.chat_app.app.is_done:
                self._approval_result["approved"] = False
                self._approval_result["choice"] = "3"
                break

        return self._approval_result

    async def _cleanup_approval_mode(self) -> None:
        """Clean up approval mode and restore normal input."""
        # CRITICAL FIX: Keep approval mode active until AFTER buffer swap
        # This prevents keystrokes from leaking into the input buffer during transition

        # Wait with dummy buffer still active - any keys go to dummy (discarded)
        await asyncio.sleep(0.2)

        # Unlock input buffer before modifying it
        self.chat_app._input_locked = False

        # Clear real buffer BEFORE swapping (should be clean, but be defensive)
        self.chat_app._clearing_buffer = True  # Prevent on_text_changed from firing
        try:
            self.chat_app.input_buffer.text = ""
            self.chat_app.input_buffer.cursor_position = 0
        finally:
            self.chat_app._clearing_buffer = False

        # NOW swap back to real buffer (after keys have settled)
        if (hasattr(self.chat_app, 'layout_manager') and
            hasattr(self.chat_app.layout_manager, 'get_input_control')):
            input_control = self.chat_app.layout_manager.get_input_control()
            input_control.buffer = self.chat_app.input_buffer

        # IMPORTANT: Only disable approval mode AFTER buffer swap completes
        # This ensures _on_buffer_text_changed protection stays active during swap
        self._approval_mode = False

        # Final defensive clear (catches any race condition stragglers)
        self.chat_app._clearing_buffer = True
        try:
            self.chat_app.input_buffer.text = ""
            self.chat_app.input_buffer.cursor_position = 0
        finally:
            self.chat_app._clearing_buffer = False

        # Flush
        self.chat_app.app.invalidate()

    def _remove_approval_message(self) -> None:
        """Remove the approval message from conversation."""
        if (self.chat_app.conversation.messages and
            self.chat_app.conversation.messages[-1][0] == "assistant"):
            self.chat_app.conversation.messages.pop()
            self.chat_app._update_conversation_buffer()

    def handle_approval_up(self) -> bool:
        """Handle up arrow in approval mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._approval_mode:
            return False

        if self._approval_selected_index > 0:
            self._approval_selected_index -= 1
            self._update_approval_message()
        return True

    def handle_approval_down(self) -> bool:
        """Handle down arrow in approval mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._approval_mode:
            return False

        if self._approval_selected_index < 2:
            self._approval_selected_index += 1
            self._update_approval_message()
        return True

    def handle_approval_enter(self) -> bool:
        """Handle enter in approval mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._approval_mode:
            return False

        if self._approval_selected_index == 0:
            self._approval_result["approved"] = True
            self._approval_result["choice"] = "1"
        elif self._approval_selected_index == 1:
            self._approval_result["approved"] = True
            self._approval_result["choice"] = "2"
        else:
            self._approval_result["approved"] = False
            self._approval_result["choice"] = "3"
        self._approval_result["done"] = True
        return True

    def handle_approval_key(self, key: str) -> bool:
        """Handle number keys and escape in approval mode.

        Args:
            key: The key that was pressed

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._approval_mode:
            return False

        if key == "1":
            self._approval_result["approved"] = True
            self._approval_result["choice"] = "1"
            self._approval_result["done"] = True
        elif key == "2":
            self._approval_result["approved"] = True
            self._approval_result["choice"] = "2"
            self._approval_result["done"] = True
        elif key in ("3", "escape"):
            self._approval_result["approved"] = False
            self._approval_result["choice"] = "3"
            self._approval_result["done"] = True
        else:
            return False
        return True

    def _update_approval_message(self) -> None:
        """Update the approval message with new selection."""
        from swecli.ui.components.approval_message import create_approval_message

        approval_msg = create_approval_message(
            self._approval_command, self._approval_selected_index
        )
        if self.chat_app.conversation.messages:
            self.chat_app.conversation.messages[-1] = (
                "assistant",
                approval_msg,
                self.chat_app.conversation.messages[-1][2],
            )
        self.chat_app._update_conversation_buffer()
        # Don't re-enable auto-scroll during approval navigation
        self.chat_app.app.invalidate()