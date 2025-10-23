"""Chat application with fixed bottom input and scrollable conversation."""

import asyncio
import shutil
from typing import Callable, Optional, List
from datetime import datetime

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    HSplit,
    VSplit,
    Window,
    WindowAlign,
    Float,
    FloatContainer,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.formatted_text import FormattedText, StyleAndTextTuples
from prompt_toolkit.styles import Style

from swecli.ui.conversation import ConversationBuffer
from swecli.ui.key_bindings import KeyBindingManager
from swecli.ui.approval_modal import ApprovalModalManager
from swecli.ui.model_selector_modal import ModelSelectorModalManager
from swecli.ui.layout_manager import LayoutManager


class ChatApplication:
    """Full-screen chat application with fixed bottom input."""

    def __init__(
        self,
        on_message: Optional[Callable[[str], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        completer=None,
    ):
        """Initialize chat application.

        Args:
            on_message: Callback for when user sends a message
            on_exit: Callback for when user exits the application
            completer: Optional completer for autocomplete (@ mentions and / commands)
        """
        self.conversation = ConversationBuffer()
        self.on_message = on_message
        self.on_exit = on_exit
        self.completer = completer
        self._scroll_to_bottom_flag = False  # Flag to trigger scroll on next render
        self._pasted_content = None  # Store original pasted content
        self._paste_threshold = 500  # Chars threshold for paste detection

        # Interrupt flag for ESC to stop processing
        self._interrupt_requested = False
        self._is_processing = False
        self._interrupt_shown = False  # Track if interrupt message was already shown

        # Exit confirmation state for "Ctrl+C again to exit" feature
        self._exit_confirmation_mode = False
        self._exit_confirmation_timer = None

        # Command history for Up/Down arrow navigation
        self._history: List[str] = []
        self._history_position = -1
        self._current_input = ""

        # Create conversation display buffer (read-only, scrollable)
        self.conversation_buffer = Buffer(read_only=True)

        # Create input buffer (where user types)
        self.input_buffer = Buffer(
            multiline=False,
            completer=completer,
            on_text_insert=self._on_text_insert,
            on_text_changed=self._on_buffer_text_changed,
        )

        # Dummy buffer for approval mode
        self.dummy_buffer = Buffer(read_only=True)

        # Create layout manager
        self.layout_manager = LayoutManager(self)

        # Create key bindings
        self.key_binding_manager = KeyBindingManager(self)
        self.key_bindings = self.key_binding_manager.create_key_bindings()

        # Create approval modal manager
        self.approval_modal_manager = ApprovalModalManager(self)

        # Create model selector modal manager
        self.model_selector_modal_manager = ModelSelectorModalManager(self)

        # Create style
        self.style = self._create_style()

        # Create layout
        self.layout = self.layout_manager.create_layout()

        # Create application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.key_bindings,
            style=self.style,
            full_screen=True,
            mouse_support=True,
            erase_when_done=False,
        )

    
    def _create_style(self) -> Style:
        """Create the application style."""
        return Style.from_dict(
            {
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
                "model-info": "#6c5ce7",  # Purple for normal model name
                "model-thinking": "#FFD700",  # Gold for thinking model
                "model-vlm": "#00CED1",  # Cyan for vision/VLM model
                "exit-confirmation": "#808080",  # Gray for exit confirmation message
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
            }
        )

    def _get_status_text(self) -> StyleAndTextTuples:
        """Get status bar text."""
        # TODO: Connect to actual mode and context info
        return [
            ("", "⏵⏵ normal mode  •  Context: 95%  •  Ctrl+C to exit"),
        ]

    def _on_text_insert(self, buffer: Buffer) -> None:
        """Handle text insertion - detect large pastes and replace with placeholder."""
        # Note: No need to check approval mode here - keys are blocked at key binding level
        text = buffer.text

        # Detect large paste (content longer than threshold)
        if len(text) > self._paste_threshold and not text.startswith("[[Pasted Content"):
            # Store original content
            self._pasted_content = text

            # Create placeholder
            char_count = len(text)
            placeholder = f"[[Pasted Content {char_count} chars]]"

            # Replace buffer content with placeholder
            buffer.text = placeholder
            # Move cursor to end
            buffer.cursor_position = len(placeholder)
        else:
            # Auto-completion: trigger when typing @ or /
            if buffer.completer and text:
                # Get text before cursor
                text_before_cursor = buffer.document.text_before_cursor

                # Check if we should trigger completion (@ or / followed by any character)
                if len(text_before_cursor) >= 1:
                    last_char = text_before_cursor[-1] if text_before_cursor else ""
                    # Check if previous text contains @ or /
                    if "@" in text_before_cursor or "/" in text_before_cursor:
                        # Start completion automatically
                        if not buffer.complete_state:
                            buffer.start_completion(select_first=False)

    def _on_buffer_text_changed(self, buffer: Buffer) -> None:
        """Immediately revert any text changes during approval mode only."""
        # Prevent recursion - if we're already clearing, don't trigger again
        if getattr(self, "_clearing_buffer", False):
            return

        # Protect buffer during approval mode (user should not be able to type during approval)
        # NOTE: We don't block during general processing - that would prevent users from
        # typing their next query while waiting for results (bad UX)
        is_approval_mode = getattr(self, "_approval_mode", False)

        # If in approval mode and text was added to real buffer, clear it immediately
        if is_approval_mode and buffer is self.input_buffer:
            if buffer.text:
                # Set flag to prevent recursion
                self._clearing_buffer = True
                try:
                    # Revert any text that appeared
                    buffer.text = ""
                    buffer.cursor_position = 0
                finally:
                    self._clearing_buffer = False

    def _start_exit_confirmation(self) -> None:
        """Start exit confirmation mode with timer."""
        self._exit_confirmation_mode = True
        self._cancel_exit_confirmation_timer()  # Cancel any existing timer

        # Set timer to cancel exit confirmation after 3 seconds
        try:
            self._exit_confirmation_timer = asyncio.create_task(self._cancel_exit_confirmation_after_delay())
        except RuntimeError:
            # No running event loop - create timer differently
            import threading
            timer = threading.Timer(3.0, self._cancel_exit_confirmation)
            timer.daemon = True
            timer.start()
            self._exit_confirmation_timer = timer

        # Update status bar
        self.app.invalidate()

    def _cancel_exit_confirmation(self) -> None:
        """Cancel exit confirmation mode."""
        if self._exit_confirmation_mode:
            self._exit_confirmation_mode = False
            self._cancel_exit_confirmation_timer()
            self.app.invalidate()

    def _cancel_exit_confirmation_timer(self) -> None:
        """Cancel the exit confirmation timer if it exists."""
        if self._exit_confirmation_timer is None:
            return

        if hasattr(self._exit_confirmation_timer, 'cancel'):
            # This is an asyncio task or threading timer
            if hasattr(self._exit_confirmation_timer, 'done') and not self._exit_confirmation_timer.done():
                # asyncio task
                self._exit_confirmation_timer.cancel()
            else:
                # threading timer
                self._exit_confirmation_timer.cancel()

        self._exit_confirmation_timer = None

    async def _cancel_exit_confirmation_after_delay(self) -> None:
        """Cancel exit confirmation after 3 seconds."""
        try:
            await asyncio.sleep(3.0)  # Wait 3 seconds
            if self._exit_confirmation_mode:
                self._exit_confirmation_mode = False
                self._exit_confirmation_timer = None
                self.app.invalidate()
        except asyncio.CancelledError:
            # Timer was cancelled - this is expected
            pass

    async def _handle_message(self, text: str) -> None:
        """Handle message in background."""
        if self.on_message:
            # Call the message handler (this might be async)
            if asyncio.iscoroutinefunction(self.on_message):
                await self.on_message(text)
            else:
                self.on_message(text)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message and refresh display."""
        self.conversation.add_assistant_message(content)
        self._update_conversation_buffer()

        # DON'T lock input during normal conversation - users should be able to type!
        # Input locking is ONLY for approval mode where we need exclusive control
        self.app.invalidate()

        # Auto-scroll to bottom ONLY if user hasn't manually scrolled up
        # Check if auto_scroll is still enabled (if user scrolled, it's disabled)
        conversation_control = self.layout_manager.get_conversation_control()
        if conversation_control._auto_scroll:
            self._scroll_to_bottom()

    async def _restore_input_after_render(self) -> None:
        """
        Restore input capability after render cycle completes.

        This method waits for the screen update to finish, then restores
        the buffer to normal read-write mode so the user can continue typing.

        CRITICAL: Monitors the buffer after unlocking and clears any corruption
        that appears from queued keystrokes.
        """
        try:
            # Wait for render cycle to complete (~100ms for safer timing)
            # Increased from 50ms to give more time for complex renders
            await asyncio.sleep(0.1)

            # CRITICAL FIX: Save current buffer text before unlocking
            # We need to preserve what the user was typing BEFORE the render
            saved_text = self.input_buffer.text
            saved_cursor = self.input_buffer.cursor_position

            # Unlock input buffer
            self._input_locked = False

            # CRITICAL: Wait a tiny bit more for any queued keys to process
            await asyncio.sleep(0.02)

            # Now check if corruption appeared (text changed unexpectedly)
            # If text is different from what we saved, it means queued keys leaked through
            if self.input_buffer.text != saved_text:
                # Corruption detected! Restore the saved text
                self._clearing_buffer = True
                try:
                    self.input_buffer.document = Document(text=saved_text, cursor_position=saved_cursor)
                finally:
                    self._clearing_buffer = False

        except asyncio.CancelledError:
            # Task was cancelled by a new render - this is expected
            # The new render will handle unlocking after its own delay
            pass

    def add_system_message(self, content: str) -> None:
        """Add a system message and refresh display."""
        self.conversation.add_system_message(content)
        self._update_conversation_buffer()

        # DON'T lock input - users should be able to type during updates
        self.app.invalidate()

    def update_last_message(self, content: str) -> None:
        """Update the last message (for streaming/thinking indicators)."""
        self.conversation.update_last_message(content)
        self._update_conversation_buffer()

        # DON'T lock input - users should be able to type during spinner updates
        self.app.invalidate()

        # Only scroll to bottom if user hasn't manually scrolled up
        conversation_control = self.layout_manager.get_conversation_control()
        if conversation_control._auto_scroll:
            self._scroll_to_bottom()

    def clear_conversation(self) -> None:
        """Clear all messages from conversation."""
        self.conversation.clear()
        self.app.invalidate()

    def safe_invalidate(self) -> None:
        """
        Safely invalidate the UI from background threads or async contexts.

        Use this method instead of calling app.invalidate() directly when
        updating the UI from background threads.
        """
        # DON'T lock input - just invalidate the display
        # Users should be able to type during background updates
        self.app.invalidate()

    def get_status_info(self) -> dict:
        """Get status info to display in status bar (override in REPL integration)."""
        return {
            "mode": "normal",
            "context_pct": 95.0,
        }

    def _update_conversation_buffer(self) -> None:
        """Update the conversation display with current messages."""
        # With FormattedTextControl, we just need to invalidate to refresh
        # The control will call _get_conversation_formatted_text() automatically
        # Scrolling is handled by _get_vertical_scroll() callback
        pass

    def _scroll_to_bottom(self) -> None:
        """Scroll conversation to bottom to show latest messages."""
        # Use our layout manager's conversation control scroll_to_bottom method
        if self.layout_manager and hasattr(self.layout_manager, "get_conversation_control"):
            conversation_control = self.layout_manager.get_conversation_control()
            # Enable auto-scroll which will show bottom on next render
            conversation_control.scroll_to_bottom()

    async def show_approval_modal(self, command: str, working_dir: str) -> tuple[bool, str, str]:
        """Show approval modal as a conversation message with arrow key selection."""
        return await self.approval_modal_manager.show_approval_modal(command, working_dir)

    def _handle_approval_up(self):
        """Handle up arrow in approval mode."""
        return self.approval_modal_manager.handle_approval_up()

    def _handle_approval_down(self):
        """Handle down arrow in approval mode."""
        return self.approval_modal_manager.handle_approval_down()

    def _handle_approval_enter(self):
        """Handle enter in approval mode."""
        return self.approval_modal_manager.handle_approval_enter()

    def _handle_approval_key(self, key: str):
        """Handle number keys and escape in approval mode."""
        return self.approval_modal_manager.handle_approval_key(key)

    @property
    def _approval_mode(self) -> bool:
        """Check if approval mode is active."""
        return self.approval_modal_manager.is_in_approval_mode()

    def _handle_selector_up(self):
        """Handle up arrow in selector mode."""
        return self.model_selector_modal_manager.handle_selector_up()

    def _handle_selector_down(self):
        """Handle down arrow in selector mode."""
        return self.model_selector_modal_manager.handle_selector_down()

    def _handle_selector_enter(self):
        """Handle enter in selector mode."""
        return self.model_selector_modal_manager.handle_selector_enter()

    def _handle_selector_escape(self):
        """Handle escape in selector mode."""
        return self.model_selector_modal_manager.handle_selector_escape()

    @property
    def _selector_mode(self) -> bool:
        """Check if selector mode is active."""
        return self.model_selector_modal_manager.is_in_selector_mode()

    def run(self) -> None:
        """Run the chat application."""
        # Simply let prompt_toolkit handle everything
        # It will automatically use alternate screen buffer in full_screen mode
        self.app.run()


# Fix import error - VSplit should be imported
from prompt_toolkit.layout.containers import VSplit


# Example usage / testing
if __name__ == "__main__":

    def handle_message(text: str):
        """Example message handler."""
        # Simulate processing
        chat.add_assistant_message(f"You said: {text}")

    chat = ChatApplication(on_message=handle_message)

    # Add some initial messages
    chat.conversation.add_system_message("Welcome to SWE-CLI!")
    chat.conversation.add_user_message("Hello")
    chat.conversation.add_assistant_message("Hi there! How can I help you?")

    # Run the application
    chat.run()
