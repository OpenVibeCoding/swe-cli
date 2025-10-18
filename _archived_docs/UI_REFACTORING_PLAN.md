# SWE-CLI UI Refactoring Plan

## Executive Summary

The `swecli/ui/` directory needs refactoring to improve modularity, remove unused code, eliminate duplication, and follow SOLID principles. Current issues include:
- Large files (chat_app.py: 1155 lines, formatters.py: 612 lines)
- Duplicate approval modal implementations (3 versions)
- Unused files (scrollable_formatted_text2.py, rules_editor_modal.py)
- Mixed responsibilities (formatting, state management, rendering all in one place)
- Poor separation of concerns

## Current State Analysis

### File Inventory & Usage

**Actively Used (11 files):**
- ✅ `chat_app.py` (1155 lines) - Main chat application
- ✅ `formatters.py` (612 lines) - Tool result formatting
- ✅ `autocomplete.py` (411 lines) - Slash commands & file mentions
- ✅ `welcome.py` (240 lines) - Welcome message display
- ✅ `task_progress.py` (193 lines) - Task progress indicators
- ✅ `animations.py` (187 lines) - Spinners and animations
- ✅ `status_line.py` (164 lines) - Status bar rendering
- ✅ `scrollable_formatted_text.py` (133 lines) - Scrollable text control
- ✅ `markdown_formatter.py` (105 lines) - Markdown conversion
- ✅ `rich_to_text.py` (106 lines) - Rich panel to text conversion
- ✅ `approval_message.py` (50 lines) - Approval message creation

**Potentially Unused/Deprecated (7 files):**
- ❌ `approval_modal.py` (209 lines) - Old approval modal
- ❌ `approval_modal_v2.py` (173 lines) - v2 approval modal
- ❌ `approval_modal_pt.py` (84 lines) - prompt_toolkit modal
- ❌ `rules_editor_modal.py` (411 lines) - Never imported
- ❌ `scrollable_formatted_text2.py` (61 lines) - Duplicate
- ❌ `conversation_buffer.py` (74 lines) - Embedded in chat_app
- ❌ `notifications.py` (74 lines) - Barely used

### Problems Identified

1. **Large Monolithic Files**
   - `chat_app.py`: 1155 lines mixing state, rendering, key bindings, approval logic
   - `formatters.py`: 612 lines with repetitive formatting methods

2. **Duplicate Code**
   - 3 approval modal implementations
   - 2 scrollable text controls
   - Conversation buffer defined twice

3. **Violation of SOLID Principles**
   - **Single Responsibility**: chat_app.py handles too many concerns
   - **Open/Closed**: Formatters require modification for new tool types
   - **Dependency Inversion**: Hard-coded dependencies everywhere

4. **Poor Modularity**
   - No clear separation between UI components, state, and business logic
   - Mixed concerns (rendering + event handling + state management)

## New Architecture Design

### Principle: Separation of Concerns

```
swecli/ui/
├── core/                    # Core UI abstractions (NEW)
│   ├── __init__.py
│   ├── component.py         # Base UI component class
│   ├── renderer.py          # Base renderer interface
│   └── event_handler.py     # Event handling base class
│
├── chat/                    # Chat UI components (RESTRUCTURED)
│   ├── __init__.py
│   ├── application.py       # Main app (< 300 lines)
│   ├── conversation.py      # Conversation display
│   ├── input_handler.py     # Input processing
│   ├── key_bindings.py      # Keyboard shortcuts
│   └── approval_handler.py  # Approval modal logic
│
├── formatters/              # Output formatting (SPLIT)
│   ├── __init__.py
│   ├── base.py              # Base formatter class
│   ├── file_formatter.py    # File operations (read/write/edit)
│   ├── command_formatter.py # Bash commands
│   ├── plan_formatter.py    # Plan mode results
│   └── syntax_highlighter.py # Code syntax highlighting
│
├── widgets/                 # Reusable widgets (NEW)
│   ├── __init__.py
│   ├── status_bar.py        # Status bar widget
│   ├── progress.py          # Progress indicators
│   ├── spinner.py           # Spinning animations
│   └── scrollable_text.py   # Scrollable text display
│
├── autocomplete/            # Autocomplete system (SPLIT)
│   ├── __init__.py
│   ├── completer.py         # Main completer
│   ├── slash_commands.py    # Slash command completion
│   └── file_mentions.py     # @ file mention completion
│
├── themes/                  # Styling and themes (NEW)
│   ├── __init__.py
│   ├── colors.py            # Color definitions
│   ├── icons.py             # Icon mappings
│   └── styles.py            # Rich styles
│
└── utils/                   # UI utilities (NEW)
    ├── __init__.py
    ├── markdown.py          # Markdown utilities
    ├── text_utils.py        # Text wrapping, truncation
    └── rich_utils.py        # Rich library helpers
```

### Key Design Patterns

1. **Component Pattern**: Each UI element is a self-contained component
2. **Strategy Pattern**: Formatters use strategy for different tool types
3. **Observer Pattern**: Event handlers notify listeners
4. **Facade Pattern**: Simplified interfaces for complex subsystems

### SOLID Compliance

**Single Responsibility Principle**
- Each class has ONE reason to change
- Separate files for formatting, rendering, event handling

**Open/Closed Principle**
- Base classes for formatters, components
- Extend through inheritance, not modification

**Liskov Substitution Principle**
- All formatters inherit from BaseFormatter
- All components inherit from Component

**Interface Segregation Principle**
- Small, focused interfaces (Renderer, EventHandler)
- Clients depend only on methods they use

**Dependency Inversion Principle**
- Depend on abstractions (BaseFormatter, Component)
- Inject dependencies through constructors

## Implementation Plan

### Phase 1: Core Infrastructure (Days 1-2)
Create foundation classes and interfaces

**Tasks:**
1. Create `swecli/ui/core/` directory
2. Implement `Component` base class
3. Implement `Renderer` interface
4. Implement `EventHandler` base class
5. Update `__init__.py` exports

**Files Created:**
- `swecli/ui/core/component.py` (~100 lines)
- `swecli/ui/core/renderer.py` (~50 lines)
- `swecli/ui/core/event_handler.py` (~80 lines)

### Phase 2: Split Formatters (Days 3-4)
Break down large formatters.py into specialized classes

**Tasks:**
1. Create `swecli/ui/formatters/` directory
2. Extract `BaseFormatter` abstract class
3. Split file operations → `file_formatter.py`
4. Split command operations → `command_formatter.py`
5. Split plan mode → `plan_formatter.py`
6. Extract syntax highlighting → `syntax_highlighter.py`
7. Update imports in consuming code

**Files Created:**
- `swecli/ui/formatters/base.py` (~80 lines)
- `swecli/ui/formatters/file_formatter.py` (~200 lines)
- `swecli/ui/formatters/command_formatter.py` (~100 lines)
- `swecli/ui/formatters/plan_formatter.py` (~80 lines)
- `swecli/ui/formatters/syntax_highlighter.py` (~60 lines)

**Files Removed:**
- `swecli/ui/formatters.py` (612 lines)

### Phase 3: Extract Widgets (Days 5-6)
Create reusable widget components

**Tasks:**
1. Create `swecli/ui/widgets/` directory
2. Extract status bar → `status_bar.py`
3. Extract progress indicators → `progress.py`
4. Extract spinners → `spinner.py`
5. Extract scrollable text → `scrollable_text.py`
6. Update imports

**Files Created:**
- `swecli/ui/widgets/status_bar.py` (~120 lines)
- `swecli/ui/widgets/progress.py` (~150 lines)
- `swecli/ui/widgets/spinner.py` (~100 lines)
- `swecli/ui/widgets/scrollable_text.py` (~150 lines)

**Files Modified:**
- `swecli/ui/animations.py` (shrink from 187 → ~50 lines)
- `swecli/ui/status_line.py` (shrink from 164 → ~80 lines)
- `swecli/ui/task_progress.py` (shrink from 193 → ~100 lines)

**Files Removed:**
- `swecli/ui/scrollable_formatted_text2.py` (61 lines - duplicate)

### Phase 4: Refactor Chat Application (Days 7-9)
Break down massive chat_app.py

**Tasks:**
1. Create `swecli/ui/chat/` directory
2. Extract conversation display → `conversation.py`
3. Extract input handling → `input_handler.py`
4. Extract key bindings → `key_bindings.py`
5. Extract approval logic → `approval_handler.py`
6. Refactor main app → `application.py`
7. Update imports in `swecli/repl/repl_chat.py`

**Files Created:**
- `swecli/ui/chat/application.py` (~250 lines)
- `swecli/ui/chat/conversation.py` (~180 lines)
- `swecli/ui/chat/input_handler.py` (~150 lines)
- `swecli/ui/chat/key_bindings.py` (~200 lines)
- `swecli/ui/chat/approval_handler.py` (~150 lines)

**Files Removed:**
- `swecli/ui/chat_app.py` (1155 lines)
- `swecli/ui/conversation_buffer.py` (74 lines - merged into conversation.py)

### Phase 5: Split Autocomplete (Days 10)
Modularize autocomplete system

**Tasks:**
1. Create `swecli/ui/autocomplete/` directory
2. Extract slash commands → `slash_commands.py`
3. Extract file mentions → `file_mentions.py`
4. Refactor main completer → `completer.py`
5. Update imports

**Files Created:**
- `swecli/ui/autocomplete/completer.py` (~150 lines)
- `swecli/ui/autocomplete/slash_commands.py` (~150 lines)
- `swecli/ui/autocomplete/file_mentions.py` (~110 lines)

**Files Removed:**
- `swecli/ui/autocomplete.py` (411 lines)

### Phase 6: Create Theme System (Day 11)
Centralize styling and themes

**Tasks:**
1. Create `swecli/ui/themes/` directory
2. Extract colors → `colors.py`
3. Extract icons → `icons.py`
4. Extract Rich styles → `styles.py`
5. Update all UI files to use theme system

**Files Created:**
- `swecli/ui/themes/colors.py` (~60 lines)
- `swecli/ui/themes/icons.py` (~40 lines)
- `swecli/ui/themes/styles.py` (~80 lines)

### Phase 7: Create Utilities (Day 12)
Extract common utility functions

**Tasks:**
1. Create `swecli/ui/utils/` directory
2. Move markdown utils → `markdown.py`
3. Create text utilities → `text_utils.py`
4. Create Rich helpers → `rich_utils.py`
5. Update imports

**Files Created:**
- `swecli/ui/utils/markdown.py` (~80 lines)
- `swecli/ui/utils/text_utils.py` (~60 lines)
- `swecli/ui/utils/rich_utils.py` (~70 lines)

**Files Modified:**
- `swecli/ui/markdown_formatter.py` (shrink from 105 → ~40 lines)
- `swecli/ui/rich_to_text.py` (shrink from 106 → ~50 lines)

### Phase 8: Cleanup & Remove Unused (Day 13)
Delete unused files and consolidate

**Tasks:**
1. Remove unused approval modals
2. Remove notification center (barely used)
3. Update all imports across codebase
4. Run tests to verify no breakage
5. Update documentation

**Files Removed:**
- `swecli/ui/approval_modal.py` (209 lines)
- `swecli/ui/approval_modal_v2.py` (173 lines)
- `swecli/ui/approval_modal_pt.py` (84 lines)
- `swecli/ui/rules_editor_modal.py` (411 lines)
- `swecli/ui/notifications.py` (74 lines)

### Phase 9: Update Main __init__.py (Day 14)
Clean public API

**Tasks:**
1. Update `swecli/ui/__init__.py` with new structure
2. Ensure backward compatibility where needed
3. Add deprecation warnings for old imports
4. Update documentation

## Migration Strategy

### Backward Compatibility

Create compatibility shims in main `__init__.py`:

```python
# swecli/ui/__init__.py
from swecli.ui.formatters.base import OutputFormatter  # New location
from swecli.ui.widgets.status_bar import StatusLine    # New location
from swecli.ui.chat.application import ChatApplication # New location

# Deprecated imports (with warnings)
import warnings

def __getattr__(name):
    if name == "OldClass":
        warnings.warn(
            f"{name} is deprecated, use NewClass instead",
            DeprecationWarning,
            stacklevel=2
        )
        from swecli.ui.new_module import NewClass
        return NewClass
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

### Testing Strategy

1. **Unit Tests**: Test each new component in isolation
2. **Integration Tests**: Test component interactions
3. **Regression Tests**: Ensure existing functionality works
4. **Manual Testing**: Test UI flows end-to-end

## Benefits

### Code Quality
- **76% reduction in duplicate code** (3 approval modals → 1)
- **Avg file size: ~150 lines** (down from ~240 lines)
- **Clear responsibility per file**

### Maintainability
- Easy to find code (logical directory structure)
- Easy to extend (base classes with inheritance)
- Easy to test (small, focused components)

### Developer Experience
- Clear imports: `from swecli.ui.chat import ChatApplication`
- Semantic organization: formatters/, widgets/, chat/
- Self-documenting structure

### Performance
- Faster imports (only load what you need)
- Better IDE autocomplete
- Reduced memory footprint

## Risks & Mitigation

### Risk 1: Breaking Changes
**Mitigation:**
- Implement backward compatibility shims
- Deprecation warnings instead of immediate removal
- Comprehensive regression testing

### Risk 2: Conflicts with REPL Refactoring
**Mitigation:**
- Don't touch `swecli/repl/` imports
- Only update UI-internal structure
- Coordinate with REPL refactoring team
- Use feature flags to enable gradually

### Risk 3: Timeline Overruns
**Mitigation:**
- Break into small, testable phases
- Each phase is independently deployable
- Can pause/resume between phases
- Prioritize high-value changes first

## Success Metrics

1. **Lines of Code**: Reduce from 4470 → ~3000 lines
2. **Avg File Size**: Reduce from ~240 → ~150 lines
3. **Test Coverage**: Increase from ? → 80%+
4. **Cyclomatic Complexity**: Reduce by 40%
5. **Import Time**: Reduce by 30%

## Timeline

- **Phase 1-2**: Days 1-4 (Foundation + Formatters)
- **Phase 3-4**: Days 5-9 (Widgets + Chat)
- **Phase 5-7**: Days 10-12 (Autocomplete + Themes + Utils)
- **Phase 8-9**: Days 13-14 (Cleanup + Documentation)

**Total: 14 working days (3 weeks with buffer)**

## Next Steps

1. ✅ Review and approve this plan
2. Create feature branch: `refactor/ui-modularization`
3. Start Phase 1: Core infrastructure
4. Regular sync with REPL refactoring team
5. Daily commits with tests
6. Weekly progress reviews

---

**Document Version**: 1.0
**Created**: 2025-01-10
**Author**: Claude Code Agent
**Status**: Ready for Implementation
