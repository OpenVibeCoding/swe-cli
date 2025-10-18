# Phase 3: Advanced REPL Refactoring - IN PROGRESS

## Progress Summary

**Status**: Cleaning up redundant methods and extracting complex logic

**Starting Point**:
- repl.py: 1,718 lines
- repl_chat.py: 1,419 lines
- Total: 3,137 lines

## Phase 3 Goals

1. Delete redundant/legacy methods already handled by command handlers
2. Extract query processing logic into dedicated classes
3. Extract lifecycle management
4. Extract chat UI components
5. Reduce file sizes by 40-60%

---

## ✅ Completed Tasks

### Step 1: Delete Redundant UI Methods (46 lines removed)
- ✅ Removed `_bottom_toolbar_tokens()` - Now using Toolbar component
- ✅ Removed `_truncate_text()` - Now using text_utils
- ✅ Removed `_build_prompt_tokens()` - Now using PromptBuilder
- ✅ Removed `_print_input_frame_top()` - Now using InputFrame
- ✅ Removed `_print_input_frame_bottom()` - Now using InputFrame

**Result**: repl.py reduced from 1,718 to 1,672 lines

---

## 🔄 In Progress

### Step 2: Identify and Remove Legacy Command Methods

Many methods in repl.py are redundant because they duplicate functionality already in command handlers:

#### Legacy Methods to Remove (~500 lines):
- `_show_help()` - Lines 439-476 → HelpCommand handles this
- `_clear_session()` - Lines 478-487 → SessionCommands handles this
- `_list_sessions()` - Lines 489-505 → SessionCommands handles this
- `_resume_session()` - Lines 507-521 → SessionCommands handles this
- `_show_tree()` - Lines 523-530 → FileCommands handles this
- `_read_file()` - Lines 532-551 → FileCommands handles this
- `_search_files()` - Lines 553-574 → FileCommands handles this
- `_detect_language()` - Lines 576-611 → Move to FileCommands utility
- `_write_file_command()` - Lines 613-690 → Redundant with WriteTool
- `_edit_file_command()` - Lines 692-794 → Redundant with EditTool
- `_run_command()` - Lines 796-865 → Redundant with BashTool
- `_switch_mode()` - Lines 867-906 → ModeCommands handles this
- `_undo_operation()` - Lines 908-920 → ModeCommands handles this
- `_show_history()` - Lines 969-985 → ModeCommands handles this

#### MCP Methods to Remove (~300 lines):
- `_handle_mcp_command()` - Lines 987-1051 → MCPCommands handles this
- All `_mcp_*` methods - Lines 1053-1315 → MCPCommands handles everything

---

## 📋 Pending Tasks

### Step 3: Extract QueryProcessor (~200 lines)
Create `swecli/repl/query_processor.py`:
```python
class QueryProcessor:
    """Handles query processing with ReAct pattern."""
    def process_query(self, query: str) -> None
    def enhance_query(self, query: str) -> str
```

### Step 4: Extract Lifecycle Management (~50 lines)
Create `swecli/repl/lifecycle.py`:
```python
class REPLLifecycle:
    """Manages REPL startup and shutdown."""
    def print_welcome(self) -> None
    def connect_mcp_servers(self) -> None
    def cleanup(self) -> None
```

### Step 5: Extract Chat Components from repl_chat.py
- Text rendering (~100 lines)
- Spinner management (~80 lines)
- Status display (~100 lines)
- Query processor (~600 lines)
- Key bindings (~40 lines)

---

## Expected Final Results

After Phase 3 completion:
- **repl.py**: ~850 lines (50% reduction!)
- **repl_chat.py**: ~520 lines (63% reduction!)
- **New modules**: 8-10 focused, testable components
- **Maintainability**: Significantly improved
- **Test coverage**: Each component independently testable

---

**Phase 3 Started**: Now
**Current Progress**: 10% complete (redundant UI methods removed)
