#!/usr/bin/env python3
"""Test SplitScreenLayout functionality."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.text import Text
from rich.panel import Panel
from swecli.ui.conversation_buffer import ConversationBuffer
from swecli.ui.split_layout import SplitScreenLayout


def test_split_layout():
    """Test SplitScreenLayout class."""
    print("Testing SplitScreenLayout...")

    # Test 1: Create layout with empty buffer
    buffer = ConversationBuffer()
    layout = SplitScreenLayout(buffer, console_width=80)

    assert layout.buffer is buffer, "Layout should reference the buffer"
    assert layout.conversation_window is not None, "Conversation window should exist"
    print("✓ SplitScreenLayout initialized with empty buffer")

    # Test 2: Add items to buffer and render
    text1 = Text("Hello World", style="bold")
    buffer.add(text1)

    # Get conversation text
    conv_text = layout._get_conversation_text()
    assert conv_text is not None, "Should get conversation text"
    assert len(conv_text) > 0, "Conversation text should not be empty"
    print("✓ Can render conversation text from buffer")

    # Test 3: Add multiple items
    text2 = Text("Second message", style="cyan")
    panel1 = Panel("Important message", title="Alert")
    buffer.add(text2)
    buffer.add(panel1)

    conv_text = layout._get_conversation_text()
    assert conv_text is not None, "Should render multiple items"
    print("✓ Can render multiple items from buffer")

    # Test 4: Test rendering Rich objects to text
    rendered = layout._render_rich_to_text(text1)
    assert isinstance(rendered, str), "Should return string"
    assert len(rendered) > 0, "Rendered text should not be empty"
    print("✓ Can render Rich objects to plain text")

    # Test 5: Test with Panel
    rendered_panel = layout._render_rich_to_text(panel1)
    assert isinstance(rendered_panel, str), "Should render panel to string"
    assert "Important message" in rendered_panel, "Should contain panel content"
    print("✓ Can render Panel to plain text")

    # Test 6: Get layout container
    container = layout.get_layout_container()
    assert container is not None, "Should get layout container"
    print("✓ Can get layout container")

    # Test 7: Test scrolling methods (they should not crash)
    layout.scroll_to_bottom()
    layout.scroll_up(5)
    layout.scroll_down(3)
    print("✓ Scrolling methods work without errors")

    # Test 8: Test refresh (should not crash)
    layout.refresh()
    print("✓ Refresh works without errors")

    # Test 9: Test with empty buffer
    empty_buffer = ConversationBuffer()
    empty_layout = SplitScreenLayout(empty_buffer)
    empty_text = empty_layout._get_conversation_text()
    assert empty_text is not None, "Should handle empty buffer"
    print("✓ Handles empty buffer gracefully")

    # Test 10: Test with complex Rich renderables
    from rich.markdown import Markdown
    md = Markdown("# Heading\n\nParagraph with **bold** text")
    buffer.add(md)
    conv_text = layout._get_conversation_text()
    assert conv_text is not None, "Should render Markdown"
    print("✓ Can render Markdown objects")

    print("\n✅ All tests passed! SplitScreenLayout is working correctly.")
    return True


if __name__ == "__main__":
    try:
        success = test_split_layout()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
