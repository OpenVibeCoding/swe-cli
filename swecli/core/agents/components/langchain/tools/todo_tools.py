"""LangChain tool wrappers for SWE-CLI Todo operations."""

from typing import Any, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .base import SWECLIToolWrapper


class TodoItem(BaseModel):
    """Schema for a single todo item."""
    content: str = Field(description="The task description")
    status: str = Field(
        default="pending",
        description="Status: 'pending', 'in_progress', or 'completed'"
    )
    activeForm: Optional[str] = Field(
        default=None,
        description="Present continuous form shown during execution (e.g., 'Running tests')"
    )


class WriteTodosInput(BaseModel):
    """Input schema for write_todos tool."""
    todos: List[TodoItem] = Field(description="List of todo items to write")


class UpdateTodoInput(BaseModel):
    """Input schema for update_todo tool."""
    id: int = Field(description="ID of the todo item to update")
    status: Optional[str] = Field(
        default=None,
        description="New status: 'pending', 'in_progress', or 'completed'"
    )
    title: Optional[str] = Field(
        default=None,
        description="New title/description for the todo"
    )


class CompleteTodoInput(BaseModel):
    """Input schema for complete_todo tool."""
    id: int = Field(description="ID of the todo item to mark as completed")


class WriteTodosTool(SWECLIToolWrapper):
    """LangChain wrapper for write_todos tool."""

    def __init__(self, tool_registry: Any):
        super().__init__(
            tool_name="write_todos",
            description=(
                "Create or replace the entire todo list. Use this to track tasks, "
                "plan work items, and manage progress. Each todo has content (description), "
                "status ('pending', 'in_progress', or 'completed'), and optional activeForm "
                "(present continuous description like 'Running tests')."
            ),
            tool_registry=tool_registry,
            args_schema=WriteTodosInput,
        )

    def _run(self, todos: List[Any], **kwargs) -> str:
        """Execute write_todos tool."""
        # Convert TodoItem objects to dicts if needed
        todo_list = []
        for t in todos:
            if isinstance(t, dict):
                todo_list.append({
                    "content": t.get("content", str(t)),
                    "status": t.get("status", "pending"),
                    "activeForm": t.get("activeForm"),
                })
            elif hasattr(t, "content"):
                todo_list.append({
                    "content": t.content,
                    "status": getattr(t, "status", "pending"),
                    "activeForm": getattr(t, "activeForm", None),
                })
            else:
                todo_list.append({
                    "content": str(t),
                    "status": "pending",
                })
        return super()._run(todos=todo_list, **kwargs)


class UpdateTodoTool(SWECLIToolWrapper):
    """LangChain wrapper for update_todo tool."""

    def __init__(self, tool_registry: Any):
        super().__init__(
            tool_name="update_todo",
            description=(
                "Update an existing todo item. Use this to change status, "
                "modify descriptions, or update task details. Specify the id "
                "of the todo to update along with the new status or title."
            ),
            tool_registry=tool_registry,
            args_schema=UpdateTodoInput,
        )

    def _run(
        self,
        id: int,
        status: Optional[str] = None,
        title: Optional[str] = None,
        **kwargs
    ) -> str:
        """Execute update_todo tool."""
        return super()._run(id=id, status=status, title=title, **kwargs)


class CompleteTodoTool(SWECLIToolWrapper):
    """LangChain wrapper for complete_todo tool."""

    def __init__(self, tool_registry: Any):
        super().__init__(
            tool_name="complete_todo",
            description=(
                "Mark a todo item as completed. Use this to track task completion "
                "and maintain progress records. Specify the id of the todo to complete."
            ),
            tool_registry=tool_registry,
            args_schema=CompleteTodoInput,
        )

    def _run(self, id: int, **kwargs) -> str:
        """Execute complete_todo tool."""
        return super()._run(id=id, **kwargs)


class ListTodosTool(SWECLIToolWrapper):
    """LangChain wrapper for list_todos tool."""

    def __init__(self, tool_registry: Any):
        super().__init__(
            tool_name="list_todos",
            description=(
                "List all todo items. Use this to see current tasks, review progress, "
                "or plan next steps. Returns all todos with their status and details."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, **kwargs) -> str:
        """Execute list_todos tool."""
        return super()._run(**kwargs)
