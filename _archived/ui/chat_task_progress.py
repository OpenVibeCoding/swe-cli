"""Task progress display for chat interface."""

import threading
import time
from typing import Optional

from opencli.core.monitoring import TaskMonitor


class ChatTaskProgressDisplay:
    """Display task progress in chat conversation."""

    UPDATE_INTERVAL = 0.5  # Update every 500ms

    # Spinner frames (Braille dots)
    SPINNER_FRAMES = [
        "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"
    ]

    def __init__(self, chat_app, task_monitor: TaskMonitor):
        """Initialize chat task progress display.

        Args:
            chat_app: ChatApplication instance
            task_monitor: TaskMonitor instance tracking the task
        """
        self.chat_app = chat_app
        self.task_monitor = task_monitor
        self._running = False
        self._update_thread: Optional[threading.Thread] = None
        self._frame_index = 0

    def start(self) -> None:
        """Start displaying task progress."""
        if self._running:
            return

        self._running = True

        # Add initial thinking message
        task_desc = self.task_monitor.get_task_description()
        spinner = self.SPINNER_FRAMES[0]
        self.chat_app.add_assistant_message(f"{spinner} {task_desc}...")
        self.chat_app.conversation.last_was_spinner = True

        # Start update loop in background thread
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()

    def stop(self) -> None:
        """Stop displaying task progress."""
        self._running = False

        # Wait for update thread to finish
        if self._update_thread:
            self._update_thread.join(timeout=0.5)
            self._update_thread = None

    def _update_loop(self) -> None:
        """Update loop running in background thread."""
        while self._running and self.task_monitor.is_running():
            # Format progress message
            spinner = self.SPINNER_FRAMES[self._frame_index]
            task_desc = self.task_monitor.get_task_description()
            elapsed = self.task_monitor.get_elapsed_seconds()

            # Build message
            message = f"{spinner} {task_desc}… ({elapsed}s)"

            # Update last message in conversation
            self.chat_app.update_last_message(message)

            # Advance spinner frame
            self._frame_index = (self._frame_index + 1) % len(self.SPINNER_FRAMES)

            # Wait for next update
            time.sleep(self.UPDATE_INTERVAL)

    def print_final_status(self) -> None:
        """Print final status after task completes."""
        stats = self.task_monitor.stop()

        # Just remove the spinner - the actual response will be added by console output
        # Don't update with final status here, let the LLM response replace it
        pass
