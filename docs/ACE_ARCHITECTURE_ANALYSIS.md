# ACE (Agentic Context Engine) Architecture Analysis

## Executive Summary

This document analyzes the ACE (Agentic Context Engine) architecture and how it solves the session history pollution problem in swecli. ACE provides a framework for maintaining useful context across multiple interactions without polluting future queries with irrelevant historical information.

**Key Learning**: Instead of saving ALL assistant messages to session history, ACE saves only **distilled strategies** that are proven to be helpful.

## The Problem ACE Solves

### Current swecli Issue

When loading session history, we include messages from previous queries that pollute the context:

```
Iteration 1 contains 8 messages:
[0] 📜 SYSTEM PROMPT
[1] 👤 USER: "delete the ping pong game"
[2] 🤖 ASSISTANT: "I'll delete..." (text-only, no tools)  ← NOISE
[3] 🤖 ASSISTANT: "I see the file..." (text-only)        ← NOISE
[4] 🤖 ASSISTANT: "I've deleted..." (text-only)          ← NOISE
[5] 👤 USER: "ok bro, now run the ping pong game again"
[6] 🤖 ASSISTANT: "I'm sorry but..." (text-only)         ← NOISE
[7] 👤 USER: "create a new one and run"
```

**Problem**: Text-only responses from previous queries create noisy conversation context with irrelevant details.

### ACE's Solution

ACE converts execution experiences into **structured, reusable strategies** stored in a **Playbook**:

```python
# Instead of raw message:
"I'll delete the ping pong game files from the current directory.
First, let me see what files are present."

# ACE distills into a strategy bullet:
Bullet(
  id="file-ops-00042",
  section="File Operations Best Practices",
  content="Before deleting files, first list directory to confirm file exists",
  helpful=5,
  harmful=0,
  neutral=0
)
```

## ACE Core Components

### 1. Playbook (Living Context Store)

A structured, evolving knowledge base that stores "bullets" (strategy entries).

**Structure**:
```python
@dataclass
class Bullet:
    id: str              # Unique identifier (e.g., "file-ops-00042")
    section: str         # Category (e.g., "File Operations Best Practices")
    content: str         # The actual strategy
    helpful: int = 0     # Effectiveness tracking
    harmful: int = 0
    neutral: int = 0
    created_at: str
    updated_at: str

class Playbook:
    _bullets: Dict[str, Bullet]
    _sections: Dict[str, List[str]]

    def as_prompt(self) -> str:
        """Format playbook for LLM consumption."""
        # Returns:
        ## File Operations Best Practices
        - [file-ops-00042] Before deleting files, first list directory (helpful=5, harmful=0)
        - [file-ops-00043] Use absolute paths when possible (helpful=3, harmful=1)

        ## Error Handling
        - [error-00015] Check parent directory exists (helpful=8, harmful=0)
```

**Key Features**:
- Structured by sections/categories
- Effectiveness tracking (helpful/harmful/neutral counters)
- Serializable to JSON for persistence
- Clean presentation format for LLM prompts

### 2. Three Specialized Roles (All using same LLM)

#### Generator (Similar to swecli's Agent)

**Purpose**: Produces answers using current playbook strategies

**Input**:
- Question (user query)
- Context (additional requirements)
- Playbook (current strategies)
- Reflection (recent feedback, NOT full history)

**Output**:
```python
@dataclass
class GeneratorOutput:
    reasoning: str           # Step-by-step chain of thought
    final_answer: str        # The actual answer
    bullet_ids: List[str]    # Which strategies were used
    raw: Dict[str, Any]      # Full JSON response
```

**Key Insight**: Generator references **playbook bullets**, not raw conversation history.

#### Reflector (Post-execution Analysis)

**Purpose**: Analyzes what worked and what didn't

**Input**:
- Question (original query)
- Generator output (reasoning + answer)
- Playbook excerpt (bullets that were used)
- Ground truth (if available)
- Feedback (execution results)

**Output**:
```python
@dataclass
class ReflectorOutput:
    reasoning: str                    # Analysis process
    error_identification: str         # What went wrong
    root_cause_analysis: str          # Why it happened
    correct_approach: str             # What should be done
    key_insight: str                  # Reusable takeaway
    bullet_tags: List[BulletTag]      # Tag bullets as helpful/harmful/neutral
```

**Key Insight**: Extracts learnings from both successes and failures, tags strategy effectiveness.

#### Curator (Playbook Updater)

**Purpose**: Transforms reflections into playbook updates

**Input**:
- Reflection (analysis from Reflector)
- Current playbook
- Question context
- Progress summary

**Output**:
```python
@dataclass
class CuratorOutput:
    delta: DeltaBatch  # Operations to apply to playbook
    raw: Dict[str, Any]

@dataclass
class DeltaBatch:
    reasoning: str
    operations: List[DeltaOperation]
```

**Key Insight**: Uses surgical updates (ADD/UPDATE/TAG/REMOVE) instead of appending everything.

### 3. Delta Operations (Incremental Updates)

Instead of appending everything to history, ACE uses targeted mutations:

```python
# ADD: Add new strategy
{
  "type": "ADD",
  "section": "Error Handling",
  "content": "When file not found, check parent directory first",
  "metadata": {"helpful": 1}
}

# UPDATE: Modify existing strategy
{
  "type": "UPDATE",
  "bullet_id": "error-00042",
  "content": "Enhanced version of strategy...",
  "metadata": {"helpful": 3}
}

# TAG: Update effectiveness counters
{
  "type": "TAG",
  "bullet_id": "error-00042",
  "metadata": {"helpful": 1}  # Increment helpful counter
}

# REMOVE: Delete unhelpful strategies
{
  "type": "REMOVE",
  "bullet_id": "error-00013"
}
```

### 4. Adaptation Loops

**OfflineAdapter**: Multiple epochs over training set for initial learning
**OnlineAdapter**: Sequential processing for continuous deployment learning

**Flow**:
1. Generator produces answer using playbook
2. Environment evaluates the answer
3. Reflector analyzes what worked/failed
4. Reflector tags bullets as helpful/harmful
5. Curator decides playbook updates
6. Playbook is updated with delta operations
7. Repeat for next query

## How ACE Prevents Context Pollution

### Principle 1: Structured Knowledge over Raw Messages

**Bad (Current swecli)**:
```python
messages = [
    {"role": "assistant", "content": "I'll delete the file..."},
    {"role": "assistant", "content": "I see the file named ping_pong.py..."},
    {"role": "assistant", "content": "I've deleted the file successfully..."}
]
```

**Good (ACE approach)**:
```python
playbook.add_bullet(
    section="File Operations",
    content="Confirm file exists before deletion",
    metadata={"helpful": 1}
)
```

### Principle 2: Effectiveness Tracking

Every strategy tracks its usefulness:
- **helpful**: Strategy led to success
- **harmful**: Strategy caused errors
- **neutral**: No clear impact

This enables:
- Auto-pruning of harmful strategies
- Prioritization of helpful strategies
- Evidence-based context management

### Principle 3: Reflection Window over Full History

Instead of loading entire conversation history:

```python
# ACE uses limited reflection window
self._recent_reflections: List[str] = []  # Max 3 recent reflections
self.reflection_window = 3

def _update_recent_reflections(self, reflection: ReflectorOutput):
    self._recent_reflections.append(serialize(reflection))
    if len(self._recent_reflections) > self.reflection_window:
        self._recent_reflections = self._recent_reflections[-self.reflection_window:]
```

**Benefits**:
- Recent context for continuity
- No accumulation of old irrelevant data
- Fixed context size

### Principle 4: Distillation over Verbosity

**Verbose message** (86 chars):
```
"I'll delete the ping pong game files. First, let me see what files are present."
```

**Distilled strategy** (52 chars):
```
"Before file deletion, list directory to confirm file exists"
```

Plus structured metadata (section, effectiveness counters, etc.)

## Generator Prompt Structure in ACE

```python
GENERATOR_PROMPT = """
You are an expert assistant.
Use the provided playbook of strategies.

Playbook:
{playbook}  # Formatted bullets with effectiveness counters

Recent reflection:
{reflection}  # Last 3 reflections, NOT full conversation

Question:
{question}

Additional context:
{context}

Respond with JSON:
{
  "reasoning": "<step-by-step>",
  "bullet_ids": ["<used-strategies>"],
  "final_answer": "<answer>"
}
"""
```

**Key differences from swecli**:
1. **Structured knowledge** instead of raw message history
2. **Effectiveness tracking** visible in prompt
3. **Reflection window** for recent context
4. **Distilled strategies** instead of verbose descriptions

## Adaptation Roadmap for swecli

### Phase 1: Immediate Fix ✅ (Already Done)

**Problem**: Text-only final responses polluting session history

**Solution**:
```python
# In async_query_processor.py
if not tool_calls:
    # Display final message to user
    self.chat_app.add_assistant_message(formatted)

    # DON'T save to session - prevents pollution
    # Only messages with tool calls are saved
    break
```

**Status**: ✅ Completed

### Phase 2: Add Reflection (Inspired by ACE)

**Goal**: Extract learnings from tool executions

**Implementation**:
```python
# swecli/core/reflection/reflector.py
class ExecutionReflector:
    """Analyzes tool execution to extract learnings."""

    def reflect_on_execution(
        self,
        query: str,
        tool_calls: List[ToolCall],
        tool_results: List[ToolResult],
        outcome: str  # "success" | "error" | "partial"
    ) -> Optional[Strategy]:
        """
        Extract a reusable strategy from tool execution.

        Returns:
            Strategy if worth remembering, None otherwise
        """
        # Only reflect on patterns worth learning
        if not self._is_worth_learning(tool_calls, tool_results):
            return None

        return self._extract_strategy(query, tool_calls, tool_results, outcome)

    def _is_worth_learning(self, tool_calls, tool_results) -> bool:
        """Determine if execution contains learnable patterns."""
        # Skip single read operations
        if len(tool_calls) == 1 and tool_calls[0].name == "read_file":
            return False

        # Learn from multi-step sequences
        if len(tool_calls) >= 2:
            return True

        # Learn from errors and recoveries
        if any(r.error for r in tool_results):
            return True

        return False
```

### Phase 3: Playbook Integration

**Goal**: Store strategies instead of raw messages

**Implementation**:
```python
# swecli/models/playbook.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class Strategy:
    """A learned pattern or best practice."""
    id: str
    category: str  # "file_operations", "error_handling", "shell_commands", etc.
    content: str   # The actual strategy description
    helpful_count: int = 0
    harmful_count: int = 0
    neutral_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)

    def tag(self, tag: str):
        """Update effectiveness counter."""
        if tag == "helpful":
            self.helpful_count += 1
        elif tag == "harmful":
            self.harmful_count += 1
        elif tag == "neutral":
            self.neutral_count += 1
        self.last_used = datetime.now()

class SessionPlaybook:
    """Stores learned strategies for a session."""

    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self._next_id = 0

    def add_strategy(self, category: str, content: str) -> Strategy:
        """Add new strategy to playbook."""
        strategy_id = f"{category[:3]}-{self._next_id:05d}"
        self._next_id += 1

        strategy = Strategy(
            id=strategy_id,
            category=category,
            content=content
        )
        self.strategies[strategy_id] = strategy
        return strategy

    def as_context(self) -> str:
        """Format strategies for inclusion in system prompt."""
        if not self.strategies:
            return ""

        # Group by category
        by_category: Dict[str, List[Strategy]] = {}
        for strategy in self.strategies.values():
            by_category.setdefault(strategy.category, []).append(strategy)

        # Format as markdown
        lines = ["\n## Learned Strategies\n"]
        for category, strategies in sorted(by_category.items()):
            lines.append(f"\n### {category.replace('_', ' ').title()}\n")
            for s in strategies:
                effectiveness = f"(helpful={s.helpful_count}, harmful={s.harmful_count})"
                lines.append(f"- [{s.id}] {s.content} {effectiveness}\n")

        return "".join(lines)

    def to_dict(self) -> dict:
        """Serialize to dict for session storage."""
        return {
            "strategies": {
                sid: {
                    "id": s.id,
                    "category": s.category,
                    "content": s.content,
                    "helpful_count": s.helpful_count,
                    "harmful_count": s.harmful_count,
                    "neutral_count": s.neutral_count,
                    "created_at": s.created_at.isoformat(),
                    "last_used": s.last_used.isoformat()
                }
                for sid, s in self.strategies.items()
            },
            "next_id": self._next_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionPlaybook":
        """Deserialize from dict."""
        playbook = cls()
        playbook._next_id = data.get("next_id", 0)

        for sid, sdata in data.get("strategies", {}).items():
            strategy = Strategy(
                id=sdata["id"],
                category=sdata["category"],
                content=sdata["content"],
                helpful_count=sdata.get("helpful_count", 0),
                harmful_count=sdata.get("harmful_count", 0),
                neutral_count=sdata.get("neutral_count", 0),
                created_at=datetime.fromisoformat(sdata.get("created_at", datetime.now().isoformat())),
                last_used=datetime.fromisoformat(sdata.get("last_used", datetime.now().isoformat()))
            )
            playbook.strategies[sid] = strategy

        return playbook
```

### Phase 4: Modify Session Storage

**Goal**: Store tool-calling messages + strategies, not text-only responses

**Implementation**:
```python
# swecli/models/message.py - Add playbook field to Session
@dataclass
class Session:
    # ... existing fields
    playbook: SessionPlaybook = field(default_factory=SessionPlaybook)

# swecli/repl/chat/async_query_processor.py
async def process_query(self, query: str) -> None:
    """Process query with reflection and strategy extraction."""

    # ... existing ReAct loop

    # After tool execution succeeds
    if tool_calls and not any(r.error for r in tool_results):
        # Extract learning from successful execution
        strategy = self._reflect_on_success(query, tool_calls, tool_results)
        if strategy:
            self.repl.session_manager.current_session.playbook.add_strategy(
                category=strategy.category,
                content=strategy.content
            )

    # Final text-only response: display but DON'T save
    if not tool_calls:
        if llm_description:
            self.chat_app.add_assistant_message(formatted)
        # No session save - prevents pollution
        break

def _reflect_on_success(
    self,
    query: str,
    tool_calls: List[ToolCall],
    tool_results: List[ToolResult]
) -> Optional[Strategy]:
    """Extract strategy from successful tool execution."""

    # Simple pattern extraction (can be enhanced with LLM later)

    # Multi-step file operations
    if len(tool_calls) >= 2:
        names = [tc.name for tc in tool_calls]
        if "list_files" in names and "read_file" in names:
            return Strategy(
                category="file_operations",
                content="List directory before reading files to understand structure"
            )

    # Error recovery patterns
    if any(tc.name == "search" for tc in tool_calls):
        if any(tc.name == "read_file" for tc in tool_calls):
            return Strategy(
                category="code_navigation",
                content="Search for patterns before reading files to locate relevant code"
            )

    # Shell command patterns
    if any(tc.name == "run_command" for tc in tool_calls):
        commands = [tc.parameters.get("command") for tc in tool_calls if tc.name == "run_command"]
        if any("test" in cmd.lower() for cmd in commands):
            return Strategy(
                category="testing",
                content="Run tests after making code changes to verify correctness"
            )

    return None
```

### Phase 5: Update Message Preparation

**Goal**: Include playbook context in system prompt

**Implementation**:
```python
# swecli/repl/chat/async_query_processor.py
def _prepare_messages(self, query: str, enhanced_query: str) -> list:
    """Prepare messages for LLM API call with playbook context."""

    # Load only tool-calling messages (ReAct reasoning chain)
    messages = (
        self.repl.session_manager.current_session.to_api_messages()
        if self.repl.session_manager.current_session
        else []
    )

    if enhanced_query != query:
        messages[-1]["content"] = enhanced_query

    # Build system prompt with playbook strategies
    system_content = self.repl.agent.system_prompt

    # Add playbook strategies if any exist
    if self.repl.session_manager.current_session:
        playbook_context = self.repl.session_manager.current_session.playbook.as_context()
        if playbook_context:
            system_content += playbook_context

    # Add system prompt
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": system_content})
    else:
        # Update existing system prompt with playbook
        messages[0]["content"] = system_content

    return messages
```

### Phase 6: Advanced Context Management

**Future enhancements**:

1. **LLM-powered reflection**: Use LLM to extract strategies instead of pattern matching
2. **Effectiveness tracking**: Tag strategies based on user feedback
3. **Auto-pruning**: Remove low-value strategies (harmful > helpful)
4. **Strategy deduplication**: Merge similar strategies
5. **Cross-session learning**: Share strategies across sessions in same repository

## Key Takeaways

### 1. Structure Matters

Raw conversation messages:
- Verbose
- Redundant
- Context-inefficient
- Hard to track effectiveness

Structured strategies:
- Concise
- Unique
- Context-efficient
- Trackable effectiveness

### 2. Don't Save Everything

**Current swecli** (before fix):
- Saves ALL assistant messages
- Includes verbose descriptions
- Accumulates noise over time

**ACE approach**:
- Saves only tool-calling messages (ReAct chain)
- Extracts distilled strategies
- Maintains clean context

### 3. Effectiveness Tracking

ACE tracks which strategies help vs. hurt:
- `helpful`: Led to success
- `harmful`: Caused errors
- `neutral`: No clear impact

This enables intelligent context management:
- Prioritize helpful strategies
- Remove harmful patterns
- Make evidence-based decisions

### 4. Reflection is Key

Post-execution analysis extracts real value:
- What worked?
- What failed?
- Why?
- What's the reusable lesson?

Without reflection, you're just accumulating data, not learning.

### 5. Incremental Evolution

ACE uses delta operations (ADD/UPDATE/TAG/REMOVE) instead of:
- Appending everything
- Regenerating from scratch
- Manual curation

This enables continuous, automated improvement.

## Comparison: Current swecli vs ACE-inspired swecli

| Aspect | Current swecli | ACE-inspired swecli |
|--------|---------------|---------------------|
| **Context Storage** | Raw messages | Structured strategies |
| **Session History** | All messages (before fix) | Tool-calling messages + strategies |
| **Text-only Responses** | Saved (before fix) | Not saved ✅ |
| **Learning** | None | Extracts patterns from execution |
| **Effectiveness** | Not tracked | Helpful/harmful/neutral counters |
| **Context Growth** | Linear accumulation | Bounded by strategy count |
| **Reusability** | Low (verbose messages) | High (distilled strategies) |
| **Noise Level** | High (before fix) | Low |
| **Cross-session** | Per-session only | Could share strategies |

## References

- ACE Paper: [Agentic Context Engineering](https://arxiv.org/abs/2510.04618)
- ACE Repository: [kayba-ai/agentic-context-engine](https://github.com/kayba-ai/agentic-context-engine)
- Related: [Dynamic Cheatsheet](https://arxiv.org/abs/2504.07952)

## Next Steps for swecli

1. ✅ **Phase 1 Complete**: Stop saving text-only responses
2. 🔄 **Phase 2 In Progress**: Implement basic reflection and strategy extraction
3. ⏳ **Phase 3 Planned**: Full playbook integration
4. ⏳ **Phase 4 Planned**: Advanced effectiveness tracking
5. ⏳ **Phase 5 Planned**: Cross-session strategy sharing

---

**Document Status**: Living document, updated as implementation progresses
**Last Updated**: 2025-10-23
**Author**: Claude Code + swecli team
