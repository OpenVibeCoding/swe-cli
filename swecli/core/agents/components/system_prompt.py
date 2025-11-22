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

        prompt = self._add_conditional_tool_docs(prompt)
        prompt = self._fill_dynamic_sections(prompt)

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
        # Fill conditional tool docs via placeholders
        replacements = self._build_tool_doc_replacements()
        for placeholder, content in replacements.items():
            prompt = prompt.replace(placeholder, content)
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

    def _build_tool_doc_replacements(self) -> dict[str, str]:
        """Build placeholder values for tool documentation sections."""
        if self._is_vlm_available():
            return {
                "[[WEB_CLONE_NOTE]]": "**FOR WEB CLONING**: Use AFTER capturing screenshots, only when needing specific text content",
                "[[SCREENSHOT_NOTE]]": "**PRIORITY FOR WEB CLONING**: ALWAYS use this first before fetch_url for web cloning\n  - Screenshots provide visual layout, styling, and component structure",
                "[[VISION_DOCS]]": "- **`analyze_image(prompt, image_path, image_url, max_tokens)`**: Analyze images using Vision Language Model\n  - **🚨 ABSOLUTELY CRITICAL WORKFLOW**: After capturing ANY screenshots, MUST IMMEDIATELY follow up with analyze_image\n  - **MANDATORY SEQUENCE**: 1) Capture screenshot → 2) Analyze image → 3) Proceed with other tools\n  - **NEVER SKIP ANALYSIS**: Even if you think you know what's in the screenshot, you MUST analyze it",
            }

        # When vision is not available, adjust guidance to avoid screenshot loops
        return {
            "[[WEB_CLONE_NOTE]]": "**FOR WEB CLONING (No Vision)**: Use as PRIMARY tool - captures text content, structure, and HTML effectively",
            "[[SCREENSHOT_NOTE]]": "**NOTE**: Without vision capabilities, screenshots cannot provide layout or styling information\n  - **FOR WEB CLONING**: Use `fetch_url` instead - screenshots are not useful without vision analysis",
            "[[VISION_DOCS]]": "- **Note**: Vision analysis (analyze_image) is not currently available.\n  - **WEB CLONING WITHOUT VISION**: Use `fetch_url` as your PRIMARY tool - it extracts text content and structure effectively\n  - **Screenshots are useless without vision**: You CANNOT analyze screenshots without vision capabilities\n  - **CRITICAL**: Do NOT capture multiple screenshots in a loop - you have no way to extract information from them\n  - **Workflow**: For web cloning tasks, use `fetch_url` directly. Skip screenshot capture unless explicitly requested by user",
        }

    def _fill_dynamic_sections(self, prompt: str) -> str:
        """Replace dynamic section placeholders in the prompt template."""
        placeholders = {
            "[[WORKING_DIR_CONTEXT]]": self._render_working_dir_context(),
            "[[ENVIRONMENT_CONTEXT_NOTE]]": self._build_environment_context(Path(self._working_dir)) if self._working_dir else "",
            "[[MCP_TOOLS_SECTION]]": self._build_mcp_section(),
        }

        for placeholder, content in placeholders.items():
            prompt = prompt.replace(placeholder, content or "")
        return prompt

    def _render_working_dir_context(self) -> str:
        """Render working directory context section."""
        if not self._working_dir:
            return ""

        return (
            "\n# Working Directory Context\n\n"
            f"You are currently working in the directory: `{self._working_dir}`\n\n"
            "When processing file paths without explicit directories (like `app.py` or `README.md`), assume they are located in the current working directory unless the user provides a specific path. Use relative paths from the working directory for file operations.\n"
        )

    def _build_environment_context(self, working_dir: Path) -> str:
        """Detect common ecosystem manifests to guide install/run commands."""
        detections: list[str] = []
        try:
            checks = [
                (("uv.lock",), "Python: **uv** detected (`uv.lock`). Prefer `uv pip install <pkg>` / `uv run ...`."),
                (("poetry.lock",), "Python: **Poetry** detected (`poetry.lock`). Prefer `poetry install` / `poetry run ...`."),
                (("Pipfile",), "Python: **Pipenv** detected (`Pipfile`). Prefer `pipenv install` / `pipenv run ...`."),
                (("environment.yml", "environment.yaml"), "Python: **Conda** env file detected. Prefer `conda env update -f environment.yml` / `conda run ...`."),
                (("requirements.txt",), "Python: `requirements.txt` present. Use project-standard installer (pip/uv) with that file."),
                (("package-lock.json",), "Node: npm lockfile detected. Prefer `npm install` / `npm run ...`."),
                (("pnpm-lock.yaml",), "Node: pnpm lockfile detected. Prefer `pnpm install` / `pnpm ...`."),
                (("yarn.lock",), "Node: yarn lockfile detected. Prefer `yarn install` / `yarn ...`."),
                (("bun.lockb",), "Node: bun lockfile detected. Prefer `bun install` / `bun run ...`."),
                (("go.mod",), "Go: module file detected. Prefer `go mod tidy` / `go run ./...` or `go test ./...`."),
                (("Cargo.toml",), "Rust: Cargo project detected. Prefer `cargo build` / `cargo test`."),
                (("Gemfile", "Gemfile.lock"), "Ruby: Bundler project detected. Prefer `bundle install` / `bundle exec ...`."),
                (("composer.json", "composer.lock"), "PHP: Composer project detected. Prefer `composer install` / `composer run`."),
                (("mix.exs",), "Elixir: Mix project detected. Prefer `mix deps.get` / `mix test`."),
                (("build.gradle", "build.gradle.kts", "gradlew"), "Java/Kotlin: Gradle project detected. Prefer `./gradlew ...` when available."),
                (("pom.xml",), "Java: Maven project detected. Prefer `mvn install` / `mvn test`."),
                (("Package.swift",), "Swift: Swift Package Manager detected. Prefer `swift build` / `swift test`."),
                (("global.json", "Directory.Packages.props", "NuGet.config", ".csproj", ".sln"), "C#/.NET: solution/project files detected. Prefer `dotnet restore` / `dotnet test` / `dotnet run`."),
                (("CMakeLists.txt",), "C/C++: CMake project detected. Prefer `cmake -S . -B build` / `cmake --build build` / `ctest --test-dir build`."),
                (("Makefile",), "C/C++/general: Makefile detected. Prefer `make` targets defined by the project."),
                (("SConstruct",), "C/C++/general: SCons build detected. Prefer `scons` targets."),
                (("build.sbt",), "Scala: sbt project detected. Prefer `sbt test` / `sbt run`."),
                (("stack.yaml",), "Haskell: Stack project detected. Prefer `stack build` / `stack test`."),
                (("cabal.project", "cabal.project.local"), "Haskell: Cabal project detected. Prefer `cabal build` / `cabal test`."),
                (("pubspec.yaml",), "Dart/Flutter: Pubspec detected. Prefer `dart pub get` / `dart test` or `flutter pub get` / `flutter test`."),
                (("rebar.config",), "Erlang: Rebar project detected. Prefer `rebar3 compile` / `rebar3 eunit`."),
                (("dune-project", "dune-workspace"), "OCaml: dune project detected. Prefer `dune build` / `dune test`."),
                (("Project.toml", "Manifest.toml"), "Julia: project detected. Prefer `julia --project -e 'using Pkg; Pkg.instantiate()'` and `Pkg.test()`."),
                (("*.rockspec",), "Lua: LuaRocks spec detected. Prefer `luarocks install --only-deps <spec>` / `luarocks make`."),
                (("*.nimble",), "Nim: nimble manifest detected. Prefer `nimble install -d` / `nimble test`."),
            ]

            for filenames, note in checks:
                if any((working_dir / name).exists() for name in filenames if "*" not in name):
                    detections.append(note)
                elif any(Path(p).match(name) for name in filenames if "*" in name for p in working_dir.glob(name)):
                    detections.append(note)

        except Exception:
            return ""

        if not detections:
            return ""

        max_items = 2
        lines = detections[:max_items]
        if len(detections) > max_items:
            lines.append(f"...and {len(detections) - max_items} more manifests detected; follow each ecosystem's standard install/run commands.")

        body = "\n".join(f"- {line}" for line in lines)
        return f"\n\n# Environment Detection (purpose: steer install/run to project-standard tooling)\n\n{body}\n"


class PlanningPromptBuilder:
    """Constructs the PLAN mode strategic planning prompt."""

    def build(self) -> str:
        """Return the static planning prompt."""
        return load_prompt("system_prompt_planning")
