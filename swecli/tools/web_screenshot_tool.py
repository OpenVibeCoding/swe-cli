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
                        # First, scroll through the page to trigger lazy-loaded content
                        # Get total scrollable height
                        total_height = page.evaluate("document.body.scrollHeight")
                        viewport_height = page.evaluate("window.innerHeight")

                        # Scroll down in steps to trigger lazy loading
                        current_position = 0
                        scroll_step = viewport_height

                        while current_position < total_height:
                            page.evaluate(f"window.scrollTo(0, {current_position})")
                            page.wait_for_timeout(100)  # Small delay for lazy content
                            current_position += scroll_step
                            # Update total height in case new content loaded
                            new_height = page.evaluate("document.body.scrollHeight")
                            if new_height > total_height:
                                total_height = new_height

                        # Scroll back to top
                        page.evaluate("window.scrollTo(0, 0)")
                        page.wait_for_timeout(200)

                        # Detect actual content height intelligently
                        content_height = page.evaluate("""
                            () => {
                                // Find the last element with meaningful content
                                const body = document.body;
                                const html = document.documentElement;

                                let lastContentBottom = 0;
                                const elements = Array.from(document.querySelectorAll('*'));

                                for (const el of elements) {
                                    // Skip structural/container elements
                                    if (el.tagName === 'HTML' || el.tagName === 'BODY' || el.tagName === 'HEAD') {
                                        continue;
                                    }

                                    // Skip hidden, empty, or whitespace-only elements
                                    const style = window.getComputedStyle(el);
                                    if (style.display === 'none' ||
                                        style.visibility === 'hidden' ||
                                        style.opacity === '0') {
                                        continue;
                                    }

                                    // Check if element has meaningful content
                                    const hasText = el.textContent?.trim().length > 0;
                                    const hasImage = el.tagName === 'IMG' || el.tagName === 'SVG';
                                    const hasCanvas = el.tagName === 'CANVAS';
                                    const hasVideo = el.tagName === 'VIDEO';
                                    const hasBackgroundImage = style.backgroundImage &&
                                                               style.backgroundImage !== 'none';

                                    // Check if element has visible dimensions
                                    const rect = el.getBoundingClientRect();
                                    const hasVisibleSize = rect.width > 0 && rect.height > 0;

                                    if (hasVisibleSize && (hasText || hasImage || hasCanvas ||
                                                          hasVideo || hasBackgroundImage)) {
                                        // Calculate absolute position from top of document
                                        // Use offsetTop for more reliable absolute positioning
                                        let offsetTop = 0;
                                        let element = el;
                                        while (element) {
                                            offsetTop += element.offsetTop || 0;
                                            element = element.offsetParent;
                                        }
                                        const bottom = offsetTop + el.offsetHeight;

                                        if (bottom > lastContentBottom) {
                                            lastContentBottom = bottom;
                                        }
                                    }
                                }

                                // Add some padding to ensure we don't clip too aggressively
                                const padding = 100;
                                let finalHeight = lastContentBottom + padding;

                                // Also check document height as fallback
                                const docHeight = Math.max(
                                    body.scrollHeight,
                                    body.offsetHeight,
                                    html.scrollHeight,
                                    html.offsetHeight
                                );

                                // If detected content height is very close to document height,
                                // use document height (likely a legitimately long page)
                                if (finalHeight > docHeight * 0.9) {
                                    finalHeight = docHeight;
                                } else {
                                    // Only apply minimum height if content is reasonably tall
                                    // Otherwise keep the detected content height to remove whitespace
                                    const minHeight = window.innerHeight;
                                    if (finalHeight < minHeight && finalHeight > docHeight * 0.5) {
                                        // Content is between 50-90% of page, use viewport as minimum
                                        finalHeight = minHeight;
                                    }
                                    // If content is < 50% of page height, keep detected height (whitespace page)
                                }

                                return finalHeight;
                            }
                        """)

                        # Get document height for comparison
                        doc_height = page.evaluate("document.body.scrollHeight")

                        # Apply max_height limit if specified
                        if max_height and content_height > max_height:
                            content_height = max_height

                        # Always use full_page to capture scrollable content
                        screenshot_options["full_page"] = True
                        page.screenshot(**screenshot_options)

                        # If content height is significantly less than document height,
                        # crop the image to remove excessive whitespace
                        if content_height < doc_height * 0.95:  # More than 5% whitespace
                            from PIL import Image
                            img = Image.open(str(screenshot_path))
                            # Crop to content height
                            cropped = img.crop((0, 0, img.width, int(content_height)))
                            cropped.save(str(screenshot_path))

                    elif full_page:
                        screenshot_options["full_page"] = True
                        page.screenshot(**screenshot_options)
                    else:
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
                    # Timeout - try to capture what we have anyway with a simple screenshot
                    try:
                        # Use simple full_page screenshot for timeout case
                        page.screenshot(path=str(screenshot_path), full_page=full_page)
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
