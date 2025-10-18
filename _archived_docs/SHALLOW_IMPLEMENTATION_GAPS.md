# SWE-CLI Implementation Gap Analysis

**Date**: 2025-10-07
**Purpose**: Document all shallow features that need deepening for 5-10x productivity

---

## Executive Summary

Current SWE-CLI has **working features but delivers minimal value**. All features are shallow implementations that don't provide the autonomous, proactive experience needed for 5-10x productivity gains.

### Critical Issues:
- ❌ **Auto mode just skips approvals** - No autonomous iteration
- ❌ **Tool calls execute once** - No error recovery or retry logic
- ❌ **No codebase intelligence** - Can't understand project structure
- ❌ **No proactive behavior** - Never suggests next steps
- ❌ **No debugging assistance** - Just shows errors, doesn't fix
- ❌ **No git integration** - No semantic commits or PR creation
- ❌ **No planning system** - No /think or /ultrathink commands
- ❌ **Basic REPL only** - No keyboard shortcuts or smooth flow

---

## 1. Auto Mode (Phase 2) - CRITICALLY SHALLOW

### Current Implementation:
**File**: `swecli/core/mode_manager.py:68-74`
```python
# Auto mode
if self._current_mode == OperationMode.AUTO:
    # Dangerous operations always require approval
    if is_dangerous:
        return True

    # Allow autonomous execution
    return False
```

**What it does**: Just returns `False` for `is_approval_required()` - skips approval prompts

### Problems:
1. ❌ **No iteration** - Executes tool once, even if it fails
2. ❌ **No error checking** - Doesn't verify success
3. ❌ **No retry logic** - Failures just stop
4. ❌ **No test execution** - Doesn't run tests after changes
5. ❌ **No proactive fixing** - Won't fix its own mistakes
6. ❌ **No multi-step tasks** - Can't decompose complex requests

### Real Example (Current Behavior):
```bash
> /mode auto
> Create a REST API for user management

AI calls write_file("api.py", code_with_syntax_error)
✓ File created

[DONE] - But the code has a syntax error!
```

### What It SHOULD Do:
```bash
> /mode auto
> Create a REST API for user management

[Step 1/5] Creating models...
  ✓ Created user.py
  ✓ Running syntax check... passed

[Step 2/5] Creating controllers...
  ✓ Created api.py
  ⚠ Syntax error detected: missing import
  → Fixing... added 'from models import User'
  ✓ Syntax check... passed

[Step 3/5] Writing tests...
  ✓ Created test_api.py (12 tests)

[Step 4/5] Running tests...
  ⚠ 2 tests failed
  → Fixing test_create_user... fixed validation
  → Rerunning tests... 12/12 passing

[Step 5/5] Finalizing...
  ✓ Updated requirements.txt
  ✓ Generated API docs

Committed: "feat: add user management REST API"
Tests: 12 passing
Ready for review!
```

### Required Changes:
**File**: `swecli/repl/repl.py:144-256` (entire `_process_query` method)
- Add iteration loop (max 5 attempts)
- Check tool results for errors
- Auto-fix common errors (imports, syntax)
- Run tests if they exist
- Iterate until success or max attempts

**Estimated Complexity**: 🔴 HIGH (requires complete refactor of query processing)

---

## 2. Tool Execution - NO ERROR RECOVERY

### Current Implementation:
**File**: `swecli/repl/repl.py:176-204`
```python
# Execute each tool call
tool_results = []
for tool_call in tool_calls:
    function_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])

    # Execute tool via registry
    result = self.tool_registry.execute_tool(...)

    # Show tool result
    if result["success"]:
        self.console.print(f"✓ {result.get('output')}")
    else:
        self.console.print(f"✗ {result.get('error')}")
```

**What it does**: Executes tools, shows success/failure, then **stops**

### Problems:
1. ❌ **No error analysis** - Just shows error message
2. ❌ **No retry** - Single attempt only
3. ❌ **No context** - AI doesn't see what went wrong
4. ❌ **No suggestions** - User left to figure out fix
5. ❌ **No rollback** - Failed state remains

### Real Example (Current Behavior):
```bash
> Install pygame and run tetris.py

→ run_command(command="pip install pygame")
✗ Error: Command failed with exit code 1
  stderr: error: externally-managed-environment

[END] - User must manually debug
```

### What It SHOULD Do:
```bash
> Install pygame and run tetris.py

→ run_command(command="pip install pygame")
✗ Error: externally-managed-environment

Analyzing error...
Root cause: System Python is externally managed
Solution: Use virtual environment

Attempt 2/5:
→ run_command(command="python -m venv venv && source venv/bin/activate && pip install pygame")
✓ pygame installed

→ run_command(command="python tetris.py")
✓ Game running on port 5000

Success! Pygame installed in venv and tetris.py running.
```

### Required Changes:
- Add error analysis function
- Implement retry loop with intelligent fixes
- Add context awareness (virtualenv, permissions, etc.)
- Suggest alternatives when commands fail

**Estimated Complexity**: 🟡 MEDIUM (add retry logic to existing flow)

---

## 3. Codebase Intelligence - COMPLETELY MISSING

### Current Implementation:
**File**: `swecli/repl/repl.py:282-324`
- Only commands: `/read`, `/search`, `/tree`
- No `/init` command exists
- No codebase scanning
- No OPENCLI.md support
- No project understanding

### Problems:
1. ❌ **No architecture detection** - Can't identify FastAPI vs Django vs Flask
2. ❌ **No pattern recognition** - Won't follow existing code style
3. ❌ **No dependency awareness** - Doesn't know what's installed
4. ❌ **No git analysis** - Can't see project history
5. ❌ **No context files** - Manual OPENCLI.md only
6. ❌ **File-by-file only** - Can't reason across codebase

### Real Example (Current Behavior):
```bash
> Add authentication to the API

AI: I'll create auth.py with JWT authentication.

[Creates generic auth.py that doesn't match project]
[Uses different patterns than existing code]
[Doesn't know if project already has auth]
```

### What It SHOULD Do:
```bash
> /init

Scanning codebase... ━━━━━━━━━━━━━━━━ 127/127 files

Project Analysis:
├── Framework: FastAPI 0.109.0
├── Database: SQLAlchemy + PostgreSQL
├── Auth: Existing JWT in src/auth/jwt.py
├── Patterns: Repository pattern, dependency injection
├── Style: Black, mypy strict, 88 char lines
├── Tests: pytest (127 tests, 94% coverage)
└── Commands: make test, make run, make migrate

Generated: .swecli/OPENCLI.md (856 tokens)
Context loaded. Ready!

> Add role-based permissions to authentication

Analyzing existing auth system...
├── Found: src/auth/jwt.py (JWT tokens, 30min expiry)
├── Found: src/auth/middleware.py (route protection)
├── Found: src/models/user.py (User model)

Planning permission system...
1. Extend User model with role field
2. Add Permission model following repository pattern
3. Update JWT to include role claims
4. Add @require_role decorator matching existing style

Proceed? [y/n]
```

### Required Changes:
**New files needed**:
1. `swecli/tools/codebase_scanner.py` - AST parsing, framework detection
2. `swecli/tools/context_loader.py` - Hierarchical OPENCLI.md loading
3. `swecli/commands/init.py` - /init command handler

**New slash commands**:
- `/init` - Scan and analyze codebase
- `/context` - Show loaded context
- `/analyze <topic>` - Deep analysis across files

**Estimated Complexity**: 🔴 HIGH (new subsystem required)

---

## 4. Proactive Suggestions - COMPLETELY MISSING

### Current Implementation:
NONE - AI only responds when prompted

### Problems:
1. ❌ **No next step suggestions** - After file edit, what's next?
2. ❌ **No workflow guidance** - Should I run tests? Commit?
3. ❌ **No token warnings** - Session fills silently
4. ❌ **No error prevention** - Could warn before mistakes

### Real Example (Current Behavior):
```bash
> Create calculator.py

✓ Created calculator.py

[END] - No suggestions, user must decide next step
```

### What It SHOULD Do:
```bash
> Create calculator.py

✓ Created calculator.py (42 lines)

💡 Suggestions:
  1. Run tests? [y/n] (found test_calculator.py)
  2. Check linting? [y/n] (black + mypy)
  3. Commit? [y/n] (1 file changed)

Token usage: 4,821/100,000 (5%)

>
```

### Required Changes:
**File**: `swecli/repl/repl.py` - Add after tool execution
- After write/edit: suggest tests
- After test pass: suggest commit
- At 70% tokens: suggest /compact
- After error: suggest /mode auto

**New file**: `swecli/core/suggestion_engine.py`
```python
class SuggestionEngine:
    def suggest_next_steps(self, last_operation, context):
        # Analyze what was just done
        # Suggest contextual next actions
        # Show as interactive prompts
```

**Estimated Complexity**: 🟢 LOW (add to existing flow)

---

## 5. Autonomous Debugging - COMPLETELY MISSING

### Current Implementation:
**File**: `swecli/core/error_handler.py`
```python
def handle_error(self, error: Exception) -> None:
    """Display formatted error."""
    self.console.print(f"[red]Error:[/red] {str(error)}")
```

**What it does**: Just prints the error message

### Problems:
1. ❌ **No stack trace analysis** - Doesn't find root cause
2. ❌ **No fix suggestions** - User must figure it out
3. ❌ **No auto-fix** - Won't try to fix automatically
4. ❌ **No test integration** - Doesn't catch test failures
5. ❌ **No iterative fixing** - Single error shown, no retry

### Real Example (Current Behavior):
```bash
> Run the tests

→ run_command(command="pytest")
✗ Error: 3 tests failed

[Shows error message only - user must debug manually]
```

### What It SHOULD Do:
```bash
> Run the tests

→ run_command(command="pytest")
⚠ 3/15 tests failed

Analyzing failures...

[1/3] test_create_user
├── Error: AssertionError: Expected 201, got 400
├── Root cause: Missing 'name' field in request
├── Fix: Add name='Test User' to test payload
└── Applied fix... Rerunning... ✓ Passed

[2/3] test_update_user
├── Error: KeyError: 'email'
├── Root cause: Endpoint doesn't validate required fields
├── Fix: Add email validation in update_user()
└── Applied fix... Rerunning... ✓ Passed

[3/3] test_delete_user
├── Error: 404 Not Found
├── Root cause: User ID not found in database
├── Fix: Seed test database with user fixture
└── Applied fix... Rerunning... ✓ Passed

Final result: 15/15 tests passing
Committed: "fix: add test data validation and fixtures"
```

### Required Changes:
**New file**: `swecli/tools/debug_assistant.py`
```python
class DebugAssistant:
    def analyze_error(self, error_msg, stack_trace):
        # Parse stack trace
        # Identify root cause
        # Return fix suggestions

    def auto_fix_tests(self, test_failures):
        # For each failure
        # Propose fix
        # Apply and rerun
        # Iterate until pass
```

**File**: `swecli/core/error_handler.py` - Complete rewrite
- Add stack trace parsing
- Identify error patterns
- Suggest fixes proactively
- In Auto mode: apply fixes automatically

**Estimated Complexity**: 🔴 HIGH (requires AI-powered analysis)

---

## 6. Keyboard Shortcuts & REPL Flow - MISSING

### Current Implementation:
**File**: `swecli/repl/repl.py:74-76`
```python
self.prompt_session: PromptSession[str] = PromptSession(
    history=FileHistory(str(history_file))
)
```

**What it does**: Basic prompt with history, that's all

### Problems:
1. ❌ **No Ctrl+R** - Can't search history with preview
2. ❌ **No Ctrl+C handling** - Crashes instead of pausing
3. ❌ **No Ctrl+D** - EOF instead of smart exit
4. ❌ **No Tab completion** - Can't autocomplete commands
5. ❌ **Slow responses** - No connection pooling, ~2-3s lag
6. ❌ **No progress indicators** - Long operations appear frozen

### Real Example (Current Behavior):
```bash
[DEFAULT] > Create a complex API
[Waits 2.8 seconds with no feedback]
Assistant: I'll create a REST API for you...
[No way to pause, cancel, or see progress]
```

### What It SHOULD Do:
```bash
[DEFAULT] > Create a complex API
Thinking... ━━━━━━━━━━ 100% (0.4s)
Assistant: I'll create a REST API...

💡 Tip: Press Ctrl+R to search history, Ctrl+C to pause
[Can press Ctrl+C anytime to pause gracefully]

# Keyboard Shortcuts:
- Ctrl+R: Fuzzy history search with preview
- Ctrl+C: Pause (preserves state, can resume)
- Ctrl+D: Smart exit with session save
- Tab: Complete commands and file paths
- Up/Down: Navigate history with inline preview
```

### Required Changes:
**File**: `swecli/repl/repl.py:74-76`
```python
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter

# Add keyboard shortcuts
bindings = KeyBindings()

@bindings.add('c-r')  # Ctrl+R
def _(event):
    # Fuzzy search history with preview

@bindings.add('c-c')  # Ctrl+C
def _(event):
    # Pause execution gracefully
    
@bindings.add('c-d')  # Ctrl+D
def _(event):
    # Smart exit with save prompt

self.prompt_session: PromptSession[str] = PromptSession(
    history=FileHistory(str(history_file)),
    key_bindings=bindings,
    completer=command_completer,
)
```

**File**: `swecli/core/ai_client.py` - Add connection pooling
```python
import httpx

class AIClient:
    def __init__(self, config):
        # Persistent connection pool
        self.http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=5),
            timeout=30.0
        )
```

**Estimated Complexity**: 🟡 MEDIUM (prompt_toolkit integration)

---

## 7. Git Integration - COMPLETELY MISSING

### Current Implementation:
NONE - No git commands, no commit creation, no PR integration

### Problems:
1. ❌ **No semantic commits** - Can't create commits with good messages
2. ❌ **No PR creation** - Manual process after Auto mode
3. ❌ **No git analysis** - Can't see who wrote code or recent changes
4. ❌ **No auto-commit** - After tasks complete, must commit manually
5. ❌ **No branch management** - No feature branch creation

### Real Example (Current Behavior):
```bash
> /mode auto
> Add user authentication

[Auto mode creates auth.py, middleware.py, tests]

✓ All done!

[User must manually git add, commit, push, create PR]
```

### What It SHOULD Do:
```bash
> /mode auto
> Add user authentication

[Auto mode creates auth.py, middleware.py, tests]
[Runs tests - all passing]

Analyzing changes for commit...
├── 3 files added (auth.py, middleware.py, test_auth.py)
├── 1 file modified (requirements.txt)
└── 127 lines added, 12 deleted

Generated commit message:
```
feat: add JWT authentication with role-based access

- Implement JWT token generation and validation
- Add authentication middleware for protected routes
- Create User model with password hashing (bcrypt)
- Add comprehensive test coverage (23 tests)

Breaking changes: None
Migration required: Yes (see migrations/003_auth.sql)

Refs: #156
```

Commit? [y/n/edit] y

✓ Committed: 6f8a2c9
✓ Pushed to feature/user-authentication

Create PR? [y/n] y

Creating PR...
✓ PR #457 created: https://github.com/user/repo/pull/457

Title: feat: Add JWT authentication with role-based access
Reviewers: auto-assigned based on git history
Labels: enhancement, security

Ready for review!
```

### Required Changes:
**New file**: `swecli/tools/git_integration.py`
```python
import subprocess
from typing import Optional

class GitIntegration:
    def analyze_changes(self) -> dict:
        # git diff --stat
        # git status --porcelain
        # Return change summary
        
    def generate_semantic_commit(self, changes) -> str:
        # Analyze file changes
        # Use AI to generate conventional commit
        # Include breaking changes, refs
        
    def create_commit(self, message: str) -> str:
        # git add .
        # git commit -m message
        # Return commit hash
        
    def create_pull_request(self, title, body) -> str:
        # Use gh CLI
        # Auto-assign reviewers based on git blame
        # Add labels based on file types
```

**New slash commands**:
- `/commit` - Create semantic commit
- `/pr` - Create pull request with gh CLI
- `/blame <file>` - Show git blame
- `/history <file>` - Show recent changes

**Estimated Complexity**: 🟡 MEDIUM (subprocess + gh CLI)

---

## 8. Graduated Reasoning (/think) - COMPLETELY MISSING

### Current Implementation:
NONE - No planning commands exist

### Problems:
1. ❌ **No /think command** - Can't get quick plans
2. ❌ **No /think hard** - Can't get detailed analysis
3. ❌ **No /ultrathink** - Can't get comprehensive planning
4. ❌ **No plan execution** - Plans aren't executable
5. ❌ **No plan tracking** - Can't track plan progress

### Real Example (Current Behavior):
```bash
> Plan how to add user permissions

[AI gives ad-hoc response, no structured plan]
[No way to execute the plan automatically]
```

### What It SHOULD Do:
```bash
> /think Add user permissions system

Planning (10s)... ━━━━━━━━━━ 100%

Plan (5 steps, ~15min):
1. Create Permission model with role enum
2. Add user_id foreign key to Permission table
3. Create has_permission() utility function
4. Update protected routes to check permissions
5. Write tests for permission checks

Execute plan? [y/n/auto] auto

---

> /think hard Add user permissions system

Deep analysis (30s)... ━━━━━━━━━━ 100%

Analyzing approaches...

Option 1: Role-Based Access Control (RBAC)
  ✓ Pros: Simple, standard, widely understood
  ✗ Cons: Less flexible, potential role explosion
  
Option 2: Attribute-Based Access Control (ABAC)
  ✓ Pros: Very flexible, fine-grained control
  ✗ Cons: Complex implementation, harder to debug

Option 3: Hybrid (roles + custom permissions)
  ✓ Pros: Best of both, scalable, covers 80% with roles
  ✗ Cons: More code to maintain

Recommendation: Hybrid approach

Implementation (7 steps, ~25min):
1. Database: Permission table with role enum + custom field
2. Migration: Safe migration with rollback
3. Business logic: has_permission() with Redis caching
4. API: CRUD endpoints for permissions
5. Tests: Unit + integration (35 tests estimated)
6. Docs: API documentation updates
7. Deploy: Staging deployment and smoke tests

Risks:
- Migration might break existing auth (10% probability)
  Mitigation: Test on staging first, keep rollback script
- Cache invalidation bugs (30% probability)
  Mitigation: Add cache health checks, monitoring

Execute plan? [y/n/auto] 

---

> /ultrathink Add user permissions system

Comprehensive planning (60s)... ━━━━━━━━━━ 100%

Deep Analysis & Task Breakdown

Main Task: User Permissions System
├── Sub-task 1: Database Schema (2h)
│   ├── 1.1: Design Permission table schema
│   │   └── Fields: id, user_id, role, resource, action
│   ├── 1.2: Add indexes for query performance
│   │   └── Index on (user_id, role), (resource, action)
│   └── 1.3: Write migration with rollback
│       Dependencies: None
│       Risk: Migration failure on prod (10%)
│       Mitigation: Test on staging, prepare rollback
│
├── Sub-task 2: Business Logic (3h)
│   ├── 2.1: has_permission() function
│   │   └── Check: role + custom permissions
│   ├── 2.2: Permission cache layer (Redis)
│   │   └── TTL: 5 minutes, invalidate on change
│   └── 2.3: Permission decorators (@require_role, @require_permission)
│       Dependencies: 1.x complete
│       Risk: Cache invalidation bugs (30%)
│       Mitigation: Cache health checks, fallback to DB
│
├── Sub-task 3: API Endpoints (2h)
│   ├── 3.1: POST /permissions - Create permission
│   ├── 3.2: GET /permissions - List permissions
│   ├── 3.3: PUT /permissions/:id - Update permission
│   └── 3.4: DELETE /permissions/:id - Delete permission
│       Dependencies: 2.x complete
│       Risk: Breaking changes to existing routes (20%)
│       Mitigation: Version API endpoints (/v2/)
│
└── Sub-task 4: Testing & Deploy (3h)
    ├── 4.1: Unit tests (20 tests)
    ├── 4.2: Integration tests (15 tests)
    ├── 4.3: Load testing (1000 rps)
    └── 4.4: Deploy to staging + smoke tests
        Dependencies: 3.x complete
        Risk: Performance degradation (15%)
        Mitigation: Query optimization, caching

Timeline:
Day 1: Database schema + Business logic (5h)
Day 2: API endpoints + Testing (4h)
Day 3: Deploy + monitor (1h)

Total: ~10 hours over 3 days

Success Criteria:
- ✅ All tests passing (35+ tests)
- ✅ API response time <100ms (p95)
- ✅ Cache hit rate >80%
- ✅ Zero breaking changes to existing auth

Execute plan in Auto mode? [y/n] y

Switching to Auto mode...
[Executes entire plan autonomously with progress updates]
```

### Required Changes:
**New file**: `swecli/tools/planner.py`
```python
class PlanningEngine:
    def quick_plan(self, task: str) -> dict:
        # 10s planning
        # Return 5-step plan
        
    def detailed_plan(self, task: str) -> dict:
        # 30s planning with trade-offs
        # Compare options
        # Return recommended approach
        
    def comprehensive_plan(self, task: str) -> dict:
        # 60s deep planning
        # Task breakdown with dependencies
        # Risk analysis
        # Timeline estimation
        # Return executable plan
```

**New slash commands**:
- `/think <task>` - 10s quick plan (5 steps)
- `/think hard <task>` - 30s detailed plan (options + tradeoffs)
- `/ultrathink <task>` - 60s comprehensive plan (sub-tasks, dependencies, risks)

**Integration with Auto mode**:
- After planning, can execute plan directly
- Track progress through plan steps
- Report on completion vs estimation

**Estimated Complexity**: 🔴 HIGH (requires sophisticated AI prompting + execution tracking)

---

## 9. Session Management - SHALLOW

### Current Implementation:
**File**: `swecli/core/session_manager.py`
- Saves sessions as JSON
- Can resume sessions
- No compacting
- No auto-summarization

### Problems:
1. ❌ **No /compact command** - Sessions grow until hitting token limit
2. ❌ **No auto-compacting** - No warning at 70% tokens
3. ❌ **No intelligent summarization** - Can't preserve key decisions
4. ❌ **No session analytics** - Can't see session stats

### What It SHOULD Have:
```bash
> /compact

Analyzing session (45,821/100,000 tokens)...

Compacting conversation...
├── Preserved: 34 key decisions
├── Preserved: 12 code snippets
├── Preserved: Current task context
├── Removed: Redundant explanations (15K tokens)
└── Removed: Resolved error discussions (8K tokens)

Before: 45,821 tokens
After: 18,342 tokens (60% reduction)

Compacted! Continue working.
```

### Required Changes:
**New file**: `swecli/tools/session_compactor.py`
- AI-powered summarization
- Preserve code and decisions
- Remove redundant conversation

**New slash command**: `/compact`

**Estimated Complexity**: 🟡 MEDIUM (AI summarization)

---

## Priority Summary

### Critical (Must Have for 5-10x productivity):
1. 🔴 **Auto Mode Iteration** - Core value, enables autonomous work
2. 🔴 **Error Recovery & Retry** - Prevents failed operations
3. 🔴 **Codebase Intelligence** - Essential for context-aware work
4. 🔴 **Autonomous Debugging** - Massive time saver

### High (Significantly enhances workflow):
5. 🟡 **Proactive Suggestions** - Smooth workflow guidance
6. 🟡 **Git Integration** - Workflow completion
7. 🟡 **Graduated Reasoning** - Better planning
8. 🟡 **Keyboard Shortcuts** - User experience improvement

### Medium (Nice to have):
9. 🟢 **Session Compacting** - Prevents token limit issues

---

## Estimated Implementation Timeline

### Phase 1: Core Autonomous Features (3 weeks)
- Week 1: Auto mode iteration + error recovery
- Week 2: Codebase intelligence + /init
- Week 3: Autonomous debugging

### Phase 2: Workflow Enhancement (2 weeks)
- Week 1: Git integration + semantic commits
- Week 2: Graduated reasoning (/think system)

### Phase 3: UX Polish (1 week)
- Keyboard shortcuts + smooth REPL flow
- Proactive suggestions
- Session compacting

**Total**: 6 weeks to deep implementation

---

## Success Metrics

After deepening implementation, we should see:
- ✅ Feature creation: 15min → 3min (5x faster)
- ✅ Bug fixing: 30min → 5min (6x faster)
- ✅ Auto mode success rate: 80%+ for common tasks
- ✅ Test auto-fix success rate: 85%+
- ✅ Time to first token: <1s (vs current ~2.8s)
- ✅ User satisfaction: "Actually useful" vs "just works"

---

## Next Steps

1. ✅ **This document created** - Gap analysis complete
2. → **Get user approval** on priorities
3. → **Start with Phase 1** - Auto mode iteration (highest impact)
4. → **Iterate and test** - Each feature must deliver value
5. → **Measure impact** - Track time savings and success rates

**The goal**: Transform SWE-CLI from "features that work" to "features that deliver 5-10x productivity"
