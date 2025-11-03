"""Conversation log widget with markdown-aware rendering and tool formatting."""

from __future__ import annotations

import re
from typing import Any, List, Tuple

from rich.console import Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from textual.geometry import Size
from textual.timer import Timer
from textual.widgets import RichLog

from swecli.ui_textual.renderers import render_markdown_text_segment


class ConversationLog(RichLog):
    """Enhanced RichLog for conversation display with scrolling support."""

    can_focus = True
    ALLOW_SELECT = False

    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            wrap=True,
            highlight=True,
            markup=True,
            auto_scroll=True,
            max_lines=10000,
        )
        self._user_scrolled = False
        self._last_assistant_rendered: str | None = None
        self._spinner_start: int | None = None
        self._spinner_line_count = 0
        self._tool_spinner_timer: Timer | None = None
        self._tool_display: Text | None = None
        self._spinner_active = False
        self._spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_index = 0
        self._tool_call_start: int | None = None
        self._approval_start: int | None = None

    def on_mount(self) -> None:
        return

    def on_unmount(self) -> None:
        if self._tool_spinner_timer is not None:
            self._tool_spinner_timer.stop()
            self._tool_spinner_timer = None

    def add_user_message(self, message: str) -> None:
        self.write(Text(f"› {message}", style="bold white"))
        self.write(Text(""))

    def add_assistant_message(self, message: str) -> None:
        normalized = self._normalize_text(message)
        if normalized and normalized == self._last_assistant_rendered:
            return

        self._last_assistant_rendered = normalized
        segments = self._split_code_blocks(message)
        text_output = False

        for _, segment in enumerate(segments):
            if segment["type"] == "code":
                self._write_code_block(segment)
            else:
                content = segment["content"]
                if not content:
                    continue
                renderables, wrote = render_markdown_text_segment(
                    content,
                    leading=not text_output,
                )
                for renderable in renderables:
                    self.write(renderable)
                if wrote:
                    text_output = True

        self.write(Text(""))

    def add_system_message(self, message: str) -> None:
        self.write(Text(message, style="dim italic"))

    def add_error(self, message: str) -> None:
        """Render an error message with a red bullet and clear any active spinner."""
        self.stop_spinner()
        bullet = Text("⦿ ", style="bold red")
        bullet.append(message, style="red")
        self.write(bullet)
        self.write(Text(""))

    def add_tool_call(self, display: Text | str, *_: Any) -> None:
        if isinstance(display, Text):
            self._tool_display = display.copy()
        else:
            self._tool_display = Text(str(display), style="white")

        self._tool_call_start = len(self.lines)
        self._write_tool_call_line("⏺")

    def start_tool_execution(self) -> None:
        if self._tool_display is None:
            return

        self._spinner_active = True
        self._spinner_index = 0
        self._render_tool_spinner_frame()
        self._schedule_tool_spinner()

    def stop_tool_execution(self) -> None:
        self._spinner_active = False
        if self._tool_call_start is not None and self._tool_display is not None:
            self._replace_tool_call_line("⏺")

        self._tool_display = None
        self._tool_call_start = None
        self._spinner_index = 0
        if self._tool_spinner_timer is not None:
            self._tool_spinner_timer.stop()
            self._tool_spinner_timer = None

    def add_tool_result(self, result: str) -> None:
        try:
            result_plain = Text.from_markup(result).plain
        except Exception:
            result_plain = result

        header, diff_lines = self._extract_edit_payload(result_plain)
        if header:
            self._write_edit_result(header, diff_lines)
        else:
            self._write_generic_tool_result(result_plain)

        self.write(Text(""))

    def render_approval_prompt(self, lines: list[Text]) -> None:
        if self._approval_start is None:
            self._approval_start = len(self.lines)

        self._truncate_from(self._approval_start)

        for line in lines:
            self.write(line, scroll_end=True, animate=False)

    def clear_approval_prompt(self) -> None:
        if self._approval_start is None:
            return

        self._truncate_from(self._approval_start)
        self._approval_start = None

    # --- Private helpers -------------------------------------------------

    def _write_code_block(self, segment: dict[str, str]) -> None:
        code = segment["content"].strip("\n")
        if not code:
            return
        language = segment.get("language") or "text"
        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=bool(code.count("\n") > 0),
        )
        title = f"Code ({language})" if language and language != "text" else "Code"
        panel = Panel(syntax, title=title, border_style="bright_blue")
        self.write(panel)

    def _write_generic_tool_result(self, text: str) -> None:
        lines = text.rstrip("\n").splitlines() or [text]
        grey = "#a0a4ad"
        for raw_line in lines:
            line = Text("  ⎿ ", style=grey)
            line.append(raw_line, style=grey)
            self.write(line)

    def _write_edit_result(self, header: str, diff_lines: list[str]) -> None:
        if not diff_lines:
            return

        self.write(Text(header, style="bold #d0d0d0"))
        match = re.search(r"Edit(?:ed)?\s+[\"']?([^\s\"']+)", header)
        title = match.group(1) if match else "diff"

        rendered_lines: List[Text] = []
        for raw_line in diff_lines:
            display = raw_line.rstrip("\n")
            if not display.strip():
                rendered_lines.append(Text(""))
                continue

            stripped = display.lstrip()
            style = "#d0d0d0"
            if stripped.startswith("+"):
                style = "green"
            elif stripped.startswith("-"):
                style = "red"
            elif stripped.startswith(("@@", "diff ", "index ", "---", "+++")):
                style = "cyan"
            rendered_lines.append(Text(display, style=style))

        panel = Panel(
            Group(*rendered_lines),
            border_style="#5a5a5a",
            padding=(0, 2),
            title=title,
            title_align="left",
        )
        self.write(panel)

    def _strip_tool_prefix(self, value: str) -> str:
        return re.sub(r"^\s*[⎿⏺•]\s+", "", value)

    def _extract_edit_payload(self, text: str) -> Tuple[str | None, list[str]]:
        lines = text.splitlines()
        if not lines:
            return None, []

        header = None
        payload_start = 0

        for idx, line in enumerate(lines):
            cleaned = self._strip_tool_prefix(line).strip()
            if not cleaned:
                continue
            if cleaned.startswith("Edit(") or cleaned.startswith("Edited "):
                header = cleaned
                payload_start = idx + 1
            break

        if not header:
            return None, []

        diff_lines = [
            self._strip_tool_prefix(ln.rstrip("\n"))
            for ln in lines[payload_start:]
        ]
        return header, diff_lines

    # --- Spinner handling ------------------------------------------------

    def start_spinner(self, message: Text | str) -> None:
        """Append spinner output at the end of the log."""
        self._spinner_start = len(self.lines)
        self._append_spinner(message)

    def update_spinner(self, message: Text | str) -> None:
        """Update spinner output without growing the log."""
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

    def _append_spinner(self, message: Text | str) -> None:
        text = message if isinstance(message, Text) else Text(message, style="bright_cyan")
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
            widths: List[int] = []
            for strip in self.lines:
                cell_length = getattr(strip, "cell_length", None)
                widths.append(cell_length() if callable(cell_length) else cell_length or 0)
            self._widest_line_width = max(widths, default=0)
            self.virtual_size = Size(self._widest_line_width, len(self.lines))
            if self.auto_scroll:
                self.scroll_end(animate=False)
        else:
            self._spinner_start = len(self.lines)

        if preserve_index:
            self._spinner_line_count = 0
        else:
            self._spinner_start = None
            self._spinner_line_count = 0

    # --- Spinner handling ------------------------------------------------

    def _render_tool_spinner_frame(self) -> None:
        if self._tool_call_start is None or self._tool_display is None:
            return

        spinner_char = self._spinner_chars[self._spinner_index]
        self._replace_tool_call_line(spinner_char)

    def _replace_tool_call_line(self, prefix: str) -> None:
        if self._tool_call_start is not None and self._tool_call_start < len(self.lines):
            del self.lines[self._tool_call_start]
            self._line_cache.clear()
            widths: List[int] = []
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
        formatted = Text()
        formatted.append(f"{prefix} ", style="white")
        if self._tool_display is not None:
            formatted += self._tool_display.copy()
        self.write(formatted, scroll_end=False, animate=False)

    def _schedule_tool_spinner(self) -> None:
        if not self._spinner_active:
            return
        if self._tool_spinner_timer is not None:
            self._tool_spinner_timer.stop()
        self._tool_spinner_timer = self.set_timer(0.12, self._animate_tool_spinner)

    def _animate_tool_spinner(self) -> None:
        if not self._spinner_active or self._tool_display is None or self._tool_call_start is None:
            return

        self._render_tool_spinner_frame()
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
        self._schedule_tool_spinner()

    def _truncate_from(self, index: int) -> None:
        if index >= len(self.lines):
            return

        del self.lines[index:]
        self._line_cache.clear()

        widths: List[int] = []
        for strip in self.lines:
            cell_length = getattr(strip, "cell_length", None)
            widths.append(cell_length() if callable(cell_length) else cell_length or 0)

        self._widest_line_width = max(widths, default=0)
        self._start_line = max(0, min(self._start_line, len(self.lines)))
        self.virtual_size = Size(self._widest_line_width, len(self.lines))

        if self.auto_scroll:
            self.scroll_end(animate=False)

        self.refresh()

    # --- Markdown helpers ------------------------------------------------

    def _split_code_blocks(self, message: str) -> list[dict[str, str]]:
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
