"""Tests for markdown rendering helpers used by Textual and CLI output."""

from rich.text import Text

from swecli.ui_textual.renderers.markdown import render_markdown_text_segment
from swecli.ui_textual.formatters_internal.markdown_formatter import markdown_to_plain_text


def _render_plain(content: str) -> list[str]:
    renderables, _ = render_markdown_text_segment(content)
    plains: list[str] = []
    for renderable in renderables:
        if isinstance(renderable, Text):
            plains.append(renderable.plain)
        else:
            plains.append(str(renderable))
    return plains


def test_heading_rendering():
    plains = _render_plain("# Title")
    assert plains == ["Title"]


def test_nested_bullet_rendering():
    plains = _render_plain("- item\n  - sub item")
    assert plains == ["• item", "  – sub item"]


def test_blockquote_rendering():
    plains = _render_plain("> quoted text")
    assert plains == ["❝ quoted text"]


def test_horizontal_rule_rendering():
    plains = _render_plain("---")
    assert plains == ["────────────────────────────────────────"]


def test_ordered_list_rendering():
    plains = _render_plain("1. first\n   1. nested")
    assert plains == ["1. first", "  – nested"]


def test_markdown_to_plain_text_alignment():
    content = """# Heading

- First
  - Nested
> Quote here
"""
    result = markdown_to_plain_text(content)
    lines = [line for line in result.splitlines() if line]
    assert "HEADING" in lines[0]
    assert "• First" in lines[1]
    assert "  – Nested" in lines[2]
    assert lines[-1].startswith(" ❝ Quote")
