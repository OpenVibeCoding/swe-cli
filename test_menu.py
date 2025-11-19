#!/usr/bin/env python3
"""Quick test script for the interactive menu with improved styling."""

from swecli.setup.interactive_menu import InteractiveMenu
from swecli.setup.providers import get_provider_choices
from rich.console import Console

console = Console()

def test_menu():
    """Test the interactive provider selection menu with new styling."""
    console.print("\n[bold cyan]Testing Interactive Menu with Improved Styling[/bold cyan]")
    console.print("[dim]Features:[/dim]")
    console.print("  • Rich Table with ROUNDED box style")
    console.print("  • Background highlighting ([on #1f2d3a]) instead of REVERSE")
    console.print("  • Pointer character (❯) for selected items")
    console.print("  • Hex colors (#7a8691) for subtle elements")
    console.print("  • Consistent with Textual UI model picker\n")

    choices = get_provider_choices()
    console.print(f"[green]✓[/green] Loaded {len(choices)} providers")
    console.print(f"[green]✓[/green] Popular providers first: {choices[0][1]}, {choices[1][1]}, {choices[2][1]}")
    console.print()

    menu = InteractiveMenu(
        items=choices,
        title="Select AI Provider",
        window_size=9,
    )

    console.print("[yellow]Starting interactive menu...[/yellow]")
    console.print("[dim]Use ↑/↓ arrows to navigate, / to search, Enter to select, Esc to cancel[/dim]\n")

    selected = menu.show()

    if selected:
        provider_name = next(
            (name for pid, name, _ in choices if pid == selected), selected
        )
        console.print(f"\n[bold green]✓[/bold green] You selected: [bold]{provider_name}[/bold] ([cyan]{selected}[/cyan])")
    else:
        console.print("\n[yellow]✗ Selection cancelled[/yellow]")

if __name__ == "__main__":
    test_menu()
