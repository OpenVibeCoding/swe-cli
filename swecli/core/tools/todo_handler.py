"""Todo/Task management handler for tracking development tasks."""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
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

    def __init__(self, storage_dir: Optional[str] = None):
        """Initialize todo handler.

        Args:
            storage_dir: Directory for storing todos (defaults to ~/.swecli/)
        """
        self._todos: Dict[str, TodoItem] = {}
        self._next_id = 1

        # Set up storage
        if storage_dir:
            self._storage_path = Path(storage_dir) / "todos.json"
        else:
            swecli_dir = Path.home() / ".swecli"
            swecli_dir.mkdir(exist_ok=True)
            self._storage_path = swecli_dir / "todos.json"

        # Load existing todos
        self._load_todos()

    def write_todos(self, todos: List[str]) -> dict:
        """Create multiple todo items in a single call.

        Args:
            todos: List of todo titles/descriptions to create

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

        # Create all todos
        results = []
        created_count = 0
        failed_count = 0
        created_ids = []

        for i, todo_text in enumerate(todos, 1):
            if not todo_text or not str(todo_text).strip():
                failed_count += 1
                results.append(f"  {i}. [SKIPPED] Empty todo")
                continue

            # Call create_todo for each item
            result = self.create_todo(title=str(todo_text).strip())

            if result.get("success"):
                todo_id = result.get("todo_id", "?")
                created_ids.append(todo_id)
                results.append(f"  {i}. [✓] Todo #{todo_id}: {str(todo_text).strip()}")
                created_count += 1
            else:
                error = result.get("error", "Unknown error")
                results.append(f"  {i}. [✗] Failed: {error}")
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
            status: Status ("todo", "doing", or "done")
            log: Optional log/notes
            expanded: Whether to show expanded in UI

        Returns:
            Result dict with success status and todo ID
        """
        # Validate status
        if status not in ["todo", "doing", "done"]:
            return {
                "success": False,
                "error": f"Invalid status '{status}'. Must be 'todo', 'doing', or 'done'.",
                "output": None,
            }

        # Create todo
        todo_id = str(self._next_id)
        self._next_id += 1

        todo = TodoItem(
            id=todo_id,
            title=title,
            status=status,
            log=log,
            expanded=expanded,
        )

        self._todos[todo_id] = todo
        self._save_todos()

        return {
            "success": True,
            "output": f"Created todo #{todo_id}: {title}",
            "todo_id": todo_id,
            "todo": asdict(todo),
        }

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
            status: New status (optional)
            log: New log/notes (optional)
            expanded: New expanded state (optional)

        Returns:
            Result dict with success status
        """
        if id not in self._todos:
            return {
                "success": False,
                "error": f"Todo #{id} not found",
                "output": None,
            }

        todo = self._todos[id]

        # Update fields
        if title is not None:
            todo.title = title
        if status is not None:
            if status not in ["todo", "doing", "done"]:
                return {
                    "success": False,
                    "error": f"Invalid status '{status}'. Must be 'todo', 'doing', or 'done'.",
                    "output": None,
                }
            todo.status = status
        if log is not None:
            todo.log = log
        if expanded is not None:
            todo.expanded = expanded

        todo.updated_at = datetime.now().isoformat()
        self._save_todos()

        return {
            "success": True,
            "output": f"Updated todo #{id}",
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
        if id not in self._todos:
            return {
                "success": False,
                "error": f"Todo #{id} not found",
                "output": None,
            }

        todo = self._todos[id]
        todo.status = "done"

        if log:
            if todo.log:
                todo.log += f"\n{log}"
            else:
                todo.log = log

        todo.updated_at = datetime.now().isoformat()
        self._save_todos()

        return {
            "success": True,
            "output": f"Completed todo #{id}: {todo.title}",
            "todo": asdict(todo),
        }

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
        sorted_todos = sorted(
            self._todos.values(),
            key=lambda t: (status_order.get(t.status, 3), int(t.id)),
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

    def _save_todos(self):
        """Save todos to disk."""
        data = {
            "next_id": self._next_id,
            "todos": {tid: asdict(todo) for tid, todo in self._todos.items()},
        }

        try:
            with open(self._storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            # Log error but don't fail
            print(f"Warning: Could not save todos: {e}")

    def _load_todos(self):
        """Load todos from disk."""
        if not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, "r") as f:
                data = json.load(f)

            self._next_id = data.get("next_id", 1)
            todos_data = data.get("todos", {})

            for todo_id, todo_dict in todos_data.items():
                self._todos[todo_id] = TodoItem(**todo_dict)

        except Exception as e:
            # Log error but start fresh
            print(f"Warning: Could not load todos: {e}")
            self._todos = {}
            self._next_id = 1
