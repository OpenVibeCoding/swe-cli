# Bug Fix: AttributeError and @ Reference Handling

**Date**: 2025-10-11
**Status**: ✅ FIXED

## Problem 1: AttributeError

After refactoring `repl.py` in Phase 3, the chat interface (`repl_chat.py`) was broken with the following error:

```
❌ Error: 'REPL' object has no attribute '_enhance_query'
```

## Problem 2: @ File Reference Not Working

After the first fix, the `@` file reference syntax stopped working. When users typed "run @app.py", the agent would search for a literal file named "@app.py" instead of understanding it as "app.py".

## Root Cause

During Phase 3 refactoring:
1. The `_enhance_query()` method was moved from `REPL` class to the new `QueryProcessor` class
2. The `THINKING_VERBS` constant was also moved to `QueryProcessor`
3. However, `repl_chat.py` was still calling these as if they were direct attributes of the REPL object:
   - Line 592: `self.repl._enhance_query(query)`
   - Line 682: `self.repl.THINKING_VERBS`

## Solution

### Fix 1: Update repl_chat.py to access through query processor

**Line 592:**
```python
# Before (broken):
enhanced_query = self.repl._enhance_query(query)

# After (fixed):
enhanced_query = self.repl.query_processor.enhance_query(query)
```

**Line 682:**
```python
# Before (broken):
thinking_verb = random.choice(self.repl.THINKING_VERBS)

# After (fixed):
from swecli.repl.query_processor import QueryProcessor
thinking_verb = random.choice(QueryProcessor.THINKING_VERBS)
```

### Fix 2: Add @ reference handling to QueryProcessor

Updated `query_processor.py` to strip `@` prefix from file references before sending to agent:

```python
def enhance_query(self, query: str) -> str:
    """Enhance query with file contents if referenced."""
    import re

    # Handle @file references - strip @ prefix so agent understands
    # Pattern: @filename or @path/to/filename (with or without extension)
    # This makes "@app.py" become "app.py" in the query
    enhanced = re.sub(r'@([a-zA-Z0-9_./\-]+)', r'\1', query)

    # ... rest of enhancement logic ...
    return enhanced
```

**Examples:**
- `"run @app.py"` → `"run app.py"`
- `"check @src/main.ts and @config.json"` → `"check src/main.ts and config.json"`
- `"run app.py"` → `"run app.py"` (no change if no @)

## Verification

- ✅ Python syntax valid for all modified files
- ✅ QueryProcessor has `enhance_query()` method
- ✅ QueryProcessor has `THINKING_VERBS` constant
- ✅ REPL has `query_processor` attribute
- ✅ @ reference stripping works correctly (tested with regex)

## Files Modified

1. `swecli/repl/repl_chat.py` (2 lines changed)
   - Line 592: Fixed `_enhance_query` access
   - Line 682: Fixed `THINKING_VERBS` access

2. `swecli/repl/query_processor.py` (11 lines changed)
   - Added regex pattern to strip `@` prefix from file references
   - Updated docstring
   - Enhanced query preprocessing

## Impact

- ✅ Chat interface now works again
- ✅ @ file references work correctly (e.g., "run @app.py" → "run app.py")
- ✅ Autocomplete still provides @ suggestions for convenience
- ✅ Agent receives clean file paths without @ prefix

## Next Steps

The immediate errors are now fixed. However, `repl_chat.py` is still 1,420 lines and should be refactored similar to how `repl.py` was refactored. This will be addressed in the next phase of refactoring.
