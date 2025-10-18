"""Web fetching tool for retrieving content from URLs."""

import requests
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup

from swecli.models.config import AppConfig


class WebFetchTool:
    """Tool for fetching web content."""

    def __init__(self, config: AppConfig, working_dir: Path):
        """Initialize web fetch tool.

        Args:
            config: Application configuration
            working_dir: Working directory (not used but kept for consistency)
        """
        self.config = config
        self.working_dir = working_dir
        self.timeout = 30  # 30 second timeout for requests

    def fetch_url(
        self,
        url: str,
        extract_text: bool = True,
        max_length: Optional[int] = 50000,
    ) -> dict[str, any]:
        """Fetch content from a URL.

        Args:
            url: URL to fetch
            extract_text: If True, extract text from HTML. If False, return raw content
            max_length: Maximum content length (None for no limit)

        Returns:
            Dictionary with success, content, and optional error
        """
        try:
            # Validate URL format
            if not url.startswith(("http://", "https://")):
                return {
                    "success": False,
                    "error": f"Invalid URL: must start with http:// or https://",
                    "content": None,
                }

            # Make request with timeout
            headers = {
                "User-Agent": "SWE-CLI/1.0 (AI Assistant Tool)",
            }

            response = requests.get(url, headers=headers, timeout=self.timeout)

            # Check for errors
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.reason}",
                    "content": None,
                }

            # Get content
            content = response.text

            # Extract text from HTML if requested
            if extract_text and "text/html" in response.headers.get("content-type", ""):
                try:
                    soup = BeautifulSoup(content, "html.parser")

                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()

                    # Get text
                    text = soup.get_text()

                    # Clean up whitespace
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = "\n".join(chunk for chunk in chunks if chunk)

                    content = text
                except Exception as e:
                    # If parsing fails, return raw content
                    pass

            # Truncate if needed
            if max_length and len(content) > max_length:
                content = content[:max_length] + f"\n\n... (truncated, total length: {len(content)} characters)"

            return {
                "success": True,
                "content": content,
                "error": None,
                "url": response.url,  # Final URL after redirects
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", "unknown"),
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Request timeout after {self.timeout} seconds",
                "content": None,
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"Connection error: {str(e)}",
                "content": None,
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "content": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "content": None,
            }
