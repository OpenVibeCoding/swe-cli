"""LangChain tool wrappers for SWE-CLI Todo operations."""

from typing import Optional

from langchain_core.tools import BaseTool

from .base import SWECLIToolWrapper


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