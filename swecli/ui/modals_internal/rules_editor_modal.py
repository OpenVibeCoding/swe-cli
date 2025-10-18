"""Rules editor modal for managing approval rules."""

from typing import Optional, List, Tuple
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window, WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

from swecli.core.approval import ApprovalRule, ApprovalRulesManager, RuleAction, RuleType


class RulesEditorModal:
    """Modal for editing approval rules."""

    def __init__(self, rules_manager: ApprovalRulesManager):
        """Initialize rules editor.

        Args:
            rules_manager: Rules manager instance
        """
        self.rules_manager = rules_manager
        self.current_index = 0
        self.result: Optional[str] = None  # "save" or "cancel"

    def _create_editor_key_bindings(self, kb: KeyBindings, rules: List) -> None:
        """Create key bindings for rules editor."""
        @kb.add("n")
        def _(event):
            """Next rule."""
            if self.current_index < len(rules) - 1:
                self.current_index += 1
                event.app.invalidate()

        @kb.add("p")
        def _(event):
            """Previous rule."""
            if self.current_index > 0:
                self.current_index -= 1
                event.app.invalidate()

        @kb.add("t")
        def _(event):
            """Toggle rule enabled/disabled."""
            rule = rules[self.current_index]
            rule.enabled = not rule.enabled
            self.rules_manager.update_rule(rule)
            event.app.invalidate()

        @kb.add("d")
        def _(event):
            """Delete current rule."""
            rule = rules[self.current_index]
            self.rules_manager.remove_rule(rule.id)
            # Refresh rules list
            rules.remove(rule)
            if self.current_index >= len(rules):
                self.current_index = max(0, len(rules) - 1)
            if not rules:
                # No more rules
                self.result = "save"
                event.app.exit()
            event.app.invalidate()

        @kb.add("s")
        @kb.add("escape")
        def _(event):
            """Save and exit."""
            self.result = "save"
            event.app.exit()

        @kb.add("c-c")
        def _(event):
            """Cancel."""
            self.result = "cancel"
            event.app.exit()

    def _get_editor_header(self, rules: List) -> FormattedText:
        """Generate header for rules editor."""
        if not rules:
            return FormattedText([("class:title", "No rules to display")])
        return FormattedText([
            ("class:box-border", "╭─ "),
            ("class:title", f"Approval Rules Editor ({self.current_index + 1}/{len(rules)})"),
            ("class:box-border", " ─╮\n"),
        ])

    def _get_rule_display(self, rules: List) -> FormattedText:
        """Generate rule display for current rule."""
        if not rules:
            return FormattedText([])

        rule = rules[self.current_index]
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
            ("class:box-border", "│ "),
            ("class:label", "Pattern: "),
            ("class:pattern", rule.pattern),
            ("class:box-border", "\n│ \n"),
            ("class:box-border", "│ "),
            ("class:label", "Action: "),
            ("class:action", rule.action.value.replace("_", " ").title()),
            ("class:box-border", "\n│ "),
            ("class:box-border", "│ "),
            ("class:label", "Priority: "),
            ("class:text", str(rule.priority)),
            ("class:box-border", "\n│ \n"),
            ("class:box-border", "╰─────────────────────────────────────────╯\n"),
        ])

    def _get_editor_footer(self, rules: List) -> FormattedText:
        """Generate footer for rules editor."""
        options = [
            ("class:option", "  t. "),
            ("class:text", "Toggle enabled/disabled\n"),
            ("class:option", "  d. "),
            ("class:text", "Delete this rule\n"),
        ]

        if len(rules) > 1:
            if self.current_index > 0:
                options.insert(0, ("class:option", "  p. "))
                options.insert(1, ("class:text", "Previous rule\n"))
            if self.current_index < len(rules) - 1:
                options.insert(0, ("class:option", "  n. "))
                options.insert(1, ("class:text", "Next rule\n"))

        options.extend([
            ("class:option", "  s/ESC. "),
            ("class:text", "Save and exit\n"),
        ])

        return FormattedText(options)

    def _create_editor_style(self) -> Style:
        """Create style for rules editor."""
        return Style.from_dict({
            "box-border": "#ffaa00",
            "title": "#ffaa00 bold",
            "label": "bold",
            "text": "",
            "pattern": "#00d7ff",
            "action": "#00ff00",
            "enabled": "#00ff00 bold",
            "disabled": "#ff0000 bold",
            "option": "#00d7ff bold",
        })

    def _create_editor_layout(self, rules: List) -> Layout:
        """Create layout for rules editor."""
        return Layout(
            HSplit([
                Window(
                    content=FormattedTextControl(lambda: self._get_editor_header(rules)),
                    dont_extend_height=True,
                ),
                Window(
                    content=FormattedTextControl(lambda: self._get_rule_display(rules)),
                    dont_extend_height=True,
                ),
                Window(height=1),
                Window(
                    content=FormattedTextControl(lambda: self._get_editor_footer(rules)),
                    dont_extend_height=True,
                ),
            ])
        )

    def show(self) -> str:
        """Show rules editor modal.

        Returns:
            "save" if user saved changes, "cancel" if cancelled
        """
        self.result = None

        # Get all rules sorted by priority
        rules = sorted(self.rules_manager.rules, key=lambda r: r.priority, reverse=True)

        if not rules:
            # No rules to display
            return "cancel"

        # Create key bindings
        kb = KeyBindings()
        self._create_editor_key_bindings(kb, rules)

        # Create application
        app = Application(
            layout=self._create_editor_layout(rules),
            key_bindings=kb,
            style=self._create_editor_style(),
            full_screen=False,
            mouse_support=False,
        )

        # Run the application
        app.run()

        return self.result or "cancel"


class RulesHistoryModal:
    """Modal for viewing command history."""

    def __init__(self, rules_manager: ApprovalRulesManager, limit: int = 50):
        """Initialize history modal.

        Args:
            rules_manager: Rules manager instance
            limit: Maximum number of history entries to show
        """
        self.rules_manager = rules_manager
        self.limit = limit
        self.current_index = 0
        self.result: Optional[str] = None

    def _create_history_key_bindings(self, kb: KeyBindings, history: List) -> None:
        """Create key bindings for history viewer."""
        @kb.add("n")
        @kb.add("down")
        def _(event):
            """Next entry."""
            if self.current_index < len(history) - 1:
                self.current_index += 1
                event.app.invalidate()

        @kb.add("p")
        @kb.add("up")
        def _(event):
            """Previous entry."""
            if self.current_index > 0:
                self.current_index -= 1
                event.app.invalidate()

        @kb.add("escape")
        @kb.add("q")
        @kb.add("c-c")
        def _(event):
            """Close."""
            self.result = "close"
            event.app.exit()

    def _get_history_header(self, history: List) -> FormattedText:
        """Generate header for history viewer."""
        return FormattedText([
            ("class:box-border", "╭─ "),
            ("class:title", f"Command History ({self.current_index + 1}/{len(history)})"),
            ("class:box-border", " ─╮\n"),
        ])

    def _get_history_display(self, history: List) -> FormattedText:
        """Generate display for current history entry."""
        entry = history[self.current_index]
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

    def _get_history_footer(self) -> FormattedText:
        """Generate footer for history viewer."""
        return FormattedText([
            ("class:option", "  n/↓. "),
            ("class:text", "Next entry\n"),
            ("class:option", "  p/↑. "),
            ("class:text", "Previous entry\n"),
            ("class:option", "  q/ESC. "),
            ("class:text", "Close\n"),
        ])

    def _create_history_style(self) -> Style:
        """Create style for history viewer."""
        return Style.from_dict({
            "box-border": "#ffaa00",
            "title": "#ffaa00 bold",
            "label": "bold",
            "text": "",
            "command": "#00d7ff",
            "approved": "#00ff00 bold",
            "denied": "#ff0000 bold",
            "option": "#00d7ff bold",
        })

    def _create_history_layout(self, history: List) -> Layout:
        """Create layout for history viewer."""
        return Layout(
            HSplit([
                Window(
                    content=FormattedTextControl(lambda: self._get_history_header(history)),
                    dont_extend_height=True,
                ),
                Window(
                    content=FormattedTextControl(lambda: self._get_history_display(history)),
                    dont_extend_height=True,
                ),
                Window(height=1),
                Window(
                    content=FormattedTextControl(self._get_history_footer),
                    dont_extend_height=True,
                ),
            ])
        )

    def show(self) -> str:
        """Show history modal.

        Returns:
            "close" when user closes the modal
        """
        self.result = None

        # Get history
        history = self.rules_manager.get_history(self.limit)

        if not history:
            # No history to display
            return "close"

        # Create key bindings
        kb = KeyBindings()
        self._create_history_key_bindings(kb, history)

        # Create application
        app = Application(
            layout=self._create_history_layout(history),
            key_bindings=kb,
            style=self._create_history_style(),
            full_screen=False,
            mouse_support=False,
        )

        # Run the application
        app.run()

        return self.result or "close"


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
