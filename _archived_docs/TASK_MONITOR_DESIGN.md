# Task Monitor Design - ESC Interrupt, Timer, Token Tracking

## Requirements

Implement a task display similar to Claude Code:
```
· Compacting conversation… (esc to interrupt · 58s · ↓ 3.7k tokens)
```

### Features Required:
1. **ESC Key Interruption**: User can press ESC to interrupt long-running operations
2. **Real-time Timer**: Shows elapsed seconds during task execution
3. **Token Counter**: Shows token usage changes (↓ for decrease, ↑ for increase)
4. **Format**: `· Task description… (esc to interrupt · XXs · ↓/↑ XXk tokens)`

---

## Architecture Design

### 1. Core Components

#### A. `TaskMonitor` Class (Logic)
**Location**: `opencli/core/task_monitor.py`

**Responsibilities**:
- Track elapsed time
- Track token usage (before/after)
- Manage interrupt flag
- Calculate token delta
- Thread-safe state management

**Key Methods**:
```python
class TaskMonitor:
    def start(self, task_description: str) -> None
    def update_tokens(self, tokens_used: int, tokens_gained: int = 0) -> None
    def request_interrupt(self) -> None
    def should_interrupt(self) -> bool
    def stop(self) -> dict  # Returns stats
    def get_elapsed_seconds(self) -> int
    def get_token_delta(self) -> tuple[str, int]  # ("↓" or "↑", count)
```

#### B. `TaskProgressDisplay` Class (UI)
**Location**: `opencli/ui/task_progress.py`

**Responsibilities**:
- Display task with live updates
- Listen for ESC key press
- Update timer every second
- Format token display (e.g., 3.7k)
- Use Rich Live for dynamic updates

**Display Format**:
```
· Processing request… (esc to interrupt · 23s · ↓ 1.2k tokens)
```

**Key Methods**:
```python
class TaskProgressDisplay:
    def __init__(self, console: Console, task_monitor: TaskMonitor)
    def start(self, task_description: str) -> None
    def stop(self) -> None
    def _update_loop(self) -> None  # Background thread
    def _format_display(self) -> Text  # Rich Text formatting
```

---

### 2. Integration Points

#### A. LLM API Calls
**File**: `opencli/repl/repl.py`

**Current flow**:
```python
thinking_verb = random.choice(self.THINKING_VERBS)
self.spinner.start(f"{thinking_verb}...")
response = self.agent.call_llm(messages)
self.spinner.stop()
```

**New flow**:
```python
thinking_verb = random.choice(self.THINKING_VERBS)
task_monitor = TaskMonitor()
progress_display = TaskProgressDisplay(self.console, task_monitor)
progress_display.start(f"{thinking_verb}")

response = self.agent.call_llm(messages, task_monitor=task_monitor)

progress_display.stop()
stats = task_monitor.stop()
# Show final stats if needed
```

#### B. Tool Execution
**File**: `opencli/repl/repl.py`

**Current flow**:
```python
if self.mode_manager.current_mode == OperationMode.PLAN:
    self.spinner.start(llm_description)
    result = self.tool_registry.execute_tool(...)
    self.spinner.stop()
```

**New flow**:
```python
if self.mode_manager.current_mode == OperationMode.PLAN:
    task_monitor = TaskMonitor()
    progress_display = TaskProgressDisplay(self.console, task_monitor)
    progress_display.start(llm_description)

    result = self.tool_registry.execute_tool(..., task_monitor=task_monitor)

    progress_display.stop()
    stats = task_monitor.stop()
```

---

### 3. Token Tracking

#### Source of Token Data

**Option 1: LLM Response Metadata**
Most LLM APIs return token usage in response:
```python
{
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 80,
        "total_tokens": 230
    }
}
```

**Option 2: Conversation History**
Track tokens in conversation:
- Before: Total tokens in history
- After: Total tokens after adding response
- Delta: Difference

**Option 3: Manual Tracking**
Use tiktoken or similar library to estimate:
```python
import tiktoken
encoder = tiktoken.encoding_for_model("gpt-4")
tokens = len(encoder.encode(text))
```

**Recommended**: Use Option 1 (LLM response metadata) as primary source, fallback to Option 3 for estimation.

#### Token Display Format

```python
def format_tokens(count: int) -> str:
    """Format token count (e.g., 3700 -> 3.7k)"""
    if count >= 1000:
        return f"{count / 1000:.1f}k"
    return str(count)

def get_token_arrow(delta: int) -> str:
    """Get arrow direction for token change"""
    if delta < 0:
        return "↓"  # Tokens reduced (compression)
    elif delta > 0:
        return "↑"  # Tokens increased (expansion)
    return "·"  # No change
```

---

### 4. ESC Key Interrupt Implementation

#### Keyboard Listener

Use `pynput` library for cross-platform keyboard listening:

```python
from pynput import keyboard

class TaskProgressDisplay:
    def _start_keyboard_listener(self):
        def on_press(key):
            try:
                if key == keyboard.Key.esc:
                    self.task_monitor.request_interrupt()
            except AttributeError:
                pass

        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        return listener
```

#### Interrupt Handling

**In LLM calls**:
```python
# Check interrupt flag during streaming
for chunk in stream:
    if task_monitor.should_interrupt():
        raise InterruptedError("Task interrupted by user")
    # Process chunk
```

**In tool execution**:
```python
# Check interrupt flag before/during operations
if task_monitor.should_interrupt():
    return {"success": False, "error": "Interrupted by user"}
```

---

### 5. Display Format Examples

#### During LLM API Call
```
· Orchestrating… (esc to interrupt · 5s · ↑ 2.3k tokens)
```

#### During Tool Execution
```
· Writing file hello.py… (esc to interrupt · 12s · ↓ 450 tokens)
```

#### After Completion
```
⏺ Orchestrating (completed in 23s, ↑ 3.7k tokens)
```

#### After Interruption
```
⏹ Orchestrating (interrupted after 15s)
```

---

## Implementation Steps

### Phase 1: Core Logic
1. Create `TaskMonitor` class in `opencli/core/task_monitor.py`
2. Implement timer tracking
3. Implement token tracking
4. Implement interrupt flag management

### Phase 2: UI Component
1. Create `TaskProgressDisplay` class in `opencli/ui/task_progress.py`
2. Implement Rich Live display
3. Implement ESC key listener
4. Implement real-time updates (1 second intervals)
5. Implement token formatting

### Phase 3: Integration
1. Add token tracking to LLM calls in `pydantic_agent.py`
2. Replace spinner with TaskProgressDisplay in REPL
3. Pass task_monitor to tool execution
4. Handle interruption gracefully

### Phase 4: Testing
1. Test ESC interruption
2. Test timer accuracy
3. Test token tracking
4. Test display formatting
5. Test with long-running operations

---

## Technical Considerations

### Dependencies
- `pynput`: For keyboard listening (ESC key)
- `rich`: Already used for UI (Live updates)
- `threading`: For background timer updates
- `time`: For elapsed time tracking

### Thread Safety
- Use `threading.Lock` for shared state
- Ensure interrupt flag is atomic
- Protect token counts during updates

### Performance
- Update display every 1 second (not faster)
- Use background thread for updates
- Minimize overhead during operations

### Error Handling
- Graceful degradation if keyboard listener fails
- Handle interrupted operations cleanly
- Show appropriate error messages

---

## Future Enhancements

### Optional Features
1. **Progress Percentage**: For operations with known total
   ```
   · Processing files… (esc to interrupt · 23s · 45% · ↑ 1.2k tokens)
   ```

2. **Configurable Display**: User preferences for display format
   ```python
   [ui]
   show_timer = true
   show_tokens = true
   show_interrupt_hint = true
   ```

3. **Multiple Task Tracking**: Stack of tasks for nested operations
   ```
   · Orchestrating… (5 tasks in progress)
     └─ Writing file… (esc to interrupt · 3s)
   ```

4. **Historical Stats**: Track all operations in session
   ```
   Session: 15 operations, 45m total, ↑ 25.3k tokens
   ```

---

## Example Output Flows

### Successful LLM Call
```
· Thinking… (esc to interrupt · 1s · ↑ 0 tokens)
· Thinking… (esc to interrupt · 2s · ↑ 150 tokens)
· Thinking… (esc to interrupt · 3s · ↑ 230 tokens)
⏺ Thinking (completed in 3s, ↑ 230 tokens)
```

### Interrupted Operation
```
· Processing request… (esc to interrupt · 5s · ↑ 1.2k tokens)
· Processing request… (esc to interrupt · 10s · ↑ 2.4k tokens)
[User presses ESC]
⏹ Processing request (interrupted after 10s)
```

### Tool Execution
```
· Now I'll write the file for you… (esc to interrupt · 1s)
· Now I'll write the file for you… (esc to interrupt · 2s)
⏺ Now I'll write the file for you (completed in 2s)
```

---

## Summary

This design provides:
- ✅ ESC key interruption for long operations
- ✅ Real-time timer showing elapsed seconds
- ✅ Token tracking with delta display
- ✅ Professional display format
- ✅ Thread-safe implementation
- ✅ Graceful error handling
- ✅ Minimal performance overhead

The implementation replaces the current spinner with a more sophisticated task monitoring system that gives users better visibility and control over operations.
