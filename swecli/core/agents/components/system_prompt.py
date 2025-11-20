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
        prompt = load_prompt("system_prompt_normal")

        # Add conditional tool documentation based on availability
        prompt = self._add_conditional_tool_docs(prompt)

        # Add working directory context
        if self._working_dir:
            prompt += f"\n\n# Working Directory Context\n\nYou are currently working in the directory: `{self._working_dir}`\n\nWhen processing file paths without explicit directories (like `app.py` or `README.md`), assume they are located in the current working directory unless the user provides a specific path. Use relative paths from the working directory for file operations.\n"

        # Add MCP section if available
        mcp_prompt = self._build_mcp_section()
        if mcp_prompt:
            prompt += mcp_prompt

        return prompt

    def _is_vlm_available(self) -> bool:
        """Check if VLM functionality is configured.

        Returns:
            True if VLM tool is configured with a model, False otherwise
        """
        if not self._tool_registry or not hasattr(self._tool_registry, 'vlm_tool'):
            return False
        vlm_tool = self._tool_registry.vlm_tool
        if not vlm_tool:
            return False
        return vlm_tool.is_available()

    def _add_conditional_tool_docs(self, prompt: str) -> str:
        """Modify tool documentation based on availability.

        Args:
            prompt: Base system prompt loaded from file

        Returns:
            Modified prompt with conditional tool documentation
        """
        # Check if VLM is NOT available
        if not self._is_vlm_available():
            # Remove analyze_image mandatory workflow instructions
            # Replace with guidance to use fetch_url instead
            vlm_section = """- **`analyze_image(prompt, image_path, image_url, max_tokens)`**: Analyze images using Vision Language Model
  - **🚨 ABSOLUTELY CRITICAL WORKFLOW**: After capturing ANY screenshots, MUST IMMEDIATELY follow up with analyze_image
  - **MANDATORY SEQUENCE**: 1) Capture screenshot → 2) Analyze image → 3) Proceed with other tools
  - **NEVER SKIP ANALYSIS**: Even if you think you know what's in the screenshot, you MUST analyze it"""

            replacement = """- **Note**: Vision analysis (analyze_image) is not currently available. When cloning websites or analyzing content, use `fetch_url` to extract text content and structure instead of analyzing screenshots."""

            prompt = prompt.replace(vlm_section, replacement)

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
        return load_prompt("system_prompt_planning")
