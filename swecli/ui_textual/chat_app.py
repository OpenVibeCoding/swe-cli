"""Textual-based chat application for SWE-CLI - POC."""

from datetime import datetime
from typing import Callable, Optional

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.events import Key
from textual.widgets import Footer, Header, Input, RichLog, Static, TextArea


class ConversationLog(RichLog):
    """Enhanced RichLog for conversation display with scrolling support."""

    # Make it focusable so it can receive mouse/keyboard events
    can_focus = True

    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            wrap=True,
            highlight=True,
            markup=True,
            auto_scroll=True,  # Auto-scroll to bottom on new messages
            max_lines=10000,  # Large scrollback buffer
        )
        self._user_scrolled = False

    def add_user_message(self, message: str) -> None:
        """Add user message to conversation."""
        self.write(Text(f"› {message}", style="bold cyan"))

    def add_assistant_message(self, message: str) -> None:
        """Add assistant message to conversation."""
        self.write(Text(f"⏺ {message}", style="white"))

    def add_system_message(self, message: str) -> None:
        """Add system message to conversation."""
        self.write(Text(message, style="dim italic"))

    def add_tool_call(self, tool_name: str, args: str) -> None:
        """Add tool call to conversation."""
        formatted = Text()
        formatted.append("⏺ ", style="white")
        formatted.append(tool_name, style="bold bright_cyan")
        formatted.append(f"({args})", style="bright_cyan")
        self.write(formatted)

    def add_tool_result(self, result: str) -> None:
        """Add tool result to conversation."""
        self.write(Text(f"  ⎿ {result}", style="green"))

    def add_error(self, error: str) -> None:
        """Add error message to conversation."""
        self.write(Text(f"❌ {error}", style="bold red"))




class ChatTextArea(TextArea):
    """Custom TextArea with Enter to send, Shift+Enter for new lines."""

    def on_key(self, event: Key) -> None:
        """Handle key events at the widget level."""
        # We'll handle this at the app level instead
        pass


class StatusBar(Static):
    """Custom status bar showing mode, context, and hints."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "normal"
        self.context_pct = 0
        self.model = "claude-sonnet-4"

    def on_mount(self) -> None:
        """Update status on mount."""
        self.update_status()

    def set_mode(self, mode: str) -> None:
        """Update mode display."""
        self.mode = mode
        self.update_status()

    def set_context(self, pct: int) -> None:
        """Update context percentage."""
        self.context_pct = pct
        self.update_status()

    def update_status(self) -> None:
        """Update status bar text."""
        mode_color = "yellow" if self.mode == "normal" else "green"
        status = Text()
        status.append("⏵⏵ ", style="bold")
        status.append(f"{self.mode} mode", style=f"bold {mode_color}")
        status.append("  •  ", style="dim")
        status.append(f"Context: {self.context_pct}%", style="dim")
        status.append("  •  ", style="dim")
        status.append(f"Model: {self.model}", style="magenta")
        status.append("  •  ", style="dim")
        status.append("Ctrl+C to exit", style="dim")

        self.update(status)


class SWECLIChatApp(App):
    """SWE-CLI Chat Application using Textual."""

    CSS = """
    Screen {
        background: $background;
    }

    #main-container {
        height: 100%;
        layout: vertical;
    }

    #conversation {
        height: 1fr;
        border: solid $accent;
        background: $surface;
        padding: 0 1;
        overflow-y: scroll;  /* Enable vertical scrolling */
    }

    #input-container {
        height: auto;
        layout: vertical;
    }

    #input-label {
        height: 1;
        content-align: left middle;
        color: $accent;
        background: $surface;
        padding: 0 1;
    }

    #input {
        height: 5;
        max-height: 15;
        min-height: 3;
        border: solid $accent;
        background: $surface;
    }

    #status-bar {
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
        content-align: left middle;
    }

    Input {
        background: $surface;
        color: $text;
    }

    Input:focus {
        border: solid $accent;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_conversation", "Clear"),
        Binding("escape", "interrupt", "Interrupt"),
        Binding("pageup", "scroll_up", "Scroll Up", show=False),
        Binding("pagedown", "scroll_down", "Scroll Down", show=False),
        Binding("up", "scroll_up_line", "Scroll Up One Line", show=False),
        Binding("down", "scroll_down_line", "Scroll Down One Line", show=False),
        Binding("ctrl+up", "focus_conversation", "Focus Conversation", show=False),
        Binding("ctrl+down", "focus_input", "Focus Input", show=False),
    ]

    def __init__(
        self,
        on_message: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        """Initialize chat application.

        Args:
            on_message: Callback for when user sends a message
        """
        super().__init__(**kwargs)
        self.on_message = on_message
        self._is_processing = False
        self._message_history = []

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # Conversation area
            yield ConversationLog(id="conversation")

            # Input area
            with Vertical(id="input-container"):
                yield Static("› Type your message (Enter to send):", id="input-label")
                yield Input(
                    id="input",
                    placeholder="Type your message..."
                )

            # Status bar
            yield StatusBar(id="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        self.title = "SWE-CLI Chat (Textual POC)"
        self.sub_title = "Full-screen terminal interface"

        # Get widgets
        self.conversation = self.query_one("#conversation", ConversationLog)
        self.input_field = self.query_one("#input", Input)
        self.status_bar = self.query_one("#status-bar", StatusBar)

        # Focus input field
        self.input_field.focus()

        # Add welcome message
        self.conversation.add_system_message("╭──────────────────────────────────────────────╮")
        self.conversation.add_system_message("│   Welcome to SWE-CLI (Textual POC)          │")
        self.conversation.add_system_message("│   Full-screen terminal interface test       │")
        self.conversation.add_system_message("╰──────────────────────────────────────────────╯")
        self.conversation.add_system_message("")
        self.conversation.add_assistant_message(
            "Hello! This is a proof-of-concept for the new Textual-based UI."
        )
        self.conversation.add_assistant_message(
            "Try typing a message (multi-line supported!). Press Ctrl+Enter to send."
        )
        self.conversation.add_assistant_message("  • /help - Show available commands")
        self.conversation.add_assistant_message("  • /scroll - Generate messages to test scrolling")
        self.conversation.add_assistant_message("  • /demo - Show message types")
        self.conversation.add_system_message("")
        self.conversation.add_system_message("✨ Multi-line input: Press Enter for new line, Ctrl+Enter to send")
        self.conversation.add_system_message("💡 Scrolling: Press Ctrl+Up to focus conversation, then use arrow keys")
        self.conversation.add_system_message("")

        # Simulate some context
        self.status_bar.set_context(15)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission when user presses Enter."""
        message = event.value.strip()

        if not message:
            return

        # Clear input field
        self.input_field.clear()

        # Add to history
        self._message_history.append(message)

        # Display user message
        self.conversation.add_user_message(message)

        # Handle special commands
        if message.startswith("/"):
            await self.handle_command(message)
        else:
            await self.process_message(message)

    async def action_send_message(self) -> None:
        """Send message when user presses Enter."""
        message = self.input_field.value.strip()

        if not message:
            return

        # Clear input field
        self.input_field.clear()

        # Add to history
        self._message_history.append(message)

        # Display user message
        self.conversation.add_user_message(message)

        # Handle special commands
        if message.startswith("/"):
            await self.handle_command(message)
        else:
            await self.process_message(message)

    async def handle_command(self, command: str) -> None:
        """Handle slash commands."""
        cmd = command.lower().split()[0]

        if cmd == "/help":
            self.conversation.add_system_message("Available commands:")
            self.conversation.add_system_message("  /help - Show this help")
            self.conversation.add_system_message("  /clear - Clear conversation")
            self.conversation.add_system_message("  /demo - Show demo messages")
            self.conversation.add_system_message("  /scroll - Generate many messages (test scrolling)")
            self.conversation.add_system_message("  /quit - Exit application")
            self.conversation.add_system_message("")
            self.conversation.add_system_message("✨ Input:")
            self.conversation.add_system_message("  Enter - Send message")
            self.conversation.add_system_message("  Type your message and press Enter!")
            self.conversation.add_system_message("")
            self.conversation.add_system_message("📜 Scrolling:")
            self.conversation.add_system_message("  Ctrl+Up - Focus conversation (then use arrow keys)")
            self.conversation.add_system_message("  Ctrl+Down - Focus input (for typing)")
            self.conversation.add_system_message("  Arrow Up/Down - Scroll line by line")
            self.conversation.add_system_message("  Page Up/Down - Scroll by page")
            self.conversation.add_system_message("")
            self.conversation.add_system_message("⌨️  Other Shortcuts:")
            self.conversation.add_system_message("  Ctrl+L - Clear conversation")
            self.conversation.add_system_message("  Ctrl+C - Quit application")
            self.conversation.add_system_message("  ESC - Interrupt processing")

        elif cmd == "/clear":
            self.conversation.clear()
            self.conversation.add_system_message("Conversation cleared.")

        elif cmd == "/demo":
            # Demonstrate different message types
            self.conversation.add_assistant_message(
                "Here's a demo of different message types:"
            )
            self.conversation.add_system_message("")

            # Tool call example
            self.conversation.add_tool_call("Shell", "command='ls -la'")
            self.conversation.add_tool_result("total 64\ndrwxr-xr-x  10 user  staff   320 Jan 27 10:00 .")

            self.conversation.add_system_message("")
            self.conversation.add_tool_call("Read", "file_path='swecli/cli.py'")
            self.conversation.add_tool_result("File read successfully (250 lines)")

            self.conversation.add_system_message("")
            self.conversation.add_tool_call("Write", "file_path='test.py', content='...'")
            self.conversation.add_tool_result("File written successfully")

            self.conversation.add_system_message("")
            self.conversation.add_error("Example error: File not found")

        elif cmd == "/scroll":
            # Generate many messages to test scrolling
            self.conversation.add_assistant_message("Generating 50 messages to test scrolling...")
            self.conversation.add_system_message("")
            for i in range(1, 51):
                if i % 10 == 0:
                    self.conversation.add_system_message(f"--- Message {i} ---")
                elif i % 5 == 0:
                    self.conversation.add_tool_call("TestTool", f"iteration={i}")
                    self.conversation.add_tool_result(f"Result for iteration {i}")
                elif i % 3 == 0:
                    self.conversation.add_user_message(f"Test user message {i}")
                else:
                    self.conversation.add_assistant_message(f"Test assistant message {i}: Lorem ipsum dolor sit amet, consectetur adipiscing elit.")
            self.conversation.add_system_message("")
            self.conversation.add_assistant_message("✓ Done! Try scrolling up with mouse wheel or Page Up.")

        elif cmd == "/quit":
            self.exit()

        else:
            self.conversation.add_error(f"Unknown command: {cmd}")

    async def process_message(self, message: str) -> None:
        """Process user message.

        This is where we'll integrate with the existing REPL logic.
        For now, just echo back with some formatting.
        """
        self._is_processing = True

        # Simulate processing
        self.conversation.add_assistant_message(f"You said: {message}")

        # Simulate a tool call
        if len(message) > 20:
            self.conversation.add_system_message("")
            self.conversation.add_assistant_message("That's a long message! Let me analyze it...")
            self.conversation.add_tool_call("Analyze", f"text='{message[:30]}...'")
            self.conversation.add_tool_result(f"Analysis complete: {len(message)} characters, {len(message.split())} words")

        # Call external callback if provided
        if self.on_message:
            self.on_message(message)

        self._is_processing = False

        # Update context simulation
        new_context = min(95, self.status_bar.context_pct + 5)
        self.status_bar.set_context(new_context)

    def action_clear_conversation(self) -> None:
        """Clear the conversation (Ctrl+L)."""
        self.conversation.clear()
        self.conversation.add_system_message("Conversation cleared (Ctrl+L)")

    def action_interrupt(self) -> None:
        """Interrupt processing (ESC)."""
        if self._is_processing:
            self.conversation.add_system_message("⚠ Processing interrupted")
            self._is_processing = False
        else:
            self.conversation.add_system_message("Nothing to interrupt")

    def action_quit(self) -> None:
        """Quit the application (Ctrl+C)."""
        self.exit()

    def action_scroll_up(self) -> None:
        """Scroll conversation up (Page Up)."""
        self.conversation.scroll_page_up()

    def action_scroll_down(self) -> None:
        """Scroll conversation down (Page Down)."""
        self.conversation.scroll_page_down()

    def action_scroll_up_line(self) -> None:
        """Scroll conversation up one line (Up Arrow)."""
        # Only scroll if conversation has focus, otherwise let input handle it
        if self.conversation.has_focus:
            self.conversation.scroll_up()
        elif not self.input_field.has_focus:
            # If nothing focused, scroll conversation anyway
            self.conversation.scroll_up()

    def action_scroll_down_line(self) -> None:
        """Scroll conversation down one line (Down Arrow)."""
        # Only scroll if conversation has focus, otherwise let input handle it
        if self.conversation.has_focus:
            self.conversation.scroll_down()
        elif not self.input_field.has_focus:
            # If nothing focused, scroll conversation anyway
            self.conversation.scroll_down()

    def action_focus_conversation(self) -> None:
        """Focus the conversation area for scrolling (Ctrl+Up)."""
        self.conversation.focus()
        self.conversation.add_system_message("📜 Conversation focused - use arrow keys or trackpad to scroll")

    def action_focus_input(self) -> None:
        """Focus the input field for typing (Ctrl+Down)."""
        self.input_field.focus()


def create_chat_app(on_message: Optional[Callable[[str], None]] = None) -> SWECLIChatApp:
    """Create and return a new chat application instance.

    Args:
        on_message: Optional callback for message processing

    Returns:
        Configured SWECLIChatApp instance
    """
    return SWECLIChatApp(on_message=on_message)


if __name__ == "__main__":
    # Run standalone for testing
    def handle_message(text: str):
        # Callback for external message handling
        # Don't print here - it will interfere with the UI!
        pass

    app = create_chat_app(on_message=handle_message)
    # Run in application mode (full screen with alternate screen buffer)
    # This is the default behavior when inline is not specified
    app.run()
