"""Slash command routing for the Textual chat app."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from swecli.ui_textual.chat_app import SWECLIChatApp


class CommandRouter:
    """Handle slash commands issued from the Textual chat input."""

    def __init__(self, app: "SWECLIChatApp") -> None:
        self.app = app

    async def handle(self, command: str) -> bool:
        """Dispatch a slash command. Returns True if handled locally."""

        cmd = command.lower().split()[0]
        conversation = getattr(self.app, "conversation", None)

        if cmd == "/help":
            if conversation is None:
                return True
            self._render_help(conversation)
            return True

        if cmd == "/clear":
            if conversation is not None:
                conversation.clear()
                conversation.add_system_message("Conversation cleared.")
            return True

        if cmd == "/demo":
            if conversation is not None:
                self._render_demo(conversation)
            return True

        if cmd == "/models":
            # Show current models first
            self._show_current_models(conversation)
            # Then open model picker
            await self.app._start_model_picker()
            return True

        if cmd == "/scroll":
            if conversation is not None:
                self._render_scroll_demo(conversation)
            return True

        if cmd == "/quit":
            self.app.exit()
            return True

        return False

    def _show_current_models(self, conversation) -> None:
        """Show current model configuration."""
        if conversation is None:
            return

        from rich.text import Text

        # Create header
        header = Text()
        header.append("🤖 Current Model Configuration\n", style="bold blue")
        conversation.add_system_message(str(header))

        # Get model config from app
        if hasattr(self.app, 'get_model_config'):
            model_config = self.app.get_model_config()

            # Normal model
            normal_model = self.app.model if hasattr(self.app, 'model') else "Unknown"
            normal_text = Text()
            normal_text.append("Normal: ", style="bold #6a6a6a")
            normal_text.append(self._get_short_model_display(normal_model), style="green")
            conversation.add_system_message(str(normal_text))

            # Thinking and Vision models (if available)
            if hasattr(self.app, 'model_slots') and self.app.model_slots:
                for slot_name, slot_value in self.app.model_slots.items():
                    if slot_value:
                        provider, model = slot_value
                        slot_text = Text()
                        slot_text.append(f"{slot_name.title()}: ", style="bold #6a6a6a")
                        slot_text.append(self._get_short_model_display(f"{provider}/{model}" if provider else model),
                                      style="cyan" if slot_name == "thinking" else "magenta")
                        conversation.add_system_message(str(slot_text))
                    else:
                        slot_text = Text()
                        slot_text.append(f"{slot_name.title()}: ", style="bold #6a6a6a")
                        slot_text.append("Not configured", style="italic #5a5a5a")
                        conversation.add_system_message(str(slot_text))

            # Separator
            conversation.add_system_message("")

        # Instructions
        info_text = Text()
        info_text.append("ℹ️  ", style="blue")
        info_text.append("Opening model selector to change configuration...", style="#6a6a6a")
        conversation.add_system_message(str(info_text))

    def _get_short_model_display(self, model_name: str) -> str:
        """Get short display name for model."""
        if not model_name:
            return "Not set"

        # Extract just the model name part
        if "/" in model_name:
            model_name = model_name.split("/")[-1]

        # Remove common suffixes
        model_name = model_name.replace("-instruct", "").replace("-latest", "")

        return model_name

    def _render_help(self, conversation) -> None:
        conversation.add_system_message("Available commands:")
        conversation.add_system_message("  /help - Show this help")
        conversation.add_system_message("  /clear - Clear conversation")
        conversation.add_system_message("  /demo - Show demo messages")
        conversation.add_system_message("  /scroll - Generate many messages (test scrolling)")
        conversation.add_system_message("  /models - Configure model slots")
        conversation.add_system_message("  /quit - Exit application")
        conversation.add_system_message("")
        conversation.add_system_message("✨ Multi-line Input:")
        conversation.add_system_message("  Enter - Send message")
        conversation.add_system_message("  Shift+Enter - New line in message")
        conversation.add_system_message("  Type multiple lines, then press Enter to send!")
        conversation.add_system_message("")
        conversation.add_system_message("📜 Scrolling:")
        conversation.add_system_message("  Ctrl+Up - Focus conversation (then use arrow keys)")
        conversation.add_system_message("  Ctrl+Down - Focus input (for typing)")
        conversation.add_system_message("  Arrow Up/Down - Scroll line by line")
        conversation.add_system_message("  Page Up/Down - Scroll by page")
        conversation.add_system_message("")
        conversation.add_system_message("⌨️  Other Shortcuts:")
        conversation.add_system_message("  Ctrl+L - Clear conversation")
        conversation.add_system_message("  Ctrl+C - Quit application")
        conversation.add_system_message("  ESC - Interrupt processing")

    def _render_demo(self, conversation) -> None:
        conversation.add_assistant_message("Here's a demo of different message types:")
        conversation.add_system_message("")

        conversation.add_tool_call("Shell", "command='ls -la'")
        conversation.add_tool_result("total 64\ndrwxr-xr-x  10 user  staff   320 Jan 27 10:00 .")

        conversation.add_system_message("")
        conversation.add_tool_call("Read", "file_path='swecli/cli.py'")
        conversation.add_tool_result("File read successfully (250 lines)")

        conversation.add_system_message("")
        conversation.add_tool_call("Write", "file_path='test.py', content='...'")
        conversation.add_tool_result("File written successfully")

        conversation.add_system_message("")
        conversation.add_error("Example error: File not found")

    def _render_scroll_demo(self, conversation) -> None:
        conversation.add_assistant_message("Generating 50 messages to test scrolling...")
        conversation.add_system_message("")
        for i in range(1, 51):
            if i % 10 == 0:
                conversation.add_system_message(f"--- Message {i} ---")
            elif i % 5 == 0:
                conversation.add_tool_call("TestTool", f"iteration={i}")
                conversation.add_tool_result(f"Result for iteration {i}")
            elif i % 3 == 0:
                conversation.add_user_message(f"Test user message {i}")
            else:
                conversation.add_assistant_message(
                    f"Test assistant message {i}: Lorem ipsum dolor sit amet, consectetur adipiscing elit."
                )
        conversation.add_system_message("")
        conversation.add_assistant_message("✓ Done! Try scrolling up with mouse wheel or Page Up.")


__all__ = ["CommandRouter"]
