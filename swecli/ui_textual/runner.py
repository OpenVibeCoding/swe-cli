"""Entry point helper for launching the Textual chat UI alongside core SWE-CLI services."""

from __future__ import annotations

import asyncio
import contextlib
import os
from pathlib import Path
from typing import Any, Callable, Optional

from rich.ansi import AnsiDecoder
from rich.text import Text

from swecli.core.management import ConfigManager, OperationMode, SessionManager
from swecli.models.message import ChatMessage, Role
from swecli.repl.repl import REPL
from swecli.ui_textual.chat_app import create_chat_app
from swecli.ui_textual.constants import TOOL_ERROR_SENTINEL
from swecli.ui_textual.controllers.mcp_command_controller import MCPCommandController
from swecli.ui_textual.managers.approval_manager import ChatApprovalManager
from swecli.ui_textual.managers.console_output_manager import ConsoleOutputManager
from swecli.ui_textual.managers.session_history_manager import SessionHistoryManager
from swecli.ui_textual.renderers.response_renderer import ResponseRenderer
from swecli.ui_textual.utils import build_tool_call_text


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
        auto_connect_mcp: bool = False,
    ) -> None:
        self.working_dir = Path(working_dir or Path.cwd()).resolve()
        self._initial_messages: list[ChatMessage] = []
        self._history_restored = False

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
            self._auto_connect_mcp = auto_connect_mcp and hasattr(self.repl, "mcp_manager")
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
            self._auto_connect_mcp = auto_connect_mcp and hasattr(self.repl, "mcp_manager")

        self._initial_messages = self._snapshot_session_history()

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
            "on_interrupt": self._handle_interrupt,
        }
        if self._auto_connect_mcp:
            create_kwargs["on_ready"] = self._start_mcp_connect_thread
        # Don't show MCP notification - user can manually connect with /mcp connect
        create_kwargs["on_ready"] = self._wrap_on_ready_callback(create_kwargs.get("on_ready"))

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
        self._loop = asyncio.new_event_loop()
        self._message_task: asyncio.Task[None] | None = None
        self._console_task: asyncio.Task[None] | None = None
        self._connect_inflight = False

        # Initialize managers and controllers for modular architecture
        self._response_renderer = ResponseRenderer(self.app)
        self._console_output_manager = ConsoleOutputManager(self.app, self._console_queue, self._loop)
        self._session_history_manager = SessionHistoryManager(
            self.app,
            self.session_manager,
            self._response_renderer.render_stored_tool_calls
        )
        self._mcp_controller = MCPCommandController(self.app, self.repl)

        # Set up console bridge through manager
        self._console_output_manager.install_console_bridge(self.repl.console)

        # Set initial messages for history hydration
        self._session_history_manager.set_initial_messages(self._initial_messages)

        # Legacy variables for compatibility - delegate to managers
        self._last_console_line: str | None = None
        self._last_assistant_message: str | None = None
        self._suppress_console_duplicate = False
        self._last_assistant_message_normalized: str | None = None

    @property
    def _original_console_print(self):
        """Access original console print - delegated to ConsoleOutputManager."""
        return self._console_output_manager._original_console_print

    @property
    def _original_console_log(self):
        """Access original console log - delegated to ConsoleOutputManager."""
        return self._console_output_manager._original_console_log

    def _snapshot_session_history(self) -> list[ChatMessage]:
        """Capture session history - delegated to SessionHistoryManager if available."""
        # During init, manager may not exist yet, so do it directly
        if not hasattr(self, '_session_history_manager'):
            manager = getattr(self, "session_manager", None)
            if manager is None:
                return []
            session = manager.get_current_session()
            if session is None or not session.messages:
                return []
            return [message.model_copy(deep=True) for message in session.messages]
        return self._session_history_manager.snapshot_session_history()

    def _wrap_on_ready_callback(
        self,
        downstream: Optional[Callable[[], None]],
    ) -> Callable[[], None]:
        """Wrap on_ready callback - delegated to SessionHistoryManager if available."""
        # During init, manager may not exist yet, so do it directly
        if not hasattr(self, '_session_history_manager'):
            def _callback() -> None:
                self._hydrate_conversation_history()
                if downstream:
                    downstream()
            return _callback
        return self._session_history_manager.wrap_on_ready_callback(downstream)

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

    def _hydrate_conversation_history(self) -> None:
        """Hydrate conversation history - delegated to SessionHistoryManager."""
        self._session_history_manager.hydrate_conversation_history()
        self._history_restored = True

    def _render_stored_tool_calls(self, conversation, tool_calls: list[Any]) -> None:
        """Replay historical tool calls - delegated to ResponseRenderer."""
        self._response_renderer.render_stored_tool_calls(conversation, tool_calls)

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

        stripped = command.strip()
        lowered = stripped.lower()

        # Background auto-connect trigger
        if lowered.startswith("/mcp autoconnect"):
            if self._connect_inflight:
                self._enqueue_console_text(
                    "[dim]MCP auto-connect already running...[/dim]"
                )
            else:
                self._enqueue_console_text(
                    "[cyan]Starting MCP auto-connect in the background...[/cyan]"
                )
                self._start_mcp_connect_thread(force=True)
            return

        # Special handling for /mcp view command - use Textual modal instead of prompt_toolkit
        if lowered.startswith("/mcp view "):
            self._handle_mcp_view_command(command)
            return

        # Special handling for /mcp connect command - async non-blocking
        if lowered.startswith("/mcp connect "):
            self._handle_mcp_connect_command(command)
            return

        with self.repl.console.capture() as capture:
            self.repl._handle_command(command)
        output = capture.get()
        if output.strip():
            self._enqueue_console_text(output)
        self._refresh_ui_config()

    def _handle_mcp_view_command(self, command: str) -> None:
        """Handle /mcp view command - delegated to MCPCommandController."""
        self._mcp_controller.handle_view(command)

    def _handle_mcp_connect_command(self, command: str) -> None:
        """Handle /mcp connect command - delegated to MCPCommandController."""
        self._mcp_controller.handle_connect(command)

    def _handle_interrupt(self) -> bool:
        """Handle interrupt request from UI (ESC key press).

        Returns:
            True if interrupt was requested, False if no task is running
        """
        if hasattr(self.repl, "query_processor") and self.repl.query_processor:
            return self.repl.query_processor.request_interrupt()
        return False

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
        """Render responses - delegated to ResponseRenderer."""
        self._response_renderer.render_responses(messages)
        # Sync state from renderer
        self._last_assistant_message = self._response_renderer._last_assistant_message
        self._last_assistant_message_normalized = self._response_renderer._last_assistant_message_normalized
        self._suppress_console_duplicate = self._response_renderer._suppress_console_duplicate

    def _render_console_output(self, text: str) -> None:
        """Render console output - delegated to ConsoleOutputManager."""
        self._console_output_manager.render_console_output(text)


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
            # Use alternate screen mode (inline=False) for clean TUI with no terminal noise
            # This ensures scrolling up shows a clean screen, not previous terminal output
            await self.app.run_async(inline=False)
        finally:
            tasks = [task for task in (self._message_task, self._console_task) if task]
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def _notify_manual_mcp_connect(self) -> None:
        """Inform users how to connect MCP servers - delegated to MCPCommandController."""
        self._mcp_controller.notify_manual_connect(self._enqueue_console_text)

    def _start_mcp_connect_thread(self, force: bool = False) -> None:
        """Queue MCP auto-connect - delegated to MCPCommandController."""
        self._mcp_controller.start_auto_connect_thread(force)

    def _launch_mcp_autoconnect(self) -> None:
        """Trigger MCP auto-connect - delegated to MCPCommandController."""
        self._mcp_controller._launch_auto_connect()

    def _enqueue_console_text(self, text: str) -> None:
        """Enqueue console text - delegated to ConsoleOutputManager."""
        self._console_output_manager.enqueue_console_text(text)

    async def _drain_console_queue(self) -> None:
        """Drain console queue - delegated to ConsoleOutputManager."""
        await self._console_output_manager.drain_console_queue()


def launch_textual_cli(message=None, **kwargs) -> None:
    """Public helper for launching the Textual UI from external callers.

    Args:
        message: Optional message to process automatically
        **kwargs: Additional arguments passed to TextualRunner
    """

    if "auto_connect_mcp" not in kwargs:
        auto_env = os.getenv("SWECLI_MCP_AUTOCONNECT", "").strip().lower()
        if auto_env in {"1", "true", "yes", "on"}:
            kwargs["auto_connect_mcp"] = True

    runner = TextualRunner(**kwargs)

    # If a message is provided, enqueue it for processing
    if message:
        runner.enqueue_message(message)

    runner.run()


if __name__ == "__main__":
    launch_textual_cli()
