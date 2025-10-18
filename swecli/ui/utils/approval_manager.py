"""Approval modal management for chat application."""

import asyncio
from typing import Tuple


class ApprovalManager:
    """Manages approval modal workflow and state."""

    def __init__(self, app):
        """Initialize approval manager.

        Args:
            app: The chat application instance
        """
        self.app = app

    async def show_approval_modal(self, command: str, working_dir: str) -> Tuple[bool, str, str]:
        """Show approval modal as a conversation message with arrow key selection.

        Args:
            command: Command to approve
            working_dir: Working directory context

        Returns:
            Tuple of (approved, choice, command)
        """
        # Initialize approval mode
        self._initialize_approval_mode(command)

        # Display approval message
        self._display_approval_message(command)

        # Wait for user selection
        result = await self._wait_for_approval_selection()

        # Clean up after approval
        self._cleanup_approval_mode()

        return (result["approved"], result["choice"], command)

    def _initialize_approval_mode(self, command: str) -> None:
        """Initialize approval mode state and input buffers."""
        # CRITICAL: Unlock input buffer before clearing it
        # It may still be locked from a previous render cycle
        self.app._input_locked = False

        # Clear input buffer
        self.app.input_buffer.text = ""
        self.app.input_buffer.cursor_position = 0

        # CRITICAL: Reuse the SAME dummy buffer every time to prevent state accumulation
        # Creating new buffers each cycle causes prompt_toolkit internal state to accumulate
        # No need to clear - it's read-only, so keys are naturally discarded

        # Swap to dummy buffer (reusing the same one)
        if (hasattr(self.app, 'layout_manager') and
            hasattr(self.app.layout_manager, 'get_input_control')):
            input_control = self.app.layout_manager.get_input_control()
            input_control.buffer = self.app.dummy_buffer

        # Set up approval mode state (activates catch-all key blocker)
        self.app._approval_mode = True
        self.app._approval_selected_index = 0
        self.app._approval_command = command
        self.app._approval_result = {"done": False, "approved": False, "choice": "3"}

    def _display_approval_message(self, command: str) -> None:
        """Display the approval message in the conversation."""
        from swecli.ui.components.approval_message import create_approval_message

        # Add initial approval message to conversation
        approval_msg = create_approval_message(command, self.app._approval_selected_index)
        self.app.conversation.add_assistant_message(approval_msg)
        self.app._update_conversation_buffer()

        # CRITICAL: Disable auto-scroll and manually position with buffer
        # Don't scroll to absolute bottom - leave space to prevent overlap
        if hasattr(self.app, "conversation_control"):
            self.app.conversation_control._auto_scroll = False
            # Scroll to show the approval message but leave 3 lines of space below
            text = self.app.conversation.get_plain_text()
            total_lines = len(text.split("\n"))
            # Position scroll so approval is visible with buffer space below
            self.app.conversation_control.scroll_offset = max(0, total_lines - 15)  # Show last 15 lines

        self.app.app.invalidate()

    async def _wait_for_approval_selection(self) -> dict:
        """Wait for user to make an approval selection."""
        try:
            # Wait for user to make a selection
            # Note: Buffer is read-only during approval via Condition
            while not self.app._approval_result["done"]:
                await asyncio.sleep(0.05)
                if self.app.app.is_done:
                    self.app._approval_result["approved"] = False
                    self.app._approval_result["choice"] = "3"
                    break

            # Store result
            return self.app._approval_result
        except:
            # Return default result if something goes wrong
            return {"approved": False, "choice": "3"}

    def _cleanup_approval_mode(self) -> None:
        """Clean up approval mode and restore normal input handling."""
        # CRITICAL FIX: Keep approval mode active until AFTER buffer swap
        # This prevents keystrokes from leaking into the input buffer during transition

        # Wait with dummy buffer still active - any keys go to dummy (discarded)
        asyncio.create_task(self._delayed_buffer_cleanup())

    async def _delayed_buffer_cleanup(self) -> None:
        """Delayed cleanup of buffers to ensure proper state transition."""
        await asyncio.sleep(0.2)

        # Unlock input buffer before modifying it
        self.app._input_locked = False

        # Clear real buffer BEFORE swapping (should be clean, but be defensive)
        self.app._clearing_buffer = True  # Prevent on_text_changed from firing
        try:
            self.app.input_buffer.text = ""
            self.app.input_buffer.cursor_position = 0
        finally:
            self.app._clearing_buffer = False

        # NOW swap back to real buffer (after keys have settled)
        if (hasattr(self.app, 'layout_manager') and
            hasattr(self.app.layout_manager, 'get_input_control')):
            input_control = self.app.layout_manager.get_input_control()
            input_control.buffer = self.app.input_buffer

        # IMPORTANT: Only disable approval mode AFTER buffer swap completes
        # This ensures _on_buffer_text_changed protection stays active during swap
        self.app._approval_mode = False

        # Final defensive clear (catches any race condition stragglers)
        self.app._clearing_buffer = True
        try:
            self.app.input_buffer.text = ""
            self.app.input_buffer.cursor_position = 0
        finally:
            self.app._clearing_buffer = False

        # Flush
        self.app.app.invalidate()

        # Remove the approval message from conversation
        if self.app.conversation.messages and self.app.conversation.messages[-1][0] == "assistant":
            self.app.conversation.messages.pop()
            self.app._update_conversation_buffer()

            # Re-enable auto-scroll after approval is done
            if hasattr(self.app, "conversation_control"):
                self.app.conversation_control._auto_scroll = True

            self.app.app.invalidate()