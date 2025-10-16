"""Init command for codebase analysis and memory creation."""

from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel

from rich.console import Console

from opencli.models.agent_deps import AgentDependencies


class InitCommandArgs(BaseModel):
    """Arguments for /init command."""

    path: Path = Path.cwd()
    skip_patterns: list[str] = [".git", "node_modules", "__pycache__", "venv", ".venv", "build", "dist"]


class InitCommandHandler:
    """Handles /init command execution.

    The handler orchestrates the codebase analysis by delegating to
    the Pydantic AI agent with a specialized system prompt.
    """

    def __init__(self, agent: Any, console: Console):
        """Initialize init command handler.

        Args:
            agent: OpenCLI Pydantic AI Agent
            console: Rich console for output
        """
        self.agent = agent
        self.console = console

    def parse_args(self, command: str) -> InitCommandArgs:
        """Parse /init command arguments.

        Args:
            command: The full command string (e.g., "/init" or "/init /path/to/project")

        Returns:
            Parsed arguments

        Examples:
            >>> parse_args("/init")
            InitCommandArgs(path=Path.cwd())

            >>> parse_args("/init ~/projects/myapp")
            InitCommandArgs(path=Path("~/projects/myapp").expanduser())
        """
        parts = command.strip().split()

        # Default: current directory
        if len(parts) == 1:
            return InitCommandArgs()

        # Custom path provided
        path_str = parts[1]
        path = Path(path_str).expanduser().absolute()

        return InitCommandArgs(path=path)

    def execute(self, args: InitCommandArgs, deps: AgentDependencies) -> dict[str, Any]:
        """Execute init command.

        This method creates a specialized task for the AI agent to analyze
        the codebase and generate OPENCLI.md. The agent follows the 4-phase
        strategic scanning approach defined in INIT_SCANNING_STRATEGY.md.

        Args:
            args: Parsed command arguments
            deps: Agent dependencies

        Returns:
            Result dictionary with success status and message
        """
        # Validate path
        if not args.path.exists():
            return {
                "success": False,
                "message": f"Path does not exist: {args.path}"
            }

        if not args.path.is_dir():
            return {
                "success": False,
                "message": f"Path is not a directory: {args.path}"
            }

        # Change working directory context
        original_cwd = Path.cwd()
        deps.working_dir = args.path

        try:
            # Create specialized prompt for codebase analysis
            task_prompt = self._create_analysis_prompt(args.path)

            # Show progress
            self.console.print(f"[cyan]Analyzing codebase at {args.path}...[/cyan]")

            # Run agent with analysis task
            result = self.agent.run_sync(
                message=task_prompt,
                deps=deps,
            )

            if result["success"]:
                opencli_path = args.path / "OPENCLI.md"

                # Check if agent wrote the file
                if not opencli_path.exists():
                    # Agent didn't write file - extract content and write it
                    content = result.get("content", "")
                    if content:
                        opencli_path.write_text(content)
                        self.console.print("[yellow]Note: Agent didn't write file, wrote manually[/yellow]")

                return {
                    "success": True,
                    "message": f"✓ Generated OPENCLI.md at {opencli_path}",
                    "content": result["content"]
                }
            else:
                return {
                    "success": False,
                    "message": f"✗ Failed to generate OPENCLI.md: {result.get('content', 'Unknown error')}"
                }

        finally:
            # Restore working directory
            deps.working_dir = original_cwd

    def _create_analysis_prompt(self, path: Path) -> str:
        """Create specialized prompt for codebase analysis.

        Args:
            path: Path to analyze

        Returns:
            Prompt string for the agent
        """
        return f"""Analyze codebase at {path} and create OPENCLI.md.

Tasks:
1. Count files: run_command("cd {path} && find . -type f | wc -l")
2. Find README: run_command("cd {path} && find . -maxdepth 1 -name README*")
3. Read README using read_file
4. Find configs: run_command("cd {path} && find . -maxdepth 2 -name package.json -o -name requirements.txt -o -name pyproject.toml")
5. Read config files using read_file
6. Get tree: run_command("cd {path} && tree -L 2 -I node_modules")
7. Create markdown with overview, structure, dependencies
8. Save using write_file("{path}/OPENCLI.md", content)

IMPORTANT: For run_command, use single quotes for shell patterns like -name '*.py' NOT double quotes."""

