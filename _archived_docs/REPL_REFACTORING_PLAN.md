# REPL Refactoring Plan

## Overview
The `swecli/repl/` directory contains two massive files that need refactoring:
- **repl.py**: 1,686 lines - Core REPL logic with 50+ methods
- **repl_chat.py**: 1,419 lines - Chat interface wrapper with complex state management

**Total**: 3,105 lines of tightly coupled code

## Current Architecture Problems

### 1. **repl.py** Issues:
- **God Object**: Single REPL class doing everything (UI, commands, AI processing, MCP management)
- **100 thinking verbs** hardcoded (lines 52-156)
- **15+ command handlers** mixed with core logic
- **Tool management** scattered throughout
- **No clear separation** between UI, business logic, and infrastructure

### 2. **repl_chat.py** Issues:
- **REPLChatApplication**: 35+ methods handling chat UI, spinners, approval, context monitoring
- **ChatApprovalManager**: 200+ lines of approval logic
- **Mixed concerns**: UI rendering, text wrapping, markdown conversion, context monitoring
- **Complex state management**: Spinner threads, conversation buffers, token monitoring

## Refactoring Strategy

### Phase 1: Extract Command Handlers (repl.py)
**Goal**: Separate command handlers from core REPL logic

**New Structure**:
```
swecli/repl/
├── commands/
│   ├── __init__.py
│   ├── base.py              # CommandHandler ABC
│   ├── session_commands.py  # /clear, /sessions, /resume
│   ├── file_commands.py     # /tree, /read, /search
│   ├── mode_commands.py     # /mode, /undo
│   ├── mcp_commands.py      # /mcp subcommands
│   └── help_command.py      # /help
```

**Benefits**:
- Each command handler is independently testable
- Easy to add new commands
- Clear command interface

**Risk**: Low - Commands are mostly independent
**Test Strategy**: Unit test each command handler with mock dependencies

---

### Phase 2: Extract UI Components (repl.py)
**Goal**: Separate UI rendering from business logic

**New Structure**:
```
swecli/repl/
├── ui/
│   ├── __init__.py
│   ├── prompt_builder.py     # Prompt tokens, input frames
│   ├── toolbar.py            # Bottom toolbar with mode/context
│   ├── welcome_screen.py     # Welcome banner (uses shared ui/welcome.py)
│   ├── status_renderer.py    # Context overview, notifications
│   └── constants.py          # THINKING_VERBS and other constants
```

**Benefits**:
- UI logic separated from business logic
- Reusable components
- Easier to test rendering

**Risk**: Low - UI components are mostly isolated
**Test Strategy**: Snapshot testing for UI output

---

### Phase 3: Extract Query Processing (repl.py)
**Goal**: Separate AI query processing into dedicated module

**New Structure**:
```
swecli/repl/
├── query/
│   ├── __init__.py
│   ├── processor.py          # QueryProcessor class
│   ├── enhancer.py           # Query enhancement (file content injection)
│   ├── react_loop.py         # ReAct loop logic
│   └── monitoring.py         # Token tracking, iteration limits
```

**Benefits**:
- Core AI logic is isolated and testable
- ReAct loop can be optimized independently
- Query enhancement is pluggable

**Risk**: Medium - Complex interaction between components
**Test Strategy**: Integration tests for full query flow

---

### Phase 4: Refactor REPLChatApplication (repl_chat.py)
**Goal**: Break down the 1000+ line chat application class

**New Structure**:
```
swecli/repl/
├── chat/
│   ├── __init__.py
│   ├── application.py        # Main REPLChatApplication (simplified)
│   ├── spinner_manager.py    # Spinner animation and state
│   ├── context_monitor.py    # Token counting and context tracking
│   ├── message_renderer.py   # Markdown rendering, text wrapping
│   ├── key_bindings.py       # Chat-specific key bindings
│   └── session_runner.py     # Async session execution (already exists!)
```

**Benefits**:
- Each concern is isolated
- Spinner management is reusable
- Context monitoring is testable

**Risk**: High - Complex state synchronization
**Test Strategy**: Careful state management, integration tests

---

### Phase 5: Extract Approval Management (repl_chat.py)
**Goal**: Move ChatApprovalManager to shared location

**New Structure**:
```
swecli/core/
├── approval/
│   ├── __init__.py
│   ├── manager.py           # Base ApprovalManager (already exists)
│   ├── chat_approval.py     # ChatApprovalManager
│   └── rules.py             # ApprovalRulesManager (if exists)
```

**Benefits**:
- Approval logic is centralized
- Reusable across REPL modes
- Rules engine is accessible

**Risk**: Low - Approval logic is well-encapsulated
**Test Strategy**: Unit tests for approval flows

---

### Phase 6: Create REPL Core (Final Integration)
**Goal**: Slim down main REPL class to orchestration only

**New Structure**:
```
swecli/repl/
├── __init__.py
├── repl.py                   # Slim REPL class (~300 lines)
├── repl_chat.py             # Slim REPLChatApplication (~300 lines)
├── commands/                 # Phase 1
├── ui/                       # Phase 2
├── query/                    # Phase 3
└── chat/                     # Phase 4
```

**Final REPL Class Responsibilities**:
- Initialize dependencies
- Run main loop
- Delegate to command handlers
- Delegate to query processor
- Minimal state management

**Risk**: Low - Just wiring components together
**Test Strategy**: End-to-end tests

---

## Implementation Plan

### Step-by-Step Execution

#### **Week 1: Phase 1 - Command Handlers**

**Day 1-2: Setup + Session Commands**
```bash
# Create structure
mkdir -p swecli/repl/commands
touch swecli/repl/commands/{__init__.py,base.py,session_commands.py}

# Extract methods:
# - _clear_session() → SessionCommands.clear()
# - _list_sessions() → SessionCommands.list()
# - _resume_session() → SessionCommands.resume()
```

**Testing Strategy**:
```python
# Test each command independently
def test_clear_session_command():
    handler = SessionCommands(session_manager=mock_manager)
    result = handler.clear()
    assert result.success == True
```

**Day 3-4: File + Mode Commands**
- Extract file operation commands
- Extract mode switching commands
- Unit tests for each

**Day 5: MCP + Help Commands**
- Extract MCP subcommand handlers
- Extract help command
- Integration tests

**Verification**:
```bash
# After Phase 1, REPL should still work:
python -m swecli.repl
# Try: /help, /clear, /mode plan, /mcp list
```

---

#### **Week 2: Phase 2 - UI Components**

**Day 1-2: Prompt + Toolbar**
- Extract prompt building logic
- Extract toolbar rendering
- Visual regression tests

**Day 3-4: Welcome + Status**
- Extract welcome screen
- Extract status renderer
- Move THINKING_VERBS to constants

**Day 5: Integration**
- Wire UI components into REPL
- Verify visual consistency

**Verification**:
```bash
# UI should look identical:
python -m swecli.repl
# Visual check: welcome banner, toolbar, prompts
```

---

#### **Week 3: Phase 3 - Query Processing**

**Day 1-2: Processor + Enhancer**
- Extract QueryProcessor class
- Extract query enhancement logic
- Unit tests

**Day 3-4: ReAct Loop**
- Extract ReAct loop logic
- Refactor iteration tracking
- Integration tests with mock agent

**Day 5: Monitoring**
- Extract monitoring logic
- Token tracking tests
- Full query flow integration test

**Verification**:
```bash
# AI queries should work:
python -m swecli.repl
> "list all python files"
# Should execute successfully
```

---

#### **Week 4: Phase 4 - Chat Application**

**Day 1-2: Spinner + Context**
- Extract SpinnerManager
- Extract ContextMonitor
- Thread safety tests

**Day 3-4: Message Renderer + Key Bindings**
- Extract message rendering
- Extract key bindings
- Rendering tests

**Day 5: Integration**
- Refactor REPLChatApplication
- Wire new components
- Full chat flow tests

**Verification**:
```bash
# Chat mode should work:
python -m swecli.cli chat
# Test: typing, spinners, context display
```

---

#### **Week 5: Phase 5 - Approval Management**

**Day 1-3: Move ChatApprovalManager**
- Move to swecli/core/approval/
- Update imports
- Approval flow tests

**Day 4-5: Integration + Cleanup**
- Wire approval manager
- Remove duplicated code
- Final approval tests

**Verification**:
```bash
# Approval should work in NORMAL mode:
python -m swecli.repl
/mode normal
> "delete all files"  # Should prompt for approval
```

---

#### **Week 6: Phase 6 - Final Integration**

**Day 1-3: Slim Down Main Classes**
- Reduce REPL.py to ~300 lines
- Reduce REPLChatApplication to ~300 lines
- Documentation

**Day 4-5: End-to-End Testing**
- Full REPL flows
- Full chat flows
- Performance benchmarks

**Final Verification**:
```bash
# Run full test suite:
pytest swecli/repl/

# Manual testing:
python -m swecli.repl  # Try all commands
python -m swecli.cli chat  # Try full chat session
```

---

## Testing Strategy

### Unit Tests (Each Phase)
```python
# Example: Command handler test
def test_mode_command_switch():
    mode_manager = ModeManager()
    handler = ModeCommands(mode_manager=mode_manager, ...)

    result = handler.switch_mode("plan")

    assert result.success == True
    assert mode_manager.current_mode == OperationMode.PLAN
```

### Integration Tests (After Each Phase)
```python
# Example: REPL integration test
def test_repl_command_handling():
    repl = REPL(config_manager, session_manager)

    # Simulate user input
    repl._handle_command("/mode plan")

    assert repl.mode_manager.current_mode == OperationMode.PLAN
    assert repl.agent == repl.planning_agent
```

### Regression Tests (After Each Phase)
- Verify all existing commands still work
- Verify UI looks identical
- Verify AI queries execute correctly
- Performance benchmarks remain stable

---

## Risk Mitigation

### High-Risk Areas

#### 1. **State Synchronization in Chat App** (Phase 4)
**Risk**: Spinner threads + context monitoring + message buffers can desync
**Mitigation**:
- Use thread-safe data structures
- Add explicit state transition tests
- Monitor for race conditions

#### 2. **ReAct Loop Refactoring** (Phase 3)
**Risk**: Breaking AI query processing flow
**Mitigation**:
- Keep original code commented during migration
- Extensive integration tests
- A/B test query results before/after

#### 3. **Import Cycles**
**Risk**: Circular dependencies between modules
**Mitigation**:
- Use dependency injection
- Keep clear module hierarchy
- Regular import cycle checks

---

## Success Metrics

### Code Quality
- **Line count reduction**: From 3,105 to ~600 (REPL) + ~300 (Chat) + ~1,500 (modules) = ~2,400 lines
- **Average method length**: From ~30 lines to ~15 lines
- **Cyclomatic complexity**: Reduce from ~10 to ~5 per function
- **Test coverage**: 80%+ for all new modules

### Maintainability
- **New command**: 10 minutes (vs. 1 hour before)
- **Fix bug**: 20 minutes (vs. 2 hours before)
- **Add feature**: 1 hour (vs. 1 day before)

### Performance
- **Startup time**: No regression (< 5% slower)
- **Query latency**: No regression (< 5% slower)
- **Memory usage**: 10% reduction (fewer duplicated objects)

---

## Rollback Plan

### Per-Phase Rollback
Each phase is isolated - if a phase fails:

1. **Revert commits** from that phase
2. **Keep previous phases** (they're independent)
3. **Fix issues** and retry

### Emergency Rollback
If everything breaks:

```bash
# Revert to pre-refactoring state
git reset --hard ccc2fa8a8a55373deaa81e60818d756d5ff9857f

# Or use backup branch
git checkout pre-repl-refactor-backup
```

---

## File-by-File Breakdown

### Files to Create (29 new files)

#### Commands (7 files)
1. `swecli/repl/commands/__init__.py`
2. `swecli/repl/commands/base.py`
3. `swecli/repl/commands/session_commands.py`
4. `swecli/repl/commands/file_commands.py`
5. `swecli/repl/commands/mode_commands.py`
6. `swecli/repl/commands/mcp_commands.py`
7. `swecli/repl/commands/help_command.py`

#### UI (6 files)
8. `swecli/repl/ui/__init__.py`
9. `swecli/repl/ui/prompt_builder.py`
10. `swecli/repl/ui/toolbar.py`
11. `swecli/repl/ui/welcome_screen.py`
12. `swecli/repl/ui/status_renderer.py`
13. `swecli/repl/ui/constants.py`

#### Query (5 files)
14. `swecli/repl/query/__init__.py`
15. `swecli/repl/query/processor.py`
16. `swecli/repl/query/enhancer.py`
17. `swecli/repl/query/react_loop.py`
18. `swecli/repl/query/monitoring.py`

#### Chat (6 files)
19. `swecli/repl/chat/__init__.py`
20. `swecli/repl/chat/application.py`
21. `swecli/repl/chat/spinner_manager.py`
22. `swecli/repl/chat/context_monitor.py`
23. `swecli/repl/chat/message_renderer.py`
24. `swecli/repl/chat/key_bindings.py`
25. `swecli/repl/chat/session_runner.py` (already exists!)

#### Approval (2 files)
26. `swecli/core/approval/__init__.py`
27. `swecli/core/approval/chat_approval.py`

#### Tests (2 files)
28. `tests/repl/test_commands.py`
29. `tests/repl/test_chat.py`

---

## Timeline Summary

| Phase | Duration | Risk | Priority |
|-------|----------|------|----------|
| Phase 1: Commands | 5 days | Low | High |
| Phase 2: UI | 5 days | Low | High |
| Phase 3: Query | 5 days | Medium | Critical |
| Phase 4: Chat | 5 days | High | High |
| Phase 5: Approval | 5 days | Low | Medium |
| Phase 6: Integration | 5 days | Low | High |

**Total**: 6 weeks (30 days)

---

## Next Steps

To begin Phase 1:

1. **Create backup branch**:
```bash
git checkout -b pre-repl-refactor-backup
git push origin pre-repl-refactor-backup
git checkout main
```

2. **Create feature branch**:
```bash
git checkout -b refactor/repl-phase1-commands
```

3. **Create command structure**:
```bash
mkdir -p swecli/repl/commands
touch swecli/repl/commands/{__init__.py,base.py,session_commands.py}
```

4. **Start extracting**: Begin with session commands (simplest)

---

## Questions Before Starting?

1. **Do you want to proceed with Phase 1 immediately?**
2. **Should I create the backup branch first?**
3. **Any specific concerns about the approach?**
4. **Do you want to see the detailed code for Phase 1 first?**

Let me know when you're ready to begin! 🚀
