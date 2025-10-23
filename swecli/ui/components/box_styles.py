"""Unified box and border styling for all UI components."""

from typing import Tuple


class BoxStyles:
    """Centralized box drawing characters and color schemes for elegant UI."""

    # ANSI Color Codes - Consistent across all components
    BORDER_COLOR = "\033[38;5;240m"      # Dim gray for borders
    TITLE_COLOR = "\033[1;36m"           # Bold cyan for titles
    ACCENT_COLOR = "\033[38;5;147m"      # Light purple for accents
    SUCCESS_COLOR = "\033[1;32m"         # Bold green for success/selected
    WARNING_COLOR = "\033[1;33m"         # Bold yellow for warnings
    ERROR_COLOR = "\033[1;31m"           # Bold red for errors
    NORMAL_COLOR = "\033[38;5;250m"      # Light gray for normal text
    DIM_COLOR = "\033[38;5;240m"         # Dim gray for subtle hints
    INFO_COLOR = "\033[38;5;117m"        # Light blue for info
    RESET = "\033[0m"

    # Box Drawing Characters - Rounded Elegant Style
    TOP_LEFT = "╭"
    TOP_RIGHT = "╮"
    BOTTOM_LEFT = "╰"
    BOTTOM_RIGHT = "╯"
    HORIZONTAL = "─"
    VERTICAL = "│"
    LEFT_T = "├"
    RIGHT_T = "┤"
    TOP_T = "┬"
    BOTTOM_T = "┴"
    CROSS = "┼"

    # Standard Box Widths
    NARROW_WIDTH = 60
    STANDARD_WIDTH = 80
    WIDE_WIDTH = 110

    @classmethod
    def top_border(cls, width: int = STANDARD_WIDTH, title: str = "", colored: bool = True) -> str:
        """Create top border with optional title.

        Args:
            width: Total width of the box
            title: Optional title to display in border
            colored: Whether to apply color styling

        Returns:
            Formatted top border string
        """
        border_color = cls.BORDER_COLOR if colored else ""
        reset = cls.RESET if colored else ""

        if title:
            # Title embedded in border: ╭─── Title ───...╮
            title_section = f"─── {title} ─"
            remaining = width - len(title_section) - 2
            return f"{border_color}{cls.TOP_LEFT}{title_section}{'─' * max(0, remaining)}{cls.TOP_RIGHT}{reset}"
        else:
            return f"{border_color}{cls.TOP_LEFT}{cls.HORIZONTAL * (width - 2)}{cls.TOP_RIGHT}{reset}"

    @classmethod
    def bottom_border(cls, width: int = STANDARD_WIDTH, colored: bool = True) -> str:
        """Create bottom border.

        Args:
            width: Total width of the box
            colored: Whether to apply color styling

        Returns:
            Formatted bottom border string
        """
        border_color = cls.BORDER_COLOR if colored else ""
        reset = cls.RESET if colored else ""
        return f"{border_color}{cls.BOTTOM_LEFT}{cls.HORIZONTAL * (width - 2)}{cls.BOTTOM_RIGHT}{reset}"

    @classmethod
    def separator(cls, width: int = STANDARD_WIDTH, colored: bool = True) -> str:
        """Create horizontal separator line.

        Args:
            width: Total width of the box
            colored: Whether to apply color styling

        Returns:
            Formatted separator string
        """
        border_color = cls.BORDER_COLOR if colored else ""
        reset = cls.RESET if colored else ""
        return f"{border_color}{cls.LEFT_T}{cls.HORIZONTAL * (width - 2)}{cls.RIGHT_T}{reset}"

    @classmethod
    def content_line(
        cls,
        content: str,
        width: int = STANDARD_WIDTH,
        padding: int = 1,
        colored: bool = True
    ) -> str:
        """Create content line with borders.

        Args:
            content: Content to display (can include ANSI codes)
            width: Total width of the box
            padding: Space padding inside borders
            colored: Whether to apply border colors

        Returns:
            Formatted content line with borders
        """
        import re

        border_color = cls.BORDER_COLOR if colored else ""
        reset = cls.RESET if colored else ""

        # Calculate content length without ANSI codes
        content_len = len(re.sub(r'\033\[[0-9;]+m', '', content))

        # Calculate padding needed
        inner_width = width - 2 - (padding * 2)
        fill = max(0, inner_width - content_len)

        return (
            f"{border_color}{cls.VERTICAL}{reset}"
            f"{' ' * padding}{content}{' ' * fill}{' ' * padding}"
            f"{border_color}{cls.VERTICAL}{reset}"
        )

    @classmethod
    def empty_line(cls, width: int = STANDARD_WIDTH, colored: bool = True) -> str:
        """Create empty line with borders.

        Args:
            width: Total width of the box
            colored: Whether to apply color styling

        Returns:
            Formatted empty line
        """
        return cls.content_line("", width=width, colored=colored)

    @classmethod
    def title_line(
        cls,
        title: str,
        width: int = STANDARD_WIDTH,
        centered: bool = True,
        colored: bool = True
    ) -> str:
        """Create a title line with proper centering and styling.

        Args:
            title: Title text
            width: Total width of the box
            centered: Whether to center the title
            colored: Whether to apply title color

        Returns:
            Formatted title line
        """
        title_color = cls.TITLE_COLOR if colored else ""
        reset = cls.RESET if colored else ""

        styled_title = f"{title_color}{title}{reset}"

        if centered:
            inner_width = width - 4  # Account for borders and padding
            title_len = len(title)
            left_pad = (inner_width - title_len) // 2
            right_pad = inner_width - title_len - left_pad
            content = f"{' ' * left_pad}{styled_title}{' ' * right_pad}"
        else:
            content = styled_title

        return cls.content_line(content, width=width, colored=colored)
