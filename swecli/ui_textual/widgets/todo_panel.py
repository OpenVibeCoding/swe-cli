"""Todo panel widget for displaying persistent todo list."""

from textual.widgets import Static
from rich.table import Table
from rich.text import Text


class TodoPanel(Static):
    """Persistent todo panel showing all todos with status indicators.

    Displays the complete todo list with:
    - Active todos (yellow ▶)
    - Pending todos (gray ○)
    - Completed todos (gray ✓ with strikethrough)

    Toggle visibility with Ctrl+T.
    """

    def __init__(self, todo_handler=None, **kwargs):
        """Initialize the todo panel.

        Args:
            todo_handler: TodoHandler instance for accessing todo state
            **kwargs: Additional widget kwargs
        """
        super().__init__(**kwargs)
        self.todo_handler = todo_handler
        self.border_title = "TODOS"
        self.is_expanded = False  # Track collapsed/expanded state

    def on_mount(self) -> None:
        """Called when widget is mounted to the DOM."""
        self.refresh_display()

    def refresh_display(self) -> None:
        """Update the panel with current todos, respecting collapsed/expanded state.

        Shows collapsed summary or full list depending on is_expanded state.
        Auto-shows panel in collapsed state when todos are created.
        """
        if not self.todo_handler:
            self.update("Todo panel not connected")
            return

        todos = list(self.todo_handler._todos.values())

        if not todos:
            self.update("[dim]No active todos[/dim]")
            self.border_title = "TODOS"
            # Hide completely when no todos
            if self.has_class("collapsed"):
                self.remove_class("collapsed")
            if self.has_class("expanded"):
                self.remove_class("expanded")
            return

        # Auto-show in collapsed state when todos are created
        if not self.has_class("collapsed") and not self.has_class("expanded"):
            self.add_class("collapsed")
            self.is_expanded = False

        # Render based on current state
        if self.is_expanded:
            self._render_expanded(todos)
        else:
            self._render_collapsed(todos)

    def _render_collapsed(self, todos: list) -> None:
        """Render compact summary line."""
        total = len(todos)
        doing = sum(1 for t in todos if t.status == "doing")

        # Format: "📋 4 todos (1 active) - Press Ctrl+T to expand"
        if doing > 0:
            summary = f"📋 {total} todo{'s' if total != 1 else ''} ({doing} active) - Press Ctrl+T to expand"
        else:
            summary = f"📋 {total} todo{'s' if total != 1 else ''} - Press Ctrl+T to expand"

        self.update(summary)
        self.border_title = ""  # No border title in collapsed mode

    def _render_expanded(self, todos: list) -> None:
        """Render full todo list with status indicators."""
        # Update border title with count
        self.border_title = f"TODOS ({len(todos)} total)"

        # Sort todos by status: doing -> todo -> done
        status_order = {"doing": 0, "todo": 1, "done": 2}
        sorted_todos = sorted(
            todos,
            key=lambda t: (status_order.get(t.status, 3), t.id)
        )

        # Build display content
        lines = []

        for todo in sorted_todos:
            if todo.status == "done":
                # Completed: gray with strikethrough
                lines.append(f"[dim]✓ [strike]{todo.title}[/strike][/dim]")
            elif todo.status == "doing":
                # In-progress: yellow
                lines.append(f"[yellow]▶ {todo.title}[/yellow]")
            else:
                # Pending: gray
                lines.append(f"[dim]○ {todo.title}[/dim]")

        # Join all lines and update display
        self.update("\n".join(lines))

    def toggle_expansion(self) -> None:
        """Toggle between collapsed and expanded states."""
        if self.is_expanded:
            # Collapse
            self.is_expanded = False
            self.remove_class("expanded")
            self.add_class("collapsed")
        else:
            # Expand
            self.is_expanded = True
            self.remove_class("collapsed")
            self.add_class("expanded")

        self.refresh_display()
