"""Key binding managers for modal dialogs."""

from prompt_toolkit.key_binding import KeyBindings


class NavigationKeyBindings:
    """Key bindings for navigation functionality."""

    @staticmethod
    def create_navigation_bindings(navigation_handler, result_handler=None):
        """Create navigation key bindings.

        Args:
            navigation_handler: Handler with go_next/go_previous methods
            result_handler: Optional handler for setting results

        Returns:
            KeyBindings instance
        """
        kb = KeyBindings()

        @kb.add("n")
        @kb.add("down")
        def _(event):
            """Next item."""
            if navigation_handler.go_next():
                event.app.invalidate()

        @kb.add("p")
        @kb.add("up")
        def _(event):
            """Previous item."""
            if navigation_handler.go_previous():
                event.app.invalidate()

        # Add exit bindings if result handler provided
        if result_handler:
            @kb.add("escape")
            @kb.add("q")
            @kb.add("c-c")
            def _(event):
                """Close."""
                result_handler("close")
                event.app.exit()

        return kb


class RulesEditorKeyBindings:
    """Key bindings for rules editor modal."""

    @staticmethod
    def create_rules_editor_bindings(rules_manager, rules_list, navigation_handler, result_handler):
        """Create key bindings for rules editor.

        Args:
            rules_manager: Approval rules manager
            rules_list: List of rules (mutable)
            navigation_handler: Navigation handler
            result_handler: Result setting handler

        Returns:
            KeyBindings instance
        """
        kb = NavigationKeyBindings.create_navigation_bindings(navigation_handler)

        @kb.add("t")
        def _(event):
            """Toggle rule enabled/disabled."""
            if navigation_handler.current_index < len(rules_list):
                rule = rules_list[navigation_handler.current_index]
                rule.enabled = not rule.enabled
                rules_manager.update_rule(rule)
                event.app.invalidate()

        @kb.add("d")
        def _(event):
            """Delete current rule."""
            if navigation_handler.current_index < len(rules_list):
                rule = rules_list[navigation_handler.current_index]
                rules_manager.remove_rule(rule.id)
                rules_list.remove(rule)

                # Update navigation
                navigation_handler.set_max_items(len(rules_list))

                if not rules_list:
                    # No more rules
                    result_handler("save")
                    event.app.exit()
                else:
                    event.app.invalidate()

        @kb.add("s")
        @kb.add("escape")
        def _(event):
            """Save and exit."""
            result_handler("save")
            event.app.exit()

        @kb.add("c-c")
        def _(event):
            """Cancel."""
            result_handler("cancel")
            event.app.exit()

        return kb