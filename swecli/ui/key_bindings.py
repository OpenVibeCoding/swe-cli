"""Key binding management for SWE-CLI chat interface."""

from __future__ import annotations

import asyncio
from typing import Callable, Optional, List
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings


class KeyBindingManager:
    """Manages keyboard shortcuts and key bindings for the chat application."""

    def __init__(self, chat_app):
        """Initialize key binding manager.

        Args:
            chat_app: The ChatApplication instance for callbacks
        """
        self.chat_app = chat_app

    def create_key_bindings(self) -> KeyBindings:
        """Create and configure all key bindings for the application."""
        kb = KeyBindings()

        # System control key bindings
        self._add_system_bindings(kb)

        # Input editing key bindings
        self._add_editing_bindings(kb)

        # Navigation key bindings
        self._add_navigation_bindings(kb)

        # Completion key bindings
        self._add_completion_bindings(kb)

        # Approval mode key bindings
        self._add_approval_bindings(kb)

        # History navigation key bindings
        self._add_history_bindings(kb)

        # Exit confirmation key bindings
        self._add_exit_confirmation_bindings(kb)

        return kb

    def _add_system_bindings(self, kb: KeyBindings) -> None:
        """Add system control key bindings (ESC, Ctrl+C, etc.)."""

        @kb.add("escape")
        def on_escape(event):
            """Handle ESC - interrupt processing or close completion menu."""
            # Check if we're in approval mode
            if self.chat_app._handle_approval_key("escape"):
                return

            # If completion menu is active, close it
            buf = event.app.current_buffer
            if buf.complete_state:
                buf.complete_state = None
                return

            # If processing, interrupt the task with instant feedback
            if self.chat_app._is_processing:
                self._handle_interrupt(event)
                return

            # If input buffer has focus and has content, clear it
            if event.app.layout.has_focus(self.chat_app.input_buffer) and self.chat_app.input_buffer.text:
                self.chat_app.input_buffer.reset()
                # Reset paste content if any
                self.chat_app._pasted_content = None
                # Reset history position
                self.chat_app._history_position = -1
                self.chat_app._current_input = ""

        @kb.add("c-c")
        def on_ctrl_c(event):
            """Handle Ctrl+C - exit confirmation only."""
            # Handle exit confirmation mode
            if hasattr(self.chat_app, '_exit_confirmation_mode') and self.chat_app._exit_confirmation_mode:
                # Second Ctrl+C - exit the application
                if self.chat_app.on_exit:
                    self.chat_app.on_exit()
                event.app.exit()
                return

            # First Ctrl+C - start exit confirmation mode
            if hasattr(self.chat_app, '_start_exit_confirmation'):
                self.chat_app._start_exit_confirmation()

        @kb.add("c-d")
        def on_exit(event):
            """Handle Ctrl+D - exit application."""
            if self.chat_app.on_exit:
                self.chat_app.on_exit()
            event.app.exit()

        @kb.add("c-l")
        def on_clear(event):
            """Handle Ctrl+L - clear conversation."""
            self.chat_app.conversation.clear()
            self.chat_app.app.invalidate()

    def _add_editing_bindings(self, kb: KeyBindings) -> None:
        """Add text editing key bindings."""

        @kb.add("enter")
        def on_enter(event):
            """Handle Enter key - submit message or approval selection."""
            # Check if we're in approval mode (this should work globally)
            if self.chat_app._handle_approval_enter():
                return

            # Only submit if input buffer has focus
            if event.app.layout.has_focus(self.chat_app.input_buffer):
                buf = event.app.current_buffer

                # If completion menu is active, accept the completion but don't submit
                if buf.complete_state:
                    # Accept the current completion selection
                    buf.complete_state = None
                    return  # Don't submit the message

                # Check if we have pasted content stored
                if self.chat_app._pasted_content:
                    # Use the original pasted content
                    text = self.chat_app._pasted_content
                    display_text = self.chat_app.input_buffer.text  # Show placeholder in conversation
                    self.chat_app._pasted_content = None  # Clear stored content
                else:
                    # Normal text input
                    text = self.chat_app.input_buffer.text.strip()
                    display_text = text

                if text:
                    # Add to history (avoid duplicates of last command)
                    if not self.chat_app._history or self.chat_app._history[-1] != text:
                        self.chat_app._history.append(text)

                    # Reset history position
                    self.chat_app._history_position = -1
                    self.chat_app._current_input = ""

                    # Add to conversation (show placeholder if it was pasted)
                    self.chat_app.conversation.add_user_message(display_text)

                    # Clear input
                    self.chat_app.input_buffer.reset()

                    # Refresh display
                    self.chat_app.app.invalidate()

                    # Call callback if provided
                    if self.chat_app.on_message:
                        # Run callback in background to avoid blocking UI
                        asyncio.create_task(self.chat_app._handle_message(text))

        # Handle backspace and delete keys properly (prevents ^? characters on Mac)
        @kb.add("backspace")
        def on_backspace(event):
            """Handle backspace key - delete character before cursor."""
            # Only work when input buffer has focus and not in approval mode
            if self._can_edit_input(event):
                buf = event.app.current_buffer
                if buf.cursor_position > 0:
                    # Delete character before cursor
                    buf.delete_before_cursor(1)

        @kb.add("c-h")  # Ctrl+H is sometimes used as backspace on some systems
        def on_ctrl_h(event):
            """Handle Ctrl+H - alternative backspace."""
            # Only work when input buffer has focus and not in approval mode
            if self._can_edit_input(event):
                buf = event.app.current_buffer
                if buf.cursor_position > 0:
                    # Delete character before cursor
                    buf.delete_before_cursor(1)

        @kb.add("delete")
        def on_delete(event):
            """Handle delete key - delete character at cursor."""
            # Only work when input buffer has focus and not in approval mode
            if self._can_edit_input(event):
                buf = event.app.current_buffer
                # Delete character at cursor
                buf.delete(1)

    def _add_navigation_bindings(self, kb: KeyBindings) -> None:
        """Add navigation key bindings."""

        @kb.add("up", eager=True)
        def on_up(event):
            """Navigate completion menu or command history."""
            # Check if we're in approval mode
            if self.chat_app._handle_approval_up():
                return

            # Only work when input buffer has focus
            if not event.app.layout.has_focus(self.chat_app.input_buffer):
                return

            buf = event.app.current_buffer

            # If completion menu is active, navigate completion
            if buf.complete_state:
                buf.complete_previous()
                return

            # Otherwise, navigate history
            self._navigate_history_up(event)

        @kb.add("down", eager=True)
        def on_down(event):
            """Navigate completion menu or command history."""
            # Check if we're in approval mode
            if self.chat_app._handle_approval_down():
                return

            # Only work when input buffer has focus
            if not event.app.layout.has_focus(self.chat_app.input_buffer):
                return

            buf = event.app.current_buffer

            # If completion menu is active, navigate completion
            if buf.complete_state:
                buf.complete_next()
                return

            # Otherwise, navigate history
            self._navigate_history_down(event)

        # Scrolling key bindings
        @kb.add("pageup")
        def on_pageup(event):
            """Scroll conversation up (Page Up or fn + up arrow on Mac)."""
            if hasattr(self.chat_app.layout_manager, 'get_conversation_control'):
                control = self.chat_app.layout_manager.get_conversation_control()
                window = self.chat_app.layout_manager.get_conversation_window()
                if control and window:
                    # Get window height for page scroll
                    if window.render_info:
                        height = window.render_info.window_height
                    else:
                        height = 10  # Default fallback
                    # Scroll up by viewport height
                    control.scroll_page_up(height)
                    event.app.invalidate()

        @kb.add("pagedown")
        def on_pagedown(event):
            """Scroll conversation down (Page Down or fn + down arrow on Mac)."""
            if hasattr(self.chat_app.layout_manager, 'get_conversation_control'):
                control = self.chat_app.layout_manager.get_conversation_control()
                window = self.chat_app.layout_manager.get_conversation_window()
                if control and window:
                    # Get window height for page scroll
                    if window.render_info:
                        height = window.render_info.window_height
                    else:
                        height = 10  # Default fallback
                    # Scroll down by viewport height
                    control.scroll_page_down(height)
                    event.app.invalidate()

    def _add_completion_bindings(self, kb: KeyBindings) -> None:
        """Add completion-related key bindings."""

        @kb.add("tab")
        def on_tab(event):
            """Handle Tab - trigger completion."""
            # Only work when input buffer has focus
            if event.app.layout.has_focus(self.chat_app.input_buffer):
                buf = event.app.current_buffer
                # Start completion
                if buf.complete_state:
                    buf.complete_next()
                else:
                    buf.start_completion(select_first=False)

        @kb.add("s-tab")
        def on_shift_tab(event):
            """Handle Shift+Tab - previous completion."""
            # Only work when input buffer has focus AND there's an active completion
            if event.app.layout.has_focus(self.chat_app.input_buffer):
                buf = event.app.current_buffer
                # ONLY navigate completion if there's an active completion state
                # This allows mode switching (in REPLChatApplication) to work when no completion
                if buf.complete_state:
                    buf.complete_previous()
                    return
            # If we don't handle it, allow other bindings (like mode switching) to handle it
            return NotImplemented

    def _add_approval_bindings(self, kb: KeyBindings) -> None:
        """Add approval mode specific key bindings."""

        # Condition for approval mode
        @Condition
        def in_approval_mode():
            return hasattr(self.chat_app, "_approval_mode") and self.chat_app._approval_mode

        # CRITICAL: Use a single catch-all key binding to block text input during approval mode
        @kb.add("<any>", filter=in_approval_mode)
        def block_any_key(event):
            """Block any key not specifically handled during approval mode."""
            # Get the key sequence that was pressed
            key_sequence = event.key_sequence

            # Convert to string representation for checking
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
                # Block this key - do nothing
                return None

            # Let allowed keys pass through to their specific handlers
            return NotImplemented

        # CRITICAL: Add approval key bindings AFTER text blocking loop with eager=True
        # This ensures they take precedence over the text blockers
        @kb.add("1", filter=in_approval_mode, eager=True)
        def on_1(event):
            """Handle 1 key - quick approval selection."""
            self.chat_app._handle_approval_key("1")

        @kb.add("2", filter=in_approval_mode, eager=True)
        def on_2(event):
            """Handle 2 key - quick approval selection."""
            self.chat_app._handle_approval_key("2")

        @kb.add("3", filter=in_approval_mode, eager=True)
        def on_3(event):
            """Handle 3 key - quick approval selection."""
            self.chat_app._handle_approval_key("3")

        @kb.add("enter", filter=in_approval_mode, eager=True)
        def on_approval_enter(event):
            """Handle Enter key in approval mode - global binding."""
            self.chat_app._handle_approval_enter()

        @kb.add("escape", filter=in_approval_mode, eager=True)
        def on_approval_escape(event):
            """Handle Escape key in approval mode - global binding."""
            self.chat_app._handle_approval_key("escape")

        @kb.add("up", filter=in_approval_mode, eager=True)
        def on_approval_up(event):
            """Handle Up arrow in approval mode - global binding."""
            self.chat_app._handle_approval_up()

        @kb.add("down", filter=in_approval_mode, eager=True)
        def on_approval_down(event):
            """Handle Down arrow in approval mode - global binding."""
            self.chat_app._handle_approval_down()

        @kb.add("k", filter=in_approval_mode, eager=True)
        def on_approval_k(event):
            """Handle k key (vim up) in approval mode - global binding."""
            self.chat_app._handle_approval_up()

        @kb.add("j", filter=in_approval_mode, eager=True)
        def on_approval_j(event):
            """Handle j key (vim down) in approval mode - global binding."""
            self.chat_app._handle_approval_down()

        # Model selector mode bindings
        @Condition
        def in_selector_mode():
            return (hasattr(self.chat_app, '_selector_mode') and
                    self.chat_app._selector_mode)

        @kb.add("enter", filter=in_selector_mode, eager=True)
        def on_selector_enter(event):
            """Handle Enter key in selector mode - global binding."""
            self.chat_app._handle_selector_enter()

        @kb.add("escape", filter=in_selector_mode, eager=True)
        def on_selector_escape(event):
            """Handle Escape key in selector mode - global binding."""
            self.chat_app._handle_selector_escape()

        @kb.add("up", filter=in_selector_mode, eager=True)
        def on_selector_up(event):
            """Handle Up arrow in selector mode - global binding."""
            self.chat_app._handle_selector_up()

        @kb.add("down", filter=in_selector_mode, eager=True)
        def on_selector_down(event):
            """Handle Down arrow in selector mode - global binding."""
            self.chat_app._handle_selector_down()

        @kb.add("k", filter=in_selector_mode, eager=True)
        def on_selector_k(event):
            """Handle k key (vim up) in selector mode - global binding."""
            self.chat_app._handle_selector_up()

        @kb.add("j", filter=in_selector_mode, eager=True)
        def on_selector_j(event):
            """Handle j key (vim down) in selector mode - global binding."""
            self.chat_app._handle_selector_down()

        @kb.add("c-c", filter=in_selector_mode, eager=True)
        def on_selector_ctrlc(event):
            """Handle Ctrl+C in selector mode - cancel selection."""
            self.chat_app._handle_selector_escape()

    def _add_history_bindings(self, kb: KeyBindings) -> None:
        """Add command history navigation key bindings."""
        # History navigation is handled in the navigation bindings
        pass

    def _add_exit_confirmation_bindings(self, kb: KeyBindings) -> None:
        """Add exit confirmation mode key bindings."""

        # Condition for exit confirmation mode
        @Condition
        def in_exit_confirmation_mode():
            return (hasattr(self.chat_app, '_exit_confirmation_mode') and
                    self.chat_app._exit_confirmation_mode)

        # Block all keys except Ctrl+C during exit confirmation mode
        @kb.add("<any>", filter=in_exit_confirmation_mode)
        def cancel_exit_confirmation(event):
            """Cancel exit confirmation on any key except Ctrl+C."""
            key_sequence = event.key_sequence
            key_str = str(key_sequence)

            # Only allow Ctrl+C to proceed, all other keys cancel
            if key_str != "c-c":
                # Cancel exit confirmation mode
                if hasattr(self.chat_app, '_cancel_exit_confirmation'):
                    self.chat_app._cancel_exit_confirmation()
                # Block the key from being processed
                return None

            # Let Ctrl+C pass through to its handler
            return NotImplemented

    def _can_edit_input(self, event) -> bool:
        """Check if input editing is allowed (not in approval mode and has focus)."""
        return (event.app.layout.has_focus(self.chat_app.input_buffer) and
                not getattr(self.chat_app, "_approval_mode", False))

    def _handle_interrupt(self, event) -> None:
        """Handle interrupt signal (ESC during processing)."""
        # Prevent duplicate interrupt messages
        if getattr(self.chat_app, "_interrupt_requested", False):
            return  # Already interrupted, don't show another message

        # Stop spinner immediately if available
        if hasattr(self.chat_app, "_stop_spinner"):
            self.chat_app._stop_spinner()

        # Set interrupt flags immediately to prevent further processing
        self.chat_app._interrupt_requested = True
        self.chat_app._interrupt_shown = True

        # Show interrupted message immediately for instant UX feedback
        if hasattr(self.chat_app, "_execution_state") and self.chat_app._execution_state == "executing_tool":
            # During tool execution: show tool call with interrupted message
            if hasattr(self.chat_app, "_current_tool_display"):
                from rich.console import Console
                from io import StringIO

                string_io = StringIO()
                temp_console = Console(
                    file=string_io, force_terminal=True, legacy_windows=False
                )
                temp_console.print(f"[green]⏺[/green] [cyan]{self.chat_app._current_tool_display}[/cyan]", end="")
                colored_tool_call = string_io.getvalue()

                interrupted_box = "┌─ Interrupted ────────────────\n"
                interrupted_box += "│ \033[31m⏺ Interrupted by user (ESC)\033[0m\n"
                interrupted_box += "└──────────────────────────────"

                combined_message = f"{colored_tool_call}\n{interrupted_box}"
                self.chat_app.add_assistant_message(combined_message)
        else:
            # During thinking: show red interrupted message
            self.chat_app.add_assistant_message("\033[31m⏺ Interrupted by user (ESC)\033[0m")

        # Cancel any running LLM task
        if hasattr(self.chat_app, "_current_llm_task"):
            task = self.chat_app._current_llm_task
            if task and not task.done():
                task.cancel()

        # Reset processing state flags (but keep interrupt flags to prevent duplicates)
        self.chat_app._is_processing = False
        self.chat_app._execution_state = None
        self.chat_app._current_tool_display = None

        event.app.invalidate()

    def _navigate_history_up(self, event) -> None:
        """Navigate up through command history."""
        if not self.chat_app._history:
            return

        # Store current input if we're starting to navigate
        if self.chat_app._history_position == -1:
            self.chat_app._current_input = self.chat_app.input_buffer.text

        # Move back in history
        if self.chat_app._history_position < len(self.chat_app._history) - 1:
            self.chat_app._history_position += 1
            # History is stored newest-first, so we go backwards from end
            history_index = len(self.chat_app._history) - 1 - self.chat_app._history_position
            self.chat_app.input_buffer.text = self.chat_app._history[history_index]
            # Move cursor to end
            self.chat_app.input_buffer.cursor_position = len(self.chat_app.input_buffer.text)

    def _navigate_history_down(self, event) -> None:
        """Navigate down through command history."""
        if self.chat_app._history_position == -1:
            return  # Already at current input

        # Move forward in history
        self.chat_app._history_position -= 1

        if self.chat_app._history_position == -1:
            # Back to current input
            self.chat_app.input_buffer.text = self.chat_app._current_input
        else:
            # Show history item
            history_index = len(self.chat_app._history) - 1 - self.chat_app._history_position
            self.chat_app.input_buffer.text = self.chat_app._history[history_index]

        # Move cursor to end
        self.chat_app.input_buffer.cursor_position = len(self.chat_app.input_buffer.text)