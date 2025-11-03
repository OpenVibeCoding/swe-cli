"""Helpers for rendering the welcome panel inside the conversation log."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from swecli.core.management import OperationMode
from swecli.ui.components.welcome import WelcomeMessage


def render_welcome_panel(
    conversation,
    *,
    real_integration: bool,
    working_dir: Optional[Path] = None,
    username: Optional[str] = None,
    current_mode: OperationMode = OperationMode.NORMAL,
) -> None:
    """Render a welcome panel tailored for either real or POC integrations."""

    if real_integration:
        resolved_working_dir = working_dir or Path.cwd()
        resolved_username = username or os.getenv("USER", "Developer")

        welcome_lines = WelcomeMessage.generate_full_welcome(
            current_mode=current_mode,
            working_dir=resolved_working_dir,
            username=resolved_username,
        )

        for line in welcome_lines:
            conversation.write(Text.from_ansi(line))

    else:
        heading = Text("SWE-CLI (Preview)", style="bold bright_cyan")
        subheading = Text("Textual POC interface", style="dim")
        body = Text(
            "Use this playground to explore the upcoming Textual UI.\n"
            "Core flows are stubbed; use /help, /demo, or /scroll to interact."
        )

        shortcuts = Text()
        shortcuts.append("Enter", style="bold green")
        shortcuts.append(" send   •   ")
        shortcuts.append("Shift+Enter", style="bold green")
        shortcuts.append(" new line   •   ")
        shortcuts.append("/help", style="bold cyan")
        shortcuts.append(" commands")

        content = Text.assemble(
            heading,
            "\n",
            subheading,
            "\n\n",
            body,
            "\n\n",
            shortcuts,
        )

        panel = Panel(
            Align.center(content, vertical="middle"),
            border_style="bright_cyan",
            padding=(1, 3),
            title="Welcome",
            subtitle="swecli-textual",
            subtitle_align="left",
            width=78,
        )

        conversation.write(panel)

    conversation.add_system_message("")
