"""LangChain tool wrappers for SWE-CLI Todo operations."""

from typing import List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .base import SWECLIToolWrapper


class WriteTodosSchema(BaseModel):
    """Schema for write_todos tool parameters."""

    todos: List[str] = Field(
        description="List of todo items to create. Each item should be a string describing a task."
    )




class WriteTodosTool(SWECLIToolWrapper):
    """LangChain wrapper for write_todos tool (Deep Agents built-in compatibility).

    This tool creates MULTIPLE todos in a single call to maintain compatibility with
    LangChain's Deep Agents framework which uses 'write_todos' as a built-in planning tool.
    """

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="create_todo",  # Maps to our create_todo backend
            description=(
                "Create multiple todo items for task planning in a single call. "
                "Use this to break down complex tasks into a list of actionable items. "
                "Pass an array of todo descriptions using the 'todos' parameter. "
                "Example: todos=['Task 1', 'Task 2', 'Task 3']"
            ),
            tool_registry=tool_registry,
            args_schema=WriteTodosSchema,  # Add Pydantic schema for validation
        )
        # Override the name to match Deep Agents' expected tool name
        object.__setattr__(self, 'name', 'write_todos')

    def _run(self, todos: Optional[list] = None, **kwargs) -> str:
        """Execute create_todo for multiple items in a single call.

        Args:
            todos: List of todo descriptions/titles to create
            **kwargs: Additional parameters (ignored)

        Returns:
            Formatted result string with all created todos
        """
        if not todos:
            return "Error: No todos provided. Use 'todos' parameter with a list of todo descriptions."

        if not isinstance(todos, list):
            return f"Error: 'todos' must be a list/array. Got {type(todos).__name__}."

        # Create all todos
        results = []
        created_count = 0
        failed_count = 0

        for i, todo_text in enumerate(todos, 1):
            if not todo_text or not str(todo_text).strip():
                failed_count += 1
                results.append(f"  {i}. [SKIPPED] Empty todo")
                continue

            # Call the parent _run which executes through tool registry
            exec_kwargs = {
                "tool_name": "create_todo",
                "arguments": {"title": str(todo_text).strip()},
            }

            try:
                result = self._swetool_registry.execute_tool(**exec_kwargs)

                if result.get("success"):
                    todo_id = result.get("todo_id", "?")
                    results.append(f"  {i}. [✓] Todo #{todo_id}: {str(todo_text).strip()}")
                    created_count += 1
                else:
                    error = result.get("error", "Unknown error")
                    results.append(f"  {i}. [✗] Failed: {error}")
                    failed_count += 1
            except Exception as e:
                results.append(f"  {i}. [✗] Error: {str(e)}")
                failed_count += 1

        # Build summary
        summary_lines = [
            f"Created {created_count} todo(s) from {len(todos)} item(s):",
            "",
        ]
        summary_lines.extend(results)

        if failed_count > 0:
            summary_lines.append(f"\nWarning: {failed_count} todo(s) failed to create.")

        return "\n".join(summary_lines)


class UpdateTodoTool(SWECLIToolWrapper):
    """LangChain wrapper for update_todo tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="update_todo",
            description=(
                "Update an existing todo item. Use this to change todo status, title, or log. "
                "IMPORTANT: Only one todo can be 'doing' at a time - setting a todo to 'doing' automatically deactivates others. "
                "ID can be: numeric index (0, 1, 2...), colon format (:0, :1, :2...), todo-1 format, or todo title/partial match. "
                "Status can be 'pending'/'in_progress'/'completed' (or 'todo'/'doing'/'done'). "
                "For efficient workflow, consider using complete_and_activate_next() to finish current task and start next one automatically. "
                "Example: update_todo(id='0', status='in_progress') to start working on first todo."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, id: str, title: Optional[str] = None, status: Optional[str] = None, log: Optional[str] = None, **kwargs) -> str:
        """Execute update_todo tool."""
        # Build arguments dict, filtering out None values
        args = {"id": id}
        if title is not None:
            args["title"] = title
        if status is not None:
            args["status"] = status
        if log is not None:
            args["log"] = log

        return super()._run(**args)


class CompleteTodoTool(SWECLIToolWrapper):
    """LangChain wrapper for complete_todo tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="complete_todo",
            description=(
                "Mark a todo as completed. Use this when you finish a specific task instead of recreating the entire todo list. "
                "ID can be: numeric index (0, 1, 2...), colon format (:0, :1, :2...), todo-1 format, or todo title/partial match. "
                "RECOMMENDED: Use complete_and_activate_next() instead for better workflow - it completes current task AND activates next one automatically. "
                "Example: complete_todo(id='0') to complete first todo, or complete_and_activate_next('0') to complete and move to next."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, id: str, log: Optional[str] = None, **kwargs) -> str:
        """Execute complete_todo tool."""
        args = {"id": id}
        if log is not None:
            args["log"] = log

        return super()._run(**args)


class CompleteAndActivateNextTool(SWECLIToolWrapper):
    """LangChain wrapper for complete_and_activate_next tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="complete_and_activate_next",
            description=(
                "Complete a todo and automatically activate the next pending one. This is the RECOMMENDED way to manage todo workflow. "
                "Atomic operation that: 1) Marks current todo as completed, 2) Deactivates other active todos, 3) Activates next pending todo. "
                "Use this instead of separate complete_todo() + update_todo() calls for cleaner workflow. "
                "ID can be: numeric index (0, 1, 2...), colon format (:0, :1, :2...), todo-1 format, or todo title/partial match. "
                "Example: complete_and_activate_next('0') to finish current task and automatically start next one."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, id: str, log: Optional[str] = None, **kwargs) -> str:
        """Execute complete_and_activate_next tool."""
        args = {"id": id}
        if log is not None:
            args["log"] = log

        return super()._run(**args)