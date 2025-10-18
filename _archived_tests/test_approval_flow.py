#!/usr/bin/env python3
"""Test approval flow in NORMAL mode."""

import sys
from pathlib import Path
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent))

from swecli.core.management import ModeManager, OperationMode
from swecli.models.operation import Operation, OperationType


def main():
    """Test mode manager approval logic."""
    console = Console()

    console.print("[cyan]Testing Mode Manager Approval Logic[/cyan]\n")

    # Create mode manager
    mode_manager = ModeManager()

    # Test NORMAL mode
    mode_manager.set_mode(OperationMode.NORMAL)
    console.print(f"[yellow]Mode: {mode_manager.get_mode_indicator()}[/yellow]")
    console.print(f"Description: {mode_manager.get_mode_description()}\n")

    # Test various operations
    test_operations = [
        Operation(type=OperationType.FILE_WRITE, target="test.txt", parameters={}),
        Operation(type=OperationType.FILE_EDIT, target="test.txt", parameters={}),
        Operation(type=OperationType.BASH_EXECUTE, target="ls -la", parameters={}),
        Operation(type=OperationType.BASH_EXECUTE, target="python game.py", parameters={}),
        Operation(type=OperationType.BASH_EXECUTE, target="sudo rm -rf /", parameters={}),  # Dangerous
    ]

    for op in test_operations:
        needs_approval = mode_manager.needs_approval(op)
        status = "✓ Requires approval" if needs_approval else "✗ Auto-executes"
        color = "green" if needs_approval else "red"

        console.print(f"[{color}]{status}[/{color}] - {op.type.value}: {op.target}")

    console.print("\n[yellow]Expected: ALL operations should require approval in NORMAL mode[/yellow]")

    # Test PLAN mode
    console.print("\n[cyan]Testing PLAN mode:[/cyan]")
    mode_manager.set_mode(OperationMode.PLAN)
    console.print(f"Mode: {mode_manager.get_mode_indicator()}")
    console.print(f"Description: {mode_manager.get_mode_description()}\n")

    for op in test_operations[:3]:  # Test first 3
        needs_approval = mode_manager.needs_approval(op)
        console.print(f"{'✓' if needs_approval else '✗'} {op.type.value}: {needs_approval}")


if __name__ == "__main__":
    main()
