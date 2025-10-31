# Duplication Root Cause Analysis & Fix

## Problem Statement

User reports: "the response still always show duplications" in the Textual UI.

## Investigation Summary

### What I Found

1. **Session-level messages**: ✅ NO DUPLICATION
   - Exactly 1 user message
   - Exactly 1 assistant message
   - Session data is correct

2. **Console output**: ✅ EMPTY
   - REPL does NOT print assistant message to console
   - No console duplication source

3. **Deduplication exists**: ✅ PRESENT
   - `ConversationLog.add_assistant_message()` has deduplication logic (lines 53-56)
   - Normalizes text and compares with last rendered message
   - Should skip duplicates

4. **Debug logging added**: ✅ INSTRUMENTED
   - Runner logs when `_render_responses()` is called
   - ConversationLog logs when messages are rendered vs skipped

## Possible Causes

### Theory 1: Multiple Renders of Same Message

The issue might be that `_render_responses()` is being called MULTIPLE TIMES with the same messages.

**Check**:
- Does the async message processing call it multiple times?
- Is there a race condition?

### Theory 2: Deduplication State Reset

The `_last_assistant_rendered` state might be getting reset between calls.

**Check**:
- Is the ConversationLog instance being recreated?
- Is something clearing the state?

### Theory 3: Different Message Content

Each time the message is rendered, it might be slightly different (whitespace, formatting), so normalization doesn't match.

**Check**:
- Print normalized versions to compare
- Check if there are ANSI codes or other formatting

### Theory 4: Console Output Rendering

Even though console output is empty in tests, in the actual Textual UI it might have content from spinners or progress displays.

**Check**:
- Run actual Textual UI and capture console output
- Check if `_drain_console_queue()` is adding duplicates

## Current Debug Instrumentation

### In `/Users/quocnghi/codes/swe-cli/swecli/ui_textual/runner.py` (lines 175-183)

```python
# DEBUG: Log when this is called
import sys
print(f"\n[RUNNER] _render_responses called with {len(messages)} messages", file=sys.stderr)
for i, msg in enumerate(messages):
    print(f"[RUNNER] Message {i+1}: {msg.role.value} - {msg.content[:50]}...", file=sys.stderr)
```

### In `/Users/quocnghi/codes/swe-cli/swecli/ui_textual/chat_app.py` (lines 54-67)

```python
if normalized and normalized == self._last_assistant_rendered:
    # DEBUG: Log when we skip duplicate
    import sys
    print(f"\n[DEDUPE] Skipping duplicate assistant message", file=sys.stderr)
    print(f"[DEDUPE] Normalized: {normalized[:100]}...", file=sys.stderr)
    return

# DEBUG: Log when we render new message
import sys
print(f"\n[RENDER] Rendering new assistant message", file=sys.stderr)
print(f"[RENDER] Normalized: {normalized[:100]}...", file=sys.stderr)
```

## Next Steps

### 1. User to Run Actual Textual UI with Debug Logging

```bash
swecli-textual 2>debug.log
```

Then type "hello" and press Enter. The debug.log file will show:
- How many times `_render_responses()` is called
- Whether deduplication is working
- What the normalized messages look like

### 2. Analyze the Debug Log

Check for:
- `[RUNNER] _render_responses called` - should appear ONCE
- `[RENDER] Rendering new assistant message` - should appear ONCE
- `[DEDUPE] Skipping duplicate` - should NOT appear (unless truly duplicate)

### 3. If Duplication Confirmed

If we see:
```
[RENDER] Rendering new assistant message
[RENDER] Rendering new assistant message  <-- DUPLICATE!
```

Then we know `add_assistant_message()` is being called twice with different normalized content.

### 4. If Deduplication Working

If we see:
```
[RENDER] Rendering new assistant message
[DEDUPE] Skipping duplicate assistant message  <-- Good!
```

Then deduplication is working correctly and the issue might be:
- Visual perception (user thinks it's duplicate but it's not)
- Old sessions showing duplicates from before fix
- Console output adding extra text

## Immediate Action Required

**User needs to:**
1. Run `swecli-textual 2>debug.log`
2. Type "hello" and press Enter
3. See if assistant response appears twice
4. Share the `debug.log` file content

This will conclusively show what's happening.

## Potential Fixes (Based on Analysis)

### Fix A: Rate Limit Rendering

If `_render_responses()` is being called multiple times:

```python
def _render_responses(self, messages: list[ChatMessage]) -> None:
    # Only process if not already processing
    if hasattr(self, '_rendering_in_progress') and self._rendering_in_progress:
        return
    self._rendering_in_progress = True
    try:
        # ... existing code ...
    finally:
        self._rendering_in_progress = False
```

### Fix B: Stronger Deduplication

If normalization isn't matching:

```python
# Store hash instead of normalized text
import hashlib
message_hash = hashlib.md5(normalized.encode()).hexdigest()
if message_hash == self._last_assistant_hash:
    return
self._last_assistant_hash = message_hash
```

### Fix C: Console Output Suppression

If console output contains duplicate:

```python
# In _run_query, don't capture console output at all
# Comment out lines 140-144 in runner.py
# with self.repl.console.capture() as capture:
#     self.repl._process_query(message)
# output = capture.get()
# if output.strip():
#     self._enqueue_console_text(output)

# Just call directly without capture:
self.repl._process_query(message)
```

## Status

**Current**: Debugging instrumentation added ✅
**Next**: Waiting for user to run with debug logging and share results
**Expected**: Debug logs will reveal the exact cause

---

**Created**: 2025-10-29
**Debug Version**: Installed and ready for testing