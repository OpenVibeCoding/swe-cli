"""WebSocket broadcaster for tool execution events."""

from __future__ import annotations

import asyncio
from typing import Any, Dict


class WebSocketToolBroadcaster:
    """Wraps tool registry to broadcast tool execution events via WebSocket."""

    def __init__(self, tool_registry: Any, ws_manager: Any, loop: asyncio.AbstractEventLoop):
        """Initialize broadcaster.

        Args:
            tool_registry: The tool registry to wrap
            ws_manager: WebSocket manager for broadcasting
            loop: Event loop for async operations
        """
        self.tool_registry = tool_registry
        self.ws_manager = ws_manager
        self.loop = loop

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute tool with WebSocket broadcasting.

        Broadcasts tool_call before execution and tool_result after.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            **kwargs: Additional execution context

        Returns:
            Tool execution result
        """
        # Broadcast tool call
        self._broadcast_tool_call(tool_name, arguments)

        # Execute the tool
        result = self.tool_registry.execute_tool(tool_name, arguments, **kwargs)

        # Broadcast tool result
        self._broadcast_tool_result(tool_name, result)

        return result

    def _broadcast_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Broadcast tool call event."""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.ws_manager.broadcast({
                    "type": "tool_call",
                    "data": {
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "description": f"Calling {tool_name}",
                    }
                }),
                self.loop
            )
            future.result(timeout=2)
        except Exception as e:
            print(f"Failed to broadcast tool call: {e}")

    def _broadcast_tool_result(self, tool_name: str, result: Dict[str, Any]) -> None:
        """Broadcast tool result event."""
        try:
            # Extract relevant result info
            success = result.get("success", False)
            output = result.get("output", "")
            error = result.get("error", "")

            result_text = output if success else f"Error: {error}"

            future = asyncio.run_coroutine_threadsafe(
                self.ws_manager.broadcast({
                    "type": "tool_result",
                    "data": {
                        "tool_name": tool_name,
                        "result": "Success" if success else "Failed",
                        "output": result_text,
                    }
                }),
                self.loop
            )
            future.result(timeout=2)
        except Exception as e:
            print(f"Failed to broadcast tool result: {e}")

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes to the wrapped tool registry."""
        return getattr(self.tool_registry, name)
