"""Rules editor modal for managing approval rules."""

from swecli.core.approval import ApprovalRulesManager

from .modals_internal.rules_editor_refactored import (
    RulesEditorModal as RefactoredRulesEditorModal,
    RulesHistoryModal as RefactoredRulesHistoryModal,
    show_rules_editor as refactored_show_rules_editor,
    show_history_viewer as refactored_show_history_viewer,
)


# Backward compatibility - use refactored implementations
class RulesEditorModal(RefactoredRulesEditorModal):
    """Modal for editing approval rules."""

    def __init__(self, rules_manager: ApprovalRulesManager):
        """Initialize rules editor.

        Args:
            rules_manager: Rules manager instance
        """
        super().__init__(rules_manager)


class RulesHistoryModal(RefactoredRulesHistoryModal):
    """Modal for viewing command history."""

    def __init__(self, rules_manager: ApprovalRulesManager, limit: int = 50):
        """Initialize history modal.

        Args:
            rules_manager: Rules manager instance
            limit: Maximum number of history entries to show
        """
        super().__init__(rules_manager, limit)


# Backward compatibility functions
def show_rules_editor(rules_manager: ApprovalRulesManager) -> str:
    """Show rules editor modal.

    Args:
        rules_manager: Rules manager instance

    Returns:
        Result string
    """
    return refactored_show_rules_editor(rules_manager)


def show_history_viewer(rules_manager: ApprovalRulesManager, limit: int = 50) -> str:
    """Show history viewer modal.

    Args:
        rules_manager: Rules manager instance
        limit: Maximum number of entries to show

    Returns:
        Result string
    """
    return refactored_show_history_viewer(rules_manager, limit)