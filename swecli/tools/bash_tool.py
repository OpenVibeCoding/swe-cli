"""Tool for executing bash commands safely."""

import re
import subprocess
import time
from pathlib import Path
from typing import Optional

from swecli.models.config import AppConfig
from swecli.models.operation import BashResult, Operation
from swecli.tools.base import BaseTool


# Safe commands that are generally allowed
SAFE_COMMANDS = [
    "ls", "cat", "head", "tail", "grep", "find", "wc",
    "echo", "pwd", "which", "whoami",
    "git", "pytest", "python", "python3", "pip",
    "node", "npm", "npx", "yarn",
    "docker", "kubectl",
    "make", "cmake",
]

# Dangerous patterns that should be blocked
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",  # Delete root
    r"sudo",  # Privileged execution
    r"chmod\s+-R\s+777",  # Permissive permissions
    r":\(\)\{\s*:\|\:&\s*\};:",  # Fork bomb
    r"mv\s+/",  # Move root directories
    r">\s*/dev/sd[a-z]",  # Write to disk directly
    r"dd\s+if=.*of=/dev",  # Disk operations
    r"curl.*\|\s*bash",  # Download and execute
    r"wget.*\|\s*bash",  # Download and execute
]


class BashTool(BaseTool):
    """Tool for executing bash commands with safety checks."""

    @property
    def name(self) -> str:
        """Tool name."""
        return "execute_command"

    @property
    def description(self) -> str:
        """Tool description."""
        return "Execute a bash command safely"

    def __init__(self, config: AppConfig, working_dir: Path):
        """Initialize bash tool.

        Args:
            config: Application configuration
            working_dir: Working directory for command execution
        """
        self.config = config
        self.working_dir = working_dir
        # Track background processes: {pid: {process, command, start_time, stdout_lines, stderr_lines}}
        self._background_processes = {}

    def execute(
        self,
        command: str,
        timeout: int = 30,
        capture_output: bool = True,
        working_dir: Optional[str] = None,
        env: Optional[dict] = None,
        background: bool = False,
        operation: Optional[Operation] = None,
    ) -> BashResult:
        """Execute a bash command.

        Args:
            command: Command to execute
            timeout: Timeout in seconds
            capture_output: Whether to capture stdout/stderr
            working_dir: Working directory (defaults to self.working_dir)
            env: Environment variables
            background: Run in background (not implemented yet)
            operation: Operation object for tracking

        Returns:
            BashResult with execution details

        Raises:
            PermissionError: If command execution is not permitted
            ValueError: If command is dangerous
        """
        # Check if bash execution is enabled
        if not self.config.permissions.bash.enabled:
            error = "Bash execution is disabled in configuration"
            if operation:
                operation.mark_failed(error)
            return BashResult(
                success=False,
                command=command,
                exit_code=-1,
                stdout="",
                stderr=error,
                duration=0.0,
                error=error,
                operation_id=operation.id if operation else None,
            )

        # Check if command is allowed
        if not self._is_command_allowed(command):
            error = f"Command not allowed: {command}"
            if operation:
                operation.mark_failed(error)
            return BashResult(
                success=False,
                command=command,
                exit_code=-1,
                stdout="",
                stderr=error,
                duration=0.0,
                error=error,
                operation_id=operation.id if operation else None,
            )

        # Check for dangerous patterns
        if self._is_dangerous(command):
            error = f"Dangerous command blocked: {command}"
            if operation:
                operation.mark_failed(error)
            return BashResult(
                success=False,
                command=command,
                exit_code=-1,
                stdout="",
                stderr=error,
                duration=0.0,
                error=error,
                operation_id=operation.id if operation else None,
            )

        # Resolve working directory
        work_dir = Path(working_dir) if working_dir else self.working_dir

        try:
            # Mark operation as executing
            if operation:
                operation.mark_executing()

            # Start timing
            start_time = time.time()

            # Handle background execution
            if background:
                import select

                # Use Popen for background execution
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE if capture_output else None,
                    stderr=subprocess.PIPE if capture_output else None,
                    text=True,
                    cwd=str(work_dir),
                    env=env,
                )

                # Capture initial startup output (wait up to 2 seconds)
                stdout_lines = []
                stderr_lines = []

                if capture_output:
                    import time as time_module
                    timeout = 2.0  # Wait 2 seconds for startup output
                    start_capture = time_module.time()

                    while time_module.time() - start_capture < timeout:
                        # Check if there's data ready to read (non-blocking)
                        ready, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)

                        for stream in ready:
                            line = stream.readline()
                            if line:
                                if stream == process.stdout:
                                    stdout_lines.append(line)
                                else:
                                    stderr_lines.append(line)

                        # Stop if process died
                        if process.poll() is not None:
                            break

                # Store process info with captured output
                self._background_processes[process.pid] = {
                    "process": process,
                    "command": command,
                    "start_time": start_time,
                    "stdout_lines": stdout_lines,
                    "stderr_lines": stderr_lines,
                }

                # Mark operation as success (background process started)
                if operation:
                    operation.mark_success()

                return BashResult(
                    success=True,
                    command=command,
                    exit_code=0,  # Process started
                    stdout=f"Background process started with PID {process.pid}",
                    stderr="",
                    duration=0.0,
                    operation_id=operation.id if operation else None,
                )

            # Regular synchronous execution
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=str(work_dir),
                env=env,
            )

            # Calculate duration
            duration = time.time() - start_time

            # Check exit code
            success = result.returncode == 0

            # Mark operation status
            if operation:
                if success:
                    operation.mark_success()
                else:
                    operation.mark_failed(f"Command failed with exit code {result.returncode}")

            return BashResult(
                success=success,
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout if capture_output else "",
                stderr=result.stderr if capture_output else "",
                duration=duration,
                operation_id=operation.id if operation else None,
            )

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            error = f"Command timed out after {timeout} seconds"

            # Extract partial output from the exception
            partial_stdout = e.stdout if e.stdout else ""
            partial_stderr = e.stderr if e.stderr else ""

            if operation:
                operation.mark_failed(error)
            return BashResult(
                success=False,
                command=command,
                exit_code=-1,
                stdout=partial_stdout,
                stderr=partial_stderr,
                duration=duration,
                error=error,
                operation_id=operation.id if operation else None,
            )

        except Exception as e:
            duration = time.time() - start_time
            error = f"Command execution failed: {str(e)}"
            if operation:
                operation.mark_failed(error)
            return BashResult(
                success=False,
                command=command,
                exit_code=-1,
                stdout="",
                stderr=error,
                duration=duration,
                error=error,
                operation_id=operation.id if operation else None,
            )

    def _is_command_allowed(self, command: str) -> bool:
        """Check if command is in the allowed list.

        Args:
            command: Command to check

        Returns:
            True if command is allowed
        """
        # Get the base command (first word)
        base_command = command.strip().split()[0] if command.strip() else ""

        # Check if it's in safe commands
        if base_command in SAFE_COMMANDS:
            return True

        # Check against permission patterns
        return self.config.permissions.bash.is_allowed(command)

    def _is_dangerous(self, command: str) -> bool:
        """Check if command matches dangerous patterns.

        Args:
            command: Command to check

        Returns:
            True if command is dangerous
        """
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True

        # Check config deny patterns
        for pattern in self.config.permissions.bash.compiled_patterns:
            if pattern.match(command):
                return True

        return False

    def preview_command(self, command: str, working_dir: Optional[str] = None) -> str:
        """Generate a preview of the command execution.

        Args:
            command: Command to preview
            working_dir: Working directory

        Returns:
            Formatted preview string
        """
        work_dir = working_dir or str(self.working_dir)

        preview = f"Command: {command}\n"
        preview += f"Working Directory: {work_dir}\n"
        preview += f"Timeout: {self.config.bash_timeout}s\n"

        # Safety checks
        if not self._is_command_allowed(command):
            preview += "\n⚠️  WARNING: Command not in allowed list\n"

        if self._is_dangerous(command):
            preview += "\n❌ DANGER: Command matches dangerous pattern\n"

        return preview

    def list_processes(self) -> list[dict]:
        """List all tracked background processes.

        Returns:
            List of process info dicts with pid, command, status, runtime
        """
        processes = []
        for pid, info in list(self._background_processes.items()):
            process = info["process"]
            status = "running" if process.poll() is None else "finished"
            runtime = time.time() - info["start_time"]

            processes.append({
                "pid": pid,
                "command": info["command"],
                "status": status,
                "runtime": runtime,
                "exit_code": process.returncode if status == "finished" else None,
            })

        return processes

    def get_process_output(self, pid: int) -> dict:
        """Get output from a background process.

        Args:
            pid: Process ID

        Returns:
            Dict with stdout, stderr, status, exit_code
        """
        if pid not in self._background_processes:
            return {
                "success": False,
                "error": f"Process {pid} not found",
            }

        info = self._background_processes[pid]
        process = info["process"]

        # Just return what's already captured - don't try to read more
        # (readline() blocks on pipes for long-running servers)
        # Output was already captured at process start

        # Check if process finished
        return_code = process.poll()
        status = "running" if return_code is None else "finished"

        return {
            "success": True,
            "pid": pid,
            "command": info["command"],
            "status": status,
            "exit_code": return_code,
            "stdout": "".join(info["stdout_lines"]),  # Return all captured output
            "stderr": "".join(info["stderr_lines"]),
            "total_stdout": "".join(info["stdout_lines"]),
            "total_stderr": "".join(info["stderr_lines"]),
            "runtime": time.time() - info["start_time"],
        }

    def kill_process(self, pid: int, signal: int = 15) -> dict:
        """Kill a background process.

        Args:
            pid: Process ID
            signal: Signal to send (default: 15/SIGTERM)

        Returns:
            Dict with success status
        """
        if pid not in self._background_processes:
            return {
                "success": False,
                "error": f"Process {pid} not found",
            }

        info = self._background_processes[pid]
        process = info["process"]

        try:
            if signal == 9:
                process.kill()  # SIGKILL
            else:
                process.terminate()  # SIGTERM

            # Wait for process to finish
            process.wait(timeout=5)

            # Clean up
            del self._background_processes[pid]

            return {
                "success": True,
                "pid": pid,
                "message": f"Process {pid} terminated",
            }

        except subprocess.TimeoutExpired:
            # Force kill if terminate didn't work
            process.kill()
            del self._background_processes[pid]

            return {
                "success": True,
                "pid": pid,
                "message": f"Process {pid} force killed",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to kill process {pid}: {str(e)}",
            }
