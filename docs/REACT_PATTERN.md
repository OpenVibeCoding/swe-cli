# ReAct Pattern Implementation in OpenCLI

## Overview

OpenCLI implements the **ReAct** (Reasoning + Acting) pattern, a powerful AI agent architecture that enables autonomous task completion through iterative cycles of reasoning, acting, and observing.

**ReAct** stands for:
- **Reasoning**: LLM thinks about what to do next
- **Acting**: Agent uses tools to gather information or perform actions
- **Observing**: Agent sees the results and uses them to inform next steps

This pattern allows the AI to break down complex tasks into manageable steps, adapt to unexpected situations, and work autonomously while remaining transparent and interruptible.

---

## Core Architecture

### 1. Main ReAct Loop

Located in: `opencli/repl/chat/async_query_processor.py:244-346`

```python
async def process_query(self, query: str) -> None:
    """Process query asynchronously with full ReAct loop."""

    # Initialize state
    messages = self._prepare_messages(query, enhanced_query)
    iteration = 0
    SAFETY_LIMIT = 30

    # ReAct loop
    while True:
        iteration += 1

        # REASONING: Call LLM to think about what to do next
        response = await self._call_llm_with_spinner(messages)
        llm_description = response.get("content", "")

        # Check if task is complete (no tool calls)
        tool_calls = response.get("tool_calls")
        if not tool_calls:
            break  # Task complete

        # Add assistant's reasoning to message history
        messages.append({
            "role": "assistant",
            "content": llm_description,
            "tool_calls": tool_calls,
        })

        # ACTING: Execute the tools the agent requested
        await self.chat_app._handle_tool_calls(tool_calls, messages)

        # OBSERVING: Tool results are added to messages
        # Loop continues - LLM will see results and reason again
```

### 2. The Three Phases

#### Phase 1: Reasoning
```python
response = await self._call_llm_with_spinner(messages)
```

**What happens:**
- Shows animated spinner with random thinking verbs ("Analyzing...", "Thinking...", "Processing...")
- LLM receives full conversation history including previous tool results
- LLM decides what tools to call (or if task is complete)
- Returns reasoning text + tool calls (or empty if done)

**User sees:**
```
🔄 Analyzing... (2s • esc to interrupt)
```

#### Phase 2: Acting
```python
await self.chat_app._handle_tool_calls(tool_calls, messages)
```

**What happens:**
- Executes requested tools with two-phase approval system
- Shows progress for each tool execution
- Handles interrupts at multiple checkpoints
- Formats and displays results

**User sees:**
```
⏺ read_file(path="auth.py")
┌─ File Content ───────────────
│ def authenticate(token):
│     # Bug: missing validation
│     return True
└──────────────────────────────
```

#### Phase 3: Observing
```python
messages.append({
    "role": "tool",
    "tool_call_id": tool_call["id"],
    "content": tool_result,
})
```

**What happens:**
- Tool results are appended to message history
- LLM receives these results in next iteration
- Agent learns from observations and adjusts strategy

---

## Two-Phase Approval System

Located in: `opencli/repl/chat/tool_executor.py:30-207`

### Phase 1: Approval Collection (Lines 45-104)

```python
# Identify bash commands that need approval
for tool_call in tool_calls:
    if tool_name == "run_command":
        # Request approval from user
        approval_result = await self.repl.approval_manager.request_approval(
            operation=operation,
            preview=f"Execute: {command}",
            command=command,
            working_dir=working_dir,
        )

        # Store decision
        bash_approvals[tool_call["id"]] = approval_result.approved

        if not approval_result.approved:
            # User cancelled - stop everything
            self.chat_app._interrupt_requested = True
            return
```

**Why separate approval phase:**
- Shows all approvals upfront before any execution
- User can review and cancel before any changes happen
- Cleaner UX - no mixing of approvals and executions

### Phase 2: Tool Execution (Lines 105-194)

```python
# Execute all approved tools
for tool_call in tool_calls:
    # Check for interrupt before each tool
    if self.chat_app._interrupt_requested:
        return

    # Show animated spinner during execution
    self.chat_app._start_spinner(tool_call_display)

    # Execute tool with interrupt checking
    result = await asyncio.to_thread(execute_with_interrupt_check)

    # Stop spinner and display result
    self.chat_app._stop_spinner()
    self._display_tool_result(tool_call_display, tool_name, tool_args, result)

    # Add result to message history
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": tool_result,
    })
```

---

## Example ReAct Flow

### User Request: "Find and fix the bug in auth.py"

#### Iteration 1: Initial Investigation
**Reasoning:**
```
I need to read auth.py first to understand the code and identify the bug.
```

**Acting:**
```
⏺ read_file(path="auth.py")
```

**Observing:**
```
┌─ File Content ───────────────
│ def authenticate(token):
│     if token:
│         return True  # Bug: no validation
│     return False
└──────────────────────────────
```

#### Iteration 2: Understanding Context
**Reasoning:**
```
I see the issue - there's no token validation. Let me check if there's a
validation function elsewhere in the codebase.
```

**Acting:**
```
⏺ search_code(pattern="validate_token")
```

**Observing:**
```
┌─ Search Results ─────────────
│ utils/security.py:15: def validate_token(token):
│ utils/security.py:16:     # JWT validation logic
└──────────────────────────────
```

#### Iteration 3: Implementing Fix
**Reasoning:**
```
Found it! There's a validate_token function in utils/security.py.
I'll update auth.py to use it.
```

**Acting:**
```
⏺ edit_file(
    path="auth.py",
    old_string="def authenticate(token):\n    if token:\n        return True",
    new_string="from utils.security import validate_token\n\ndef authenticate(token):\n    if token and validate_token(token):\n        return True"
)
```

**Observing:**
```
┌─ File Edit ──────────────────
│ ✓ File updated successfully
│ Modified: auth.py
└──────────────────────────────
```

#### Iteration 4: Verification
**Reasoning:**
```
Let me verify the fix works by running the auth tests.
```

**Acting:**
```
⏺ run_command(command="pytest tests/test_auth.py -v")

[Approval Dialog Appears]
❯ 1. Yes, run this command
  2. Yes, and don't ask again for pytest tests
  3. No, cancel this operation (esc)
```

**Observing:**
```
┌─ Command Output ─────────────
│ tests/test_auth.py::test_valid_token PASSED
│ tests/test_auth.py::test_invalid_token PASSED
│ tests/test_auth.py::test_missing_token PASSED
│ ==================== 3 passed in 0.5s ====================
└──────────────────────────────
```

#### Iteration 5: Conclusion
**Reasoning:**
```
Perfect! All tests pass. The bug is fixed. Here's what I did:

1. Found the bug: authenticate() was accepting any token without validation
2. Located the existing validate_token() function in utils/security.py
3. Updated auth.py to import and use validate_token()
4. Verified with tests - all passing

The authentication system now properly validates tokens before granting access.
```

**Acting:**
(No tool calls - task complete)

**Loop Exits** ✓

---

## Safety Mechanisms

### 1. Iteration Limit

```python
SAFETY_LIMIT = 30  # Maximum iterations

if iteration > SAFETY_LIMIT:
    await self._handle_safety_limit(messages)
    break
```

**Purpose:** Prevents infinite loops if agent gets stuck

**What happens:**
- After 30 iterations, automatically stops
- Requests summary from agent
- Shows warning to user

### 2. Read Operation Nudging

```python
consecutive_reads = 0
READ_OPERATIONS = {"read_file", "list_files", "search"}

# Track consecutive read-only operations
all_reads = all(tc["function"]["name"] in READ_OPERATIONS
                for tc in tool_calls)
consecutive_reads = consecutive_reads + 1 if all_reads else 0

if consecutive_reads >= 5:
    # Nudge agent to conclude
    messages.append({
        "role": "user",
        "content": "Based on what you've seen, please summarize your findings..."
    })
    consecutive_reads = 0
```

**Purpose:** Prevents agent from endlessly exploring without taking action

**What happens:**
- Tracks if agent is only reading files (not writing/executing)
- After 5 consecutive read operations, nudges agent to summarize
- Encourages agent to conclude investigation phase

### 3. Interrupt System

The interrupt system checks at **multiple checkpoints**:

```python
# Before LLM call
if self._check_interrupt(messages):
    return

# During LLM call (0.1s polling)
while not llm_task.done():
    if self._check_interrupt(messages):
        llm_task.cancel()
        return
    await asyncio.sleep(0.1)

# After LLM call
if self._check_interrupt(messages):
    return

# Before each tool
if self.chat_app._interrupt_requested:
    return

# During tool execution
def execute_with_interrupt_check():
    if self.chat_app._interrupt_requested:
        return {"success": False, "error": "Interrupted by user"}
    return result

# After tool execution
if self._check_interrupt(messages):
    return
```

**Purpose:** User can press ESC at any time to stop processing

**User experience:**
```
🔄 Analyzing... (5s • esc to interrupt)
[User presses ESC]
⏺ Interrupted by user (ESC)
```

### 4. Context Management

```python
# Check before each iteration (except first)
if iteration > 1:
    await self.chat_app._check_and_compact_context(messages)
```

**Purpose:** Manages token usage to stay within LLM context limits

**What happens:**
- Monitors token count in real-time (shown in status bar)
- At 80% capacity, triggers intelligent compaction
- Preserves recent context and important messages
- Compresses older messages for efficiency

**User sees:**
```
▶ normal mode • 204,800 / 256,000 tokens (80%)
⚠ Context compaction in progress...
✓ Context compacted: 256,000 → 128,000 tokens
```

---

## Interrupt Handling Deep Dive

### Interrupt Flow

```
User presses ESC
    ↓
Key binding sets: _interrupt_requested = True
    ↓
Next checkpoint detects interrupt
    ↓
_check_interrupt() called
    ↓
Stop spinner
    ↓
Show interrupt message (if not already shown)
    ↓
Clean up incomplete assistant messages
    ↓
Set: _interrupt_shown = True
    ↓
Reset processing state
    ↓
Return to REPL prompt
```

### Interrupt Display States

**During Thinking:**
```
🔄 Analyzing... (3s • esc to interrupt)
[ESC pressed]
⏺ Interrupted by user (ESC)
```

**During Tool Execution:**
```
⏺ run_command(command="npm install")
[ESC pressed]
⏺ run_command(command="npm install")
┌─ Interrupted ────────────────
│ ⏺ Interrupted by user (ESC)
└──────────────────────────────
```

### Why Multiple Checkpoints?

Different stages have different interrupt needs:

1. **Before LLM call**: Fast interrupt, no cleanup needed
2. **During LLM call**: Cancel async task, minimal cleanup
3. **After LLM call**: Clean up message history
4. **Before tool**: Prevent starting new work
5. **During tool**: Stop long-running commands
6. **After tool**: Prevent showing results of cancelled work

---

## Message History Structure

The message history follows OpenAI's chat completion format:

```python
messages = [
    # System prompt (always first)
    {
        "role": "system",
        "content": "You are OpenCLI, an AI coding assistant..."
    },

    # User message
    {
        "role": "user",
        "content": "Find and fix the bug in auth.py"
    },

    # Assistant reasoning + tool calls
    {
        "role": "assistant",
        "content": "I'll read auth.py first to identify the bug.",
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": '{"path": "auth.py"}'
                }
            }
        ]
    },

    # Tool result
    {
        "role": "tool",
        "tool_call_id": "call_abc123",
        "content": "def authenticate(token):\n    if token:\n        return True..."
    },

    # Assistant reasoning + more tool calls
    {
        "role": "assistant",
        "content": "I found the bug. Let me fix it...",
        "tool_calls": [...]
    },

    # ... more tool results ...

    # Assistant final response (no tool_calls)
    {
        "role": "assistant",
        "content": "Bug fixed! Here's what I did..."
    }
]
```

**Key points:**
- System prompt always first
- Alternates: user → assistant → tool → assistant → tool → ...
- Assistant with no `tool_calls` signals completion
- All tool results reference their `tool_call_id`

---

## Available Tools

The agent has access to these tools (defined in tool registry):

### File Operations
- `read_file(path)` - Read file contents
- `write_file(path, content)` - Create or overwrite file
- `edit_file(path, old_string, new_string)` - Edit existing file
- `list_files(path)` - List directory contents
- `search_code(pattern, path)` - Search for code patterns

### Command Execution
- `run_command(command, working_dir)` - Execute bash commands (requires approval)

### Project Navigation
- `get_file_tree(max_depth)` - Get project structure
- `find_definition(symbol)` - Find where symbol is defined

### Context Management
- `compact_context()` - Manually trigger context compaction

Each tool returns structured results that the LLM can understand and use.

---

## Performance Optimizations

### 1. Async/Await Throughout

```python
# All blocking operations run in threads
response = await asyncio.to_thread(self.repl.agent.call_llm, messages)
result = await asyncio.to_thread(execute_tool, tool_name, tool_args)
```

**Benefits:**
- UI remains responsive during LLM calls
- Multiple operations can overlap
- Interrupt system can check frequently without blocking

### 2. Spinner Animations

```python
# Start spinner before long operations
self.chat_app._start_spinner("Analyzing...")

# Spinner updates every 0.1s in background
# Shows elapsed time and interrupt hint
# "🔄 Analyzing... (3s • esc to interrupt)"

# Stop when operation completes
self.chat_app._stop_spinner()
```

**Benefits:**
- User knows something is happening
- Shows elapsed time for transparency
- Interrupt hint reminds user of control

### 3. Smart Context Compaction

Instead of truncating old messages:
- Analyzes message importance (system, user requests, key results)
- Summarizes middle portions intelligently
- Preserves recent context fully
- Result: More efficient token usage

---

## Extending the ReAct Loop

### Adding New Tools

1. **Register tool in tool registry:**
```python
# opencli/core/tools/registry.py
self.register_tool(
    name="analyze_performance",
    description="Analyze performance bottlenecks in code",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "metrics": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["file_path"]
    },
    function=self._analyze_performance
)
```

2. **Implement tool function:**
```python
def _analyze_performance(self, file_path: str, metrics: list = None):
    """Analyze performance of code file."""
    # Tool implementation
    return {
        "success": True,
        "output": "Performance analysis results..."
    }
```

3. **LLM automatically discovers and uses new tool!**

The ReAct loop doesn't need modification - it dynamically handles any registered tool.

### Adding Safety Checks

Add custom safety checks in the ReAct loop:

```python
# In async_query_processor.py, inside the while loop:

# Custom check: Warn if too many write operations
write_count = sum(1 for tc in tool_calls
                  if tc["function"]["name"] in {"write_file", "edit_file"})
if write_count > 5:
    self.chat_app.add_assistant_message(
        "⚠ Warning: Multiple file writes detected"
    )
```

---

## Comparison with Other Patterns

### Linear Execution (Traditional)
```
User → LLM → Execute all tools → Done
```
- No adaptation
- Can't handle unexpected situations
- Fixed plan

### ReAct (OpenCLI)
```
User → [LLM → Tools → Observe → LLM → Tools → ...] → Done
```
- Adapts based on observations
- Handles unexpected situations
- Dynamic planning

### Chain of Thought (CoT)
```
User → LLM (with reasoning steps) → Done
```
- Pure reasoning, no actions
- Can't interact with environment
- Good for math/logic, not coding

---

## Best Practices

### For Users

1. **Let the agent work**: Don't interrupt unless necessary - the agent often needs multiple iterations
2. **Trust the process**: Agent may explore seemingly unrelated files while understanding context
3. **Use approval wisely**: Option 2 ("don't ask again") creates persistent rules
4. **Monitor context**: Keep eye on token usage in status bar

### For Developers

1. **Tool design**: Make tools focused and composable
2. **Error handling**: Tools should return structured errors the LLM can understand
3. **Safety first**: Add approval for destructive operations
4. **Observability**: Log key decision points for debugging

---

## Debugging the ReAct Loop

### Enable Debug Logging

```python
# In async_query_processor.py, add logging:
import logging
logger = logging.getLogger(__name__)

# In ReAct loop:
logger.debug(f"Iteration {iteration}: {len(tool_calls)} tool calls")
logger.debug(f"Messages history: {len(messages)} messages")
logger.debug(f"Token usage: {calculate_tokens(messages)}")
```

### Common Issues

**Agent gets stuck in loop:**
- Check if tools are returning useful information
- May need to adjust read operation nudging threshold
- Consider lowering SAFETY_LIMIT

**Agent doesn't use tools:**
- Verify tools are registered correctly
- Check system prompt encourages tool usage
- Ensure tool descriptions are clear

**Approval blocks flow:**
- Use approval rules to auto-approve safe commands
- Consider making read-only operations approval-free

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                       User Input                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              AsyncQueryProcessor.process_query           │
│  ┌───────────────────────────────────────────────────┐  │
│  │                   ReAct Loop                      │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────┐    │  │
│  │  │  1. REASONING (_call_llm_with_spinner)  │    │  │
│  │  │     - Show spinner                      │    │  │
│  │  │     - Call LLM with messages           │    │  │
│  │  │     - Get reasoning + tool_calls       │    │  │
│  │  └─────────────────────────────────────────┘    │  │
│  │                      ↓                           │  │
│  │  ┌─────────────────────────────────────────┐    │  │
│  │  │  2. ACTING (_handle_tool_calls)         │    │  │
│  │  │     Phase 1: Collect approvals          │    │  │
│  │  │     Phase 2: Execute tools              │    │  │
│  │  │     - Show progress spinners            │    │  │
│  │  │     - Check interrupts                  │    │  │
│  │  └─────────────────────────────────────────┘    │  │
│  │                      ↓                           │  │
│  │  ┌─────────────────────────────────────────┐    │  │
│  │  │  3. OBSERVING                           │    │  │
│  │  │     - Tool results added to messages    │    │  │
│  │  │     - Display results to user           │    │  │
│  │  └─────────────────────────────────────────┘    │  │
│  │                      ↓                           │  │
│  │          Check: tool_calls present?              │  │
│  │              Yes → Loop    No → Break            │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                      Task Complete                       │
│              Return to REPL Prompt                       │
└─────────────────────────────────────────────────────────┘
```

---

## Conclusion

The ReAct pattern in OpenCLI provides:

✓ **Autonomous operation** - Agent decides its own steps
✓ **Adaptability** - Handles unexpected situations
✓ **Transparency** - User sees each reasoning step
✓ **Control** - Interruptible at any point
✓ **Safety** - Approval for dangerous operations
✓ **Efficiency** - Smart context management
✓ **Extensibility** - Easy to add new tools

This architecture enables OpenCLI to tackle complex coding tasks while maintaining user control and transparency throughout the process.
