#!/usr/bin/env python3
"""Test conversation buffer functionality."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown
from swecli.ui.conversation_buffer import ConversationBuffer


def test_conversation_buffer():
    """Test ConversationBuffer class."""
    print("Testing ConversationBuffer...")

    # Test 1: Create buffer
    buffer = ConversationBuffer(max_items=100)
    assert buffer.is_empty(), "Buffer should start empty"
    assert buffer.count() == 0, "Count should be 0"
    print("✓ Buffer initialized correctly")

    # Test 2: Add different types of renderables
    text1 = Text("Hello World", style="bold")
    panel1 = Panel("Test Panel", title="Title")
    markdown1 = Markdown("# Heading\nContent")

    buffer.add(text1)
    buffer.add(panel1)
    buffer.add(markdown1)

    assert buffer.count() == 3, "Should have 3 items"
    assert not buffer.is_empty(), "Buffer should not be empty"
    print("✓ Added 3 different renderables")

    # Test 3: Get all items
    all_items = buffer.get_all()
    assert len(all_items) == 3, "get_all() should return 3 items"
    assert all_items[0] is text1, "First item should be text1"
    assert all_items[1] is panel1, "Second item should be panel1"
    assert all_items[2] is markdown1, "Third item should be markdown1"
    print("✓ get_all() returns correct items in order")

    # Test 4: Get last N items
    last_2 = buffer.get_last_n(2)
    assert len(last_2) == 2, "get_last_n(2) should return 2 items"
    assert last_2[0] is panel1, "First of last 2 should be panel1"
    assert last_2[1] is markdown1, "Second of last 2 should be markdown1"
    print("✓ get_last_n() works correctly")

    # Test 5: Get more than available
    last_10 = buffer.get_last_n(10)
    assert len(last_10) == 3, "get_last_n(10) should return all 3 items"
    print("✓ get_last_n() handles requests larger than buffer size")

    # Test 6: Test max_items limit
    small_buffer = ConversationBuffer(max_items=10)
    for i in range(15):
        small_buffer.add(Text(f"Item {i}"))

    # Should only keep 10 items (90% of max after cleanup)
    assert small_buffer.count() <= 10, f"Buffer should have <= 10 items, has {small_buffer.count()}"
    print(f"✓ Max items limit works (kept {small_buffer.count()} items out of 15)")

    # Test 7: Clear buffer
    buffer.clear()
    assert buffer.is_empty(), "Buffer should be empty after clear()"
    assert buffer.count() == 0, "Count should be 0 after clear()"
    print("✓ clear() empties the buffer")

    # Test 8: Add after clear
    buffer.add(Text("New item"))
    assert buffer.count() == 1, "Should have 1 item after add"
    print("✓ Can add items after clearing")

    print("\n✅ All tests passed! ConversationBuffer is working correctly.")
    return True


if __name__ == "__main__":
    try:
        success = test_conversation_buffer()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
