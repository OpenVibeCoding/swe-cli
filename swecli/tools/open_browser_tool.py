"""Tool for opening URLs in the default web browser."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Any, Dict

from swecli.models.config import AppConfig


class OpenBrowserTool:
    """Tool for opening URLs in the default web browser.

    This tool allows the agent to automatically open web pages, which is useful
    for web development workflows where the agent creates a web app and wants
    to show it to the user.
    """

    def __init__(self, config: AppConfig, working_dir: Path):
        """Initialize the open browser tool.

        Args:
            config: Configuration object
            working_dir: Working directory path
        """
        self.config = config
        self.working_dir = working_dir

    def execute(self, url: str, **kwargs) -> Dict[str, Any]:
        """Open a URL in the default web browser.

        Args:
            url: The URL to open
            **kwargs: Additional arguments (ignored)

        Returns:
            Result dictionary with success status and message
        """
        try:
            # Normalize localhost URLs
            if url.startswith("localhost:"):
                url = f"http://{url}"
            elif url.startswith(":"):
                url = f"http://localhost{url}"

            # Validate URL format
            if not (url.startswith("http://") or url.startswith("https://")):
                return {
                    "success": False,
                    "error": f"Invalid URL format: {url}. Must start with http:// or https://",
                }

            # Open in browser
            webbrowser.open(url)

            return {
                "success": True,
                "message": f"Opened {url} in your default browser",
                "url": url,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to open browser: {str(e)}",
            }
