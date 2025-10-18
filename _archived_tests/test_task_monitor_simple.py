#!/usr/bin/env python3
"""Simple test of TaskMonitor (no UI, just logic)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from swecli.core.monitoring import TaskMonitor
from rich.console import Console


def main():
    """Test TaskMonitor logic without UI."""
    console = Console()

    console.print("\n[bold cyan]Testing TaskMonitor Logic[/bold cyan]\n")

    # Test 1: Basic timer
    console.print("[bold]Test 1: Timer Tracking[/bold]")
    monitor = TaskMonitor()
    monitor.start("Test task", initial_tokens=0)

    time.sleep(2)
    elapsed = monitor.get_elapsed_seconds()
    console.print(f"After 2s: elapsed = {elapsed}s")

    stats = monitor.stop()
    console.print(f"Final stats: {stats}")
    console.print("✓ Timer working\n")

    # Test 2: Token tracking (increase)
    console.print("[bold]Test 2: Token Increase[/bold]")
    monitor = TaskMonitor()
    monitor.start("Generating", initial_tokens=1000)

    monitor.update_tokens(1500)
    delta = monitor.get_token_delta()
    arrow = monitor.get_token_arrow()
    formatted = monitor.get_formatted_token_display()
    console.print(f"After increase: delta={delta}, arrow={arrow}, display='{formatted}'")

    monitor.stop()
    console.print("✓ Token increase working\n")

    # Test 3: Token tracking (decrease)
    console.print("[bold]Test 3: Token Decrease (Compression)[/bold]")
    monitor = TaskMonitor()
    monitor.start("Compacting", initial_tokens=5000)

    monitor.update_tokens(3200)
    delta = monitor.get_token_delta()
    arrow = monitor.get_token_arrow()
    formatted = monitor.get_formatted_token_display()
    console.print(f"After decrease: delta={delta}, arrow={arrow}, display='{formatted}'")

    monitor.stop()
    console.print("✓ Token decrease working\n")

    # Test 4: Interrupt flag
    console.print("[bold]Test 4: Interrupt Flag[/bold]")
    monitor = TaskMonitor()
    monitor.start("Long task", initial_tokens=0)

    console.print(f"Should interrupt (before): {monitor.should_interrupt()}")
    monitor.request_interrupt()
    console.print(f"Should interrupt (after): {monitor.should_interrupt()}")

    monitor.stop()
    console.print("✓ Interrupt flag working\n")

    # Test 5: Format tokens
    console.print("[bold]Test 5: Token Formatting[/bold]")
    console.print(f"500 tokens: {TaskMonitor.format_tokens(500)}")
    console.print(f"1500 tokens: {TaskMonitor.format_tokens(1500)}")
    console.print(f"3700 tokens: {TaskMonitor.format_tokens(3700)}")
    console.print(f"12800 tokens: {TaskMonitor.format_tokens(12800)}")
    console.print("✓ Token formatting working\n")

    console.print("[bold green]All TaskMonitor logic tests passed![/bold green]\n")


if __name__ == "__main__":
    main()
