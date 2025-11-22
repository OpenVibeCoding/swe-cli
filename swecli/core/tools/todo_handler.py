"""Todo/Task management handler for tracking development tasks."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


@dataclass
class TodoItem:
    """A todo/task item."""

    id: str
    title: str
    status: str  # "todo", "doing", or "done"
    log: str = ""
    expanded: bool = False
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


class TodoHandler:
    """Handler for todo/task management operations."""

    def __init__(self):
        """Initialize todo handler with in-memory storage."""
        self._todos: Dict[str, TodoItem] = {}
        self._next_id = 1

    def write_todos(self, todos: List[str] | List[dict]) -> dict:
        """Create multiple todo items in a single call.

        Supports both formats:
        - List[str]: Simple string list ["Task 1", "Task 2"]
        - List[dict]: Deep Agent format [{"content": "Task 1", "status": "pending"}]

        Args:
            todos: List of todo titles/descriptions (str) or todo objects (dict)

        Returns:
            Result dict with success status and summary
        """
        if not todos:
            return {
                "success": False,
                "error": "No todos provided. 'todos' parameter must be a non-empty list.",
                "output": None,
            }

        if not isinstance(todos, list):
            return {
                "success": False,
                "error": f"'todos' must be a list. Got {type(todos).__name__}.",
                "output": None,
            }

        # Normalize to string list
        # Handle both List[str] and List[dict] formats (Deep Agent compatibility)
        normalized_todos = []
        for item in todos:
            if isinstance(item, str):
                normalized_todos.append(item)
            elif isinstance(item, dict):
                # Extract 'content' and 'status' fields from Deep Agent's todo dict format
                content = item.get("content", "")
                status = item.get("status", "pending")
                if content:
                    # Map Deep Agent status to internal status
                    status_mapping = {
                        "pending": "todo",
                        "in_progress": "doing",
                        "completed": "done",
                        "todo": "todo",
                        "doing": "doing",
                        "done": "done"
                    }
                    mapped_status = status_mapping.get(status, "todo")
                    # Store as tuple to preserve status information
                    normalized_todos.append((content, mapped_status))
            else:
                # Skip invalid items
                continue

        if not normalized_todos:
            return {
                "success": False,
                "error": "No valid todos found in the list.",
                "output": None,
            }

        todos = normalized_todos

        # Clear existing todos - write_todos replaces the entire list
        self._todos.clear()
        self._next_id = 1

        # Create all todos
        results = []
        created_count = 0
        failed_count = 0
        created_ids = []

        for i, todo_item in enumerate(normalized_todos, 1):
            # Handle both string and tuple formats
            if isinstance(todo_item, tuple):
                todo_text, todo_status = todo_item
            else:
                todo_text = todo_item
                todo_status = "todo"

            if not todo_text or not str(todo_text).strip():
                failed_count += 1
                results.append(f"  {i}. [SKIPPED] Empty todo")
                continue

            # Call create_todo for each item with correct status
            result = self.create_todo(title=str(todo_text).strip(), status=todo_status)

            if result.get("success"):
                todo_id = result.get("todo_id", "?")
                created_ids.append(todo_id)
                # Format with correct color and styling based on status
                if todo_status == "done":
                    results.append(f"  [dim]✓ [strike]{str(todo_text).strip()}[/strike][/dim]")
                elif todo_status == "doing":
                    results.append(f"  [yellow]▶ {str(todo_text).strip()}[/yellow]")
                else:
                    results.append(f"  [dim]○ {str(todo_text).strip()}[/dim]")
                created_count += 1
            else:
                error = result.get("error", "Unknown error")
                results.append(f"  [red]✗ {error}[/red]")
                failed_count += 1

        # Build summary
        summary_lines = [
            f"Created {created_count} todo(s) from {len(todos)} item(s):",
            "",
        ]
        summary_lines.extend(results)

        if failed_count > 0:
            summary_lines.append(f"\nWarning: {failed_count} todo(s) failed to create.")

        return {
            "success": True,
            "output": "\n".join(summary_lines),
            "created_count": created_count,
            "failed_count": failed_count,
            "todo_ids": created_ids,
        }

    def create_todo(
        self,
        title: str,
        status: str = "todo",
        log: str = "",
        expanded: bool = False,
    ) -> dict:
        """Create a new todo item.

        Args:
            title: Todo title/description
            status: Status ("todo", "doing", "done" OR "pending", "in_progress", "completed")
            log: Optional log/notes
            expanded: Whether to show expanded in UI

        Returns:
            Result dict with success status and todo ID
        """
        # Map Deep Agent statuses to internal statuses
        status_map = {
            "pending": "todo",
            "in_progress": "doing",
            "completed": "done",
        }

        # Normalize status
        normalized_status = status_map.get(status, status)

        # Validate status
        if normalized_status not in ["todo", "doing", "done"]:
            return {
                "success": False,
                "error": f"Invalid status '{status}'. Must be 'todo', 'doing', or 'done' (or 'pending', 'in_progress', 'completed').",
                "output": None,
            }

        # Create todo with Deep Agent compatible ID format
        todo_id = f"todo-{self._next_id}"
        self._next_id += 1

        todo = TodoItem(
            id=todo_id,
            title=title,
            status=normalized_status,
            log=log,
            expanded=expanded,
        )

        self._todos[todo_id] = todo

        return {
            "success": True,
            "output": f"Created todo #{todo_id}: {title}",
            "todo_id": todo_id,
            "todo": asdict(todo),
        }

    def _find_todo(self, id: str) -> tuple[Optional[str], Optional[TodoItem]]:
        """Find a todo by ID, trying multiple matching strategies.

        Deep Agent uses 0-based indexing (0, 1, 2...) while we use 1-based IDs (todo-1, todo-2, todo-3...).
        This method handles the conversion. Also supports finding by title string, kebab-case slugs, and fuzzy matching.

        Args:
            id: Todo ID in formats: "0", "1", "todo-1", exact title, kebab-case slug like "implement-basic-level"

        Returns:
            Tuple of (actual_id, todo_item) or (None, None) if not found
        """
        # Try exact match first
        if id in self._todos:
            return id, self._todos[id]

        # If numeric ID provided, convert from 0-based to 1-based then try "todo-X" format
        if id.isdigit():
            numeric_id = int(id)
            # Deep Agent uses 0-based indexing, convert to 1-based
            one_based_id = numeric_id + 1
            todo_id = f"todo-{one_based_id}"
            if todo_id in self._todos:
                return todo_id, self._todos[todo_id]

        # If "todo-X" provided, try numeric format
        if id.startswith("todo-"):
            numeric_id = id[5:]
            if numeric_id in self._todos:
                return numeric_id, self._todos[numeric_id]

        # If ":X" provided (colon format), treat as numeric 0-based index
        if id.startswith(":") and len(id) > 1:
            numeric_part = id[1:]
            if numeric_part.isdigit():
                # Convert ":1" → "todo-2" (0-based to 1-based)
                one_based_id = int(numeric_part) + 1
                todo_id = f"todo-{one_based_id}"
                if todo_id in self._todos:
                    return todo_id, self._todos[todo_id]

        # If "todo_X" provided (Deep Agent format with underscore), convert to "todo-X"
        if id.startswith("todo_"):
            numeric_part = id[5:]
            if numeric_part.isdigit():
                # Convert "todo_1" → "todo-1" (our internal format)
                internal_id = f"todo-{numeric_part}"
                if internal_id in self._todos:
                    return internal_id, self._todos[internal_id]

        # Try to find by title (case-sensitive exact match)
        for todo_id, todo in self._todos.items():
            if todo.title == id:
                return todo_id, todo

        # Try case-insensitive exact match
        id_lower = id.lower()
        for todo_id, todo in self._todos.items():
            if todo.title.lower() == id_lower:
                return todo_id, todo

        # Try kebab-case slug matching (e.g., "implement-basic-level" → "Implement basic level design...")
        # Convert kebab-case to words and try fuzzy matching
        if "-" in id:
            # Convert "implement-basic-level" → "implement basic level"
            slug_words = id.replace("-", " ").lower()
            for todo_id, todo in self._todos.items():
                title_lower = todo.title.lower()
                # Check if slug words appear at start of title
                if title_lower.startswith(slug_words):
                    return todo_id, todo
                # Check if all slug words appear in title (in order)
                if all(word in title_lower for word in slug_words.split()):
                    # Verify words appear in order
                    pos = 0
                    all_in_order = True
                    for word in slug_words.split():
                        idx = title_lower.find(word, pos)
                        if idx == -1:
                            all_in_order = False
                            break
                        pos = idx + len(word)
                    if all_in_order:
                        return todo_id, todo

        # Try partial matching - if id is contained in title
        for todo_id, todo in self._todos.items():
            if id_lower in todo.title.lower():
                return todo_id, todo

        return None, None

    def update_todo(
        self,
        id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        log: Optional[str] = None,
        expanded: Optional[bool] = None,
    ) -> dict:
        """Update an existing todo item.

        Args:
            id: Todo ID
            title: New title (optional)
            status: New status ("todo", "doing", "done" OR "pending", "in_progress", "completed") (optional)
            log: New log/notes (optional)
            expanded: New expanded state (optional)

        Returns:
            Result dict with success status
        """
        actual_id, todo = self._find_todo(id)
        if todo is None:
            return {
                "success": False,
                "error": f"Todo #{id} not found",
                "output": None,
            }

        # Update fields
        if title is not None:
            todo.title = title
        if status is not None:
            # Map Deep Agent statuses to internal statuses
            status_map = {
                "pending": "todo",
                "in_progress": "doing",
                "completed": "done",
            }

            # Normalize status
            normalized_status = status_map.get(status, status)

            if normalized_status not in ["todo", "doing", "done"]:
                return {
                    "success": False,
                    "error": f"Invalid status '{status}'. Must be 'todo', 'doing', or 'done' (or 'pending', 'in_progress', 'completed').",
                    "output": None,
                }
            todo.status = normalized_status
        if log is not None:
            todo.log = log
        if expanded is not None:
            todo.expanded = expanded

        todo.updated_at = datetime.now().isoformat()

        # Generate full todo list after update
        todo_list = self._format_todo_list_simple()
        output_lines = [f"Updated: {todo.title}", ""]
        if todo_list:
            output_lines.append("Current todos:")
            output_lines.extend(todo_list)

        return {
            "success": True,
            "output": "\n".join(output_lines),
            "todo": asdict(todo),
        }

    def complete_todo(self, id: str, log: Optional[str] = None) -> dict:
        """Mark a todo as complete.

        Args:
            id: Todo ID
            log: Optional final log entry

        Returns:
            Result dict with success status
        """
        actual_id, todo = self._find_todo(id)
        if todo is None:
            return {
                "success": False,
                "error": f"Todo #{id} not found",
                "output": None,
            }
        todo.status = "done"

        if log:
            if todo.log:
                todo.log += f"\n{log}"
            else:
                todo.log = log

        todo.updated_at = datetime.now().isoformat()

        # Generate full todo list after completion
        todo_list = self._format_todo_list_simple()
        output_lines = [f"✅ Completed: {todo.title}", ""]
        if todo_list:
            output_lines.append("Current todos:")
            output_lines.extend(todo_list)

        return {
            "success": True,
            "output": "\n".join(output_lines),
            "todo": asdict(todo),
        }

    def _format_todo_list_simple(self) -> list[str]:
        """Format todo list for display after updates.

        Returns:
            List of formatted todo lines with status indicators and strikethrough for completed items.
        """
        if not self._todos:
            return []

        lines = []
        status_order = {"doing": 0, "todo": 1, "done": 2}

        def extract_id_number(todo_id: str) -> int:
            """Extract numeric part from 'todo-X' format."""
            if todo_id.startswith("todo-"):
                return int(todo_id[5:])
            return int(todo_id)

        sorted_todos = sorted(
            self._todos.values(),
            key=lambda t: (status_order.get(t.status, 3), extract_id_number(t.id)),
        )

        for todo in sorted_todos:
            if todo.status == "done":
                # Completed: gray with strikethrough
                lines.append(f"  [dim]✓ [strike]{todo.title}[/strike][/dim]")
            elif todo.status == "doing":
                # In progress: yellow
                lines.append(f"  [yellow]▶ {todo.title}[/yellow]")
            else:
                # Pending: gray
                lines.append(f"  [dim]○ {todo.title}[/dim]")

        return lines

    def list_todos(self) -> dict:
        """List all todos with formatted display.

        Returns:
            Result dict with success status and formatted output
        """
        if not self._todos:
            return {
                "success": True,
                "output": "No todos found. Create one with create_todo().",
                "todos": [],
            }

        # Create Rich table
        table = Table(title="Current Todos", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Status", width=8)
        table.add_column("Title")
        table.add_column("Log", style="dim")

        # Sort by status (doing -> todo -> done) then by ID
        status_order = {"doing": 0, "todo": 1, "done": 2}

        def extract_id_number(todo_id: str) -> int:
            """Extract numeric part from 'todo-X' format."""
            if todo_id.startswith("todo-"):
                return int(todo_id[5:])
            return int(todo_id)

        sorted_todos = sorted(
            self._todos.values(),
            key=lambda t: (status_order.get(t.status, 3), extract_id_number(t.id)),
        )

        for todo in sorted_todos:
            # Status with color
            if todo.status == "done":
                status_str = "[green]✓ done[/green]"
            elif todo.status == "doing":
                status_str = "[yellow]▶ doing[/yellow]"
            else:
                status_str = "[cyan]○ todo[/cyan]"

            # Truncate long logs
            log_display = todo.log[:50] + "..." if len(todo.log) > 50 else todo.log

            table.add_row(f"#{todo.id}", status_str, todo.title, log_display)

        # Format as string for output
        console = Console(record=True)
        console.print(table)
        output = console.export_text()

        return {
            "success": True,
            "output": output,
            "todos": [asdict(t) for t in sorted_todos],
            "count": len(self._todos),
        }
