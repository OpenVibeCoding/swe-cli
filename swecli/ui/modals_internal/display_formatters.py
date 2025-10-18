"""Display formatters for modal content."""

from prompt_toolkit.formatted_text import FormattedText

from swecli.core.approval import ApprovalRule, CommandHistory


class RuleDisplayFormatter:
    """Formatter for displaying approval rules."""

    @staticmethod
    def format_rule_display(rule: ApprovalRule) -> FormattedText:
        """Format a rule for display.

        Args:
            rule: Approval rule to format

        Returns:
            Formatted text for rule display
        """
        status = "[ENABLED]" if rule.enabled else "[DISABLED]"
        status_class = "enabled" if rule.enabled else "disabled"

        return FormattedText([
            ("class:box-border", "│ \n"),
            ("class:box-border", "│ "),
            ("class:label", "Name: "),
            ("class:text", rule.name),
            ("class:box-border", "\n│ "),
            ("class:label", "Status: "),
            (f"class:{status_class}", status),
            ("class:box-border", "\n│ \n"),
            ("class:box-border", "│ "),
            ("class:label", "Description: "),
            ("class:text", rule.description),
            ("class:box-border", "\n│ \n"),
            ("class:box-border", "│ "),
            ("class:label", "Type: "),
            ("class:text", rule.rule_type.value.replace("_", " ").title()),
            ("class:box-border", "\n│ "),
            ("class:label", "Pattern: "),
            ("class:pattern", rule.pattern),
            ("class:box-border", "\n│ \n"),
            ("class:box-border", "│ "),
            ("class:label", "Action: "),
            ("class:action", rule.action.value.replace("_", " ").title()),
            ("class:box-border", "\n│ "),
            ("class:label", "Priority: "),
            ("class:text", str(rule.priority)),
            ("class:box-border", "\n│ \n"),
            ("class:box-border", "╰─────────────────────────────────────────╯\n"),
        ])


class HistoryDisplayFormatter:
    """Formatter for displaying history entries."""

    @staticmethod
    def format_history_display(entry: CommandHistory) -> FormattedText:
        """Format a history entry for display.

        Args:
            entry: CommandHistory entry to format

        Returns:
            Formatted text for history display
        """
        status = "APPROVED" if entry.approved else "DENIED"
        status_class = "approved" if entry.approved else "denied"

        result = [
            ("class:box-border", "│ \n"),
            ("class:box-border", "│ "),
            ("class:label", "Command: "),
            ("class:command", entry.command),
            ("class:box-border", "\n│ \n"),
            ("class:box-border", "│ "),
            ("class:label", "Status: "),
            (f"class:{status_class}", status),
            ("class:box-border", "\n│ \n"),
        ]

        if entry.edited_command:
            result.extend([
                ("class:box-border", "│ "),
                ("class:label", "Edited to: "),
                ("class:command", entry.edited_command),
                ("class:box-border", "\n│ \n"),
            ])

        if entry.rule_matched:
            result.extend([
                ("class:box-border", "│ "),
                ("class:label", "Rule matched: "),
                ("class:text", entry.rule_matched),
                ("class:box-border", "\n│ \n"),
            ])

        if entry.timestamp:
            result.extend([
                ("class:box-border", "│ "),
                ("class:label", "Time: "),
                ("class:text", entry.timestamp),
                ("class:box-border", "\n│ \n"),
            ])

        result.append(("class:box-border", "╰─────────────────────────────────────────╯\n"))

        return FormattedText(result)