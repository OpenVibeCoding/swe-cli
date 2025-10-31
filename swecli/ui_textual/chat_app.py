"""Textual-based chat application for SWE-CLI - POC."""

from dataclasses import dataclass
import random
import re
import time
from typing import Callable, Optional

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.events import Key, Paste
from textual.geometry import Size
from textual.message import Message
from textual.timer import Timer
from textual.widgets import Footer, Header, RichLog, Static, TextArea

from swecli.ui_textual.approval_modal import ApprovalModal


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
        self._last_assistant_rendered: str | None = None
        self._spinner_start: int | None = None
        self._spinner_line_count = 0

    def add_user_message(self, message: str) -> None:
        """Add user message to conversation."""
        self.write(Text(f"› {message}", style="bold cyan"))

    def add_assistant_message(self, message: str) -> None:
        """Add assistant message with lightweight markdown and code support."""

        normalized = self._normalize_text(message)
        if normalized and normalized == self._last_assistant_rendered:
            return

        self._last_assistant_rendered = normalized

        segments = self._split_code_blocks(message)
        for index, segment in enumerate(segments):
            if segment["type"] == "code":
                code = segment["content"].strip("\n")
                if not code:
                    continue
                language = segment.get("language") or "text"
                syntax = Syntax(code, language, theme="monokai", line_numbers=bool(code.count("\n") > 0))
                title = f"Code ({language})" if language and language != "text" else "Code"
                panel = Panel(syntax, title=title, border_style="bright_blue")
                self.write(panel)
            else:
                content = segment["content"].strip()
                if not content:
                    continue
                # Only prefix first paragraph with bullet; subsequent lines keep indentation
                clean_segments = content.splitlines()
                if index == 0 and clean_segments:
                    first, *rest = clean_segments
                    bullet_line = f"⏺ {first.strip()}"
                    self.write(Text(bullet_line, style="white"))
                    for line in rest:
                        self.write(Text(line.rstrip()))
                else:
                    if self._looks_like_markdown(content):
                        self.write(Markdown(content, code_theme="monokai"))
                    else:
                        for line in clean_segments or [content]:
                            self.write(Text(line.rstrip()))

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
        self.stop_spinner()

    def start_spinner(self, message: str) -> None:
        """Append spinner message at the end of the log."""

        self._spinner_start = len(self.lines)
        self._append_spinner(message)

    def update_spinner(self, message: str) -> None:
        """Update the spinner message without growing the log."""

        if self._spinner_start is None:
            self.start_spinner(message)
            return

        self._remove_spinner_lines(preserve_index=True)
        self._append_spinner(message)

    def stop_spinner(self) -> None:
        """Remove the spinner message entirely."""

        if self._spinner_start is None:
            return

        self._remove_spinner_lines(preserve_index=False)
        self._spinner_start = None
        self._spinner_line_count = 0

    def _append_spinner(self, message: str) -> None:
        text = Text(message, style="bright_cyan")
        self.write(text, scroll_end=True, animate=False)
        if self._spinner_start is not None:
            self._spinner_line_count = len(self.lines) - self._spinner_start

    def _remove_spinner_lines(self, *, preserve_index: bool) -> None:
        if self._spinner_start is None:
            return

        start = min(self._spinner_start, len(self.lines))
        if start < len(self.lines):
            del self.lines[start:]
            self._line_cache.clear()
            widths: list[int] = []
            for strip in self.lines:
                cell_length = getattr(strip, "cell_length", None)
                widths.append(cell_length() if callable(cell_length) else cell_length or 0)
            self._widest_line_width = max(widths, default=0)
            self._start_line = max(0, min(self._start_line, len(self.lines)))
            self.virtual_size = Size(self._widest_line_width, len(self.lines))
            if self.auto_scroll:
                self.scroll_end(animate=False)
            self.refresh()

        if preserve_index:
            self._spinner_line_count = 0
        else:
            self._spinner_start = None
            self._spinner_line_count = 0

    def _looks_like_markdown(self, content: str) -> bool:
        """Heuristic to decide if content should use Markdown rendering."""

        markdown_patterns = (
            r"\*\*.+\*\*",
            r"_.+_",
            r"^\s*[-*+]\s+",
            r"^\s*\d+\.\s+",
            r"`.+?`",
        )
        return any(re.search(pattern, content, flags=re.MULTILINE) for pattern in markdown_patterns)

    def _split_code_blocks(self, message: str) -> list[dict[str, str]]:
        """Split message into text and fenced code segments."""

        pattern = re.compile(r"```(\w+)?\n?(.*?)```", re.DOTALL)
        segments: list[dict[str, str]] = []
        last_end = 0

        for match in pattern.finditer(message):
            start, end = match.span()
            if start > last_end:
                segments.append({"type": "text", "content": message[last_end:start]})

            language = match.group(1) or ""
            code = match.group(2) or ""
            segments.append({"type": "code", "language": language, "content": code})
            last_end = end

        if last_end < len(message):
            segments.append({"type": "text", "content": message[last_end:]})

        if not segments:
            segments.append({"type": "text", "content": message})

        return segments

    @staticmethod
    def _normalize_text(message: str) -> str:
        cleaned = re.sub(r"\x1b\[[0-9;]*m", "", message)
        cleaned = cleaned.replace("⏺", " ")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()






class ChatTextArea(TextArea):
    """Multi-line text area that sends on Enter and inserts newline on Shift+Enter."""

    def __init__(self, *args, paste_threshold: int = 200, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._paste_threshold = paste_threshold
        self._paste_counter = 0
        self._large_paste_cache: dict[str, str] = {}

    @dataclass
    class Submitted(Message):
        """Message emitted when the user submits the chat input."""

        text_area: "ChatTextArea"
        value: str

        @property
        def control(self) -> "ChatTextArea":
            """Compatibility alias matching Textual input events."""
            return self.text_area

    async def _on_key(self, event: Key) -> None:
        """Intercept Enter to submit while preserving Shift+Enter for new lines."""

        if self._should_insert_newline(event):
            event.stop()
            event.prevent_default()
            self._insert_newline()
            return

        if event.key == "up":
            event.stop()
            event.prevent_default()
            if hasattr(self.app, "action_history_up"):
                self.app.action_history_up()
            return

        if event.key == "down":
            event.stop()
            event.prevent_default()
            if hasattr(self.app, "action_history_down"):
                self.app.action_history_down()
            return

        if event.key in {"enter", "return"} and "+" not in event.key:
            event.stop()
            event.prevent_default()
            self.post_message(self.Submitted(self, self.text))
            return

        await super()._on_key(event)

    def on_paste(self, event: Paste) -> None:
        """Handle paste events, collapsing large blocks into placeholders."""

        paste_text = event.text
        event.stop()

        if len(paste_text) > self._paste_threshold:
            token = self._register_large_paste(paste_text)
            self._replace_via_keyboard(token, *self.selection)
            return

        self._replace_via_keyboard(paste_text, *self.selection)

    @staticmethod
    def _should_insert_newline(event: Key) -> bool:
        """Return True if the key event should produce a newline."""

        newline_keys = {
            "shift+enter",
            "ctrl+j",
            "ctrl+shift+enter",
            "newline",
        }

        if event.key in newline_keys:
            return True

        if any(alias in newline_keys for alias in event.aliases):
            return True

        return event.character == "\n"

    def _insert_newline(self) -> None:
        """Insert a newline at the current cursor position, preserving selection."""

        start, end = self.selection
        self._replace_via_keyboard("\n", start, end)

    def resolve_large_pastes(self, text: str) -> str:
        """Expand placeholder tokens back to the original pasted content."""

        for token, content in self._large_paste_cache.items():
            text = text.replace(token, content)
        return text

    def clear_large_pastes(self) -> None:
        """Clear cached large paste payloads after submission."""

        self._large_paste_cache.clear()

    def _register_large_paste(self, content: str) -> str:
        """Store large paste content and return the placeholder token."""

        self._paste_counter += 1
        token = f"[[PASTE-{self._paste_counter}:{len(content)} chars]]"
        self._large_paste_cache[token] = content
        return token

    def move_cursor_to_end(self) -> None:
        """Position the cursor at the end of the current text content."""

        if not self.text:
            self.cursor_location = (0, 0)
            return

        lines = self.text.split("\n")
        if self.text.endswith("\n"):
            row = len(lines)
            column = 0
        else:
            row = len(lines) - 1
            column = len(lines[-1])

        self.cursor_location = (row, column)


class StatusBar(Static):
    """Custom status bar showing mode, context, and hints."""

    def __init__(self, model: str = "claude-sonnet-4", **kwargs):
        super().__init__(**kwargs)
        self.mode = "normal"
        self.context_pct = 0
        self.model = model
        self.spinner_text: str | None = None
        self.spinner_tip: str | None = None

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

    def set_spinner(self, text: str, tip: str | None = None) -> None:
        """Display spinner status."""
        self.spinner_text = text
        if tip is not None:
            self.spinner_tip = tip
        self.update_status()

    def clear_spinner(self) -> None:
        """Clear spinner status."""
        self.spinner_text = None
        self.spinner_tip = None
        self.update_status()

    def update_status(self) -> None:
        """Update status bar text - clean and professional."""
        # Simple, elegant colors (no emojis, no bright colors)
        mode_color = "#4a9eff" if self.mode == "normal" else "#89d185"
        status = Text()

        # Mode indicator (uppercase for clarity)
        status.append(f"{self.mode.upper()}", style=f"bold {mode_color}")
        status.append("  │  ", style="#6a6a6a")  # Pipe separator

        # Context percentage
        status.append(f"Context {self.context_pct}%", style="#808080")
        status.append("  │  ", style="#6a6a6a")

        # Model (truncate if too long)
        model_display = self.model if len(self.model) < 40 else self.model[:37] + "..."
        status.append(model_display, style="#007acc")

        # Spinner status (if active)
        if self.spinner_text:
            status.append("  │  ", style="#6a6a6a")
            status.append(self.spinner_text, style="#4a9eff")
            if self.spinner_tip:
                status.append(" ", style="dim")
                status.append(self.spinner_tip, style="#6a6a6a")

        # Exit hint
        status.append("  │  ", style="#6a6a6a")
        status.append("^C quit", style="#6a6a6a")

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
        border: none;                /* Clean, borderless design */
        background: $surface;
        padding: 1 2;                /* More generous padding */
        overflow-y: scroll;
    }

    #input-container {
        height: auto;
        layout: vertical;
    }

    #input-label {
        height: 1;
        content-align: left middle;
        color: $text-muted;          /* Subtle label */
        background: $surface;
        padding: 0 2;
    }

    #input {
        height: 5;
        max-height: 15;
        min-height: 3;
        border: none;                /* No border by default */
        background: $surface;
        padding: 1 2;
    }

    #status-bar {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 2;
        content-align: left middle;
    }

    TextArea {
        background: $surface;
        color: $text;
        border: none;
    }

    TextArea:focus {
        border-left: thick $accent;  /* Subtle left accent on focus */
        background: $surface-darken-1;
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
        model: str = "claude-sonnet-4",
        **kwargs,
    ):
        """Initialize chat application.

        Args:
            on_message: Callback for when user sends a message
            model: Model name to display in status bar
        """
        super().__init__(**kwargs)
        self.on_message = on_message
        self.model = model
        self._is_processing = False
        self._message_history = []
        self._history_index = -1
        self._current_input = ""
        self._status_mode_before_processing = "normal"
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_timer: Timer | None = None
        self._spinner_frame_index = 0
        self._spinner_message = "Thinking…"
        self._spinner_started_at = 0.0
        self._spinner_active = False
        self._queued_console_renderables: list[RenderableType] = []
        self._last_assistant_lines: set[str] = set()
        self._last_rendered_assistant: str | None = None
        self._last_assistant_normalized: str | None = None
        self._buffer_console_output = False
        self._pending_assistant_normalized: str | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # Conversation area
            yield ConversationLog(id="conversation")

            # Input area
            with Vertical(id="input-container"):
                yield Static("› Type your message (Enter to send, Shift+Enter for new line):", id="input-label")
                yield ChatTextArea(
                    id="input",
                    placeholder="Type your message...",
                    soft_wrap=True,
                )

            # Status bar
            yield StatusBar(model=self.model, id="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        self.title = "SWE-CLI Chat (Textual POC)"
        self.sub_title = "Full-screen terminal interface"

        # Get widgets
        self.conversation = self.query_one("#conversation", ConversationLog)
        self.input_field = self.query_one("#input", ChatTextArea)
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
            "Try typing a message (multi-line supported!). Press Enter to send."
        )
        self.conversation.add_assistant_message("  • /help - Show available commands")
        self.conversation.add_assistant_message("  • /scroll - Generate messages to test scrolling")
        self.conversation.add_assistant_message("  • /demo - Show message types")
        self.conversation.add_system_message("")
        self.conversation.add_system_message("✨ Multi-line input: Press Shift+Enter for new line, Enter to send")
        self.conversation.add_system_message("💡 Scrolling: Press Ctrl+Up to focus conversation, then use arrow keys")
        self.conversation.add_system_message("")

        # Simulate some context
        self.status_bar.set_context(15)

    def _start_local_spinner(self) -> None:
        """Begin local spinner animation while backend processes."""

        if self._spinner_timer is not None:
            return

        if not hasattr(self, "conversation") or not hasattr(self, "status_bar"):
            return

        if self._queued_console_renderables:
            self._queued_console_renderables.clear()

        self._spinner_message = self._get_spinner_message()
        self._spinner_frame_index = 0
        self._spinner_started_at = time.monotonic()
        self._spinner_active = True
        self._update_spinner_output(initial=True)
        self._spinner_timer = self.set_interval(0.12, self._update_spinner_frame)

    def _stop_local_spinner(self) -> None:
        """Stop spinner animation and clear indicators."""

        if self._spinner_timer is not None:
            self._spinner_timer.stop()
            self._spinner_timer = None

        if self._spinner_active and hasattr(self, "conversation"):
            self.conversation.stop_spinner()
        self._spinner_active = False
        self.status_bar.clear_spinner()
        self._spinner_started_at = 0.0
        self._last_rendered_assistant = None
        self._last_assistant_normalized = None

        self.flush_console_buffer()

    def _should_suppress_renderable(self, renderable: RenderableType) -> bool:
        """Return True if renderable duplicates the last assistant output."""

        if not self._last_assistant_lines:
            return False

        if isinstance(renderable, str):
            segments = [renderable]
        elif isinstance(renderable, Text):
            segments = [renderable.plain]
        elif hasattr(renderable, "render") and hasattr(self, "app"):
            try:
                console = self.app.console
                segments = [segment.text for segment in console.render(renderable) if getattr(segment, "text", "")]
            except Exception:  # pragma: no cover - defensive
                return False
        else:
            return False

        combined = " ".join(segments)
        normalized_combined = self._normalize_paragraph(combined)
        targets = [value for value in (self._pending_assistant_normalized, self._last_assistant_normalized) if value]
        if normalized_combined and targets:
            if any(normalized_combined == target for target in targets):
                return True

        normalized_segments = [self._normalize_assistant_line(seg) for seg in segments]
        normalized_segments = [seg for seg in normalized_segments if seg]
        if normalized_segments and self._last_assistant_lines and all(seg in self._last_assistant_lines for seg in normalized_segments):
            return True

        return False

    @staticmethod
    def _normalize_assistant_line(line: str) -> str:
        cleaned = re.sub(r"\x1b\[[0-9;]*m", "", line)
        cleaned = cleaned.strip()
        if not cleaned:
            return ""
        if cleaned.startswith("⏺"):
            cleaned = cleaned.lstrip("⏺").strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @staticmethod
    def _normalize_paragraph(text: str) -> str:
        cleaned = re.sub(r"\x1b\[[0-9;]*m", "", text)
        cleaned = cleaned.replace("⏺", " ")
        cleaned = cleaned.replace("\n", " ")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def flush_console_buffer(self) -> None:
        """Flush queued console renderables after assistant message is recorded."""

        if self._spinner_active or self._buffer_console_output:
            return

        if not self._queued_console_renderables:
            return

        for renderable in self._queued_console_renderables:
            if not self._should_suppress_renderable(renderable):
                self.conversation.write(renderable)
        self._queued_console_renderables.clear()

    def start_console_buffer(self) -> None:
        self._buffer_console_output = True

    def stop_console_buffer(self) -> None:
        self._buffer_console_output = False
        self.flush_console_buffer()

    def _update_spinner_frame(self) -> None:
        """Advance spinner frame."""

        self._spinner_frame_index = (self._spinner_frame_index + 1) % len(self._spinner_frames)
        self._update_spinner_output()

    def _update_spinner_output(self, *, initial: bool = False) -> None:
        """Render spinner frame to UI."""

        if not self._spinner_active:
            return

        if not hasattr(self, "status_bar") or not hasattr(self, "conversation"):
            return

        text = self._format_spinner_text()
        if initial:
            self.conversation.start_spinner(text)
        else:
            self.conversation.update_spinner(text)
        self.status_bar.set_spinner(text)

    def _get_spinner_message(self) -> str:
        """Return a human-friendly spinner message."""

        try:
            from swecli.repl.query_processor import QueryProcessor
            verb = random.choice(QueryProcessor.THINKING_VERBS)
        except Exception:
            verb = "Thinking"
        return f"{verb}…"

    def _format_spinner_text(self) -> str:
        """Create spinner text with elapsed time."""

        frame = self._spinner_frames[self._spinner_frame_index]
        elapsed = 0
        if self._spinner_started_at:
            elapsed = int(time.monotonic() - self._spinner_started_at)
        suffix = f" ({elapsed}s)" if elapsed else " (0s)"
        return f"{frame} {self._spinner_message}{suffix}"

    def record_assistant_message(self, message: str) -> None:
        """Track assistant lines to suppress duplicate console echoes."""

        lines = []
        for line in message.splitlines():
            normalized = self._normalize_assistant_line(line)
            if normalized:
                lines.append(normalized)
        if not lines:
            normalized = self._normalize_assistant_line(message)
            if normalized:
                lines.append(normalized)
        self._last_assistant_lines = set(lines)
        self._last_rendered_assistant = message.strip()
        self._last_assistant_normalized = self._normalize_paragraph(message)
        self._pending_assistant_normalized = None

    def render_console_output(self, renderable: RenderableType) -> None:
        """Render console output, buffering if spinner is active."""

        if self._spinner_active or self._buffer_console_output:
            self._queued_console_renderables.append(renderable)
            return

        if self._should_suppress_renderable(renderable):
            return

        self.conversation.write(renderable)

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

        # Clear input field in preparation for the next message
        self.input_field.load_text("")
        self._history_index = -1
        self._current_input = ""
        self.input_field.clear_large_pastes()

        # Add to history
        self._message_history.append(message)

        # Display user message
        self.conversation.add_user_message(message)

        stripped_message = message.strip()

        # Handle special commands (trimmed for robustness)
        if stripped_message.startswith("/"):
            handled = await self.handle_command(stripped_message)
            if not handled and self.on_message:
                self.on_message(message)
            return

        await self.process_message(message)

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
            self.conversation.add_system_message("  /scroll - Generate many messages (test scrolling)")
            self.conversation.add_system_message("  /quit - Exit application")
            self.conversation.add_system_message("")
            self.conversation.add_system_message("✨ Multi-line Input:")
            self.conversation.add_system_message("  Enter - Send message")
            self.conversation.add_system_message("  Shift+Enter - New line in message")
            self.conversation.add_system_message("  Type multiple lines, then press Enter to send!")
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
            return True

        elif cmd == "/clear":
            self.conversation.clear()
            self.conversation.add_system_message("Conversation cleared.")
            return True

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
            self.conversation.add_assistant_message("✓ Done! Try scrolling up with mouse wheel or Page Up.")
            return True

        elif cmd == "/quit":
            self.exit()
            return True

        else:
            if not self.on_message:
                self.conversation.add_error(f"Unknown command: {cmd}")
            return False

        return True

    async def show_approval_modal(self, command: str, working_dir: str) -> tuple[bool, str, str]:
        """Show approval dialog and return (approved, choice, edited_command)."""

        modal = ApprovalModal(command, working_dir)
        result = await self.app.push_screen_wait(modal)
        if result is None:
            return False, "3", command
        return result

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
            self._status_mode_before_processing = self.status_bar.mode
            self.status_bar.set_mode("processing")
            self._start_local_spinner()
        else:
            previous_mode = getattr(self, "_status_mode_before_processing", "normal")
            self.status_bar.set_mode(previous_mode or "normal")
            self._stop_local_spinner()

    def notify_processing_complete(self) -> None:
        """Reset processing indicators once backend work completes."""

        self._set_processing_state(False)

    def notify_processing_error(self, error: str) -> None:
        """Display an error message and reset processing indicators."""

        self.conversation.add_error(error)
        self._set_processing_state(False)

    def action_clear_conversation(self) -> None:
        """Clear the conversation (Ctrl+L)."""
        self.conversation.clear()
        self.conversation.add_system_message("Conversation cleared (Ctrl+L)")

    def action_interrupt(self) -> None:
        """Interrupt processing (ESC)."""
        if self._is_processing:
            self.conversation.add_system_message("⚠ Processing interrupted")
            self._set_processing_state(False)
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


def create_chat_app(
    on_message: Optional[Callable[[str], None]] = None,
    model: str = "claude-sonnet-4"
) -> SWECLIChatApp:
    """Create and return a new chat application instance.

    Args:
        on_message: Optional callback for message processing
        model: Model name to display in status bar

    Returns:
        Configured SWECLIChatApp instance
    """
    return SWECLIChatApp(on_message=on_message, model=model)


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
