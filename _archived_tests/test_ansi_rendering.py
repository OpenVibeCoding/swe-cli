#!/usr/bin/env python3
"""Test ANSI rendering in chat UI."""

import sys
from pathlib import Path

# Add opencli to path
sys.path.insert(0, str(Path(__file__).parent))

from swecli.ui.chat_app import ChatApplication
from swecli.ui.chat_formatters import ChatBoxFormatter
from prompt_toolkit.formatted_text import ANSI

print("Testing ANSI Rendering in Chat UI")
print("=" * 50)

# Create chat application
chat = ChatApplication()
print("✓ ChatApplication created")

# Add messages
chat.conversation.add_user_message("test command")
formatter = ChatBoxFormatter()
tool_box = formatter.tool_call_box("list_files", {"path": "."})
chat.add_assistant_message(tool_box)
result_box = formatter.success_result_box("list_files", "Files listed successfully")
chat.add_assistant_message(result_box)

# Test ANSI parsing
print("\n" + "=" * 50)
print("Testing ANSI Parsing:")
print("=" * 50)

try:
    formatted_text = chat._get_conversation_formatted_text()
    print(f"✓ Formatted text generated: {type(formatted_text)}")

    # Check if it's an ANSI object
    from prompt_toolkit.formatted_text import ANSI
    is_ansi = isinstance(formatted_text, ANSI)
    print(f"✓ Is ANSI object: {is_ansi}")

    # ANSI objects have a __pt_formatted_text__() method that returns the actual formatted text
    if hasattr(formatted_text, '__pt_formatted_text__'):
        print("✓ Has __pt_formatted_text__() method")

        # Get the actual formatted text tuples
        actual_text = formatted_text.__pt_formatted_text__()
        print(f"✓ Actual formatted text type: {type(actual_text)}")
        print(f"✓ Number of segments: {len(list(actual_text))}")

        # Sample output
        print("\n" + "=" * 50)
        print("Sample Formatted Text (first 10 items):")
        print("=" * 50)
        for i, item in enumerate(list(formatted_text.__pt_formatted_text__())[:10]):
            if isinstance(item, tuple):
                style, text = item
                text_preview = repr(text)[:30]
                print(f"{i}: style='{style}', text={text_preview}")
            else:
                print(f"{i}: {repr(item)[:50]}")

    if is_ansi:
        print("\n✅ ANSI object is being created!")
        print("   • ANSI codes will be parsed by prompt_toolkit")
        print("   • Colors should now render properly in SWE-CLI")
        sys.exit(0)
    else:
        print("\n❌ ANSI object not being created")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
