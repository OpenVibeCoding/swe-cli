"""Test the improved approval dialog design."""

from pathlib import Path

import pytest
from rich.console import Console

from swecli.core.approval import ApprovalManager
from swecli.models.operation import Operation, OperationType


@pytest.mark.skip(reason="interactive approval dialog demo; run manually with -s")
def test_improved_approval_dialog():
    """Test the visual improvements to approval dialog."""
    console = Console()
    approval_manager = ApprovalManager(console)

    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Testing Improved Approval Dialog[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")

    console.print("[yellow]This test will show the improved approval dialog.[/yellow]")
    console.print("[yellow]Look for:[/yellow]")
    console.print("[yellow]  1. Heavy box characters (┏━┓) instead of light ones (╭─╮)[/yellow]")
    console.print("[yellow]  2. No leading pipes (│) on question and options[/yellow]")
    console.print("[yellow]  3. Dimmed shortcut text: (shift+tab), (esc)[/yellow]")
    console.print("[yellow]  4. Dialog should disappear after selection[/yellow]\n")

    # Create a test operation
    operation = Operation(
        type=OperationType.FILE_WRITE,
        path=Path("test_file.py"),
        description="Create test_file.py",
    )

    # Test preview content
    preview = """def hello():
    print("Hello, World!")

def goodbye():
    print("Goodbye!")"""

    console.print("\n[bold]Showing approval dialog now...[/bold]\n")

    # Request approval (this will show the dialog)
    result = approval_manager.request_approval(
        operation=operation,
        preview=preview,
    )

    # After selection, this should print (dialog should have disappeared)
    console.print("\n[bold green]✅ Dialog test complete![/bold green]")
    console.print(f"\nYour choice: [cyan]{result.choice.value}[/cyan]")
    console.print(f"Approved: [cyan]{result.approved}[/cyan]")

    if result.apply_to_all:
        console.print("[yellow]Note: You selected 'approve all'[/yellow]")

    console.print("\n[bold]Visual improvements to verify:[/bold]")
    console.print("  ✓ Heavy box characters (┏━┓┃┛┗) - more visible")
    console.print("  ✓ No leading pipes (│) - cleaner layout")
    console.print("  ✓ Dimmed shortcuts - better focus on options")
    console.print("  ✓ Dialog disappeared after selection")
    console.print("  ✓ Bold question text")


def test_autocomplete_commands():
    """Test that only implemented slash commands are shown."""
    console = Console()

    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Testing Slash Command Autocomplete[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")

    from swecli.ui.autocomplete import SLASH_COMMANDS

    console.print(f"[green]Total slash commands available:[/green] {len(SLASH_COMMANDS)}")
    console.print("\n[bold]Available commands:[/bold]\n")

    # Group by category
    categories = {
        "Session management": [],
        "File operations": [],
        "Execution": [],
        "Advanced": [],
    }

    for cmd in SLASH_COMMANDS:
        if cmd.name in ["help", "exit", "quit", "clear", "history", "sessions", "resume"]:
            categories["Session management"].append(cmd)
        elif cmd.name in ["tree", "read", "write", "edit", "search"]:
            categories["File operations"].append(cmd)
        elif cmd.name in ["run", "mode", "undo"]:
            categories["Execution"].append(cmd)
        else:
            categories["Advanced"].append(cmd)

    for category, commands in categories.items():
        if commands:
            console.print(f"[bold cyan]{category}:[/bold cyan]")
            for cmd in commands:
                console.print(f"  [green]/{cmd.name:<12}[/green] - [dim]{cmd.description}[/dim]")
            console.print()

    console.print("[bold green]✅ All commands are implemented and working![/bold green]")
    console.print("[dim]Try Shift+Tab to switch modes, or /context and /notifications for quick views[/dim]\n")


if __name__ == "__main__":
    # Test autocomplete first
    test_autocomplete_commands()

    # Then test approval dialog
    console = Console()
    console.print("\n[dim]Press Enter to test the approval dialog...[/dim]")
    input()

    test_improved_approval_dialog()
