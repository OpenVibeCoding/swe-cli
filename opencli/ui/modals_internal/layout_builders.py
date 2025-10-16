"""Layout builders for modal dialogs."""

from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl


class HeaderBuilder:
    """Builder for modal headers."""

    @staticmethod
    def create_rules_editor_header(current_index: int, total_rules: int) -> FormattedText:
        """Create header for rules editor modal.

        Args:
            current_index: Current rule index
            total_rules: Total number of rules

        Returns:
            Formatted text for header
        """
        if total_rules == 0:
            return FormattedText([("class:title", "No rules to display")])

        return FormattedText([
            ("class:box-border", "╭─ "),
            ("class:title", f"Approval Rules Editor ({current_index + 1}/{total_rules})"),
            ("class:box-border", " ─╮\n"),
        ])

    @staticmethod
    def create_history_viewer_header(current_index: int, total_entries: int) -> FormattedText:
        """Create header for history viewer modal.

        Args:
            current_index: Current entry index
            total_entries: Total number of entries

        Returns:
            Formatted text for header
        """
        return FormattedText([
            ("class:box-border", "╭─ "),
            ("class:title", f"Command History ({current_index + 1}/{total_entries})"),
            ("class:box-border", " ─╮\n"),
        ])


class FooterBuilder:
    """Builder for modal footers."""

    @staticmethod
    def create_rules_editor_footer(
        current_index: int, total_rules: int, can_go_next: bool, can_go_previous: bool
    ) -> FormattedText:
        """Create footer for rules editor modal.

        Args:
            current_index: Current rule index
            total_rules: Total number of rules
            can_go_next: Whether next rule is available
            can_go_previous: Whether previous rule is available

        Returns:
            Formatted text for footer
        """
        options = [
            ("class:option", "  t. "),
            ("class:text", "Toggle enabled/disabled\n"),
            ("class:option", "  d. "),
            ("class:text", "Delete this rule\n"),
        ]

        if total_rules > 1:
            if can_go_previous:
                options.insert(0, ("class:option", "  p. "))
                options.insert(1, ("class:text", "Previous rule\n"))
            if can_go_next:
                options.insert(0, ("class:option", "  n. "))
                options.insert(1, ("class:text", "Next rule\n"))

        options.extend([
            ("class:option", "  s/ESC. "),
            ("class:text", "Save and exit\n"),
        ])

        return FormattedText(options)

    @staticmethod
    def create_history_viewer_footer() -> FormattedText:
        """Create footer for history viewer modal.

        Returns:
            Formatted text for footer
        """
        options = [
            ("class:option", "  n/↓. "),
            ("class:text", "Next entry\n"),
            ("class:option", "  p/↑. "),
            ("class:text", "Previous entry\n"),
            ("class:option", "  q/ESC. "),
            ("class:text", "Close\n"),
        ]

        return FormattedText(options)


class LayoutBuilder:
    """Builder for complete modal layouts."""

    @staticmethod
    def create_modal_layout(header_func, content_func, footer_func) -> HSplit:
        """Create a standard modal layout.

        Args:
            header_func: Function that returns header content
            content_func: Function that returns main content
            footer_func: Function that returns footer content

        Returns:
            HSplit layout container
        """
        return HSplit([
            Window(
                content=FormattedTextControl(header_func),
                dont_extend_height=True,
            ),
            Window(
                content=FormattedTextControl(content_func),
                dont_extend_height=True,
            ),
            Window(height=1),
            Window(
                content=FormattedTextControl(footer_func),
                dont_extend_height=True,
            ),
        ])