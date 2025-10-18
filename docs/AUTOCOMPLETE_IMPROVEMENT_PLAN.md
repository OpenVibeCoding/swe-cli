# 🎨 Autocomplete Visual Improvement Plan

## 🎯 Problem Statement

The current autocomplete for @ (file mentions) and / (slash commands) uses prompt_toolkit's basic completion system, which looks plain and unpolished compared to Claude Code's beautiful autocomplete UI.

**Current Issues:**
- ❌ Plain text display (no icons, no colors)
- ❌ Basic dropdown menu (no borders, no styling)
- ❌ Limited metadata display
- ❌ No file/folder icons
- ❌ No syntax highlighting in preview
- ❌ No fuzzy matching
- ❌ Looks "cheap" and dated

**Goal:** Make the autocomplete look modern, polished, and professional like Claude Code.

---

## 📊 Current Implementation Analysis

### Using prompt_toolkit's Completion System

```python
# Current completion (swecli/ui/autocomplete.py)
yield Completion(
    text=f"/{cmd.name}",
    start_position=start_position,
    display=f"/{cmd.name}",           # Plain text
    display_meta=cmd.description,     # Plain text meta
)
```

**Rendering:**
```
/help              show available commands and help
/exit              exit SWE-CLI
/tree              show directory tree structure
```

**Problems:**
- No icons (📝, 📁, ⚡)
- No colors or styling
- No borders or visual separation
- Looks like a plain text list

---

## 🎨 Improvement Strategy

### Option 1: Enhanced prompt_toolkit Styling ⭐ RECOMMENDED

Use prompt_toolkit's `FormattedTextControl` and custom styling to create beautiful completions.

**Advantages:**
- ✅ Native integration with existing prompt_toolkit
- ✅ No major architecture changes
- ✅ Custom styling with ANSI colors
- ✅ Can add icons, borders, colors
- ✅ Maintains keyboard navigation

**Implementation:**

1. **Create Custom Completer with Styled Output**
   ```python
   from prompt_toolkit.formatted_text import FormattedText

   class StyledCompletion(Completion):
       def __init__(self, text, start_position, icon, display_text, meta, style):
           super().__init__(text, start_position)
           self.icon = icon
           self.display_text = display_text
           self.meta = meta
           self.style = style
   ```

2. **Use FormattedText for Rich Display**
   ```python
   display = FormattedText([
       ('class:icon', f'{icon} '),           # Icon with color
       ('class:command', f'{name}'),         # Command name
       ('', '  '),                            # Spacing
       ('class:meta', f'{description}'),     # Description
   ])
   ```

3. **Custom Style Configuration**
   ```python
   from prompt_toolkit.styles import Style

   autocomplete_style = Style.from_dict({
       'icon': '#00ff00 bold',           # Green icons
       'command': '#00ffff',             # Cyan commands
       'meta': '#808080',                # Gray descriptions
       'file': '#ffff00',                # Yellow files
       'folder': '#00ff00',              # Green folders
       'border': '#444444',              # Gray borders
   })
   ```

### Option 2: Custom Completion Menu Rendering

Create a completely custom completion menu with full control over rendering.

**Advantages:**
- ✅ Complete visual control
- ✅ Can add borders, boxes, previews
- ✅ Can show file previews
- ✅ Can add file icons (📝, 📁)

**Disadvantages:**
- ❌ More complex implementation
- ❌ Need to handle keyboard navigation
- ❌ Need to handle cursor positioning

### Option 3: Hybrid Approach (Rich + prompt_toolkit)

Use Rich for rendering but integrate with prompt_toolkit for input.

**Advantages:**
- ✅ Beautiful Rich formatting
- ✅ Syntax highlighting
- ✅ Tables, panels, trees

**Disadvantages:**
- ❌ Complex integration
- ❌ May have rendering conflicts
- ❌ Harder to maintain

---

## 🎯 Recommended Implementation (Option 1)

### Phase 1: Enhanced Styling with Icons

**Goal:** Add icons, colors, and better formatting to completions

**Files to Modify:**
- `swecli/ui/autocomplete.py`
- `swecli/repl/repl.py` (for style integration)

**Features:**
1. **Slash Command Icons**
   ```
   📚 /help          show available commands and help
   🚪 /exit          exit SWE-CLI
   🌲 /tree          show directory tree structure
   📖 /read          read a file
   📝 /write         write to a file
   ✏️  /edit          edit a file
   ⚡ /run           run a bash command
   ```

2. **File/Folder Icons**
   ```
   📁 src/                   directory
   📄 README.md              markdown file
   🐍 main.py                python file
   ⚙️  config.json            config file
   📦 package.json           package file
   ```

3. **Color Coding**
   - Commands: Cyan
   - Descriptions: Dim gray
   - Files: Yellow
   - Folders: Green
   - Icons: Matching colors

4. **Visual Improvements**
   ```
   ╭─ Slash Commands ─────────────────────────────────╮
   │ 📚 /help          show available commands         │
   │ 🚪 /exit          exit SWE-CLI                    │
   │ 🌲 /tree          show directory tree             │
   ╰───────────────────────────────────────────────────╯
   ```

### Phase 2: Fuzzy Matching

**Goal:** Better search with fuzzy matching

**Features:**
1. Use `fuzzywuzzy` or `rapidfuzz` for fuzzy string matching
2. Rank completions by relevance
3. Highlight matched characters

**Example:**
```
User types: /he

Matches:
📚 /help          show available commands and help
📜 /history       show command history
```

### Phase 3: File Previews

**Goal:** Show file previews in autocomplete

**Features:**
1. Show first few lines of file
2. Syntax highlighting in preview
3. File metadata (size, modified time)

**Example:**
```
╭─ @main.py ──────────────────────────╮
│ 🐍 main.py                           │
│ Size: 1.2 KB | Modified: 2 min ago  │
│                                      │
│ Preview:                             │
│   1  import sys                      │
│   2  from swecli import ...         │
│   3                                  │
╰──────────────────────────────────────╯
```

### Phase 4: Advanced Features

1. **Multi-column Layout**
   ```
   Commands                Files
   ─────────               ─────────
   📚 /help                📁 src/
   🚪 /exit                📄 README.md
   🌲 /tree                🐍 main.py
   ```

2. **Categorization**
   ```
   ╭─ Session Management ─────────╮
   │ 📚 /help                      │
   │ 🚪 /exit                      │
   │ 🔄 /clear                     │
   ╰───────────────────────────────╯

   ╭─ File Operations ────────────╮
   │ 🌲 /tree                      │
   │ 📖 /read                      │
   │ 📝 /write                     │
   ╰───────────────────────────────╯
   ```

3. **Keyboard Shortcuts Display**
   ```
   📚 /help          show available commands     [Enter]
   🚪 /exit          exit SWE-CLI                [Ctrl+X]
   ```

---

## 📋 Implementation Roadmap

### Priority 1: Basic Icon & Color Enhancement (1-2 hours)
- ✅ Add icons to slash commands
- ✅ Add icons to file/folder completions
- ✅ Apply color styling
- ✅ Test with prompt_toolkit

### Priority 2: Better Layout & Borders (1 hour)
- ✅ Add borders to completion menu
- ✅ Add section headers
- ✅ Improve spacing and alignment

### Priority 3: Fuzzy Matching (1 hour)
- ✅ Integrate fuzzy matching library
- ✅ Rank completions by relevance
- ✅ Highlight matched characters

### Priority 4: File Previews (2-3 hours)
- ✅ Show file previews in autocomplete
- ✅ Add syntax highlighting to previews
- ✅ Display file metadata

---

## 🎨 Visual Design Mockups

### Slash Command Autocomplete (Before)
```
/help              show available commands and help
/exit              exit SWE-CLI
/tree              show directory tree structure
```

### Slash Command Autocomplete (After - Phase 1)
```
╭─ Commands ───────────────────────────────────────────╮
│ 📚 /help          show available commands and help   │
│ 🚪 /exit          exit SWE-CLI                       │
│ 🌲 /tree          show directory tree structure      │
│ 📖 /read          read a file                        │
│ 📝 /write         write to a file                    │
╰──────────────────────────────────────────────────────╯
```

### File Mention Autocomplete (Before)
```
src/main.py        file
src/utils.py       file
tests/             file
```

### File Mention Autocomplete (After - Phase 1)
```
╭─ Files ──────────────────────────────────────────────╮
│ 📁 src/                    directory                 │
│ 🐍 src/main.py             python • 1.2 KB           │
│ 🐍 src/utils.py            python • 856 B            │
│ 📁 tests/                  directory                 │
│ 🐍 tests/test_main.py      python • 2.1 KB           │
╰──────────────────────────────────────────────────────╯
```

### File Mention Autocomplete (After - Phase 3 with Preview)
```
╭─ Files ──────────────────────────────────────────────╮
│ 🐍 src/main.py             python • 1.2 KB           │
│ ─────────────────────────────────────────────────── │
│ Preview:                                             │
│   1  import sys                                      │
│   2  from swecli.repl import REPL                   │
│   3                                                  │
│   4  def main():                                     │
│   5      repl = REPL()                               │
│ ─────────────────────────────────────────────────── │
│ Modified: 2 minutes ago                              │
╰──────────────────────────────────────────────────────╯
```

---

## 🔧 Technical Implementation Details

### 1. Icon Mapping

```python
# File type icons
FILE_ICONS = {
    '.py': '🐍',
    '.js': '📜',
    '.ts': '📘',
    '.json': '⚙️',
    '.md': '📄',
    '.txt': '📝',
    '.yaml': '⚙️',
    '.yml': '⚙️',
    '.toml': '⚙️',
    '.sh': '⚡',
    '.bash': '⚡',
    'directory': '📁',
    'default': '📄',
}

# Command category icons
COMMAND_ICONS = {
    'help': '📚',
    'exit': '🚪',
    'quit': '🚪',
    'clear': '🔄',
    'tree': '🌲',
    'read': '📖',
    'write': '📝',
    'edit': '✏️',
    'search': '🔍',
    'run': '⚡',
    'mode': '🔀',
    'undo': '↩️',
    'history': '📜',
    'sessions': '📋',
    'resume': '▶️',
    'init': '🚀',
}
```

### 2. Styled Completion Class

```python
from prompt_toolkit.completion import Completion
from prompt_toolkit.formatted_text import FormattedText

class StyledCompletion(Completion):
    """Enhanced completion with icons and styling."""

    def __init__(
        self,
        text: str,
        start_position: int,
        icon: str,
        display_text: str,
        meta: str,
        category: str = "default",
    ):
        # Create formatted display
        display = FormattedText([
            ('class:icon', f'{icon} '),
            ('class:name', f'{display_text:<20}'),
            ('', '  '),
            ('class:meta', meta),
        ])

        super().__init__(
            text=text,
            start_position=start_position,
            display=display,
            display_meta='',  # We handle meta in display
        )
```

### 3. Custom Completion Menu Style

```python
from prompt_toolkit.styles import Style

autocomplete_style = Style.from_dict({
    # Icons
    'completion-menu icon': '#00ff00',

    # Command names
    'completion-menu name': '#00ffff bold',

    # Descriptions
    'completion-menu meta': '#808080',

    # Selected item
    'completion-menu.completion.current': 'bg:#444444 #ffffff',

    # Menu border
    'completion-menu': 'bg:#1a1a1a #00ffff',
    'completion-menu.border': '#444444',
})
```

### 4. Integration with REPL

```python
# In swecli/repl/repl.py

from swecli.ui.autocomplete import SWE-CLICompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import ThreadedCompleter

# Initialize with styled completer
completer = SWE-CLICompleter(self.config.working_dir)
threaded_completer = ThreadedCompleter(completer)

self.session = PromptSession(
    completer=threaded_completer,
    style=autocomplete_style,  # Apply custom style
    complete_while_typing=True,
    complete_in_thread=True,
)
```

---

## 🎯 Success Metrics

### Before (Current State)
- Visual Appeal: 3/10
- User Experience: 5/10
- Information Density: 4/10
- Professionalism: 3/10

### After (Phase 1 - Icons & Colors)
- Visual Appeal: 7/10 (+4)
- User Experience: 7/10 (+2)
- Information Density: 6/10 (+2)
- Professionalism: 7/10 (+4)

### After (Phase 4 - Full Implementation)
- Visual Appeal: 9/10 (+6)
- User Experience: 9/10 (+4)
- Information Density: 9/10 (+5)
- Professionalism: 9/10 (+6)

---

## 🚀 Getting Started

### Step 1: Install Dependencies (if needed)
```bash
pip install rapidfuzz  # For fuzzy matching
```

### Step 2: Implement Phase 1
1. Update `swecli/ui/autocomplete.py` with icon mapping
2. Create `StyledCompletion` class
3. Update completers to use styled completions
4. Add custom style in REPL

### Step 3: Test
```bash
swecli
# Type / to see styled slash commands
# Type @ to see styled file mentions
```

---

## 📚 Resources

- [prompt_toolkit Documentation](https://python-prompt-toolkit.readthedocs.io/)
- [FormattedText Guide](https://python-prompt-toolkit.readthedocs.io/en/master/pages/printing_text.html#formatted-text)
- [Completion Styling](https://python-prompt-toolkit.readthedocs.io/en/master/pages/asking_for_input.html#autocompletion)
- [Unicode Icons Reference](https://unicode.org/emoji/charts/full-emoji-list.html)

---

## 🎉 Expected Result

A beautiful, modern, professional autocomplete system that:
- ✅ Looks polished and premium (like Claude Code)
- ✅ Provides rich visual feedback with icons and colors
- ✅ Shows useful metadata (file size, type, descriptions)
- ✅ Has fuzzy matching for better search
- ✅ Includes file previews with syntax highlighting
- ✅ Makes the CLI feel modern and professional

**No more "cheap and ugly" autocomplete!** 🚀

---

*Ready to implement Phase 1 when you approve the plan!*
