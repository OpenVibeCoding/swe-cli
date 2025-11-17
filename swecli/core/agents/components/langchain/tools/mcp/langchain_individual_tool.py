"""Individual MCP tool wrapper that optionally uses langchain-mcp-adapters.

This module provides individual tool wrappers for each MCP function,
maintaining compatibility with the existing SWE-CLI infrastructure
while allowing optional use of langchain-mcp-adapters for communication.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any as AnyType

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from swecli.core.agents.components.langchain.tools.base import SWECLIToolWrapper


logger = logging.getLogger(__name__)


class MCPLangChainIndividualTool(SWECLIToolWrapper):
    """Individual SWE-CLI tool wrapper for a single MCP tool function.

    This wrapper creates individual tools for each MCP function (like GitHub search_repositories),
    which is what the Deep Agent expects. It preserves all SWE-CLI functionality and can
    optionally use langchain-mcp-adapters for the actual MCP communication.
    """

    def __init__(
        self,
        server_name: str,
        mcp_tool_name: str,
        mcp_tool_info: Dict[str, Any],
        mcp_manager: Any,
        tool_registry: Any,
        description: Optional[str] = None,
    ):
        """Initialize the individual MCP tool wrapper.

        Args:
            server_name: Name of the MCP server
            mcp_tool_name: Name of the specific MCP tool function
            mcp_tool_info: Complete tool information including schema
            mcp_manager: SWE-CLI MCP manager instance
            tool_registry: SWE-CLI tool registry for execution context
            description: Optional description override
        """
        # Initialize with the specific tool name and improved description
        tool_full_name = f"mcp__{server_name}__{mcp_tool_name}"

        # Create an enhanced description that makes it clear this is a GitHub API tool
        original_desc = description or mcp_tool_info.get("description", f"MCP tool: {mcp_tool_name}")
        enhanced_desc = self._create_enhanced_description(original_desc, mcp_tool_name, server_name)

        # Create args schema from the tool input schema (pass tool name directly)
        args_schema = self._create_args_schema(mcp_tool_info.get("input_schema", {}), tool_full_name)
        super().__init__(
            tool_name=tool_full_name,
            description=enhanced_desc,
            tool_registry=tool_registry,
            args_schema=args_schema,
        )

        # Set attributes using object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, 'server_name', server_name)
        object.__setattr__(self, 'mcp_tool_name', mcp_tool_name)
        object.__setattr__(self, 'mcp_tool_info', mcp_tool_info)
        object.__setattr__(self, 'mcp_manager', mcp_manager)

    def _create_enhanced_description(self, original_desc: str, tool_name: str, server_name: str) -> str:
        """Create an enhanced description that clearly indicates this is a server-specific API tool.

        Args:
            original_desc: Original tool description from MCP
            tool_name: Name of the tool
            server_name: Name of the server (e.g., 'github')

        Returns:
            Enhanced description for LLM clarity
        """
        server_display_name = server_name.title()

        # Create specific enhanced descriptions for common tools
        if server_name.lower() == 'github':
            if 'search_repositories' in tool_name.lower():
                return f"🔍 **GITHUB API**: Search GitHub repositories using the official GitHub API. Use this for finding repositories by language, stars, topics, etc. This is NOT for local file search - use the 'search' tool for local files."
            elif 'search_code' in tool_name.lower():
                return f"🔍 **GITHUB API**: Search for code across GitHub repositories using the official GitHub API. Use this for finding code within GitHub repositories. This is NOT for local file search - use the 'search' tool for local files."
            elif 'search_issues' in tool_name.lower():
                return f"🔍 **GITHUB API**: Search for issues and pull requests across GitHub repositories using the official GitHub API. Use this for finding GitHub issues and PRs. This is NOT for local file search - use the 'search' tool for local files."
            elif 'get_file' in tool_name.lower() or 'get_file_contents' in tool_name.lower():
                return f"📁 **GITHUB API**: Get file contents from GitHub repositories using the official GitHub API. Use this for reading files from GitHub repos. This is NOT for local files - use 'read_file' for local files."
            elif 'create' in tool_name.lower() and 'repositor' in tool_name.lower():
                return f"🆕 **GITHUB API**: Create new GitHub repositories using the official GitHub API. Use this for creating new GitHub repos."
            else:
                return f"⚡ **GITHUB API**: {original_desc} This tool uses the official GitHub API and is NOT for local operations."
        else:
            # Generic enhancement for other servers
            return f"⚡ **{server_display_name.upper()} API**: {original_desc} This tool uses the {server_display_name} API."

    def _create_args_schema(self, input_schema: Dict[str, Any], tool_name: str) -> Optional[Type[BaseModel]]:
        """Create Pydantic args schema from MCP input schema.

        Args:
            input_schema: MCP tool input schema
            tool_name: Name of the tool for model creation

        Returns:
            Pydantic BaseModel class or None
        """
        # Return None to avoid JSON Schema compatibility issues entirely
        # Both Deep Agent and SwecliAgent will work with kwargs-based approach
        # The LLM will still receive tool descriptions but without strict schema validation
        # This prevents the "could not understand the instance {}" error from Fireworks
        return None

    @staticmethod
    def _map_json_type_to_python(field_def: Dict[str, Any]) -> Type:
        """Map JSON schema type to Python type.

        Args:
            field_def: Field definition from JSON schema

        Returns:
            Python type
        """
        field_type = field_def.get("type", "string")
        field_format = field_def.get("format", "")

        if field_type == "string":
            return str
        elif field_type == "integer":
            return int
        elif field_type == "number":
            return float
        elif field_type == "boolean":
            return bool
        elif field_type == "array":
            return list
        elif field_type == "object":
            return dict
        else:
            return str

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Execute the specific MCP tool function.

        Args:
            *args: Positional arguments (can include JSON strings from LangChain)
            **kwargs: Tool arguments including SWE-CLI managers

        Returns:
            Tool execution result
        """
        # Handle JSON string passed as positional argument (common from LangChain)
        if args and not kwargs:
            # If we have exactly one positional argument that's a string, treat it as JSON
            if len(args) == 1 and isinstance(args[0], str):
                json_str = args[0]
                try:
                    import json
                    parsed_json = json.loads(json_str)
                    kwargs = parsed_json
                except json.JSONDecodeError:
                    # If it's not JSON, treat it as a simple query parameter
                    kwargs = {"query": json_str}
            else:
                # Multiple positional args, convert to kwargs if possible
                kwargs = {}
                for i, arg in enumerate(args):
                    if isinstance(arg, dict):
                        kwargs.update(arg)

        # Handle case where kwargs contains empty strings or empty JSON from LLM
        if kwargs:
            # Remove empty string values that LLM sometimes generates
            kwargs = {k: v for k, v in kwargs.items() if v != "" and v is not None}

            # Handle case where kwargs is a single empty JSON string
            if len(kwargs) == 1:
                single_key, single_value = next(iter(kwargs.items()))
                if isinstance(single_value, str) and single_value.strip() == "":
                    kwargs = {}

        # If we still have no valid parameters, provide reasonable defaults
        if not kwargs:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"No valid parameters extracted, providing default for {self._swetool_name}")
            if 'search_repositories' in self._swetool_name:
                kwargs = {"query": "language:java stars:>1000"}
            else:
                kwargs = {}

        # Extract SWE-CLI managers
        mode_manager = kwargs.pop("mode_manager", None)
        approval_manager = kwargs.pop("approval_manager", None)
        undo_manager = kwargs.pop("undo_manager", None)

        # Debug: Print what parameters we received
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Executing {self._swetool_name} with args: {args}, kwargs: {kwargs}")

        # Handle parameter mapping for GitHub tools
        if self.server_name.lower() == 'github':
            # GitHub search tools have specific parameter names
            if 'search_repositories' in self.mcp_tool_name.lower():
                logger.debug(f"Before parameter extraction: {kwargs}")

                # Check for parameters in kwargs wrapper (LangChain style)
                if 'kwargs' in kwargs and isinstance(kwargs['kwargs'], dict):
                    inner_params = kwargs.pop('kwargs')
                    logger.debug(f"Extracted inner params: {inner_params}")
                    kwargs.update(inner_params)

                # Handle JSON string input (common from LLM)
                if len(kwargs) == 1 and isinstance(list(kwargs.values())[0], str):
                    # Try to parse as JSON if it looks like JSON
                    json_str = list(kwargs.values())[0]
                    if json_str.strip().startswith('{') and json_str.strip().endswith('}'):
                        try:
                            import json
                            parsed_json = json.loads(json_str)
                            logger.debug(f"Parsed JSON from LLM: {parsed_json}")
                            kwargs.clear()
                            kwargs.update(parsed_json)
                        except json.JSONDecodeError:
                            logger.debug(f"Failed to parse JSON, keeping original: {json_str}")

                # Map common parameter names to GitHub's expected 'query' parameter
                if 'q' in kwargs and 'query' not in kwargs:
                    kwargs['query'] = kwargs.pop('q')
                    logger.debug(f"Mapped 'q' to 'query': {kwargs['query']}")
                elif 'search_query' in kwargs and 'query' not in kwargs:
                    kwargs['query'] = kwargs.pop('search_query')
                    logger.debug(f"Mapped 'search_query' to 'query': {kwargs['query']}")
                elif 'search' in kwargs and 'query' not in kwargs:
                    kwargs['query'] = kwargs.pop('search')
                    logger.debug(f"Mapped 'search' to 'query': {kwargs['query']}")

                # Debug: Print what parameters we're sending to MCP
                logger.debug(f"After mapping: {kwargs}")

                # Ensure query parameter exists for GitHub search
                if 'query' not in kwargs or kwargs['query'] in [None, '', 'undefined']:
                    # Default to a reasonable search if no valid query provided
                    default_query = "language:java stars:>1000"
                    kwargs['query'] = default_query
                    logger.debug(f"Using default query: {default_query}")

                # Remove any parameters that aren't in the MCP schema
                # Based on the schema, only 'query', 'page', and 'perPage' are allowed
                allowed_params = {'query', 'page', 'perPage'}
                final_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
                if final_kwargs != kwargs:
                    removed_params = set(kwargs.keys()) - set(final_kwargs.keys())
                    logger.debug(f"Removed unsupported parameters: {removed_params}")
                    kwargs = final_kwargs

                logger.debug(f"Final parameters for {self._swetool_name}: {kwargs}")

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

        try:
            # Use the existing MCP manager for tool execution
            # This maintains compatibility with the existing SWE-CLI infrastructure
            result = self.mcp_manager.call_tool_sync(
                self.server_name,
                self.mcp_tool_name,
                kwargs
            )

            # Record action for undo if undo manager is available
            if undo_manager and isinstance(result, dict):
                output = result.get("output", "")
                undo_manager.record_action(
                    self._swetool_name,
                    kwargs,
                    str(output)
                )

            # Format the result
            if result.get("success"):
                return str(result.get("output", "")) or "Tool executed successfully"
            else:
                error = result.get("error", "Unknown error")
                return f"Error: {error}"

        except Exception as e:
            logger.error(f"Failed to execute MCP tool {self._swetool_name}: {e}")
            return f"Error: Tool execution failed - {str(e)}"

    async def _arun(
        self,
        **kwargs: Any,
    ) -> str:
        """Async execution - runs sync tool in thread pool."""
        import asyncio
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"[ASYNC] Executing {self._swetool_name} asynchronously")

        try:
            # Run the synchronous _run method in a thread pool
            result = await asyncio.to_thread(
                self._run,
                **kwargs
            )
            logger.info(f"[ASYNC] {self._swetool_name} completed successfully")
            return result

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"[ASYNC] Tool execution error for {self._swetool_name}: {e}\n{error_trace}")
            return f"Error executing {self._swetool_name}: {str(e)}"

    def _extract_parameters_from_mcp_info(self) -> Dict[str, Any]:
        """Extract parameter information from MCP tool info.

        Returns:
            Parameter schema dictionary or empty dict
        """
        if not hasattr(self, 'mcp_tool_info') or not self.mcp_tool_info:
            return {}

        try:
            mcp_tool_info = self.mcp_tool_info
            input_schema = mcp_tool_info.get('input_schema', {})

            if input_schema and input_schema.get('type') == 'object':
                return self._convert_mcp_schema_to_json_schema(input_schema)

            return {}
        except Exception as e:
            logger.warning(f"Error extracting parameters from MCP info for {self._swetool_name}: {e}")
            return {}

    def _convert_mcp_schema_to_json_schema(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MCP input schema to JSON schema format.

        Args:
            input_schema: MCP tool input schema

        Returns:
            JSON schema dictionary
        """
        if not input_schema or input_schema.get('type') != 'object':
            return {}

        try:
            properties = input_schema.get('properties', {})
            required = input_schema.get('required', [])

            json_schema = {
                'type': 'object',
                'properties': {},
                'required': required
            }

            # Convert each property
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get('type', 'string')
                prop_description = prop_info.get('description', '')

                json_prop = {
                    'type': prop_type,
                    'description': prop_description
                }

                # Add default value if present
                if 'default' in prop_info:
                    json_prop['default'] = prop_info['default']

                json_schema['properties'][prop_name] = json_prop

            return json_schema

        except Exception as e:
            logger.warning(f"Error converting MCP schema to JSON schema for {self._swetool_name}: {e}")
            return {}

    def get_tool_schema(self) -> Dict[str, Any]:
        """Get tool schema for this individual MCP tool.

        Returns:
            Tool schema compatible with SWE-CLI
        """
        schema = {
            "type": "function",
            "function": {
                "name": self._swetool_name,
                "description": self.description or "",
            }
        }

        # Add parameters from MCP tool info even if args_schema is None
        # This ensures the LLM gets proper parameter information
        parameters = self._extract_parameters_from_mcp_info()
        if parameters:
            schema["function"]["parameters"] = parameters
        elif self.args_schema:
            try:
                schema["function"]["parameters"] = self.args_schema.model_json_schema()
            except Exception:
                schema["function"]["parameters"] = {"type": "object", "properties": {}}

        return schema