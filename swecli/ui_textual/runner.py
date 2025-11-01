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
            connect = getattr(self.repl, "_connect_mcp_servers", None)
            if callable(connect):
                connect()

        # Get model display name from config
        model_display = f"{self.config.model_provider}/{self.config.model}"

        self.app = create_chat_app(on_message=self.enqueue_message, model=model_display)
        if hasattr(self.repl.approval_manager, "chat_app"):
            self.repl.approval_manager.chat_app = self.app

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

        session = self.session_manager.get_current_session()
        previous_count = len(session.messages) if session else 0

        try:
            # Create UI callback for real-time tool display
            # Try to get conversation widget using the same method as the app
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

        with self.repl.console.capture() as capture:
            self.repl._handle_command(command)
        output = capture.get()
        if output.strip():
            self._enqueue_console_text(output)

    def _render_responses(self, messages: list[ChatMessage]) -> None:
        """Render new session messages inside the Textual conversation log."""

        for msg in messages:
            if msg.role == Role.ASSISTANT:
                if hasattr(self.app, "_stop_local_spinner"):
                    self.app._stop_local_spinner()

                if hasattr(self.app, "start_console_buffer"):
                    self.app.start_console_buffer()

                content = msg.content.strip()
                if hasattr(self.app, "_normalize_paragraph"):
                    normalized = self.app._normalize_paragraph(content)
                    if normalized:
                        self.app._pending_assistant_normalized = normalized
                        self._last_assistant_message_normalized = normalized
                else:
                    self._last_assistant_message_normalized = content if content else None
                if content:
                    self.app.conversation.add_assistant_message(msg.content)
                    if hasattr(self.app, "record_assistant_message"):
                        self.app.record_assistant_message(msg.content)
                    if hasattr(self.app, "_last_rendered_assistant"):
                        self.app._last_rendered_assistant = content
                    self._last_assistant_message = content
                    self._suppress_console_duplicate = True

                if getattr(msg, "tool_calls", None):
                    for tool_call in msg.tool_calls:
                        args_display = ", ".join(
                            f"{key}={value!r}" for key, value in sorted(tool_call.parameters.items())
                        )
                        if hasattr(self.app.conversation, "add_tool_call"):
                            self.app.conversation.add_tool_call(tool_call.name, args_display)
                        result_payload: dict[str, str] = {}
                        if tool_call.result is not None:
                            result_payload = {"success": True, "output": str(tool_call.result)}
                        elif tool_call.error:
                            result_payload = {"success": False, "error": str(tool_call.error)}

                        if result_payload:
                            formatted = self.repl.output_formatter.format_tool_result(
                                tool_name=tool_call.name,
                                tool_args=tool_call.parameters,
                                result=result_payload,
                            )
                            if isinstance(formatted, str):
                                for line in formatted.splitlines():
                                    stripped = line.strip()
                                    if not stripped:
                                        continue
                                    if stripped.lstrip().startswith("⎿") and hasattr(self.app.conversation, "add_tool_result"):
                                        self.app.conversation.add_tool_result(stripped.lstrip("⎿ ").strip())
                                    elif hasattr(self.app.conversation, "add_assistant_message"):
                                        self.app.conversation.add_assistant_message(stripped)
                            else:
                                content_width = getattr(self.app, "_get_content_width", lambda: 80)()
                                from swecli.ui.utils.rich_to_text import rich_to_text_box

                                tool_text = rich_to_text_box(formatted, width=content_width)
                                for line in tool_text.splitlines():
                                    stripped = line.strip()
                                    if not stripped:
                                        continue
                                    if stripped.lstrip().startswith("⎿") and hasattr(self.app.conversation, "add_tool_result"):
                                        self.app.conversation.add_tool_result(stripped.lstrip("⎿ ").strip())
                                    elif hasattr(self.app.conversation, "add_assistant_message"):
                                        self.app.conversation.add_assistant_message(stripped)
            elif msg.role == Role.SYSTEM:
                self.app.conversation.add_system_message(msg.content)
            # Skip USER messages - they're already displayed by the UI when user types them
            # elif msg.role == Role.USER:
            #     self.app.conversation.add_user_message(msg.content)
            # else:
            #     self.app.conversation.add_system_message(msg.content)

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
