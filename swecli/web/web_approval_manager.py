"""Web-based approval manager for WebSocket clients."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Optional, Union

from swecli.models.operation import Operation
from swecli.web.state import get_state


class ApprovalResult:
    """Result of an approval request (simplified for web)."""

    def __init__(
        self,
        approved: bool,
        choice: str = "approve",
        edited_content: Optional[str] = None,
        apply_to_all: bool = False,
        cancelled: bool = False,
    ) -> None:
        self.approved = approved
        self.choice = choice
        self.edited_content = edited_content
        self.apply_to_all = apply_to_all
        self.cancelled = cancelled


class WebApprovalManager:
    """Approval manager for web UI that uses WebSocket for approval requests."""

    def __init__(self, ws_manager: Any, loop: asyncio.AbstractEventLoop):
        """Initialize web approval manager.

        Args:
            ws_manager: WebSocket manager for broadcasting
            loop: Event loop for async operations
        """
        self.ws_manager = ws_manager
        self.loop = loop
        self.state = get_state()

    def request_approval(
        self,
        operation: Operation,
        preview: str,
        *,
        command: Optional[str] = None,
        working_dir: Optional[str] = None,
        allow_edit: bool = True,
        timeout: Union[Any, None] = None,
        force_prompt: bool = False,
    ) -> ApprovalResult:
        """Request approval for an operation via WebSocket.

        This is called from a sync context (agent thread), so we need to
        schedule the async broadcast and wait for response.

        Args:
            operation: Operation to approve
            preview: Preview of the operation (for display)
            command: Command being executed (for bash operations)
            working_dir: Working directory context
            allow_edit: Whether to allow editing (not supported in web)
            timeout: Custom timeout (uses default 5 minutes if None)
            force_prompt: Force prompt even if auto-approve is enabled

        Returns:
            ApprovalResult with approval status
        """
        approval_id = str(uuid.uuid4())

        # Create approval request with preview
        approval_request = {
            "id": approval_id,
            "tool_name": operation.tool_name,
            "arguments": operation.arguments,
            "description": operation.description or f"{operation.tool_name}({operation.arguments})",
            "preview": preview[:500] if preview else "",  # Truncate long previews
        }

        # Store pending approval in shared state
        self.state.add_pending_approval(
            approval_id,
            operation.tool_name,
            operation.arguments,
        )

        # Broadcast approval request via WebSocket
        future = asyncio.run_coroutine_threadsafe(
            self.ws_manager.broadcast({
                "type": "approval_required",
                "data": approval_request,
            }),
            self.loop
        )

        # Wait for broadcast to complete
        try:
            future.result(timeout=5)
        except Exception as e:
            print(f"Failed to broadcast approval request: {e}")
            self.state.clear_approval(approval_id)
            return ApprovalResult(approved=False, choice="deny", cancelled=True)

        # Wait for approval response (with timeout)
        wait_timeout = timeout if timeout else 300  # 5 minutes default
        start_time = time.time()

        while time.time() - start_time < wait_timeout:
            approval = self.state.get_pending_approval(approval_id)
            if approval and approval["resolved"]:
                # Clean up
                approved = approval["approved"]
                self.state.clear_approval(approval_id)
                choice = "approve" if approved else "deny"
                return ApprovalResult(approved=approved, choice=choice)

            # Sleep briefly to avoid busy waiting
            time.sleep(0.1)

        # Timeout - default to deny
        print(f"Approval request {approval_id} timed out")
        self.state.clear_approval(approval_id)
        return ApprovalResult(approved=False, choice="deny", cancelled=True)

    def reset_auto_approve(self) -> None:
        """Reset auto-approve state (for compatibility with ApprovalManager interface)."""
        # Web approval manager doesn't have auto-approve state
        pass

    def check_rules(self, operation: Operation) -> Optional[bool]:
        """Check auto-approval rules.

        For now, return None to always require explicit approval.
        In the future, this can check user-configured rules.

        Args:
            operation: Operation to check

        Returns:
            True to auto-approve, False to auto-deny, None to require user approval
        """
        # TODO: Implement rule checking based on user preferences
        # For now, always require approval
        return None
