"""Textual-based chat application for SWE-CLI - POC."""

import asyncio
import inspect
import random
import re
import time
import threading
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from prompt_toolkit.completion import Completer
from prompt_toolkit.document import Document as PTDocument

from rich import box
from rich.console import Group, RenderableType
from rich.align import Align
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.events import Key, Paste
from textual.geometry import Size
from textual.message import Message
from textual.timer import Timer
from textual.widgets import Footer, Header, RichLog, Rule, Static, TextArea

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
        self._tool_spinner_timer: Timer | None = None
        self._tool_name = None
        self._tool_args = None
        self._spinner_active = False
        self._spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_index = 0
        self._tool_call_start: int | None = None
        self._approval_start: int | None = None

    def on_mount(self) -> None:
        """Placeholder to mirror base method (timer created lazily)."""
        return

    def on_unmount(self) -> None:
        """Dispose of the spinner timer when the widget is removed."""
        if self._tool_spinner_timer is not None:
            self._tool_spinner_timer.stop()
            self._tool_spinner_timer = None

    def add_user_message(self, message: str) -> None:
        """Add user message to conversation."""
        self.write(Text(f"› {message}", style="bold white"))
        self.write(Text(""))  # Add spacing after user message

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
                syntax = Syntax(
                    code, language, theme="monokai", line_numbers=bool(code.count("\n") > 0)
                )
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

        # Add spacing after assistant message
        self.write(Text(""))

    def add_system_message(self, message: str) -> None:
        """Add system message to conversation."""
        self.write(Text(message, style="dim italic"))

    def add_tool_call(self, tool_name: str, args: str) -> None:
        """Add tool call to conversation."""
        self._tool_name = tool_name
        self._tool_args = args

        # Store the starting index (like thinking spinner does)
        self._tool_call_start = len(self.lines)

        # Write initial line with ⏺
        self._write_tool_call_line("⏺")

    def start_tool_execution(self) -> None:
        """Start animating the spinner on the tool call line."""

        if self._tool_name is None:
            return

        self._spinner_active = True
        self._spinner_index = 0
        self._render_tool_spinner_frame()
        self._schedule_tool_spinner()

    def stop_tool_execution(self) -> None:
        """Stop spinner and restore ⏺."""
        self._spinner_active = False

        # Restore the ⏺ by updating the line directly
        if (
            self._tool_call_start is not None
            and self._tool_name
            and self._tool_call_start < len(self.lines)
        ):
            from rich.segment import Segment
            from rich.style import Style
            from textual.strip import Strip

            segments = [
                Segment("⏺ ", Style(color="green")),
                Segment(self._tool_name, Style(color="bright_cyan", bold=True)),
                Segment(f"({self._tool_args})", Style(color="bright_cyan")),
            ]
            self.lines[self._tool_call_start] = Strip(segments)
            self.refresh_lines(self._tool_call_start, 1)

        self._tool_name = None
        self._tool_args = None
        self._tool_call_start = None
        self._spinner_index = 0
        if self._tool_spinner_timer is not None:
            self._tool_spinner_timer.stop()
            self._tool_spinner_timer = None

    def _animate_tool_spinner(self) -> None:
        """Update spinner character - runs on UI thread via timer."""
        if not self._spinner_active or self._tool_name is None or self._tool_call_start is None:
            return

        self._render_tool_spinner_frame()
        # Move to next spinner frame
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
        self._schedule_tool_spinner()

    def _schedule_tool_spinner(self) -> None:
        """Schedule the next spinner frame if still active."""
        if not self._spinner_active:
            return
        if self._tool_spinner_timer is not None:
            self._tool_spinner_timer.stop()
        self._tool_spinner_timer = self.set_timer(0.12, self._animate_tool_spinner)

    def _render_tool_spinner_frame(self) -> None:
        """Render the current spinner frame into the conversation log."""
        if self._tool_call_start is None or self._tool_name is None:
            return

        spinner_char = self._spinner_chars[self._spinner_index]
        self._replace_tool_call_line(spinner_char)

    def _replace_tool_call_line(self, prefix: str) -> None:
        """Replace the current tool call line with a new prefix (spinner frame)."""
        if self._tool_call_start is not None and self._tool_call_start < len(self.lines):
            del self.lines[self._tool_call_start]
            self._line_cache.clear()
            widths: list[int] = []
            for strip in self.lines:
                cell_length = getattr(strip, "cell_length", None)
                widths.append(cell_length() if callable(cell_length) else cell_length or 0)
            self._widest_line_width = max(widths, default=0)
            self.virtual_size = Size(self._widest_line_width, len(self.lines))
            if self.auto_scroll:
                self.scroll_end(animate=False)
        else:
            self._tool_call_start = len(self.lines)

        self._write_tool_call_line(prefix)
        self._tool_call_start = len(self.lines) - 1

    def _write_tool_call_line(self, prefix: str) -> None:
        """Write a tool call line with the given prefix character."""
        formatted = Text()
        prefix_style = "green" if prefix == "⏺" else "bright_cyan"
        formatted.append(f"{prefix} ", style=prefix_style)
        formatted.append(self._tool_name, style="bold bright_cyan")
        formatted.append(f"({self._tool_args})", style="bright_cyan")
        self.write(formatted, scroll_end=False, animate=False)

    def add_tool_result(self, result: str) -> None:
        """Add tool result to conversation."""
        try:
            result_plain = Text.from_markup(result).plain
        except Exception:
            result_plain = result
        line = Text("  ⎿ ", style="green")
        line.append(result_plain, style="green")
        self.write(line)
        self.write(Text(""))  # Add spacing after tool result

    def render_approval_prompt(self, lines: list[Text]) -> None:
        """Render or update the inline approval prompt."""

        if self._approval_start is None:
            self._approval_start = len(self.lines)

        self._truncate_from(self._approval_start)

        for line in lines:
            self.write(line, scroll_end=True, animate=False)

    def clear_approval_prompt(self) -> None:
        """Remove the approval prompt from the log."""

        if self._approval_start is None:
            return

        self._truncate_from(self._approval_start)
        self._approval_start = None

    def _truncate_from(self, index: int) -> None:
        """Remove all lines from the log starting at the given index."""

        if index >= len(self.lines):
            return

        del self.lines[index:]
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

    def __init__(
        self,
        *args,
        paste_threshold: int = 200,
        completer: Optional[Completer] = None,
        **kwargs,
    ) -> None:
        self._completer: Optional[Completer] = completer
        self._completions: list[Any] = []
        self._completion_entries: list[tuple[str, str]] = []
        self._highlight_index: int | None = None
        super().__init__(*args, **kwargs)
        self._paste_threshold = paste_threshold
        self._paste_counter = 0
        self._large_paste_cache: dict[str, str] = {}
        self._suppress_next_autocomplete = False

    @dataclass
    class Submitted(Message):
        """Message emitted when the user submits the chat input."""

        text_area: "ChatTextArea"
        value: str

        @property
        def control(self) -> "ChatTextArea":
            """Compatibility alias matching Textual input events."""
            return self.text_area

    def set_completer(self, completer: Optional[Completer]) -> None:
        """Assign a prompt-toolkit completer for @ mentions and / commands."""

        self._completer = completer
        self.update_suggestion()

    def update_suggestion(self) -> None:
        """Populate the inline suggestion using the configured completer."""

        super().update_suggestion()

        if getattr(self, "_suppress_next_autocomplete", False):
            self._suppress_next_autocomplete = False
            self._clear_completions()
            return

        if not self._completer:
            self._clear_completions()
            return

        if self.selection.start != self.selection.end:
            self._clear_completions()
            return

        text = self.text or ""
        if not text:
            self._clear_completions()
            return

        try:
            cursor_index = self.document.get_index_from_location(self.cursor_location)
        except Exception:
            self._clear_completions()
            return

        document = PTDocument(text=text, cursor_position=cursor_index)
        try:
            completions = list(self._completer.get_completions(document, None))
        except Exception:
            self._clear_completions()
            return

        self._completions = completions
        self._completion_entries = [
            (
                getattr(item, "display_text", item.text),
                getattr(item, "display_meta_text", "") or "",
            )
            for item in completions
        ]

        if self._completions:
            self._set_highlight_index(0)
        else:
            self._set_highlight_index(None)

        self._notify_autocomplete()

    def _notify_autocomplete(self) -> None:
        """Inform the parent app about available autocomplete entries."""

        try:
            app = self.app  # type: ignore[attr-defined]
        except Exception:
            app = None

        if app and hasattr(app, "update_autocomplete"):
            try:
                selected = self._highlight_index if self._highlight_index is not None else None
                app.update_autocomplete(self._completion_entries, selected)
            except Exception:
                pass

    def _clear_completions(self) -> None:
        """Reset completion tracking and hide popup."""

        self._completions = []
        self._completion_entries = []
        self._highlight_index = None
        self.suggestion = ""
        self._notify_autocomplete()

    def _set_highlight_index(self, index: int | None) -> None:
        """Update active selection and inline suggestion."""

        if not self._completions or index is None:
            self._highlight_index = None
            self.suggestion = ""
            return

        clamped = max(0, min(index, len(self._completions) - 1))
        self._highlight_index = clamped

        details = self._compute_completion_details(self._completions[clamped])
        if details:
            self.suggestion = details["remainder"]
        else:
            self.suggestion = ""

    def _compute_completion_details(self, completion: Any) -> dict[str, Any] | None:
        """Compute replacement info for a completion relative to current cursor."""

        try:
            cursor_index = self.document.get_index_from_location(self.cursor_location)
        except Exception:
            return None

        text = self.text or ""
        start_pos = getattr(completion, "start_position", 0) or 0
        replace_start = max(0, cursor_index + start_pos)
        replace_end = cursor_index
        if replace_start > replace_end:
            replace_start = replace_end

        existing = text[replace_start:replace_end]
        completion_text = getattr(completion, "text", "") or ""
        if existing and not completion_text.startswith(existing):
            return None

        remainder = completion_text[len(existing) :] if existing else completion_text
        return {
            "remainder": remainder,
            "replace_start": replace_start,
            "replace_end": replace_end,
            "completion_text": completion_text,
        }

    def _move_completion_selection(self, delta: int) -> None:
        """Advance selection within available completions."""

        if not self._completions:
            return

        current = self._highlight_index or 0
        new_index = (current + delta) % len(self._completions)
        self._set_highlight_index(new_index)
        self._notify_autocomplete()

    def _accept_completion_selection(self) -> bool:
        """Apply the currently selected completion into the text area."""

        if not self._completions:
            return False

        index = self._highlight_index or 0
        index = max(0, min(index, len(self._completions) - 1))
        completion = self._completions[index]
        details = self._compute_completion_details(completion)
        if not details:
            return False

        completion_text = details["completion_text"]
        replace_start = details["replace_start"]
        replace_end = details["replace_end"]

        start_location = self.document.get_location_from_index(replace_start)
        end_location = self.document.get_location_from_index(replace_end)

        result = self._replace_via_keyboard(completion_text, start_location, end_location)
        if result is not None:
            self.cursor_location = result.end_location

        self._clear_completions()
        self._suppress_next_autocomplete = True
        self.update_suggestion()
        return True

    async def _on_key(self, event: Key) -> None:
        """Intercept Enter to submit while preserving Shift+Enter for new lines."""

        app = getattr(self, "app", None)
        approval_mode = getattr(app, "_approval_active", False)

        if approval_mode:
            if event.key == "up":
                event.stop()
                event.prevent_default()
                if hasattr(app, "_approval_move"):
                    app._approval_move(-1)
                return
            if event.key == "down":
                event.stop()
                event.prevent_default()
                if hasattr(app, "_approval_move"):
                    app._approval_move(1)
                return
            if event.key in {"escape", "ctrl+c"}:
                event.stop()
                event.prevent_default()
                if hasattr(app, "_approval_cancel"):
                    app._approval_cancel()
                return
            if event.key in {"enter", "return"} and "+" not in event.key:
                event.stop()
                event.prevent_default()
                if hasattr(app, "_approval_confirm"):
                    app._approval_confirm()
                return

        if event.key in {"pageup", "pagedown"}:
            event.stop()
            event.prevent_default()
            if hasattr(app, "action_scroll_up") and event.key == "pageup":
                app.action_scroll_up()
            elif hasattr(app, "action_scroll_down") and event.key == "pagedown":
                app.action_scroll_down()
            return

        if self._should_insert_newline(event):
            event.stop()
            event.prevent_default()
            self._insert_newline()
            return

        if event.key == "up":
            if self._completions:
                event.stop()
                event.prevent_default()
                self._move_completion_selection(-1)
                return
            event.stop()
            event.prevent_default()
            if hasattr(self.app, "action_history_up"):
                self.app.action_history_up()
            return

        if event.key == "down":
            if self._completions:
                event.stop()
                event.prevent_default()
                self._move_completion_selection(1)
                return
            event.stop()
            event.prevent_default()
            if hasattr(self.app, "action_history_down"):
                self.app.action_history_down()
            return

        if event.key == "shift+tab":
            event.stop()
            event.prevent_default()
            if hasattr(self.app, "action_cycle_mode"):
                self.app.action_cycle_mode()
            return

        if event.key == "tab":
            event.stop()
            event.prevent_default()
            if self._accept_completion_selection():
                return
            if self.suggestion:
                self.insert(self.suggestion)
                return

            await super()._on_key(event)
            return

        if event.key in {"enter", "return"} and "+" not in event.key:
            if self._completions and self._accept_completion_selection():
                event.stop()
                event.prevent_default()
                return
            event.stop()
            event.prevent_default()
            self.post_message(self.Submitted(self, self.text))
            return

        await super()._on_key(event)

        if approval_mode and hasattr(app, "_render_approval_prompt"):
            app._render_approval_prompt()

    def on_paste(self, event: Paste) -> None:
        """Handle paste events, collapsing large blocks into placeholders."""

        paste_text = event.text
        event.stop()
        event.prevent_default()  # Prevent default paste behavior to avoid double paste

        if len(paste_text) > self._paste_threshold:
            token = self._register_large_paste(paste_text)
            self._replace_via_keyboard(token, *self.selection)
            self.update_suggestion()
            return

        self._replace_via_keyboard(paste_text, *self.selection)
        self.update_suggestion()
        app = getattr(self, "app", None)
        if getattr(app, "_approval_active", False) and hasattr(app, "_render_approval_prompt"):
            app._render_approval_prompt()

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
        self.update_suggestion()

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
        self.update_suggestion()


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

    def set_model_name(self, model: str) -> None:
        """Update the displayed model name."""
        self.model = model
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

        # Model (smart truncation if too long)
        model_display = self._smart_truncate_model(self.model, 60)
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

    def _smart_truncate_model(self, model: str, max_len: int) -> str:
        """Smart model name truncation that preserves important parts.

        Args:
            model: Full model name (e.g., "fireworks/accounts/fireworks/models/qwen2p5-coder-32b-instruct")
            max_len: Maximum length allowed

        Returns:
            Truncated model name with important parts preserved
        """
        # For fireworks models, always simplify to show provider + actual model name
        if "accounts/fireworks/models/" in model:
            try:
                # Extract: "accounts/fireworks/models/actual-model-name" -> "fireworks/actual-model-name"
                parts = model.split("accounts/fireworks/models/")
                if len(parts) == 2:
                    provider = "fireworks"
                    model_name = parts[1]
                    simplified = f"{provider}/{model_name}"
                    if len(simplified) <= max_len:
                        return simplified
                    # If still too long, truncate the model name part
                    available = max_len - len(provider) - 1  # -1 for "/"
                    if available > 10:  # Ensure meaningful truncation
                        return f"{provider}/{model_name[: available - 3]}..."
            except Exception:
                pass

        # If no truncation needed and no special processing applied
        if len(model) <= max_len:
            return model

        # For other providers with slashes, try to keep provider/model format
        if "/" in model:
            parts = model.split("/")
            if len(parts) >= 2:
                provider = parts[0]
                model_name = parts[-1]  # Last part is usually the model name
                simplified = f"{provider}/{model_name}"
                if len(simplified) <= max_len:
                    return simplified
                # If still too long, truncate model name
                available = max_len - len(provider) - 1
                if available > 10:
                    return f"{provider}/{model_name[: available - 3]}..."

        # Fallback: simple truncation
        return model[: max_len - 3] + "..."


class ModelFooter(Footer):
    """Footer variant that shows configured model slots alongside key hints."""

    def __init__(
        self,
        model_slots: Mapping[str, tuple[str, str]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._model_slots: dict[str, tuple[str, str]] = dict(model_slots or {})
        self._models_label: Static | None = None

    def compose(self) -> ComposeResult:
        """Compose footer with model display prefix and inherited key hints."""
        self._models_label = Static(
            self._build_model_text(),
            classes="footer--models",
            expand=True,
        )
        yield self._models_label

        parent_compose = super().compose()
        if parent_compose is not None:
            yield from parent_compose

    def update_models(self, model_slots: Mapping[str, tuple[str, str]] | None) -> None:
        """Refresh displayed models."""
        self._model_slots = dict(model_slots or {})
        if self._models_label is not None:
            self._models_label.update(self._build_model_text())

    def _build_model_text(self) -> Text:
        """Create Rich text describing configured model slots."""
        base_style = "#6a6a6a"
        thinking_style = "#FFD700"
        vision_style = "#00CED1"

        text = Text(no_wrap=True)

        thinking_slot = self._model_slots.get("thinking")
        vision_slot = self._model_slots.get("vision")

        def append_slot(label: str, slot: tuple[str, str] | None, style: str) -> None:
            text.append(f"{label}: ", style=base_style)
            if slot:
                provider, model_name = slot
                provider = provider or ""
                model_name = model_name or ""
                display = model_name
                if provider:
                    if model_name:
                        if not model_name.lower().startswith(provider.lower()):
                            display = f"{provider}/{model_name}"
                    else:
                        display = provider
                text.append(display, style=style)
            else:
                text.append("Not set", style="italic #5a5a5a")

        append_slot("Thinking", thinking_slot, thinking_style)
        text.append("  |  ", style=base_style)
        append_slot("Vision", vision_slot, vision_style)

        return text


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
        self._last_autocomplete_state: tuple[tuple[tuple[str, str], ...], int] | None = None
        self.footer: ModelFooter | None = None
        self._is_processing = False
        self._message_history = []
        self._history_index = -1
        self._current_input = ""
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
        self._pending_tool_summaries: list[str] = []
        self._assistant_response_received = False
        self._saw_tool_result = False
        self._ui_thread: threading.Thread | None = None
        self._model_picker_state: dict[str, Any] | None = None
        self._approval_active = False
        self._approval_future: asyncio.Future[tuple[bool, str, str]] | None = None
        self._approval_options: list[tuple[str, str, str]] = []
        self._approval_selected_index = 0
        self._approval_command: str = ""
        self._approval_working_dir: str = ""

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
        self._last_autocomplete_state = None
        self.update_autocomplete([], None)

        # Focus input field
        self.input_field.focus()

        # Show different welcome message based on whether we have real backend integration
        if self.on_message:
            self.title = "SWE-CLI Chat"
            self.sub_title = "AI-powered coding assistant"
            self._render_welcome_panel(real_integration=True)
            self.status_bar.set_context(15)
        else:
            self.title = "SWE-CLI Chat (Textual POC)"
            self.sub_title = "Full-screen terminal interface"
            self._render_welcome_panel(real_integration=False)
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

    def _render_welcome_panel(self, *, real_integration: bool) -> None:
        """Render a polished welcome panel with structured two-column layout."""
        from pathlib import Path
        from swecli.ui.components.welcome import WelcomeMessage
        from swecli.core.management import OperationMode
        import os

        if real_integration:
            # Get current session info
            working_dir = Path.cwd()
            username = os.getenv("USER", "Developer")
            current_mode = OperationMode.NORMAL  # Default mode on startup

            # Generate the full two-column welcome banner
            welcome_lines = WelcomeMessage.generate_full_welcome(
                current_mode=current_mode,
                working_dir=working_dir,
                username=username,
            )

            # Write each line to the conversation
            for line in welcome_lines:
                self.conversation.write(Text.from_ansi(line))

        else:
            # POC mode - simple welcome
            heading = Text("SWE-CLI (Preview)", style="bold bright_cyan")
            subheading = Text("Textual POC interface", style="dim")
            body = Text(
                "Use this playground to explore the upcoming Textual UI.\n"
                "Core flows are stubbed; use /help, /demo, or /scroll to interact."
            )

            shortcuts = Text()
            shortcuts.append("Enter", style="bold green")
            shortcuts.append(" send   •   ")
            shortcuts.append("Shift+Enter", style="bold green")
            shortcuts.append(" new line   •   ")
            shortcuts.append("/help", style="bold cyan")
            shortcuts.append(" commands")

            content = Text.assemble(
                heading,
                "\n",
                subheading,
                "\n\n",
                body,
                "\n\n",
                shortcuts,
            )

            panel = Panel(
                Align.center(content, vertical="middle"),
                border_style="bright_cyan",
                padding=(1, 3),
                title="Welcome",
                subtitle="swecli-textual",
                subtitle_align="left",
                width=78,
            )

            self.conversation.write(panel)

        self.conversation.add_system_message("")

    def update_autocomplete(
        self,
        entries: list[tuple[str, str]],
        selected_index: int | None = None,
    ) -> None:
        """Render autocomplete options directly beneath the input field."""

        if not self.autocomplete_popup:
            return

        if self._approval_active:
            self.autocomplete_popup.update("")
            self.autocomplete_popup.styles.display = "none"
            self._last_autocomplete_state = None
            return

        if not entries:
            self.autocomplete_popup.update("")
            self.autocomplete_popup.styles.display = "none"
            self._last_autocomplete_state = None
            return

        limit = min(len(entries), 5)
        rows = [
            (label or "", meta or "")
            for label, meta in entries[:limit]
        ]
        active = selected_index if selected_index is not None else 0
        active = max(0, min(active, len(rows) - 1))

        state = (tuple(rows), active)
        if state == self._last_autocomplete_state:
            self.autocomplete_popup.styles.display = "block"
            return

        text = Text()
        for index, (label, meta) in enumerate(rows):
            is_active = index == active
            pointer = "▸ " if is_active else "  "
            pointer_style = "bold bright_cyan" if is_active else "dim"
            text.append(pointer, style=pointer_style)
            text.append(label, style="bold white" if is_active else "bright_cyan")
            if meta:
                text.append("  ", style="")
                text.append(meta, style="dim white" if is_active else "dim")
            if index < len(rows) - 1:
                text.append("\n")

        self.autocomplete_popup.update(text)
        self.autocomplete_popup.styles.display = "block"
        self._last_autocomplete_state = state

    def _start_local_spinner(self, message: str | None = None) -> None:
        """Begin local spinner animation while backend processes."""

        if self._spinner_timer is not None:
            return

        if not hasattr(self, "conversation") or not hasattr(self, "status_bar"):
            return

        if self._queued_console_renderables:
            self._queued_console_renderables.clear()

        if message is not None:
            self._spinner_message = message
        else:
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
        self._spinner_started_at = 0.0
        self._last_rendered_assistant = None
        self._last_assistant_normalized = None

        self.flush_console_buffer()

    def resume_reasoning_spinner(self) -> None:
        """Restart the thinking spinner after tool output while waiting for reply."""

        if not self._is_processing:
            return

        if self._spinner_timer is not None:
            self._stop_local_spinner()

        self._start_local_spinner(self._get_spinner_message())

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
                segments = [
                    segment.text
                    for segment in console.render(renderable)
                    if getattr(segment, "text", "")
                ]
            except Exception:  # pragma: no cover - defensive
                return False
        else:
            return False

        combined = " ".join(segments)
        normalized_combined = self._normalize_paragraph(combined)
        targets = [
            value
            for value in (self._pending_assistant_normalized, self._last_assistant_normalized)
            if value
        ]
        if normalized_combined and targets:
            if any(normalized_combined == target for target in targets):
                return True

        normalized_segments = [self._normalize_assistant_line(seg) for seg in segments]
        normalized_segments = [seg for seg in normalized_segments if seg]
        if (
            normalized_segments
            and self._last_assistant_lines
            and all(seg in self._last_assistant_lines for seg in normalized_segments)
        ):
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

    def _invoke_on_ui_thread(self, func: Callable[[], None]) -> None:
        """Ensure func executes on the UI thread regardless of caller context."""
        if self._ui_thread is not None and threading.current_thread() is self._ui_thread:
            func()
            return

        if getattr(self, "is_running", False):
            try:
                self.call_from_thread(func)
                return
            except Exception:
                pass

        func()

    def _reset_interaction_state(self) -> None:
        """Clear per-request tracking for tool summaries and assistant follow-ups."""
        self._pending_tool_summaries.clear()
        self._assistant_response_received = False
        self._saw_tool_result = False
        if hasattr(self.input_field, "_clear_completions"):
            self.input_field._clear_completions()

    def record_tool_summary(
        self, tool_name: str, tool_args: dict[str, Any], result_lines: list[str]
    ) -> None:
        """Record a tool result summary for fallback assistant messaging."""
        if not result_lines:
            return

        summary = self._build_tool_summary(tool_name, tool_args, result_lines)
        if not summary:
            return

        self._pending_tool_summaries.append(summary)
        self._saw_tool_result = True

    def _build_tool_summary(
        self, tool_name: str, tool_args: dict[str, Any], result_lines: list[str]
    ) -> str:
        """Create a human-friendly sentence summarizing a tool result."""
        primary = (result_lines[0] or "").strip()
        if not primary:
            return ""

        friendly_tool = tool_name.replace("_", " ")
        args_display = self._format_tool_args_for_summary(tool_args)

        if not primary.endswith((".", "!", "?")):
            primary = f"{primary}."

        # Capitalize the first letter for readability
        if primary and primary[0].islower():
            primary = primary[0].upper() + primary[1:]

        if args_display:
            prefix = f"{friendly_tool}({args_display})"
        else:
            prefix = friendly_tool

        if len(result_lines) > 1:
            return f"Completed {prefix} — {primary}"

        return f"Completed {prefix}."

    def _format_tool_args_for_summary(self, tool_args: dict[str, Any]) -> str:
        """Format tool arguments for a concise summary sentence."""
        if not isinstance(tool_args, dict) or not tool_args:
            return ""

        parts: list[str] = []
        for key in sorted(tool_args):
            value = tool_args[key]
            if value is None:
                continue
            if isinstance(value, str):
                display = value.strip()
                if len(display) > 30:
                    display = f"{display[:27]}..."
                display = display.replace("\n", " ")
                parts.append(f"{key}='{display}'")
            else:
                parts.append(f"{key}={value!r}")

        return ", ".join(parts)

    def _emit_tool_follow_up_if_needed(self) -> None:
        """Render a fallback assistant follow-up if tools finished without LLM wrap-up."""
        if not hasattr(self, "conversation"):
            self._pending_tool_summaries.clear()
            self._saw_tool_result = False
            return

        if self._assistant_response_received or not self._saw_tool_result:
            self._pending_tool_summaries.clear()
            self._saw_tool_result = False
            return

        if not self._pending_tool_summaries:
            self._saw_tool_result = False
            return

        if len(self._pending_tool_summaries) == 1:
            message = self._pending_tool_summaries[0]
        else:
            lines = ["Summary of tool activity:"]
            lines.extend(f"- {summary}" for summary in self._pending_tool_summaries)
            message = "\n".join(lines)

        self._stop_local_spinner()
        self.conversation.add_assistant_message(message)
        self.record_assistant_message(message)
        self._pending_tool_summaries.clear()
        self._saw_tool_result = False

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
        self._assistant_response_received = True
        self._pending_tool_summaries.clear()
        self._saw_tool_result = False

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

        if self._model_picker_state:
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
        if self._model_picker_state:
            self.conversation.add_system_message(
                "Model selector already open — finish the current flow or type X to cancel."
            )
            self.refresh()
            return

        try:
            from swecli.config import get_model_registry

            registry = get_model_registry()
        except Exception as exc:  # pragma: no cover - defensive
            self.conversation.add_system_message(f"❌ Unable to load model registry: {exc}")
            self.refresh()
            return

        self._model_picker_state = {
            "stage": "slot",
            "registry": registry,
            "slot": None,
            "providers": [],
            "provider_index": 0,
            "provider": None,
            "models": [],
            "model_index": 0,
            "slot_items": [],
            "slot_index": 0,
            "panel_start": None,
        }

        self.input_field.load_text("")
        self.input_field.cursor_position = 0
        self.input_field.focus()
        self._render_model_slot_panel()

    @staticmethod
    def _model_slot_labels() -> dict[str, str]:
        """Friendly labels for each slot."""
        return {
            "normal": "Normal (Primary)",
            "thinking": "Thinking (Reasoning)",
            "vision": "Vision (Multimodal)",
        }

    @staticmethod
    def _model_slot_description(slot: str) -> str:
        """Short description for slot instructions."""
        descriptions = {
            "normal": "Standard coding and chat tasks",
            "thinking": "Deep reasoning and planning",
            "vision": "Image analysis and multimodal inputs",
        }
        return descriptions.get(slot, "")

    def _get_model_config_snapshot(self) -> dict[str, dict[str, str]]:
        """Return current model configuration details."""
        snapshot: dict[str, dict[str, str]] = {}
        if self.get_model_config:
            try:
                raw_config = self.get_model_config()
                if isinstance(raw_config, Mapping):
                    for slot, value in raw_config.items():
                        if isinstance(value, Mapping):
                            snapshot[slot] = {
                                "provider": str(value.get("provider", "") or ""),
                                "provider_display": str(value.get("provider_display", "") or value.get("provider", "") or ""),
                                "model": str(value.get("model", "") or ""),
                                "model_display": str(value.get("model_display", "") or value.get("model", "") or ""),
                            }
            except Exception:  # pragma: no cover - defensive
                snapshot = {}

        if not snapshot and self.model_slots:
            for slot, (provider_display, model_display) in self.model_slots.items():
                snapshot[slot] = {
                    "provider_display": provider_display,
                    "model_display": model_display,
                }

        return snapshot

    def _compute_providers_for_slot(self, slot: str, registry) -> list[dict[str, Any]]:
        """Return providers with matching models for a given slot."""
        if registry is None:
            return []

        capability_map = {
            "normal": None,
            "thinking": "reasoning",
            "vision": "vision",
        }
        required_capability = capability_map.get(slot)
        universal_providers = {"openai", "anthropic"}

        providers: list[dict[str, Any]] = []
        for provider in sorted(registry.list_providers(), key=lambda info: info.name.lower()):
            is_universal = provider.id in universal_providers
            if slot == "normal":
                models = provider.list_models()
            else:
                if is_universal:
                    models = provider.list_models()
                else:
                    models = [
                        model
                        for model in provider.list_models()
                        if required_capability and required_capability in model.capabilities
                    ]
            if not models:
                continue

            models = sorted(models, key=lambda m: m.context_length, reverse=True)
            providers.append(
                {
                    "provider": provider,
                    "models": models,
                    "is_universal": is_universal,
                }
            )

        return providers

    def _render_model_slot_panel(self) -> None:
        """Render slot selection panel."""
        if not self._model_picker_state:
            return

        config_snapshot = self._get_model_config_snapshot()
        labels = self._model_slot_labels()

        items: list[dict[str, str]] = []
        order = ["normal", "thinking", "vision"]
        for slot in order:
            slot_label = labels.get(slot, slot.title())
            current = config_snapshot.get(slot, {})
            provider_display = current.get("provider_display") or current.get("provider") or ""
            model_display = current.get("model_display") or current.get("model") or ""
            if provider_display and model_display:
                summary = f"{provider_display}/{model_display}"
            elif provider_display:
                summary = provider_display
            else:
                summary = "Not set"
            items.append({
                "value": slot,
                "label": slot_label,
                "summary": summary,
            })

        items.append({
            "value": "finish",
            "label": "Finish & summary",
            "summary": "Show current configuration",
        })
        items.append({
            "value": "cancel",
            "label": "Cancel",
            "summary": "Close the selector",
        })

        state = self._model_picker_state
        state["slot_items"] = items
        index = state.get("slot_index", 0)
        if not 0 <= index < len(items):
            index = 0
        state["slot_index"] = index

        table = Table.grid(expand=False, padding=(0, 1))
        table.add_column(width=2, justify="center")
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        for row_index, item in enumerate(items):
            is_active = row_index == index
            pointer = "❯" if is_active else " "
            row_style = "on #1f2d3a" if is_active else ""
            pointer_style = "bold bright_cyan" if is_active else "dim"
            label_style = "bold white" if is_active else "white"
            summary_style = "dim white" if is_active else "dim"
            table.add_row(
                Text(pointer, style=pointer_style),
                Text(item["label"], style=label_style),
                Text(item["summary"], style=summary_style),
                style=row_style,
            )

        instructions = Text(
            "Use ↑/↓ to highlight a slot, Enter to select (1-3 also work), Esc to cancel.",
            style="italic #7a8691",
        )
        header = Text("Select which model slot you’d like to configure.", style="#9ccffd")
        panel = Panel(
            Group(header, table, instructions),
            title="[bold]Model Configuration[/bold]",
            title_align="left",
            border_style="bright_cyan",
            padding=(1, 2),
        )
        self._post_model_panel(panel)

    def _render_provider_panel(self) -> None:
        """Render provider selection panel."""
        if not self._model_picker_state:
            return

        slot = self._model_picker_state.get("slot")
        registry = self._model_picker_state.get("registry")
        providers = self._compute_providers_for_slot(slot, registry)

        if not providers:
            labels = self._model_slot_labels()
            self.conversation.add_system_message(
                f"⚠️ No providers currently offer models for {labels.get(slot, slot)}."
            )
            self._model_picker_state["stage"] = "slot"
            self._model_picker_state["providers"] = []
            self._render_model_slot_panel()
            return

        state = self._model_picker_state
        state["providers"] = providers
        index = state.get("provider_index", 0)
        if not 0 <= index < len(providers):
            index = 0
        state["provider_index"] = index

        labels = self._model_slot_labels()
        description = self._model_slot_description(slot or "")

        table = Table.grid(expand=False, padding=(0, 1))
        table.add_column(width=2, justify="center")
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        for row_index, entry in enumerate(providers):
            provider = entry["provider"]
            models = entry["models"]
            total_models = len(models)
            capabilities = sorted({cap for model in models for cap in model.capabilities})
            caps_display = ", ".join(capabilities[:3])
            if len(capabilities) > 3:
                caps_display += ", …"

            summary = Text(style="dim")
            summary.append(f"{total_models} models", style="dim")
            if caps_display:
                summary.append(f" • {caps_display}", style="dim")
            if provider.description:
                summary.append(f"\n{provider.description}", style="dim")

            is_active = row_index == index
            pointer = "❯" if is_active else " "
            row_style = "on #1f2d3a" if is_active else ""
            pointer_style = "bold bright_cyan" if is_active else "dim"
            label_style = "bold white" if is_active else "white"

            table.add_row(
                Text(pointer, style=pointer_style),
                Text(provider.name, style=label_style),
                summary,
                style=row_style,
            )

        instructions = Text(
            "Use ↑/↓ to choose a provider, Enter to view models (numbers work too), B to go back, Esc to cancel.",
            style="italic #7a8691",
        )
        subtitle = Text(
            f"{labels.get(slot, slot.title())} · {description}",
            style="#9ccffd",
        )
        panel = Panel(
            Group(subtitle, table, instructions),
            title="[bold]Choose a Provider[/bold]",
            title_align="left",
            border_style="bright_blue",
            padding=(1, 2),
        )
        self._post_model_panel(panel)

    def _render_model_list_panel(self) -> None:
        """Render model options for the selected provider."""
        if not self._model_picker_state:
            return

        provider_entry = self._model_picker_state.get("provider")
        models = self._model_picker_state.get("models") or []
        slot = self._model_picker_state.get("slot")

        if not provider_entry or not models:
            self.conversation.add_system_message("No models available for the selected provider.")
            self._model_picker_state["stage"] = "provider"
            self._render_provider_panel()
            return

        labels = self._model_slot_labels()

        state = self._model_picker_state
        state["models"] = models
        index = state.get("model_index", 0)
        if not 0 <= index < len(models):
            index = 0
        state["model_index"] = index

        table = Table.grid(expand=False, padding=(0, 1))
        table.add_column(width=2, justify="center")
        table.add_column(ratio=1)
        table.add_column(width=14, justify="right")

        for row_index, model in enumerate(models):
            model_name = model.name
            if model.recommended:
                model_name = f"★ {model_name}"
            context_k = f"{model.context_length // 1000}k context"

            is_active = row_index == index
            pointer = "❯" if is_active else " "
            row_style = "on #1f2d3a" if is_active else ""
            pointer_style = "bold bright_cyan" if is_active else "dim"
            label_style = "bold white" if is_active else "white"
            info_style = "dim white" if is_active else "dim"

            table.add_row(
                Text(pointer, style=pointer_style),
                Text(model_name, style=label_style),
                Text(context_k, style=info_style),
                style=row_style,
            )

        instructions = Text(
            "Use ↑/↓ to highlight a model, Enter to apply, B to go back, Esc to cancel.",
            style="italic #7a8691",
        )
        subtitle = Text(
            f"{provider_entry.name} · {labels.get(slot, slot.title())}",
            style="#9ccffd",
        )
        panel = Panel(
            Group(subtitle, table, instructions),
            title="[bold]Select a Model[/bold]",
            title_align="left",
            border_style="bright_green",
            padding=(1, 2),
        )
        self._post_model_panel(panel)

    def _render_model_summary(self) -> None:
        """Render a summary of configured models."""
        snapshot = self._get_model_config_snapshot()
        labels = self._model_slot_labels()

        table = Table(
            show_header=True,
            header_style="bold #8cc8ff",
            box=box.ROUNDED,
            expand=True,
        )
        table.add_column("Slot", style="bold white")
        table.add_column("Provider", style="#d7d7d7")
        table.add_column("Model", style="#d7d7d7")

        for slot in ["normal", "thinking", "vision"]:
            entry = snapshot.get(slot, {})
            provider_display = entry.get("provider_display") or entry.get("provider") or "Not set"
            model_display = entry.get("model_display") or entry.get("model") or "—"
            if provider_display == "Not set":
                model_display = "—"
            table.add_row(labels.get(slot, slot.title()), provider_display, model_display)

        instructions = Text("Type /models again to reopen the selector anytime.", style="italic #7a8691")
        panel = Panel(
            Group(Text("Current model configuration", style="#9ccffd"), table, instructions),
            title="[bold]Model Summary[/bold]",
            title_align="left",
            border_style="bright_cyan",
            padding=(1, 2),
        )
        self._post_model_panel(panel)

    def _post_model_panel(self, panel: RenderableType) -> None:
        """Write a panel to the conversation with spacing."""
        self.conversation.write(panel)
        self.conversation.write(Text(""))
        self.refresh()

    async def _handle_model_picker_input(self, raw_value: str) -> bool:
        """Process user input while the model picker is active."""
        if not self._model_picker_state:
            return False

        value = (raw_value or "").strip()
        if not value:
            return True

        normalized = value.lower().strip()
        normalized = normalized.lstrip("/")
        state = self._model_picker_state
        stage = state.get("stage")

        if stage == "slot":
            if normalized in {"x", "cancel", "quit"}:
                self._end_model_picker("Model selector closed.")
                return True
            if normalized in {"f", "finish", "4"}:
                self._render_model_summary()
                self._end_model_picker(None)
                return True

            slot_map = {"1": "normal", "2": "thinking", "3": "vision"}
            slot = slot_map.get(normalized)
            if not slot:
                self.conversation.add_system_message("Enter 1-3 to select a slot, F to finish, or X to cancel.")
                self.refresh()
                return True

            state["slot"] = slot
            state["stage"] = "provider"
            state["provider"] = None
            state["providers"] = self._compute_providers_for_slot(slot, state.get("registry"))
            self._render_provider_panel()
            return True

        if stage == "provider":
            if normalized in {"x", "cancel", "quit"}:
                self._end_model_picker("Model selector closed.")
                return True
            if normalized in {"b", "back"}:
                state["stage"] = "slot"
                self._render_model_slot_panel()
                return True

            providers = state.get("providers") or []
            try:
                index = int(normalized) - 1
            except ValueError:
                self.conversation.add_system_message("Enter a provider number, B to go back, or X to cancel.")
                self.refresh()
                return True

            if 0 <= index < len(providers):
                entry = providers[index]
                state["provider_index"] = index
                state["provider"] = entry["provider"]
                state["models"] = entry["models"]
                state["stage"] = "model"
                self._render_model_list_panel()
            else:
                self.conversation.add_system_message("That provider number is out of range.")
                self.refresh()
            return True

        if stage == "model":
            if normalized in {"x", "cancel", "quit"}:
                self._end_model_picker("Model selector closed.")
                return True
            if normalized in {"b", "back"}:
                state["stage"] = "provider"
                self._render_provider_panel()
                return True

            models = state.get("models") or []
            try:
                index = int(normalized) - 1
            except ValueError:
                self.conversation.add_system_message("Enter a model number, B to go back, or X to cancel.")
                self.refresh()
                return True

            if 0 <= index < len(models):
                provider_info = state.get("provider")
                slot = state.get("slot")
                if not provider_info or not slot:
                    self.conversation.add_system_message("Internal model selector state invalid.")
                    self.refresh()
                    return True

                model_info = models[index]
                selection_success = await self._apply_model_selection(slot, provider_info, model_info)
                if selection_success:
                    state["stage"] = "slot"
                    state["providers"] = []
                    state["provider"] = None
                    state["models"] = []
                    self._render_model_slot_panel()
                else:
                    self.refresh()
            else:
                self.conversation.add_system_message("That model number is out of range.")
                self.refresh()
            return True

        self._end_model_picker("Model selector reset.")
        return True

    async def _apply_model_selection(self, slot: str, provider_info, model_info) -> bool:
        """Invoke callback to save model selection."""
        if not self.on_model_selected:
            self.conversation.add_system_message("No handler available to update models.")
            return False

        try:
            result = self.on_model_selected(slot, provider_info.id, model_info.id)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:  # pragma: no cover - defensive
            self.conversation.add_system_message(f"❌ Failed to update model: {exc}")
            return False

        success = getattr(result, "success", None)
        message = getattr(result, "message", None)

        if success:
            if message:
                self.conversation.add_system_message(f"✓ {message}")
            else:
                labels = self._model_slot_labels()
                display_name = f"{provider_info.name}/{model_info.name}"
                self.conversation.add_system_message(
                    f"✓ {labels.get(slot, slot.title())} model set to {display_name}"
                )
            self.refresh()
            return True

        error_message = message or "Model update failed."
        self.conversation.add_system_message(f"❌ {error_message}")
        self.refresh()
        return False

    def _end_model_picker(self, message: str | None) -> None:
        """Reset model picker state and optionally display a message."""
        self._model_picker_state = None
        if message:
            self.conversation.add_system_message(message)
        self.refresh()

    async def show_approval_modal(self, command: str, working_dir: str) -> tuple[bool, str, str]:
        """Display an inline approval prompt inside the conversation log."""

        if self._approval_future is not None:
            raise RuntimeError("Approval prompt already active")

        self._approval_command = command or ""
        self._approval_working_dir = working_dir or "."
        base_prefix = ""
        if self._approval_command.strip():
            base_prefix = self._approval_command.strip().split()[0]
        auto_desc = (
            f"Automatically approve commands starting with '{base_prefix}' in {self._approval_working_dir}."
            if base_prefix
            else f"Automatically approve future commands in {self._approval_working_dir}."
        )
        self._approval_options = [
            {"choice": "1", "label": "Yes", "description": "Run this command now.", "approved": True},
            {
                "choice": "2",
                "label": "Yes, and don't ask again",
                "description": auto_desc,
                "approved": True,
            },
            {
                "choice": "3",
                "label": "No",
                "description": "Cancel and adjust your request.",
                "approved": False,
            },
        ]
        self._approval_selected_index = 0
        self._approval_active = True

        loop = asyncio.get_running_loop()
        self._approval_future = loop.create_future()
        # Don't load command into input field - keep it empty during approval
        self.input_field.load_text("")

        if getattr(self.conversation, "_tool_call_start", None) is not None:
            if getattr(self.conversation, "_tool_spinner_timer", None) is not None:
                self.conversation._tool_spinner_timer.stop()
                self.conversation._tool_spinner_timer = None
            self.conversation._spinner_active = False
            self.conversation._replace_tool_call_line("⏺")

        self._render_approval_prompt()
        self.input_field.focus()

        try:
            result = await self._approval_future
        finally:
            self.conversation.clear_approval_prompt()
            self._approval_future = None
            self._approval_active = False
            self._approval_options = []
            self._approval_selected_index = 0
            self._last_autocomplete_state = None
            self.input_field.focus()
            self.input_field.load_text("")

        return result

    def _render_approval_prompt(self) -> None:
        """Compose and display the approval prompt within the conversation log."""

        if not self._approval_active:
            return

        from rich.console import Group
        from rich.panel import Panel
        from rich.table import Table

        cmd_display = self._approval_command or "(empty command)"

        # Build command text with proper styling (not markup)
        command_text = Text("Command: ", style="white")
        command_text.append(cmd_display, style="bold white")

        description_group = Group(
            command_text,
            Text(f"Directory: {self._approval_working_dir}", style="dim"),
            Text(""),
            Text(
                "Use ↑/↓ to choose, Enter to confirm, Esc to cancel.",
                style="dim",
            ),
            Text(""),
        )

        table = Table.grid(padding=(0, 1))
        table.add_column(width=2)
        table.add_column(no_wrap=True)
        table.add_column(ratio=1)

        for index, option in enumerate(self._approval_options):
            is_active = index == self._approval_selected_index
            pointer = "❯" if is_active else " "
            pointer_style = "bold bright_cyan" if is_active else "dim"
            label_style = "bold white" if is_active else "bright_cyan"
            desc_style = "dim white" if is_active else "dim"

            table.add_row(
                Text(pointer, style=pointer_style),
                Text(f"{option['choice']}. {option['label']}", style=label_style),
                Text(option.get("description", ""), style=desc_style),
            )

        panel = Panel(
            Group(description_group, table),
            title="Approval Required",
            border_style="bright_cyan",
            padding=(1, 2),
        )

        self.conversation.render_approval_prompt([panel])
        self.conversation.scroll_end(animate=False)

    def _approval_move(self, delta: int) -> None:
        if not self._approval_active or not self._approval_options:
            return
        self._approval_selected_index = (self._approval_selected_index + delta) % len(self._approval_options)
        self._render_approval_prompt()

    def _approval_confirm(self) -> None:
        if not self._approval_active or not self._approval_future or self._approval_future.done():
            return

        option = self._approval_options[self._approval_selected_index]
        edited_command = self.input_field.text.strip() or self._approval_command
        result = (option.get("approved", True), option["choice"], edited_command)

        call_name = getattr(self.conversation, "_tool_name", None)
        call_args = getattr(self.conversation, "_tool_args", None)
        call_start = getattr(self.conversation, "_tool_call_start", None)

        self.conversation.clear_approval_prompt()

        if option.get("approved", True):
            if call_name and call_args:
                self.conversation.start_tool_execution()
        else:
            if call_start is not None:
                self.conversation._truncate_from(call_start)
                if self.conversation._tool_spinner_timer is not None:
                    self.conversation._tool_spinner_timer.stop()
                    self.conversation._tool_spinner_timer = None
                self.conversation._spinner_active = False
                display_text = call_name or "Command"
                if call_name and call_name.lower().startswith("run command") and call_args:
                    extracted = call_args
                    if "command=" in extracted:
                        extracted = extracted.split("command=", 1)[1].strip()
                        if extracted.startswith("'") and extracted.endswith("'"):
                            extracted = extracted[1:-1]
                        elif extracted.startswith('"') and extracted.endswith('"'):
                            extracted = extracted[1:-1]
                    display_text = f"Bash({extracted})"
                elif call_args:
                    display_text = f"{display_text}({call_args})"

                call_line = Text(display_text, style="bright_cyan")
                self.conversation.write(call_line, scroll_end=True, animate=False)
                result_line = Text("  ⎿ Interrupted · What should we do instead?", style="yellow")
                self.conversation.write(result_line, scroll_end=True, animate=False)
                self.conversation.write(Text(""))
            else:
                self.conversation.add_system_message("Command cancelled.")
            self.conversation._tool_name = None
            self.conversation._tool_args = None
            self.conversation._tool_call_start = None


        self._approval_future.set_result(result)

    def _approval_cancel(self) -> None:
        if not self._approval_active or not self._approval_options:
            return
        self._approval_selected_index = len(self._approval_options) - 1
        self._render_approval_prompt()
        self._approval_confirm()

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
