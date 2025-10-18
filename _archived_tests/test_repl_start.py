#!/usr/bin/env python3
"""Test that REPL can start without errors."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from swecli.repl.repl import REPL
    from swecli.models.config import AppConfig

    print("Testing REPL initialization...")

    # Create config
    config = AppConfig()

    # Try to create REPL instance
    repl = REPL(config)

    print("✓ REPL initialized successfully!")
    print(f"✓ Mode: {repl.mode_manager.current_mode.value}")
    print(f"✓ Bottom toolbar method exists: {hasattr(repl, '_bottom_toolbar_tokens')}")
    print(f"✓ Prompt session created: {repl.prompt_session is not None}")

    # Test the bottom toolbar
    if hasattr(repl, '_bottom_toolbar_tokens'):
        toolbar = repl._bottom_toolbar_tokens()
        print(f"✓ Bottom toolbar works: {len(toolbar)} elements")
        print(f"  Content preview: {toolbar[0][1] if toolbar else 'empty'}")

    print("\n✅ All tests passed! REPL is ready to run.")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
