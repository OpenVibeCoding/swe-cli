"""Primary tool registry implementation coordinating handlers."""

from __future__ import annotations

from typing import Any, Union

from swecli.core.management import OperationMode
from swecli.core.tools.context import ToolExecutionContext
from swecli.core.tools.file_handlers import FileToolHandler
from swecli.core.tools.mcp_handler import McpToolHandler
from swecli.core.tools.process_handlers import ProcessToolHandler
from swecli.core.tools.todo_handler import TodoHandler
from swecli.core.tools.web_handlers import WebToolHandler
from swecli.core.tools.screenshot_handler import ScreenshotToolHandler

_PLAN_READ_ONLY_TOOLS = {
    "read_file",
    "list_files",
    "search",
    "fetch_url",
    "list_processes",
    "get_process_output",
    "list_screenshots",
    "analyze_image",  # VLM is read-only, safe for planning mode
    "list_todos",  # List todos is read-only, safe for planning mode
}


class ToolRegistry:
    """Dispatches tool invocations to dedicated handlers."""

    def __init__(
        self,
        file_ops: Union[Any, None] = None,
        write_tool: Union[Any, None] = None,
        edit_tool: Union[Any, None] = None,
        bash_tool: Union[Any, None] = None,
        web_fetch_tool: Union[Any, None] = None,
        open_browser_tool: Union[Any, None] = None,
        vlm_tool: Union[Any, None] = None,
        web_screenshot_tool: Union[Any, None] = None,
        mcp_manager: Union[Any, None] = None
    ) -> None:
        self.file_ops = file_ops
        self.write_tool = write_tool
        self.edit_tool = edit_tool
        self.bash_tool = bash_tool
        self.web_fetch_tool = web_fetch_tool
        self.open_browser_tool = open_browser_tool
        self.vlm_tool = vlm_tool
        self.web_screenshot_tool = web_screenshot_tool

        self._file_handler = FileToolHandler(file_ops, write_tool, edit_tool)
        self._process_handler = ProcessToolHandler(bash_tool)
        self._web_handler = WebToolHandler(web_fetch_tool)
        self._mcp_handler = McpToolHandler(mcp_manager)
        self._screenshot_handler = ScreenshotToolHandler()
        self._todo_handler = TodoHandler()
        self.set_mcp_manager(mcp_manager)

        # Initialize Deep Agent filesystem backend for built-in tools
        from deepagents.backends import FilesystemBackend
        import os
        self._deep_backend = FilesystemBackend(root_dir=os.getcwd())

        self._handlers: dict[str, Any] = {
            "write_file": self._file_handler.write_file,
            "edit_file": self._file_handler.edit_file,
            "read_file": self._file_handler.read_file,
            "list_files": self._file_handler.list_files,
            "search": self._file_handler.search,
            # Add Deep Agent built-in tools
            "grep": self._deep_grep,
            "glob": self._deep_glob,
            "ls": self._deep_ls,
            "run_command": self._process_handler.run_command,
            "list_processes": lambda args, ctx: self._process_handler.list_processes(),
            "get_process_output": self._process_handler.get_process_output,
            "kill_process": self._process_handler.kill_process,
            "fetch_url": self._web_handler.fetch_url,
            "open_browser": self._open_browser,
            "capture_screenshot": self._screenshot_handler.capture_screenshot,
            "list_screenshots": lambda args: self._screenshot_handler.list_screenshots(),
            "clear_screenshots": self._screenshot_handler.clear_screenshots,
            "analyze_image": self._analyze_image,
            "capture_web_screenshot": self._capture_web_screenshot,
            "list_web_screenshots": lambda args: self._list_web_screenshots(),
            "clear_web_screenshots": self._clear_web_screenshots,
            # Todo/task management tools
            "write_todos": self._todo_handler.write_todos,  # Accepts both List[str] and List[dict] formats (Deep Agent compatible)
            "create_todo": self._todo_handler.create_todo,
            "update_todo": self._todo_handler.update_todo,
            "complete_todo": self._todo_handler.complete_todo,
            "complete_and_activate_next": self._todo_handler.complete_and_activate_next,  # Atomic operation
            "list_todos": lambda args: self._todo_handler.list_todos(),
        }

    def get_schemas(self) -> list[dict[str, Any]]:
        """Compatibility hook (schemas generated elsewhere)."""
        return []

    def get_langchain_tools(self) -> list[Any]:
        """Return LangChain-compatible tool instances.

        Returns:
            List of LangChain BaseTool instances wrapping SWE-CLI tools
        """
        try:
            from swecli.core.agents.components.langchain.tools import ToolRegistryAdapter
            adapter = ToolRegistryAdapter(self)
            return adapter.get_langchain_tools()
        except ImportError:
            # LangChain not available, return empty list
            return []

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        mode_manager: Union[Any, None] = None,
        approval_manager: Union[Any, None] = None,
        undo_manager: Union[Any, None] = None,
        task_monitor: Union[Any, None] = None,
        session_manager: Union[Any, None] = None,
    ) -> dict[str, Any]:
        """Execute a tool by delegating to registered handlers."""
        if tool_name.startswith("mcp__"):
            return self._mcp_handler.execute(tool_name, arguments, task_monitor)

        if tool_name not in self._handlers:
            return {"success": False, "error": f"Unknown tool: {tool_name}", "output": None}

        context = ToolExecutionContext(
            mode_manager=mode_manager,
            approval_manager=approval_manager,
            undo_manager=undo_manager,
            task_monitor=task_monitor,
            session_manager=session_manager,
        )

        if self._is_plan_blocked(tool_name, context):
            return self._plan_blocked_result(tool_name, arguments)

        # Check for interrupt before executing tool
        if task_monitor and task_monitor.should_interrupt():
            return {
                "success": False,
                "error": "Operation cancelled by user",
                "output": None,
                "interrupted": True,
            }

        handler = self._handlers[tool_name]
        try:
            if tool_name in {"write_file", "edit_file", "run_command", "fetch_url"}:
                # Handlers requiring context
                return handler(arguments, context)

            if tool_name == "list_processes":
                return handler(arguments, context)

            if tool_name in {"get_process_output", "kill_process"}:
                return handler(arguments)

            # Remaining handlers ignore execution context
            # Unpack arguments dict to pass as keyword arguments
            return handler(**arguments)
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

    def set_mcp_manager(self, mcp_manager: Union[Any, None]) -> None:
        """Update the MCP manager and refresh the handler."""
        self.mcp_manager = mcp_manager
        self._mcp_handler = McpToolHandler(mcp_manager)

    def _open_browser(self, **arguments) -> dict[str, Any]:
        """Execute the open_browser tool."""
        if not self.open_browser_tool:
            return {
                "success": False,
                "error": "open_browser tool not available",
                "output": None,
            }
        return self.open_browser_tool.execute(**arguments)

    def _analyze_image(self, **arguments) -> dict[str, Any]:
        """Execute the analyze_image tool (VLM)."""
        if not self.vlm_tool:
            return {
                "success": False,
                "error": "VLM tool not available",
                "output": None,
            }
        result = self.vlm_tool.analyze_image(**arguments)
        # Format output for consistency with other tools
        if result.get("success"):
            return {
                "success": True,
                "output": result.get("content", ""),
                "model": result.get("model"),
                "provider": result.get("provider"),
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "output": None,
            }

    def _capture_web_screenshot(self, **arguments) -> dict[str, Any]:
        """Execute the capture_web_screenshot tool."""
        if not self.web_screenshot_tool:
            return {
                "success": False,
                "error": "Web screenshot tool not available",
                "output": None,
            }
        result = self.web_screenshot_tool.capture_web_screenshot(**arguments)
        # Format output for consistency
        if result.get("success"):
            output_lines = [
                f"Screenshot captured: {result.get('screenshot_path')}",
                f"URL: {result.get('url')}",
            ]
            if result.get("pdf_path"):
                output_lines.append(f"PDF captured: {result.get('pdf_path')}")
            if result.get("warning"):
                output_lines.append(f"Warning: {result['warning']}")
            if result.get("pdf_warning"):
                output_lines.append(f"PDF Warning: {result['pdf_warning']}")

            response = {
                "success": True,
                "output": "\n".join(output_lines),
                "screenshot_path": result.get("screenshot_path"),
            }
            if result.get("pdf_path"):
                response["pdf_path"] = result.get("pdf_path")
            return response
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "output": None,
            }

    def _list_web_screenshots(self) -> dict[str, Any]:
        """Execute the list_web_screenshots tool."""
        if not self.web_screenshot_tool:
            return {
                "success": False,
                "error": "Web screenshot tool not available",
                "output": None,
            }
        result = self.web_screenshot_tool.list_web_screenshots()
        if result.get("success"):
            screenshots = result.get("screenshots", [])
            if screenshots:
                output_lines = [f"Found {len(screenshots)} web screenshot(s):"]
                for ss in screenshots:
                    output_lines.append(f"  - {ss['name']} ({ss['size_kb']} KB)")
                output_lines.append(f"\nDirectory: {result.get('directory')}")
            else:
                output_lines = ["No web screenshots found"]
            return {
                "success": True,
                "output": "\n".join(output_lines),
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "output": None,
            }

    def _clear_web_screenshots(self, **arguments) -> dict[str, Any]:
        """Execute the clear_web_screenshots tool."""
        if not self.web_screenshot_tool:
            return {
                "success": False,
                "error": "Web screenshot tool not available",
                "output": None,
            }
        result = self.web_screenshot_tool.clear_web_screenshots(**arguments)
        if result.get("success"):
            deleted = result.get("deleted_count", 0)
            kept = result.get("kept_count", 0)
            output = f"Deleted {deleted} old screenshot(s), kept {kept} recent"
            return {
                "success": True,
                "output": output,
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "output": None,
            }

    def _deep_grep(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute grep using Deep Agent's FilesystemBackend."""
        pattern = arguments.get("pattern")
        path = arguments.get("path")
        glob_pattern = arguments.get("glob")
        output_mode = arguments.get("output_mode", "files_with_matches")

        try:
            # Call backend's grep_raw method
            result = self._deep_backend.grep_raw(
                pattern,
                path=path,
                glob=glob_pattern
            )

            if isinstance(result, str):
                # Error message
                return {"success": False, "error": result, "output": None}

            # Format results based on output_mode
            from deepagents.middleware.filesystem import format_grep_matches
            formatted = format_grep_matches(result, output_mode)

            return {"success": True, "output": formatted}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}

    def _deep_glob(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute glob using Deep Agent's FilesystemBackend."""
        pattern = arguments.get("pattern")
        path = arguments.get("path", "/")

        try:
            infos = self._deep_backend.glob_info(pattern, path=path)
            paths = [fi.get("path", "") for fi in infos]

            return {"success": True, "output": "\n".join(paths)}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}

    def _deep_ls(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute ls using Deep Agent's FilesystemBackend."""
        path = arguments.get("path", ".")

        try:
            infos = self._deep_backend.ls_info(path)
            # Format as list of paths
            paths = [fi.get("path", "") for fi in infos]

            return {"success": True, "output": "\n".join(paths)}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}
