"""Screenshot capture tool handler."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


class ScreenshotToolHandler:
    """Handles screenshot capture functionality."""

    def __init__(self, temp_dir: Optional[Path] = None):
        """Initialize screenshot handler.

        Args:
            temp_dir: Optional temporary directory for screenshots
        """
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "swecli_screenshots"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def capture_screenshot(self, args: dict[str, Any]) -> dict[str, Any]:
        """Capture a screenshot and save to temporary location.

        Args:
            args: Dictionary containing optional parameters:
                - monitor: Monitor number to capture (default: 1 for primary)
                - region: Optional dict with x, y, width, height for partial capture

        Returns:
            Dictionary with success status, file path, and any errors
        """
        if not MSS_AVAILABLE:
            return {
                "success": False,
                "error": "Screenshot functionality requires 'mss' package. Install with: pip install mss",
                "path": None,
            }

        try:
            # Get parameters
            monitor_num = args.get("monitor", 1)
            region = args.get("region")

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = self.temp_dir / filename

            # Capture screenshot
            with mss.mss() as sct:
                if region:
                    # Capture specific region
                    monitor = {
                        "left": region["x"],
                        "top": region["y"],
                        "width": region["width"],
                        "height": region["height"],
                    }
                else:
                    # Capture full monitor
                    monitor = sct.monitors[monitor_num]

                # Save screenshot
                screenshot = sct.grab(monitor)
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=str(filepath))

            return {
                "success": True,
                "path": str(filepath),
                "output": f"Screenshot saved to: {filepath}\n\nYou can now reference this image in your queries by mentioning the path:\n@{filepath}",
                "error": None,
            }

        except IndexError:
            return {
                "success": False,
                "error": f"Monitor {monitor_num} not found. Available monitors: {len(mss.mss().monitors) - 1}",
                "path": None,
            }
        except Exception as exc:
            return {
                "success": False,
                "error": f"Failed to capture screenshot: {str(exc)}",
                "path": None,
            }

    def list_screenshots(self) -> dict[str, Any]:
        """List all captured screenshots in temporary directory.

        Returns:
            Dictionary with success status and list of screenshots
        """
        try:
            screenshots = sorted(
                self.temp_dir.glob("screenshot_*.png"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            if not screenshots:
                output = "No screenshots found in temporary directory."
            else:
                lines = ["Recent screenshots:"]
                for idx, screenshot in enumerate(screenshots[:10], 1):
                    stat = screenshot.stat()
                    size_mb = stat.st_size / (1024 * 1024)
                    timestamp = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    lines.append(f"  {idx}. {screenshot.name} ({size_mb:.2f} MB) - {timestamp}")
                    lines.append(f"     Path: {screenshot}")
                output = "\n".join(lines)

            return {
                "success": True,
                "output": output,
                "screenshots": [str(s) for s in screenshots],
                "error": None,
            }

        except Exception as exc:
            return {
                "success": False,
                "error": f"Failed to list screenshots: {str(exc)}",
                "screenshots": [],
                "output": None,
            }

    def clear_screenshots(self, args: dict[str, Any]) -> dict[str, Any]:
        """Clear old screenshots from temporary directory.

        Args:
            args: Dictionary containing optional parameters:
                - keep_recent: Number of recent screenshots to keep (default: 5)

        Returns:
            Dictionary with success status and count of deleted files
        """
        try:
            keep_recent = args.get("keep_recent", 5)

            screenshots = sorted(
                self.temp_dir.glob("screenshot_*.png"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            # Keep the most recent ones
            to_delete = screenshots[keep_recent:]
            deleted_count = 0

            for screenshot in to_delete:
                screenshot.unlink()
                deleted_count += 1

            if deleted_count == 0:
                output = f"No screenshots to delete (keeping {keep_recent} most recent)"
            else:
                output = f"Deleted {deleted_count} old screenshot(s), kept {min(len(screenshots), keep_recent)} recent"

            return {
                "success": True,
                "output": output,
                "deleted_count": deleted_count,
                "error": None,
            }

        except Exception as exc:
            return {
                "success": False,
                "error": f"Failed to clear screenshots: {str(exc)}",
                "deleted_count": 0,
                "output": None,
            }
