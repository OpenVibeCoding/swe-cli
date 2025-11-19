from typing import Optional
from rich.text import Text

class DisplayFormatter:
    """Formats general UI messages like errors, info, and warnings."""

    def format_error(self, primary: str, secondary: Optional[str] = None) -> Text:
        """Formats an error message."""
        text = Text.from_markup(f"  [red]⎿ {primary}[/red]")
        if secondary:
            text.append(f"\n  [dim]⎿ {secondary}[/dim]")
        return text

    def format_info(self, primary: str, secondary: Optional[str] = None) -> Text:
        """Formats an info message."""
        text = Text.from_markup(f"  ⎿ {primary}")
        if secondary:
            text.append(f"\n  ⎿ [dim]{secondary}[/dim]")
        return text

    def format_warning(self, primary: str, secondary: Optional[str] = None) -> Text:
        """Formats a warning message."""
        text = Text.from_markup(f"  [yellow]⎿ {primary}[/yellow]")
        if secondary:
            text.append(f"\n  [dim]⎿ {secondary}[/dim]")
        return text
