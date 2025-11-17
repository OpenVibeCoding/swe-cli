"""Slash command routing for the Textual chat app."""

from __future__ import annotations

import asyncio
import time
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
            await self.app._start_model_picker()
            return True

        if cmd == "/scroll":
            if conversation is not None:
                self._render_scroll_demo(conversation)
            return True

        if cmd == "/quit":
            self.app.exit()
            return True

        # Handle MCP commands asynchronously to avoid blocking
        if cmd == "/mcp":
            await self._handle_mcp_command(command)
            return True

        return False

    def _render_help(self, conversation) -> None:
        conversation.add_system_message("Available commands:")
        conversation.add_system_message("  /help - Show this help")
        conversation.add_system_message("  /clear - Clear conversation")
        conversation.add_system_message("  /demo - Show demo messages")
        conversation.add_system_message("  /scroll - Generate many messages (test scrolling)")
        conversation.add_system_message("  /models - Configure model slots")
        conversation.add_system_message("  /mcp connect <server> - Connect to MCP server (non-blocking)")
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

    async def _handle_mcp_command(self, command: str) -> None:
        """Handle MCP commands asynchronously with proper UI formatting.

        Args:
            command: The full MCP command (e.g., "/mcp connect github")
        """
        import shlex

        conversation = getattr(self.app, "conversation", None)
        if conversation is None:
            return

        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.strip().split()

        if len(parts) < 2:
            conversation.add_system_message("Usage: /mcp <subcommand> [args]")
            return

        subcommand = parts[1].lower()

        # Handle connect subcommand asynchronously
        if subcommand == "connect":
            if len(parts) < 3:
                conversation.add_system_message("Usage: /mcp connect <server_name>")
                return

            server_name = parts[2]
            await self._async_mcp_connect(server_name, conversation)
        else:
            # For other MCP subcommands, fall back to backend processing
            if hasattr(self.app, 'on_message') and self.app.on_message:
                self.app.on_message(command)

    async def _async_mcp_connect(self, server_name: str, conversation) -> None:
        """Connect to MCP server asynchronously with spinner.

        Args:
            server_name: Name of the MCP server to connect to
            conversation: Conversation log to display results
        """
        start_time = time.monotonic()

        # Start spinner
        if hasattr(self.app, '_start_local_spinner'):
            self.app._start_local_spinner()

        try:
            # Get MCP manager from the app or runner
            mcp_manager = None
            if hasattr(self.app, 'runner') and hasattr(self.app.runner, 'repl'):
                mcp_manager = getattr(self.app.runner.repl, 'mcp_manager', None)
            elif hasattr(self.app, 'mcp_manager'):
                mcp_manager = self.app.mcp_manager

            if not mcp_manager:
                conversation.add_system_message("❌ MCP manager not available")
                return

            # Add initial status message
            elapsed = int(time.monotonic() - start_time)
            status_msg = f"⏺ MCP ({server_name}) ({elapsed}s)\n  ⎿ Connecting to {server_name}..."
            conversation.add_system_message(status_msg)

            # Run connection in background thread to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, mcp_manager.connect_sync, server_name)

            if success:
                tools = mcp_manager.get_server_tools(server_name)
                elapsed = int(time.monotonic() - start_time)

                # Success message with proper formatting
                result_msg = f"⏺ MCP ({server_name}) ({elapsed}s)\n  ⎿ Connected to {server_name} ({len(tools)} tools available)"
                conversation.add_system_message(result_msg)

                # Refresh runtime tooling if callback is available
                refresh_callback = None
                if hasattr(self.app, 'runner') and hasattr(self.app.runner, '_refresh_runtime_tooling'):
                    refresh_callback = self.app.runner._refresh_runtime_tooling
                elif hasattr(self.app, 'refresh_runtime'):
                    refresh_callback = self.app.refresh_runtime

                if refresh_callback:
                    await loop.run_in_executor(None, refresh_callback)

            else:
                elapsed = int(time.monotonic() - start_time)
                error_msg = f"⏺ MCP ({server_name}) ({elapsed}s)\n  ⎿ ❌ Failed to connect to {server_name}"
                conversation.add_system_message(error_msg)

        except Exception as e:
            elapsed = int(time.monotonic() - start_time)
            error_msg = f"⏺ MCP ({server_name}) ({elapsed}s)\n  ⎿ ❌ Error connecting to {server_name}: {str(e)}"
            conversation.add_system_message(error_msg)

        finally:
            # Stop spinner
            if hasattr(self.app, '_stop_local_spinner'):
                self.app._stop_local_spinner()


__all__ = ["CommandRouter"]
