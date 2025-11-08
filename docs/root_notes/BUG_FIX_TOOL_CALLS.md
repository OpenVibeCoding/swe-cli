# Bug Fix: Tool Calls Lost When Resuming Sessions

## Problem Description

After integrating the ACE-inspired playbook system, tool execution appeared to work (processes started/stopped, PIDs changed) but the formatted tool call boxes were not displaying. Instead, only verbose LLM text descriptions were shown.

## Root Cause

The issue was NOT caused by the playbook integration itself, but by an existing bug in `Session.to_api_messages()` that was exposed when resuming sessions.

### The Bug

In `swecli/models/session.py`, the `to_api_messages()` method was only copying message content:

```python
def to_api_messages(self) -> list[dict[str, str]]:
    """Convert to API-compatible message format."""
    return [{"role": msg.role.value, "content": msg.content} for msg in self.messages]
```

This meant when a session was loaded:
1. **Tool calls were lost** - Assistant messages with `tool_calls` didn't include them
2. **Tool results were lost** - Tool execution results stored in `ToolCall.result` were not converted back to API format

### Impact

When resuming a session:
- The LLM didn't know what tools had been called previously
- The LLM didn't have access to tool execution results
- This caused the LLM to behave differently, potentially describing actions instead of taking them
- The tool display formatting relied on tool_calls being in the correct format

## The Fix

Updated `to_api_messages()` to:
1. Include `tool_calls` array in assistant messages
2. Generate corresponding `role="tool"` messages with tool results

```python
def to_api_messages(self) -> list[dict[str, str]]:
    """Convert to API-compatible message format."""
    result = []
    for msg in self.messages:
        api_msg = {"role": msg.role.value, "content": msg.content}
        # Include tool_calls if present
        if msg.tool_calls:
            api_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.parameters)
                    }
                }
                for tc in msg.tool_calls
            ]
            # Add the assistant message with tool_calls
            result.append(api_msg)

            # Add tool result messages for each tool call
            for tc in msg.tool_calls:
                tool_content = tc.error if tc.error else (tc.result or "")
                if tc.error:
                    tool_content = f"Error: {tool_content}"
                result.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_content
                })
        else:
            result.append(api_msg)
    return result
```

### Message Flow Example

**Before (Bug):**
```
Session has 3 messages:
1. USER: "run app.py"
2. ASSISTANT: "I'll run the app." [tool_calls: run_command] [result: "PID 12345"]
3. USER: "check status"

Converted to 3 API messages:
1. {"role": "user", "content": "run app.py"}
2. {"role": "assistant", "content": "I'll run the app."}  ← tool_calls LOST!
3. {"role": "user", "content": "check status"}
```

**After (Fixed):**
```
Session has 3 messages:
1. USER: "run app.py"
2. ASSISTANT: "I'll run the app." [tool_calls: run_command] [result: "PID 12345"]
3. USER: "check status"

Converted to 4 API messages:
1. {"role": "user", "content": "run app.py"}
2. {"role": "assistant", "content": "I'll run the app.", "tool_calls": [...]}  ← PRESERVED!
3. {"role": "tool", "tool_call_id": "...", "content": "PID 12345"}  ← RECONSTRUCTED!
4. {"role": "user", "content": "check status"}
```

## Why This Matters

The LLM needs to see:
1. What tools were called (via `tool_calls` in assistant messages)
2. What those tools returned (via `role="tool"` messages)

Without this information, the LLM loses critical context about what has already been done, leading to:
- Repeating actions
- Describing actions instead of taking them
- Inconsistent behavior between fresh and resumed sessions

## Testing

Tested with a session containing tool calls:
- ✅ Tool calls are preserved in assistant messages
- ✅ Tool results are reconstructed as separate messages
- ✅ Tool errors are properly formatted with "Error: " prefix
- ✅ Message order is correct: ASSISTANT (with tool_calls) → TOOL (result) → next message

## Related Changes

This fix was discovered while integrating the ACE-inspired playbook system:
- `swecli/core/context_management/` - Playbook and reflection system
- `swecli/repl/chat/async_query_processor.py` - Playbook integration
- `swecli/models/session.py` - **This bug fix**

The playbook integration is working correctly and is not the cause of the tool display issue.

## Impact on Users

**Before:**
- Tool calls worked in fresh sessions
- Tool calls appeared broken when resuming sessions
- Inconsistent behavior confused users

**After:**
- Tool calls work correctly in both fresh and resumed sessions
- Full conversation context is preserved across session loads
- Consistent LLM behavior

---

**Status**: ✅ Fixed
**Date**: 2025-10-23
**Files Modified**: `swecli/models/session.py` (added json import, fixed to_api_messages())
