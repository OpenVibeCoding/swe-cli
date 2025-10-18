"""Animation components for SWE-CLI UI."""

import threading
import time
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.text import Text


class Spinner:
    """Animated spinner for loading states (LLM thinking)."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]  # Basic Braille Dots
    INTERVAL = 0.05  # 50ms per frame (faster, smoother animation)

    def __init__(self, console: Console):
        """Initialize spinner.

        Args:
            console: Rich console for output
        """
        self.console = console
        self.live: Optional[Live] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, message: str = "Thinking...") -> None:
        """Start spinner animation.

        Args:
            message: Message to display with spinner
        """
        if self._running:
            return

        self._running = True
        self._message = message

        # Start animation in background thread
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def _animate(self) -> None:
        """Animation loop (runs in background thread)."""
        with Live(console=self.console, auto_refresh=False, transient=True) as live:
            self.live = live
            frame_idx = 0

            while self._running:
                frame = self.FRAMES[frame_idx % len(self.FRAMES)]
                text = Text(f"{frame} {self._message}", style="dim")
                live.update(text)
                live.refresh()

                frame_idx += 1
                time.sleep(self.INTERVAL)

    def stop(self) -> None:
        """Stop spinner animation."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.2)
        self._thread = None


class FlashingSymbol:
    """Flashing symbol for active tool execution."""

    FRAMES = ["⏺", "⏵", "▷", "⏵"]  # Pulse pattern
    INTERVAL = 0.25  # 250ms per frame

    def __init__(self, console: Console):
        """Initialize flashing symbol.

        Args:
            console: Rich console for output
        """
        self.console = console
        self.live: Optional[Live] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, tool_call_text: str) -> None:
        """Start flashing animation for tool call.

        Args:
            tool_call_text: Tool call description to display
        """
        if self._running:
            return

        self._running = True
        self._tool_call_text = tool_call_text

        # Start animation in background thread
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def _animate(self) -> None:
        """Animation loop (runs in background thread)."""
        with Live(console=self.console, auto_refresh=False, transient=True) as live:
            self.live = live
            frame_idx = 0

            while self._running:
                frame = self.FRAMES[frame_idx % len(self.FRAMES)]
                # Keep cyan color for tool calls
                text = Text()
                text.append(f"\n{frame} ", style="cyan")
                text.append(self._tool_call_text, style="cyan")

                live.update(text)
                live.refresh()

                frame_idx += 1
                time.sleep(self.INTERVAL)

    def stop(self) -> None:
        """Stop flashing animation."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.2)
        self._thread = None


class ProgressIndicator:
    """Progress indicator for long-running operations."""

    def __init__(self, console: Console):
        """Initialize progress indicator.

        Args:
            console: Rich console for output
        """
        self.console = console
        self.live: Optional[Live] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time: float = 0

    def start(self, message: str) -> None:
        """Start progress indicator with elapsed time.

        Args:
            message: Operation message
        """
        if self._running:
            return

        self._running = True
        self._message = message
        self._start_time = time.time()

        # Start update loop in background
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    def _update_loop(self) -> None:
        """Update loop showing elapsed time."""
        with Live(console=self.console, auto_refresh=False, transient=True) as live:
            self.live = live
            spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            frame_idx = 0

            while self._running:
                elapsed = time.time() - self._start_time

                # Show elapsed time after 2 seconds
                if elapsed >= 2.0:
                    spinner = spinner_frames[frame_idx % len(spinner_frames)]
                    text = Text()
                    text.append(f"  {self._message} ", style="dim")
                    text.append(f"({elapsed:.0f}s elapsed)", style="dim yellow")
                    text.append(f" {spinner}", style="dim")
                    live.update(text)
                    live.refresh()

                frame_idx += 1
                time.sleep(0.1)

    def stop(self) -> None:
        """Stop progress indicator."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.2)
        self._thread = None
