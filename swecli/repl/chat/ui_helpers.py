"""UI helper functions for chat interface."""

import textwrap
from typing import Optional


class ChatUIHelpers:
    """Helper functions for chat UI rendering."""

    @staticmethod
    def get_content_width() -> int:
        """Get the current terminal width for content rendering.

        Returns:
            Content width (terminal width minus margins for scrollbar and padding)
        """
        import shutil

        terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        # Reserve space for scrollbar (1) and padding (3)
        return max(terminal_size.columns - 4, 60)  # Minimum 60 chars

    @staticmethod
    def wrap_text(text: str, width: int = 76) -> str:
        """Wrap text to specified width, preserving intentional line breaks.

        Args:
            text: Text to wrap
            width: Maximum line width

        Returns:
            Wrapped text
        """
        # Split into paragraphs (preserve intentional breaks)
        paragraphs = text.split("\n")

        wrapped_paragraphs = []
        for para in paragraphs:
            if para.strip():
                # Check if line starts with ⏺ symbol (with or without ANSI color codes)
                if para.startswith("⏺") or para.startswith("\033[32m⏺"):
                    # Add indentation for continuation lines (3 spaces to align with text after "⏺ ")
                    wrapped = textwrap.fill(
                        para,
                        width=width,
                        break_long_words=False,
                        break_on_hyphens=False,
                        subsequent_indent="   ",  # 3 spaces for indentation
                    )
                    wrapped_paragraphs.append(wrapped)
                elif para.lstrip().startswith("• "):
                    indent = "   "
                    leading = "" if not para.startswith(" ") else " "
                    wrapped = textwrap.fill(
                        para,
                        width=width,
                        break_long_words=False,
                        break_on_hyphens=False,
                        subsequent_indent=f"{leading}{indent}",
                    )
                    wrapped_paragraphs.append(wrapped)
                elif len(para) > width:
                    # Regular wrapping without indentation
                    wrapped = textwrap.fill(
                        para, width=width, break_long_words=False, break_on_hyphens=False
                    )
                    wrapped_paragraphs.append(wrapped)
                else:
                    wrapped_paragraphs.append(para)
            else:
                # Preserve empty lines
                wrapped_paragraphs.append(para)

        return "\n".join(wrapped_paragraphs)

    @staticmethod
    def render_markdown_message(content: str, width: int) -> Optional[str]:
        """Render Markdown output as wrapped plain text for the chat window.

        Args:
            content: Markdown content to render
            width: Content width for wrapping

        Returns:
            Rendered and wrapped message, or None if content is empty
        """
        from swecli.ui.formatters_internal.markdown_formatter import markdown_to_plain_text

        cleaned = (content or "").strip()
        if not cleaned:
            return None

        plain = markdown_to_plain_text(cleaned)
        lines = plain.splitlines() if plain else []

        # ANSI color code for green
        GREEN = "\033[32m"
        RESET = "\033[0m"

        if lines:
            lines[0] = f"{GREEN}⏺{RESET} {lines[0]}"
        else:
            lines = [f"{GREEN}⏺{RESET}"]

        message = "\n".join(lines)
        return ChatUIHelpers.wrap_text(message, width=width)
