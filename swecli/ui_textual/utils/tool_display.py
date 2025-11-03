"""Utilities for presenting human-friendly tool call information in Textual."""

from __future__ import annotations

from pathlib import PurePath
from typing import Any, Mapping, Tuple

from rich.text import Text

__all__ = [
    "build_tool_call_text",
    "format_tool_call",
    "get_tool_display_parts",
    "summarize_tool_arguments",
]

_TOOL_DISPLAY_PARTS: dict[str, tuple[str, str]] = {
    "read_file": ("Read", "file"),
    "write_file": ("Write", "file"),
    "edit_file": ("Edit", "file"),
    "delete_file": ("Delete", "file"),
    "list_files": ("List", "files"),
    "list_directory": ("List", "directory"),
    "search_code": ("Search", "code"),
    "search": ("Search", "project"),
    "run_command": ("Run", "command"),
    "bash_execute": ("Run", "command"),
    "get_process_output": ("Output", "process"),
    "list_processes": ("List", "processes"),
    "kill_process": ("Stop", "process"),
    "fetch_url": ("Fetch", "url"),
    "open_browser": ("Open", "browser"),
    "capture_screenshot": ("Capture", "screenshot"),
    "list_screenshots": ("List", "screenshots"),
    "clear_screenshots": ("Clear", "screenshots"),
    "capture_web_screenshot": ("Capture", "page"),
    "list_web_screenshots": ("List", "pages"),
    "clear_web_screenshots": ("Clear", "pages"),
    "analyze_image": ("Analyze", "image"),
    "git_commit": ("Commit", "changes"),
    "git_branch": ("Branch", "git"),
}

_PATH_HINT_KEYS = {
    "file_path",
    "path",
    "directory",
    "dir",
    "image_path",
    "working_dir",
    "target",
}

_PRIMARY_ARG_MAP: dict[str, tuple[str, ...]] = {
    "read_file": ("file_path",),
    "write_file": ("file_path", "path"),
    "edit_file": ("file_path", "path"),
    "delete_file": ("file_path", "path"),
    "list_files": ("path", "directory"),
    "list_directory": ("path", "directory"),
    "search_code": ("pattern", "query"),
    "search": ("query",),
    "run_command": ("command",),
    "bash_execute": ("command",),
    "get_process_output": ("pid", "command"),
    "kill_process": ("pid",),
    "fetch_url": ("url",),
    "open_browser": ("url",),
    "capture_screenshot": ("target", "path"),
    "capture_web_screenshot": ("url",),
    "analyze_image": ("image_path", "file_path"),
    "git_commit": ("message",),
}

_MAX_SUMMARY_LEN = 60
_NESTED_KEY_PRIORITY: tuple[str, ...] = (
    "command",
    "file_path",
    "path",
    "target",
    "url",
    "pid",
    "process_id",
    "query",
    "pattern",
    "directory",
    "name",
    "title",
    "description",
)


def _fallback_parts(tool_name: str) -> tuple[str, str]:
    cleaned = tool_name.replace("-", "_")
    tokens = [token for token in cleaned.split("_") if token]
    if not tokens:
        return ("Call", "tool")
    verb = tokens[0].capitalize()
    if len(tokens) == 1:
        return (verb, "item")
    label = " ".join(tokens[1:])
    return (verb, label)


def get_tool_display_parts(tool_name: str) -> Tuple[str, str]:
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        if len(parts) == 3:
            return ("MCP", f"{parts[1]}/{parts[2]}")
        if len(parts) == 2:
            return ("MCP", parts[1])
        return ("MCP", "tool")

    if tool_name in _TOOL_DISPLAY_PARTS:
        return _TOOL_DISPLAY_PARTS[tool_name]

    return _fallback_parts(tool_name)


def _shorten_path(value: str) -> str:
    try:
        path = PurePath(value)
    except Exception:
        return value

    parts = path.parts
    if len(parts) <= 2:
        return str(path)
    return f".../{'/'.join(parts[-2:])}"


def _format_summary_value(value: Any, key: str | None = None) -> str:
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        return f"{key}={value}" if key else str(value)

    if isinstance(value, str):
        display = value.strip()
        if not display:
            return ""
        if key in {"pid", "process_id"} and display.isdigit():
            return f"{key}={display}"
        display = display.replace("\n", " ")

        # Don't shorten URLs (they contain :// which PurePath mangles)
        is_url = display.startswith(("http://", "https://", "ftp://", "file://"))
        if not is_url and (key in _PATH_HINT_KEYS or "/" in display or "\\" in display):
            display = _shorten_path(display)

        if len(display) > _MAX_SUMMARY_LEN:
            display = display[: _MAX_SUMMARY_LEN - 3] + "..."
        return f'"{display}"'

    display = str(value)
    if len(display) > _MAX_SUMMARY_LEN:
        display = display[: _MAX_SUMMARY_LEN - 3] + "..."
    return f"{key}={display}" if key else display


def _summarize_nested_value(value: Any, key: str | None, seen: set[int] | None = None) -> str:
    if seen is None:
        seen = set()

    identity = id(value)
    if identity in seen:
        return ""

    seen.add(identity)

    if isinstance(value, Mapping):
        for preferred_key in _NESTED_KEY_PRIORITY:
            if preferred_key in value:
                nested_summary = _summarize_nested_value(value[preferred_key], preferred_key, seen)
                if nested_summary:
                    return nested_summary
        for nested_key, nested_value in value.items():
            nested_summary = _summarize_nested_value(nested_value, nested_key, seen)
            if nested_summary:
                return nested_summary
        return ""

    if isinstance(value, (list, tuple, set)):
        for item in value:
            nested_summary = _summarize_nested_value(item, key, seen)
            if nested_summary:
                return nested_summary
        return ""

    return _format_summary_value(value, key)


def summarize_tool_arguments(tool_name: str, tool_args: Mapping[str, Any]) -> str:
    if not isinstance(tool_args, Mapping) or not tool_args:
        return ""

    primary_keys = _PRIMARY_ARG_MAP.get(tool_name, ())
    for key in primary_keys:
        if key in tool_args:
            summary = _summarize_nested_value(tool_args[key], key)
            if summary:
                return summary

    for key, value in tool_args.items():
        summary = _summarize_nested_value(value, key)
        if summary:
            return summary

    return ""


def format_tool_call(tool_name: str, tool_args: Mapping[str, Any] | None = None) -> str:
    verb, label = get_tool_display_parts(tool_name)
    summary = summarize_tool_arguments(tool_name, tool_args or {})

    display = verb
    if label:
        display = f"{verb}({label})"

    bold_cyan = "\033[1;36m"
    reset = "\033[0m"

    if summary:
        return f"{bold_cyan}{verb}{reset}({summary})"
    return f"{bold_cyan}{display}{reset}" if display else f"{bold_cyan}{verb}{reset}"


def build_tool_call_text(tool_name: str, tool_args: Mapping[str, Any] | None = None) -> Text:
    verb, label = get_tool_display_parts(tool_name)
    summary = summarize_tool_arguments(tool_name, tool_args or {})

    text = Text()
    text.append(verb, style="bold cyan")
    if summary:
        text.append("(", style="white")
        text.append(summary, style="white")
        text.append(")", style="white")
    elif label:
        text.append(f"({label})", style="white")
    return text
