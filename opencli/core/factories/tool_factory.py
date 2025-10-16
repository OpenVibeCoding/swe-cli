"""Factory for assembling the tool registry and related primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opencli.core.tools import ToolRegistry


@dataclass
class ToolDependencies:
    """Value object capturing tool-level dependencies."""

    file_ops: Any | None
    write_tool: Any | None
    edit_tool: Any | None
    bash_tool: Any | None
    web_fetch_tool: Any | None


class ToolFactory:
    """Creates tool registries with consistent wiring."""

    def __init__(self, dependencies: ToolDependencies) -> None:
        self._deps = dependencies

    def create_registry(self, *, mcp_manager: Any | None = None) -> ToolRegistry:
        """Instantiate a `ToolRegistry` with the configured dependencies."""
        registry = ToolRegistry(
            file_ops=self._deps.file_ops,
            write_tool=self._deps.write_tool,
            edit_tool=self._deps.edit_tool,
            bash_tool=self._deps.bash_tool,
            web_fetch_tool=self._deps.web_fetch_tool,
            mcp_manager=mcp_manager,
        )
        return registry
