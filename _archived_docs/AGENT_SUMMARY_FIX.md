# Agent Summary After Tool Calls - FIXED

## Problem

When users asked the agent to perform tasks (like "create a tetris game"), the agent would call tools and show the raw tool output, but NOT provide a natural language summary:

**Before (BAD)**:
```
[NORMAL] > help me to create a tetris game

Using tools...

write_file("tetris.html", "<!DOCTYPE html>\n<html>...")
```

**After (GOOD)**:
```
[NORMAL] > help me to create a tetris game

I've created a complete Tetris game in tetris.html! The game features:
- Classic Tetris gameplay with rotating pieces
- Score tracking and level progression
- Smooth controls using arrow keys
...
```

## Root Cause

The system prompt said:
> "After tools execute successfully, **you can** provide a brief summary"

The word "can" made it optional. Kimi K2 would often skip the summary and just return after tool calls.

## Solution

Updated `swecli/core/pydantic_agent.py` system prompt to make summaries **mandatory**:

```python
CRITICAL INSTRUCTIONS:
1. When you need to use tools, call them IMMEDIATELY without any explanatory text first
2. After ALL tool calls complete, you MUST provide a natural language summary
3. Your final message should explain what was accomplished in a conversational way
4. Never end your response with just tool calls - always add a summary message
```

## Testing

Tested with:
1. ✅ Simple file creation: Provides clear summary
2. ✅ Complex game creation (Pong): Provides detailed feature list and usage instructions
3. ✅ `/init` command: Works correctly with both tool calls and summary

## Files Modified

- **`swecli/core/pydantic_agent.py`** (lines 58-64)

## Impact

All agent interactions now:
- Show tool execution (what's happening)
- Provide natural language summary (what was accomplished)
- Give context and next steps to users
- Feel more conversational and helpful

## Next Steps

Reinstall the package for changes to take effect:
```bash
pip install -e . --quiet
```

Then test in REPL:
```bash
swecli
[NORMAL] > create a simple calculator in HTML
```

Should see both tool execution AND a nice summary!
