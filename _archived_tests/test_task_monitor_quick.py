#!/usr/bin/env python3
"""Quick test of task monitor (no long waits)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from swecli.core.monitoring import TaskMonitor
from swecli.ui.task_progress import TaskProgressDisplay
from rich.console import Console


def main():
    """Run quick tests."""
    console = Console()

    console.print("\n╔════════════════════════════════════════════════════════════╗")
    console.print("║        [bold yellow]TASK MONITOR QUICK DEMO[/bold yellow]                         ║")
    console.print("║  Timer · Token Tracking · ESC Interrupt                  ║")
    console.print("╚════════════════════════════════════════════════════════════╝")

    # Test 1: Basic task
    console.print("\n[bold cyan]Test 1: Basic Task (3 seconds)[/bold cyan]\n")
    task_monitor = TaskMonitor()
    task_monitor.start("Processing request", initial_tokens=0)
    progress = TaskProgressDisplay(console, task_monitor)
    progress.start()
    time.sleep(3)
    progress.stop()
    progress.print_final_status()

    # Test 2: Token increase
    console.print("\n[bold cyan]Test 2: Token Increase (4 seconds)[/bold cyan]\n")
    task_monitor = TaskMonitor()
    task_monitor.start("Generating response", initial_tokens=1000)
    progress = TaskProgressDisplay(console, task_monitor)
    progress.start()

    for i in range(4):
        time.sleep(1)
        task_monitor.update_tokens(1000 + (i + 1) * 500)

    progress.stop()
    progress.print_final_status()

    # Test 3: Token decrease
    console.print("\n[bold cyan]Test 3: Token Compression (3 seconds)[/bold cyan]\n")
    task_monitor = TaskMonitor()
    task_monitor.start("Compacting conversation", initial_tokens=5000)
    progress = TaskProgressDisplay(console, task_monitor)
    progress.start()

    for i in range(3):
        time.sleep(1)
        task_monitor.update_tokens(5000 - (i + 1) * 600)

    progress.stop()
    progress.print_final_status()

    console.print("\n[bold green]═══════════════════════════════════════════════════════════[/bold green]")
    console.print("\n[bold]✨ Task Monitor Features:[/bold]")
    console.print("  [cyan]•[/cyan] Real-time timer showing elapsed seconds")
    console.print("  [cyan]•[/cyan] Token tracking with ↑/↓ indicators")
    console.print("  [cyan]•[/cyan] ESC key interrupt support (press ESC to interrupt tasks)")
    console.print("  [cyan]•[/cyan] Format: · Task… (esc to interrupt · XXs · ↓/↑ XXk tokens)")
    console.print("\n[bold]🎯 Ready for REPL integration![/bold]\n")


if __name__ == "__main__":
    main()
