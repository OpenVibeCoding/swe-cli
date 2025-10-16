#!/usr/bin/env python3
"""Test REPL with DualConsole integration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from opencli.core.management import ConfigManager
from opencli.core.management import SessionManager
from opencli.repl.repl import REPL


def test_repl_with_dual_console():
    """Test that REPL works with DualConsole."""
    print("Testing REPL with DualConsole integration...")

    # Test 1: Create REPL instance
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Initialize session manager properly
    session_dir = Path(config.session_dir).expanduser()
    session_manager = SessionManager(session_dir)
    session_manager.create_session(working_directory=str(Path.cwd()))

    try:
        repl = REPL(config_manager, session_manager)
        print("✓ REPL initialized successfully with DualConsole")
    except Exception as e:
        print(f"✗ Failed to initialize REPL: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Check that console is DualConsole
    from opencli.ui.dual_console import DualConsole
    assert isinstance(repl.console, DualConsole), "Console should be DualConsole instance"
    print("✓ Console is DualConsole instance")

    # Test 3: Check that buffer exists
    assert hasattr(repl, '_conversation_buffer'), "REPL should have _conversation_buffer"
    print("✓ Conversation buffer exists")

    # Test 4: Check that buffer is accessible via console
    assert repl.console.buffer is repl._conversation_buffer, "Console buffer should match REPL buffer"
    print("✓ Buffer is properly connected to console")

    # Test 5: Test that console.print() works and captures to buffer
    initial_count = repl._conversation_buffer.count()
    repl.console.print("Test message")

    # Buffer should have increased
    new_count = repl._conversation_buffer.count()
    assert new_count == initial_count + 1, f"Buffer should have 1 more item (was {initial_count}, now {new_count})"
    print("✓ console.print() captures to buffer")

    # Test 6: Test that console properties work (width, height)
    assert hasattr(repl.console, 'width'), "Console should have width property"
    assert hasattr(repl.console, 'height'), "Console should have height property"
    assert repl.console.width > 0, "Width should be positive"
    print(f"✓ Console properties work (width: {repl.console.width})")

    # Test 7: Test that all components using console still work
    assert repl.output_formatter is not None, "Output formatter should be initialized"
    assert repl.output_formatter.console is repl.console, "Formatter should use REPL console"
    print("✓ All components properly initialized with DualConsole")

    # Test 8: Test buffer capture enable/disable
    repl.console.disable_buffer_capture()
    before_count = repl._conversation_buffer.count()
    repl.console.print("This should NOT be captured")
    after_count = repl._conversation_buffer.count()
    assert before_count == after_count, "Buffer should not change when capture disabled"

    repl.console.enable_buffer_capture()
    repl.console.print("This SHOULD be captured")
    assert repl._conversation_buffer.count() == after_count + 1, "Buffer should increase when capture re-enabled"
    print("✓ Buffer capture enable/disable works")

    print("\n✅ All tests passed! REPL works correctly with DualConsole.")
    print(f"   Buffer contains {repl._conversation_buffer.count()} items")
    return True


if __name__ == "__main__":
    try:
        success = test_repl_with_dual_console()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
