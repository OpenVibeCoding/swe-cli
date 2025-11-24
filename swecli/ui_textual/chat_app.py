"""Textual-based chat application for SWE-CLI - POC."""

import threading
from typing import Any, Callable, Mapping, Optional

from prompt_toolkit.completion import Completer

from rich.console import RenderableType
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Header, Rule, Static

from swecli.ui_textual.widgets import ConversationLog
from swecli.ui_textual.widgets.chat_text_area import ChatTextArea
from swecli.ui_textual.widgets.status_bar import ModelFooter, StatusBar
from swecli.ui_textual.widgets.todo_panel import TodoPanel
from swecli.ui_textual.components import TipsManager
from swecli.ui_textual.controllers.approval_prompt_controller import ApprovalPromptController
from swecli.ui_textual.controllers.autocomplete_popup_controller import AutocompletePopupController
from swecli.ui_textual.controllers.command_router import CommandRouter
from swecli.ui_textual.controllers.message_controller import MessageController
from swecli.ui_textual.controllers.model_picker_controller import ModelPickerController
from swecli.ui_textual.controllers.spinner_controller import SpinnerController
from swecli.ui_textual.managers.console_buffer_manager import ConsoleBufferManager
from swecli.ui_textual.managers.message_history import MessageHistory
from swecli.ui_textual.managers.tool_summary_manager import ToolSummaryManager
from swecli.ui_textual.renderers.welcome_panel import render_welcome_panel
from swecli.ui_textual import style_tokens



class SWECLIChatApp(App):
    """SWE-CLI Chat Application using Textual."""

    CSS_PATH = "styles/chat.tcss"
    INPUT_LABEL_DEFAULT = "› Type your message (Enter to send, Shift+Enter for new line):"
    INPUT_LABEL_EXIT = "Press Ctrl + C again to exit"

    # Disable mouse support to allow natural terminal text selection
    ENABLE_MOUSE = False

    BINDINGS = [
        Binding("ctrl+c", "quit", "", show=False, priority=True),
        Binding("ctrl+l", "clear_conversation", "", show=False),
        Binding("ctrl+t", "toggle_todo_panel", "Toggle Todos", show=False),
        Binding("escape", "interrupt", "", show=False),
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
        on_ready: Optional[Callable[[], None]] = None,
        on_interrupt: Optional[Callable[[], bool]] = None,
        working_dir: Optional[str] = None,
        todo_handler=None,
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
            on_ready: Callback invoked once the UI finishes its first layout pass
            on_interrupt: Callback for when user presses ESC to interrupt
            working_dir: Working directory path for repo display
        """
        # Set color system to inherit from terminal
        kwargs.setdefault("ansi_color", "auto")
        super().__init__(**kwargs)
        self.on_message = on_message
        self.on_cycle_mode = on_cycle_mode
        self.on_interrupt = on_interrupt
        self.model = model
        self.completer = completer
        self.model_slots = dict(model_slots or {})
        self.on_model_selected = on_model_selected
        self.get_model_config = get_model_config
        self._on_ready = on_ready
        self.working_dir = working_dir or ""
        self.todo_handler = todo_handler
        self.autocomplete_popup: Static | None = None
        self._autocomplete_controller: AutocompletePopupController | None = None
        self.footer: ModelFooter | None = None
        self._is_processing = False
        self._last_assistant_lines: set[str] = set()
        self._last_rendered_assistant: str | None = None
        self._last_assistant_normalized: str | None = None
        self._buffer_console_output = False
        self._pending_assistant_normalized: str | None = None
        self._ui_thread: threading.Thread | None = None
        self._tips_manager = TipsManager()
        self._model_picker: ModelPickerController = ModelPickerController(self)
        self._approval_controller = ApprovalPromptController(self)
        self._spinner = SpinnerController(self, self._tips_manager)
        self._console_buffer = ConsoleBufferManager(self)
        self._queued_console_renderables = self._console_buffer._queue
        self._tool_summary = ToolSummaryManager(self)
        self._command_router = CommandRouter(self)
        self._history = MessageHistory()
        self._message_controller = MessageController(self)
        self._quit_armed = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # Conversation area
            yield ConversationLog(id="conversation")

            # Separator line between conversation and input
            yield Rule(line_style="solid")

            # Todo panel (persistent, toggleable with Ctrl+T)
            yield TodoPanel(todo_handler=self.todo_handler, id="todo-panel")

            # Input area
            with Vertical(id="input-container"):
                yield Static(
                    self.INPUT_LABEL_DEFAULT,
                    id="input-label",
                )
                yield ChatTextArea(
                    id="input",
                    placeholder="Type your message...",
                    soft_wrap=True,
                    completer=self.completer,
                )

            # Status bar
            yield StatusBar(model=self.model, working_dir=self.working_dir, id="status-bar")

        yield ModelFooter(self.model_slots, normal_model=self.model, id="model-footer")

    def on_mount(self) -> None:
        """Initialize the app on mount."""

        self._ui_thread = threading.current_thread()

        # Get widgets
        self.conversation = self.query_one("#conversation", ConversationLog)
        self.input_field = self.query_one("#input", ChatTextArea)
        input_container = self.query_one("#input-container")
        self.status_bar = self.query_one("#status-bar", StatusBar)
        self.footer = self.query_one("#model-footer", ModelFooter)
        self.input_label = self.query_one("#input-label", Static)
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
        else:
            self.title = "SWE-CLI Chat (Textual POC)"
            self.sub_title = "Full-screen terminal interface"
            render_welcome_panel(self.conversation, real_integration=False)

        if self._on_ready is not None:
            self.call_after_refresh(self._on_ready)

    def update_model_slots(self, model_slots: Mapping[str, tuple[str, str]] | None) -> None:
        """Update footer model display with new slot information."""
        self.model_slots = dict(model_slots or {})
        if self.footer is not None:
            self.footer.update_models(self.model_slots)

    def update_primary_model(self, model: str) -> None:
        """Update the primary model label shown in the status bar and footer."""
        self.model = model
        if hasattr(self, "status_bar"):
            self.status_bar.set_model_name(model)
        # Also update the footer to show the normal model
        if hasattr(self, "footer"):
            self.footer.set_normal_model(model)


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

    def _show_interrupt_message_immediately(self) -> None:
        """Show interrupt message IMMEDIATELY in the UI without any delays.

        This provides instant visual feedback when ESC is pressed, even if
        the actual process termination takes time in the background.
        """
        # Stop spinner immediately
        if hasattr(self, '_spinner'):
            self._spinner.stop()

        # Stop any local spinners
        self._stop_local_spinner()

        # Stop conversation spinner if it exists
        if hasattr(self.conversation, 'stop_spinner'):
            self.conversation.stop_spinner()

        # Immediately display the interrupt message using the shared utility
        from swecli.ui_textual.utils.interrupt_utils import create_interrupt_text, THINKING_INTERRUPT_MESSAGE
        from rich.text import Text

        # Remove blank line if present (same logic as ui_callback.py on_interrupt)
        if hasattr(self.conversation, 'lines') and len(self.conversation.lines) > 0:
            last_line = self.conversation.lines[-1]
            is_blank = False

            # Check if it's a Strip object with empty content
            if hasattr(last_line, '_segments'):
                segments = last_line._segments
                if len(segments) == 0:
                    is_blank = True
                elif len(segments) == 1 and segments[0].text == '':
                    is_blank = True
            elif hasattr(last_line, 'plain'):
                # Fallback for Text objects
                if last_line.plain.strip() == "":
                    is_blank = True

            if is_blank and hasattr(self.conversation, '_truncate_from'):
                self.conversation._truncate_from(len(self.conversation.lines) - 1)

        # Write interrupt message
        interrupt_line = create_interrupt_text(THINKING_INTERRUPT_MESSAGE)
        self.conversation.write(interrupt_line)

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
        if hasattr(self, "_tool_summary"):
            self._tool_summary.on_assistant_message(message)

    async def action_send_message(self) -> None:
        """Send message when user presses Enter."""
        await self._message_controller.submit(self.input_field.text)

    async def on_chat_text_area_submitted(self, event: ChatTextArea.Submitted) -> None:
        """Handle chat submissions from the custom text area."""
        self._handle_input_activity()
        await self._message_controller.submit(event.value)

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
        handled = await self._command_router.handle(command)
        if not handled and not self.on_message:
            cmd = command.lower().split()[0]
            self.conversation.add_error(
                f"Unknown command: {cmd}",
                hint=style_tokens.UNKNOWN_COMMAND_HINT,
            )
        return handled

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
        await self._message_controller.process(message)

    def _set_processing_state(self, active: bool) -> None:
        """Update internal processing state and status bar indicator."""
        self._message_controller.set_processing_state(active)

    def record_tool_summary(
        self, tool_name: str, tool_args: dict[str, Any], result_lines: list[str]
    ) -> None:
        """Record a tool result summary for fallback assistant messaging."""
        if hasattr(self, "_tool_summary"):
            self._tool_summary.record_summary(tool_name, tool_args, result_lines)

    def _emit_tool_follow_up_if_needed(self) -> None:
        """Render a fallback assistant follow-up if tools finished without LLM wrap-up."""
        if hasattr(self, "_tool_summary"):
            self._tool_summary.emit_follow_up_if_needed()

    @property
    def _pending_tool_summaries(self) -> list[str]:
        if hasattr(self, "_tool_summary"):
            return self._tool_summary._pending
        return []

    @_pending_tool_summaries.setter
    def _pending_tool_summaries(self, value: list[str]) -> None:
        if hasattr(self, "_tool_summary"):
            self._tool_summary._pending = list(value)

    @property
    def _assistant_response_received(self) -> bool:
        if hasattr(self, "_tool_summary"):
            return self._tool_summary._assistant_response_received
        return False

    @_assistant_response_received.setter
    def _assistant_response_received(self, value: bool) -> None:
        if hasattr(self, "_tool_summary"):
            self._tool_summary._assistant_response_received = value

    @property
    def _saw_tool_result(self) -> bool:
        if hasattr(self, "_tool_summary"):
            return self._tool_summary._saw_tool_result
        return False

    @_saw_tool_result.setter
    def _saw_tool_result(self, value: bool) -> None:
        if hasattr(self, "_tool_summary"):
            self._tool_summary._saw_tool_result = value

    def notify_processing_complete(self) -> None:
        """Reset processing indicators once backend work completes."""
        self._message_controller.notify_processing_complete()

    def notify_processing_error(self, error: str) -> None:
        """Display an error message and reset processing indicators."""
        self._message_controller.notify_processing_error(error)

    def action_clear_conversation(self) -> None:
        """Clear the conversation (Ctrl+L)."""
        self.conversation.clear()
        self.conversation.add_system_message("Conversation cleared (Ctrl+L)")

    def action_interrupt(self) -> None:
        """Interrupt processing (ESC) - shows message IMMEDIATELY, then interrupts in background."""
        if self._is_processing:
            # STEP 1: Show interrupt message IMMEDIATELY for instant visual feedback
            self._show_interrupt_message_immediately()

            # STEP 2: Trigger actual interrupt handling in background (non-blocking)
            if self.on_interrupt:
                # Run interrupt in background thread so UI stays responsive
                import threading
                interrupt_thread = threading.Thread(
                    target=self.on_interrupt,
                    daemon=True,
                    name="interrupt-handler"
                )
                interrupt_thread.start()

    def action_quit(self) -> None:
        """Require a double Ctrl+C to exit; first press clears and arms the prompt."""
        if self._quit_armed:
            self.exit()
            return

        self._quit_armed = True
        self._set_input_label(self.INPUT_LABEL_EXIT)
        self.input_field.load_text("")
        self.input_field.clear_large_pastes()
        self.input_field.focus()

    def action_scroll_up(self) -> None:
        """Scroll conversation up (Page Up)."""
        if hasattr(self.conversation, "scroll_partial_page"):
            self.conversation.scroll_partial_page(direction=-1)
        else:
            self.conversation.scroll_page_up()

    def action_scroll_down(self) -> None:
        """Scroll conversation down (Page Down)."""
        if hasattr(self.conversation, "scroll_partial_page"):
            self.conversation.scroll_partial_page(direction=1)
        else:
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

        if not hasattr(self, '_history'):
            return

        result = self._history.navigate_up(self.input_field.text)
        if result is None:
            return

        self.input_field.load_text(result)
        self.input_field.move_cursor_to_end()


    def action_history_down(self) -> None:
        """Navigate forward through history or restore unsent input."""

        if not hasattr(self, '_history'):
            return

        result = self._history.navigate_down()
        if result is None:
            return

        self.input_field.load_text(result)
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

    def action_toggle_todo_panel(self) -> None:
        """Toggle todo panel between collapsed and expanded (Ctrl+T)."""
        try:
            panel = self.query_one("#todo-panel", TodoPanel)

            # If panel is hidden (no todos), do nothing
            if not panel.has_class("collapsed") and not panel.has_class("expanded"):
                return

            # Toggle between collapsed and expanded
            panel.toggle_expansion()

        except Exception:  # pragma: no cover - defensive
            pass

    def _set_input_label(self, text: str) -> None:
        """Update the helper label above the input field."""
        if hasattr(self, "input_label"):
            self.input_label.update(text)

    def _handle_input_activity(self) -> None:
        """Reset the quit prompt if the user resumes typing."""
        if self._quit_armed:
            self._quit_armed = False
            self._set_input_label(self.INPUT_LABEL_DEFAULT)


def create_chat_app(
    on_message: Optional[Callable[[str], None]] = None,
    model: str = "claude-sonnet-4",
    model_slots: Mapping[str, tuple[str, str]] | None = None,
    on_cycle_mode: Optional[Callable[[], str]] = None,
    completer: Optional[Completer] = None,
    on_model_selected: Optional[Callable[[str, str, str], Any]] = None,
    get_model_config: Optional[Callable[[], Mapping[str, Any]]] = None,
    on_ready: Optional[Callable[[], None]] = None,
    on_interrupt: Optional[Callable[[], bool]] = None,
    working_dir: Optional[str] = None,
    todo_handler=None,
) -> SWECLIChatApp:
    """Create and return a new chat application instance.

    Args:
        on_message: Optional callback for message processing
        model: Model name to display in status bar
        model_slots: Mapping of model slots to formatted provider/model names
        completer: Autocomplete provider for @ mentions and slash commands
        on_model_selected: Callback invoked after a model is selected
        get_model_config: Callback returning current model configuration details
        on_ready: Callback invoked once the UI completes its first render pass
        on_interrupt: Callback for when user presses ESC to interrupt
        working_dir: Working directory path for repo display

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
        on_ready=on_ready,
        on_interrupt=on_interrupt,
        working_dir=working_dir,
        todo_handler=todo_handler,
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
