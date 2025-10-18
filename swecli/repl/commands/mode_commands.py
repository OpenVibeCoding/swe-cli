"""Mode and operation commands for REPL."""

from typing import TYPE_CHECKING

from rich.console import Console

from swecli.core.management import OperationMode
from swecli.repl.commands.base import CommandHandler, CommandResult

if TYPE_CHECKING:
    from swecli.core.management import ModeManager, UndoManager
    from swecli.core.approval import ApprovalManager


class ModeCommands(CommandHandler):
    """Handler for mode-related commands: /mode, /undo, /history."""

    def __init__(
        self,
        console: Console,
        mode_manager: "ModeManager",
        undo_manager: "UndoManager",
        approval_manager: "ApprovalManager",
    ):
        """Initialize mode commands handler.

        Args:
            console: Rich console for output
            mode_manager: Mode manager instance
            undo_manager: Undo manager instance
            approval_manager: Approval manager instance
        """
        super().__init__(console)
        self.mode_manager = mode_manager
        self.undo_manager = undo_manager
        self.approval_manager = approval_manager

    def handle(self, args: str) -> CommandResult:
        """Handle mode command (not used, individual methods called directly)."""
        raise NotImplementedError("Use specific methods: switch_mode(), undo(), show_history()")

    def switch_mode(self, mode_name: str) -> CommandResult:
        """Switch operation mode.

        Args:
            mode_name: Mode to switch to (normal/plan) or empty to show current

        Returns:
            CommandResult indicating success or failure
        """
        if not mode_name:
            # Show current mode
            self.console.print(
                f"\n[bold]Current Mode:[/bold] {self.mode_manager.current_mode.value.upper()}"
            )
            self.console.print(self.mode_manager.get_mode_description())
            self.console.print("\n[dim]Available modes: normal, plan[/dim]")
            return CommandResult(success=True)

        mode_name = mode_name.strip().lower()

        try:
            if mode_name == "normal":
                new_mode = OperationMode.NORMAL
            elif mode_name == "plan":
                new_mode = OperationMode.PLAN
            else:
                self.print_error(f"Unknown mode: {mode_name}")
                self.console.print("[dim]Available modes: normal, plan[/dim]")
                return CommandResult(success=False, message=f"Unknown mode: {mode_name}")

            self.mode_manager.set_mode(new_mode)

            # Reset auto-approve when switching modes
            if hasattr(self.approval_manager, "reset_auto_approve"):
                self.approval_manager.reset_auto_approve()

            self.print_success(f"Switched to {new_mode.value.upper()} mode")
            self.console.print(self.mode_manager.get_mode_description())

            return CommandResult(
                success=True,
                message=f"Switched to {new_mode.value.upper()}",
                data=new_mode
            )

        except Exception as e:
            self.print_error(f"Error switching mode: {e}")
            return CommandResult(success=False, message=str(e))

    def undo(self) -> CommandResult:
        """Undo the last operation.

        Returns:
            CommandResult indicating success or failure
        """
        try:
            result = self.undo_manager.undo_last()

            if result:
                self.print_success("Operation undone successfully")
                self.console.print(
                    f"[dim]Undid: {result['operation'].type.value} on {result['operation'].target}[/dim]"
                )
                return CommandResult(success=True, data=result)
            else:
                self.print_warning("No operations to undo")
                return CommandResult(success=False, message="No operations to undo")

        except Exception as e:
            self.print_error(f"Error during undo: {e}")
            return CommandResult(success=False, message=str(e))

    def show_history(self) -> CommandResult:
        """Show operation history.

        Returns:
            CommandResult with history data
        """
        history = self.undo_manager.list_history()

        if not history:
            self.print_warning("No operations in history")
            return CommandResult(success=True, message="No history")

        self.console.print("\n[bold]Operation History:[/bold]\n")
        for i, entry in enumerate(reversed(history), 1):
            op = entry["operation"]
            timestamp = op.created_at.strftime("%H:%M:%S")
            status = "✓" if entry.get("result", {}).get("success") else "✗"
            self.console.print(
                f"  {status} [{timestamp}] {op.type.value}: {op.target}"
            )
        self.console.print()

        return CommandResult(success=True, data=history)
