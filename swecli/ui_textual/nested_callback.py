"""Nested UI callback wrapper for subagent tool call display."""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class UICallback(Protocol):
    """Protocol for UI callbacks that receive tool events."""

    def on_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> None:
        """Called when a tool call is about to be executed."""
        ...

    def on_tool_result(self, tool_name: str, tool_args: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Called when a tool execution completes."""
        ...


class NestedUICallback:
    """Wraps a UI callback to add nesting/indentation context for subagent tool calls.

    This wrapper intercepts tool events from subagents and forwards them to the parent
    callback with additional nesting information (depth and parent context).
    """

    def __init__(
        self,
        parent_callback: Any,
        parent_context: str,
        depth: int = 1,
    ) -> None:
        """Initialize the nested callback wrapper.

        Args:
            parent_callback: The parent UI callback to forward events to
            parent_context: Name/identifier of the parent subagent (e.g., "researcher")
            depth: Nesting depth level (1 = direct child of main agent)
        """
        self._parent = parent_callback
        self._context = parent_context
        self._depth = depth

    def on_thinking_start(self) -> None:
        """Called when the agent starts thinking."""
        # Don't forward thinking events from subagents
        pass

    def on_thinking_complete(self) -> None:
        """Called when the agent completes thinking."""
        # Don't forward thinking events from subagents
        pass

    def on_assistant_message(self, content: str) -> None:
        """Called when assistant provides a message.

        Args:
            content: The assistant's message
        """
        # Don't forward assistant messages from subagents (they'll appear as final result)
        pass

    def on_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> None:
        """Called when a tool call is about to be executed.

        Forwards to parent as a nested tool call with depth information.

        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments for the tool call
        """
        if self._parent is None:
            return

        # Check if parent supports nested tool calls
        if hasattr(self._parent, "on_nested_tool_call"):
            self._parent.on_nested_tool_call(
                tool_name,
                tool_args,
                depth=self._depth,
                parent=self._context,
            )
        elif hasattr(self._parent, "on_tool_call"):
            # Fallback: use regular tool call (loses nesting info)
            self._parent.on_tool_call(tool_name, tool_args)

    def on_tool_result(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Called when a tool execution completes.

        Forwards to parent as a nested tool result with depth information.

        Args:
            tool_name: Name of the tool that was executed
            tool_args: Arguments that were used
            result: Result of the tool execution
        """
        if self._parent is None:
            return

        # Check if parent supports nested tool results
        if hasattr(self._parent, "on_nested_tool_result"):
            self._parent.on_nested_tool_result(
                tool_name,
                tool_args,
                result,
                depth=self._depth,
                parent=self._context,
            )
        elif hasattr(self._parent, "on_tool_result"):
            # Fallback: use regular tool result (loses nesting info)
            self._parent.on_tool_result(tool_name, tool_args, result)

    def on_interrupt(self) -> None:
        """Called when execution is interrupted."""
        # Forward interrupt to parent
        if self._parent and hasattr(self._parent, "on_interrupt"):
            self._parent.on_interrupt()

    def on_debug(self, message: str, prefix: str = "DEBUG") -> None:
        """Called to display debug information.

        Args:
            message: The debug message
            prefix: Optional prefix for categorizing
        """
        # Forward debug with context prefix
        if self._parent and hasattr(self._parent, "on_debug"):
            self._parent.on_debug(f"[{self._context}] {message}", prefix)

    def create_nested(self, child_context: str) -> "NestedUICallback":
        """Create a further nested callback for child subagents.

        Args:
            child_context: Name/identifier of the child subagent

        Returns:
            A new NestedUICallback with incremented depth
        """
        return NestedUICallback(
            parent_callback=self._parent,
            parent_context=child_context,
            depth=self._depth + 1,
        )
