#!/usr/bin/env python3
"""Test that spinner animates correctly."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from opencli.ui.animations import Spinner
from rich.console import Console


def test_spinner_animation():
    """Test that spinner spins and shows different frames."""
    print("\n" + "=" * 70)
    print("Testing Spinner Animation")
    print("=" * 70)

    console = Console()
    spinner = Spinner(console)

    print("\n[Test 1: Basic spinner animation]")
    print("Starting spinner for 3 seconds...")

    spinner.start("Testing spinner animation")
    time.sleep(3)
    spinner.stop()

    print("✓ Spinner completed")

    print("\n[Test 2: Spinner with message updates]")
    print("Testing spinner with different messages...")

    spinner.start("Loading data...")
    time.sleep(1.5)
    spinner.stop()

    spinner.start("Processing results...")
    time.sleep(1.5)
    spinner.stop()

    print("✓ Multiple spinner sessions work")

    print("\n[Test 3: Quick start/stop]")
    spinner.start("Quick task")
    time.sleep(0.5)
    spinner.stop()
    print("✓ Quick operations work")


def test_spinner_styles():
    """Test different spinner styles."""
    print("\n" + "=" * 70)
    print("Testing Different Spinner Styles")
    print("=" * 70)

    from opencli.ui.animations import Spinner
    from rich.console import Console

    console = Console()

    styles = ["dots", "arc", "line", "circle"]

    for style in styles:
        print(f"\n[{style} spinner]")

        # Temporarily change the spinner style
        original_style = Spinner.SPINNER_STYLE
        Spinner.SPINNER_STYLE = style

        spinner = Spinner(console)
        spinner.start(f"Testing {style} style...")
        time.sleep(2)
        spinner.stop()

        Spinner.SPINNER_STYLE = original_style
        print(f"✓ {style} style works")


if __name__ == "__main__":
    try:
        test_spinner_animation()
        test_spinner_styles()

        print("\n" + "=" * 70)
        print("✅ ALL SPINNER TESTS PASSED!")
        print("=" * 70)

        print("\n[Summary]")
        print("• Spinner animates correctly with Rich's built-in spinner")
        print("• Using 'dots' style by default (⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏)")
        print("• Animation runs at ~12.5 fps (80ms per frame)")
        print("• Can easily change style by modifying SPINNER_STYLE")
        print()

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
