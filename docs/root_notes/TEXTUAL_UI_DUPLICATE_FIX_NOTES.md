# Textual UI Debugging Progress (Assistant Message Duplication)

## Observed Issues
- Assistant replies were appearing twice in the conversation log after each spinner cycle.
- The duplicate line only appeared after the `[DEBUG] …` console output that the runner mirrors into the UI.
- Tool-call output was rendered as plain assistant text instead of Claude-style `⏺ … / ⎿ …` blocks.

## Root Causes Identified
1. **Console Echo Duplication**
   - The REPL prints a formatted copy of the assistant reply (with ANSI styles and wrapped lines) to stdout.
   - The Textual runner mirrors stdout into the conversation log, so the echo was rendered a second time.
   - Early suppression only compared raw strings; spacing, ANSI codes, or bullets caused mismatches.

2. **Tool Call Metadata Missing in Sync Path**
   - In the synchronous ReAct pipeline (`QueryProcessor.process_query`), assistant messages were saved without `tool_calls`.
   - The runner therefore had nothing to render for CLI-only sessions.

3. **Conversation Log Bullet Handling**
   - Each line of an assistant reply received a new `⏺` bullet, so wrapped lines looked like separate responses.

## Fixes Implemented
- **ConversationLog dedupe guard:** Track the last rendered assistant message (normalized) and skip re-rendering if the same text arrives again (`swecli/ui_textual/chat_app.py`).
- **Runner suppression:** Normalize console text (remove ANSI, collapse whitespace, strip `⏺`) and compare against both the current assistant reply and any “pending” reply before writing (`swecli/ui_textual/runner.py`).
- **Spinner-aware buffering:** Queue console output while the spinner runs and flush after the reply is written; prevents spinner cleanup from erasing tool output (`chat_app.py` & `runner.py`).
- **Tool-call rendering:** Persist tool call objects in both async and sync paths, then render them in Claude-style blocks via `ConversationLog.add_tool_call` / `add_tool_result` (`async_query_processor.py`, `query_processor.py`, `runner.py`).
- **Single bullet formatting:** Prefix only the first paragraph of each assistant reply with `⏺`, leave wrapped lines and Markdown untouched for readability (`chat_app.py`).

## Test Coverage
- `tests/test_textual_dedupe.py`: exercises normalization logic—including ANSI codes, wrapped lines, and buffered console output.
- `tests/test_tool_display.py`: asserts that tool calls surface as Claude-style `⏺ … / ⎿ …` entries.
- Run locally with:
  ```bash
  python -m pytest tests/test_textual_dedupe.py tests/test_tool_display.py
  ```

## Current Status (2025-10-29)
- Assistant duplication resolved in local runs (`python test_textual_runner.py` + manual prompts).
- Tool calls render in the expected Claude Code format.
- Spinner still animates inline and no longer interferes with final output.

## Suggested Next Steps
1. **Real-world validation:** Run the full CLI workflow (not just the `test_textual_runner.py` harness) to confirm tool calls appear during longer ReAct sessions.
2. **Styling polish:** Review the whitespace between assistant bullet paragraphs and long Markdown blocks.
3. **Log trace:** If duplicates reappear, capture the console buffer (`_queued_console_renderables`) and `_pending_assistant_normalized` values for comparison.
