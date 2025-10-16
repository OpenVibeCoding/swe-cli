# 🎨 Elegant Autocomplete Design Plan

## 🎯 Design Philosophy

**Goal:** Make autocomplete feel native, elegant, and naturally integrated with the terminal - no flashy icons, just clean, professional design.

### Design Principles
- ✅ Minimalist and clean
- ✅ Natural terminal integration
- ✅ Subtle, not flashy
- ✅ Good typography and spacing
- ✅ Elegant use of terminal colors
- ✅ Feels like it belongs in the terminal

### What We DON'T Want
- ❌ Icons and emojis (📚 🐍 etc.)
- ❌ Heavy borders
- ❌ Bright, flashy colors
- ❌ Anything that feels "bolted on"

---

## 📊 Current vs. Elegant Design

### Current (Ugly prompt_toolkit default)
```
/help              show available commands and help
/exit              exit OpenCLI
/tree              show directory tree structure
```
*Problems: Plain, no structure, hard to scan*

### Elegant Design (Goal)
```
Commands
  help              show available commands and help
  exit              exit OpenCLI
  tree              show directory tree structure
  read              read a file
  write             write to a file

↑↓ navigate  ⏎ select  esc cancel
```

### Alternative Elegant Design (Subtle borders)
```
┌─ Commands ─────────────────────────────────────┐
│ help              show available commands       │
│ exit              exit OpenCLI                  │
│ tree              show directory tree           │
│ read              read a file                   │
│ write             write to a file               │
└─────────────────────────────────────────────────┘
```

### File Mentions - Elegant
```
Files
  opencli/
    core/
      approval.py                    2.5 KB
      tool_registry.py               1.8 KB
    ui/
      autocomplete.py                4.2 KB
      formatters.py                  8.1 KB

  docs/
    README.md                        3.4 KB

↑↓ navigate  ⏎ select  esc cancel
```

---

## 🎨 Visual Design Elements

### 1. Typography & Spacing
```
# Good spacing, aligned columns
help              show available commands and help
exit              exit OpenCLI
tree              show directory tree structure

# VS bad (current)
/help              show available commands and help
/exit              exit OpenCLI
```

**Key improvements:**
- Remove `/` prefix from display (cleaner)
- Align command names and descriptions
- Consistent spacing between columns
- Clean line spacing

### 2. Color Palette (Subtle, Terminal-Native)

```python
# Elegant color scheme
COLORS = {
    'command': '#FFFFFF',        # White for commands (primary)
    'description': '#808080',    # Gray for descriptions (secondary)
    'selected_bg': '#2A2A2A',    # Subtle dark gray for selection
    'selected_fg': '#FFFFFF',    # White text on selection
    'border': '#404040',         # Subtle gray borders
    'header': '#A0A0A0',         # Light gray for headers
    'hint': '#606060',           # Dim gray for hints
}
```

**No bright colors, no cyan/green/yellow** - just elegant grays and whites.

### 3. Layout Options

#### Option A: No Borders (Most Minimal)
```
Commands

  help              show available commands and help
  exit              exit OpenCLI
  tree              show directory tree structure

↑↓ navigate  ⏎ select
```

#### Option B: Subtle Single-Line Borders
```
┌─ Commands ─────────────────────────────────────┐
│ help              show available commands       │
│ exit              exit OpenCLI                  │
│ tree              show directory tree           │
└─────────────────────────────────────────────────┘
```

#### Option C: Top/Bottom Lines Only
```
─── Commands ─────────────────────────────────────
  help              show available commands
  exit              exit OpenCLI
  tree              show directory tree
──────────────────────────────────────────────────
```

**Recommendation:** Start with Option A (no borders), add Option B if needed.

---

## 🔧 Technical Implementation

### Phase 1: Clean Typography & Spacing (30 min)

**Goal:** Fix spacing, alignment, and remove visual clutter

**Changes to `opencli/ui/autocomplete.py`:**

```python
from prompt_toolkit.completion import Completion
from prompt_toolkit.formatted_text import FormattedText

class OpenCLICompleter(Completer):
    def _get_slash_command_completions(self, word: str):
        query = word[1:].lower()

        for cmd in self.slash_commands:
            if cmd.name.startswith(query):
                # Clean display without / prefix
                display = FormattedText([
                    ('', f'{cmd.name:<20}'),           # Left-aligned command
                    ('class:meta', f'{cmd.description}'),  # Gray description
                ])

                yield Completion(
                    text=f'/{cmd.name}',  # Still insert with /
                    start_position=-len(word),
                    display=display,
                )
```

**Key changes:**
- Remove `/` from display (keep in insertion text)
- Left-align commands in a column
- Descriptions in muted gray
- Consistent spacing with `:<20` formatting

### Phase 2: Elegant Selection Highlight (30 min)

**Goal:** Subtle, professional selection highlight

**Add to style configuration:**

```python
from prompt_toolkit.styles import Style

elegant_style = Style.from_dict({
    # Completion menu
    'completion-menu': 'bg:#000000',  # Black background
    'completion-menu.completion': '#FFFFFF',  # White text
    'completion-menu.completion.current': 'bg:#2A2A2A #FFFFFF',  # Subtle selection

    # Meta text (descriptions)
    'completion-menu.completion meta': '#808080',  # Gray descriptions
    'completion-menu.completion.current meta': '#A0A0A0',  # Lighter on selection
})
```

### Phase 3: Smart Categorization (1 hour)

**Goal:** Group completions naturally

**For slash commands:**
```
Session
  help              show available commands
  exit              exit OpenCLI
  clear             clear session

Files
  tree              show directory tree
  read              read a file
  write             write to a file
```

**Implementation:**
```python
def _get_slash_command_completions_with_categories(self, word: str):
    categories = {
        'Session': ['help', 'exit', 'quit', 'clear', 'history'],
        'Files': ['tree', 'read', 'write', 'edit', 'search'],
        'Execution': ['run', 'mode', 'undo'],
    }

    for category, cmd_names in categories.items():
        # Yield category header
        yield Completion(
            text='',  # Not selectable
            start_position=0,
            display=FormattedText([('class:header', f'\n{category}')]),
        )

        # Yield commands in category
        for cmd in self.slash_commands:
            if cmd.name in cmd_names and cmd.name.startswith(query):
                yield ...
```

### Phase 4: File Tree View (1 hour)

**Goal:** Show files in natural tree structure

**For file mentions:**
```
opencli/
  core/
    approval.py                2.5 KB
    tool_registry.py           1.8 KB
  ui/
    autocomplete.py            4.2 KB

docs/
  README.md                    3.4 KB
```

**Implementation:**
```python
def _get_file_mention_completions(self, word: str):
    files = self._find_files(query)

    # Group by directory
    by_dir = {}
    for file_path in files:
        dir_path = file_path.parent
        if dir_path not in by_dir:
            by_dir[dir_path] = []
        by_dir[dir_path].append(file_path)

    # Display with indentation
    for dir_path, files in sorted(by_dir.items()):
        # Directory header
        yield Completion(
            text='',
            start_position=0,
            display=FormattedText([('', f'\n{dir_path}/')]),
        )

        # Files in directory (indented)
        for file_path in files:
            size = self._format_size(file_path.stat().st_size)
            display = FormattedText([
                ('', f'  {file_path.name:<30}'),
                ('class:meta', f'{size:>8}'),
            ])

            yield Completion(
                text=f'@{file_path}',
                start_position=-len(word),
                display=display,
            )
```

---

## 🎯 Implementation Roadmap

### Priority 1: Clean Typography (30 min) ⭐
- Remove `/` from command display
- Fix column alignment
- Add consistent spacing
- Muted colors for descriptions

**Result:** Immediately looks cleaner and more professional

### Priority 2: Subtle Selection (30 min) ⭐
- Elegant selection highlight
- Smooth color transitions
- Terminal-native feel

**Result:** Feels polished and native

### Priority 3: Smart Categorization (1 hour)
- Group commands by category
- Group files by directory
- Clean section headers

**Result:** Easier to navigate and scan

### Priority 4: Advanced Features (optional)
- Fuzzy matching
- File metadata (size, modified)
- Keyboard shortcuts display

---

## 📐 Design Specs

### Spacing
- Command column width: 20 characters
- Description starts at column 22
- Line height: 1 (no extra spacing)
- Category headers: 1 blank line before

### Colors
- Primary text: `#FFFFFF` (white)
- Secondary text: `#808080` (gray)
- Selection background: `#2A2A2A` (dark gray)
- Selection text: `#FFFFFF` (white)
- Headers: `#A0A0A0` (light gray)

### Typography
- Monospace font (terminal default)
- No bold or italic (keeps it clean)
- Left-aligned text
- Right-aligned metadata (sizes, etc.)

---

## ✨ Expected Result

### Before (Current)
```
/help              show available commands and help
/exit              exit OpenCLI
/tree              show directory tree structure
```
*Rating: 3/10 - Plain and hard to scan*

### After Phase 1 (Clean Typography)
```
help              show available commands and help
exit              exit OpenCLI
tree              show directory tree structure
read              read a file
write             write to a file
```
*Rating: 7/10 - Clean and professional*

### After Phase 3 (Categorization)
```
Session
  help              show available commands and help
  exit              exit OpenCLI
  clear             clear current session

Files
  tree              show directory tree structure
  read              read a file
  write             write to a file

Execution
  run               run a bash command
  mode              switch between modes
```
*Rating: 9/10 - Elegant and easy to navigate*

---

## 🚀 Getting Started

### Step 1: Update autocomplete.py
- Clean up display formatting
- Remove visual clutter
- Fix alignment

### Step 2: Add elegant style
- Subtle colors
- Smooth selection
- Terminal-native feel

### Step 3: Test
```bash
opencli
# Type / to see clean command list
# Type @ to see organized file list
```

---

## 💡 Key Philosophy

> "The best design is invisible. It should feel like it's always been part of the terminal."

**Focus on:**
- Clarity over decoration
- Elegance over flash
- Function over form
- Natural over forced

**No icons, no heavy borders, no bright colors - just clean, elegant, terminal-native design.** ✨

---

*Ready to implement Phase 1 for immediate improvement!*
