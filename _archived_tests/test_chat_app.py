#!/usr/bin/env python3
"""Test the new ChatApplication with fixed bottom input."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from swecli.ui.chat_app import ChatApplication


def handle_message(text: str):
    """Handle user messages."""
    # Echo the message back
    chat.add_assistant_message(f"You said: '{text}'")

    # Show some example responses
    if "hello" in text.lower():
        chat.add_assistant_message("Hi there! How can I help you today?")
    elif "file" in text.lower():
        chat.add_assistant_message("I can help you create, edit, or read files.")
    elif "help" in text.lower():
        chat.add_assistant_message("Available commands:\n- Type any message to chat\n- Ctrl+C to exit\n- Ctrl+L to clear conversation")


def main():
    global chat

    print("Starting ChatApplication test...")
    print("Instructions:")
    print("  - Type messages in the input field at the bottom")
    print("  - Press Enter to send")
    print("  - Messages appear in the conversation area above")
    print("  - Input box stays fixed at bottom (like ChatGPT)")
    print("  - Press Ctrl+C to exit")
    print()

    # Create chat application
    chat = ChatApplication(on_message=handle_message)

    # Add welcome messages
    chat.conversation.add_system_message("═══════════════════════════════════════════════")
    chat.conversation.add_system_message("  Welcome to SWE-CLI Chat Interface Test")
    chat.conversation.add_system_message("═══════════════════════════════════════════════")
    chat.conversation.add_system_message("")
    chat.conversation.add_assistant_message("Hello! I'm the SWE-CLI assistant.")
    chat.conversation.add_assistant_message("Try typing messages in the input box below.")
    chat.conversation.add_assistant_message("The input box will stay at the bottom, just like ChatGPT!")

    # Run the application
    chat.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
