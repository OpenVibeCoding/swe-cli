"""System prompt builders for SWE-CLI agents."""

from __future__ import annotations

from pathlib import Path
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

            env_context = self._build_environment_context(Path(self._working_dir))
            if env_context:
                prompt += env_context

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
            # 1. Remove analyze_image mandatory workflow and add anti-loop guidance
            vlm_section = """- **`analyze_image(prompt, image_path, image_url, max_tokens)`**: Analyze images using Vision Language Model
  - **🚨 ABSOLUTELY CRITICAL WORKFLOW**: After capturing ANY screenshots, MUST IMMEDIATELY follow up with analyze_image
  - **MANDATORY SEQUENCE**: 1) Capture screenshot → 2) Analyze image → 3) Proceed with other tools
  - **NEVER SKIP ANALYSIS**: Even if you think you know what's in the screenshot, you MUST analyze it"""

            vlm_replacement = """- **Note**: Vision analysis (analyze_image) is not currently available.
  - **WEB CLONING WITHOUT VISION**: Use `fetch_url` as your PRIMARY tool - it extracts text content and structure effectively
  - **Screenshots are useless without vision**: You CANNOT analyze screenshots without vision capabilities
  - **CRITICAL**: Do NOT capture multiple screenshots in a loop - you have no way to extract information from them
  - **Workflow**: For web cloning tasks, use `fetch_url` directly. Skip screenshot capture unless explicitly requested by user"""

            prompt = prompt.replace(vlm_section, vlm_replacement)

            # 2. Replace screenshot priority instructions for web cloning
            screenshot_priority = """  - **PRIORITY FOR WEB CLONING**: ALWAYS use this first before fetch_url for web cloning
  - Screenshots provide visual layout, styling, and component structure"""

            screenshot_replacement = """  - **NOTE**: Without vision capabilities, screenshots cannot provide layout or styling information
  - **FOR WEB CLONING**: Use `fetch_url` instead - screenshots are not useful without vision analysis"""

            prompt = prompt.replace(screenshot_priority, screenshot_replacement)

            # 3. Update fetch_url guidance to make it primary for web cloning
            fetch_url_old = """  - **FOR WEB CLONING**: Use AFTER capturing screenshots, only when needing specific text content"""
            fetch_url_new = """  - **FOR WEB CLONING (No Vision)**: Use as PRIMARY tool - captures text content, structure, and HTML effectively"""

            prompt = prompt.replace(fetch_url_old, fetch_url_new)

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

    def _build_environment_context(self, working_dir: Path) -> str:
        """Detect common Python environment managers to nudge correct install commands."""
        try:
            uv_lock = (working_dir / "uv.lock").exists()
            poetry_lock = (working_dir / "poetry.lock").exists()
            pipfile = (working_dir / "Pipfile").exists()
            conda_env = any((working_dir / name).exists() for name in ("environment.yml", "environment.yaml"))
            requirements = (working_dir / "requirements.txt").exists()
            pyproject = (working_dir / "pyproject.toml").exists()
        except Exception:
            return ""

        message = None
        if uv_lock or (pyproject and (working_dir / "uv.lock").exists()):
            message = "Python dependency manager detected: **uv** (`uv.lock`). Prefer `uv pip install <pkg>` and `uv run ...`."
        elif poetry_lock and pyproject:
            message = "Python dependency manager detected: **Poetry** (`poetry.lock`). Prefer `poetry install` and `poetry run ...`."
        elif pipfile:
            message = "Python dependency manager detected: **Pipenv** (`Pipfile`). Prefer `pipenv install` and `pipenv run ...`."
        elif conda_env:
            message = "Environment file detected: **Conda** (`environment.yml`). Prefer `conda env update -f environment.yml` and `conda run ...`."
        elif requirements:
            message = "Dependencies listed in `requirements.txt`. Use `pip install -r requirements.txt` (or project-standard installer)."

        if not message:
            return ""

        return f"\n\n# Environment Detection\n\n{message}\n"


class PlanningPromptBuilder:
    """Constructs the PLAN mode strategic planning prompt."""

    def build(self) -> str:
        """Return the static planning prompt."""
        return load_prompt("system_prompt_planning")
