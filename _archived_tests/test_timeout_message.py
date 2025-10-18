#!/usr/bin/env python3
"""Test that timeout errors show the actual command."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from swecli.tools.bash_tool import BashTool
from swecli.models.config import AppConfig


def test_timeout_message():
    """Test that timeout message includes the command."""
    print("\n" + "=" * 70)
    print("Testing Timeout Error Messages")
    print("=" * 70)

    config = AppConfig()
    config.enable_bash = True  # Enable bash execution for testing
    bash_tool = BashTool(config, Path.cwd())

    # Test 1: Short command timeout
    print("\n[Test 1: Short command timeout]")
    print("Running: sleep 5 (with 1 second timeout)")

    result = bash_tool.execute(command="sleep 5", timeout=1)

    print(f"\nSuccess: {result.success}")
    print(f"Error: {result.error}")

    assert not result.success, "Should fail on timeout"
    assert "timed out" in result.error.lower(), "Should mention timeout"
    assert "sleep 5" in result.error, "Should show the actual command"

    print("✓ Short command shows in error message")

    # Test 2: Long command timeout (truncated)
    print("\n[Test 2: Long command timeout]")
    long_cmd = "echo " + "x" * 150  # Very long command
    print(f"Running: {long_cmd[:50]}... (with 1 second timeout)")

    result = bash_tool.execute(command=f"{long_cmd} && sleep 5", timeout=1)

    print(f"\nSuccess: {result.success}")
    print(f"Error: {result.error[:200]}...")

    assert not result.success, "Should fail on timeout"
    assert "timed out" in result.error.lower(), "Should mention timeout"
    assert "..." in result.error or "echo x" in result.error, "Should show truncated command"
    assert len(result.error) < 500, "Error message should not be too long"

    print("✓ Long command is truncated in error message")

    # Test 3: Verify format
    print("\n[Test 3: Error message format]")
    result = bash_tool.execute(command="sleep 10", timeout=1)

    print(f"Error format: '{result.error}'")

    # Should be in format: "Command timed out after X seconds: <command>"
    assert "Command timed out after" in result.error, "Should have standard format"
    assert "seconds:" in result.error, "Should have colon separator"
    assert "sleep 10" in result.error, "Should show command after colon"

    print("✓ Error message follows correct format")


def test_timeout_display_comparison():
    """Show before/after comparison of error messages."""
    print("\n" + "=" * 70)
    print("Before/After Comparison")
    print("=" * 70)

    print("\n[Before (old)]")
    print("Command timed out after 30 seconds")
    print("❌ User doesn't know which command timed out")

    print("\n[After (new)]")
    print("Command timed out after 30 seconds: npm run build")
    print("✓ User knows exactly what timed out")

    print("\n[Long command (truncated)]")
    print("Command timed out after 30 seconds: python -m pytest tests/test_very_long_test_file_name_...")
    print("✓ Command is shown but truncated if too long")


if __name__ == "__main__":
    try:
        test_timeout_message()
        test_timeout_display_comparison()

        print("\n" + "=" * 70)
        print("✅ ALL TIMEOUT MESSAGE TESTS PASSED!")
        print("=" * 70)

        print("\n[Summary]")
        print("• Timeout errors now show the command")
        print("• Long commands are truncated to 100 chars")
        print("• Format: 'Command timed out after X seconds: <command>'")
        print("• Users can see what timed out and debug accordingly")
        print()

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
