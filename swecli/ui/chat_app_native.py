"""Terminal-native chat application with unlimited scrollback."""

import asyncio
from typing import Callable, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from swecli.ui.terminal_printer import TerminalMessagePrinter


class NativeChatApplication:
    """Chat application using terminal-native output for unlimited scrollback."""

    def __init__(
        self,
        on_message: Optional[Callable[[str], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        completer=None,
    ):
        """Initialize native chat application.

        Args:
            on_message: Callback for when user sends a message
            on_exit: Callback for when user exits the application
            completer: Optional completer for autocomplete
        """
        self.on_message = on_message
        self.on_exit = on_exit
        self.printer = TerminalMessagePrinter()
        self._running = False

        # Create key bindings first (so they can be accessed by child classes)
        self.key_bindings = self._create_key_bindings()

        # Create prompt session for input
        self.session = PromptSession(
            completer=completer,
            multiline=False,
            enable_history_search=True,
            bottom_toolbar=self._get_bottom_toolbar,
            key_bindings=self.key_bindings,
            style=self._create_style(),
        )

        # Compatibility: expose session as 'app' for existing code
        self.app = self.session.app

        # Compatibility: dummy layout_manager
        self.layout_manager = None

    def _create_style(self) -> Style:
        """Create style for prompt."""
        return Style.from_dict({
            "bottom-toolbar": "#888888",
            "prompt": "#00FFFF bold",  # Cyan prompt
        })

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings."""
        kb = KeyBindings()

        @kb.add("c-c")
        def exit_app(event):
            """Exit on Ctrl+C."""
            self._running = False
            if self.on_exit:
                self.on_exit()
            event.app.exit()

        @kb.add("escape")
        def handle_escape(event):
            """Handle escape key (for interrupting operations)."""
            # For now, just clear input
            event.current_buffer.text = ""

        return kb

    def _get_bottom_toolbar(self):
        """Get bottom toolbar content."""
        # TODO: Get actual status from REPL
        return ANSI("\033[38;5;245m▶ normal mode • Context: 100% • Ctrl+C to exit\033[0m")

    def add_user_message(self, content: str) -> None:
        """Add and print user message."""
        self.printer.print_user_message(content)

    def add_assistant_message(self, content: str) -> None:
        """Add and print assistant message."""
        self.printer.print_assistant_message(content)

    def add_system_message(self, content: str) -> None:
        """Add and print system message."""
        self.printer.print_system_message(content)

    def update_spinner(self, text: str) -> None:
        """Update spinner display."""
        self.printer.print_spinner(text)

    def stop_spinner(self) -> None:
        """Stop and clear spinner."""
        self.printer.clear_spinner()

    def print_welcome(self, lines: list[str]) -> None:
        """Print welcome banner."""
        self.printer.print_welcome(lines)

    async def prompt_async(self) -> Optional[str]:
        """Get input from user asynchronously."""
        try:
            # Show prompt
            text = await self.session.prompt_async(
                ANSI("\033[1;36m› \033[0m"),  # Cyan › symbol
                default="",
            )
            return text.strip() if text else None
        except (KeyboardInterrupt, EOFError):
            return None

    def run(self) -> None:
        """Run the chat application."""
        self._running = True

        # Run async event loop
        asyncio.run(self._run_loop())

    async def _run_loop(self) -> None:
        """Main input loop."""
        while self._running:
            try:
                text = await self.prompt_async()

                if text is None:
                    # User cancelled (Ctrl+C or Ctrl+D)
                    break

                if not text:
                    # Empty input, skip
                    continue

                # Handle message
                if self.on_message:
                    if asyncio.iscoroutinefunction(self.on_message):
                        await self.on_message(text)
                    else:
                        self.on_message(text)

            except Exception as e:
                self.printer.print_system_message(f"Error: {e}")
                import traceback
                traceback.print_exc()

        # Cleanup on exit
        if self.on_exit:
            self.on_exit()

    # Compatibility methods for existing code
    def invalidate(self) -> None:
        """No-op for compatibility (no screen to invalidate)."""
        pass

    def safe_invalidate(self) -> None:
        """No-op for compatibility."""
        pass

    def _update_conversation_buffer(self) -> None:
        """No-op for compatibility."""
        pass

    @property
    def conversation(self):
        """Return a conversation object that prints to terminal."""
        parent = self
        class TerminalConversation:
            @property
            def messages(self):
                return []  # No stored messages needed

            def add_user_message(self, content):
                parent.add_user_message(content)

            def add_assistant_message(self, content):
                parent.add_assistant_message(content)

            def add_system_message(self, content):
                parent.add_system_message(content)

            def clear(self):
                pass  # Can't clear terminal

            def update_last_message(self, content):
                # For spinners - just print
                parent.printer.print_spinner(content)

        return TerminalConversation()
