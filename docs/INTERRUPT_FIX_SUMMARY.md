# ESC Interrupt Feature - Complete Fix Summary

## Problem Statement
The ESC key interrupt feature was not working correctly in the Textual UI:
1. Pressing ESC during tool execution did not stop the process
2. When interruption did work, the display format was incorrect (showing "⏺ ❌ Interrupted by user")
3. The agent would continue executing remaining tools even after interruption

## Desired Behavior
- Pressing ESC should immediately stop all execution (LLM calls and tool execution)
- Display should show:
  ```
  ⏺ Run(command)
    ⎿  Interrupted by user - What should I do instead?
  ```
  with the interruption message in **bold red text** (no ❌ icon)

## Root Causes Identified

### Issue 1: Blocking subprocess execution
- `BashTool.execute()` used `subprocess.run()` which blocks without checking for interrupts
- No way to signal the subprocess to stop mid-execution

### Issue 2: ESC key not propagating to task monitor
- In Textual UI, ESC is captured by Textual's key bindings, not pynput
- `action_interrupt()` only updated UI state but didn't signal the running task
- No connection between UI interrupt and `TaskMonitor.request_interrupt()`

### Issue 3: Agent loop continuation
- Even when one tool was interrupted, the agent continued to:
  - Execute remaining tools in the current iteration
  - Make new LLM calls
  - Start new iterations

### Issue 4: Display formatting
- Interrupted errors used `::tool_error::` sentinel
- `conversation_log.py` strips this sentinel and shows ❌ icon
- ANSI color codes don't work through Textual's rendering pipeline

## Solution Implemented

### 1. Non-blocking subprocess with interrupt polling
**File**: `swecli/tools/bash_tool.py`

Replaced `subprocess.run()` with `subprocess.Popen()` + polling loop:

```python
process = subprocess.Popen(
    command,
    shell=True,
    stdout=subprocess.PIPE if capture_output else None,
    stderr=subprocess.PIPE if capture_output else None,
    text=True,
    cwd=str(work_dir),
    env=env,
)

poll_interval = 0.1  # Check every 100ms
while process.poll() is None:
    # Check for interrupt
    if task_monitor is not None and task_monitor.should_interrupt():
        try:
            process.terminate()
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        return BashResult(
            success=False,
            command=command,
            exit_code=-1,
            stdout="",
            stderr="Command interrupted by user",
            duration=time.time() - start_time,
            error="Command interrupted by user",
            operation_id=operation.id if operation else None,
        )

    time.sleep(poll_interval)
```

### 2. Task monitor propagation chain
**Files**:
- `swecli/core/tools/context.py` - Added `task_monitor` parameter
- `swecli/core/tools/registry.py` - Pass `task_monitor` to context
- `swecli/core/tools/process_handlers.py` - Pass to `BashTool.execute()`

### 3. UI interrupt callback wiring
**Files**:
- `swecli/repl/query_processor.py`:
  - Added `_current_task_monitor` tracking
  - Implemented `request_interrupt()` method
  - Set/clear monitor in try/finally blocks around LLM calls and tool execution

- `swecli/ui_textual/chat_app.py`:
  - Added `on_interrupt` callback parameter
  - Call callback in `action_interrupt()` when ESC is pressed

- `swecli/ui_textual/runner.py`:
  - Implemented `_handle_interrupt()` method
  - Wired to app via `on_interrupt` parameter

### 4. Agent loop interrupt checks
**File**: `swecli/repl/query_processor.py`

Added interrupt checking at strategic points:

```python
# At start of each agent iteration
if self._current_task_monitor and self._current_task_monitor.should_interrupt():
    self.console.print("\n[red]⚠ Interrupted by user - stopping execution[/red]")
    return (self._last_operation_summary, "Interrupted by user", self._last_latency_ms)

# Before each tool execution
for tool_call in tool_calls:
    if self._current_task_monitor and self._current_task_monitor.should_interrupt():
        self.console.print("\n[red]⚠ Interrupted by user - stopping execution[/red]")
        return (self._last_operation_summary, "Interrupted by user", self._last_latency_ms)

    result = self._execute_tool_call(...)
```

### 5. Display formatting with special marker
**File**: `swecli/ui_textual/formatters/style_formatter.py`

Created new `_interrupted_line()` method:

```python
@staticmethod
def _interrupted_line(message: str) -> str:
    """Format an interrupted command message in red without error sentinel.

    Uses special ::interrupted:: marker instead of ::tool_error:: to avoid
    showing the ❌ icon in the conversation log.
    """
    return f"::interrupted:: {message.strip()}"
```

Updated all tool formatters to detect "interrupted" errors:

```python
if not result.get("success"):
    error_msg = result.get("error", "Unknown error")
    if "interrupted" in error_msg.lower():
        return [self._interrupted_line("Interrupted by user - What should I do instead?")]
    return [self._error_line(error_msg)]
```

**File**: `swecli/ui_textual/widgets/conversation_log.py`

Added handling for `::interrupted::` marker:

```python
def _write_generic_tool_result(self, text: str) -> None:
    lines = text.rstrip("\n").splitlines() or [text]
    grey = "#a0a4ad"
    for raw_line in lines:
        line = Text("  ⎿  ", style=grey)
        message = raw_line.rstrip("\n")
        is_error = False
        is_interrupted = False

        if message.startswith(TOOL_ERROR_SENTINEL):
            is_error = True
            message = message[len(TOOL_ERROR_SENTINEL):].lstrip()
        elif message.startswith("::interrupted::"):
            is_interrupted = True
            message = message[len("::interrupted::"):].lstrip()

        if is_interrupted:
            line.append(message, style="bold red")  # Bold red, no ❌
        else:
            line.append(message, style="red" if is_error else grey)
        self.write(line)
```

## Files Modified

1. `swecli/core/tools/context.py` - Added task_monitor parameter
2. `swecli/core/tools/registry.py` - Pass task_monitor through
3. `swecli/core/tools/process_handlers.py` - Pass to BashTool
4. `swecli/tools/bash_tool.py` - Non-blocking execution with polling
5. `swecli/repl/query_processor.py` - Task monitor tracking and interrupt checks
6. `swecli/ui_textual/chat_app.py` - Interrupt callback support
7. `swecli/ui_textual/runner.py` - Interrupt handler implementation
8. `swecli/ui_textual/formatters/style_formatter.py` - Special interrupted formatting
9. `swecli/ui_textual/widgets/conversation_log.py` - ::interrupted:: marker handling

## Tests Created

1. `tests/test_interrupt_bash.py` - Verifies subprocess interruption works
   - ✅ Command interrupted within 1 second (not 30 seconds)
   - ✅ Error message: "Command interrupted by user"
   - ✅ Exit code: -1

2. `tests/test_interrupt_display.py` - Verifies display formatting
   - ✅ Uses `::interrupted::` marker (not `::tool_error::`)
   - ✅ Contains "Interrupted by user - What should I do instead?"
   - ✅ No ❌ icon in the marker

## Expected Result

When user presses ESC during tool execution:

1. **Subprocess terminates immediately** (within ~100ms polling interval)
2. **Agent stops executing** (doesn't continue with remaining tools or LLM calls)
3. **Display shows**:
   ```
   ⏺ Run(command)
     ⎿  Interrupted by user - What should I do instead?
   ```
   - First line: Tool call with ⏺ symbol
   - Second line: Interrupted message in **bold red text**
   - **No ❌ error icon** displayed

## Verification Steps

1. Start swecli in Textual UI mode
2. Run a long command (e.g., `run sleep 30`)
3. Press ESC immediately
4. Verify:
   - Command stops within 1 second
   - Display format matches expected format
   - Message is in bold red without ❌ icon
   - Agent doesn't continue with other actions

## Git Commits

- `1f8ec6c` - feat: implement interrupt support for tool execution
- `a2384d0` - feat: wire ESC key to interrupt running tasks in Textual UI
- (pending) - fix: use ::interrupted:: marker for correct display formatting
