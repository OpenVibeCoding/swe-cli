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


class CreateTodoTool(SWECLIToolWrapper):
    """LangChain wrapper for create_todo tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="create_todo",
            description=(
                "Create a new todo item. Use this to track tasks, create reminders, "
                "or manage work items. The text parameter contains the todo description, "
                "and optional category parameter helps organize related todos."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, text: str, category: Optional[str] = None, **kwargs) -> str:
        """Execute create_todo tool."""
        return super()._run(text=text, category=category, **kwargs)


class UpdateTodoTool(SWECLIToolWrapper):
    """LangChain wrapper for update_todo tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="update_todo",
            description=(
                "Update an existing todo item. Use this to modify todo descriptions, "
                "change categories, or update task details. The id parameter specifies "
                "which todo to update, and text parameter contains the new description."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, id: int, text: str, category: Optional[str] = None, **kwargs) -> str:
        """Execute update_todo tool."""
        return super()._run(id=id, text=text, category=category, **kwargs)


class CompleteTodoTool(SWECLIToolWrapper):
    """LangChain wrapper for complete_todo tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="complete_todo",
            description=(
                "Mark a todo item as completed. Use this to track task completion, "
                "remove finished items from active lists, or maintain progress records. "
                "The id parameter specifies which todo to mark as complete."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, id: int, **kwargs) -> str:
        """Execute complete_todo tool."""
        return super()._run(id=id, **kwargs)


class ListTodosTool(SWECLIToolWrapper):
    """LangChain wrapper for list_todos tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="list_todos",
            description=(
                "List all todo items. Use this to see current tasks, review progress, "
                "or plan next steps. The category parameter allows filtering todos by "
                "specific categories, and completed parameter controls whether to show "
                "completed items."
            ),
            tool_registry=tool_registry,
        )

    def _run(
        self,
        category: Optional[str] = None,
        completed: Optional[bool] = None,
        **kwargs
    ) -> str:
        """Execute list_todos tool."""
        return super()._run(category=category, completed=completed, **kwargs)


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