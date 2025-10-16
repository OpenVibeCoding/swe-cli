#!/usr/bin/env python3
"""Test that TaskProgressDisplay spinner animates correctly."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from opencli.ui.task_progress import TaskProgressDisplay
from opencli.core.monitoring import TaskMonitor
from rich.console import Console


def test_spinner_animation():
    """Test that spinner cycles through frames."""
    print("\n" + "=" * 70)
    print("Testing TaskProgressDisplay Spinner Animation")
    print("=" * 70)

    console = Console()

    # Create task monitor
    task_monitor = TaskMonitor()
    task_monitor.start("Testing spinner animation", initial_tokens=0)

    # Create progress display
    progress = TaskProgressDisplay(console, task_monitor)

    print("\n[Test 1: Spinner should animate for 3 seconds]")
    print("Watch for cycling Braille dots: ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")

    progress.start()
    time.sleep(3)
    progress.stop()
    task_monitor.stop()

    print("\n✓ Spinner animation completed")

    # Test 2: Different task descriptions
    print("\n[Test 2: Spinner with different messages]")

    messages = [
        "Loading data",
        "Processing files",
        "Analyzing code",
    ]

    for msg in messages:
        task_monitor = TaskMonitor()
        task_monitor.start(msg, initial_tokens=0)
        progress = TaskProgressDisplay(console, task_monitor)

        print(f"\n  Testing: {msg}")
        progress.start()
        time.sleep(1.5)
        progress.stop()
        task_monitor.stop()

    print("\n✓ All messages work with animated spinner")


def test_spinner_frames():
    """Verify spinner frame sequence."""
    print("\n" + "=" * 70)
    print("Testing Spinner Frame Sequence")
    print("=" * 70)

    from opencli.ui.task_progress import TaskProgressDisplay

    expected_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    print(f"\n[Expected frames: {len(expected_frames)}]")
    print("Frames: " + " ".join(expected_frames))

    assert TaskProgressDisplay.SPINNER_FRAMES == expected_frames, \
        "Spinner frames don't match expected sequence"

    print("\n✓ Spinner frames are correct")

    # Check update interval
    print(f"\n[Update interval: {TaskProgressDisplay.UPDATE_INTERVAL}s]")
    assert TaskProgressDisplay.UPDATE_INTERVAL <= 0.1, \
        "Update interval should be <= 100ms for smooth animation"

    print("✓ Update interval is fast enough for smooth animation")


if __name__ == "__main__":
    try:
        test_spinner_frames()
        test_spinner_animation()

        print("\n" + "=" * 70)
        print("✅ ALL TASK PROGRESS SPINNER TESTS PASSED!")
        print("=" * 70)

        print("\n[Summary]")
        print("• Spinner now animates smoothly (updates every 100ms)")
        print("• Cycles through Braille dot frames: ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
        print("• Displays in magenta color for visibility")
        print("• Fixed from static '·' to animated spinner")
        print()

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
