"""Web fetching tool for retrieving content from URLs using Crawl4AI."""

import asyncio
from pathlib import Path
from typing import Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from swecli.models.config import AppConfig


class WebFetchTool:
    """Tool for fetching web content using Crawl4AI."""

    def __init__(self, config: AppConfig, working_dir: Path):
        """Initialize web fetch tool.

        Args:
            config: Application configuration
            working_dir: Working directory (not used but kept for consistency)
        """
        self.config = config
        self.working_dir = working_dir
        self.timeout = 30000  # 30 second timeout for page load

    def fetch_url(
        self,
        url: str,
        extract_text: bool = True,
        max_length: Optional[int] = 50000,
    ) -> dict[str, any]:
        """Fetch content from a URL using Crawl4AI.

        Args:
            url: URL to fetch
            extract_text: If True, return markdown format. If False, return raw HTML
            max_length: Maximum content length (None for no limit)

        Returns:
            Dictionary with success, content, and optional error
        """
        # Run async fetch in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._fetch_url_async(url, extract_text, max_length))

    async def _fetch_url_async(
        self,
        url: str,
        extract_text: bool = True,
        max_length: Optional[int] = 50000,
    ) -> dict[str, any]:
        """Async implementation of URL fetching.

        Args:
            url: URL to fetch
            extract_text: If True, return markdown format. If False, return raw HTML
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

            # Configure browser
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
                user_agent="SWE-CLI/1.0 (AI Assistant Tool; Crawl4AI)",
            )

            # Configure crawler
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                word_count_threshold=10,
                exclude_external_links=False,
                remove_overlay_elements=True,
                process_iframes=False,
                page_timeout=self.timeout,
            )

            # Fetch URL
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)

                # Check if fetch was successful
                if not result.success:
                    error_msg = result.error_message if hasattr(result, 'error_message') else "Unknown error"
                    return {
                        "success": False,
                        "error": error_msg,
                        "content": None,
                    }

                # Get content - use markdown for extract_text, HTML otherwise
                content = result.markdown if extract_text else result.html

                # Truncate if needed
                if max_length and len(content) > max_length:
                    content = content[:max_length] + f"\n\n... (truncated, total length: {len(content)} characters)"

                return {
                    "success": True,
                    "content": content,
                    "error": None,
                    "url": result.url,  # Final URL after redirects
                    "status_code": 200,  # Crawl4AI doesn't expose status codes directly
                    "content_type": "text/markdown" if extract_text else "text/html",
                    "links": result.links if hasattr(result, 'links') else {},
                    "media": result.media if hasattr(result, 'media') else {},
                }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Request timeout after {self.timeout / 1000} seconds",
                "content": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to fetch URL: {str(e)}",
                "content": None,
            }
