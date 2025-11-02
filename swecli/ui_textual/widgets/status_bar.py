"""Status bar and footer widgets for the SWE-CLI Textual UI."""

from __future__ import annotations

from typing import Mapping

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Footer, Static


class StatusBar(Static):
    """Custom status bar showing mode, context, and hints."""

    def __init__(self, model: str = "claude-sonnet-4", **kwargs):
        super().__init__(**kwargs)
        self.mode = "normal"
        self.context_pct = 0
        self.model = model
        self.spinner_text: str | None = None
        self.spinner_tip: str | None = None

    def on_mount(self) -> None:
        """Update status on mount."""
        self.update_status()

    def set_mode(self, mode: str) -> None:
        """Update mode display."""
        self.mode = mode
        self.update_status()

    def set_context(self, pct: int) -> None:
        """Update context percentage."""
        self.context_pct = pct
        self.update_status()

    def set_model_name(self, model: str) -> None:
        """Update the displayed model name."""
        self.model = model
        self.update_status()

    def set_spinner(self, text: str, tip: str | None = None) -> None:
        """Display spinner status."""
        self.spinner_text = text
        if tip is not None:
            self.spinner_tip = tip
        self.update_status()

    def clear_spinner(self) -> None:
        """Clear spinner status."""
        self.spinner_text = None
        self.spinner_tip = None
        self.update_status()

    def update_status(self) -> None:
        """Update status bar text - clean and professional."""
        mode_color = "#4a9eff" if self.mode == "normal" else "#89d185"
        status = Text()

        status.append(f"{self.mode.upper()}", style=f"bold {mode_color}")
        status.append("  │  ", style="#6a6a6a")

        status.append(f"Context {self.context_pct}%", style="#808080")
        status.append("  │  ", style="#6a6a6a")

        model_display = self._smart_truncate_model(self.model, 60)
        status.append(model_display, style="#007acc")

        if self.spinner_text:
            status.append("  │  ", style="#6a6a6a")
            status.append(self.spinner_text, style="#4a9eff")
            if self.spinner_tip:
                status.append(" ", style="dim")
                status.append(self.spinner_tip, style="#6a6a6a")

        status.append("  │  ", style="#6a6a6a")
        status.append("^C quit", style="#6a6a6a")

        self.update(status)

    def _smart_truncate_model(self, model: str, max_len: int) -> str:
        """Smart model name truncation that preserves important parts."""
        if len(model) <= max_len:
            return model

        if "/" in model:
            parts = model.split("/")
            if len(parts) >= 2:
                provider = parts[0]
                model_name = parts[-1]
                simplified = f"{provider}/{model_name}"
                if len(simplified) <= max_len:
                    return simplified
                available = max_len - len(provider) - 1
                if available > 10:
                    return f"{provider}/{model_name[: available - 3]}..."

        return model[: max_len - 3] + "..."


class ModelFooter(Footer):
    """Footer variant that shows configured model slots alongside key hints."""

    def __init__(
        self,
        model_slots: Mapping[str, tuple[str, str]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._model_slots: dict[str, tuple[str, str]] = dict(model_slots or {})
        self._models_label: Static | None = None

    def compose(self) -> ComposeResult:
        """Compose footer with model display prefix and inherited key hints."""
        self._models_label = Static(
            self._build_model_text(),
            classes="footer--models",
            expand=True,
        )
        yield self._models_label

        parent_compose = super().compose()
        if parent_compose is not None:
            yield from parent_compose

    def update_models(self, model_slots: Mapping[str, tuple[str, str]] | None) -> None:
        """Refresh displayed models."""
        self._model_slots = dict(model_slots or {})
        if self._models_label is not None:
            self._models_label.update(self._build_model_text())

    def _build_model_text(self) -> Text:
        """Create Rich text describing configured model slots."""
        base_style = "#6a6a6a"
        thinking_style = "#FFD700"
        vision_style = "#00CED1"

        text = Text(no_wrap=True)

        thinking_slot = self._model_slots.get("thinking")
        vision_slot = self._model_slots.get("vision")

        def append_slot(label: str, slot: tuple[str, str] | None, style: str) -> None:
            text.append(f"{label}: ", style=base_style)
            if slot:
                provider, model_name = slot
                provider = provider or ""
                model_name = model_name or ""
                display = model_name
                if provider:
                    if model_name:
                        if not model_name.lower().startswith(provider.lower()):
                            display = f"{provider}/{model_name}"
                    else:
                        display = provider
                text.append(display, style=style)
            else:
                text.append("Not set", style="italic #5a5a5a")

        append_slot("Thinking", thinking_slot, thinking_style)
        text.append("  |  ", style=base_style)
        append_slot("Vision", vision_slot, vision_style)

        return text


__all__ = ["StatusBar", "ModelFooter"]
