#!/usr/bin/env python3
"""Test the task monitor with timer, token tracking, and ESC interrupt."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from opencli.core.monitoring import TaskMonitor
from opencli.ui.task_progress import TaskProgressDisplay
from rich.console import Console


def test_basic_task():
    """Test basic task with timer only."""
    console = Console()
    console.print("\n[bold cyan]Test 1: Basic Task (5 seconds)[/bold cyan]")
    console.print("[dim]Watch the timer count up...[/dim]\n")

    task_monitor = TaskMonitor()
    task_monitor.start("Processing request", initial_tokens=0)

    progress = TaskProgressDisplay(console, task_monitor)
    progress.start()

    # Simulate work for 5 seconds
    time.sleep(5)

    progress.stop()
    progress.print_final_status()


def test_task_with_tokens():
    """Test task with token tracking."""
    console = Console()
    console.print("\n[bold cyan]Test 2: Task with Token Tracking (8 seconds)[/bold cyan]")
    console.print("[dim]Watch tokens increase over time...[/dim]\n")

    task_monitor = TaskMonitor()
    task_monitor.start("Generating response", initial_tokens=1000)

    progress = TaskProgressDisplay(console, task_monitor)
    progress.start()

    # Simulate token increases
    for i in range(8):
        time.sleep(1)
        # Simulate tokens increasing
        current_tokens = 1000 + (i + 1) * 500
        task_monitor.update_tokens(current_tokens)

    progress.stop()
    progress.print_final_status()


def test_task_with_token_decrease():
    """Test task with token compression."""
    console = Console()
    console.print("\n[bold cyan]Test 3: Task with Token Compression (6 seconds)[/bold cyan]")
    console.print("[dim]Watch tokens decrease (compression)...[/dim]\n")

    task_monitor = TaskMonitor()
    task_monitor.start("Compacting conversation", initial_tokens=5000)

    progress = TaskProgressDisplay(console, task_monitor)
    progress.start()

    # Simulate token decreases
    for i in range(6):
        time.sleep(1)
        # Simulate tokens decreasing
        current_tokens = 5000 - (i + 1) * 400
        task_monitor.update_tokens(current_tokens)

    progress.stop()
    progress.print_final_status()


def test_interruptible_task():
    """Test task with ESC interruption."""
    console = Console()
    console.print("\n[bold cyan]Test 4: Interruptible Task (20 seconds or until ESC)[/bold cyan]")
    console.print("[bold yellow]Press ESC to interrupt![/bold yellow]")
    console.print("[dim]This will run for 20 seconds unless you press ESC...[/dim]\n")

    task_monitor = TaskMonitor()
    task_monitor.start("Long running operation", initial_tokens=2000)

    progress = TaskProgressDisplay(console, task_monitor)
    progress.start()

    # Simulate long work, checking for interruption
    for i in range(20):
        if task_monitor.should_interrupt():
            console.print("\n[bold red]Interrupted by user![/bold red]")
            break

        time.sleep(1)

        # Simulate token changes
        current_tokens = 2000 + (i + 1) * 200
        task_monitor.update_tokens(current_tokens)

    progress.stop()
    progress.print_final_status()


def test_multiple_tasks():
    """Test multiple tasks in sequence."""
    console = Console()
    console.print("\n[bold cyan]Test 5: Multiple Tasks in Sequence[/bold cyan]")
    console.print("[dim]Simulating a typical workflow...[/dim]\n")

    # Task 1: Thinking
    console.print("[bold]Step 1: Thinking...[/bold]")
    task_monitor = TaskMonitor()
    task_monitor.start("Thinking", initial_tokens=500)
    progress = TaskProgressDisplay(console, task_monitor)
    progress.start()

    for i in range(3):
        time.sleep(1)
        task_monitor.update_tokens(500 + (i + 1) * 150)

    progress.stop()
    progress.print_final_status()

    # Task 2: Writing file
    console.print("\n[bold]Step 2: Writing file...[/bold]")
    task_monitor = TaskMonitor()
    task_monitor.start("Writing hello.py", initial_tokens=0)
    progress = TaskProgressDisplay(console, task_monitor)
    progress.start()
    time.sleep(2)
    progress.stop()
    progress.print_final_status()

    # Task 3: Running tests
    console.print("\n[bold]Step 3: Running tests...[/bold]")
    task_monitor = TaskMonitor()
    task_monitor.start("Running pytest", initial_tokens=0)
    progress = TaskProgressDisplay(console, task_monitor)
    progress.start()
    time.sleep(4)
    progress.stop()
    progress.print_final_status()


def main():
    """Run all tests."""
    console = Console()

    console.print("\n╔════════════════════════════════════════════════════════════╗")
    console.print("║        [bold yellow]TASK MONITOR DEMO[/bold yellow]                                ║")
    console.print("║  Timer · Token Tracking · ESC Interrupt                  ║")
    console.print("╚════════════════════════════════════════════════════════════╝")

    try:
        # Test 1: Basic timer
        test_basic_task()

        # Test 2: Token increase
        test_task_with_tokens()

        # Test 3: Token decrease
        test_task_with_token_decrease()

        # Test 4: ESC interruption
        test_interruptible_task()

        # Test 5: Multiple tasks
        test_multiple_tasks()

        console.print("\n[bold green]═══════════════════════════════════════════════════════════[/bold green]")
        console.print("\n[bold]✨ Task Monitor Features:[/bold]")
        console.print("  [cyan]•[/cyan] Real-time timer showing elapsed seconds")
        console.print("  [cyan]•[/cyan] Token tracking with ↑ increase / ↓ decrease indicators")
        console.print("  [cyan]•[/cyan] ESC key to interrupt long-running operations")
        console.print("  [cyan]•[/cyan] Format: · Task… (esc to interrupt · XXs · ↓/↑ XXk tokens)")
        console.print("  [cyan]•[/cyan] Thread-safe implementation")
        console.print("\n[bold]🎯 Ready for REPL integration![/bold]\n")

    except KeyboardInterrupt:
        console.print("\n\n[bold red]Demo interrupted by Ctrl+C[/bold red]")


if __name__ == "__main__":
    main()
