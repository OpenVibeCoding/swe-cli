"""DEPRECATED: Base classes for MCP LangChain tool wrappers.

This module has been replaced by langchain_adapters_tool.py which uses
the official langchain-mcp-adapters library. This file is kept for
reference only and should not be used in new code.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from swecli.core.agents.components.langchain.tools.base import SWECLIToolWrapper


def _convert_mcp_schema_to_pydantic(input_schema: Any) -> Type[BaseModel]:
    """Convert MCP input schema to Pydantic model.

    Args:
        input_schema: MCP tool input schema

    Returns:
        Pydantic BaseModel for the schema
    """
    import logging
    from pydantic import BaseModel, Field

    logger = logging.getLogger(__name__)

    # Simple fallback that always works - accept **kwargs
    # This is sufficient for the LLM to understand the tool accepts parameters
    class MCPToolInput(BaseModel):
        """Input model for MCP tool that accepts any keyword arguments."""
        kwargs: dict = Field(default_factory=dict, description="Tool arguments as key-value pairs")

    logger.debug(f"Created simple MCP tool input model")
    return MCPToolInput




class MCPLangChainTool(BaseTool):
    """LangChain tool wrapper for MCP tools."""

    def __init__(
        self,
        server_name: str,
        mcp_tool: Any,
        mcp_adapter: Any,
        description: Optional[str] = None,
    ):
        """Initialize the MCP LangChain tool.

        Args:
            server_name: Name of the MCP server
            mcp_tool: MCP tool definition
            mcp_adapter: MCP LangChain adapter instance
            description: Optional description override
        """
        # Set attributes using object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, 'server_name', server_name)
        object.__setattr__(self, 'mcp_tool', mcp_tool)
        object.__setattr__(self, 'mcp_adapter', mcp_adapter)

        # Determine tool name and description
        tool_name = mcp_tool.name if hasattr(mcp_tool, 'name') else 'unknown'
        tool_desc = description or (mcp_tool.description if hasattr(mcp_tool, 'description') else f"MCP tool: {tool_name}")

        super().__init__(
            name=f"mcp_{server_name}_{tool_name}",
            description=tool_desc,
            args_schema=_convert_mcp_schema_to_pydantic(mcp_tool.input_schema) if hasattr(mcp_tool, 'input_schema') else None,
        )

    def _convert_schema(self, input_schema: Any) -> Type[BaseModel]:
        """Convert MCP input schema to Pydantic model.

        Args:
            input_schema: MCP tool input schema

        Returns:
            Pydantic BaseModel for the schema
        """
        if not input_schema:
            return BaseModel

        try:
            # Create dynamic Pydantic model from JSON schema
            return self._create_pydantic_model(input_schema)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to convert MCP schema: {e}")
            logger.debug(f"Input schema: {input_schema}")
            # Fall back to simple model with **kwargs
            return type("MCPToolInput", (BaseModel,), {"kwargs": (dict, None)})

    def _create_pydantic_model(self, schema: Dict[str, Any]) -> Type[BaseModel]:
        """Create a Pydantic model from JSON schema.

        Args:
            schema: JSON schema dictionary

        Returns:
            Pydantic BaseModel class
        """
        # Simplified schema conversion - would need to be more robust
        fields = {}
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        for field_name, field_def in properties.items():
            field_type = str
            default = None

            # Handle different JSON schema types
            if field_def.get("type") == "string":
                field_type = str
            elif field_def.get("type") == "integer":
                field_type = int
            elif field_def.get("type") == "number":
                field_type = float
            elif field_def.get("type") == "boolean":
                field_type = bool
            elif field_def.get("type") == "array":
                field_type = list
            elif field_def.get("type") == "object":
                field_type = dict

            # Handle default values
            if "default" in field_def:
                default = field_def["default"]

            # Handle required fields
            if field_name in required:
                if default is not None:
                    fields[field_name] = (field_type, Field(default=default))
                else:
                    fields[field_name] = (field_type, Field(...))
            else:
                if default is not None:
                    fields[field_name] = (field_type, Field(default=default))
                else:
                    fields[field_name] = (field_type, Field(None))

        return type("MCPToolInput", (BaseModel,), fields)

    def _run(self, **kwargs: Any) -> str:
        """Execute the MCP tool.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool execution result
        """
        tool_name = self.mcp_tool.name if hasattr(self.mcp_tool, 'name') else self.name

        try:
            result = self.mcp_adapter.execute_tool(
                self.server_name,
                tool_name,
                kwargs
            )

            if result.get("success"):
                return result.get("output", "") or "Tool executed successfully"
            else:
                error = result.get("error", "Unknown error")
                return f"Error: {error}"

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to execute MCP tool {self.name}: {e}")
            return f"Error: Tool execution failed - {str(e)}"


class MCPSWECLIToolWrapper(SWECLIToolWrapper):
    """SWE-CLI tool wrapper for MCP tools that preserves all SWE-CLI functionality.

    This wrapper bridges MCP tools with the existing SWE-CLI tool infrastructure,
    ensuring compatibility with approval systems, mode restrictions, undo/redo capabilities,
    and permission management.
    """

    def __init__(
        self,
        server_name: str,
        mcp_tool: Any,
        mcp_adapter: Any,
        tool_registry: Any,
        description: Optional[str] = None,
    ):
        """Initialize the MCP SWE-CLI tool wrapper.

        Args:
            server_name: Name of the MCP server
            mcp_tool: MCP tool definition
            mcp_adapter: MCP LangChain adapter
            tool_registry: SWE-CLI tool registry for execution context
            description: Optional description override
        """
        # Initialize the base SWE-CLI wrapper with the correct tool name and schema
        tool_name = mcp_tool.name if hasattr(mcp_tool, 'name') else 'unknown'
        full_tool_name = f"mcp__{server_name}__{tool_name}"

        # Convert input schema to Pydantic model if available
        args_schema = None
        if hasattr(mcp_tool, 'input_schema') and mcp_tool.input_schema:
            try:
                args_schema = _convert_mcp_schema_to_pydantic(mcp_tool.input_schema)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to convert MCP schema for {tool_name}: {e}")

        super().__init__(
            tool_name=full_tool_name,
            description=description or (mcp_tool.description if hasattr(mcp_tool, 'description') else f"MCP tool: {tool_name}"),
            tool_registry=tool_registry,
            args_schema=args_schema,
        )

        # Set attributes using object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, 'server_name', server_name)
        object.__setattr__(self, 'mcp_tool', mcp_tool)
        object.__setattr__(self, 'mcp_adapter', mcp_adapter)

    def _run(
        self,
        **kwargs: Any,
    ) -> str:
        """Execute the MCP tool with full SWE-CLI context.

        Args:
            **kwargs: Tool arguments plus SWE-CLI managers

        Returns:
            Tool execution result
        """
        # Handle nested kwargs from our schema wrapper
        if "kwargs" in kwargs:
            # The LLM passes arguments as {"kwargs": {...}} - unwrap them
            actual_kwargs = kwargs.pop("kwargs", {})
            # Merge with any other kwargs that might be passed
            kwargs.update(actual_kwargs)

        # Map parameter names for GitHub tools
        tool_name = getattr(self.mcp_tool, 'name', '')

        # Debug logging to trace the issue
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"MCP tool {tool_name} received kwargs: {kwargs}")

        # Handle parameter name mismatches for GitHub search tools
        if 'search_repositories' in tool_name:
            # LLM might use 'q' but MCP expects 'query' for search_repositories
            if 'q' in kwargs and 'query' not in kwargs:
                kwargs['query'] = kwargs.pop('q')
                logger.debug(f"Mapped 'q' to 'query' for {tool_name}")
            # Also handle the case where 'query' might be missing
            elif 'query' not in kwargs and 'q' in kwargs:
                kwargs['query'] = kwargs.pop('q')
                logger.debug(f"Mapped 'q' to 'query' for {tool_name} (fallback)")
        elif 'search_code' in tool_name or 'search_users' in tool_name or 'search_issues' in tool_name:
            # LLM might use 'query' but MCP expects 'q' for these tools
            if 'query' in kwargs and 'q' not in kwargs:
                kwargs['q'] = kwargs.pop('query')
                logger.debug(f"Mapped 'query' to 'q' for {tool_name}")
            # Also handle case where 'q' might be missing
            elif 'q' not in kwargs and 'query' in kwargs:
                kwargs['q'] = kwargs.pop('query')
                logger.debug(f"Mapped 'query' to 'q' for {tool_name} (fallback)")

        logger.debug(f"MCP tool {tool_name} final kwargs: {kwargs}")

        # Extract SWE-CLI managers from kwargs
        mode_manager = kwargs.pop("mode_manager", None)
        approval_manager = kwargs.pop("approval_manager", None)
        undo_manager = kwargs.pop("undo_manager", None)

        # Check if the tool is allowed in current mode
        if mode_manager and not mode_manager.is_tool_allowed(self._swetool_name):
            return f"Error: Tool '{self._swetool_name}' is not allowed in {mode_manager.current_mode} mode"

        # Handle approval if required
        if approval_manager:
            approval_result = approval_manager.check_tool_approval(
                self._swetool_name,
                kwargs
            )
            if not approval_result.approved:
                return f"Tool execution denied: {approval_result.reason}"

        # Execute the tool
        try:
            tool_name = self.mcp_tool.name if hasattr(self.mcp_tool, 'name') else self._swetool_name
            result = self.mcp_adapter.execute_tool(
                self.server_name,
                tool_name,
                kwargs
            )

            if result.get("success"):
                output = result.get("output", "") or "Tool executed successfully"

                # Record action for undo if undo manager is available
                if undo_manager:
                    undo_manager.record_action(
                        self._swetool_name,
                        kwargs,
                        output
                    )

                return output
            else:
                error = result.get("error", "Unknown error")
                return f"Error: {error}"

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to execute MCP tool {self._swetool_name}: {e}")
            return f"Error: Tool execution failed - {str(e)}"