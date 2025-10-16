"""Input handling for chat application."""

from prompt_toolkit.buffer import Buffer


class InputHandler:
    """Handles user input processing and validation."""

    def __init__(self, app):
        """Initialize input handler.

        Args:
            app: The chat application instance
        """
        self.app = app
        self._paste_threshold = 500  # Chars threshold for paste detection

    def on_text_insert(self, buffer: Buffer) -> None:
        """Handle text insertion - detect large pastes and replace with placeholder."""
        # Note: No need to check approval mode here - keys are blocked at key binding level
        text = buffer.text

        # Detect large paste (content longer than threshold)
        if len(text) > self._paste_threshold and not text.startswith("[[Pasted Content"):
            self._handle_large_paste(buffer, text)
        else:
            self._handle_auto_completion(buffer, text)

    def _handle_large_paste(self, buffer: Buffer, text: str) -> None:
        """Handle large text paste by showing placeholder."""
        # Store original content
        self.app._pasted_content = text

        # Create placeholder
        char_count = len(text)
        placeholder = f"[[Pasted Content {char_count} chars]]"

        # Replace buffer content with placeholder
        buffer.text = placeholder
        # Move cursor to end
        buffer.cursor_position = len(placeholder)

    def _handle_auto_completion(self, buffer: Buffer, text: str) -> None:
        """Handle auto-completion triggering."""
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

    def on_buffer_text_changed(self, buffer: Buffer) -> None:
        """Immediately revert any text changes during approval mode only."""
        # Prevent recursion - if we're already clearing, don't trigger again
        if getattr(self.app, "_clearing_buffer", False):
            return

        # Protect buffer during approval mode (user should not be able to type during approval)
        # NOTE: We don't block during general processing - that would prevent users from
        # typing their next query while waiting for results (bad UX)
        is_approval_mode = getattr(self.app, "_approval_mode", False)

        # If in approval mode and text was added to real buffer, clear it immediately
        if is_approval_mode and buffer is self.app.input_buffer:
            if buffer.text:
                # Set flag to prevent recursion
                self.app._clearing_buffer = True
                try:
                    # Revert any text that appeared
                    buffer.text = ""
                    buffer.cursor_position = 0
                finally:
                    self.app._clearing_buffer = False