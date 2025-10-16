# LLM Message Prefix Fix ✅

## Problem

The `⏺` symbol prefix for LLM responses was appearing on a separate line from the actual content:

```
⏺

Perfect! I can see there's already a complete ping pong game implementation
in `ping_pong.py`. Let me check if pygame is installed and then run the game
for you.
```

**Expected:**
```
⏺ Perfect! I can see there's already a complete ping pong game implementation
in `ping_pong.py`. Let me check if pygame is installed and then run the game
for you.
```

## Root Cause

The LLM API responses (`response.get("content")` and `llm_description`) may contain leading whitespace or newlines. When these were concatenated with the `⏺` prefix without stripping:

```python
self.add_assistant_message(f"⏺ {llm_description}")
```

If `llm_description` = `"\n\nPerfect! I can see..."`, the result would be:
```python
"⏺ \n\nPerfect! I can see..."
```

Which displays as:
```
⏺

Perfect! I can see...
```

## Solution

Strip whitespace from LLM content before adding the prefix.

### Fix 1: Main Response Display

**Location:** `opencli/repl/repl_chat.py:250`

**Before:**
```python
if llm_description:
    self.add_assistant_message(f"⏺ {llm_description}")
```

**After:**
```python
if llm_description:
    self.add_assistant_message(f"⏺ {llm_description.strip()}")
```

### Fix 2: Safety Limit Summary

**Location:** `opencli/repl/repl_chat.py:232`

**Before:**
```python
if response.get("content"):
    self.add_assistant_message(f"⏺ {response['content']}")
```

**After:**
```python
if response.get("content"):
    self.add_assistant_message(f"⏺ {response['content'].strip()}")
```

## Why `.strip()` Works

The `str.strip()` method removes:
- Leading whitespace (spaces, tabs)
- Leading newlines (`\n`)
- Trailing whitespace and newlines

This ensures the LLM content starts immediately after the `⏺` prefix.

### Example Transformations

| Original Content | After `.strip()` | With Prefix |
|-----------------|------------------|-------------|
| `"\n\nHello"` | `"Hello"` | `"⏺ Hello"` ✅ |
| `"  \nWorld"` | `"World"` | `"⏺ World"` ✅ |
| `"Test"` | `"Test"` | `"⏺ Test"` ✅ |
| `"\n  \nFoo\n"` | `"Foo"` | `"⏺ Foo"` ✅ |

## Impact

### Visual Display

**Before:**
```
⏺

Perfect! I can see there's already a complete ping pong game
implementation in `ping_pong.py`.

⏺

Great! I can see that there's already a complete ping pong game
implementation in the `ping_pong.py` file.
```

**After:**
```
⏺ Perfect! I can see there's already a complete ping pong game
implementation in `ping_pong.py`.

⏺ Great! I can see that there's already a complete ping pong game
implementation in the `ping_pong.py` file.
```

### Where This Applies

1. **Regular LLM responses** (line 250): During normal ReAct loop iterations
2. **Safety limit summaries** (line 232): When the iteration limit is reached
3. **All message display**: Both are passed to `add_assistant_message()` which handles wrapping

### Text Wrapping Compatibility

The fix works well with the existing text wrapping logic:

```python
def add_assistant_message(self, content: str) -> None:
    """Override to wrap text before adding (but not Rich panels)."""
    # ... detection logic ...
    if is_rich_panel:
        super().add_assistant_message(content)
    else:
        wrapped_content = self._wrap_text(content, width=76)
        super().add_assistant_message(wrapped_content)
```

After stripping, the content `"⏺ Perfect! I can see..."` is treated as plain text and properly wrapped at 76 characters while keeping the prefix on the first line.

## Testing

### Manual Verification

Run the chat REPL and observe LLM responses:

```bash
python test_repl_chat.py
```

**Expected:** All `⏺` symbols appear on the same line as the first word of the response.

### Scenarios Tested

1. ✅ LLM response with leading newlines
2. ✅ LLM response with leading spaces
3. ✅ LLM response with no leading whitespace (no regression)
4. ✅ Safety limit summary responses
5. ✅ Multi-line responses with proper wrapping

## Files Modified

### `opencli/repl/repl_chat.py`
- Line 232: Strip content in safety limit summary
- Line 250: Strip llm_description in main response

## Related Systems

### Consistent with Original REPL

The original REPL (`opencli/repl/repl.py`) doesn't use a prefix symbol, so this issue didn't exist there. However, this fix maintains the expected behavior where symbols and their associated text appear together.

### Message Session Storage

The stripped content is only used for display. The original API response (with whitespace) is preserved in the session history via:

```python
assistant_msg_dict = {
    "role": "assistant",
    "content": llm_description,  # Original content
}
if tool_calls:
    assistant_msg_dict["tool_calls"] = tool_calls
messages.append(assistant_msg_dict)
```

This ensures:
- **Display:** Clean, properly formatted with prefix
- **Session history:** Preserves exact API response
- **API context:** Full original content sent back to LLM

## Status

**Date:** 2025-10-08
**Status:** ✅ FIXED
**Breaking Changes:** None
**Quality:** Improved visual consistency

---

**The LLM response prefix now appears on the same line as the content, providing cleaner and more readable output.**
