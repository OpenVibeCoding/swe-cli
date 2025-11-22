"""Base class for LangChain tool wrappers that preserve SWE-CLI functionality."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Type, Union

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from swecli.core.interfaces.tool_interface import ToolInterface


class SWECLIToolWrapper(BaseTool):
    """Base wrapper for SWE-CLI tools to make them compatible with LangChain.

    This wrapper preserves all SWE-CLI functionality including:
    - Permission and approval systems
    - Context-aware execution
    - Undo/redo capabilities
    - Plan mode restrictions
    - Tool result formatting
    """

    def __init__(
        self,
        tool_name: str,
        description: str,
        tool_registry: Any,
        args_schema: Optional[Type[BaseModel]] = None,
        **kwargs: Any,
    ):
        """Initialize the wrapper.

        Args:
            tool_name: Name of the SWE-CLI tool
            description: Description for LangChain
            tool_registry: SWE-CLI tool registry for execution
            args_schema: Pydantic schema for arguments
            **kwargs: Additional arguments for BaseTool
        """
        # Initialize Pydantic model first
        super().__init__(
            name=tool_name,
            description=description,
            args_schema=args_schema,
            **kwargs,
        )

        # Then set our attributes using object.__setattr__ to bypass Pydantic
        object.__setattr__(self, '_swetool_name', tool_name)
        object.__setattr__(self, '_swetool_registry', tool_registry)

    def _run(
        self,
        *args: Any,
        mode_manager: Optional[Any] = None,
        approval_manager: Optional[Any] = None,
        undo_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        """Execute the SWE-CLI tool via the tool registry.

        Args:
            *args: Positional arguments (unused for SWE-CLI tools)
            mode_manager: Operation mode manager (optional, uses registry's if None)
            approval_manager: Approval workflow manager (optional)
            undo_manager: Undo/redo manager (optional)
            **kwargs: Tool arguments

        Returns:
            Formatted tool result as string
        """
        try:
            # Prepare execution arguments - only include managers if provided
            exec_kwargs = {
                "tool_name": self._swetool_name,
                "arguments": kwargs,
            }

            # Add optional managers only if provided
            if mode_manager is not None:
                exec_kwargs["mode_manager"] = mode_manager
            if approval_manager is not None:
                exec_kwargs["approval_manager"] = approval_manager
            if undo_manager is not None:
                exec_kwargs["undo_manager"] = undo_manager

            # Execute the tool through SWE-CLI's tool registry
            result = self._swetool_registry.execute_tool(**exec_kwargs)

            # Format the result for LangChain
            return self._format_result(result)

        except Exception as e:
            # Handle any unexpected errors
            import traceback
            error_trace = traceback.format_exc()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Tool execution error for {self._swetool_name}: {e}\n{error_trace}")
            return f"Error executing {self._swetool_name}: {str(e)}"

    async def _arun(
        self,
        *args: Any,
        mode_manager: Optional[Any] = None,
        approval_manager: Optional[Any] = None,
        undo_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        """Async execution - runs sync tool in thread pool."""
        import asyncio
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"[ASYNC] Executing {self._swetool_name} asynchronously")

        try:
            # Run the synchronous _run method in a thread pool
            # This prevents blocking the async event loop
            result = await asyncio.to_thread(
                self._run,
                *args,
                mode_manager=mode_manager,
                approval_manager=approval_manager,
                undo_manager=undo_manager,
                **kwargs
            )
            logger.info(f"[ASYNC] {self._swetool_name} completed successfully")
            return result

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"[ASYNC] Tool execution error for {self._swetool_name}: {e}\n{error_trace}")
            return f"Error executing {self._swetool_name}: {str(e)}"

    def _format_result(self, result: Dict[str, Any]) -> str:
        """Format SWE-CLI tool result for LangChain consumption.

        Args:
            result: Raw result from SWE-CLI tool execution

        Returns:
            Formatted result string
        """
        if not result.get("success", False):
            # Handle error cases
            error = result.get("error", "Unknown error")
            if result.get("plan_only"):
                return f"Plan-only restriction: {error}"
            return f"Tool execution failed: {error}"

        # Extract meaningful content
        output_parts = []

        # Add main output
        if result.get("output"):
            output_parts.append(str(result["output"]))

        # Add additional metadata for specific tools
        if self._swetool_name == "write_file" and result.get("file_path"):
            output_parts.append(f"File written: {result['file_path']}")

        elif self._swetool_name == "edit_file" and result.get("file_path"):
            if result.get("backup_created"):
                output_parts.append(f"Backup created: {result['backup_path']}")
            output_parts.append(f"File edited: {result['file_path']}")

        elif self._swetool_name == "capture_screenshot" and result.get("screenshot_path"):
            output_parts.append(f"Screenshot saved: {result['screenshot_path']}")

        elif self._swetool_name == "capture_web_screenshot":
            if result.get("screenshot_path"):
                output_parts.append(f"Screenshot saved: {result['screenshot_path']}")
            if result.get("pdf_path"):
                output_parts.append(f"PDF saved: {result['pdf_path']}")

        elif self._swetool_name == "analyze_image":
            if result.get("model"):
                output_parts.append(f"Analysis model: {result['model']}")
            if result.get("provider"):
                output_parts.append(f"Provider: {result['provider']}")

        return "\n".join(output_parts) if output_parts else "Tool executed successfully"

    @classmethod
    def create_schema_for_tool(cls, tool_name: str, existing_schemas: list[dict]) -> Optional[Type[BaseModel]]:
        """Create a Pydantic schema from existing tool schema.

        Args:
            tool_name: Name of the tool
            existing_schemas: List of existing tool schemas

        Returns:
            Pydantic schema class or None
        """
        # Find the schema for this tool
        tool_schema = None
        for schema in existing_schemas:
            if schema.get("function", {}).get("name") == tool_name:
                tool_schema = schema["function"]
                break

        if not tool_schema:
            return None

        # Extract parameters
        parameters = tool_schema.get("parameters", {})
        properties = parameters.get("properties", {})
        required = parameters.get("required", [])

        # Create dynamic Pydantic model
        fields = {}
        for param_name, param_info in properties.items():
            field_type = cls._map_json_type_to_python(param_info)
            fields[param_name] = (
                field_type,
                Field(
                    description=param_info.get("description", ""),
                    default=... if param_name in required else None,
                ),
            )

        return type(f"{tool_name.title()}Schema", (BaseModel,), fields)

    @staticmethod
    def _map_json_type_to_python(param_info: dict) -> Type:
        """Map JSON schema type to Python type.

        Args:
            param_info: Parameter information from JSON schema

        Returns:
            Python type
        """
        param_type = param_info.get("type", "string")
        param_format = param_info.get("format", "")

        if param_type == "string":
            if param_format == "uri":
                return str  # Could be more specific, but str is fine
            return str
        elif param_type == "integer":
            return int
        elif param_type == "number":
            return float
        elif param_type == "boolean":
            return bool
        elif param_type == "array":
            # For arrays, we'll use a list of strings by default
            # In a more sophisticated implementation, we could handle nested schemas
            return list
        elif param_type == "object":
            return dict
        else:
            return str  # Default to str


class ToolRegistryAdapter:
    """Adapter to make SWE-CLI tool registry compatible with LangChain tool discovery."""

    def __init__(self, tool_registry: Any):
        """Initialize the adapter.

        Args:
            tool_registry: SWE-CLI tool registry instance
        """
        self.tool_registry = tool_registry
        self._langchain_tools: Optional[list[BaseTool]] = None
        self._mcp_adapter = None
        self._mcp_tools_created = False

    def get_langchain_tools(self, force_refresh: bool = False) -> list[BaseTool]:
        """Get LangChain-compatible tools from the SWE-CLI registry.

        Args:
            force_refresh: If True, force recreation of tools even if cached

        Returns:
            List of LangChain BaseTool instances
        """
        if force_refresh or self._langchain_tools is None:
            self._langchain_tools = self._create_langchain_tools()

        return self._langchain_tools

    def refresh_tools(self) -> None:
        """Force refresh of cached tools to pick up updated ordering."""
        self._langchain_tools = None

    def _create_langchain_tools(self) -> list[BaseTool]:
        """Create LangChain tool instances from SWE-CLI registry.

        NOTE: File operation tools (read_file, write_file, edit_file, ls, grep, glob)
        are provided by Deep Agent's built-in FilesystemMiddleware. We only register
        custom tools that provide unique functionality not available in Deep Agents.

        Returns:
            List of LangChain BaseTool instances
        """
        # File tools are now handled by Deep Agent's built-in FilesystemMiddleware
        # No need to import file_tools

        from .bash_tools import (
            RunCommandTool, ListProcessesTool,
            GetProcessOutputTool, KillProcessTool
        )
        from .web_tools import (
            FetchUrlTool, OpenBrowserTool,
            CaptureWebScreenshotTool, ListWebScreenshotsTool,
            ClearWebScreenshotsTool
        )
        from .screenshot_tools import (
            CaptureScreenshotTool, ListScreenshotsTool, ClearScreenshotsTool
        )
        from .vlm_tools import AnalyzeImageTool
        # Todo tools removed - using Deep Agent's built-in TodoListMiddleware (write_todos)

        # Create custom tools (built-in file and todo tools are provided by Deep Agent)
        base_tools = [
            # File operations: read_file, write_file, edit_file, ls, grep, glob
            # are provided by Deep Agent's FilesystemMiddleware - NOT included here

            # Todo operations: write_todos is provided by Deep Agent's TodoListMiddleware
            # - NOT included here

            # Process operations (custom - not in Deep Agent)
            RunCommandTool(self.tool_registry),
            ListProcessesTool(self.tool_registry),
            GetProcessOutputTool(self.tool_registry),
            KillProcessTool(self.tool_registry),

            # Web operations (custom - not in Deep Agent)
            FetchUrlTool(self.tool_registry),
            OpenBrowserTool(self.tool_registry),

            # Screenshot operations (custom - not in Deep Agent)
            CaptureScreenshotTool(self.tool_registry),
            ListScreenshotsTool(self.tool_registry),
            ClearScreenshotsTool(self.tool_registry),
            CaptureWebScreenshotTool(self.tool_registry),
            ListWebScreenshotsTool(self.tool_registry),
            ClearWebScreenshotsTool(self.tool_registry),
        ]

        # Add VLM tool conditionally based on configuration
        # Only include if VLM model is configured
        if self._is_vlm_available():
            base_tools.append(AnalyzeImageTool(self.tool_registry))
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("VLM tool is available and included in tool list")
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("VLM tool not configured, skipping AnalyzeImageTool")

        # Add individual todo management tools for proper workflow
        # write_todos is built-in to Deep Agent, but update_todo and complete_todo are custom
        from .todo_tools import UpdateTodoTool, CompleteTodoTool
        base_tools.extend([
            UpdateTodoTool(self.tool_registry),
            CompleteTodoTool(self.tool_registry),
        ])
        import logging
        logger = logging.getLogger(__name__)
        logger.debug("Added individual todo management tools (update_todo, complete_todo)")

        # Create MCP tools
        mcp_tools = self._create_mcp_tools()

        # 🔧 IMPORTANT: Put MCP tools FIRST to ensure LLM sees specific API tools before generic ones
        # This fixes the issue where LLM chooses generic 'search' over GitHub-specific tools
        if mcp_tools:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Placing {len(mcp_tools)} MCP tools first, followed by {len(base_tools)} base tools")
            return mcp_tools + base_tools
        else:
            return base_tools

    def _create_mcp_tools(self) -> list[BaseTool]:
        """Create LangChain tools for MCP tools using langchain-mcp-adapters.

        Returns:
            List of MCP tool wrappers or empty list
        """
        if not hasattr(self.tool_registry, 'mcp_manager') or not self.tool_registry.mcp_manager:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("No MCP manager available")
            return []

        mcp_tools = []
        try:
            # Use the existing approach but with better error handling
            mcp_manager = self.tool_registry.mcp_manager
            import logging
            logger = logging.getLogger(__name__)

            # Debug: Check MCP manager state
            if hasattr(mcp_manager, 'clients'):
                logger.debug(f"MCP clients: {list(mcp_manager.clients.keys())}")
            if hasattr(mcp_manager, 'server_tools'):
                logger.debug(f"MCP server_tools: {list(mcp_manager.server_tools.keys())}")

            all_tools = mcp_manager.get_all_tools()
            logger.debug(f"Found {len(all_tools)} MCP tools from manager")

            for mcp_tool in all_tools:
                tool_name = mcp_tool.get("name")
                tool_description = mcp_tool.get("description", "")
                mcp_server = mcp_tool.get("mcp_server")
                mcp_tool_name = mcp_tool.get("mcp_tool_name")

                if not mcp_server or not mcp_tool_name:
                    continue

                # Create individual tool wrappers for each MCP tool
                # This is what worked before and what the Deep Agent expects
                from .mcp.langchain_individual_tool import MCPLangChainIndividualTool

                mcp_tool_wrapper = MCPLangChainIndividualTool(
                    server_name=mcp_server,
                    mcp_tool_name=mcp_tool_name,
                    mcp_tool_info=mcp_tool,
                    mcp_manager=self.tool_registry.mcp_manager,
                    tool_registry=self.tool_registry,
                    description=tool_description,
                )

                mcp_tools.append(mcp_tool_wrapper)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create MCP tools: {e}", exc_info=True)
            # If MCP tools can't be loaded, just skip them
            pass

        return mcp_tools

    def _is_vlm_available(self) -> bool:
        """Check if VLM (Vision Language Model) is configured and available.

        Returns:
            True if VLM tool is configured with a model, False otherwise
        """
        if not hasattr(self.tool_registry, 'vlm_tool') or not self.tool_registry.vlm_tool:
            return False
        return self.tool_registry.vlm_tool.is_available()