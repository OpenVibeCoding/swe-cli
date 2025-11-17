"""DEPRECATED: LangChain MCP adapter that bridges SWE-CLI MCP tools to LangChain.

This adapter has been replaced by MCPLangChainAdaptersTool which uses
the official langchain-mcp-adapters library. This file is kept for
backward compatibility only and should not be used in new code.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from swecli.mcp.manager import MCPManager


logger = logging.getLogger(__name__)


class MCPLangChainAdapter:
    """Adapter that bridges SWE-CLI MCP tools to LangChain BaseTool format.

    This adapter uses the existing SWE-CLI MCP implementation (based on FastMCP)
    and provides clean LangChain tool wrappers without duplicating MCP functionality.
    """

    def __init__(self, mcp_manager: Optional[MCPManager] = None):
        """Initialize the MCP LangChain adapter.

        Args:
            mcp_manager: SWE-CLI MCP manager instance
        """
        self.mcp_manager = mcp_manager

    def set_mcp_manager(self, mcp_manager: MCPManager) -> None:
        """Update the MCP manager.

        Args:
            mcp_manager: New MCP manager instance
        """
        self.mcp_manager = mcp_manager

    def get_connected_servers(self) -> List[str]:
        """Get list of connected MCP servers.

        Returns:
            List of server names that are connected
        """
        if not self.mcp_manager:
            return []

        # Use existing MCPManager clients
        return list(self.mcp_manager.clients.keys())

    def get_server_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Get tools available from a specific MCP server.

        Args:
            server_name: Name of the MCP server

        Returns:
            List of tool definitions from the server
        """
        if not self.mcp_manager:
            return []

        # Use existing MCPManager server_tools
        return self.mcp_manager.get_server_tools(server_name)

    def get_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all available tools from all connected MCP servers.

        Returns:
            Dictionary mapping server names to their tool lists
        """
        if not self.mcp_manager:
            return {}

        all_tools = {}
        connected_servers = self.get_connected_servers()

        for server_name in connected_servers:
            tools = self.get_server_tools(server_name)
            if tools:
                all_tools[server_name] = tools

        return all_tools

    def execute_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool through the existing manager.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to execute
            arguments: Arguments for the tool

        Returns:
            Result dictionary compatible with SWE-CLI format
        """
        if not self.mcp_manager:
            return {
                "success": False,
                "error": "MCP manager not initialized",
                "output": None,
            }

        try:
            # Use existing MCPManager call_tool_sync method
            result = self.mcp_manager.call_tool_sync(server_name, tool_name, arguments)
            return result
        except Exception as exc:
            logger.error(f"MCP tool execution failed: {exc}")
            return {
                "success": False,
                "error": f"MCP tool execution failed: {exc}",
                "output": None,
            }

    def is_server_connected(self, server_name: str) -> bool:
        """Check if an MCP server is connected and ready.

        Args:
            server_name: Name of the MCP server

        Returns:
            True if server is connected, False otherwise
        """
        if not self.mcp_manager:
            return False

        # Use existing MCPManager is_connected method
        return self.mcp_manager.is_connected(server_name)

    def refresh_tools(self) -> None:
        """Force refresh of available MCP tools."""
        if self.mcp_manager:
            # Force reconnection and tool discovery
            logger.info("Refreshing MCP connections and tools")
            # Note: MCPManager handles reconnection automatically