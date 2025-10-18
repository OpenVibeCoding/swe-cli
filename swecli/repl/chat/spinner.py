"""Animated spinner for chat interface."""

import threading
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from swecli.ui.chat_app import Conversation


class ChatSpinner:
    """Animated spinner with gradient colors for chat interface."""

    # Braille dots for animated spinner (same as TaskProgressDisplay)
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    SPINNER_UPDATE_INTERVAL = 0.1  # Update every 100ms for smooth animation

    # Elegant color gradient for spinner animation (slow, luxury transition)
    SPINNER_COLORS = [
        "\033[38;5;39m",  # Deep sky blue
        "\033[38;5;45m",  # Turquoise
        "\033[38;5;51m",  # Cyan
        "\033[38;5;87m",  # Sky blue
        "\033[38;5;123m",  # Light cyan
        "\033[38;5;87m",  # Sky blue
        "\033[38;5;51m",  # Cyan
        "\033[38;5;45m",  # Turquoise
        "\033[38;5;39m",  # Deep sky blue
        "\033[38;5;33m",  # Dodger blue
    ]

    def __init__(self, conversation: "Conversation", update_callback, buffer_update_callback=None):
        """Initialize spinner.

        Args:
            conversation: Conversation object to add messages to
            update_callback: Callback function to refresh UI (typically app.invalidate)
            buffer_update_callback: Optional callback to update conversation buffer
        """
        self.conversation = conversation
        self.update_callback = update_callback
        self.buffer_update_callback = buffer_update_callback

        # Spinner state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_index = 0
        self._text = ""
        self._start_time = 0.0

    def start(self, text: str, add_message_callback) -> None:
        """Start animated spinner with given text.

        Args:
            text: Text to display after spinner
            add_message_callback: Callback to add assistant message (e.g., self.add_assistant_message)
        """
        # Stop any existing spinner first
        self.stop()

        self._text = text
        self._running = True
        self._frame_index = 0
        self._start_time = time.time()

        # Add initial spinner message with gradient color animation
        spinner_char = self.SPINNER_FRAMES[0]
        color = self.SPINNER_COLORS[0]
        add_message_callback(f"{color}{spinner_char}\033[0m {text} (0s • esc to interrupt)")

        # Start animation thread
        self._thread = threading.Thread(target=self._animation_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the animated spinner."""
        if not self._running:
            return

        self._running = False

        # Wait for thread to finish (very short timeout for instant UX)
        if self._thread:
            self._thread.join(timeout=0.01)  # 10ms - instant from user perspective
            self._thread = None

        # Remove spinner message if it's still there
        if (
            self.conversation.messages
            and len(self.conversation.messages) > 0
            and any(char in self.conversation.messages[-1][1] for char in self.SPINNER_FRAMES)
        ):
            self.conversation.messages.pop()
            # Update conversation buffer if callback provided
            if self.buffer_update_callback:
                self.buffer_update_callback()
            # Trigger UI update through callback
            self.update_callback()

    def _animation_loop(self) -> None:
        """Background thread that animates the spinner."""
        while self._running:
            time.sleep(self.SPINNER_UPDATE_INTERVAL)

            if not self._running:
                break

            # Update frame index
            self._frame_index = (self._frame_index + 1) % len(self.SPINNER_FRAMES)
            spinner_char = self.SPINNER_FRAMES[self._frame_index]

            # Cycle through colors slowly for elegant gradient effect
            color_index = self._frame_index % len(self.SPINNER_COLORS)
            color = self.SPINNER_COLORS[color_index]

            # Calculate elapsed time
            elapsed_seconds = int(time.time() - self._start_time)

            # Update last message if it contains a spinner
            if (
                self.conversation.messages
                and len(self.conversation.messages) > 0
                and any(char in self.conversation.messages[-1][1] for char in self.SPINNER_FRAMES)
            ):
                # Replace with new spinner frame with color gradient animation on entire line
                old_message = self.conversation.messages[-1]
                self.conversation.messages[-1] = (
                    old_message[0],  # role
                    f"{color}{spinner_char} {self._text} ({elapsed_seconds}s • esc to interrupt)\033[0m",  # gradient animation on entire text
                    old_message[2] if len(old_message) > 2 else None,  # timestamp
                )
                # Trigger UI update through callback
                self.update_callback()
