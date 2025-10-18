"""Status line component for SWE-CLI."""

from pathlib import Path
from typing import List, Optional, Sequence, Tuple
import subprocess
from rich.console import Console
from rich.text import Text


class StatusLine:
    """Bottom status line showing context info."""

    def __init__(self, console: Console):
        """Initialize status line.

        Args:
            console: Rich console for output
        """
        self.console = console
        self._detailed = False

    def render(
        self,
        model: str,
        working_dir: Path,
        tokens_used: int,
        tokens_limit: int,
        git_branch: Optional[str] = None,
        mode: Optional[str] = None,
        latency_ms: Optional[int] = None,
        key_hints: Optional[Sequence[Tuple[str, str]]] = None,
        notifications: Optional[Sequence[str]] = None,
    ) -> None:
        """Render status line at bottom.

        Args:
            model: Model name
            working_dir: Current working directory
            tokens_used: Tokens used in session
            tokens_limit: Token limit
            git_branch: Git branch name (if in repo)
            mode: Current operation mode label
            latency_ms: Milliseconds elapsed on last model call
            key_hints: Shortcut hints to surface inline
            notifications: Recent notification summaries to surface inline
        """
        return

    def _truncate_model(self, model: str, max_len: int = 25) -> str:
        """Truncate model name if too long.

        Args:
            model: Full model name
            max_len: Maximum length

        Returns:
            Truncated model name
        """
        if len(model) <= max_len:
            return model

        # Try to keep the important part
        if "/" in model:
            parts = model.split("/")
            model_name = parts[-1]
            if len(model_name) <= max_len:
                return model_name

        # Truncate with ellipsis
        return model[:max_len-1] + "…"

    def _smart_path(self, path: Path, max_len: int = 30) -> str:
        """Smart path display.

        Args:
            path: Path to display
            max_len: Maximum length

        Returns:
            Formatted path
        """
        path_str = str(path)

        # Replace home with ~
        home = str(Path.home())
        if path_str.startswith(home):
            path_str = "~" + path_str[len(home):]

        # Truncate if too long
        if len(path_str) > max_len:
            # Show start and end
            start_len = max_len // 2 - 2
            end_len = max_len // 2 - 2
            path_str = path_str[:start_len] + "..." + path_str[-end_len:]

        return path_str

    def _get_git_branch(self, working_dir: Path) -> Optional[str]:
        """Get current git branch.

        Args:
            working_dir: Working directory

        Returns:
            Branch name or None
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _format_tokens(self, used: int, limit: int) -> Text:
        """Format token usage with color coding.

        Args:
            used: Tokens used
            limit: Token limit

        Returns:
            Formatted token string
        """
        # Format numbers with K suffix
        def format_num(n: int) -> str:
            if n >= 1000:
                return f"{n/1000:.1f}k"
            return str(n)

        usage_pct = (used / limit * 100) if limit > 0 else 0

        # Color code based on usage
        if usage_pct > 90:
            status = "critical"
        elif usage_pct > 80:
            status = "warning"
        else:
            status = "normal"

        label = f"{format_num(used)}/{format_num(limit)}"
        text = Text(label)
        if status == "critical":
            text.stylize("bold red")
        elif status == "warning":
            text.stylize("yellow")
        else:
            text.stylize("green")
        return text

    def toggle_detailed(self) -> bool:
        """Toggle detailed mode.

        Returns:
            bool: True when detailed mode enabled
        """
        self._detailed = not self._detailed
        return self._detailed
