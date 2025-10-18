"""Pydantic models for MCP configuration."""

from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    command: str = Field(..., description="Command to start the MCP server")
    args: list[str] = Field(default_factory=list, description="Arguments for the command")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    enabled: bool = Field(default=True, description="Whether the server is enabled")
    auto_start: bool = Field(default=True, description="Auto-start when SWE-CLI launches")
    transport: str = Field(default="stdio", description="Transport type (stdio, sse, http)")


class MCPConfig(BaseModel):
    """Root MCP configuration."""

    mcp_servers: Dict[str, MCPServerConfig] = Field(
        default_factory=dict, alias="mcpServers", description="MCP server configurations"
    )

    model_config = ConfigDict(
        populate_by_name=True  # Allow both snake_case and camelCase
    )
