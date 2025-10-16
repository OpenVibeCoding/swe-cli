"""Handlers for web-related tool invocations."""

from __future__ import annotations

from typing import Any


class WebToolHandler:
    """Executes web fetch operations."""

    def __init__(self, web_fetch_tool: Any) -> None:
        self._web_fetch_tool = web_fetch_tool

    def fetch_url(self, args: dict[str, Any]) -> dict[str, Any]:
        if not self._web_fetch_tool:
            return {"success": False, "error": "WebFetchTool not available"}

        url = args["url"]
        extract_text = args.get("extract_text", True)
        max_length = args.get("max_length", 50000)

        try:
            result = self._web_fetch_tool.fetch_url(
                url=url,
                extract_text=extract_text,
                max_length=max_length,
            )

            if not result["success"]:
                return {"success": False, "error": result["error"], "output": None}

            output = (
                f"Fetched: {result.get('url', url)}\n"
                f"Status: {result.get('status_code', 'unknown')}\n"
                f"Content-Type: {result.get('content_type', 'unknown')}\n"
                f"\n{result['content']}"
            )

            return {"success": True, "output": output, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "output": None}
