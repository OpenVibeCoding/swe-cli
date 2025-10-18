#!/usr/bin/env python3
"""Test the spinner animation live."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from swecli.ui.animations import Spinner
from rich.console import Console

console = Console()

print("=" * 60)
print("Testing Braille Dots Spinner - Live Animation")
print("=" * 60)
print()

# Show the frames and current speed
print(f"Frames: {' '.join(Spinner.FRAMES)}")
print(f"Current interval: {Spinner.INTERVAL}s ({int(Spinner.INTERVAL * 1000)}ms)")
print(f"Total frames: {len(Spinner.FRAMES)}")
print(f"Full cycle time: {Spinner.INTERVAL * len(Spinner.FRAMES):.2f}s")
print()

# Test the spinner
print("Starting spinner for 5 seconds...")
print("Watch for the Braille dots animation: ⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏")
print("-" * 60)

spinner = Spinner(console)
spinner.start("Testing new Braille dots spinner...")

time.sleep(5)

spinner.stop()

print()
print("-" * 60)
print("✓ Test complete!")
print()
print("Did you see the Braille dots animation?")
print("If the animation was too slow or fast, I can adjust the speed.")
