"""Entry point helper for launching the Textual chat UI alongside core SWE-CLI services."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Optional

from rich.ansi import AnsiDecoder
from rich.text import Text

from swecli.core.management import ConfigManager, OperationMode, SessionManager
from swecli.models.message import ChatMessage, Role
from swecli.repl.repl import REPL
from swecli.repl.chat.approval_manager import ChatApprovalManager
from swecli.ui_textual.chat_app import create_chat_app


class TextualRunner:
    """Orchestrates the Textual chat UI with the core SWE-CLI runtime."""

    def __init__(
        self,
        *,
        working_dir: Optional[Path] = None,
        resume_session: Optional[str] = None,
        continue_session: bool = False,
        repl: Optional[REPL] = None,
        config_manager: Optional[ConfigManager] = None,
        session_manager: Optional[SessionManager] = None,
    ) -> None:
        self.working_dir = Path(working_dir or Path.cwd()).resolve()

        if repl is not None:
            self.repl = repl
            self.config_manager = config_manager or getattr(repl, "config_manager", ConfigManager(self.working_dir))
            self.config = getattr(repl, "config", None) or self.config_manager.get_config()
            self.session_manager = session_manager or getattr(repl, "session_manager", None)
            if self.session_manager is None:
                raise ValueError("SessionManager is required when providing a custom REPL")
            if not hasattr(self.repl, "config"):
                self.repl.config = self.config
            if hasattr(self.repl.config, "permissions") and hasattr(self.repl.config.permissions, "bash"):
                self.repl.config.permissions.bash.enabled = True
            elif hasattr(self.repl.config, "enable_bash"):
                self.repl.config.enable_bash = True
        else:
            self.config_manager = config_manager or ConfigManager(self.working_dir)
            self.config = self.config_manager.load_config()
            self.config_manager.ensure_directories()

            session_root = Path(self.config.session_dir).expanduser()
            self.session_manager = session_manager or SessionManager(session_root)
            self._configure_session(resume_session, continue_session)

            self.repl = REPL(self.config_manager, self.session_manager)
            self.repl.mode_manager.set_mode(OperationMode.NORMAL)
            self.repl.approval_manager = ChatApprovalManager(self.repl.console)
            if hasattr(self.repl.config, "permissions") and hasattr(self.repl.config.permissions, "bash"):
                self.repl.config.permissions.bash.enabled = True
            elif hasattr(self.repl.config, "enable_bash"):
                self.repl.config.enable_bash = True
            connect = getattr(self.repl, "_connect_mcp_servers", None)
            if callable(connect):
                connect()

        # Get model display name and slot summaries from config
        model_display = f"{self.config.model_provider}/{self.config.model}"
        model_slots = self._build_model_slots()

        create_kwargs = {
            "on_message": self.enqueue_message,
            "model": model_display,
            "model_slots": model_slots,
            "on_cycle_mode": self._cycle_mode,
            "completer": getattr(self.repl, "completer", None),
            "on_model_selected": self._apply_model_selection,
            "get_model_config": self._get_model_config_snapshot,
        }

        try:
            self.app = create_chat_app(**create_kwargs)
        except TypeError:
            legacy_kwargs = {
                "on_message": self.enqueue_message,
                "model": model_display,
                "model_slots": model_slots,
                "on_cycle_mode": self._cycle_mode,
                "completer": getattr(self.repl, "completer", None),
            }
            self.app = create_chat_app(**legacy_kwargs)
        if hasattr(self.repl.approval_manager, "chat_app"):
            self.repl.approval_manager.chat_app = self.app
        if hasattr(self.repl, "config_commands"):
            self.repl.config_commands.chat_app = self.app

        self._pending: asyncio.Queue[str] = asyncio.Queue()
        self._console_queue: asyncio.Queue[str] = asyncio.Queue()
        self._ansi_decoder = AnsiDecoder()
        self._install_console_bridge()
        self._loop = asyncio.new_event_loop()
        self._message_task: asyncio.Task[None] | None = None
        self._console_task: asyncio.Task[None] | None = None
        self._last_console_line: str | None = None
        self._last_assistant_message: str | None = None
        self._suppress_console_duplicate = False
        self._last_assistant_message_normalized: str | None = None

    def _build_model_slots(self) -> dict[str, tuple[str, str]]:
        """Prepare formatted model slot information for the footer."""

        def format_model(
            provider: Optional[str],
            model_id: Optional[str],
        ) -> tuple[str, str] | None:
            if not model_id:
                return None
            provider_display = provider.capitalize() if provider else "Unknown"
            return provider_display, model_id

        config = self.config
        slots: dict[str, tuple[str, str]] = {}

        normal = format_model(config.model_provider, config.model)
        if normal:
            slots["normal"] = normal

        if config.model_thinking and config.model_thinking != config.model:
            thinking = format_model(
                config.model_thinking_provider,
                config.model_thinking,
            )
            if thinking:
                slots["thinking"] = thinking

        if config.model_vlm and config.model_vlm != config.model:
            vision = format_model(
                config.model_vlm_provider,
                config.model_vlm,
            )
            if vision:
                slots["vision"] = vision

        return slots

    def _refresh_ui_config(self) -> None:
        """Refresh cached config-driven UI indicators after config changes."""
        # Refresh cached config instance (commands may mutate or reload it)
        self.config = self.config_manager.get_config()
        model_display = f"{self.config.model_provider}/{self.config.model}"
        if hasattr(self.app, "update_primary_model"):
            self.app.update_primary_model(model_display)
        if hasattr(self.app, "update_model_slots"):
            self.app.update_model_slots(self._build_model_slots())

    def _get_model_config_snapshot(self) -> dict[str, dict[str, str]]:
        """Return current model configuration details for the UI."""
        config = self.config_manager.get_config()

        try:
            from swecli.config import get_model_registry

            registry = get_model_registry()
        except Exception:  # pragma: no cover - defensive
            registry = None

        def resolve(provider_id: Optional[str], model_id: Optional[str]) -> dict[str, str]:
            if not provider_id or not model_id:
                return {}

            provider_display = provider_id.capitalize()
            model_display = model_id

            if registry is not None:
                provider_info = registry.get_provider(provider_id)
                if provider_info:
                    provider_display = provider_info.name
                found = registry.find_model_by_id(model_id)
                if found:
                    _, _, model_info = found
                    model_display = model_info.name
            else:
                if "/" in model_id:
                    model_display = model_id.split("/")[-1]

            return {
                "provider": provider_id,
                "provider_display": provider_display,
                "model": model_id,
                "model_display": model_display,
            }

        snapshot: dict[str, dict[str, str]] = {}
        snapshot["normal"] = resolve(config.model_provider, config.model)

        thinking_entry = resolve(config.model_thinking_provider, config.model_thinking)
        if thinking_entry:
            snapshot["thinking"] = thinking_entry

        vision_entry = resolve(config.model_vlm_provider, config.model_vlm)
        if vision_entry:
            snapshot["vision"] = vision_entry

        return snapshot

    async def _apply_model_selection(self, slot: str, provider_id: str, model_id: str):
        """Apply a model selection coming from the Textual UI."""
        result = await asyncio.to_thread(
            self.repl.config_commands._switch_to_model,
            provider_id,
            model_id,
            slot,
        )
        if result.success:
            self._refresh_ui_config()
        return result

    def _configure_session(self, resume: Optional[str], continue_session: bool) -> None:
        """Prepare session state mirroring CLI semantics."""

        if resume:
            self.session_manager.load_session(resume)
            return

        if continue_session:
            loaded = self.session_manager.load_latest_session(self.working_dir)
            if loaded:
                return

        self.session_manager.create_session(working_directory=str(self.working_dir))

    def enqueue_message(self, text: str) -> None:
        """Queue a message from the UI for processing."""
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is self._loop:
            self._pending.put_nowait(text)
        elif self._loop.is_running():
            self._loop.call_soon_threadsafe(self._pending.put_nowait, text)
        else:
            self._pending.put_nowait(text)

    async def _process_messages(self) -> None:
        """Consume queued submissions and delegate to the REPL pipeline."""

        try:
            while True:
                message = await self._pending.get()
                is_command = message.startswith("/")
                try:
                    if is_command:
                        await asyncio.to_thread(self._run_command, message)
                    else:
                        new_messages = await asyncio.to_thread(self._run_query, message)
                        if new_messages:
                            self._render_responses(new_messages)
                except Exception as exc:  # pragma: no cover - defensive guard
                    if is_command:
                        self.app.conversation.add_error(str(exc))
                    else:
                        self.app.notify_processing_error(str(exc))
                finally:
                    if not is_command:
                        self.app.notify_processing_complete()
                    self._pending.task_done()
        except asyncio.CancelledError:  # pragma: no cover - task shutdown
            return

    def _run_query(self, message: str) -> list[ChatMessage]:
        """Execute a user query via the REPL and return new session messages."""
        import traceback

        try:
            config = self.config_manager.get_config()
            self.config = config
            model_info = config.get_model_info()
        except Exception as exc:  # pragma: no cover - defensive guard
            self.app.notify_processing_error(
                f"Send failed: unable to validate active model ({exc})."
            )
            return []

        if model_info is None:
            self.app.notify_processing_error(
                "Send failed: configured Normal model is missing. Run /models to choose a valid model."
            )
            return []

        session = self.session_manager.get_current_session()
        previous_count = len(session.messages) if session else 0

        try:
            # Create UI callback for real-time tool display
            conversation_widget = None
            try:
                # Use the same query method the app uses to get the conversation widget
                from swecli.ui_textual.chat_app import ConversationLog
                conversation_widget = self.app.query_one("#conversation", ConversationLog)
            except Exception:
                # Fallback to direct attribute access
                if hasattr(self.app, 'conversation') and self.app.conversation is not None:
                    conversation_widget = self.app.conversation

            if conversation_widget is not None:
                from swecli.ui_textual.ui_callback import TextualUICallback
                ui_callback = TextualUICallback(conversation_widget, self.app)
            else:
                # Create a mock callback for when app is not mounted (e.g., during testing)
                class MockCallback:
                    def on_thinking_start(self): pass
                    def on_thinking_complete(self): pass
                    def on_tool_call(self, tool_name, tool_args): pass
                    def on_tool_result(self, tool_name, tool_args, result): pass
                ui_callback = MockCallback()

            # Temporarily disable console bridge to prevent duplicate rendering
            # All relevant messages are already in session.messages
            console = self.repl.console
            original_print = console.print
            original_log = getattr(console, "log", None)

            # Restore original print/log functions (bypass bridge)
            console.print = self._original_console_print
            if original_log and self._original_console_log:
                console.log = self._original_console_log

            try:
                # Process query with UI callback for real-time display
                if hasattr(self.repl, '_process_query_with_callback'):
                    self.repl._process_query_with_callback(message, ui_callback)
                else:
                    # Fallback to normal processing if callback method doesn't exist
                    self.repl._process_query(message)
            finally:
                # Restore bridge
                console.print = original_print
                if original_log:
                    console.log = original_log

            session = self.session_manager.get_current_session()
            if not session:
                return []

            new_messages = session.messages[previous_count:]
            return new_messages
        except Exception as e:
            error_msg = f"[ERROR] Query processing failed: {str(e)}\n{traceback.format_exc()}"
            self._enqueue_console_text(error_msg)
            return []

    def _run_command(self, command: str) -> None:
        """Execute a slash command and capture console output."""

        # Special handling for /mcp view command - use Textual modal instead of prompt_toolkit
        if command.strip().startswith("/mcp view "):
            self._handle_mcp_view_command(command)
            return

        with self.repl.console.capture() as capture:
            self.repl._handle_command(command)
        output = capture.get()
        if output.strip():
            self._enqueue_console_text(output)
        self._refresh_ui_config()

    def _handle_mcp_view_command(self, command: str) -> None:
        """Handle /mcp view command with Textual-native modal.

        Args:
            command: The full command (e.g., "/mcp view server_name")
        """
        from io import StringIO
        from rich.console import Console as RichConsole

        # Extract server name
        parts = command.split()
        if len(parts) < 3:
            # Render error with Rich to get ANSI codes
            string_io = StringIO()
            temp_console = RichConsole(file=string_io, force_terminal=True)
            temp_console.print("[red]Error: Server name required for /mcp view[/red]")
            self._enqueue_console_text(string_io.getvalue())
            return

        server_name = parts[2]

        # Get server details from MCP manager
        servers = self.repl.mcp_manager.list_servers()
        if server_name not in servers:
            # Render error with Rich to get ANSI codes
            string_io = StringIO()
            temp_console = RichConsole(file=string_io, force_terminal=True)
            temp_console.print(f"[red]Error: Server '{server_name}' not found in configuration[/red]")
            self._enqueue_console_text(string_io.getvalue())
            return

        server_config = servers[server_name]
        is_connected = self.repl.mcp_manager.is_connected(server_name)
        tools = self.repl.mcp_manager.get_server_tools(server_name) if is_connected else []

        # Build elegant panel content for the conversation log
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich import box

        # Create main info table
        info_table = Table(show_header=False, box=None, padding=(0, 1))
        info_table.add_column("Property", style="cyan", no_wrap=True)
        info_table.add_column("Value")

        # Status with color
        status_text = Text()
        if is_connected:
            status_text.append("Connected", style="bold green")
        else:
            status_text.append("Disconnected", style="dim")
        info_table.add_row("Status", status_text)

        # Command
        cmd_text = f"{server_config.command} {' '.join(server_config.args)}" if server_config.args else server_config.command
        info_table.add_row("Command", cmd_text)

        # Enabled/Auto-start
        enabled_text = Text("Yes", style="green") if server_config.enabled else Text("No", style="red")
        info_table.add_row("Enabled", enabled_text)

        auto_start_text = Text("Yes", style="green") if server_config.auto_start else Text("No", style="dim")
        info_table.add_row("Auto-start", auto_start_text)

        # Environment variables
        if server_config.env:
            env_str = "\n".join(f"{k}={v}" for k, v in server_config.env.items())
            info_table.add_row("Environment", env_str)

        # Tools count
        if is_connected:
            info_table.add_row("Tools", f"{len(tools)} available")

        # Create tools table if connected
        tools_content = None
        if is_connected and tools:
            tools_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
            tools_table.add_column("Tool Name", style="cyan")
            tools_table.add_column("Description", style="white")

            for tool in tools[:10]:  # Show first 10 tools
                tool_name = tool.get('name', 'unknown')
                tool_desc = tool.get('description', '')
                # Truncate long descriptions
                if len(tool_desc) > 60:
                    tool_desc = tool_desc[:57] + "..."
                tools_table.add_row(tool_name, tool_desc)

            if len(tools) > 10:
                tools_table.add_row(f"... and {len(tools) - 10} more", "", style="dim")

            tools_content = tools_table

        # Create main panel
        title = f"MCP Server: {server_name}"
        main_panel = Panel(
            info_table,
            title=title,
            title_align="left",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(1, 2)
        )

        # Render to conversation log
        self._enqueue_console_text("\n")  # Add spacing

        # Reuse the temp console from earlier
        string_io = StringIO()
        temp_console = RichConsole(file=string_io, force_terminal=True, width=100)
        temp_console.print(main_panel)

        if tools_content:
            temp_console.print("\n")
            tools_panel = Panel(
                tools_content,
                title="Available Tools",
                title_align="left",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            temp_console.print(tools_panel)

        # Show actions hint
        temp_console.print("\n[dim]Available actions:[/dim]")
        if is_connected:
            temp_console.print("  [cyan]/mcp disconnect " + server_name + "[/cyan] - Disconnect from server")
            temp_console.print("  [cyan]/mcp tools " + server_name + "[/cyan] - List all tools")
        else:
            temp_console.print("  [cyan]/mcp connect " + server_name + "[/cyan] - Connect to server")

        if server_config.enabled:
            temp_console.print("  [cyan]/mcp disable " + server_name + "[/cyan] - Disable auto-start")
        else:
            temp_console.print("  [cyan]/mcp enable " + server_name + "[/cyan] - Enable auto-start")

        output = string_io.getvalue()
        self._enqueue_console_text(output)

    def _cycle_mode(self) -> str:
        """Toggle between NORMAL and PLAN modes and return the active mode."""

        current = self.repl.mode_manager.current_mode
        from swecli.core.management import OperationMode

        new_mode = (
            OperationMode.PLAN
            if current == OperationMode.NORMAL
            else OperationMode.NORMAL
        )

        self.repl.mode_manager.set_mode(new_mode)
        if new_mode == OperationMode.PLAN:
            self.repl.agent = self.repl.planning_agent
        else:
            self.repl.agent = self.repl.normal_agent

        return new_mode.value

    def _render_responses(self, messages: list[ChatMessage]) -> None:
        """Render new session messages inside the Textual conversation log."""

        buffer_started = False
        assistant_text_rendered = False

        for msg in messages:
            if msg.role == Role.ASSISTANT:
                if hasattr(self.app, "_stop_local_spinner"):
                    self.app._stop_local_spinner()

                if hasattr(self.app, "start_console_buffer"):
                    self.app.start_console_buffer()
                    buffer_started = True

                content = msg.content.strip()
                if hasattr(self.app, "_normalize_paragraph"):
                    normalized = self.app._normalize_paragraph(content)
                    if normalized:
                        self.app._pending_assistant_normalized = normalized
                        self._last_assistant_message_normalized = normalized
                else:
                    self._last_assistant_message_normalized = content if content else None

                # Only render assistant messages that DON'T have tool calls
                # Messages with tool calls were already displayed in real-time by callbacks
                has_tool_calls = getattr(msg, "tool_calls", None) and len(msg.tool_calls) > 0

                if content and not has_tool_calls:
                    self.app.conversation.add_assistant_message(msg.content)
                    if hasattr(self.app, "record_assistant_message"):
                        self.app.record_assistant_message(msg.content)
                    if hasattr(self.app, "_last_rendered_assistant"):
                        self.app._last_rendered_assistant = content
                    self._last_assistant_message = content
                    self._suppress_console_duplicate = True
                    assistant_text_rendered = True

                # Skip rendering messages with tool calls - already shown in real-time
            elif msg.role == Role.SYSTEM:
                self.app.conversation.add_system_message(msg.content)
            # Skip USER messages - they're already displayed by the UI when user types them

        if buffer_started and hasattr(self.app, "stop_console_buffer"):
            self.app.stop_console_buffer()

    def _render_console_output(self, text: str) -> None:
        """Render console output captured from REPL commands/processings."""

        normalized = self._normalize_console_text(text)
        renderables = list(self._ansi_decoder.decode(normalized))
        if not renderables:
            return
        for renderable in renderables:
            if isinstance(renderable, Text):
                plain = renderable.plain.strip()
                if not plain:
                    continue
                if self._is_spinner_text(plain) or self._is_spinner_tip(plain):
                    continue
                normalized_plain = plain.strip()
                if hasattr(self.app, "_normalize_paragraph"):
                    normalized_plain = self.app._normalize_paragraph(plain)
                pending = getattr(self.app, "_pending_assistant_normalized", None)
                targets = [value for value in (pending, self._last_assistant_message_normalized) if value]
                if self._suppress_console_duplicate and normalized_plain and targets:
                    if any(normalized_plain == target for target in targets):
                        continue
                if plain == self._last_console_line:
                    continue
                self._last_console_line = plain
            else:
                self._last_console_line = None

            if hasattr(self.app, "render_console_output"):
                self.app.render_console_output(renderable)
            else:
                self.app.conversation.write(renderable)
        if not isinstance(renderables[-1], Text):
            self._last_console_line = None
        if self._suppress_console_duplicate:
            self._suppress_console_duplicate = False

        if hasattr(self.app, "stop_console_buffer"):
            self.app.stop_console_buffer()

    @staticmethod
    def _normalize_console_text(text: str) -> str:
        """Collapse carriage-return spinner updates into a single line."""

        if "\r" not in text:
            return text

        lines = text.split("\n")
        for index, line in enumerate(lines):
            if "\r" in line:
                lines[index] = line.split("\r")[-1]
        return "\n".join(lines)

    @staticmethod
    def _clean_tool_summary(summary: str) -> str:
        """Normalize tool summary text for assistant follow-up."""

        cleaned = summary.strip()
        if not cleaned:
            return ""

        if cleaned.lower().startswith("found") and ":" in cleaned:
            cleaned = cleaned.split(":", 1)[1].strip()

        cleaned = cleaned.strip(". ")
        if cleaned:
            return cleaned
        return summary.strip()

    @staticmethod
    def _is_spinner_text(plain: str) -> bool:
        """Return True if the console line appears to be a spinner update."""

        if not plain:
            return False

        first = plain[0]
        # Braille spinner characters live in the Unicode Braille block.
        if 0x2800 <= ord(first) <= 0x28FF:
            return True

        return False

    @staticmethod
    def _is_spinner_tip(plain: str) -> bool:
        """Return True if line looks like a spinner tip."""

        if not plain:
            return False

        normalized = plain.replace("⎿", "").strip().lower()
        return normalized.startswith("tip:")

    def run(self) -> None:
        """Launch the Textual application and background consumer."""

        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_app())
        finally:
            self.repl._cleanup()
            with contextlib.suppress(RuntimeError):
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            asyncio.set_event_loop(None)
            self._loop.close()

    async def _run_app(self) -> None:
        """Run Textual app alongside background processing tasks."""

        self._message_task = asyncio.create_task(self._process_messages())
        self._console_task = asyncio.create_task(self._drain_console_queue())
        try:
            await self.app.run_async()
        finally:
            tasks = [task for task in (self._message_task, self._console_task) if task]
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def _install_console_bridge(self) -> None:
        """Mirror console prints/logs into the Textual conversation."""

        console = self.repl.console
        self._original_console_print = getattr(console, "print")
        self._original_console_log = getattr(console, "log", None)

        def bridge_print(*args, **kwargs):
            with console.capture() as capture:
                self._original_console_print(*args, **kwargs)
            text = capture.get()
            if text.strip():
                self._enqueue_console_text(text)

        console.print = bridge_print  # type: ignore[assignment]

        if self._original_console_log is not None:
            def bridge_log(*args, **kwargs):
                with console.capture() as capture:
                    self._original_console_log(*args, **kwargs)
                text = capture.get()
                if text.strip():
                    self._enqueue_console_text(text)

            console.log = bridge_log  # type: ignore[assignment]

    def _enqueue_console_text(self, text: str) -> None:
        if not text:
            return

        if hasattr(self.app, "_normalize_paragraph"):
            normalized = self.app._normalize_paragraph(text)
            last_assistant = getattr(self.app, "_last_assistant_normalized", None)
            if normalized and last_assistant and normalized == last_assistant:
                return

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is self._loop:
            self._console_queue.put_nowait(text)
        elif self._loop.is_running():
            self._loop.call_soon_threadsafe(self._console_queue.put_nowait, text)
        else:
            self._console_queue.put_nowait(text)

    async def _drain_console_queue(self) -> None:
        try:
            while True:
                text = await self._console_queue.get()
                self._render_console_output(text)
                self._console_queue.task_done()
        except asyncio.CancelledError:  # pragma: no cover - task shutdown
            return


def launch_textual_cli(message=None, **kwargs) -> None:
    """Public helper for launching the Textual UI from external callers.

    Args:
        message: Optional message to process automatically
        **kwargs: Additional arguments passed to TextualRunner
    """

    runner = TextualRunner(**kwargs)

    # If a message is provided, enqueue it for processing
    if message:
        runner.enqueue_message(message)

    runner.run()


if __name__ == "__main__":
    launch_textual_cli()
