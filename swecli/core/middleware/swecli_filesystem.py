"""SWE-CLI FilesystemMiddleware for DeepAgent integration.

This module provides a custom FilesystemMiddleware that uses SWE-CLI's custom backend
while maintaining all existing functionality including UI callbacks, approval systems,
and undo management.
"""

import logging
from typing import Any, Dict, List

from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.backends.protocol import BACKEND_TYPES

from swecli.core.backends.swecli_backend import SWECliSandboxBackend

logger = logging.getLogger(__name__)


class SWECliFilesystemMiddleware(FilesystemMiddleware):
    """Custom FilesystemMiddleware that uses SWE-CLI's custom backend.

    This middleware extends the standard FilesystemMiddleware to use SWE-CLI's
    custom backend while preserving all SWE-CLI features like UI callbacks,
    approval systems, and undo management.
    """

    def __init__(
        self,
        tool_registry: Any,
        *,
        working_dir: str | None = None,
        system_prompt: str | None = None,
        custom_tool_descriptions: dict[str, str] | None = None,
        tool_token_limit_before_evict: int | None = 20000,
        ui_callback: Any = None,
        mode_manager: Any = None,
        approval_manager: Any = None,
        undo_manager: Any = None,
        task_monitor: Any = None,
        session_manager: Any = None,
    ) -> None:
        """Initialize the SWE-CLI FilesystemMiddleware.

        Args:
            tool_registry: SWE-CLI tool registry for backend operations
            working_dir: Working directory for file operations
            system_prompt: Optional custom system prompt override
            custom_tool_descriptions: Optional custom tool descriptions override
            tool_token_limit_before_evict: Optional token limit before evicting tool results
            ui_callback: UI callback for tool execution transparency
            mode_manager: Mode manager for operation mode tracking
            approval_manager: Approval manager for user confirmations
            undo_manager: Undo manager for operation history
            task_monitor: Task monitor for interrupt handling
            session_manager: Session manager for conversation tracking
        """
        # Create SWE-CLI custom backend
        self._swecli_backend = SWECliSandboxBackend(
            tool_registry=tool_registry,
            working_dir=working_dir,
            backend_id="swecli-main",
            mode_manager=mode_manager,
            approval_manager=approval_manager,
            undo_manager=undo_manager,
            task_monitor=task_monitor,
            session_manager=session_manager,
        )

        # Store tool registry for potential use in overridden methods
        self._tool_registry = tool_registry
        self._ui_callback = ui_callback

        logger.info(f"Created SWE-CLI backend with working directory: {working_dir or 'current'}")

        # Initialize parent FilesystemMiddleware with our custom backend
        super().__init__(
            backend=self._swecli_backend,
            system_prompt=system_prompt,
            custom_tool_descriptions=custom_tool_descriptions,
            tool_token_limit_before_evict=tool_token_limit_before_evict
        )

        logger.info("SWE-CLI FilesystemMiddleware initialized with custom backend")

    def wrap_tool_call(
        self,
        request,
        handler,
    ) -> Any:
        """Wrap tool calls to trigger UI callbacks for transparency.

        This method intercepts tool calls to trigger UI callbacks while letting
        the original handler execute the operation through our custom backend.

        Args:
            request: The tool call request being processed
            handler: The original handler function to execute the tool

        Returns:
            The tool execution result
        """
        # Extract tool information for UI callback
        tool_name = request.tool_call["name"]
        tool_args = request.tool_call["args"]

        # Trigger UI callback for tool transparency if available
        if self._ui_callback and hasattr(self._ui_callback, 'on_tool_call'):
            try:
                # Convert tool name to SWE-CLI display format
                display_name = self._map_tool_name_for_display(tool_name)

                # Call the UI callback with tool execution info
                self._ui_callback.on_tool_call(
                    tool_name=display_name,
                    arguments=tool_args,
                    tool_call_id=request.tool_call.get("id", "")
                )

                logger.debug(f"Triggered UI callback for SWE-CLI backend tool: {tool_name}")
            except Exception as e:
                # Don't let UI callback errors break tool execution
                logger.error(f"Failed to trigger UI callback for {tool_name}: {e}", exc_info=True)

        # Let the parent class handle the actual tool execution through our custom backend
        return super().wrap_tool_call(request, handler)

    async def awrap_tool_call(
        self,
        request,
        handler,
    ) -> Any:
        """Async version of wrap_tool_call for tool interception.

        Args:
            request: The tool call request being processed
            handler: The original async handler function to execute the tool

        Returns:
            The tool execution result
        """
        # Extract tool information for UI callback
        tool_name = request.tool_call["name"]
        tool_args = request.tool_call["args"]

        # Trigger UI callback for tool transparency if available
        if self._ui_callback and hasattr(self._ui_callback, 'on_tool_call'):
            try:
                # Convert tool name to SWE-CLI display format
                display_name = self._map_tool_name_for_display(tool_name)

                # Call the UI callback with tool execution info
                self._ui_callback.on_tool_call(
                    tool_name=display_name,
                    arguments=tool_args,
                    tool_call_id=request.tool_call.get("id", "")
                )

                logger.debug(f"Triggered UI callback for SWE-CLI backend tool: {tool_name} (async)")
            except Exception as e:
                # Don't let UI callback errors break tool execution
                logger.error(f"Failed to trigger UI callback for {tool_name}: {e}", exc_info=True)

        # Let the parent class handle the actual tool execution through our custom backend
        return await super().awrap_tool_call(request, handler)

    def _map_tool_name_for_display(self, tool_name: str) -> str:
        """Map Deep Agent tool names to SWE-CLI display format.

        This ensures consistent tool display formatting regardless of whether
        a tool comes from SWE-CLI or Deep Agent's FilesystemMiddleware.

        Args:
            tool_name: Deep Agent tool name (ls, grep, glob, etc.)

        Returns:
            SWE-CLI compatible tool name for display
        """
        # Map Deep Agent tool names to SWE-CLI equivalents for consistent display
        tool_mapping = {
            "ls": "list_files",
            "glob": "find_files",
            "grep": "search",
            "read_file": "read_file",
            "write_file": "write_file",
            "edit_file": "edit_file",
            "execute": "run_command",
        }

        return tool_mapping.get(tool_name, tool_name)

    def get_backend(self) -> Any:
        """Get the SWE-CLI custom backend instance.

        Returns:
            The SWECliSandboxBackend instance used by this middleware
        """
        return self._swecli_backend

    def set_ui_callback(self, ui_callback: Any) -> None:
        """Set the UI callback for tool execution transparency.

        This allows the UI callback to be configured after middleware creation,
        which is useful when the callback isn't available during initialization.

        Args:
            ui_callback: SWE-CLI UI callback instance
        """
        self._ui_callback = ui_callback
        logger.info("UI callback configured for SWE-CLI FilesystemMiddleware")

    def update_managers(
        self,
        mode_manager: Any = None,
        approval_manager: Any = None,
        undo_manager: Any = None,
        task_monitor: Any = None,
        session_manager: Any = None,
    ) -> None:
        """Update managers on the backend for tool execution context.

        This allows managers to be updated after middleware initialization,
        enabling full SWE-CLI integration (approval, undo, etc.) for Deep Agent tools.

        Args:
            mode_manager: Mode manager for operation mode tracking
            approval_manager: Approval manager for user confirmations
            undo_manager: Undo manager for operation history
            task_monitor: Task monitor for interrupt handling
            session_manager: Session manager for conversation tracking
        """
        if hasattr(self._swecli_backend, 'update_managers'):
            self._swecli_backend.update_managers(
                mode_manager=mode_manager,
                approval_manager=approval_manager,
                undo_manager=undo_manager,
                task_monitor=task_monitor,
                session_manager=session_manager
            )
            logger.debug("Updated managers on SWE-CLI backend for Deep Agent integration")


def create_swecli_filesystem_middleware(
    tool_registry: Any,
    working_dir: str | None = None,
    ui_callback: Any = None,
    mode_manager: Any = None,
    approval_manager: Any = None,
    undo_manager: Any = None,
    task_monitor: Any = None,
    session_manager: Any = None,
    **filesystem_kwargs
) -> SWECliFilesystemMiddleware:
    """Factory function to create SWE-CLI FilesystemMiddleware.

    This provides a convenient way to create the custom middleware with proper
    configuration and SWE-CLI tool registry integration.

    Args:
        tool_registry: SWE-CLI tool registry instance
        working_dir: Working directory for file operations
        ui_callback: UI callback for tool execution transparency
        mode_manager: Mode manager for operation mode tracking
        approval_manager: Approval manager for user confirmations
        undo_manager: Undo manager for operation history
        task_monitor: Task monitor for interrupt handling
        session_manager: Session manager for conversation tracking
        **filesystem_kwargs: Additional arguments for FilesystemMiddleware

    Returns:
        Configured SWECliFilesystemMiddleware instance
    """
    return SWECliFilesystemMiddleware(
        tool_registry=tool_registry,
        working_dir=working_dir,
        ui_callback=ui_callback,
        mode_manager=mode_manager,
        approval_manager=approval_manager,
        undo_manager=undo_manager,
        task_monitor=task_monitor,
        session_manager=session_manager,
        **filesystem_kwargs
    )