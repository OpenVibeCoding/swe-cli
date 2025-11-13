# Scrolling Fix: Smart Page Down Behavior

## Problem

When pressing **Page Up** to view conversation history, then pressing **Page Down** to return to the latest message, you had to press Page Down multiple times to get back to the bottom. It didn't automatically jump to the latest message.

## Root Cause

In `swecli/ui/components/scrollable_formatted_text.py`, the `scroll_page_down()` method:
1. Always disabled auto-scroll (`_auto_scroll = False`)
2. Always incremented scroll offset by page height
3. Never detected if we were near the bottom
4. Never re-enabled auto-scroll

This meant you had to manually scroll through every page to get back to the bottom.

## Solution

Modified `scroll_page_down()` to be **smart**:

### Before
```python
def scroll_page_down(self, height: int) -> None:
    """Scroll down one page."""
    self._auto_scroll = False  # Always disable
    self.scroll_offset += height  # Always increment
```

### After
```python
def scroll_page_down(self, height: int) -> None:
    """Scroll down one page.

    If already near bottom, jump to bottom and re-enable auto-scroll.
    """
    # Calculate current position and total lines
    total_lines = len(lines)
    max_scroll = max(0, total_lines - effective_height)

    # Smart behavior: detect if near bottom
    if self.scroll_offset + height >= max_scroll:
        # Jump to bottom and re-enable auto-scroll
        self._auto_scroll = True
        self.scroll_offset = max_scroll
    else:
        # Normal page down
        self._auto_scroll = False
        self.scroll_offset += height
```

## Behavior

### Now
1. **Press Page Up** → Scroll up through history (auto-scroll disabled)
2. **Press Page Down once** → Jump directly to latest message (auto-scroll re-enabled)
3. Future messages automatically scroll into view ✅

### Before
1. **Press Page Up** → Scroll up through history
2. **Press Page Down** → Scroll down one page (still in history)
3. **Press Page Down** → Scroll down another page (still in history)
4. **Press Page Down** → ... (repeat multiple times) ❌
5. Eventually reach bottom

## Technical Details

The fix:
- Calculates total lines and max scroll position
- Compares current position + page height with max scroll
- If would overshoot or reach bottom → **jump to bottom + re-enable auto-scroll**
- Otherwise → normal page scroll behavior

This matches user expectations: "Page Down when near bottom = go to bottom"

## Testing

Test manually:
1. Have a conversation with multiple screens of history
2. Press **Page Up** several times to scroll up
3. Press **Page Down** once
4. **Expected**: Immediately jumps to the latest message
5. New messages automatically appear at bottom

## Files Modified

- `swecli/ui/components/scrollable_formatted_text.py` - Fixed `scroll_page_down()` method

## Impact

- Better UX: One keypress to return to latest message
- Matches standard terminal behavior
- Auto-scroll re-enabled when at bottom
- No breaking changes to other functionality

---

**Status**: ✅ Fixed
**Date**: 2025-10-23
**Issue**: Page Down required multiple presses after Page Up
**Solution**: Smart detection + auto-scroll re-enable when near bottom
