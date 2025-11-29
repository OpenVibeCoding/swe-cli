"""System prompt builders for SWE-CLI agents."""

from __future__ import annotations

from typing import Any, Sequence, Union

from swecli.prompts import load_prompt


class SystemPromptBuilder:
    """Constructs the NORMAL mode system prompt with optional MCP tooling."""

    def __init__(self, tool_registry: Union[Any, None], working_dir: Union[Any, None] = None) -> None:
        self._tool_registry = tool_registry
        self._working_dir = working_dir

    def build(self) -> str:
        """Return the formatted system prompt string."""
        # Load base prompt from file
        prompt = load_prompt("agent_normal")

        # Add working directory context
        if self._working_dir:
            prompt += f"\n\n# Working Directory Context\n\nYou are currently working in the directory: `{self._working_dir}`\n\nWhen processing file paths without explicit directories (like `app.py` or `README.md`), assume they are located in the current working directory unless the user provides a specific path. Use relative paths from the working directory for file operations.\n"

        # Add MCP section if available
        mcp_prompt = self._build_mcp_section()
        if mcp_prompt:
            prompt += mcp_prompt

        return prompt

    def _build_mcp_section(self) -> str:
        """Render the MCP tool section when servers are connected."""
        if not self._tool_registry or not getattr(self._tool_registry, "mcp_manager", None):
            return ""

        mcp_tools: Sequence[dict[str, Any]] = self._tool_registry.mcp_manager.get_all_tools()  # type: ignore[attr-defined]
        if not mcp_tools:
            return ""

        lines = ["\n## MCP Tools (Extended Capabilities)\n", "The following external tools are available through MCP servers:\n"]
        for tool in mcp_tools:
            tool_name = tool.get("name", "")
            description = tool.get("description", "")
            lines.append(f"- `{tool_name}` - {description}\n")

        lines.append("\nUse these MCP tools when they're relevant to the user's task.\n")
        return "".join(lines)


class PlanningPromptBuilder:
    """Constructs the PLAN mode strategic planning prompt."""

    def build(self) -> str:
        """Return the static planning prompt."""
        return load_prompt("agent_planning")
