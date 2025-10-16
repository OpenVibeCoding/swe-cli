"""Primary tool registry implementation coordinating handlers."""

from __future__ import annotations

from typing import Any

from opencli.core.management import OperationMode
from opencli.core.tools.context import ToolExecutionContext
from opencli.core.tools.file_handlers import FileToolHandler
from opencli.core.tools.mcp_handler import McpToolHandler
from opencli.core.tools.process_handlers import ProcessToolHandler
from opencli.core.tools.web_handlers import WebToolHandler

_PLAN_READ_ONLY_TOOLS = {
    "read_file",
    "list_files",
    "search",
    "fetch_url",
    "list_processes",
    "get_process_output",
}


class ToolRegistry:
    """Dispatches tool invocations to dedicated handlers."""

    def __init__(
        self,
        file_ops: Any | None = None,
        write_tool: Any | None = None,
        edit_tool: Any | None = None,
        bash_tool: Any | None = None,
        web_fetch_tool: Any | None = None,
        mcp_manager: Any | None = None,
    ) -> None:
        self.file_ops = file_ops
        self.write_tool = write_tool
        self.edit_tool = edit_tool
        self.bash_tool = bash_tool
        self.web_fetch_tool = web_fetch_tool

        self._file_handler = FileToolHandler(file_ops, write_tool, edit_tool)
        self._process_handler = ProcessToolHandler(bash_tool)
        self._web_handler = WebToolHandler(web_fetch_tool)
        self._mcp_handler = McpToolHandler(mcp_manager)
        self.set_mcp_manager(mcp_manager)

        self._handlers: dict[str, Any] = {
            "write_file": self._file_handler.write_file,
            "edit_file": self._file_handler.edit_file,
            "read_file": self._file_handler.read_file,
            "list_files": self._file_handler.list_files,
            "search": self._file_handler.search,
            "run_command": self._process_handler.run_command,
            "list_processes": lambda args, ctx: self._process_handler.list_processes(),
            "get_process_output": self._process_handler.get_process_output,
            "kill_process": self._process_handler.kill_process,
            "fetch_url": self._web_handler.fetch_url,
        }

    def get_schemas(self) -> list[dict[str, Any]]:
        """Compatibility hook (schemas generated elsewhere)."""
        return []

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        mode_manager: Any | None = None,
        approval_manager: Any | None = None,
        undo_manager: Any | None = None,
    ) -> dict[str, Any]:
        """Execute a tool by delegating to registered handlers."""
        if tool_name.startswith("mcp__"):
            return self._mcp_handler.execute(tool_name, arguments)

        if tool_name not in self._handlers:
            return {"success": False, "error": f"Unknown tool: {tool_name}", "output": None}

        context = ToolExecutionContext(
            mode_manager=mode_manager,
            approval_manager=approval_manager,
            undo_manager=undo_manager,
        )

        if self._is_plan_blocked(tool_name, context):
            return self._plan_blocked_result(tool_name, arguments)

        handler = self._handlers[tool_name]
        try:
            if tool_name in {"write_file", "edit_file", "run_command"}:
                # Handlers requiring context
                return handler(arguments, context)

            if tool_name == "list_processes":
                return handler(arguments, context)

            if tool_name in {"get_process_output", "kill_process"}:
                return handler(arguments)

            # Remaining handlers ignore execution context
            return handler(arguments)
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "output": None}

    @staticmethod
    def _plan_blocked_result(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        summary_text = (
            f"Plan-only mode blocks '{tool_name}'. Switch to normal mode to execute."
        )
        return {
            "success": False,
            "error": summary_text,
            "plan_only": True,
            "tool_name": tool_name,
            "arguments": arguments,
            "plan_summary": summary_text,
        }

    @staticmethod
    def _is_plan_blocked(tool_name: str, context: ToolExecutionContext) -> bool:
        mode_manager = context.mode_manager
        if not mode_manager:
            return False

        if getattr(mode_manager, "current_mode", None) != OperationMode.PLAN:
            return False

        return tool_name not in _PLAN_READ_ONLY_TOOLS

    def set_mcp_manager(self, mcp_manager: Any | None) -> None:
        """Update the MCP manager and refresh the handler."""
        self.mcp_manager = mcp_manager
        self._mcp_handler = McpToolHandler(mcp_manager)
