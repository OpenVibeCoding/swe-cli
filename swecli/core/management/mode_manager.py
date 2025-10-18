"""Mode management for controlling operation behavior."""

from enum import Enum
from typing import Optional

from swecli.models.operation import OperationType


class OperationMode(str, Enum):
    """Operation modes."""

    NORMAL = "normal"  # Interactive execution with approval for each operation
    PLAN = "plan"  # Planning only, no execution


class ModeManager:
    """Manager for operation modes."""

    def __init__(self, default_mode: OperationMode = OperationMode.NORMAL):
        """Initialize mode manager.

        Args:
            default_mode: Initial mode
        """
        self._current_mode = default_mode
        self._operation_count = 0  # Track operations in normal mode

    @property
    def current_mode(self) -> OperationMode:
        """Get current operation mode."""
        return self._current_mode

    def set_mode(self, mode: OperationMode) -> None:
        """Set operation mode.

        Args:
            mode: Mode to set
        """
        self._current_mode = mode
        # Reset operation counter when switching to normal
        if mode == OperationMode.NORMAL:
            self._operation_count = 0

    def is_approval_required(
        self,
        operation: OperationType,
        is_dangerous: bool = False,
    ) -> bool:
        """Check if approval is required for an operation.

        Args:
            operation: Type of operation
            is_dangerous: Whether operation is considered dangerous

        Returns:
            True if approval is required
        """
        # Plan mode never executes, always requires "approval" to plan
        if self._current_mode == OperationMode.PLAN:
            return True

        # Normal mode: all operations require approval (interactive workflow)
        if self._current_mode == OperationMode.NORMAL:
            return True

        return True  # Default to requiring approval

    def needs_approval(self, operation) -> bool:
        """Check if an operation needs approval.

        Args:
            operation: Operation object

        Returns:
            True if approval is required
        """
        # Import here to avoid circular dependency
        from swecli.models.operation import Operation
        import re

        if isinstance(operation, Operation):
            # Smart danger detection for bash commands
            is_dangerous = False

            if operation.type == OperationType.BASH_EXECUTE:
                # Only dangerous if matches dangerous patterns
                # Command is stored in 'target' field for bash operations
                command = operation.target or operation.parameters.get("command", "") or ""

                # Dangerous patterns (from bash_tool.py)
                dangerous_patterns = [
                    r"rm\s+-rf\s+/",  # Delete root
                    r"sudo",  # Privileged execution
                    r"chmod\s+-R\s+777",  # Permissive permissions
                    r":\(\)\{\s*:\|\:&\s*\};:",  # Fork bomb
                    r"mv\s+/",  # Move root directories
                    r">\s*/dev/sd[a-z]",  # Write to disk directly
                    r"dd\s+if=.*of=/dev",  # Disk operations
                    r"curl.*\|\s*bash",  # Download and execute
                    r"wget.*\|\s*bash",  # Download and execute
                    r"mkfs",  # Format filesystem
                    r"fdisk",  # Disk partitioning
                ]

                for pattern in dangerous_patterns:
                    if re.search(pattern, command, re.IGNORECASE):
                        is_dangerous = True
                        break

            return self.is_approval_required(operation.type, is_dangerous)
        else:
            # Fallback for OperationType
            return self.is_approval_required(operation)

    def record_operation(self) -> None:
        """Record that an operation was performed (for normal mode tracking)."""
        if self._current_mode == OperationMode.NORMAL:
            self._operation_count += 1

    def get_operation_count(self) -> int:
        """Get count of operations performed in normal mode."""
        return self._operation_count

    def get_mode_indicator(self) -> str:
        """Get a visual indicator for the current mode.

        Returns:
            String indicator for display
        """
        indicators = {
            OperationMode.NORMAL: "[NORMAL]",
            OperationMode.PLAN: "[PLAN]",
        }
        return indicators.get(self._current_mode, "[UNKNOWN]")

    def get_mode_description(self) -> str:
        """Get description of current mode.

        Returns:
            Mode description
        """
        descriptions = {
            OperationMode.NORMAL: "Interactive execution with approval for each operation",
            OperationMode.PLAN: "Planning only, no execution",
        }
        return descriptions.get(self._current_mode, "Unknown mode")
