"""Handler for MCP tool invocations."""

from __future__ import annotations

from typing import Any


class McpToolHandler:
    """Executes MCP-backed tools via the manager."""

    def __init__(self, mcp_manager: Any) -> None:
        self._mcp_manager = mcp_manager

    def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if not self._mcp_manager:
            return {
                "success": False,
                "error": "MCP manager not initialized",
                "output": None,
            }

        parts = tool_name.split("__")
        if len(parts) < 3:
            return {
                "success": False,
                "error": f"Invalid MCP tool name format: {tool_name}",
                "output": None,
            }

        server_name = parts[1]
        mcp_tool_name = "__".join(parts[2:])

        if not self._mcp_manager.is_connected(server_name):
            return {
                "success": False,
                "error": f"MCP server '{server_name}' is not connected",
                "output": None,
            }

        try:
            return self._mcp_manager.call_tool_sync(server_name, mcp_tool_name, args)
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "error": f"MCP tool execution failed: {exc}",
                "output": None,
            }
