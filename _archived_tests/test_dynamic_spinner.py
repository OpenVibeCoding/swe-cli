#!/usr/bin/env python3
"""Test the dynamic spinner with LLM descriptions."""

import sys
import time
from pathlib import Path

# Add opencli to path
sys.path.insert(0, str(Path(__file__).parent))

from swecli.ui.animations import Spinner
from rich.console import Console

def test_dynamic_spinner():
    """Test spinner with different natural language descriptions."""
    console = Console()
    spinner = Spinner(console)

    test_cases = [
        "Creating a simple ping pong game for you",
        "Now that I've created the ping pong game, let me run it for you",
        "Installing required dependencies for the project",
        "Analyzing your codebase structure and dependencies",
        "Refactoring the authentication module for better security",
    ]

    console.print("\n[bold]Testing Dynamic Spinner with Natural Descriptions[/bold]\n")
    console.print("Each spinner will show a natural language description instead of 'Thinking...'\n")

    for i, description in enumerate(test_cases, 1):
        console.print(f"\n[dim]Test {i}/{len(test_cases)}:[/dim]")

        # Start spinner with natural description
        spinner.start(description)

        # Simulate work
        time.sleep(2.5)

        # Stop spinner
        spinner.stop()

        # Print the full description with ⏺ symbol
        console.print(f"⏺ {description}")
        console.print()

    console.print("\n[green]✓[/green] All tests completed!")
    console.print("\nAs you can see:")
    console.print("  • Spinner shows natural task descriptions from LLM")
    console.print("  • ⏺ symbol marks completion")
    console.print("  • Full description appears after spinner stops")
    console.print("  • Smart mixture: 'Thinking...' during API call, natural descriptions during execution\n")

if __name__ == "__main__":
    test_dynamic_spinner()
