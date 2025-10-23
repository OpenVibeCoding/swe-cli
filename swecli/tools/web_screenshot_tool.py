"""Web screenshot tool using Playwright for high-quality full-page captures."""

import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from swecli.models.config import AppConfig


class WebScreenshotTool:
    """Tool for capturing full-page screenshots of web pages using Playwright."""

    def __init__(self, config: AppConfig, working_dir: Path):
        """Initialize web screenshot tool.

        Args:
            config: Application configuration
            working_dir: Working directory for resolving relative paths
        """
        self.config = config
        self.working_dir = working_dir
        self.screenshot_dir = Path(tempfile.gettempdir()) / "swecli_web_screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def is_playwright_available(self) -> bool:
        """Check if Playwright is installed and browsers are available.

        Returns:
            True if Playwright is available, False otherwise
        """
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            return False

    def capture_web_screenshot(
        self,
        url: str,
        output_path: Optional[str] = None,
        wait_until: str = "networkidle",
        timeout_ms: int = 30000,
        full_page: bool = True,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        clip_to_content: bool = True,
        max_height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Capture a full-page screenshot of a web page.

        Args:
            url: URL of the web page to capture
            output_path: Path to save screenshot (relative to working_dir or absolute).
                        If None, saves to temp directory with auto-generated name.
            wait_until: When to consider navigation complete:
                       - "load": wait for load event
                       - "domcontentloaded": wait for DOMContentLoaded event
                       - "networkidle": wait until no network requests for 500ms (recommended)
            timeout_ms: Maximum time to wait for page load (milliseconds)
            full_page: Whether to capture full scrollable page (True) or just viewport (False)
            viewport_width: Browser viewport width in pixels
            viewport_height: Browser viewport height in pixels
            clip_to_content: If True, automatically detect actual content height and clip
                            to avoid excessive whitespace (only works with full_page=True)
            max_height: Maximum screenshot height in pixels (prevents extremely tall screenshots)

        Returns:
            Dictionary with success, screenshot_path, and optional error
        """
        # Check if Playwright is available
        if not self.is_playwright_available():
            return {
                "success": False,
                "error": (
                    "Playwright is not installed. Install it with:\n"
                    "  pip install playwright\n"
                    "  playwright install chromium"
                ),
                "screenshot_path": None,
            }

        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

            # Determine output path
            if output_path:
                screenshot_path = Path(output_path)
                if not screenshot_path.is_absolute():
                    screenshot_path = self.working_dir / screenshot_path
            else:
                # Auto-generate filename from URL
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc.replace(":", "_").replace("/", "_")
                timestamp = Path(tempfile.mktemp()).name  # Get unique ID
                filename = f"{domain}_{timestamp}.png"
                screenshot_path = self.screenshot_dir / filename

            # Ensure parent directory exists
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            # Capture screenshot with Playwright
            with sync_playwright() as p:
                # Launch headless Chromium
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": viewport_width, "height": viewport_height}
                )
                page = context.new_page()

                try:
                    # Navigate to URL and wait for page to be ready
                    page.goto(url, wait_until=wait_until, timeout=timeout_ms)

                    # Determine screenshot options
                    screenshot_options = {"path": str(screenshot_path)}

                    if full_page and clip_to_content:
                        # Detect actual content height to avoid excessive whitespace
                        content_height = page.evaluate("""
                            () => {
                                // Get all possible content boundaries
                                const body = document.body;
                                const html = document.documentElement;

                                // Find the maximum bottom position of all visible elements
                                let maxBottom = 0;
                                const elements = document.querySelectorAll('*');

                                for (const el of elements) {
                                    // Skip hidden elements
                                    const style = window.getComputedStyle(el);
                                    if (style.display === 'none' || style.visibility === 'hidden') {
                                        continue;
                                    }

                                    const rect = el.getBoundingClientRect();
                                    const bottom = rect.bottom + window.scrollY;

                                    if (bottom > maxBottom) {
                                        maxBottom = bottom;
                                    }
                                }

                                // Also check common height measurements
                                const heights = [
                                    maxBottom,
                                    body.scrollHeight,
                                    body.offsetHeight,
                                    html.clientHeight,
                                    html.scrollHeight,
                                    html.offsetHeight
                                ];

                                // Return the maximum that's reasonable (not absurdly large)
                                const filtered = heights.filter(h => h > 0 && h < 50000);
                                return Math.max(...filtered);
                            }
                        """)

                        # Apply max_height limit if specified
                        if max_height and content_height > max_height:
                            content_height = max_height

                        # Use clip parameter to capture only the content area
                        screenshot_options["clip"] = {
                            "x": 0,
                            "y": 0,
                            "width": viewport_width,
                            "height": int(content_height)
                        }
                    elif full_page:
                        screenshot_options["full_page"] = True

                    # Capture screenshot
                    page.screenshot(**screenshot_options)

                    return {
                        "success": True,
                        "screenshot_path": str(screenshot_path),
                        "url": url,
                        "full_page": full_page,
                        "clipped": clip_to_content and full_page,
                        "viewport": f"{viewport_width}x{viewport_height}",
                        "error": None,
                    }

                except PlaywrightTimeout:
                    # Timeout - try to capture what we have anyway
                    try:
                        # Use same clipping logic for partial screenshot
                        page.screenshot(**screenshot_options)
                        return {
                            "success": True,
                            "screenshot_path": str(screenshot_path),
                            "url": url,
                            "warning": f"Page took longer than {timeout_ms/1000}s to load, captured partial screenshot",
                            "error": None,
                        }
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Timeout after {timeout_ms/1000}s and failed to capture partial screenshot: {str(e)}",
                            "screenshot_path": None,
                        }

                finally:
                    browser.close()

        except ImportError:
            return {
                "success": False,
                "error": (
                    "Playwright is not installed. Install it with:\n"
                    "  pip install playwright\n"
                    "  playwright install chromium"
                ),
                "screenshot_path": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to capture screenshot: {str(e)}",
                "screenshot_path": None,
            }

    def list_web_screenshots(self) -> Dict[str, Any]:
        """List all captured web screenshots in the temp directory.

        Returns:
            Dictionary with success, screenshots list, and optional error
        """
        try:
            screenshots = []
            if self.screenshot_dir.exists():
                for screenshot_file in sorted(
                    self.screenshot_dir.glob("*.png"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )[:10]:  # Show 10 most recent
                    stat = screenshot_file.stat()
                    screenshots.append({
                        "path": str(screenshot_file),
                        "name": screenshot_file.name,
                        "size_kb": round(stat.st_size / 1024, 1),
                        "modified": stat.st_mtime,
                    })

            return {
                "success": True,
                "screenshots": screenshots,
                "count": len(screenshots),
                "directory": str(self.screenshot_dir),
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list screenshots: {str(e)}",
                "screenshots": [],
            }

    def clear_web_screenshots(self, keep_recent: int = 5) -> Dict[str, Any]:
        """Clear old web screenshots from temp directory.

        Args:
            keep_recent: Number of most recent screenshots to keep

        Returns:
            Dictionary with success, deleted count, and optional error
        """
        try:
            if not self.screenshot_dir.exists():
                return {
                    "success": True,
                    "deleted_count": 0,
                    "kept_count": 0,
                    "error": None,
                }

            # Get all screenshots sorted by modification time
            screenshots = sorted(
                self.screenshot_dir.glob("*.png"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            # Keep recent, delete old
            kept = screenshots[:keep_recent]
            to_delete = screenshots[keep_recent:]

            deleted_count = 0
            for screenshot_file in to_delete:
                try:
                    screenshot_file.unlink()
                    deleted_count += 1
                except Exception:
                    pass  # Continue deleting others

            return {
                "success": True,
                "deleted_count": deleted_count,
                "kept_count": len(kept),
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to clear screenshots: {str(e)}",
                "deleted_count": 0,
            }
