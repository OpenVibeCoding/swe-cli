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
        **kwargs: Any,
    ) -> str:
        """Async execution - not supported by SWE-CLI tools."""
        return f"Error: {self.tool_name} does not support async execution"

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

    def get_langchain_tools(self) -> list[BaseTool]:
        """Get LangChain-compatible tools from the SWE-CLI registry.

        Returns:
            List of LangChain BaseTool instances
        """
        if self._langchain_tools is None:
            self._langchain_tools = self._create_langchain_tools()

        return self._langchain_tools

    def _create_langchain_tools(self) -> list[BaseTool]:
        """Create LangChain tool instances from SWE-CLI registry.

        Returns:
            List of LangChain BaseTool instances
        """
        from .file_tools import (
            WriteFileTool, EditFileTool, ReadFileTool,
            ListFilesTool, SearchTool
        )
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
        from .todo_tools import (
            CreateTodoTool, UpdateTodoTool, CompleteTodoTool, ListTodosTool
        )

        tools = [
            # File operations
            WriteFileTool(self.tool_registry),
            EditFileTool(self.tool_registry),
            ReadFileTool(self.tool_registry),
            ListFilesTool(self.tool_registry),
            SearchTool(self.tool_registry),

            # Process operations
            RunCommandTool(self.tool_registry),
            ListProcessesTool(self.tool_registry),
            GetProcessOutputTool(self.tool_registry),
            KillProcessTool(self.tool_registry),

            # Web operations
            FetchUrlTool(self.tool_registry),
            OpenBrowserTool(self.tool_registry),

            # Screenshot operations
            CaptureScreenshotTool(self.tool_registry),
            ListScreenshotsTool(self.tool_registry),
            ClearScreenshotsTool(self.tool_registry),
            CaptureWebScreenshotTool(self.tool_registry),
            ListWebScreenshotsTool(self.tool_registry),
            ClearWebScreenshotsTool(self.tool_registry),

            # VLM operations
            AnalyzeImageTool(self.tool_registry),

            # Todo operations
            CreateTodoTool(self.tool_registry),
            UpdateTodoTool(self.tool_registry),
            CompleteTodoTool(self.tool_registry),
            ListTodosTool(self.tool_registry),
        ]

        # Add MCP tools if available
        mcp_tools = self._create_mcp_tools()
        if mcp_tools:
            tools.extend(mcp_tools)

        return tools

    def _create_mcp_tools(self) -> list[BaseTool]:
        """Create LangChain tools for MCP tools.

        Returns:
            List of MCP tool wrappers or empty list
        """
        if not hasattr(self.tool_registry, 'mcp_manager') or not self.tool_registry.mcp_manager:
            return []

        mcp_tools = []
        try:
            mcp_tool_list = self.tool_registry.mcp_manager.get_all_tools()
            for mcp_tool in mcp_tools:
                tool_name = mcp_tool.get("name")
                tool_description = mcp_tool.get("description", "")

                # Create a dynamic wrapper for each MCP tool
                mcp_wrapper = type(
                    f"MCP{tool_name.title()}Tool",
                    (SWECLIToolWrapper,),
                    {
                        "name": tool_name,
                        "description": tool_description,
                    }
                )

                mcp_tools.append(mcp_wrapper(
                    tool_name=tool_name,
                    description=tool_description,
                    tool_registry=self.tool_registry,
                ))
        except Exception:
            # If MCP tools can't be loaded, just skip them
            pass

        return mcp_tools