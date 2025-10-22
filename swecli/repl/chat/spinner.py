"""Animated spinner for chat interface."""

import threading
import time
from typing import Optional, TYPE_CHECKING

from swecli.ui.components.tips import TipsManager

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
        self._lock = threading.Lock()  # Protect against race conditions

        # Tips manager for displaying helpful hints
        self._tips_manager = TipsManager()
        self._current_tip = ""

    def start(self, text: str, add_message_callback) -> None:
        """Start animated spinner with given text.

        Args:
            text: Text to display after spinner
            add_message_callback: Callback to add assistant message (e.g., self.add_assistant_message)
        """
        # CRITICAL: Use lock to prevent race condition with animation thread
        with self._lock:
            # ALWAYS stop animation thread, regardless of _running state
            # This handles cases where stop() is called multiple times
            self._running = False

        # Wait for thread to terminate if it exists (outside lock to avoid deadlock)
        if self._thread:
            self._thread.join(timeout=0.5)  # Wait longer to ensure thread stops
            self._thread = None

        # Remove ALL spinner messages from conversation before starting new one
        # Use lock to ensure animation thread can't add messages during removal
        with self._lock:
            if self.conversation.messages:
                self.conversation.messages[:] = [
                    msg for msg in self.conversation.messages
                    if not any(char in msg[1] for char in self.SPINNER_FRAMES)
                ]

            # Now safe to start new spinner
            self._text = text
            self._running = True
            self._frame_index = 0
            self._start_time = time.time()

            # Get a new tip for this spinner
            self._current_tip = self._tips_manager.get_next_tip()

        # Add initial spinner message with gradient color animation and tip
        spinner_char = self.SPINNER_FRAMES[0]
        color = self.SPINNER_COLORS[0]

        # Format tip with dim gray color (Claude Code style)
        tip_color = "\033[38;5;240m"  # Dim gray
        reset = "\033[0m"
        formatted_tip = f"{tip_color}  ⎿ Tip: {self._current_tip}{reset}"

        # Combine spinner line and tip (two lines)
        spinner_with_tip = f"{color}{spinner_char}{reset} {text} (0s • esc to interrupt)\n{formatted_tip}"
        add_message_callback(spinner_with_tip)

        # Start NEW animation thread
        self._thread = threading.Thread(target=self._animation_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the animated spinner and remove ALL spinner messages."""
        # CRITICAL: Use lock to prevent race condition with animation thread
        with self._lock:
            # ALWAYS stop animation thread, regardless of _running state
            # This handles cases where stop() is called multiple times
            self._running = False

        # Wait for thread to terminate if it exists (outside lock to avoid deadlock)
        if self._thread:
            self._thread.join(timeout=0.5)  # Wait longer to ensure thread stops
            self._thread = None

        # Remove ALL messages containing spinner characters (not just last one)
        # Use lock to ensure animation thread can't add messages during removal
        with self._lock:
            if self.conversation.messages:
                before_count = len(self.conversation.messages)
                self.conversation.messages[:] = [
                    msg for msg in self.conversation.messages
                    if not any(char in msg[1] for char in self.SPINNER_FRAMES)
                ]
                spinners_removed = (before_count != len(self.conversation.messages))

        # Always trigger UI update when stop() is called
        # Only force heavy refresh if we actually removed spinners
        if spinners_removed and self.buffer_update_callback:
            self.buffer_update_callback()

        # Trigger screen invalidation
        self.update_callback()

    def _animation_loop(self) -> None:
        """Background thread that animates the spinner."""
        while True:
            # Check if we should stop IMMEDIATELY at start of loop
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

            # CRITICAL: Use lock to prevent race condition with stop()
            # This ensures we atomically check _running and update messages
            with self._lock:
                # Check if still running before updating
                if not self._running:
                    break

                # Update last message if it contains a spinner
                if (
                    self.conversation.messages
                    and len(self.conversation.messages) > 0
                    and any(char in self.conversation.messages[-1][1] for char in self.SPINNER_FRAMES)
                ):
                    # Format tip with dim gray color (Claude Code style)
                    tip_color = "\033[38;5;240m"  # Dim gray
                    reset = "\033[0m"
                    formatted_tip = f"{tip_color}  ⎿ Tip: {self._current_tip}{reset}"

                    # Combine spinner line and tip (two lines)
                    spinner_with_tip = f"{color}{spinner_char}{reset} {self._text} ({elapsed_seconds}s • esc to interrupt)\n{formatted_tip}"

                    # Replace with new spinner frame with tip below it
                    old_message = self.conversation.messages[-1]
                    self.conversation.messages[-1] = (
                        old_message[0],  # role
                        spinner_with_tip,  # spinner line + tip
                        old_message[2] if len(old_message) > 2 else None,  # timestamp
                    )
                    # Trigger UI update through callback
                    self.update_callback()

            # Sleep AFTER update to ensure stable timing
            # Check _running again before sleeping to exit quickly if stopped
            if not self._running:
                break
            time.sleep(self.SPINNER_UPDATE_INTERVAL)
