#!/usr/bin/env python3
"""Test the renovated chat UI with colors and boxes."""

import sys
from pathlib import Path

# Add opencli to path
sys.path.insert(0, str(Path(__file__).parent))

from swecli.ui.chat_app import ChatApplication
from swecli.ui.chat_formatters import ChatBoxFormatter

print("Testing Renovated Chat UI")
print("=" * 50)

# Create chat application
chat = ChatApplication()
print("✓ ChatApplication created")

# Add user message
chat.conversation.add_user_message("list files in current directory")
print("✓ User message added")

# Simulate tool call box
formatter = ChatBoxFormatter()
tool_call_box = formatter.tool_call_box("list_files", {"path": "."})
chat.add_assistant_message(tool_call_box)
print("✓ Tool call box added")

# Simulate result box
result_output = """├── opencli/
│   ├── ui/
│   │   ├── chat_app.py
│   │   ├── chat_console.py
│   │   └── chat_formatters.py
│   └── repl/
│       └── repl.py
└── README.md"""

result_box = formatter.success_result_box("list_files", result_output)
chat.add_assistant_message(result_box)
print("✓ Result box added")

# Add LLM response
chat.add_assistant_message("⏺ I found the project structure. Let me help you with that.")
print("✓ LLM response added")

# Test ANSI colors in plain text
print("\n" + "=" * 50)
print("Testing ANSI Colors in Plain Text:")
print("=" * 50)
plain_text = chat.conversation.get_plain_text()

# Check if ANSI codes are present
has_cyan = '\033[36m' in plain_text or '\033[1;36m' in plain_text
has_green = '\033[32m' in plain_text or '\033[92m' in plain_text
has_reset = '\033[0m' in plain_text

print(f"✓ Cyan color codes present: {has_cyan}")
print(f"✓ Green color codes present: {has_green}")
print(f"✓ Reset codes present: {has_reset}")

# Test box formatting
print("\n" + "=" * 50)
print("Testing Box Formatting:")
print("=" * 50)
has_tool_box = "Tool Call" in plain_text and "┌" in plain_text
has_result_box = "Result" in plain_text and "┌" in plain_text
has_box_chars = "│" in plain_text and "└" in plain_text

print(f"✓ Tool call box present: {has_tool_box}")
print(f"✓ Result box present: {has_result_box}")
print(f"✓ Box characters present: {has_box_chars}")

# Print sample output
print("\n" + "=" * 50)
print("Sample Plain Text Output (with ANSI codes):")
print("=" * 50)
print(plain_text[:500])
print("...")

print("\n" + "=" * 50)
if has_cyan and has_green and has_tool_box and has_result_box:
    print("✅ All UI renovation tests passed!")
    print("   • ANSI colors are working")
    print("   • Box formatting is working")
    print("   • Chat interface is ready")
    sys.exit(0)
else:
    print("❌ Some tests failed")
    if not has_cyan:
        print("   • Missing cyan colors")
    if not has_green:
        print("   • Missing green colors")
    if not has_tool_box:
        print("   • Missing tool call boxes")
    if not has_result_box:
        print("   • Missing result boxes")
    sys.exit(1)
