# REPL Files Strategy - Keep and Refactor

## Strategy: **KEEP** repl.py and repl_chat.py

These files are the **main orchestrators** and should remain as thin coordinator classes.

---

## What Each File Should Become

### repl.py - The CLI REPL Orchestrator (~850 lines target)

**Purpose**: Coordinate the text-based REPL experience

**What it KEEPS**:
```python
class REPL:
    """Interactive REPL for AI-powered coding assistance."""

    # Core responsibilities:
    def __init__(self):
        """Initialize all components and dependencies"""

    def start(self):
        """Main REPL loop - coordinate everything"""

    def _handle_command(self, command: str):
        """Route commands to handlers"""

    # Minimal delegation methods (thin wrappers):
    def _print_markdown_message(self, content: str):
        """Delegate to message_printer"""

    def _render_context_overview(self):
        """Delegate to context_display"""

    # Essential utilities:
    def _notify(self, message: str):
        """Notification helper"""

    def _build_key_bindings(self):
        """Key binding configuration"""
```

**What it DELEGATES**:
- ✅ Commands → `opencli/repl/commands/*`
- ✅ UI rendering → `opencli/repl/ui/*`
- 🔄 Query processing → `opencli/repl/query_processor.py` (to extract)
- 🔄 Lifecycle → `opencli/repl/lifecycle.py` (to extract)

**What gets DELETED**:
- ❌ ~500 lines of legacy command methods (never called)
- ❌ ~300 lines of MCP methods (fully delegated)
- ❌ ~60 lines of old UI methods (already extracted)

---

### repl_chat.py - The Terminal UI Chat Orchestrator (~520 lines target)

**Purpose**: Coordinate the full-screen terminal chat experience

**What it KEEPS**:
```python
class ChatREPL:
    """Full-screen terminal chat interface using prompt_toolkit."""

    # Core responsibilities:
    def __init__(self):
        """Initialize chat UI components and layout"""

    def run(self):
        """Main event loop for chat interface"""

    def _handle_user_message(self, text: str):
        """Process user input"""

    def add_assistant_message(self, content: str):
        """Add AI response to conversation"""
```

**What it DELEGATES**:
- 🔄 Text rendering → `opencli/repl/ui/text_renderer.py` (to extract)
- 🔄 Spinner → `opencli/repl/ui/spinner.py` or reuse existing
- 🔄 Status display → `opencli/repl/ui/status_display.py` (to extract)
- 🔄 Query processing → `opencli/repl/chat_query_processor.py` (to extract)
- 🔄 Key bindings → `opencli/repl/chat_key_bindings.py` (to extract)

**What gets DELETED**:
- ❌ Duplicate implementations (consolidate with repl.py where possible)

---

## Final Architecture

```
opencli/repl/
├── repl.py                      # CLI REPL orchestrator (~850 lines)
│   └── class REPL
│       ├── Delegates to commands/
│       ├── Delegates to ui/
│       ├── Uses QueryProcessor
│       └── Uses Lifecycle
│
├── repl_chat.py                 # Chat REPL orchestrator (~520 lines)
│   └── class ChatREPL
│       ├── Uses text_renderer
│       ├── Uses spinner
│       ├── Uses status_display
│       ├── Uses ChatQueryProcessor
│       └── Uses chat_key_bindings
│
├── query_processor.py           # NEW - Query processing logic
│   └── class QueryProcessor
│
├── lifecycle.py                 # NEW - Startup/shutdown logic
│   └── class REPLLifecycle
│
├── chat_query_processor.py      # NEW - Chat-specific query processing
│   └── class ChatQueryProcessor
│
├── commands/                    # ✅ DONE - Command handlers
│   ├── session_commands.py
│   ├── file_commands.py
│   ├── mode_commands.py
│   ├── mcp_commands.py
│   └── help_command.py
│
└── ui/                          # ✅ DONE + MORE TO ADD
    ├── text_utils.py            # ✅ Done
    ├── message_printer.py       # ✅ Done
    ├── input_frame.py           # ✅ Done
    ├── prompt_builder.py        # ✅ Done
    ├── toolbar.py               # ✅ Done
    ├── context_display.py       # ✅ Done
    ├── text_renderer.py         # 🔄 To extract from repl_chat
    ├── spinner.py               # 🔄 To extract (or reuse existing)
    ├── status_display.py        # 🔄 To extract from repl_chat
    └── chat_key_bindings.py     # 🔄 To extract from repl_chat
```

---

## Why Keep These Files?

### 1. **Entry Points**
These are the main classes that external code uses:
```python
from opencli.repl.repl import REPL
from opencli.repl.repl_chat import ChatREPL

# Used by main application
repl = REPL(config_manager, session_manager)
repl.start()
```

### 2. **Orchestration Role**
They coordinate multiple components:
- Initialize dependencies
- Wire components together
- Handle the main event loop
- Route to appropriate handlers

### 3. **Backward Compatibility**
Keeping these files maintains the public API:
```python
# Users expect this to work
from opencli.repl import REPL
```

---

## Comparison: Before vs After

### Before (Current)
```
repl.py (1,633 lines)
├── REPL loop logic
├── Command implementations  ← REDUNDANT (already in commands/)
├── MCP implementations      ← REDUNDANT (already in commands/)
├── UI implementations       ← REDUNDANT (already in ui/)
├── Query processing         ← SHOULD EXTRACT
└── Lifecycle                ← SHOULD EXTRACT
```

### After (Target)
```
repl.py (~850 lines)
├── REPL loop logic          ✅ Keep
├── Command routing          ✅ Keep (delegates)
├── Component initialization ✅ Keep
└── Thin wrapper methods     ✅ Keep (delegates)

+ query_processor.py          ✨ New
+ lifecycle.py                ✨ New
```

---

## Benefits of This Approach

### ✅ Pros
1. **Maintains Public API**: No breaking changes
2. **Clear Orchestration**: Each file has clear coordination role
3. **Single Responsibility**: Extracted modules have focused purposes
4. **Better Testing**: Can test components independently
5. **Easier Maintenance**: Smaller, focused files
6. **Backward Compatible**: Existing imports still work

### ❌ If We Deleted These Files
1. **Breaking Change**: Would break all imports
2. **Loss of Entry Point**: Where would main loop go?
3. **No Orchestrator**: Need something to wire components together
4. **Migration Pain**: All code using REPL would break

---

## Phase 3 Execution Plan

### Step 1: Delete Redundant Code (~860 lines)
```python
# In repl.py, DELETE:
- All _show_help, _clear_session, etc. (~500 lines)
- All _mcp_* methods (~300 lines)
- Old UI methods (~60 lines)

# Result: repl.py goes from 1,633 → ~773 lines
```

### Step 2: Extract Query Processing (~200 lines)
```python
# Move from repl.py to query_processor.py:
- _process_query() method
- _enhance_query() method

# In repl.py, replace with delegation:
def _process_query(self, query: str):
    self.query_processor.process_query(query)

# Result: repl.py ~773 → ~573 lines
            query_processor.py: ~200 lines
```

### Step 3: Extract Lifecycle (~50 lines)
```python
# Move from repl.py to lifecycle.py:
- _print_welcome()
- _connect_mcp_servers()
- _cleanup()

# Result: repl.py ~573 → ~523 lines
            lifecycle.py: ~50 lines
```

### Step 4-6: Similar for repl_chat.py
Extract chat components, reduce from 1,419 → ~520 lines

---

## Final Target Structure

```
repl.py           ~850 lines  (was 1,718) - 50% reduction ✅
repl_chat.py      ~520 lines  (was 1,419) - 63% reduction ✅

Total: ~1,370 lines (was 3,137) - 56% reduction overall!
```

**Plus 8-10 new focused modules with extracted logic**

---

## Conclusion

**repl.py** and **repl_chat.py** are **keepers**!

They will remain as thin, focused orchestrators that:
- Initialize components
- Coordinate the main loop
- Route to appropriate handlers
- Maintain the public API

The refactoring makes them **smaller, cleaner, and more maintainable** while preserving their essential orchestration role.
