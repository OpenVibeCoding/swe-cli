# 🎯 UI/UX Improvement Strategy - Phase 3+

## 📊 Current State Analysis

### ✅ What We Have (Phases 1 & 2)
- Spinner animations (LLM thinking)
- Flashing symbols (tool execution)
- Status line (context bar)
- Interactive approval dialog
- @ file mention autocomplete
- / slash command autocomplete

### 🔍 What Needs Improvement

After analyzing the current REPL output (swecli/repl/repl.py:287-298), I've identified these gaps:

```python
# Current tool output (lines 287-298)
if result["success"]:
    output = result.get("output", "")
    if len(output) > 200:
        display_output = output[:200] + f"... ({len(output)} chars total)"
    else:
        display_output = output if output else "(No output)"
    self.console.print(f"  ⎿  [dim]{display_output}[/dim]")
else:
    error_msg = result.get("error", "Tool execution failed")
    self.console.print(f"  ⎿  [red]Error: {error_msg}[/red]")
```

**Problems:**
1. ❌ Plain text output with no visual hierarchy
2. ❌ Simple truncation (" ... (200 chars total)")
3. ❌ No syntax highlighting for code
4. ❌ No collapsible content for long outputs
5. ❌ Generic error messages
6. ❌ No file tree visualization
7. ❌ No diff display for edits

---

## 🎯 Phase 3: Enhanced Output Formatting

### Priority 1: Tool Output Improvements

#### 1.1 Rich Tool Call Display
**Current:**
```
⏺ write_file(file_path='test.py', content='def hello():\n  ...')
  ⎿  File created successfully (287 bytes)
```

**Target:**
```
╭─ write_file ──────────────────────────────────────────╮
│ 📝 test.py                                            │
│ ✓ Created (287 bytes, 12 lines)                      │
│ [See content ↓]                                       │
╰───────────────────────────────────────────────────────╯
```

#### 1.2 Collapsible Content
**Interaction:**
```
╭─ write_file ──────────────────────────────────────────╮
│ 📝 test.py                                            │
│ ✓ Created (287 bytes, 12 lines)                      │
│ [Press Enter to expand] ↓                            │
╰───────────────────────────────────────────────────────╯

[User presses Enter]

╭─ write_file ─────────────────────────────────────────╮
│ 📝 test.py                                           │
│ ✓ Created (287 bytes, 12 lines)                     │
│                                                       │
│  1 │ def hello():                                    │
│  2 │     print("Hello, World!")                      │
│  3 │                                                  │
│  4 │ if __name__ == "__main__":                      │
│  5 │     hello()                                     │
│                                                       │
│ [Press Enter to collapse] ↑                         │
╰──────────────────────────────────────────────────────╯
```

#### 1.3 Syntax Highlighting
- Use `rich.syntax.Syntax` for code blocks
- Detect language from file extension
- Highlight Python, JS, TypeScript, JSON, etc.

#### 1.4 File Tree Visualization
**For directory operations:**
```
╭─ Created Project Structure ──────────────────────────╮
│                                                       │
│ my_project/                                          │
│ ├── src/                                             │
│ │   ├── __init__.py                                  │
│ │   ├── main.py          (120 lines)                │
│ │   └── utils.py         (45 lines)                 │
│ ├── tests/                                           │
│ │   └── test_main.py     (30 lines)                 │
│ ├── README.md            (15 lines)                 │
│ └── setup.py             (25 lines)                 │
│                                                       │
│ Total: 6 files, 235 lines                           │
╰───────────────────────────────────────────────────────╯
```

#### 1.5 Diff Display
**For file edits:**
```
╭─ edit_file ───────────────────────────────────────────╮
│ 📝 main.py                                            │
│ ✓ Modified (3 additions, 1 deletion)                 │
│                                                        │
│   5 │  def main():                                    │
│ - 6 │      print("Hello")                             │
│ + 6 │      print("Hello, World!")                     │
│ + 7 │      # Added new feature                        │
│ + 8 │      do_something()                             │
│   9 │      return 0                                   │
│                                                        │
╰────────────────────────────────────────────────────────╯
```

---

### Priority 2: Enhanced Error Formatting

#### 2.1 Error Types with Icons
```
╭─ ERROR ───────────────────────────────────────────────╮
│ ❌ File Not Found                                     │
│                                                        │
│ Could not find: /path/to/missing_file.py             │
│                                                        │
│ 💡 Suggestions:                                       │
│   • Check if the file path is correct                │
│   • Create the file first with write_file            │
│   • Use list_directory to see available files        │
│                                                        │
│ Similar files:                                        │
│   • /path/to/existing_file.py                        │
│   • /path/to/another_file.py                         │
╰────────────────────────────────────────────────────────╯
```

#### 2.2 Error Categories
- **File Errors**: ❌ Not found, permission denied, etc.
- **Syntax Errors**: ⚠️ Code parsing issues
- **Runtime Errors**: 🔥 Execution failures
- **Network Errors**: 🌐 Connection issues
- **Validation Errors**: ⚡ Invalid input

#### 2.3 Context-Aware Suggestions
Based on error type, suggest:
- Alternative commands
- How to fix the issue
- Related documentation links

---

### Priority 3: Response Streaming

#### 3.1 Partial Response Display
**Current:** Wait for complete response, then show all at once

**Target:** Show response as it arrives
```
Assistant: I'll create a new feature for you.

First, let me analyze the codebase...
[partial response appears in real-time]

Now I'll create the following files:
[more content streams in]

⏺ write_file(...)
[tool call appears when ready]
```

#### 3.2 Typing Effect
- Smooth character-by-character display
- Configurable speed
- Can skip with Ctrl+C (non-blocking)

---

### Priority 4: Status Line Enhancements

#### 4.1 Real-Time Token Counter
**Current:**
```
────────────────────────────────────────────────
qwen3-coder-480b | ~/project | main | 2.5k/100k
────────────────────────────────────────────────
```

**Target:**
```
────────────────────────────────────────────────────────
qwen3-coder-480b | ~/project | main | 2.5k/100k (2%)
🟢 Active | ⚡ Last: 234 tokens | 💬 This turn: +234
────────────────────────────────────────────────────────
```

#### 4.2 Session Statistics
- Total tokens used
- Average tokens per query
- Cost estimation (if applicable)
- Time spent in session

#### 4.3 Warning Indicators
- 🟢 Normal (< 70% tokens)
- 🟡 Warning (70-85% tokens)
- 🟠 High (85-95% tokens)
- 🔴 Critical (> 95% tokens)

---

### Priority 5: Mode Switching UI

#### 5.1 Enhanced Mode Indicator
**Current:**
```
[NORMAL] >
[PLAN] >
```

**Target:**
```
╭─ NORMAL Mode ─────────────────────────────────────────╮
│ Requires approval for all operations                  │
│ [Ctrl+P to switch to PLAN mode]                       │
╰────────────────────────────────────────────────────────╯

> your input here
```

#### 5.2 Quick Mode Switcher
- **Ctrl+P**: Toggle PLAN mode
- **Ctrl+N**: Toggle NORMAL mode
- Visual feedback when switching

---

## 🚀 Implementation Roadmap

### Phase 3A: Output Formatting (Week 1)
- [ ] Create `OutputFormatter` class
- [ ] Implement rich tool call display
- [ ] Add syntax highlighting for code
- [ ] Add file tree visualization
- [ ] Add diff display for edits

### Phase 3B: Collapsible Content (Week 1)
- [ ] Create `CollapsiblePanel` component
- [ ] Implement expand/collapse logic
- [ ] Add keyboard shortcuts (Enter to toggle)
- [ ] Store expansion state

### Phase 3C: Error Formatting (Week 2)
- [ ] Create `ErrorFormatter` class
- [ ] Categorize error types
- [ ] Add context-aware suggestions
- [ ] Add "similar files" finder

### Phase 3D: Response Streaming (Week 2)
- [ ] Implement streaming response display
- [ ] Add typing effect
- [ ] Make it non-blocking (Ctrl+C to skip)
- [ ] Test with different models

### Phase 3E: Status Line Enhancements (Week 3)
- [ ] Add real-time token counter
- [ ] Add session statistics
- [ ] Add warning indicators
- [ ] Add cost estimation

### Phase 3F: Mode Switching UI (Week 3)
- [ ] Enhanced mode indicator
- [ ] Keyboard shortcuts (Ctrl+P, Ctrl+N)
- [ ] Visual feedback for mode changes

---

## 📐 Technical Architecture

### New Components

```
swecli/ui/
├── __init__.py
├── animations.py          [Existing]
├── status_line.py         [Existing]
├── autocomplete.py        [Existing]
├── formatters.py          [NEW] - OutputFormatter, ErrorFormatter
├── panels.py              [NEW] - CollapsiblePanel, RichToolDisplay
├── streaming.py           [NEW] - StreamingResponse, TypingEffect
└── themes.py              [NEW] - Color schemes, icons

swecli/repl/
├── repl.py                [Modified] - Use new formatters
└── output_manager.py      [NEW] - Manage output state
```

### Key Classes

#### `OutputFormatter`
```python
class OutputFormatter:
    """Formats tool outputs with rich styling."""

    def format_tool_result(
        self,
        tool_name: str,
        result: dict,
        collapsed: bool = True
    ) -> Panel:
        """Format a tool result as a rich panel."""
        # Detect content type
        # Apply syntax highlighting
        # Add expand/collapse controls
        # Return formatted panel
```

#### `CollapsiblePanel`
```python
class CollapsiblePanel:
    """Panel that can be expanded/collapsed."""

    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content
        self.expanded = False

    def toggle(self):
        """Toggle expansion state."""

    def render(self) -> Panel:
        """Render panel based on current state."""
```

#### `ErrorFormatter`
```python
class ErrorFormatter:
    """Formats errors with context and suggestions."""

    def format_error(
        self,
        error_type: str,
        message: str,
        context: dict
    ) -> Panel:
        """Format error with suggestions."""
        # Categorize error
        # Generate suggestions
        # Find similar files/commands
        # Return formatted panel
```

#### `StreamingResponse`
```python
class StreamingResponse:
    """Display response as it streams in."""

    def start_streaming(self, initial_text: str = ""):
        """Start streaming display."""

    def append(self, text: str):
        """Append text to display."""

    def complete(self):
        """Mark streaming as complete."""
```

---

## 🎨 Design Principles

### 1. **Progressive Disclosure**
- Show summary by default
- Allow expansion for details
- Never overwhelm with information

### 2. **Visual Hierarchy**
- Use boxes/panels for structure
- Icons for quick recognition
- Color coding for status

### 3. **Responsive Feedback**
- Real-time updates
- Smooth animations
- Non-blocking interactions

### 4. **Helpful Errors**
- Clear problem description
- Actionable suggestions
- Related information

---

## 📊 Success Metrics

### User Experience
- ✅ Easier to scan outputs
- ✅ Faster to understand results
- ✅ Better error recovery
- ✅ More professional appearance

### Developer Experience
- ✅ Modular, reusable components
- ✅ Easy to extend
- ✅ Well-tested
- ✅ Good documentation

### Performance
- ✅ < 50ms formatting overhead
- ✅ Smooth streaming (no lag)
- ✅ Minimal memory impact
- ✅ Responsive UI even with large outputs

---

## 🎯 Phase 4+ Ideas

### Advanced Features (Future)
- [ ] **Custom Themes**: User-configurable color schemes
- [ ] **Output History**: Scroll back through previous outputs
- [ ] **Export Outputs**: Save formatted outputs to files
- [ ] **Rich Diffs**: Side-by-side diff view
- [ ] **Interactive Prompts**: Choose from multiple options
- [ ] **Progress Bars**: For batch operations
- [ ] **Notifications**: System notifications for long operations
- [ ] **Session Replay**: Replay past sessions
- [ ] **Collaborative Mode**: Share sessions with team
- [ ] **Voice Commands**: Voice input support

---

## 📝 Next Steps

### Immediate Actions (This Session)
1. Start with Priority 1: Tool Output Improvements
2. Create `OutputFormatter` class
3. Implement rich tool call display
4. Add syntax highlighting
5. Test with real examples

### Short Term (Next Week)
- Complete Phase 3A (Output Formatting)
- Complete Phase 3B (Collapsible Content)
- Create comprehensive tests

### Medium Term (Next Month)
- Complete all of Phase 3
- User testing and feedback
- Iteration based on feedback

---

## 💡 Inspiration Sources

### Claude Code Features to Match:
- ✅ Spinner animations
- ✅ Tool execution feedback
- ✅ Status line
- ✅ @ mentions
- ✅ / commands
- ⏳ Collapsible content
- ⏳ Rich tool outputs
- ⏳ Response streaming
- ⏳ Enhanced error messages

### Modern CLI Tools:
- **gh cli**: Rich formatting, interactive prompts
- **lazygit**: TUI with keyboard navigation
- **htop**: Real-time updates, color coding
- **fzf**: Fast fuzzy finding
- **bat**: Syntax highlighting, git integration

---

Let's build the most polished AI coding assistant CLI! 🚀
