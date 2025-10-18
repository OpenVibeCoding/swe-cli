"""Key binding management for chat application."""

import asyncio
from typing import TYPE_CHECKING
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition

if TYPE_CHECKING:
    from swecli.ui.chat_app import ChatApplication


class KeyBindingManager:
    """Manages all key bindings for the chat application."""

    def __init__(self, app: 'ChatApplication'):
        """Initialize key binding manager.

        Args:
            app: The chat application instance
        """
        self.app = app

    def create_key_bindings(self) -> KeyBindings:
        """Create all key bindings for the application."""
        kb = KeyBindings()

        # Create different groups of key bindings
        self._create_enter_key_bindings(kb)
        self._create_interrupt_key_bindings(kb)
        self._create_editing_key_bindings(kb)
        self._create_approval_key_bindings(kb)
        self._create_navigation_key_bindings(kb)
        self._create_completion_key_bindings(kb)
        self._create_control_key_bindings(kb)

        return kb

    def _create_enter_key_bindings(self, kb: KeyBindings) -> None:
        """Create Enter key binding for message submission."""
        @kb.add("enter")
        def on_enter(event):
            """Handle Enter key - submit message or approval selection."""
            # Check if we're in approval mode (this should work globally)
            if self.app._handle_approval_enter():
                return

            # Only submit if input buffer has focus
            if event.app.layout.has_focus(self.app.input_buffer):
                self._handle_message_submission(event)

    def _handle_message_submission(self, event) -> None:
        """Handle message submission logic."""
        # Check if we have pasted content stored
        if self.app._pasted_content:
            # Use the original pasted content
            text = self.app._pasted_content
            display_text = self.app.input_buffer.text  # Show placeholder in conversation
            self.app._pasted_content = None  # Clear stored content
        else:
            # Normal text input
            text = self.app.input_buffer.text.strip()
            display_text = text

        if text:
            # Add to history (avoid duplicates of last command)
            if not self.app._history or self.app._history[-1] != text:
                self.app._history.append(text)

            # Reset history position
            self.app._history_position = -1
            self.app._current_input = ""

            # Add to conversation (show placeholder if it was pasted)
            self.app.conversation.add_user_message(display_text)

            # Clear input
            self.app.input_buffer.reset()

            # Refresh display
            event.app.invalidate()

            # Call callback if provided
            if self.app.on_message:
                # Run callback in background to avoid blocking UI
                asyncio.create_task(self.app._handle_message(text))

    def _create_interrupt_key_bindings(self, kb: KeyBindings) -> None:
        """Create interrupt key bindings (ESC, Ctrl+C)."""
        @kb.add("escape")
        def on_escape(event):
            """Handle ESC - interrupt processing or close completion menu."""
            # Check if we're in approval mode
            if self.app._handle_approval_key("escape"):
                return

            # If completion menu is active, close it
            buf = event.app.current_buffer
            if buf.complete_state:
                buf.complete_state = None
                return

            # If processing, interrupt the task with instant feedback
            if self.app._is_processing:
                self.app._show_interrupted_message()
                event.app.invalidate()
                return

        @kb.add("c-c")
        def on_ctrl_c(event):
            """Handle Ctrl+C - interrupt processing, clear input, or exit."""
            # If processing, interrupt the task with instant feedback
            if self.app._is_processing:
                self.app._show_interrupted_message()
                event.app.invalidate()
                return

            # If input buffer has focus and has content, clear it
            if event.app.layout.has_focus(self.app.input_buffer) and self.app.input_buffer.text:
                self.app.input_buffer.reset()
                # Reset paste content if any
                self.app._pasted_content = None
                # Reset history position
                self.app._history_position = -1
                self.app._current_input = ""
            else:
                # Otherwise, exit application
                if self.app.on_exit:
                    self.app.on_exit()
                event.app.exit()

    def _create_editing_key_bindings(self, kb: KeyBindings) -> None:
        """Create text editing key bindings (backspace, delete)."""
        @kb.add("backspace")
        def on_backspace(event):
            """Handle backspace key - delete character before cursor."""
            if self._can_edit_input(event):
                buf = event.app.current_buffer
                if buf.cursor_position > 0:
                    buf.delete_before_cursor(1)

        @kb.add("c-h")  # Ctrl+H is sometimes used as backspace on some systems
        def on_ctrl_h(event):
            """Handle Ctrl+H - alternative backspace."""
            if self._can_edit_input(event):
                buf = event.app.current_buffer
                if buf.cursor_position > 0:
                    buf.delete_before_cursor(1)

        @kb.add("delete")
        def on_delete(event):
            """Handle delete key - delete character at cursor."""
            if self._can_edit_input(event):
                buf = event.app.current_buffer
                buf.delete(1)

    def _can_edit_input(self, event) -> bool:
        """Check if input editing is allowed."""
        return (event.app.layout.has_focus(self.app.input_buffer) and
                not getattr(self.app, "_approval_mode", False))

    def _create_approval_key_bindings(self, kb: KeyBindings) -> None:
        """Create approval mode key bindings."""
        # Condition for approval mode
        @Condition
        def in_approval_mode():
            return hasattr(self.app, "_approval_mode") and self.app._approval_mode

        # CRITICAL: Use a single catch-all key binding to block text input during approval mode
        @kb.add("<any>", filter=in_approval_mode)
        def block_any_key(event):
            """Block any key not specifically handled during approval mode."""
            # Get the key sequence that was pressed
            key_sequence = event.key_sequence
            key_str = str(key_sequence)

            # Allow specific keys that should work during approval mode
            allowed_keys = {
                # Navigation keys
                "up", "down", "left", "right",
                # Vim navigation
                "j", "k",
                # Selection keys
                "1", "2", "3",
                # Control keys
                "enter", "escape", "c-c", "c-d",
                # CRITICAL: Enter key can be represented as c-m or c-j
                "c-m", "c-j",
                # Special keys that should be handled by their specific bindings
                "backspace", "delete", "c-h", "tab", "s-tab",
                # Page navigation
                "pageup", "pagedown",
            }

            # Block the key if it's not in the allowed list
            if key_str not in allowed_keys:
                return None

            # Let allowed keys pass through to their specific handlers
            return NotImplemented

        # CRITICAL: Add approval key bindings AFTER text blocking loop with eager=True
        self._add_approval_shortcuts(kb, in_approval_mode)

    def _add_approval_shortcuts(self, kb: KeyBindings, in_approval_mode) -> None:
        """Add approval mode shortcut key bindings."""
        shortcuts = [
            ("1", lambda e: self.app._handle_approval_key("1")),
            ("2", lambda e: self.app._handle_approval_key("2")),
            ("3", lambda e: self.app._handle_approval_key("3")),
            ("enter", lambda e: self.app._handle_approval_enter()),
            ("escape", lambda e: self.app._handle_approval_key("escape")),
            ("up", lambda e: self.app._handle_approval_up()),
            ("down", lambda e: self.app._handle_approval_down()),
            ("k", lambda e: self.app._handle_approval_up()),
            ("j", lambda e: self.app._handle_approval_down()),
        ]

        for key, handler in shortcuts:
            kb.add(key, filter=in_approval_mode, eager=True)(handler)

    def _create_navigation_key_bindings(self, kb: KeyBindings) -> None:
        """Create navigation key bindings (up/down for history)."""
        @kb.add("up", eager=True)
        def on_up(event):
            """Navigate completion menu or command history."""
            # Check if we're in approval mode
            if self.app._handle_approval_up():
                return

            # Only work when input buffer has focus
            if not event.app.layout.has_focus(self.app.input_buffer):
                return

            self._navigate_history_up(event)

        @kb.add("down", eager=True)
        def on_down(event):
            """Navigate completion menu or command history."""
            # Check if we're in approval mode
            if self.app._handle_approval_down():
                return

            # Only work when input buffer has focus
            if not event.app.layout.has_focus(self.app.input_buffer):
                return

            self._navigate_history_down(event)

    def _navigate_history_up(self, event) -> None:
        """Navigate up through command history."""
        buf = event.app.current_buffer

        # If completion menu is active, navigate completion
        if buf.complete_state:
            buf.complete_previous()
            return

        # Otherwise, navigate history
        if not self.app._history:
            return

        # Store current input if we're starting to navigate
        if self.app._history_position == -1:
            self.app._current_input = self.app.input_buffer.text

        # Move back in history
        if self.app._history_position < len(self.app._history) - 1:
            self.app._history_position += 1
            # History is stored newest-first, so we go backwards from end
            history_index = len(self.app._history) - 1 - self.app._history_position
            self.app.input_buffer.text = self.app._history[history_index]
            # Move cursor to end
            self.app.input_buffer.cursor_position = len(self.app.input_buffer.text)

    def _navigate_history_down(self, event) -> None:
        """Navigate down through command history."""
        buf = event.app.current_buffer

        # If completion menu is active, navigate completion
        if buf.complete_state:
            buf.complete_next()
            return

        # Otherwise, navigate history
        if self.app._history_position == -1:
            return  # Already at current input

        # Move forward in history
        self.app._history_position -= 1

        if self.app._history_position == -1:
            # Back to current input
            self.app.input_buffer.text = self.app._current_input
        else:
            # Show history item
            history_index = len(self.app._history) - 1 - self.app._history_position
            self.app.input_buffer.text = self.app._history[history_index]

        # Move cursor to end
        self.app.input_buffer.cursor_position = len(self.app.input_buffer.text)

    def _create_completion_key_bindings(self, kb: KeyBindings) -> None:
        """Create completion and scrolling key bindings."""
        @kb.add("pageup")
        def on_pageup(event):
            """Scroll conversation up."""
            # Focus conversation window and scroll
            event.app.layout.focus_next()

        @kb.add("pagedown")
        def on_pagedown(event):
            """Scroll conversation down."""
            # Focus conversation window and scroll
            event.app.layout.focus_next()

        @kb.add("tab")
        def on_tab(event):
            """Handle Tab - trigger completion."""
            # Only work when input buffer has focus
            if event.app.layout.has_focus(self.app.input_buffer):
                buf = event.app.current_buffer
                # Start completion
                if buf.complete_state:
                    buf.complete_next()
                else:
                    buf.start_completion(select_first=False)

        @kb.add("s-tab")
        def on_shift_tab(event):
            """Handle Shift+Tab - previous completion."""
            # Only work when input buffer has focus
            if event.app.layout.has_focus(self.app.input_buffer):
                buf = event.app.current_buffer
                # Go to previous completion
                if buf.complete_state:
                    buf.complete_previous()

    def _create_control_key_bindings(self, kb: KeyBindings) -> None:
        """Create control key bindings (Ctrl+D, Ctrl+L)."""
        @kb.add("c-d")
        def on_exit(event):
            """Handle Ctrl+D - exit application."""
            if self.app.on_exit:
                self.app.on_exit()
            event.app.exit()

        @kb.add("c-l")
        def on_clear(event):
            """Handle Ctrl+L - clear conversation."""
            self.app.conversation.messages.clear()
            event.app.invalidate()