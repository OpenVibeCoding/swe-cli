#!/usr/bin/env python3
"""Test ContextTokenMonitor and Session integration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from swecli.core.context import ContextTokenMonitor
from swecli.models.message import ChatMessage, Role, ToolCall
from swecli.models.session import Session

def test_basic_counting():
    """Test basic token counting."""
    print("\n" + "=" * 60)
    print("Test 1: Basic Token Counting")
    print("=" * 60)

    monitor = ContextTokenMonitor()

    # Simple text
    text = "Hello, world! This is a test of token counting."
    tokens = monitor.count_tokens(text)
    print(f"Text: '{text}'")
    print(f"Tokens: {tokens}")
    assert tokens > 0, "Token count should be greater than 0"
    print("✓ Basic counting works\n")


def test_message_counting():
    """Test message token counting."""
    print("=" * 60)
    print("Test 2: Message Token Counting")
    print("=" * 60)

    monitor = ContextTokenMonitor()

    # Create a message
    msg = ChatMessage(
        role=Role.USER,
        content="Create a Python script that calculates fibonacci numbers"
    )

    tokens = monitor.count_message_tokens(msg)
    print(f"Message: {msg.content}")
    print(f"Tokens: {tokens}")
    assert tokens > 0, "Message should have tokens"
    print("✓ Message counting works\n")


def test_tool_call_counting():
    """Test tool call token counting."""
    print("=" * 60)
    print("Test 3: Tool Call Token Counting")
    print("=" * 60)

    monitor = ContextTokenMonitor()

    tool_call = ToolCall(
        id="tc_123",
        name="write_file",
        parameters={"file_path": "test.py", "content": "print('hello world')"},
        result="File written successfully"
    )

    tokens = monitor._count_tool_call_tokens(tool_call)
    print(f"Tool: {tool_call.name}")
    print(f"Parameters: {tool_call.parameters}")
    print(f"Result: {tool_call.result}")
    print(f"Tokens: {tokens}")
    assert tokens > 10, "Tool call should have substantial tokens"
    print("✓ Tool call counting works\n")


def test_compaction_threshold():
    """Test compaction threshold detection."""
    print("=" * 60)
    print("Test 4: Compaction Threshold")
    print("=" * 60)

    monitor = ContextTokenMonitor()

    # Test below threshold
    below = 100000  # 39% of 256k
    assert not monitor.needs_compaction(below), "Should not need compaction at 39%"
    print(f"✓ {below} tokens (39%) - No compaction needed")

    # Test above threshold
    above = 210000  # 82% of 256k
    assert monitor.needs_compaction(above), "Should need compaction at 82%"
    print(f"✓ {above} tokens (82%) - Compaction needed\n")


def test_usage_stats():
    """Test usage statistics."""
    print("=" * 60)
    print("Test 5: Usage Statistics")
    print("=" * 60)

    monitor = ContextTokenMonitor()

    current = 150000  # 58.6%
    stats = monitor.get_usage_stats(current)

    print(f"Current tokens: {stats['current_tokens']:,}")
    print(f"Limit: {stats['limit']:,}")
    print(f"Available: {stats['available']:,}")
    print(f"Usage: {stats['usage_percent']:.1f}%")
    print(f"Until compact: {stats['until_compact_percent']:.1f}%")
    print(f"Needs compaction: {stats['needs_compaction']}")

    assert stats["current_tokens"] == 150000
    assert stats["available"] == 106000
    assert 58 <= stats["usage_percent"] <= 59
    assert not stats["needs_compaction"]
    print("✓ Usage stats correct\n")


def test_session_integration():
    """Test Session integration with token monitoring."""
    print("=" * 60)
    print("Test 6: Session Integration")
    print("=" * 60)

    # Create session
    session = Session()

    # Add messages
    msg1 = ChatMessage(role=Role.USER, content="Hello, how are you?")
    session.add_message(msg1)

    print(f"Message 1: '{msg1.content}'")
    print(f"Cached tokens: {msg1.tokens}")
    assert msg1.tokens is not None, "Message should have cached tokens"
    assert msg1.tokens > 0, "Cached tokens should be positive"

    # Add more messages
    msg2 = ChatMessage(role=Role.ASSISTANT, content="I'm doing well, thank you! How can I help you today?")
    session.add_message(msg2)

    print(f"\nMessage 2: '{msg2.content}'")
    print(f"Cached tokens: {msg2.tokens}")

    # Check session totals
    print(f"\nSession total: {session.total_tokens_cached:,} tokens")
    assert session.total_tokens_cached > 0, "Session should have total tokens"
    print("✓ Session integration works\n")


def test_token_stats_method():
    """Test Session.get_token_stats() method."""
    print("=" * 60)
    print("Test 7: Session Token Stats")
    print("=" * 60)

    session = Session()

    # Add several messages
    for i in range(5):
        msg = ChatMessage(
            role=Role.USER if i % 2 == 0 else Role.ASSISTANT,
            content=f"This is message number {i+1} with some content to count."
        )
        session.add_message(msg)

    # Get stats
    stats = session.get_token_stats()

    print(f"Current tokens: {stats['current_tokens']:,}")
    print(f"Limit: {stats['limit']:,}")
    print(f"Usage: {stats['usage_percent']:.2f}%")
    print(f"Until compact: {stats['until_compact_percent']:.2f}%")
    print(f"Needs compaction: {stats['needs_compaction']}")

    assert stats["current_tokens"] > 0, "Should have tokens"
    assert stats["usage_percent"] < 1, "Usage should be very low"
    assert not stats["needs_compaction"], "Should not need compaction yet"
    print("✓ Session token stats work\n")


def test_format_tokens():
    """Test token formatting."""
    print("=" * 60)
    print("Test 8: Token Formatting")
    print("=" * 60)

    monitor = ContextTokenMonitor()

    test_cases = [
        (150, "150"),
        (1000, "1.0k"),
        (1500, "1.5k"),
        (3700, "3.7k"),
        (150000, "150.0k"),
    ]

    for count, expected in test_cases:
        formatted = monitor.format_tokens(count)
        print(f"{count:,} tokens → '{formatted}' (expected: '{expected}')")
        assert formatted == expected, f"Expected '{expected}', got '{formatted}'"

    print("✓ Token formatting works\n")


def main():
    """Run all tests."""
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║     CONTEXT TOKEN MONITOR TESTS                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    try:
        test_basic_counting()
        test_message_counting()
        test_tool_call_counting()
        test_compaction_threshold()
        test_usage_stats()
        test_session_integration()
        test_token_stats_method()
        test_format_tokens()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n💡 Token monitoring is working correctly!")
        print("   • tiktoken provides accurate token counts")
        print("   • Session integration is functional")
        print("   • Compaction threshold detection works")
        print("   • Token stats are accurate")
        print("\n🎉 Phase 1 Complete: Token Monitoring\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
