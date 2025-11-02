"""Textual-based chat application for SWE-CLI - POC."""

import asyncio
import re
import threading
from typing import Any, Callable, Mapping, Optional

from prompt_toolkit.completion import Completer

from rich import box
from rich.console import Group, RenderableType
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.geometry import Size
from textual.widgets import Header, Rule, Static

from swecli.ui.components.tips import TipsManager
from swecli.ui_textual.widgets import ConversationLog
from swecli.ui_textual.widgets.chat_text_area import ChatTextArea
from swecli.ui_textual.widgets.status_bar import ModelFooter, StatusBar
from swecli.ui_textual.approval_prompt import ApprovalPromptController
from swecli.ui_textual.model_picker import ModelPickerController
from swecli.ui_textual.spinner import SpinnerController
from swecli.ui_textual.console_buffer import ConsoleBufferManager
from swecli.ui_textual.autocomplete_popup import AutocompletePopupController
from swecli.ui_textual.welcome_panel import render_welcome_panel
from swecli.ui.utils.tool_display import get_tool_display_parts, summarize_tool_arguments



class SWECLIChatApp(App):
    """SWE-CLI Chat Application using Textual."""

    CSS = """
    Screen {
        background: $background;
    }

    #main-container {
        height: 100%;
        layout: vertical;
        background: $background;
    }

    #conversation {
        height: 1fr;
        border: none;
        background: $background;
        padding: 1 2;
        overflow-y: scroll;
    }

    Rule {
        height: 1;
        color: $text 30%;            /* Text color with 30% opacity for separator */
        background: transparent;
        margin: 0;
    }

    #input-container {
        height: auto;
        layout: vertical;
        background: $background;
    }

    #input-label {
        height: 1;
        content-align: left middle;
        color: $text-muted;          /* Subtle label text */
        background: $background;
        padding: 0 2;
    }

    #input {
        height: 5;
        max-height: 15;
        min-height: 3;
        border: none;                /* No border by default */
        background: $background;
        padding: 1 2;
    }

    #autocomplete-popup {
        display: none;
        background: $surface-darken-2;
        color: $text;
        border: tall $surface;
        padding: 0 1;
        overflow-y: auto;
        margin: 1 2 0 2;
        max-height: 8;
    }

    #status-bar {
        height: 1;
        background: $background;
        color: $text-muted;
        padding: 0 2;
        content-align: left middle;
    }

    TextArea {
        background: $background;
        color: $text;
        border: none;
        min-width: 0;
        content-align: left top;
    }

    TextArea:focus {
        border-left: thick $accent;  /* Subtle left accent on focus */
        background: $background;     /* Keep same background on focus */
    }


    Footer {
        background: $background;
        color: $text;
    }

    Footer > .footer--links {
        color: $text-muted;
    }

    Footer > .footer--models {
        color: $text-muted;
        padding: 0 2;
        width: 1fr;
        min-width: 0;
    }

    Footer > .footer--keys {
        background: transparent;
    }

    FooterKey {
        background: $background;
        color: $text;
        border: none;
    }

    FooterKey .footer-key--key {
        background: $background;
        color: $text;
    }

    FooterKey .footer-key--description {
        background: $background;
        color: $text-muted;
    }

    FooterKey.-command-palette {
        border-left: none;
    }

    FooterKey:hover {
        background: $surface;
        color: $accent;
        .footer-key--key {
            background: $surface;
            color: $accent;
        }
        .footer-key--description {
            background: $surface;
            color: $accent;
        }
    }

    Footer:ansi {
        background: $background;
        .footer-key--key {
            background: $background;
            color: $text;
        }
        .footer-key--description {
            background: $background;
            color: $text-muted;
        }
        FooterKey.-command-palette {
            border-left: none;
        }
    }

    Footer > .footer--text {
        color: $text;
    }

    Footer > .footer--keys .key {
        background: $surface-darken-1;
        color: $text;
        border: none;
    }

    Footer > .footer--keys .key:hover {
        background: $surface;
        color: $accent;
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
        Binding("shift+tab", "cycle_mode", "Switch Mode"),
    ]

    def __init__(
        self,
        on_message: Optional[Callable[[str], None]] = None,
        model: str = "claude-sonnet-4",
        model_slots: Mapping[str, tuple[str, str]] | None = None,
        on_cycle_mode: Optional[Callable[[], str]] = None,
        completer: Optional[Completer] = None,
        on_model_selected: Optional[Callable[[str, str, str], Any]] = None,
        get_model_config: Optional[Callable[[], Mapping[str, Any]]] = None,
        **kwargs,
    ):
        """Initialize chat application.

        Args:
            on_message: Callback for when user sends a message
            model: Model name to display in status bar
            model_slots: Mapping of model slots (normal/thinking/vision) to human-readable values
            completer: Autocomplete provider for slash commands and @ mentions
            on_model_selected: Callback invoked after a model is selected
            get_model_config: Callback returning current model configuration details
        """
        # Set color system to inherit from terminal
        kwargs.setdefault("ansi_color", "auto")
        super().__init__(**kwargs)
        self.on_message = on_message
        self.on_cycle_mode = on_cycle_mode
        self.model = model
        self.completer = completer
        self.model_slots = dict(model_slots or {})
        self.on_model_selected = on_model_selected
        self.get_model_config = get_model_config
        self.autocomplete_popup: Static | None = None
        self._autocomplete_controller: AutocompletePopupController | None = None
        self.footer: ModelFooter | None = None
        self._is_processing = False
        self._message_history = []
        self._history_index = -1
        self._current_input = ""
        self._last_assistant_lines: set[str] = set()
        self._last_rendered_assistant: str | None = None
        self._last_assistant_normalized: str | None = None
        self._buffer_console_output = False
        self._pending_assistant_normalized: str | None = None
        self._pending_tool_summaries: list[str] = []
        self._assistant_response_received = False
        self._saw_tool_result = False
        self._ui_thread: threading.Thread | None = None
        self._tips_manager = TipsManager()
        self._model_picker: ModelPickerController = ModelPickerController(self)
        self._approval_controller = ApprovalPromptController(self)
        self._spinner = SpinnerController(self, self._tips_manager)
        self._console_buffer = ConsoleBufferManager(self)
        self._queued_console_renderables = self._console_buffer._queue

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # Conversation area
            yield ConversationLog(id="conversation")

            # Separator line between conversation and input
            yield Rule(line_style="solid")

            # Input area
            with Vertical(id="input-container"):
                yield Static(
                    "› Type your message (Enter to send, Shift+Enter for new line):",
                    id="input-label",
                )
                yield ChatTextArea(
                    id="input",
                    placeholder="Type your message...",
                    soft_wrap=True,
                    completer=self.completer,
                )

            # Status bar
            yield StatusBar(model=self.model, id="status-bar")

        yield ModelFooter(self.model_slots, id="model-footer")

    def on_mount(self) -> None:
        """Initialize the app on mount."""

        self._ui_thread = threading.current_thread()

        # Get widgets
        self.conversation = self.query_one("#conversation", ConversationLog)
        self.input_field = self.query_one("#input", ChatTextArea)
        input_container = self.query_one("#input-container")
        self.status_bar = self.query_one("#status-bar", StatusBar)
        self.footer = self.query_one("#model-footer", ModelFooter)
        self.input_field.set_completer(self.completer)
        self.autocomplete_popup = Static("", id="autocomplete-popup")
        self.autocomplete_popup.can_focus = False
        self.autocomplete_popup.styles.display = "none"
        input_container.mount(self.autocomplete_popup)
        self._autocomplete_controller = AutocompletePopupController(self.autocomplete_popup)
        self.update_autocomplete([], None)

        # Focus input field
        self.input_field.focus()

        # Show different welcome message based on whether we have real backend integration
        if self.on_message:
            self.title = "SWE-CLI Chat"
            self.sub_title = "AI-powered coding assistant"
            render_welcome_panel(self.conversation, real_integration=True)
            self.status_bar.set_context(15)
        else:
            self.title = "SWE-CLI Chat (Textual POC)"
            self.sub_title = "Full-screen terminal interface"
            render_welcome_panel(self.conversation, real_integration=False)
            self.status_bar.set_context(15)

    def update_model_slots(self, model_slots: Mapping[str, tuple[str, str]] | None) -> None:
        """Update footer model display with new slot information."""
        self.model_slots = dict(model_slots or {})
        if self.footer is not None:
            self.footer.update_models(self.model_slots)

    def update_primary_model(self, model: str) -> None:
        """Update the primary model label shown in the status bar."""
        self.model = model
        if hasattr(self, "status_bar"):
            self.status_bar.set_model_name(model)


    def update_autocomplete(
        self,
        entries: list[tuple[str, str]],
        selected_index: int | None = None,
    ) -> None:
        """Render autocomplete options directly beneath the input field."""

        controller = self._autocomplete_controller
        if controller is None:
            return

        if self._approval_controller.active:
            controller.reset()
            return

        controller.render(entries, selected_index)


    def _start_local_spinner(self, message: str | None = None) -> None:
        """Begin local spinner animation while backend processes."""

        if hasattr(self, "_console_buffer"):
            self._console_buffer.clear()
        self._spinner.start(message)

    def _stop_local_spinner(self) -> None:
        """Stop spinner animation and clear indicators."""

        self._spinner.stop()
        if hasattr(self, "_console_buffer"):
            self._console_buffer.clear_assistant_history()
            self._console_buffer.flush()
        self.flush_console_buffer()

    def resume_reasoning_spinner(self) -> None:
        """Restart the thinking spinner after tool output while waiting for reply."""

        if not self._is_processing:
            return

        self._stop_local_spinner()
        self._start_local_spinner()

    def flush_console_buffer(self) -> None:
        """Flush queued console renderables after assistant message is recorded."""

        if hasattr(self, "_console_buffer"):
            self._console_buffer.flush()

    def start_console_buffer(self) -> None:
        """Begin buffering console output to avoid interleaving with spinner."""

        self._buffer_console_output = True
        if hasattr(self, "_console_buffer"):
            self._console_buffer.start()

    def stop_console_buffer(self) -> None:
        """Stop buffering console output and flush any pending items."""

        self._buffer_console_output = False
        if hasattr(self, "_console_buffer"):
            self._console_buffer.stop()

    @staticmethod
    def _normalize_assistant_line(line: str) -> str:
        return ConsoleBufferManager._normalize_line(line)

    @staticmethod
    def _normalize_paragraph(text: str) -> str:
        return ConsoleBufferManager._normalize_paragraph(text)

    def _should_suppress_renderable(self, renderable: RenderableType) -> bool:
        if hasattr(self, "_console_buffer"):
            return self._console_buffer.should_suppress(renderable)
        return False


    def render_console_output(self, renderable: RenderableType) -> None:
        """Render console output, buffering if spinner is active."""

        if hasattr(self, "_console_buffer"):
            self._console_buffer.enqueue_or_write(renderable)
        elif hasattr(self, "conversation"):
            self.conversation.write(renderable)


    def record_assistant_message(self, message: str) -> None:
        """Track assistant lines to suppress duplicate console echoes."""

        if hasattr(self, "_console_buffer"):
            self._console_buffer.record_assistant_message(message)

    async def action_send_message(self) -> None:
        """Send message when user presses Enter."""
        await self._submit_message(self.input_field.text)

    async def on_chat_text_area_submitted(self, event: ChatTextArea.Submitted) -> None:
        """Handle chat submissions from the custom text area."""
        await self._submit_message(event.value)

    async def _submit_message(self, raw_text: str) -> None:
        """Normalize, display, and process submitted chat text."""

        if not raw_text.strip():
            self.input_field.load_text("")
            return

        message_with_placeholders = raw_text.rstrip("\n")
        message = self.input_field.resolve_large_pastes(message_with_placeholders)

        self._reset_interaction_state()

        # Clear input field in preparation for the next message
        self.input_field.load_text("")
        self._history_index = -1
        self._current_input = ""
        self.input_field.clear_large_pastes()

        # Add to history
        self._message_history.append(message)

        # Display user message
        self.conversation.add_user_message(message)

        if self._model_picker.active:
            handled = await self._handle_model_picker_input(message.strip())
            if handled:
                return

        stripped_message = message.strip()

        # Handle special commands (trimmed for robustness)
        if stripped_message.startswith("/"):
            handled = await self.handle_command(stripped_message)
            if not handled and self.on_message:
                self.on_message(message)
            return

        await self.process_message(message)

    def add_assistant_message(self, message: str) -> None:
        """Proxy to conversation helper for compatibility with approval manager."""
        if hasattr(self, "conversation"):
            self.conversation.add_assistant_message(message)

    def add_system_message(self, message: str) -> None:
        """Proxy system message helper."""
        if hasattr(self, "conversation"):
            self.conversation.add_system_message(message)

    async def handle_command(self, command: str) -> bool:
        """Handle slash commands.

        Returns True if the command was handled locally, False to allow higher-level
        handlers (e.g., REPL runner) to process it.
        """
        cmd = command.lower().split()[0]

        if cmd == "/help":
            self.conversation.add_system_message("Available commands:")
            self.conversation.add_system_message("  /help - Show this help")
            self.conversation.add_system_message("  /clear - Clear conversation")
            self.conversation.add_system_message("  /demo - Show demo messages")
            self.conversation.add_system_message(
                "  /scroll - Generate many messages (test scrolling)"
            )
            self.conversation.add_system_message("  /quit - Exit application")
            self.conversation.add_system_message("")
            self.conversation.add_system_message("✨ Multi-line Input:")
            self.conversation.add_system_message("  Enter - Send message")
            self.conversation.add_system_message("  Shift+Enter - New line in message")
            self.conversation.add_system_message("  Type multiple lines, then press Enter to send!")
            self.conversation.add_system_message("")
            self.conversation.add_system_message("📜 Scrolling:")
            self.conversation.add_system_message(
                "  Ctrl+Up - Focus conversation (then use arrow keys)"
            )
            self.conversation.add_system_message("  Ctrl+Down - Focus input (for typing)")
            self.conversation.add_system_message("  Arrow Up/Down - Scroll line by line")
            self.conversation.add_system_message("  Page Up/Down - Scroll by page")
            self.conversation.add_system_message("")
            self.conversation.add_system_message("⌨️  Other Shortcuts:")
            self.conversation.add_system_message("  Ctrl+L - Clear conversation")
            self.conversation.add_system_message("  Ctrl+C - Quit application")
            self.conversation.add_system_message("  ESC - Interrupt processing")
            return True

        elif cmd == "/clear":
            self.conversation.clear()
            self.conversation.add_system_message("Conversation cleared.")
            return True

        elif cmd == "/demo":
            # Demonstrate different message types
            self.conversation.add_assistant_message("Here's a demo of different message types:")
            self.conversation.add_system_message("")

            # Tool call example
            self.conversation.add_tool_call("Shell", "command='ls -la'")
            self.conversation.add_tool_result(
                "total 64\ndrwxr-xr-x  10 user  staff   320 Jan 27 10:00 ."
            )

            self.conversation.add_system_message("")
            self.conversation.add_tool_call("Read", "file_path='swecli/cli.py'")
            self.conversation.add_tool_result("File read successfully (250 lines)")

            self.conversation.add_system_message("")
            self.conversation.add_tool_call("Write", "file_path='test.py', content='...'")
            self.conversation.add_tool_result("File written successfully")

            self.conversation.add_system_message("")
            self.conversation.add_error("Example error: File not found")
            return True

        elif cmd == "/models":
            await self._start_model_picker()
            return True

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
                    self.conversation.add_assistant_message(
                        f"Test assistant message {i}: Lorem ipsum dolor sit amet, consectetur adipiscing elit."
                    )
            self.conversation.add_system_message("")
            self.conversation.add_assistant_message(
                "✓ Done! Try scrolling up with mouse wheel or Page Up."
            )
            return True

        elif cmd == "/quit":
            self.exit()
            return True

        else:
            if not self.on_message:
                self.conversation.add_error(f"Unknown command: {cmd}")
            return False

        return True

    async def _start_model_picker(self) -> None:
        """Launch the in-conversation model picker flow."""
        await self._model_picker.start()

    def _model_picker_move(self, delta: int) -> None:
        self._model_picker.move(delta)

    def _model_picker_back(self) -> None:
        self._model_picker.back()

    def _model_picker_cancel(self) -> None:
        self._model_picker.cancel()

    async def _model_picker_confirm(self) -> None:
        await self._model_picker.confirm()

    async def _handle_model_picker_input(self, raw_value: str) -> bool:
        return await self._model_picker.handle_input(raw_value)

    async def show_approval_modal(self, command: str, working_dir: str) -> tuple[bool, str, str]:
        """Display an inline approval prompt inside the conversation log."""
        return await self._approval_controller.start(command, working_dir)

    def _render_approval_prompt(self) -> None:
        self._approval_controller.render()

    def _approval_move(self, delta: int) -> None:
        self._approval_controller.move(delta)

    def _approval_confirm(self) -> None:
        self._approval_controller.confirm()

    def _approval_cancel(self) -> None:
        self._approval_controller.cancel()

    async def process_message(self, message: str) -> None:
        """Send the user message to the backend for processing."""

        if not self.on_message:
            self.conversation.add_error("No backend handler configured; unable to process message.")
            return

        self._set_processing_state(True)

        try:
            self.on_message(message)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.notify_processing_error(f"Failed to submit message: {exc}")

    def _set_processing_state(self, active: bool) -> None:
        """Update internal processing state and status bar indicator."""

        if active == self._is_processing:
            return

        self._is_processing = active

        if not hasattr(self, "status_bar"):
            return

        if active:
            self._start_local_spinner()
        else:
            self._stop_local_spinner()

    def notify_processing_complete(self) -> None:
        """Reset processing indicators once backend work completes."""

        def finalize() -> None:
            self._set_processing_state(False)
            self._emit_tool_follow_up_if_needed()

        self._invoke_on_ui_thread(finalize)

    def notify_processing_error(self, error: str) -> None:
        """Display an error message and reset processing indicators."""

        def finalize() -> None:
            self.conversation.add_error(error)
            self._set_processing_state(False)
            self._reset_interaction_state()

        self._invoke_on_ui_thread(finalize)

    def action_clear_conversation(self) -> None:
        """Clear the conversation (Ctrl+L)."""
        self.conversation.clear()
        self.conversation.add_system_message("Conversation cleared (Ctrl+L)")

    def action_interrupt(self) -> None:
        """Interrupt processing (ESC)."""
        if self._is_processing:
            self.conversation.add_system_message("⚠ Processing interrupted")
            self._set_processing_state(False)

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
        self.conversation.add_system_message(
            "📜 Conversation focused - use arrow keys or trackpad to scroll"
        )

    def action_focus_input(self) -> None:
        """Focus the input field for typing (Ctrl+Down)."""
        self.input_field.focus()

    def action_history_up(self) -> None:
        """Navigate backward through previously submitted messages."""

        if not self._message_history:
            return

        if self._history_index == -1:
            self._current_input = self.input_field.text

        if self._history_index < len(self._message_history) - 1:
            self._history_index += 1

        history_entry = self._message_history[-(self._history_index + 1)]
        self.input_field.load_text(history_entry)
        self.input_field.move_cursor_to_end()

    def action_history_down(self) -> None:
        """Navigate forward through history or restore unsent input."""

        if self._history_index == -1:
            return

        if self._history_index > 0:
            self._history_index -= 1
            history_entry = self._message_history[-(self._history_index + 1)]
            self.input_field.load_text(history_entry)
            self.input_field.move_cursor_to_end()
            return

        self._history_index = -1
        self.input_field.load_text(self._current_input)
        self.input_field.move_cursor_to_end()

    def action_cycle_mode(self) -> None:
        """Cycle between PLAN and NORMAL modes (Shift+Tab)."""

        if not self.on_cycle_mode:
            return

        try:
            new_mode = self.on_cycle_mode()
        except Exception:  # pragma: no cover - defensive
            return

        if not new_mode:
            return

        mode_label = new_mode.lower()
        self.status_bar.set_mode(mode_label)


def create_chat_app(
    on_message: Optional[Callable[[str], None]] = None,
    model: str = "claude-sonnet-4",
    model_slots: Mapping[str, tuple[str, str]] | None = None,
    on_cycle_mode: Optional[Callable[[], str]] = None,
    completer: Optional[Completer] = None,
    on_model_selected: Optional[Callable[[str, str, str], Any]] = None,
    get_model_config: Optional[Callable[[], Mapping[str, Any]]] = None,
) -> SWECLIChatApp:
    """Create and return a new chat application instance.

    Args:
        on_message: Optional callback for message processing
        model: Model name to display in status bar
        model_slots: Mapping of model slots to formatted provider/model names
        completer: Autocomplete provider for @ mentions and slash commands
        on_model_selected: Callback invoked after a model is selected
        get_model_config: Callback returning current model configuration details

    Returns:
        Configured SWECLIChatApp instance
    """
    return SWECLIChatApp(
        on_message=on_message,
        model=model,
        model_slots=model_slots,
        on_cycle_mode=on_cycle_mode,
        completer=completer,
        on_model_selected=on_model_selected,
        get_model_config=get_model_config,
    )


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
