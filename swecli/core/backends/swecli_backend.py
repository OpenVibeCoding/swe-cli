"""SWE-CLI custom backend implementation for DeepAgent integration.

This module provides a custom backend that bridges SWE-CLI's tool registry with
DeepAgent's BackendProtocol, allowing SWE-CLI tools to work natively with DeepAgent
while preserving all existing functionality.
"""

import os
import re
from datetime import datetime
from typing import Any, Dict, List

from deepagents.backends.protocol import (
    BackendProtocol,
    SandboxBackendProtocol,
    FileInfo,
    GrepMatch,
    WriteResult,
    EditResult,
    ExecuteResponse,
)


class SWECliBackend(BackendProtocol):
    """Custom backend for SWE-CLI that integrates with SWE-CLI's tool registry.

    This backend provides DeepAgent-compatible file operations by delegating to
    SWE-CLI's existing tool handlers, ensuring all SWE-CLI functionality
    (approval systems, undo management, UI callbacks) is preserved.
    """

    def __init__(self, tool_registry: Any, working_dir: str = None):
        """Initialize the SWE-CLI backend.

        Args:
            tool_registry: SWE-CLI tool registry instance for tool execution
            working_dir: Working directory for file operations
        """
        self.tool_registry = tool_registry
        self.working_dir = working_dir or os.getcwd()

    def ls_info(self, path: str) -> List[FileInfo]:
        """Structured listing with file metadata using SWE-CLI's list_files tool.

        Args:
            path: Directory path to list

        Returns:
            List of FileInfo objects with file metadata
        """
        try:
            # Use SWE-CLI's list_files tool
            result = self.tool_registry.execute_tool(
                "list_files",
                {"path": path},
                mode_manager=self.mode_manager,
                approval_manager=self.approval_manager,
                undo_manager=self.undo_manager,
                task_monitor=self.task_monitor,
                session_manager=self.session_manager
            )

            if not result.get("success"):
                return []

            # Convert SWE-CLI result to FileInfo format
            file_infos = []
            for item in result.get("files", []):
                file_info = FileInfo(
                    path=item["path"],
                    is_dir=item.get("is_dir", False),
                    size=item.get("size", 0),
                    modified_at=item.get("modified", "")
                )
                file_infos.append(file_info)

            return file_infos

        except Exception as e:
            # Return empty list on error rather than raising
            return []

    def read(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> str:
        """Read file content with pagination using SWE-CLI's read_file tool.

        Args:
            file_path: Path to file to read
            offset: Line offset for pagination
            limit: Maximum number of lines to read

        Returns:
            File content as string, or error message
        """
        try:
            # Use SWE-CLI's read_file tool with pagination
            result = self.tool_registry.execute_tool(
                "read_file",
                {"file_path": file_path, "offset": offset, "limit": limit},
                mode_manager=self.mode_manager,
                approval_manager=self.approval_manager,
                undo_manager=self.undo_manager,
                task_monitor=self.task_monitor,
                session_manager=self.session_manager
            )

            if not result.get("success"):
                return result.get("error", f"Failed to read {file_path}")

            return result.get("content", "")

        except Exception as e:
            return f"Error reading {file_path}: {str(e)}"

    def grep_raw(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> List[GrepMatch] | str:
        """Structured search results using SWE-CLI's search tool.

        Args:
            pattern: Search pattern
            path: Directory path to search in
            glob: File pattern to match

        Returns:
            List of GrepMatch objects or error message
        """
        try:
            # Use SWE-CLI's search tool
            args = {"query": pattern}
            if path:
                args["path"] = path
            if glob:
                args["glob"] = glob

            result = self.tool_registry.execute_tool(
                "search",
                args,
                mode_manager=self.mode_manager,
                approval_manager=self.approval_manager,
                undo_manager=self.undo_manager,
                task_monitor=self.task_monitor,
                session_manager=self.session_manager
            )

            if not result.get("success"):
                return result.get("error", f"Search failed for pattern: {pattern}")

            # Convert SWE-CLI search results to GrepMatch format
            grep_matches = []
            for match in result.get("matches", []):
                grep_match = GrepMatch(
                    path=match.get("file", ""),
                    line=match.get("line", 0),
                    text=match.get("text", "")
                )
                grep_matches.append(grep_match)

            return grep_matches

        except Exception as e:
            return f"Search error: {str(e)}"

    def glob_info(self, pattern: str, path: str = "/") -> List[FileInfo]:
        """Structured glob matching using SWE-CLI's list_files tool.

        Args:
            pattern: Glob pattern to match
            path: Directory path to search in

        Returns:
            List of FileInfo objects matching the pattern
        """
        try:
            # Use SWE-CLI's list_files tool (supports pattern matching)
            args = {"pattern": pattern}
            if path != "/":
                args["path"] = path

            result = self.tool_registry.execute_tool(
                "list_files",
                args,
                mode_manager=self.mode_manager,
                approval_manager=self.approval_manager,
                undo_manager=self.undo_manager,
                task_monitor=self.task_monitor,
                session_manager=self.session_manager
            )

            if not result.get("success"):
                return []

            # Convert SWE-CLI result to FileInfo format
            file_infos = []
            for item in result.get("files", []):
                file_info = FileInfo(
                    path=item["path"],
                    is_dir=item.get("is_dir", False),
                    size=item.get("size", 0),
                    modified_at=item.get("modified", "")
                )
                file_infos.append(file_info)

            return file_infos

        except Exception as e:
            return []

    def write(
        self,
        file_path: str,
        content: str,
    ) -> WriteResult:
        """Create a new file using SWE-CLI's write_file tool.

        Args:
            file_path: Path to create
            content: File content to write

        Returns:
            WriteResult with operation status
        """
        try:
            result = self.tool_registry.execute_tool(
                "write_file",
                {"file_path": file_path, "content": content},
                mode_manager=self.mode_manager,
                approval_manager=self.approval_manager,
                undo_manager=self.undo_manager,
                task_monitor=self.task_monitor,
                session_manager=self.session_manager
            )

            if result.get("success"):
                return WriteResult(
                    error=None,
                    path=file_path,
                    files_update=None  # External storage, no state update needed
                )
            else:
                return WriteResult(
                    error=result.get("error", f"Failed to write {file_path}"),
                    path=None,
                    files_update=None
                )

        except Exception as e:
            return WriteResult(
                error=f"Write error: {str(e)}",
                path=None,
                files_update=None
            )

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Edit a file by replacing string occurrences using SWE-CLI's edit_file tool.

        Args:
            file_path: Path to file to edit
            old_string: String to replace
            new_string: Replacement string
            replace_all: Whether to replace all occurrences

        Returns:
            EditResult with operation status
        """
        try:
            result = self.tool_registry.execute_tool(
                "edit_file",
                {
                    "file_path": file_path,
                    "old_string": old_string,
                    "new_string": new_string,
                    "replace_all": replace_all
                },
                mode_manager=self.mode_manager,
                approval_manager=self.approval_manager,
                undo_manager=self.undo_manager,
                task_monitor=self.task_monitor,
                session_manager=self.session_manager
            )

            if result.get("success"):
                return EditResult(
                    error=None,
                    path=file_path,
                    files_update=None,  # External storage, no state update needed
                    occurrences=result.get("occurrences", 1)
                )
            else:
                return EditResult(
                    error=result.get("error", f"Failed to edit {file_path}"),
                    path=None,
                    files_update=None,
                    occurrences=None
                )

        except Exception as e:
            return EditResult(
                error=f"Edit error: {str(e)}",
                path=None,
                files_update=None,
                occurrences=None
            )


class SWECliSandboxBackend(SWECliBackend, SandboxBackendProtocol):
    """Extended SWE-CLI backend with command execution support.

    This extends SWECliBackend to implement SandboxBackendProtocol, enabling
    shell command execution through SWE-CLI's existing command tools.
    """

    def __init__(
        self,
        tool_registry: Any,
        working_dir: str = None,
        backend_id: str = "swecli",
        mode_manager: Any = None,
        approval_manager: Any = None,
        undo_manager: Any = None,
        task_monitor: Any = None,
        session_manager: Any = None,
    ):
        """Initialize the SWE-CLI sandbox backend.

        Args:
            tool_registry: SWE-CLI tool registry instance
            working_dir: Working directory for operations
            backend_id: Unique identifier for this backend instance
            mode_manager: Mode manager for operation mode tracking
            approval_manager: Approval manager for user confirmations
            undo_manager: Undo manager for operation history
            task_monitor: Task monitor for interrupt handling
            session_manager: Session manager for conversation tracking
        """
        super().__init__(tool_registry, working_dir)
        self._backend_id = backend_id

        # Store managers for passing to tool execution
        self.mode_manager = mode_manager
        self.approval_manager = approval_manager
        self.undo_manager = undo_manager
        self.task_monitor = task_monitor
        self.session_manager = session_manager

    @property
    def id(self) -> str:
        """Unique identifier for this sandbox backend."""
        return self._backend_id

    def update_managers(
        self,
        mode_manager: Any = None,
        approval_manager: Any = None,
        undo_manager: Any = None,
        task_monitor: Any = None,
        session_manager: Any = None,
    ) -> None:
        """Update managers for tool execution context.

        This allows managers to be updated after backend initialization,
        which is useful when managers aren't available during startup.

        Args:
            mode_manager: Mode manager for operation mode tracking
            approval_manager: Approval manager for user confirmations
            undo_manager: Undo manager for operation history
            task_monitor: Task monitor for interrupt handling
            session_manager: Session manager for conversation tracking
        """
        if mode_manager is not None:
            self.mode_manager = mode_manager
        if approval_manager is not None:
            self.approval_manager = approval_manager
        if undo_manager is not None:
            self.undo_manager = undo_manager
        if task_monitor is not None:
            self.task_monitor = task_monitor
        if session_manager is not None:
            self.session_manager = session_manager

    def execute(self, command: str) -> ExecuteResponse:
        """Execute a command using SWE-CLI's run_command tool.

        Args:
            command: Full shell command string to execute

        Returns:
            ExecuteResponse with command output and status
        """
        try:
            result = self.tool_registry.execute_tool(
                "run_command",
                {"command": command},
                mode_manager=self.mode_manager,
                approval_manager=self.approval_manager,
                undo_manager=self.undo_manager,
                task_monitor=self.task_monitor,
                session_manager=self.session_manager
            )

            if result.get("success"):
                return ExecuteResponse(
                    output=result.get("output", ""),
                    exit_code=result.get("exit_code", 0),
                    truncated=result.get("truncated", False)
                )
            else:
                return ExecuteResponse(
                    output=result.get("error", f"Command failed: {command}"),
                    exit_code=1,
                    truncated=False
                )

        except Exception as e:
            return ExecuteResponse(
                output=f"Execution error: {str(e)}",
                exit_code=1,
                truncated=False
            )