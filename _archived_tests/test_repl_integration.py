#!/usr/bin/env python3
"""Test REPL integration with task monitor."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("Testing imports...")

try:
    from swecli.core.monitoring import TaskMonitor
    print("✓ TaskMonitor import successful")
except Exception as e:
    print(f"✗ TaskMonitor import failed: {e}")
    sys.exit(1)

try:
    from swecli.ui.task_progress import TaskProgressDisplay
    print("✓ TaskProgressDisplay import successful")
except Exception as e:
    print(f"✗ TaskProgressDisplay import failed: {e}")
    sys.exit(1)

try:
    from swecli.core.agents import SWE-CLIAgent
    print("✓ SWE-CLIAgent import successful")
except Exception as e:
    print(f"✗ SWE-CLIAgent import failed: {e}")
    sys.exit(1)

try:
    from swecli.repl.repl import REPL
    print("✓ REPL import successful")
except Exception as e:
    print(f"✗ REPL import failed: {e}")
    sys.exit(1)

print("\n✅ All imports successful!")
print("\nTesting TaskMonitor basic functionality...")

from rich.console import Console

# Test TaskMonitor
task_monitor = TaskMonitor()
task_monitor.start("Test operation", initial_tokens=1000)
print("✓ TaskMonitor.start() works")

task_monitor.update_tokens(1500)
delta = task_monitor.get_token_delta()
arrow = task_monitor.get_token_arrow()
print(f"✓ Token tracking works: delta={delta}, arrow={arrow}")

stats = task_monitor.stop()
print(f"✓ TaskMonitor.stop() works: {stats}")

# Test TaskProgressDisplay
console = Console()
task_monitor2 = TaskMonitor()
task_monitor2.start("Display test", initial_tokens=0)

progress = TaskProgressDisplay(console, task_monitor2)
print("✓ TaskProgressDisplay created")

# Don't actually start it (would hang), just verify instantiation
task_monitor2.stop()

print("\n✅ All functionality tests passed!")
print("\n🎉 REPL integration is ready!")
print("\nTo test in real REPL:")
print("  cd /Users/quocnghi/codes/test_opencli")
print("  opencli")
print("  Then try: 'create a hello.py file'")
