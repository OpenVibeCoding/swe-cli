# OpenCLI UI/UX Improvement Strategy
## Inspired by Claude Code's Design Philosophy

> **Goal**: Transform OpenCLI into an elegant, minimal, highly usable CLI tool with Claude Code-level UX

---

## 🎯 Core Design Principles

### 1. **Minimal & Functional**
- Clean, uncluttered interface
- Information only when needed
- Progressive disclosure over information overload
- Monochrome-first design (minimal colors)

### 2. **Consistent Visual Language**
- Use consistent symbols throughout
- Maintain visual hierarchy
- Clear separation between reasoning, actions, and observations

### 3. **Smart Content Management**
- Intelligent truncation
- Collapsible sections
- Context-aware display

---

## 📊 Current State Analysis

### ❌ Problems with Current UI

1. **Approval Boxes**
   ```
   ╭────────────────── Operation: file_write ──────────────────╮
   │ import pygame                                             │
   │ import random                                             │
   │ ...500 more lines...                                      │
   ╰───────────────────────────────────────────────────────────╯
   ```
   - Too large and intrusive
   - Shows entire file content
   - Poor UX for multi-step tasks

2. **Tool Output Display**
   ```
   ⏺ read_file(file_path='money_saver_app/main.py')
     ⎿  #!/usr/bin/env python3
   """
   Money Saver App - Main Application File
   """
   ... (551 chars total)
   ```
   - Basic truncation
   - No collapsible sections
   - Hard to navigate long outputs

3. **No Status Line**
   - Missing context: model, directory, tokens
   - No git branch info
   - No operation progress

4. **Token Display**
   ```
   Tokens: 189/100000
   ```
   - Too simple
   - Not integrated into status line

5. **Error Messages**
   - Plain text errors
   - No formatting hierarchy
   - Missing actionable suggestions

---

## ✨ Improvement Strategy

### Phase 1: Enhanced Tool Display (Week 1)

#### 1.1 Collapsible Content System
```
⏺ Read(file.py)
  ⎿  import os
     import sys
     … +245 lines (ctrl+o to expand)

⏺ Write(tetris.py)
  ⎿  Created 287 lines (ctrl+o to view)
```

**Implementation:**
- Add `(ctrl+o to expand)` for truncated content
- Store full output in memory with unique IDs
- Keyboard handler for `ctrl+o` expansion
- Smart truncation based on content type

#### 1.2 Smart Truncation Rules

| Content Type | Display Strategy |
|--------------|------------------|
| File reads < 50 lines | Show first 10 + last 5 lines |
| File reads > 50 lines | Show first 5 lines + count |
| Command output | Show first 15 lines + preview |
| File writes | Show file info + line count |
| Diffs | Show changed sections only |

#### 1.3 Enhanced Symbol Set

**Static Symbols:**
```
⏺  Tool call completed
⎿  Tool result/observation
✓  Successful operation
✗  Failed operation
⚠  Warning/caution needed
💭 Agent reasoning
📝 File modified
➜  Next action
```

**Animated Symbols (for active operations):**
```
⏺ → ⏵ → ▶ → ⏵ → ⏺  (flashing during execution)
⠋ → ⠙ → ⠹ → ⠸ → ⠼ → ⠴ → ⠦ → ⠧ → ⠇ → ⠏  (spinner for thinking)
```

#### 1.4 Loading States & Progress Indicators

**Critical UX Principle**: *Never leave the user wondering if something is happening*

##### State 1: Model Thinking (API Call in Progress)
```
Assistant:

⠋ Thinking...
```

- Animated spinner (10 frames, 80ms each)
- Shows immediately after user hits Enter
- Replaces with actual response when model responds
- Subtle, non-intrusive

**Animation frames:**
```
Frame 1:  ⠋ Thinking...
Frame 2:  ⠙ Thinking...
Frame 3:  ⠹ Thinking...
Frame 4:  ⠸ Thinking...
Frame 5:  ⠼ Thinking...
Frame 6:  ⠴ Thinking...
Frame 7:  ⠦ Thinking...
Frame 8:  ⠧ Thinking...
Frame 9:  ⠇ Thinking...
Frame 10: ⠏ Thinking...
```

##### State 2: Tool Execution in Progress
```
⏵ write_file(game.py, ...)  ← flashing
```

- Symbol pulses while tool executes
- Locks to solid ⏺ when complete
- Shows elapsed time for long operations (>2s)

**Animation pattern:**
```
Frame 1:  ⏺ write_file(...)      (solid)
Frame 2:  ⏵ write_file(...)      (hollow)
Frame 3:  ▷ write_file(...)      (outline)
Frame 4:  ⏵ write_file(...)      (hollow)
[repeat every 250ms]
```

##### State 3: Multi-Step Operations
```
Writing 3 files...
  ⏵ game.py (in progress)          ← flashing
  ○ config.py (pending)             ← dim
  ○ utils.py (pending)              ← dim
```

**Progress visualization:**
```
# Step 1 complete
  ✓ game.py
  ⏵ config.py (in progress)        ← now flashing
  ○ utils.py (pending)

# All complete
  ✓ game.py
  ✓ config.py
  ✓ utils.py
```

##### State 4: Long-Running Commands
```
⏵ run_command(python test.py)

  Running tests... (3s elapsed)
  [⠏ Still running...]
```

**Features:**
- Show elapsed time after 2 seconds
- Update every second
- Spinner + timer for operations >5s
- Timeout warning at 80% of limit

##### State 5: Batch Operations with Progress Bar
```
Processing 12 files...

[████████░░░░░░] 8/12 (66%)  ⏵ analyzing utils.py

Elapsed: 4s | Est. remaining: 2s
```

**When to use:**
- Operations on >5 items
- Predictable total count
- Each item takes >0.5s

---

### Phase 1.5: Animation System (Week 1.5)

#### Implementation Architecture

```python
# opencli/ui/animations.py

class Spinner:
    """Animated spinner for loading states"""
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    INTERVAL = 0.08  # 80ms per frame

    def start(self, message: str):
        """Start spinner with message"""
        # Use rich.Live for smooth updates

    def stop(self, final_message: str = None):
        """Stop and replace with final message"""

class FlashingSymbol:
    """Pulsing symbol for active operations"""
    FRAMES = ["⏺", "⏵", "▷", "⏵"]  # pulse pattern
    INTERVAL = 0.25  # 250ms per frame

    def animate_tool_call(self, tool_name: str):
        """Show flashing symbol during tool execution"""

class ProgressBar:
    """Progress bar for batch operations"""

    def update(self, current: int, total: int, message: str):
        """Update progress display"""

    def complete(self):
        """Mark as complete"""
```

#### Usage Examples

**Example 1: Model Thinking**
```python
# In REPL when calling LLM
with console.status("⠋ Thinking...", spinner="dots"):
    response = agent.call_llm(messages)
# Spinner automatically stops and is replaced by response
```

**Example 2: Tool Execution**
```python
# Show tool call with flashing symbol
flash = FlashingSymbol(console)
flash.start(f"⏺ {tool_name}({args})")

# Execute tool
result = execute_tool(...)

# Stop flashing, show result
flash.stop()
console.print(f"⏺ {tool_name}({args})")
console.print(f"  ⎿  {result}")
```

**Example 3: Long Command**
```python
# For commands that might take time
with TimedOperation(console, "⏺ run_command(pytest)") as op:
    result = subprocess.run(...)
    # If >2s, shows elapsed time
    # If >5s, shows spinner + timer
```

#### Animation Rules

1. **Spinner (Thinking)**
   - Show: When waiting for LLM response
   - Hide: As soon as first token arrives
   - Fallback: Static "Thinking..." after 30s

2. **Flashing Symbol (Executing)**
   - Show: During tool execution
   - Hide: When tool returns result
   - Frequency: 4 Hz (250ms intervals)

3. **Progress Bar**
   - Show: For >5 items or >3s operations
   - Update: Every 100ms or per item
   - Format: `[████░░] 8/12 (66%)`

4. **Elapsed Time**
   - Show: After 2 seconds of operation
   - Update: Every second
   - Format: `(3s elapsed)`

5. **Estimated Time**
   - Show: When >50% complete AND predictable
   - Format: `Est. 2s remaining`

---

### Phase 2: Smart Approval System (Week 2)

#### 2.1 Minimal Approval Prompt

**Before (Current):**
```
╭───────────── Operation: file_write ─────────────╮
│ [500 lines of content shown]                   │
╰─────────────────────────────────────────────────╯

Approve? [y/n/e/a/q]
  y - Yes, approve
  n - No, skip
  e - Edit first
  a - Approve all remaining
  q - Quit and cancel
```

**After (Improved):**
```
⏺ Write(src/game.py)
  287 lines, 8.2KB (ctrl+o to preview)

  [y]es  [n]o  [e]dit  [a]ll  [q]uit  [?] →
```

**Benefits:**
- 90% less visual space
- One-line prompt
- Still shows file info
- Expandable on demand

#### 2.2 Batch Approval Intelligence
```
⏺ Multiple operations detected (3 files)
  • Write(game.py) - 287 lines
  • Write(config.py) - 45 lines
  • Write(utils.py) - 123 lines

  [a]pprove all  [r]eview each  [c]ancel →
```

---

### Phase 3: Status Line System (Week 3)

#### 3.1 Bottom Status Bar

```
──────────────────────────────────────────────────
qwen3-coder-480b | ~/project | main | 2.3k/100k
──────────────────────────────────────────────────
```

**Components:**
- Model name (truncated)
- Working directory (smart path display)
- Git branch (if in repo)
- Token usage (used/limit)

**Features:**
- Always visible at bottom
- Auto-updates after each turn
- Customizable via config
- Color-coded warnings (>80% tokens)

#### 3.2 Progress Indicators
```
⏺ Writing 5 files...
  ✓ game.py
  ✓ config.py
  ⋯ utils.py (in progress)
  ○ tests.py
  ○ README.md
```

---

### Phase 4: Enhanced Content Formatting (Week 4)

#### 4.1 Diff Display

**Before:**
```
[Shows raw diff output]
```

**After:**
```
⏺ Edit(config.py:15)
  ⎿  Changed 1 line:

     - timeout = 30
     + timeout = 60

     ✓ Applied successfully
```

#### 4.2 Error Formatting

**Before:**
```
Error: File not found
```

**After:**
```
✗ File not found: config.yaml

  Suggestions:
  • Did you mean: config.yml?
  • Create file: opencli write config.yaml
  • Check path: ls -la | grep config
```

#### 4.3 File Tree Display
```
⏺ List(src/)
  ⎿  src/
     ├─ models/
     │  ├─ user.py (125 lines)
     │  └─ transaction.py (87 lines)
     ├─ ui/
     │  └─ console.py (234 lines)
     └─ utils/
        └─ helpers.py (56 lines)

     4 files, 502 total lines
```

---

### Phase 5: Interactive Features (Week 5)

#### 5.1 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `ctrl+o` | Expand last truncated output |
| `ctrl+c` | Cancel current operation |
| `ctrl+d` | Show detailed info |
| `↑/↓` | Navigate history |
| `tab` | Auto-complete commands |

#### 5.2 Expandable History
```
> create a game

⏺ Read(examples/games.py) [1m ago]
⏺ Write(game.py) [30s ago]
⏺ Run(python game.py) [5s ago]

Press ↑ to expand any operation
```

---

## 🎨 Visual Design System

### Color Palette (Minimal)

| Element | Color | Usage |
|---------|-------|-------|
| Tool calls | Cyan | `⏺ tool_name()` |
| Success | Green | `✓ Done` |
| Error | Red | `✗ Failed` |
| Warning | Yellow | `⚠ Caution` |
| Thinking | Dim | `💭 Planning...` |
| Results | Dim | `⎿ output` |
| Normal text | Default | Assistant messages |

**Rule**: Use colors sparingly, only for status/meaning

### Typography Hierarchy

```
1. Assistant Messages (Normal weight)
   Plain text explanations

2. Tool Calls (Cyan + Symbol)
   ⏺ tool_name(args)

3. Results (Dim + Indent)
     ⎿ output text

4. Status (Dim + Small)
     model | dir | tokens
```

---

## 🔧 Technical Implementation Plan

### Dependencies
- `rich` (current) - Keep for basic formatting
- `prompt_toolkit` (current) - Keep for input
- Add: `textual` (optional) - For advanced TUI features

### File Structure
```
opencli/ui/
├── __init__.py
├── display.py          # Core display logic
├── status_line.py      # Status bar component
├── formatters.py       # Content formatters
├── truncator.py        # Smart truncation
├── expander.py         # Collapsible content
└── themes.py           # Theme system
```

### Key Classes

```python
class DisplayManager:
    """Central UI manager"""
    - render_tool_call()
    - render_observation()
    - render_approval()
    - update_status_line()

class ContentTruncator:
    """Smart content truncation"""
    - truncate_file()
    - truncate_output()
    - truncate_diff()

class ExpandableContent:
    """Manage expandable sections"""
    - register_content()
    - expand_by_id()
    - keyboard_handler()

class StatusLine:
    """Bottom status bar"""
    - format_status()
    - update_tokens()
    - update_git_info()
```

---

## 📈 Success Metrics

### Measurable Improvements

1. **Visual Clarity**
   - Reduce screen space per operation by 70%
   - Max 5 lines per tool call (expandable)

2. **User Efficiency**
   - Batch approval for multi-file operations
   - One-key approvals (y/n/a)
   - Quick access to details (ctrl+o)

3. **Information Density**
   - Always-visible status line
   - Smart truncation preserves context
   - Progressive disclosure

4. **Professional Aesthetics**
   - Minimal color usage
   - Consistent symbol language
   - Clean spacing and alignment

---

## 🗓️ Implementation Timeline

### Week 1: Foundation
- [ ] Create `opencli/ui/` module structure
- [ ] Implement `DisplayManager` class
- [ ] Add collapsible content system
- [ ] Smart truncation for common content types

### Week 2: Approval System
- [ ] Redesign approval prompts (minimal)
- [ ] Add batch approval support
- [ ] Implement content preview (ctrl+o)
- [ ] One-key approval shortcuts

### Week 3: Status Line
- [ ] Implement bottom status bar
- [ ] Add token counter integration
- [ ] Git branch detection
- [ ] Model/directory display

### Week 4: Content Formatting
- [ ] Enhanced diff display
- [ ] Better error formatting
- [ ] File tree visualization
- [ ] Progress indicators

### Week 5: Polish & Testing
- [ ] Keyboard shortcuts (ctrl+o, etc.)
- [ ] Theme customization
- [ ] User testing
- [ ] Documentation

---

## 🎯 Quick Wins (Priority)

Start with these high-impact, low-effort improvements:

1. **Minimal approval prompts** (2 days)
   - One-line format
   - File info without full content

2. **Collapsible tool output** (3 days)
   - "ctrl+o to expand" system
   - Store truncated content

3. **Status line** (3 days)
   - Simple bottom bar
   - Model + tokens + directory

4. **Better tool call display** (2 days)
   - Cleaner formatting
   - Consistent symbols

**Total: ~10 days for 80% improvement**

---

## 🔄 Iterative Approach

### Phase 0: Quick Prototype (3 days)
Create proof-of-concept for:
- Minimal approval prompt
- Collapsible content
- Status line

**Goal**: Validate design direction

### Phase 1-5: As detailed above (5 weeks)

### Phase 6: Community Feedback (1 week)
- Beta testing
- Gather feedback
- Iterate on design

---

## 📚 Reference Examples

### Claude Code Style
```
⏺ Read(main.py)
  ⎿  Read 245 lines (ctrl+o to expand)

⏺ Write(config.py)
  ⎿  Created 67 lines

Done! The configuration is now set up.

──────────────────────────────────────────
claude-sonnet-4 | ~/project | main | 5k/200k
──────────────────────────────────────────
```

### OpenCLI Target Style
```
I'll update the configuration file for you.

⏺ read_file(config.py)
  ⎿  67 lines, 2.1KB (ctrl+o to view)

The timeout is currently 30 seconds. I'll increase it to 60.

⏺ edit_file(config.py:15)
  ⎿  - timeout = 30
     + timeout = 60
     ✓ Applied

Done! Configuration updated.

──────────────────────────────────────────
qwen3-coder | ~/opencli | main | 3k/100k
──────────────────────────────────────────
```

---

## 🚀 Getting Started

1. Review this document with the team
2. Prioritize features (vote on quick wins)
3. Create GitHub issues for each phase
4. Start with Week 1 prototype
5. Iterate based on feedback

**Next Step**: Implement the `DisplayManager` class and minimal approval prompt as proof-of-concept.
