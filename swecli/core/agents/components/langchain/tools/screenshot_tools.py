"""LangChain tool wrappers for SWE-CLI screenshot operations."""

from typing import Optional

from langchain_core.tools import BaseTool

from .base import SWECLIToolWrapper


class CaptureScreenshotTool(SWECLIToolWrapper):
    """LangChain wrapper for capture_screenshot tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="capture_screenshot",
            description=(
                "Capture a screenshot of the current screen or desktop. Use this to "
                "document the current state of applications, capture error messages, "
                "or create visual references of the desktop environment. "
                "The name parameter provides an optional custom filename."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, name: Optional[str] = None, **kwargs) -> str:
        """Execute capture_screenshot tool."""
        return super()._run(name=name, **kwargs)


class ListScreenshotsTool(SWECLIToolWrapper):
    """LangChain wrapper for list_screenshots tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="list_screenshots",
            description=(
                "List previously captured screenshots. Use this to see what screenshots "
                "are available, find specific captures, or manage screenshot collections. "
                "Returns a list of screenshot files with their sizes and timestamps."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, **kwargs) -> str:
        """Execute list_screenshots tool."""
        return super()._run(**kwargs)


class ClearScreenshotsTool(SWECLIToolWrapper):
    """LangChain wrapper for clear_screenshots tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="clear_screenshots",
            description=(
                "Remove all screenshots from the screenshot directory. Use this to "
                "clean up screenshot collections, remove old captures, or manage "
                "disk space. This action cannot be undone."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, **kwargs) -> str:
        """Execute clear_screenshots tool."""
        return super()._run(**kwargs)