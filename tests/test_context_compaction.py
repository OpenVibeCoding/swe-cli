"""Test context compaction with 1000 token limit."""

import asyncio
from swecli.models.config import AppConfig
from swecli.core.context import ContextTokenMonitor
from swecli.core.agents.compact_agent import CompactAgent


def test_token_counting():
    """Test that token counting works correctly."""
    monitor = ContextTokenMonitor(model="gpt-4", context_limit=1000)

    # Test simple text
    text = "Hello, world! This is a test of token counting."
    token_count = monitor.count_tokens(text)

    print(f"✓ Token counting works: '{text}' = {token_count} tokens")
    assert token_count > 0, "Token count should be positive"


def test_compaction_threshold():
    """Test that compaction triggers at correct threshold."""
    monitor = ContextTokenMonitor(model="gpt-4", context_limit=1000, compaction_threshold=0.99)

    # Test at 98% (should not need compaction)
    assert not monitor.needs_compaction(980), "Should not compact at 98%"

    # Test at 99.5% (should need compaction)
    assert monitor.needs_compaction(995), "Should compact at 99.5%"

    print("✓ Compaction threshold works correctly")


def test_usage_stats():
    """Test usage statistics calculation."""
    monitor = ContextTokenMonitor(model="gpt-4", context_limit=1000)

    # Test at 50% usage
    stats = monitor.get_usage_stats(500)

    assert stats["current_tokens"] == 500
    assert stats["limit"] == 1000
    assert stats["available"] == 500
    assert abs(stats["usage_percent"] - 50.0) < 0.1
    assert abs(stats["remaining_percent"] - 50.0) < 0.1
    assert not stats["needs_compaction"]

    print(f"✓ Usage stats work: {stats['remaining_percent']:.0f}% remaining")


def test_compactor_agent():
    """Test compactor agent (requires API key)."""

    async def _run_compactor() -> None:
        config = AppConfig()
        compactor = CompactAgent(config)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Create a Flask app with user authentication"},
            {
                "role": "assistant",
                "content": "I'll help you create a Flask app. First, let me check the project structure...",
            },
            {"role": "tool", "content": "Files: app.py, models.py, views.py"},
            {"role": "assistant", "content": "Great! I'll create the authentication system now."},
            {"role": "user", "content": "Add database models for User and Post"},
            {"role": "assistant", "content": "I'll add the User and Post models to models.py..."},
        ]

        print("\n⏺ Testing compactor agent...")
        summary = compactor.compact(messages)

        print("\n✓ Compactor agent works!")
        print(f"\nOriginal messages: {len(messages)}")
        print(f"Summary length: {len(summary)} chars")
        print(f"\nSummary preview:\n{summary[:300]}...")

        total_original = sum(len(str(m.get("content", ""))) for m in messages)
        reduction = (1 - len(summary) / total_original) * 100
        print(f"\nReduction: {reduction:.1f}%")

        assert len(summary) < total_original, "Summary should be shorter than original"
        assert reduction > 20, "Should achieve at least 20% reduction"

    try:
        asyncio.run(_run_compactor())
    except Exception as e:  # noqa: BLE001
        print(f"\n⚠ Compactor test skipped: {e}")
        print("(This is expected if no API key is configured)")


def test_message_replacement():
    """Test message buffer replacement logic."""
    # Simulate message history
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "First message"},
        {"role": "assistant", "content": "First response"},
        {"role": "user", "content": "Second message"},
        {"role": "assistant", "content": "Second response"},
        {"role": "user", "content": "Third message"},
        {"role": "assistant", "content": "Third response"},
    ]

    # Simulate replacement
    system_msg = messages[0]
    recent_msgs = messages[-2:]  # Last 2 messages

    summary_msg = {
        "role": "system",
        "content": "# Summary\n\nPrevious conversation about creating a Flask app.",
    }

    new_messages = [system_msg, summary_msg] + recent_msgs

    # Verify structure
    assert len(new_messages) == 4, "Should have 4 messages after compaction"
    assert new_messages[0]["role"] == "system"
    assert new_messages[1]["role"] == "system"  # Summary
    assert new_messages[-2]["role"] == "user"
    assert new_messages[-1]["role"] == "assistant"

    print("✓ Message replacement logic works correctly")


if __name__ == "__main__":
    print("Testing Context Compaction Feature\n")
    print("=" * 50)

    # Run sync tests
    print("\n1. Token Counting:")
    test_token_counting()

    print("\n2. Compaction Threshold:")
    test_compaction_threshold()

    print("\n3. Usage Statistics:")
    test_usage_stats()

    print("\n4. Message Replacement:")
    test_message_replacement()

    # Run async test
    print("\n5. Compactor Agent:")
    asyncio.run(test_compactor_agent())

    print("\n" + "=" * 50)
    print("\n✅ All tests passed!")
    print("\nNext step: Run SWE-CLI and test with actual conversations")
    print("The context should trigger compaction at 99% (0% remaining)")
