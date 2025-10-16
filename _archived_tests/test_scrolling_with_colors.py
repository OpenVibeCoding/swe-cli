#!/usr/bin/env python3
"""Test scrolling with ANSI colors working together."""

import sys
from pathlib import Path

# Add opencli to path
sys.path.insert(0, str(Path(__file__).parent))

from opencli.ui.chat_app import ChatApplication
from opencli.ui.chat_formatters import ChatBoxFormatter

print("Testing Scrolling + ANSI Colors")
print("=" * 50)

# Create chat application
chat = ChatApplication()
print("✓ ChatApplication created")

# Add many messages to test scrolling
formatter = ChatBoxFormatter()

print("\nAdding messages...")
for i in range(10):
    chat.conversation.add_user_message(f"Test command {i}")
    tool_box = formatter.tool_call_box("test_tool", {"index": str(i)})
    chat.add_assistant_message(tool_box)
    result_box = formatter.success_result_box("test_tool", f"Result {i}")
    chat.add_assistant_message(result_box)
    chat.add_assistant_message(f"⏺ Response {i}")

print(f"✓ Added {len(chat.conversation.messages)} messages")

# Test ANSI rendering
print("\n" + "=" * 50)
print("Testing ANSI Rendering:")
print("=" * 50)
formatted_text = chat._get_conversation_formatted_text()
from prompt_toolkit.formatted_text import ANSI
is_ansi = isinstance(formatted_text, ANSI)
print(f"✓ ANSI object created: {is_ansi}")

# Test vertical scroll calculation
print("\n" + "=" * 50)
print("Testing Vertical Scroll:")
print("=" * 50)
scroll_pos = chat._get_vertical_scroll(chat._conversation_window)
print(f"✓ Scroll position calculated: {scroll_pos}")

plain_text = chat.conversation.get_plain_text()
line_count = plain_text.count('\n')
print(f"✓ Total lines in conversation: {line_count}")
print(f"✓ Scroll matches line count: {scroll_pos == line_count}")

# Summary
print("\n" + "=" * 50)
if is_ansi and scroll_pos > 0 and scroll_pos == line_count:
    print("✅ All tests passed!")
    print("   • ANSI colors: Working")
    print("   • Auto-scroll: Working")
    print("   • Scroll position: Correct")
    print("\nOpenCLI should now have:")
    print("   ✓ Colored text (cyan › prompt, cyan tool boxes, green results)")
    print("   ✓ Auto-scrolling to bottom on new messages")
    print("   ✓ Manual scrolling with PageUp/PageDown")
    sys.exit(0)
else:
    print("❌ Some tests failed")
    if not is_ansi:
        print("   • ANSI colors not working")
    if scroll_pos == 0:
        print("   • Scroll position is 0")
    if scroll_pos != line_count:
        print(f"   • Scroll mismatch: {scroll_pos} != {line_count}")
    sys.exit(1)
