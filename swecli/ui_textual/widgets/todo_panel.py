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

    def on_mount(self) -> None:
        """Called when widget is mounted to the DOM."""
        self.refresh_display()

    def refresh_display(self) -> None:
        """Update the panel with current todos from TodoHandler.

        Shows COMPLETE todo list sorted by status:
        1. In-progress (doing) - yellow
        2. Pending (todo) - gray
        3. Completed (done) - gray with strikethrough
        """
        if not self.todo_handler:
            self.update("Todo panel not connected")
            return

        todos = list(self.todo_handler._todos.values())

        if not todos:
            self.update("[dim]No active todos[/dim]")
            self.border_title = "TODOS"
            # Auto-hide panel when no todos exist
            if self.has_class("visible"):
                self.remove_class("visible")
            return

        # Auto-show panel when todos exist
        if not self.has_class("visible"):
            self.add_class("visible")

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
