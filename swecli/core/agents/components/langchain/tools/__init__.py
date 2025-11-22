"""LangChain tool wrappers for SWE-CLI tools.

NOTE: File operation tools (read_file, write_file, edit_file, ls, grep, glob)
and todo tools (write_todos) are provided by Deep Agent's built-in middleware
and are not exported here.
"""

from .base import SWECLIToolWrapper, ToolRegistryAdapter
# File tools removed - using Deep Agent's built-in FilesystemMiddleware
# (read_file, write_file, edit_file, ls, grep, glob)
# Todo tools removed - using Deep Agent's built-in TodoListMiddleware
# (write_todos)
from .bash_tools import RunCommandTool, ListProcessesTool, GetProcessOutputTool, KillProcessTool
from .web_tools import FetchUrlTool, OpenBrowserTool, CaptureWebScreenshotTool, ListWebScreenshotsTool, ClearWebScreenshotsTool
from .screenshot_tools import CaptureScreenshotTool, ListScreenshotsTool, ClearScreenshotsTool
from .vlm_tools import AnalyzeImageTool
from .todo_tools import UpdateTodoTool, CompleteTodoTool

__all__ = [
    "SWECLIToolWrapper",
    "ToolRegistryAdapter",
    # File tools removed - using Deep Agent built-ins
    # Todo tools: write_todos is built-in, but update_todo and complete_todo are custom
    "RunCommandTool",
    "ListProcessesTool",
    "GetProcessOutputTool",
    "KillProcessTool",
    "FetchUrlTool",
    "OpenBrowserTool",
    "CaptureWebScreenshotTool",
    "ListWebScreenshotsTool",
    "ClearWebScreenshotsTool",
    "CaptureScreenshotTool",
    "ListScreenshotsTool",
    "ClearScreenshotsTool",
    "AnalyzeImageTool",
    "UpdateTodoTool",
    "CompleteTodoTool",
]