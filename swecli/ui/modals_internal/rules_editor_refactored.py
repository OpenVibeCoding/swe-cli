"""Refactored rules editor modal using modular components."""

from typing import List

from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from swecli.core.approval import ApprovalRulesManager, ApprovalRule

from .base import BaseModal, NavigationMixin
from .styles import ModalStyles
from .layout_builders import HeaderBuilder, FooterBuilder, LayoutBuilder
from .display_formatters import RuleDisplayFormatter
from .key_bindings import RulesEditorKeyBindings


class RulesEditorModal(BaseModal, NavigationMixin):
    """Modal for editing approval rules using modular components."""

    def __init__(self, rules_manager: ApprovalRulesManager):
        """Initialize rules editor.

        Args:
            rules_manager: Rules manager instance
        """
        BaseModal.__init__(self)
        NavigationMixin.__init__(self, 0)  # Will be updated when rules are loaded

        self.rules_manager = rules_manager
        self.rules: List[ApprovalRule] = []

    def show(self) -> str:
        """Show rules editor modal.

        Returns:
            "save" if user saved changes, "cancel" if cancelled
        """
        # Load rules sorted by priority
        self.rules = sorted(self.rules_manager.rules, key=lambda r: r.priority, reverse=True)
        self.set_max_items(len(self.rules))

        if not self.rules:
            return "cancel"

        return super().show()

    def create_layout(self) -> Layout:
        """Create the modal layout.

        Returns:
            Configured Layout instance
        """
        return LayoutBuilder.create_modal_layout(
            self._get_header,
            self._get_rule_display,
            self._get_footer
        )

    def create_style(self) -> Style:
        """Create the modal style.

        Returns:
            Configured Style instance
        """
        return ModalStyles.get_rules_editor_style()

    def create_key_bindings(self) -> KeyBindings:
        """Create key bindings for the modal.

        Returns:
            KeyBindings instance
        """
        def set_result(result: str) -> None:
            self.result = result

        return RulesEditorKeyBindings.create_rules_editor_bindings(
            self.rules_manager,
            self.rules,
            self,
            set_result
        )

    def get_default_result(self) -> str:
        """Get default result if modal is closed without explicit action.

        Returns:
            Default result string
        """
        return "cancel"

    def _get_header(self):
        """Generate header."""
        return HeaderBuilder.create_rules_editor_header(
            self.current_index, len(self.rules)
        )

    def _get_rule_display(self):
        """Generate rule display."""
        if not self.rules:
            from prompt_toolkit.formatted_text import FormattedText
            return FormattedText([])

        rule = self.rules[self.current_index]
        return RuleDisplayFormatter.format_rule_display(rule)

    def _get_footer(self):
        """Generate footer."""
        return FooterBuilder.create_rules_editor_footer(
            self.current_index,
            len(self.rules),
            self.can_go_next(),
            self.can_go_previous()
        )


class RulesHistoryModal(BaseModal, NavigationMixin):
    """Modal for viewing command history using modular components."""

    def __init__(self, rules_manager: ApprovalRulesManager, limit: int = 50):
        """Initialize history modal.

        Args:
            rules_manager: Rules manager instance
            limit: Maximum number of history entries to show
        """
        BaseModal.__init__(self)
        NavigationMixin.__init__(self, 0)  # Will be updated when history is loaded

        self.rules_manager = rules_manager
        self.limit = limit
        self.history = []

    def show(self) -> str:
        """Show history modal.

        Returns:
            "close" when user closes the modal
        """
        # Load history
        self.history = self.rules_manager.get_history(self.limit)
        self.set_max_items(len(self.history))

        if not self.history:
            return "close"

        return super().show()

    def create_layout(self) -> Layout:
        """Create the modal layout.

        Returns:
            Configured Layout instance
        """
        return LayoutBuilder.create_modal_layout(
            self._get_header,
            self._get_history_display,
            self._get_footer
        )

    def create_style(self) -> Style:
        """Create the modal style.

        Returns:
            Configured Style instance
        """
        return ModalStyles.get_history_viewer_style()

    def create_key_bindings(self) -> KeyBindings:
        """Create key bindings for the modal.

        Returns:
            KeyBindings instance
        """
        def set_result(result: str) -> None:
            self.result = result

        from .key_bindings import NavigationKeyBindings
        return NavigationKeyBindings.create_navigation_bindings(
            self, set_result
        )

    def get_default_result(self) -> str:
        """Get default result if modal is closed without explicit action.

        Returns:
            Default result string
        """
        return "close"

    def _get_header(self):
        """Generate header."""
        return HeaderBuilder.create_history_viewer_header(
            self.current_index, len(self.history)
        )

    def _get_history_display(self):
        """Generate history display."""
        if not self.history:
            from prompt_toolkit.formatted_text import FormattedText
            return FormattedText([])

        entry = self.history[self.current_index]
        from .display_formatters import HistoryDisplayFormatter
        return HistoryDisplayFormatter.format_history_display(entry)

    def _get_footer(self):
        """Generate footer."""
        return FooterBuilder.create_history_viewer_footer()


# Backward compatibility functions
def show_rules_editor(rules_manager: ApprovalRulesManager) -> str:
    """Show rules editor modal.

    Args:
        rules_manager: Rules manager instance

    Returns:
        Result string
    """
    modal = RulesEditorModal(rules_manager)
    return modal.show()


def show_history_viewer(rules_manager: ApprovalRulesManager, limit: int = 50) -> str:
    """Show history viewer modal.

    Args:
        rules_manager: Rules manager instance
        limit: Maximum number of entries to show

    Returns:
        Result string
    """
    modal = RulesHistoryModal(rules_manager, limit)
    return modal.show()