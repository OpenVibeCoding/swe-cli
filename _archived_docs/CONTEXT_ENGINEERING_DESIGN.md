# Context Engineering Design for SWE-CLI

**Based on:** [Anthropic's Context Engineering Article](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

**Date:** 2025-10-07
**Status:** Design Phase

---

## 🎯 Core Principle

> **"Context is a finite resource with diminishing marginal returns."**
>
> **Goal:** Find the smallest possible set of high-signal tokens to maximize desired outcomes.

---

## 📋 Design Overview

### Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      SWE-CLI Context System                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Context State │  │  Token       │  │  Compaction      │   │
│  │  (Pydantic)    │◄─┤  Monitor     │◄─┤  Engine          │   │
│  │                │  │  (tiktoken)  │  │  (AI-driven)     │   │
│  └────────┬───────┘  └──────────────┘  └──────────────────┘   │
│           │                                                      │
│  ┌────────▼──────────────────────────────────────────────────┐ │
│  │              Conversation History                          │ │
│  │  • User prompts                                            │ │
│  │  • Agent responses                                         │ │
│  │  • Tool outputs (grep, read, bash)                        │ │
│  │  • Reasoning traces                                        │ │
│  └─────────────────────────────────────────────────────────┬──┘ │
│                                                              │    │
│  ┌────────────────────────────────────────────────────────┐ │    │
│  │            Persistent Context (OPENCLI.md)             │ │    │
│  │  • Codebase summary (generated via /init)             │ │    │
│  │  • Project structure                                   │ │    │
│  │  • Key files and patterns                             │ │    │
│  └────────────────────────────────────────────────────────┘ │    │
│                                                              │    │
│  ┌────────────────────────────────────────────────────────┐ │    │
│  │            Just-in-Time Retrieval                      │ │    │
│  │  • Proactive grep for patterns                        │ │    │
│  │  • Read files mentioned in prompts                    │ │    │
│  │  • Bash commands for context discovery               │ │    │
│  └────────────────────────────────────────────────────────┘ │    │
│                                                                  │
│                           ▼                                      │
│                  ┌──────────────────┐                           │
│                  │   LLM API Call   │                           │
│                  │  (256k context)  │                           │
│                  └──────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Implementation Strategy

### Phase 1: Context State Foundation

**File:** `swecli/core/context_engine.py`

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime
import tiktoken

class Message(BaseModel):
    """Single message in conversation history."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tokens: int = 0
    tool_calls: Optional[List[Dict]] = None
    tool_results: Optional[List[Dict]] = None

class CodebaseSummary(BaseModel):
    """Persistent codebase context (OPENCLI.md)."""
    summary: str
    project_structure: Dict[str, List[str]]  # folder -> [files]
    key_files: List[str]  # Important files to track
    patterns: Dict[str, str]  # Pattern name -> location
    last_updated: datetime
    tokens: int = 0

class TaskContext(BaseModel):
    """Just-in-time task-specific context."""
    task_description: str
    relevant_files: List[str] = []
    grep_results: List[Dict] = []
    bash_outputs: List[Dict] = []
    retrieved_at: datetime = Field(default_factory=datetime.now)
    tokens: int = 0

class ContextState(BaseModel):
    """Main context state for SWE-CLI."""

    # Conversation history
    messages: List[Message] = []

    # Persistent context
    codebase_summary: Optional[CodebaseSummary] = None

    # Just-in-time context
    current_task: Optional[TaskContext] = None

    # Token tracking
    total_tokens: int = 0
    context_limit: int = 256000  # 256k tokens
    compaction_threshold: float = 0.8  # Compact at 80%

    # Session metadata
    session_id: str
    working_dir: str
    started_at: datetime = Field(default_factory=datetime.now)
    last_compacted: Optional[datetime] = None
    compaction_count: int = 0

    def needs_compaction(self) -> bool:
        """Check if context needs compaction."""
        return self.total_tokens >= (self.context_limit * self.compaction_threshold)

    def get_available_tokens(self) -> int:
        """Get remaining available tokens."""
        return self.context_limit - self.total_tokens

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text using tiktoken."""
        encoding = tiktoken.encoding_for_model("gpt-4")
        return len(encoding.encode(text))
```

---

## 🔄 Context Flow: Turn-by-Turn

### Anthropic Principle: "Just-in-Time Context Loading"

```
User Input
    │
    ├─► 1. Parse user intent
    │      • What files are mentioned?
    │      • What patterns to grep?
    │      • What context is needed?
    │
    ├─► 2. Proactive Context Retrieval (Just-in-Time)
    │      • grep 'error' src/ → Add to TaskContext
    │      • read main.py → Add to TaskContext
    │      • bash ls -la → Add to TaskContext
    │
    ├─► 3. Build LLM Input
    │      • System prompt (tools, mode)
    │      • Codebase summary (OPENCLI.md)
    │      • Conversation history (compressed if needed)
    │      • Current task context (just-in-time)
    │      • User's new message
    │
    ├─► 4. Token Check
    │      • If < 80%: Proceed
    │      • If ≥ 80%: Compact first (see below)
    │
    ├─► 5. LLM Call with Streaming
    │      • Stream reasoning: "Thought: Grep for..."
    │      • Stream actions: "Action: Write main.py"
    │      • Execute tools as they're called
    │
    ├─► 6. Append to History
    │      • User message → messages[]
    │      • Assistant response → messages[]
    │      • Tool outputs → messages[]
    │
    └─► 7. Update Token Count
           • Recalculate total_tokens
           • Log to .swecli/logs/<session>.log
```

---

## 🗜️ Compaction Strategy

### Anthropic Principle: "Compaction maintains coherence beyond context limits"

**Trigger:** When `total_tokens ≥ 80% of 256k` (~204,800 tokens)

**Goal:** Reduce tokens by 60-80% while preserving:
- Key decisions and plans
- Bug fixes and feature implementations
- File paths and code patterns
- Current task state

### Compaction Process

```python
async def compact_context(context_state: ContextState) -> ContextState:
    """
    AI-driven compaction using Claude to summarize history.

    Strategy:
    1. Extract key information from messages
    2. Identify critical context to preserve
    3. Generate dense summary (60-80% reduction)
    4. Replace old messages with summary message
    5. Keep recent N messages untouched
    """

    # 1. Divide history into segments
    recent_messages = context_state.messages[-20:]  # Keep last 20 as-is
    to_compact = context_state.messages[:-20]  # Compact older messages

    # 2. Build compaction prompt
    compaction_prompt = f"""
You are a context compaction assistant. Your job is to summarize a conversation
history while preserving ALL critical information.

PRESERVE:
- Key decisions and rationale
- Bug fixes with file paths and solutions
- Feature implementations and design choices
- Important file paths, function names, code patterns
- Current project state and goals

REMOVE:
- Verbose explanations already acted upon
- Redundant tool outputs (keep references to results, not full output)
- Conversational pleasantries
- Repeated information

Original History ({len(to_compact)} messages, {sum(m.tokens for m in to_compact)} tokens):

{format_messages_for_compaction(to_compact)}

Generate a dense, structured summary that reduces tokens by 70% while preserving
all critical context. Use bullet points and clear sections.
"""

    # 3. Call LLM to generate summary
    summary_response = await llm.call(compaction_prompt)

    # 4. Create summary message
    summary_message = Message(
        role="system",
        content=f"""
=== CONVERSATION HISTORY SUMMARY ===
(Compacted {len(to_compact)} messages at {datetime.now()})

{summary_response}

=== END SUMMARY ===

Recent messages follow below (unmodified)...
""",
        timestamp=datetime.now(),
        tokens=context_state.estimate_tokens(summary_response)
    )

    # 5. Replace old messages with summary
    context_state.messages = [summary_message] + recent_messages
    context_state.last_compacted = datetime.now()
    context_state.compaction_count += 1

    # 6. Recalculate tokens
    context_state.total_tokens = sum(m.tokens for m in context_state.messages)
    context_state.total_tokens += context_state.codebase_summary.tokens if context_state.codebase_summary else 0

    return context_state
```

---

## 📝 Structured Note-Taking

### Anthropic Principle: "Persist memory outside context windows"

**File:** `.swecli/memory/session_notes.md`

Created automatically during conversation to track:
- Project goals and plans
- Key decisions made
- Files modified and why
- Current task progress
- Open issues and blockers

**Example Structure:**

```markdown
# Session Memory: 2025-10-07

## Project: test_swecli

### Current Goal
Implement user authentication feature with JWT tokens.

### Key Decisions
- Use FastAPI for API framework (decided 2025-10-07 14:30)
- Store tokens in Redis with 24h expiry
- Password hashing with bcrypt

### Files Modified
- `api/auth.py` (created) - JWT token generation
- `models/user.py` (updated) - Added password_hash field
- `requirements.txt` (updated) - Added PyJWT, redis

### Current Task
Writing integration tests for auth endpoints.

### Open Issues
- [ ] Need to configure Redis connection in production
- [ ] Decide on refresh token strategy

### Code Patterns Discovered
- Authentication middleware in `api/middleware/auth.py:15`
- User validation in `models/user.py:validate_user()`
```

This gets loaded at session start and updated after each significant action.

---

## 🔍 Just-in-Time Context Retrieval

### Anthropic Principle: "Progressive disclosure through autonomous exploration"

**Strategy:** Proactively retrieve context based on user intent, not loading everything upfront.

### Retrieval Triggers

```python
class ContextRetriever:
    """Proactively retrieve context based on user input."""

    async def retrieve_for_task(self, user_input: str, working_dir: str) -> TaskContext:
        """
        Analyze user input and retrieve relevant context.

        Examples:
        - "fix the login bug" → grep 'login' src/, read auth files
        - "add a new endpoint" → read api files, grep 'router'
        - "optimize the database query" → grep 'query' db/, read schema
        """

        task_context = TaskContext(task_description=user_input)

        # 1. Extract entities (files, patterns, keywords)
        entities = await self._extract_entities(user_input)

        # 2. Grep for relevant patterns
        for pattern in entities.patterns:
            results = await grep_tool(pattern, working_dir)
            task_context.grep_results.append({
                "pattern": pattern,
                "matches": results[:10],  # Limit to top 10
                "file_count": len(results)
            })

        # 3. Read mentioned files
        for file_path in entities.files:
            if os.path.exists(file_path):
                content = await read_tool(file_path)
                task_context.relevant_files.append(file_path)

        # 4. Run discovery commands if needed
        if entities.needs_file_listing:
            output = await bash_tool(f"find {working_dir} -name '*.py' -type f")
            task_context.bash_outputs.append({
                "command": "find",
                "output": output[:1000]  # Limit output
            })

        # 5. Estimate tokens
        task_context.tokens = self._estimate_context_tokens(task_context)

        return task_context

    async def _extract_entities(self, user_input: str) -> Dict:
        """
        Use lightweight LLM call to extract entities.

        Prompt: "Extract file paths, search patterns, and keywords from: {user_input}"
        """
        # Small, fast model for entity extraction
        entities = await small_llm.call(f"Extract entities from: {user_input}")
        return entities
```

---

## 🚀 Initialization: `/init` Command

### Anthropic Principle: "Maintain lightweight identifiers, load dynamically"

**Purpose:** Generate `OPENCLI.md` codebase summary on first use or when explicitly called.

```bash
/init
```

**Actions:**
1. Scan project structure: `find . -type f -name '*.py' | head -100`
2. Identify key files: `grep -r "class\|def" --include="*.py" | wc -l`
3. Discover patterns: `grep -r "import" --include="*.py" | sort | uniq`
4. Generate summary using LLM
5. Save to `OPENCLI.md`
6. Add to `ContextState.codebase_summary`

**OPENCLI.md Structure:**

```markdown
# Project: test_swecli

## Overview
A web application using FastAPI for authentication and user management.

## Structure
```
test_swecli/
├── api/
│   ├── auth.py (JWT token generation)
│   ├── users.py (User CRUD endpoints)
│   └── middleware/
│       └── auth.py (Authentication middleware)
├── models/
│   └── user.py (User data model)
├── tests/
│   └── test_auth.py (Authentication tests)
└── main.py (Application entry)
```

## Key Files
- `api/auth.py` - Core authentication logic
- `models/user.py` - User model with validation
- `main.py` - FastAPI app initialization

## Patterns
- Authentication: `api/middleware/auth.py:auth_required()`
- User validation: `models/user.py:validate_user()`
- Token generation: `api/auth.py:create_access_token()`

## Dependencies
- FastAPI, PyJWT, bcrypt, redis, sqlalchemy

## Current State (as of 2025-10-07)
- User authentication implemented
- JWT tokens with Redis storage
- Integration tests passing
```

**Token Budget:** Aim for 2,000-3,000 tokens (lightweight reference)

---

## 📊 Token Monitoring

### Implementation with tiktoken

```python
class TokenMonitor:
    """Monitor token usage and trigger compaction."""

    def __init__(self, context_limit: int = 256000):
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self.context_limit = context_limit
        self.compaction_threshold = 0.8

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    def count_message_tokens(self, message: Message) -> int:
        """Count tokens in a message including tool calls."""
        total = self.count_tokens(message.content)

        if message.tool_calls:
            for tool_call in message.tool_calls:
                total += self.count_tokens(str(tool_call))

        if message.tool_results:
            for result in message.tool_results:
                total += self.count_tokens(str(result))

        return total

    def update_context_state(self, context_state: ContextState) -> None:
        """Recalculate total tokens in context state."""
        total = 0

        # Count all messages
        for message in context_state.messages:
            if message.tokens == 0:
                message.tokens = self.count_message_tokens(message)
            total += message.tokens

        # Add codebase summary
        if context_state.codebase_summary:
            total += context_state.codebase_summary.tokens

        # Add current task context
        if context_state.current_task:
            total += context_state.current_task.tokens

        context_state.total_tokens = total

    def get_usage_stats(self, context_state: ContextState) -> Dict:
        """Get detailed usage statistics."""
        return {
            "total_tokens": context_state.total_tokens,
            "limit": context_state.context_limit,
            "usage_percent": (context_state.total_tokens / context_state.context_limit) * 100,
            "available_tokens": context_state.get_available_tokens(),
            "needs_compaction": context_state.needs_compaction(),
            "message_count": len(context_state.messages),
            "compaction_count": context_state.compaction_count,
            "breakdown": {
                "messages": sum(m.tokens for m in context_state.messages),
                "codebase_summary": context_state.codebase_summary.tokens if context_state.codebase_summary else 0,
                "current_task": context_state.current_task.tokens if context_state.current_task else 0,
            }
        }
```

---

## 🎭 Streaming Reasoning & Actions

### Anthropic Principle: "Transparency in agent behavior"

**Display Format:**

```
User: Fix the login bug

· Analyzing… (esc to interrupt · 1s)

💭 Reasoning:
   Need to find login-related code and error patterns

🔍 Action: grep 'login' src/
   Found 15 matches across 4 files:
   • src/api/auth.py:42: def login(username, password):
   • src/api/auth.py:78: if not validate_login(user):
   • src/models/user.py:23: # Login validation

💭 Reasoning:
   Error likely in src/api/auth.py:78 validation logic

📖 Action: read src/api/auth.py
   [File content displayed]

💭 Reasoning:
   Found the bug - missing null check before validation

✏️  Action: edit src/api/auth.py
   Fixed null check at line 78

⏺ Analyzing (completed in 12s, ↑ 3.2k tokens)

✅ Done! Fixed login bug in src/api/auth.py:78
```

**Implementation:**

```python
async def stream_reasoning_and_actions(llm_response_stream):
    """
    Stream LLM response with visual indicators for reasoning and actions.

    Parse streaming response for:
    - <thought>...</thought> → Display as 💭 Reasoning
    - <tool_call>...</tool_call> → Display as action with icon
    - Regular text → Display normally
    """
    current_section = None

    async for chunk in llm_response_stream:
        if "<thought>" in chunk:
            current_section = "reasoning"
            console.print("\n💭 Reasoning:", style="dim yellow")
        elif "</thought>" in chunk:
            current_section = None
        elif "<tool_call>" in chunk:
            current_section = "action"
            tool_name = extract_tool_name(chunk)
            icon = get_tool_icon(tool_name)
            console.print(f"\n{icon} Action: {tool_name}", style="cyan")
        elif current_section == "reasoning":
            console.print(f"   {chunk}", style="dim", end="")
        elif current_section == "action":
            console.print(f"   {chunk}", style="cyan", end="")
        else:
            console.print(chunk, end="")
```

---

## 🔒 Permission System

### Default Mode: Approval Required

```python
async def execute_tool_with_approval(tool_name: str, tool_args: Dict) -> Dict:
    """
    Execute tool after user approval in Default mode.

    Display:
    ✏️  Action: edit src/api/auth.py
        Change: Add null check at line 78

        Allow edit? [y/n]
    """
    if mode == OperationMode.DEFAULT:
        # Show proposed action
        console.print(f"\n{get_tool_icon(tool_name)} Action: {tool_name}", style="cyan")
        console.print(f"   {format_tool_args(tool_args)}", style="dim")

        # Ask for approval
        approved = Prompt.ask("   Allow?", choices=["y", "n"], default="y")

        if approved == "n":
            return {"status": "cancelled", "reason": "User declined"}

    # Execute tool
    return await tool_registry.execute(tool_name, tool_args)
```

### Plan/Auto Mode: Full Autonomy

```python
async def execute_tool_autonomous(tool_name: str, tool_args: Dict) -> Dict:
    """
    Execute tool without approval in Plan/Auto mode.

    Display:
    ✏️  Action: edit src/api/auth.py ✓
        Added null check at line 78
    """
    # Execute immediately
    result = await tool_registry.execute(tool_name, tool_args)

    # Show completion
    console.print(f"{get_tool_icon(tool_name)} Action: {tool_name} ✓", style="green")

    return result
```

---

## 📝 Logging System

### File: `.swecli/logs/<session_id>.log`

**Structure:**

```json
{
  "session_id": "2025-10-07-14-30-45",
  "started_at": "2025-10-07T14:30:45Z",
  "working_dir": "/Users/user/test_swecli",
  "events": [
    {
      "timestamp": "2025-10-07T14:30:50Z",
      "type": "user_input",
      "content": "Fix the login bug",
      "tokens": 5
    },
    {
      "timestamp": "2025-10-07T14:30:52Z",
      "type": "context_retrieval",
      "actions": ["grep 'login' src/", "read src/api/auth.py"],
      "tokens_added": 850
    },
    {
      "timestamp": "2025-10-07T14:30:55Z",
      "type": "llm_call",
      "tokens_in": 3200,
      "tokens_out": 450,
      "duration_ms": 2500
    },
    {
      "timestamp": "2025-10-07T14:30:58Z",
      "type": "tool_execution",
      "tool": "edit",
      "file": "src/api/auth.py",
      "approved": true
    },
    {
      "timestamp": "2025-10-07T14:31:00Z",
      "type": "context_update",
      "total_tokens": 12500,
      "usage_percent": 4.9
    },
    {
      "timestamp": "2025-10-07T14:45:00Z",
      "type": "compaction",
      "tokens_before": 210000,
      "tokens_after": 62000,
      "reduction_percent": 70.5,
      "messages_compacted": 45
    }
  ],
  "stats": {
    "total_turns": 12,
    "llm_calls": 12,
    "tools_executed": 18,
    "compactions": 1,
    "total_tokens_used": 62000,
    "files_modified": ["src/api/auth.py", "tests/test_auth.py"]
  }
}
```

---

## 🎯 Target Metrics

Based on Anthropic's principles and your requirements:

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Task Autonomy** | 90% | Tasks completed without user intervention |
| **Context Efficiency** | <80% | Token usage stays below compaction threshold |
| **Compaction Effectiveness** | 60-80% | Token reduction after compaction |
| **Retrieval Precision** | >85% | Just-in-time context is relevant |
| **User Satisfaction** | High | Fluid flow, minimal interruptions |
| **Token Waste** | <10% | Redundant or low-signal tokens |

---

## 📁 File Structure

```
swecli/
├── core/
│   ├── context_engine.py         (NEW) - ContextState, compaction
│   ├── token_monitor.py           (NEW) - Token counting with tiktoken
│   ├── context_retriever.py       (NEW) - Just-in-time retrieval
│   └── agent.py                   (MODIFY) - Integration
├── commands/
│   ├── init_command.py            (NEW) - /init for OPENCLI.md
│   └── compact_command.py         (NEW) - /compact manual trigger
└── models/
    └── context_models.py          (NEW) - Pydantic models

.swecli/
├── OPENCLI.md                     (GENERATED) - Codebase summary
├── memory/
│   └── session_notes.md           (GENERATED) - Structured notes
└── logs/
    └── <session_id>.log           (GENERATED) - Session logs
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create `context_engine.py` with ContextState
- [ ] Implement TokenMonitor with tiktoken
- [ ] Add basic message history append
- [ ] Test with simple conversations

### Phase 2: Just-in-Time Retrieval (Week 2)
- [ ] Implement ContextRetriever
- [ ] Add entity extraction
- [ ] Proactive grep/read based on user input
- [ ] Test context relevance

### Phase 3: Compaction (Week 3)
- [ ] Design compaction prompt
- [ ] Implement AI-driven summarization
- [ ] Test 60-80% reduction
- [ ] Verify critical info preservation

### Phase 4: Persistence (Week 4)
- [ ] Implement /init command
- [ ] Generate OPENCLI.md
- [ ] Structured note-taking (session_notes.md)
- [ ] Session logs (.swecli/logs/)

### Phase 5: Streaming & UX (Week 5)
- [ ] Stream reasoning and actions
- [ ] Visual indicators (💭, 🔍, ✏️)
- [ ] Permission system (Default vs Plan mode)
- [ ] Polish user experience

### Phase 6: Optimization (Week 6)
- [ ] Measure and optimize token usage
- [ ] Fine-tune compaction prompts
- [ ] Improve retrieval precision
- [ ] Performance testing

---

## 💡 Key Design Decisions

### 1. Why 256k Context Window?
- **Large enough** for most software tasks without frequent compaction
- **Available via Fireworks AI** (Claude 3.5 Sonnet)
- **Matches Claude Code's** approach (long context, minimal complexity)

### 2. Why 80% Compaction Threshold?
- **Safety margin** before hitting hard limit
- **Time to compact** without interrupting user flow
- **Anthropic's recommendation** for proactive management

### 3. Why AI-Driven Compaction?
- **Better than rule-based** - understands semantic importance
- **Context-aware** - preserves what matters for current task
- **Flexible** - adapts to different project types

### 4. Why Just-in-Time Retrieval?
- **Token efficiency** - only load what's needed
- **Anthropic's principle** - "progressive disclosure"
- **Faster** - smaller context = faster LLM calls

### 5. Why OPENCLI.md as Persistent Memory?
- **Lightweight reference** (2-3k tokens)
- **Always available** - loaded at session start
- **User-readable** - can be edited manually
- **Project-specific** - each project has its own

---

## 🎊 Expected Outcomes

Following Anthropic's context engineering principles:

✅ **90% task autonomy** - Agent handles most tasks without intervention

✅ **Fluid conversation flow** - Minimal interruptions, natural interaction

✅ **Token efficiency** - <10% wasted tokens, high signal-to-noise

✅ **Long-running sessions** - Support multi-hour sessions without degradation

✅ **Context awareness** - Agent always has relevant info at hand

✅ **Transparency** - User sees what agent is thinking and doing

✅ **Safety** - Permission system in Default mode, logging for audit

---

**Next Step:** Implement Phase 1 (Foundation) with ContextState and TokenMonitor.

**References:**
- [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Fireworks AI Claude 3.5 Sonnet](https://fireworks.ai/models/claude-3-5-sonnet)
- [tiktoken](https://github.com/openai/tiktoken)
