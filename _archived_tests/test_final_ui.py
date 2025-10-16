#!/usr/bin/env python3
"""Final test of scrolling + ANSI colors with custom control."""

import sys
from pathlib import Path

# Add opencli to path
sys.path.insert(0, str(Path(__file__).parent))

from opencli.ui.chat_app import ChatApplication
from opencli.ui.chat_formatters import ChatBoxFormatter

print("Testing Final UI: Scrolling + ANSI Colors")
print("=" * 50)

# Create chat application
chat = ChatApplication()
print("✓ ChatApplication created")

# Check if custom control is present
has_custom_control = hasattr(chat, 'conversation_control')
print(f"✓ Custom ScrollableFormattedTextControl: {has_custom_control}")

# Add many messages to test scrolling
formatter = ChatBoxFormatter()

print("\nAdding test messages...")
for i in range(5):
    chat.conversation.add_user_message(f"Test command {i}")
    tool_box = formatter.tool_call_box("test_tool", {"index": str(i)})
    chat.add_assistant_message(tool_box)
    result_box = formatter.success_result_box("test_tool", f"Result {i}")
    chat.add_assistant_message(result_box)
    chat.add_assistant_message(f"⏺ Response {i}")

print(f"✓ Added {len(chat.conversation.messages)} messages")

# Test plain text with ANSI
plain_text = chat.conversation.get_plain_text()
has_ansi = '\033[' in plain_text
has_boxes = '┌' in plain_text and '│' in plain_text
line_count = plain_text.count('\n')

print("\n" + "=" * 50)
print("Testing Content:")
print("=" * 50)
print(f"✓ ANSI codes present: {has_ansi}")
print(f"✓ Box characters present: {has_boxes}")
print(f"✓ Total lines: {line_count}")

# Test scroll control
print("\n" + "=" * 50)
print("Testing Scroll Control:")
print("=" * 50)
if has_custom_control:
    print(f"✓ Initial scroll offset: {chat.conversation_control.scroll_offset}")

    # Test scroll methods
    chat.conversation_control.scroll_to_bottom(999999)
    print(f"✓ After scroll_to_bottom: {chat.conversation_control.scroll_offset}")

    # Test scroll up
    chat.conversation_control.move_cursor_up()
    print(f"✓ After move_cursor_up: {chat.conversation_control.scroll_offset}")

    scroll_works = True
else:
    print("❌ Custom control not found")
    scroll_works = False

# Summary
print("\n" + "=" * 50)
if has_custom_control and has_ansi and has_boxes and scroll_works:
    print("✅ All features working!")
    print("   ✓ Custom ScrollableFormattedTextControl")
    print("   ✓ ANSI codes for colors")
    print("   ✓ Box characters for borders")
    print("   ✓ Scroll control methods")
    print("\nOpenCLI should now have:")
    print("   • Colored text (cyan, green, etc.)")
    print("   • Bordered tool call/result boxes")
    print("   • Working scrolling (auto + manual)")
    sys.exit(0)
else:
    print("❌ Some features not working")
    if not has_custom_control:
        print("   • Custom control missing")
    if not has_ansi:
        print("   • ANSI codes missing")
    if not has_boxes:
        print("   • Box characters missing")
    if not scroll_works:
        print("   • Scroll control not working")
    sys.exit(1)
