"""Test UI improvements - spinner, flashing symbols, and status line."""

import time
from pathlib import Path
from rich.console import Console

from swecli.ui.animations import Spinner, FlashingSymbol, ProgressIndicator
from swecli.ui.status_line import StatusLine


def test_spinner():
    """Test spinner animation."""
    console = Console()
    console.print("\n[bold]Testing Spinner (LLM Thinking):[/bold]")

    spinner = Spinner(console)
    spinner.start("Thinking...")
    time.sleep(3)
    spinner.stop()

    console.print("✓ Spinner test complete\n")


def test_flashing_symbol():
    """Test flashing symbol animation."""
    console = Console()
    console.print("\n[bold]Testing Flashing Symbol (Tool Execution):[/bold]")

    flasher = FlashingSymbol(console)
    flasher.start("write_file(hello.txt, content='Hello World')")
    time.sleep(2)
    flasher.stop()

    # Show final solid symbol
    console.print("\n⏺ [cyan]write_file(hello.txt, content='Hello World')[/cyan]")
    console.print("  ⎿  [dim]File created successfully[/dim]")
    console.print("✓ Flashing symbol test complete\n")


def test_progress_indicator():
    """Test progress indicator for long operations."""
    console = Console()
    console.print("\n[bold]Testing Progress Indicator (Long Operation):[/bold]")

    progress = ProgressIndicator(console)
    progress.start("Running tests")
    time.sleep(4)
    progress.stop()

    console.print("  ⎿  [dim]All tests passed[/dim]")
    console.print("✓ Progress indicator test complete\n")


def test_status_line():
    """Test status line display."""
    console = Console()
    console.print("\n[bold]Testing Status Line:[/bold]\n")

    status = StatusLine(console)

    # Test 1: Normal display
    console.print("1. Normal status:")
    status.render(
        model="accounts/fireworks/models/glm-4p5",
        working_dir=Path.cwd(),
        tokens_used=2500,
        tokens_limit=100000,
    )

    time.sleep(1)

    # Test 2: High token usage (warning level)
    console.print("\n2. High token usage (80%+):")
    status.render(
        model="gpt-4",
        working_dir=Path.home() / "projects" / "my-app",
        tokens_used=85000,
        tokens_limit=100000,
        git_branch="feature/new-ui",
    )

    time.sleep(1)

    # Test 3: Very high token usage (danger level)
    console.print("\n3. Critical token usage (90%+):")
    status.render(
        model="claude-sonnet-4",
        working_dir=Path("/very/long/path/to/project/directory/that/needs/truncation"),
        tokens_used=95000,
        tokens_limit=100000,
        git_branch="main",
    )

    console.print("✓ Status line test complete\n")


def test_complete_flow():
    """Test complete flow with all UI elements."""
    console = Console()
    console.print("\n[bold cyan]═══ Testing Complete Flow ═══[/bold cyan]\n")

    console.print("[bold]User:[/bold] Create a hello.txt file\n")
    console.print("[bold blue]Assistant:[/bold blue]")

    # 1. Show spinner while "thinking"
    spinner = Spinner(console)
    spinner.start("Thinking...")
    time.sleep(2)
    spinner.stop()

    # 2. Show reasoning
    console.print("\nI'll create a hello.txt file with a greeting message.")

    # 3. Show tool call with flashing
    flasher = FlashingSymbol(console)
    flasher.start("write_file(file_path='hello.txt', content='Hello, World!')")
    time.sleep(1.5)
    flasher.stop()

    # 4. Show result
    console.print("\n⏺ [cyan]write_file(file_path='hello.txt', content='Hello, World!')[/cyan]")
    console.print("  ⎿  [dim]File created successfully (13 bytes)[/dim]")

    # 5. Show final message
    console.print("\nDone! The file has been created.")

    # 6. Show status line
    status = StatusLine(console)
    status.render(
        model="accounts/fireworks/models/glm-4p5",
        working_dir=Path.cwd(),
        tokens_used=1250,
        tokens_limit=100000,
        git_branch="main",
    )

    console.print("[bold green]✓ Complete flow test finished![/bold green]\n")


if __name__ == "__main__":
    console = Console()
    console.print("\n[bold magenta]═══════════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]  SWE-CLI UI Improvements - Test Suite[/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════════[/bold magenta]\n")

    # Run individual tests
    test_spinner()
    test_flashing_symbol()
    test_progress_indicator()
    test_status_line()

    # Run complete flow test
    test_complete_flow()

    console.print("[bold green]✅ All UI tests completed successfully![/bold green]\n")
