"""MCP tool wrapper using langchain-mcp-adapters library for SWE-CLI compatibility.

This module provides a bridge between the langchain-mcp-adapters library
and SWE-CLI's tool infrastructure, preserving all SWE-CLI functionality
while leveraging the robust MCP implementation from langchain-mcp-adapters.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from swecli.core.agents.components.langchain.tools.base import SWECLIToolWrapper


logger = logging.getLogger(__name__)


class MCPLangChainAdaptersTool(SWECLIToolWrapper):
    """SWE-CLI tool wrapper that uses langchain-mcp-adapters for MCP communication.

    This wrapper provides:
    - Integration with langchain-mcp-adapters for robust MCP communication
    - Preservation of SWE-CLI's approval, mode management, and undo systems
    - Individual LangChain tools for each MCP tool
    - Proper parameter handling and schema conversion
    """

    def __init__(
        self,
        server_name: str,
        mcp_manager: Any,
        tool_registry: Any,
    ):
        """Initialize the MCP LangChain adapters tool.

        Args:
            server_name: Name of the MCP server
            mcp_manager: SWE-CLI MCP manager instance
            tool_registry: SWE-CLI tool registry for execution context
        """
        # Initialize with a generic description - individual tools will have their own descriptions
        super().__init__(
            tool_name=f"mcp_{server_name}",
            description=f"MCP server tools from {server_name}",
            tool_registry=tool_registry,
            args_schema=None,  # Will be set dynamically when tools are loaded
        )

        # Set attributes using object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, 'server_name', server_name)
        object.__setattr__(self, 'mcp_manager', mcp_manager)
        object.__setattr__(self, '_mcp_tools', None)
        object.__setattr__(self, '_tools_loaded', False)

    def _load_mcp_tools(self) -> List[BaseTool]:
        """Load MCP tools using langchain-mcp-adapters.

        Returns:
            List of LangChain tools from the MCP server
        """
        if self._tools_loaded and self._mcp_tools is not None:
            return self._mcp_tools

        try:
            # Run the async loading in a sync context
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            self._mcp_tools = loop.run_until_complete(self._load_mcp_tools_async())
            self._tools_loaded = True
            return self._mcp_tools

        except Exception as e:
            logger.error(f"Failed to load MCP tools from {self.server_name}: {e}")
            self._mcp_tools = []
            self._tools_loaded = True
            return []

    async def _load_mcp_tools_async(self) -> List[BaseTool]:
        """Async method to load MCP tools using langchain-mcp-adapters.

        Returns:
            List of LangChain tools from the MCP server
        """
        try:
            from langchain_mcp_adapters.tools import load_mcp_tools

            # Try to get the existing session from the MCP manager
            client_info = None
            if hasattr(self.mcp_manager, 'clients') and self.server_name in self.mcp_manager.clients:
                client_info = self.mcp_manager.clients[self.server_name]

            session = None
            connection = None

            if client_info:
                # Check if we have a session we can use
                if hasattr(client_info, 'session') and client_info.session:
                    session = client_info.session
                else:
                    # Try to create connection from client info
                    connection = self._extract_connection_info(client_info)

            # If no session or connection, try to get from config
            if session is None and connection is None:
                connection = self._get_connection_from_config()

            if session is not None:
                # Load tools using existing session
                tools = await load_mcp_tools(
                    session=session,
                    server_name=self.server_name
                )
            elif connection is not None:
                # Load tools by creating new connection
                tools = await load_mcp_tools(
                    session=None,
                    connection=connection,
                    server_name=self.server_name
                )
            else:
                logger.warning(f"No connection info available for MCP server {self.server_name}")
                return []

            logger.info(f"Loaded {len(tools)} tools from MCP server {self.server_name}")
            return tools

        except Exception as e:
            logger.error(f"Failed to load MCP tools from {self.server_name}: {e}")
            return []

    def _extract_connection_info(self, client_info: Any) -> Optional[Dict[str, Any]]:
        """Extract connection information from client info.

        Args:
            client_info: Client information from MCP manager

        Returns:
            Connection configuration for langchain-mcp-adapters
        """
        try:
            # Try different attribute names that might contain connection info
            connection_info = None

            if hasattr(client_info, 'connection_info'):
                connection_info = client_info.connection_info
            elif hasattr(client_info, 'config'):
                connection_info = client_info.config
            elif hasattr(client_info, 'server_config'):
                connection_info = client_info.server_config

            if connection_info:
                return self._convert_to_langchain_connection(connection_info)

        except Exception as e:
            logger.debug(f"Could not extract connection info: {e}")

        return None

    def _get_connection_from_config(self) -> Optional[Dict[str, Any]]:
        """Get connection information from MCP manager config.

        Returns:
            Connection configuration for langchain-mcp-adapters
        """
        try:
            if hasattr(self.mcp_manager, 'get_server_config'):
                server_config = self.mcp_manager.get_server_config(self.server_name)
                if server_config:
                    return self._convert_to_langchain_connection(server_config)

        except Exception as e:
            logger.debug(f"Could not get connection from config: {e}")

        return None

    def _convert_to_langchain_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert SWE-CLI config to langchain-mcp-adapters connection format.

        Args:
            config: SWE-CLI server configuration

        Returns:
            Connection configuration for langchain-mcp-adapters
        """
        transport = config.get("transport", "stdio")

        if transport == "stdio":
            return {
                "transport": "stdio",
                "command": config.get("command", ""),
                "args": config.get("args", []),
                "env": config.get("env"),
                "cwd": config.get("cwd"),
                "encoding": config.get("encoding", "utf-8"),
            }
        elif transport in ("sse", "http", "streamable_http"):
            return {
                "transport": transport,
                "url": config.get("url", ""),
                "headers": config.get("headers"),
                "timeout": config.get("timeout"),
            }
        else:
            logger.warning(f"Unsupported transport type: {transport}")
            return {}

    def _run(
        self,
        **kwargs: Any,
    ) -> str:
        """Execute MCP tool by delegating to the appropriate langchain-mcp-adapters tool.

        Args:
            **kwargs: Tool arguments including SWE-CLI managers

        Returns:
            Tool execution result
        """
        # Handle special case for tool listing/discovery
        if "list_tools" in kwargs or kwargs.get("_action") == "list":
            return self._list_tools_response()

        # Extract the actual MCP tool to call
        mcp_tool_name = kwargs.pop("mcp_tool_name", None)
        if not mcp_tool_name:
            # If no specific tool specified, list available tools
            return self._list_tools_response()

        # Extract SWE-CLI managers
        mode_manager = kwargs.pop("mode_manager", None)
        approval_manager = kwargs.pop("approval_manager", None)
        undo_manager = kwargs.pop("undo_manager", None)

        # Check if the tool is allowed in current mode
        tool_full_name = f"mcp_{self.server_name}_{mcp_tool_name}"
        if mode_manager and not mode_manager.is_tool_allowed(tool_full_name):
            return f"Error: Tool '{tool_full_name}' is not allowed in {mode_manager.current_mode} mode"

        # Handle approval if required
        if approval_manager:
            approval_result = approval_manager.check_tool_approval(
                tool_full_name,
                kwargs
            )
            if not approval_result.approved:
                return f"Tool execution denied: {approval_result.reason}"

        try:
            # Load MCP tools if not already loaded
            mcp_tools = self._load_mcp_tools()

            # Find the specific tool to execute
            target_tool = None
            for tool in mcp_tools:
                if tool.name == mcp_tool_name or tool.name.endswith(f"_{mcp_tool_name}"):
                    target_tool = tool
                    break

            if not target_tool:
                return f"Error: MCP tool '{mcp_tool_name}' not found on server '{self.server_name}'"

            # Execute the tool using langchain-mcp-adapters
            result = self._execute_mcp_tool(target_tool, kwargs)

            # Record action for undo if undo manager is available
            if undo_manager and isinstance(result, str):
                undo_manager.record_action(
                    tool_full_name,
                    kwargs,
                    result
                )

            return result

        except Exception as e:
            logger.error(f"Failed to execute MCP tool {mcp_tool_name}: {e}")
            return f"Error: MCP tool execution failed - {str(e)}"

    def _execute_mcp_tool(self, tool: BaseTool, args: Dict[str, Any]) -> str:
        """Execute a specific MCP tool.

        Args:
            tool: The LangChain tool to execute
            args: Arguments for the tool

        Returns:
            Tool execution result as string
        """
        try:
            # Run the async tool in sync context
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Execute the tool and format the result
            if hasattr(tool, 'ainvoke'):
                result = loop.run_until_complete(tool.ainvoke(args))
            else:
                result = tool.invoke(args)

            # Format the result for SWE-CLI
            return self._format_mcp_result(result)

        except Exception as e:
            logger.error(f"Error executing MCP tool {tool.name}: {e}")
            return f"Error executing {tool.name}: {str(e)}"

    def _format_mcp_result(self, result: Any) -> str:
        """Format MCP tool result for SWE-CLI.

        Args:
            result: Raw result from MCP tool

        Returns:
            Formatted result string
        """
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            # Extract meaningful content from the result
            if "output" in result:
                return str(result["output"])
            elif "result" in result:
                return str(result["result"])
            else:
                return json.dumps(result, indent=2)
        else:
            return str(result)

    def _list_tools_response(self) -> str:
        """Generate a response listing available MCP tools.

        Returns:
            String listing available tools
        """
        try:
            mcp_tools = self._load_mcp_tools()

            if not mcp_tools:
                return f"No MCP tools available from server '{self.server_name}'"

            tool_list = []
            for tool in mcp_tools:
                tool_info = {
                    "name": tool.name,
                    "description": tool.description or "",
                }
                if tool.args_schema:
                    try:
                        schema = tool.args_schema.model_json_schema()
                        if "properties" in schema:
                            tool_info["parameters"] = list(schema["properties"].keys())
                    except Exception:
                        pass
                tool_list.append(tool_info)

            result = f"MCP tools available from server '{self.server_name}':\n"
            for i, tool_info in enumerate(tool_list, 1):
                result += f"{i}. {tool_info['name']}: {tool_info['description']}\n"
                if "parameters" in tool_info:
                    result += f"   Parameters: {', '.join(tool_info['parameters'])}\n"

            return result

        except Exception as e:
            return f"Error listing MCP tools: {str(e)}"

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get tool schemas for all MCP tools.

        Returns:
            List of tool schemas compatible with SWE-CLI
        """
        try:
            mcp_tools = self._load_mcp_tools()
            schemas = []

            for tool in mcp_tools:
                schema = {
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                    }
                }

                if tool.args_schema:
                    try:
                        schema["function"]["parameters"] = tool.args_schema.model_json_schema()
                    except Exception as e:
                        logger.debug(f"Could not get schema for {tool.name}: {e}")
                        schema["function"]["parameters"] = {"type": "object", "properties": {}}

                schemas.append(schema)

            return schemas

        except Exception as e:
            logger.error(f"Failed to get MCP tool schemas: {e}")
            return []