"""MCP viewer modal management for SWE-CLI chat interface."""

from __future__ import annotations

import asyncio
from typing import Optional, Dict, List, Any, Tuple


class MCPViewerModalManager:
    """Manages MCP viewer modal state, display, and user interactions."""

    def __init__(self, chat_app):
        """Initialize MCP viewer modal manager.

        Args:
            chat_app: The ChatApplication instance for callbacks
        """
        self.chat_app = chat_app
        self.reset_state()

    def reset_state(self) -> None:
        """Reset MCP viewer modal state to defaults."""
        self._viewer_mode = False
        self._selected_index = 0
        self._viewer_result = {"done": False, "action": None}
        self._view_mode = "server"  # "server", "tools", or "tool_detail"
        self._tools_scroll_offset = 0
        self._tools_per_page = 20
        self._selected_tool = None  # Currently selected tool for detail view

        # Server data
        self._server_name = ""
        self._server_config = {}
        self._is_connected = False
        self._tools = []
        self._capabilities = []
        self._config_location = ""

    def is_in_viewer_mode(self) -> bool:
        """Check if viewer mode is currently active."""
        return self._viewer_mode

    async def show_mcp_viewer(
        self,
        server_name: str,
        server_config: Dict[str, Any],
        is_connected: bool,
        tools: List[Dict[str, str]],
        capabilities: List[str],
        config_location: str,
    ) -> Tuple[bool, Optional[str]]:
        """Show MCP viewer modal with arrow key navigation.

        Args:
            server_name: Name of the MCP server
            server_config: Server configuration
            is_connected: Whether server is connected
            tools: List of available tools
            capabilities: Server capabilities
            config_location: Path to config file

        Returns:
            Tuple of (action_taken: bool, action: str or None)
                action can be: "reconnect", "connect", "disable", "enable", or None
        """
        from swecli.ui.components.mcp_viewer_message import create_mcp_viewer_message

        # Reset state for new viewer
        self.reset_state()

        # Store server data
        self._server_name = server_name
        self._server_config = server_config
        self._is_connected = is_connected
        self._tools = tools
        self._capabilities = capabilities
        self._config_location = config_location

        # CRITICAL: Unlock input buffer before clearing it
        self.chat_app._input_locked = False

        # Clear input buffer
        self.chat_app.input_buffer.text = ""
        self.chat_app.input_buffer.cursor_position = 0

        # Set up viewer mode state (activates key handlers)
        self._viewer_mode = True

        # Add initial viewer message to conversation (as assistant message for proper display)
        viewer_msg = create_mcp_viewer_message(
            server_name=self._server_name,
            server_config=self._server_config,
            is_connected=self._is_connected,
            tools=self._tools,
            capabilities=self._capabilities,
            config_location=self._config_location,
            selected_index=self._selected_index,
            view_mode=self._view_mode,
            tools_scroll_offset=self._tools_scroll_offset,
            tools_per_page=self._tools_per_page,
            selected_tool=self._selected_tool,
        )
        self.chat_app.conversation.add_assistant_message(viewer_msg)
        self.chat_app._update_conversation_buffer()

        # Position conversation for viewer visibility
        self._position_conversation_for_viewer()

        self.chat_app.app.invalidate()

        try:
            # Wait for user to make a selection
            result = await self._wait_for_user_action()

        finally:
            # Clean up viewer mode
            await self._cleanup_viewer_mode()

        # Remove the viewer message from conversation
        self._remove_viewer_message()

        # Re-enable auto-scroll after viewer is done
        if (hasattr(self.chat_app, 'layout_manager') and
            hasattr(self.chat_app.layout_manager, 'get_conversation_control')):
            conversation_control = self.chat_app.layout_manager.get_conversation_control()
            conversation_control._auto_scroll = True

        self.chat_app.app.invalidate()

        return (result["action"] is not None, result["action"])

    def _position_conversation_for_viewer(self) -> None:
        """Position conversation to show viewer message properly."""
        if (hasattr(self.chat_app, 'layout_manager') and
            hasattr(self.chat_app.layout_manager, 'get_conversation_control')):
            conversation_control = self.chat_app.layout_manager.get_conversation_control()
            # Scroll to bottom to show the viewer
            conversation_control.scroll_to_bottom()
            self.chat_app.app.invalidate()

    async def _wait_for_user_action(self) -> dict:
        """Wait for user to make an action."""
        while not self._viewer_result["done"]:
            await asyncio.sleep(0.05)
        return self._viewer_result

    async def _cleanup_viewer_mode(self) -> None:
        """Clean up viewer mode state."""
        self._viewer_mode = False
        self.chat_app._input_locked = False
        self.chat_app.app.invalidate()

    def _remove_viewer_message(self) -> None:
        """Remove the viewer message from conversation."""
        if self.chat_app.conversation.messages:
            self.chat_app.conversation.messages.pop()
            self.chat_app._update_conversation_buffer()

    def handle_viewer_up(self) -> bool:
        """Handle up arrow in viewer mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._viewer_mode:
            return False

        if self._view_mode == "server":
            # Server view - navigate menu options
            if self._selected_index > 0:
                self._selected_index -= 1
                self._update_viewer_message()
        elif self._view_mode == "tools":
            # Tools view - scroll up
            if self._selected_index > 0:
                self._selected_index -= 1
                # Adjust scroll offset if needed
                if self._selected_index < self._tools_scroll_offset:
                    self._tools_scroll_offset = max(0, self._tools_scroll_offset - 1)
                self._update_viewer_message()
        # In tool_detail view, up/down don't do anything
        return True

    def handle_viewer_down(self) -> bool:
        """Handle down arrow in viewer mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._viewer_mode:
            return False

        if self._view_mode == "server":
            # Server view - navigate menu options (3 options: View tools, Reconnect/Connect, Disable/Enable)
            if self._selected_index < 2:
                self._selected_index += 1
                self._update_viewer_message()
        elif self._view_mode == "tools":
            # Tools view - scroll down
            if self._selected_index < len(self._tools) - 1:
                self._selected_index += 1
                # Adjust scroll offset if needed
                if self._selected_index >= self._tools_scroll_offset + self._tools_per_page:
                    self._tools_scroll_offset = min(
                        max(0, len(self._tools) - self._tools_per_page),
                        self._tools_scroll_offset + 1
                    )
                self._update_viewer_message()
        # In tool_detail view, up/down don't do anything
        return True

    def handle_viewer_enter(self) -> bool:
        """Handle enter in viewer mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._viewer_mode:
            return False

        if self._view_mode == "server":
            # Handle menu selection
            if self._selected_index == 0:
                # View tools
                self._view_mode = "tools"
                self._selected_index = 0
                self._tools_scroll_offset = 0
                self._update_viewer_message()
            elif self._selected_index == 1:
                # Reconnect/Connect
                self._viewer_result["action"] = "reconnect" if self._is_connected else "connect"
                self._viewer_result["done"] = True
            elif self._selected_index == 2:
                # Disable/Enable
                self._viewer_result["action"] = "disable" if self._server_config.get("enabled", True) else "enable"
                self._viewer_result["done"] = True
        elif self._view_mode == "tools":
            # View tool details
            if 0 <= self._selected_index < len(self._tools):
                self._selected_tool = self._tools[self._selected_index]
                self._view_mode = "tool_detail"
                self._update_viewer_message()
        # In tool_detail view, enter doesn't do anything

        return True

    def handle_viewer_escape(self) -> bool:
        """Handle escape in viewer mode.

        Returns:
            True if the event was handled, False otherwise
        """
        if not self._viewer_mode:
            return False

        if self._view_mode == "tool_detail":
            # Go back to tools list
            self._view_mode = "tools"
            self._selected_tool = None
            self._update_viewer_message()
        elif self._view_mode == "tools":
            # Go back to server view
            self._view_mode = "server"
            self._selected_index = 0
            self._update_viewer_message()
        else:
            # Close viewer
            self._viewer_result["action"] = None
            self._viewer_result["done"] = True

        return True

    def _update_viewer_message(self) -> None:
        """Update the viewer message with new selection."""
        from swecli.ui.components.mcp_viewer_message import create_mcp_viewer_message

        viewer_msg = create_mcp_viewer_message(
            server_name=self._server_name,
            server_config=self._server_config,
            is_connected=self._is_connected,
            tools=self._tools,
            capabilities=self._capabilities,
            config_location=self._config_location,
            selected_index=self._selected_index,
            view_mode=self._view_mode,
            tools_scroll_offset=self._tools_scroll_offset,
            tools_per_page=self._tools_per_page,
            selected_tool=self._selected_tool,
        )

        if self.chat_app.conversation.messages:
            # Update last message (the viewer) - keep as assistant message
            self.chat_app.conversation.messages[-1] = (
                "assistant",
                viewer_msg,
                self.chat_app.conversation.messages[-1][2] if len(self.chat_app.conversation.messages[-1]) > 2 else None,
            )
            self.chat_app._update_conversation_buffer()
            self.chat_app.app.invalidate()
