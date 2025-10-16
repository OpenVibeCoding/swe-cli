"""Style definitions for modal dialogs."""

from prompt_toolkit.styles import Style


class ModalStyles:
    """Style definitions for modals."""

    @staticmethod
    def get_rules_editor_style() -> Style:
        """Get style for rules editor modal.

        Returns:
            Style instance
        """
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

    @staticmethod
    def get_history_viewer_style() -> Style:
        """Get style for history viewer modal.

        Returns:
            Style instance
        """
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