"""Utilities for converting Markdown into simple plain-text formatting."""

from __future__ import annotations

import re
from typing import Iterable


def _strip_emphasis(text: str) -> str:
    """Remove common Markdown emphasis markers."""
    patterns: Iterable[tuple[str, str]] = (
        (r"\*\*(.*?)\*\*", r"\1"),
        (r"__(.*?)__", r"\1"),
        (r"\*(.*?)\*", r"\1"),
        (r"_(.*?)_", r"\1"),
        (r"`([^`]*)`", r"\1"),
    )
    cleaned = text
    for pattern, replacement in patterns:
        cleaned = re.sub(pattern, replacement, cleaned)
    return cleaned


def markdown_to_plain_text(content: str) -> str:
    """Convert Markdown content to a lightly formatted plain-text string."""
    lines = content.splitlines()
    output: list[str] = []
    in_code_block = False
    code_buffer: list[str] = []

    def flush_code_block() -> None:
        if not code_buffer:
            return
        # Separate code block from previous text
        if output and output[-1] != "":
            output.append("")
        for line in code_buffer:
            # Preserve indentation with four leading spaces
            output.append(f"    {line}")
        output.append("")
        code_buffer.clear()

    for raw_line in lines:
        stripped = raw_line.strip()

        # Handle code fences
        if stripped.startswith("```"):
            if in_code_block:
                flush_code_block()
                in_code_block = False
            else:
                in_code_block = True
                code_buffer.clear()
            continue

        if in_code_block:
            code_buffer.append(raw_line.rstrip())
            continue

        if not stripped:
            if output and output[-1] != "":
                output.append("")
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip('#'))
            title = _strip_emphasis(stripped[level:].strip())
            if output and output[-1] != "":
                output.append("")
            if level <= 2:
                title = title.upper()
            output.append(title)
            output.append("")
            continue

        if stripped.startswith(('-', '*', '+')):
            bullet_text = _strip_emphasis(stripped[1:].strip())
            output.append(f" • {bullet_text}")
            continue

        ordered_match = re.match(r"(\d+)[.)]\s+(.*)", stripped)
        if ordered_match:
            bullet_text = _strip_emphasis(ordered_match.group(2).strip())
            output.append(f" {ordered_match.group(1)}. {bullet_text}")
            continue

        cleaned_line = _strip_emphasis(raw_line.rstrip())
        output.append(cleaned_line)

    if in_code_block:
        flush_code_block()

    # Collapse excessive blank lines but preserve single spacing
    cleaned_output: list[str] = []
    previous_blank = False
    for line in output:
        if not line.strip():
            if not previous_blank and cleaned_output:
                cleaned_output.append("")
            previous_blank = True
        else:
            cleaned_output.append(line.rstrip())
            previous_blank = False

    return "\n".join(cleaned_output).strip()
