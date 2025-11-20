"""LangChain tool wrappers for SWE-CLI web operations."""

from typing import Optional

from langchain_core.tools import BaseTool

from .base import SWECLIToolWrapper


class FetchUrlTool(SWECLIToolWrapper):
    """LangChain wrapper for fetch_url tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="fetch_url",
            description=(
                "Fetch and display the content of a web page or API endpoint. Use this to "
                "retrieve documentation, API responses, web content, or online resources. "
                "The url parameter specifies the web address to fetch. This tool can handle "
                "both HTML pages and JSON API responses."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, url: str, **kwargs) -> str:
        """Execute fetch_url tool."""
        return super()._run(url=url, **kwargs)


class OpenBrowserTool(SWECLIToolWrapper):
    """LangChain wrapper for open_browser tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="open_browser",
            description=(
                "Open a web browser to a specified URL. Use this to launch web applications, "
                "open documentation in a browser, or access web-based interfaces. "
                "The url parameter specifies the web address to open in the default browser."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, url: str, **kwargs) -> str:
        """Execute open_browser tool."""
        return super()._run(url=url, **kwargs)


class CaptureWebScreenshotTool(SWECLIToolWrapper):
    """LangChain wrapper for capture_web_screenshot tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="capture_web_screenshot",
            description=(
                "Capture a screenshot of a web page. Use this to capture visual content "
                "from websites, document web applications, or create image references of "
                "web pages. The url parameter specifies the web page to screenshot, "
                "and optional output_path parameter provides a custom save path."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, url: str, output_path: Optional[str] = None, **kwargs) -> str:
        """Execute capture_web_screenshot tool."""
        return super()._run(url=url, output_path=output_path, **kwargs)


class ListWebScreenshotsTool(SWECLIToolWrapper):
    """LangChain wrapper for list_web_screenshots tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="list_web_screenshots",
            description=(
                "List previously captured web screenshots. Use this to see what web "
                "screenshots are available, find specific captures, or manage screenshot "
                "collections. Returns a list of screenshot files with their metadata."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, **kwargs) -> str:
        """Execute list_web_screenshots tool."""
        return super()._run(**kwargs)


class ClearWebScreenshotsTool(SWECLIToolWrapper):
    """LangChain wrapper for clear_web_screenshots tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="clear_web_screenshots",
            description=(
                "Remove old or unnecessary web screenshots. Use this to clean up "
                "screenshot collections, remove old captures, or manage disk space. "
                "The days parameter specifies how old screenshots should be to be deleted."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, days: int = 7, **kwargs) -> str:
        """Execute clear_web_screenshots tool."""
        return super()._run(days=days, **kwargs)