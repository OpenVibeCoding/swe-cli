# Phase 3: Further REPL Refactoring Analysis

## Current Status

- **repl.py**: 1,718 lines (still too long)
- **repl_chat.py**: 1,419 lines (still too long)
- **Total**: 3,137 lines

## Phase 3 Goals

Break down these large files into more manageable, focused modules by extracting:
1. Query processing logic
2. MCP command handlers (already extracted but still called from REPL)
3. Legacy file operation commands
4. Session management UI
5. Chat UI components

---

## repl.py Analysis (1,718 lines)

### Current Method Groups

#### ✅ Already Extracted (Phase 1 & 2)
- Command handlers → `swecli/repl/commands/`
- UI components → `swecli/repl/ui/`

#### 🔴 Still in REPL - Need Extraction

### 1. **Query Processing Engine** (~200 lines)
**Location**: Lines 527-729
**Methods**:
- `_process_query()` - Main ReAct loop (203 lines!)
- `_enhance_query()` - Query enhancement logic

**Recommendation**: Extract to `swecli/repl/query_processor.py`
```python
class QueryProcessor:
    """Handles query processing with ReAct pattern."""
    def process_query(self, query: str) -> None
    def enhance_query(self, query: str) -> str
```

### 2. **Legacy Command Methods** (~500 lines)
**Location**: Lines 804-1285
**Methods** (still in REPL but should be removed):
- `_show_help()` → Use HelpCommand
- `_clear_session()` → Use SessionCommands
- `_list_sessions()` → Use SessionCommands
- `_resume_session()` → Use SessionCommands
- `_show_tree()` → Use FileCommands
- `_read_file()` → Use FileCommands
- `_search_files()` → Use FileCommands
- `_detect_language()` → Move to FileCommands
- `_write_file_command()` → Remove (redundant with WriteTool)
- `_edit_file_command()` → Remove (redundant with EditTool)
- `_run_command()` → Remove (redundant with BashTool)
- `_switch_mode()` → Use ModeCommands
- `_undo_operation()` → Use ModeCommands
- `_init_codebase()` → Already delegated but method still exists

**Recommendation**: DELETE these methods entirely - they're already handled by command handlers

### 3. **MCP Command Handlers** (~300 lines)
**Location**: Lines 1352-1680
**Methods**:
- `_handle_mcp_command()` → Already in MCPCommands
- `_mcp_list_servers()` → Already in MCPCommands
- `_mcp_connect_server()` → Already in MCPCommands
- `_mcp_disconnect_server()` → Already in MCPCommands
- `_mcp_show_tools()` → Already in MCPCommands
- `_mcp_test_server()` → Already in MCPCommands
- `_mcp_debug()` → Already in MCPCommands
- `_mcp_status()` → Already in MCPCommands
- `_mcp_enable_server()` → Already in MCPCommands
- `_mcp_disable_server()` → Already in MCPCommands
- `_mcp_reload()` → Already in MCPCommands
- `_connect_mcp_servers()` → Startup logic, can extract

**Recommendation**: DELETE all `_mcp_*` methods - MCPCommands already handles everything

### 4. **Lifecycle Management** (~50 lines)
**Methods**:
- `_print_welcome()` - Lines 484-526
- `_connect_mcp_servers()` - Lines 1682-1702
- `_cleanup()` - Lines 1704-1718

**Recommendation**: Extract to `swecli/repl/lifecycle.py`
```python
class REPLLifecycle:
    """Manages REPL startup and shutdown."""
    def print_welcome(self) -> None
    def connect_mcp_servers(self) -> None
    def cleanup(self) -> None
```

### 5. **Old UI Methods** (~60 lines)
**Methods** (kept for backward compatibility but should delegate):
- `_bottom_toolbar_tokens()` - Lines 366-385 → Already have Toolbar
- `_truncate_text()` - Lines 412-416 → Already have text_utils
- `_build_prompt_tokens()` - Lines 418-423 → Already have PromptBuilder
- `_print_input_frame_top()` - Lines 425-429 → Already have InputFrame
- `_print_input_frame_bottom()` - Lines 431-435 → Already have InputFrame

**Recommendation**: DELETE these methods - UI components already handle everything

---

## repl_chat.py Analysis (1,419 lines)

### Method Groups

### 1. **Text Rendering** (~100 lines)
**Methods**:
- `_get_content_width()` - Line 236
- `_wrap_text()` - Lines 248-300
- `_render_markdown_message()` - Lines 302-317

**Recommendation**: Extract to `swecli/repl/ui/text_renderer.py`

### 2. **Spinner Management** (~80 lines)
**Methods**:
- `_start_spinner()` - Lines 319-340
- `_stop_spinner()` - Lines 342-362
- `_spinner_loop()` - Lines 364-397

**Recommendation**: Extract to `swecli/repl/ui/spinner.py` (or reuse existing Spinner)

### 3. **Status Display** (~100 lines)
**Methods**:
- `_get_status_text()` - Lines 119-234

**Recommendation**: Extract to `swecli/repl/ui/status_display.py`

### 4. **Query Processing** (~600 lines!)
**Methods**:
- `_process_query()` - Lines 561-1172 (611 LINES!)

**Recommendation**: Extract to `swecli/repl/chat_query_processor.py`

### 5. **Key Bindings** (~40 lines)
**Methods**:
- `_create_key_bindings()` - Lines 76-117

**Recommendation**: Extract to `swecli/repl/chat_key_bindings.py`

---

## Phase 3 Refactoring Plan

### Priority 1: DELETE Redundant Methods (Immediate ~860 line reduction)
1. Remove all legacy command methods from repl.py (~500 lines)
2. Remove all MCP command methods from repl.py (~300 lines)
3. Remove old UI methods from repl.py (~60 lines)

### Priority 2: Extract Query Processing (Biggest complexity reduction)
1. Extract `QueryProcessor` from repl.py (~200 lines)
2. Extract `ChatQueryProcessor` from repl_chat.py (~600 lines)

### Priority 3: Extract Chat UI Components
1. Extract text rendering components (~100 lines)
2. Extract spinner management (~80 lines)
3. Extract status display (~100 lines)
4. Extract key bindings (~40 lines)

### Priority 4: Extract Lifecycle Management
1. Extract REPL lifecycle methods (~50 lines)

## Expected Results

### After Phase 3:
- **repl.py**: ~850 lines (50% reduction!)
- **repl_chat.py**: ~520 lines (63% reduction!)
- **New files**: 8-10 focused modules
- **Total lines**: Similar, but much better organized

### Benefits:
- Each file has a clear, single responsibility
- Query processing logic is isolated and testable
- No code duplication (redundant methods removed)
- Easier to maintain and extend
- Better separation of concerns

---

## Implementation Order

1. **Step 1**: Delete redundant methods (safe, immediate cleanup)
2. **Step 2**: Extract QueryProcessor from repl.py
3. **Step 3**: Extract lifecycle management
4. **Step 4**: Extract ChatQueryProcessor from repl_chat.py
5. **Step 5**: Extract remaining chat UI components
6. **Step 6**: Test and validate

