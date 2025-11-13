"""LangChain tool wrappers for SWE-CLI bash and process operations."""

from typing import Optional

from langchain_core.tools import BaseTool

from .base import SWECLIToolWrapper


class RunCommandTool(SWECLIToolWrapper):
    """LangChain wrapper for run_command tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="run_command",
            description=(
                "Execute a shell command safely. Use this for running build commands, "
                "tests, git operations, package management, and other development tasks. "
                "The command parameter specifies the shell command to execute. "
                "Note: This tool has safety restrictions and may require approval for certain commands."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, command: str, **kwargs) -> str:
        """Execute run_command tool."""
        return super()._run(command=command, **kwargs)


class ListProcessesTool(SWECLIToolWrapper):
    """LangChain wrapper for list_processes tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="list_processes",
            description=(
                "List currently running processes. Use this to check what processes "
                "are running, identify specific processes by name or PID, and understand "
                "the system's process state. Useful for finding servers, daemons, or "
                "background processes."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, **kwargs) -> str:
        """Execute list_processes tool."""
        return super()._run(**kwargs)


class GetProcessOutputTool(SWECLIToolWrapper):
    """LangChain wrapper for get_process_output tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="get_process_output",
            description=(
                "Get recent output from a running process. Use this to check the output "
                "of background processes, servers, or long-running commands. The pid "
                "parameter specifies the process ID, and lines parameter controls how "
                "many lines of output to retrieve."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, pid: int, lines: Optional[int] = 50, **kwargs) -> str:
        """Execute get_process_output tool."""
        return super()._run(pid=pid, lines=lines, **kwargs)


class KillProcessTool(SWECLIToolWrapper):
    """LangChain wrapper for kill_process tool."""

    def __init__(self, tool_registry):
        super().__init__(
            tool_name="kill_process",
            description=(
                "Terminate a running process. Use this to stop background servers, "
                "terminate hung processes, or clean up running tasks. The pid parameter "
                "specifies the process ID to terminate. Use with caution as this will "
                "immediately stop the specified process."
            ),
            tool_registry=tool_registry,
        )

    def _run(self, pid: int, **kwargs) -> str:
        """Execute kill_process tool."""
        return super()._run(pid=pid, **kwargs)