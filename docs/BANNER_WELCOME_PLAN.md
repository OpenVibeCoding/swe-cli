# 🎨 Banner-Style Welcome Screen Design Plan

## 🎯 Goal

Create a visually appealing banner welcome screen with:
1. **Banner/Header** - Eye-catching title section
2. **Key Commands** - Essential keyboard shortcuts and commands

**Requirements:**
- More substantial than current minimal design
- Elegant, not cluttered
- No emoji icons (keep it professional)
- Show important key commands
- Informative but not overwhelming

---

## 🎨 Banner Design Options

### Option 1: Bold Text Banner with Border (RECOMMENDED)

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ██████  ██████  ███████ ███    ██  ██████ ██      ██          ║
║  ██    ██ ██   ██ ██      ████   ██ ██      ██      ██          ║
║  ██    ██ ██████  █████   ██ ██  ██ ██      ██      ██          ║
║  ██    ██ ██      ██      ██  ██ ██ ██      ██      ██          ║
║   ██████  ██      ███████ ██   ████  ██████ ███████ ██          ║
║                                                                  ║
║  AI-Powered Development Assistant                      v0.3.0   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

Key Commands:
  /help            Show all available commands
  /tree            Explore project structure
  /mode            Switch between plan/normal modes

  Ctrl+K           Open command palette
  @filename        Mention files in your prompt
  /command         Execute slash commands

Working Directory: ~/OpenCLI • User: quocnghi • Mode: NORMAL
```

### Option 2: Gradient-Style Banner

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                 ┃
┃     ╔═══╗ ╔═══╗ ╔═══╗ ╔═╗ ╔╗  ╔═══╗ ╔═══╗ ╔══╗                ┃
┃     ║   ║ ║   ║ ║    ║ ║ ║ ║  ║     ║   ║ ║  ║                ┃
┃     ║   ║ ╠═══╝ ╠═══ ║ ║ ║ ║  ║     ║   ║ ║  ║                ┃
┃     ║   ║ ║     ║    ║ ║ ║ ║  ║     ║   ║ ║  ║                ┃
┃     ╚═══╝ ╩     ╚═══╝ ╚╩═╝ ╚═╝╚═══╝ ╚═══╝ ╚══╝                ┃
┃                                                                 ┃
┃     AI-Powered Development Assistant                   v0.3.0  ┃
┃                                                                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Essential Commands:
  /help            Get started with OpenCLI
  /tree            Browse your project files
  /mode plan       Enable auto-execution mode
  /mode normal     Enable interactive approval mode

Keyboard Shortcuts:
  Ctrl+K           Command palette (quick access)
  Esc+S            Toggle status bar verbosity
  Esc+N            View notification history

Context: ~/OpenCLI • quocnghi • NORMAL mode
```

### Option 3: Simple Styled Header (Elegant)

```
═══════════════════════════════════════════════════════════════════

    OPENCLI                                               v0.3.0

    AI-Powered Development Assistant

═══════════════════════════════════════════════════════════════════

Essential Commands:

  Slash Commands                    Keyboard Shortcuts
  ─────────────────────────────    ──────────────────────
  /help       Get started           Ctrl+K    Command palette
  /tree       Explore files         @file     Mention files
  /mode       Switch modes          /cmd      Run commands

Current Context:
  Directory: ~/OpenCLI
  User: quocnghi
  Mode: NORMAL (interactive approval)

───────────────────────────────────────────────────────────────────
```

### Option 4: Box Drawing Banner (Clean & Professional)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│    ╔═════════════════════════════════════════════════╗         │
│    ║                                                 ║         │
│    ║   OpenCLI - AI Development Assistant           ║         │
│    ║   Version 0.3.0                                 ║         │
│    ║                                                 ║         │
│    ╚═════════════════════════════════════════════════╝         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Quick Start Commands:
─────────────────────
  /help            Show full command reference
  /tree            View project structure
  /mode plan       Enable auto-execution
  /mode normal     Enable interactive mode

Key Bindings:
─────────────
  Ctrl+K           Open command palette
  Esc+S            Toggle status bar
  Esc+N            View notifications

Session Info: quocnghi @ ~/OpenCLI • Mode: NORMAL
```

---

## 🎯 Recommended Design (Option 5: Hybrid - Best of All)

```
╔══════════════════════════════════════════════════════════════════╗
║                          OPENCLI                          v0.3.0 ║
║                                                                  ║
║              AI-Powered Development Assistant                    ║
╚══════════════════════════════════════════════════════════════════╝

Essential Commands:
──────────────────────────────────────────────────────────────────
  /help            Show all available commands
  /tree            Explore your project structure
  /mode plan       Enable auto-execution mode
  /mode normal     Enable interactive approval mode

Keyboard Shortcuts:
──────────────────────────────────────────────────────────────────
  Ctrl+K           Open command palette (quick access)
  @filename        Mention files in prompts
  /command         Execute slash commands

Current Session:
──────────────────────────────────────────────────────────────────
  Directory: ~/OpenCLI
  User: quocnghi
  Mode: NORMAL (requires approval for operations)
```

---

## 📐 Design Structure

### Section 1: Banner (Top)
```
╔══════════════════════════════════════════════════════════════════╗
║                          OPENCLI                          v0.3.0 ║
║                                                                  ║
║              AI-Powered Development Assistant                    ║
╚══════════════════════════════════════════════════════════════════╝
```

**Elements:**
- Double-line box border (elegant)
- Product name centered and prominent
- Version in top right
- Tagline centered below
- Clean spacing

### Section 2: Essential Commands
```
Essential Commands:
──────────────────────────────────────────────────────────────────
  /help            Show all available commands
  /tree            Explore your project structure
  /mode plan       Enable auto-execution mode
  /mode normal     Enable interactive approval mode
```

**Elements:**
- Section title
- Horizontal divider
- 4-5 most important commands
- Command name left-aligned
- Description follows
- Clean spacing

### Section 3: Keyboard Shortcuts
```
Keyboard Shortcuts:
──────────────────────────────────────────────────────────────────
  Ctrl+K           Open command palette (quick access)
  @filename        Mention files in prompts
  /command         Execute slash commands
```

**Elements:**
- Section title
- Horizontal divider
- Key bindings and syntax helpers
- Shortcut left-aligned
- Description follows

### Section 4: Current Session Info
```
Current Session:
──────────────────────────────────────────────────────────────────
  Directory: ~/OpenCLI
  User: quocnghi
  Mode: NORMAL (requires approval for operations)
```

**Elements:**
- Section title
- Horizontal divider
- Current context info
- Each item on separate line

---

## 🎨 Color Scheme

### Banner Section
- **Border**: `bright_white` or `cyan`
- **"OPENCLI"**: `bold bright_white`
- **Version**: `dim white`
- **Tagline**: `dim white`

### Commands Section
- **Section Title**: `bold white`
- **Divider**: `dim white`
- **Command**: `cyan`
- **Description**: `white`

### Shortcuts Section
- **Section Title**: `bold white`
- **Divider**: `dim white`
- **Shortcut**: `yellow` or `cyan`
- **Description**: `white`

### Session Info
- **Section Title**: `bold white`
- **Divider**: `dim white`
- **Labels**: `dim white`
- **Values**: `white`

---

## 📏 Layout Specifications

### Banner
- Width: 70 characters
- Height: 4 lines
- Centered text
- Double-line border

### Sections
- Width: Match banner (70 chars)
- Title: Bold
- Divider: Single line (──────)
- Content: Indented 2 spaces
- Spacing: 1 blank line between sections

### Commands/Shortcuts
- Command column: 20 characters
- Description starts at column 21
- Left-aligned throughout

---

## 🎯 Implementation Plan

### Step 1: Create Banner Component
```python
def _create_banner() -> str:
    """Create the welcome banner."""
    banner = [
        "╔══════════════════════════════════════════════════════════════════╗",
        "║                          OPENCLI                          v0.3.0 ║",
        "║                                                                  ║",
        "║              AI-Powered Development Assistant                    ║",
        "╚══════════════════════════════════════════════════════════════════╝",
    ]
    return "\n".join(banner)
```

### Step 2: Create Command Section
```python
def _create_commands_section() -> str:
    """Create essential commands section."""
    commands = [
        "\nEssential Commands:",
        "─" * 70,
        "  /help            Show all available commands",
        "  /tree            Explore your project structure",
        "  /mode plan       Enable auto-execution mode",
        "  /mode normal     Enable interactive approval mode",
    ]
    return "\n".join(commands)
```

### Step 3: Create Shortcuts Section
```python
def _create_shortcuts_section() -> str:
    """Create keyboard shortcuts section."""
    shortcuts = [
        "\nKeyboard Shortcuts:",
        "─" * 70,
        "  Ctrl+K           Open command palette (quick access)",
        "  @filename        Mention files in prompts",
        "  /command         Execute slash commands",
    ]
    return "\n".join(shortcuts)
```

### Step 4: Create Session Info Section
```python
def _create_session_info(username: str, cwd: str, mode: str) -> str:
    """Create current session info section."""
    info = [
        "\nCurrent Session:",
        "─" * 70,
        f"  Directory: ~/{cwd}",
        f"  User: {username}",
        f"  Mode: {mode} (requires approval for operations)",
    ]
    return "\n".join(info)
```

### Step 5: Combine All Sections
```python
def _print_welcome(self) -> None:
    """Print banner-style welcome message."""
    username = os.getenv('USER', 'user')
    cwd = Path.cwd().name
    mode = self.mode_manager.current_mode.value

    # Create all sections
    banner = self._create_banner()
    commands = self._create_commands_section()
    shortcuts = self._create_shortcuts_section()
    session_info = self._create_session_info(username, cwd, mode)

    # Print with styling
    self.console.print()
    self.console.print(banner, style="bright_white")
    self.console.print(commands)
    self.console.print(shortcuts)
    self.console.print(session_info)
    self.console.print()
```

---

## ✨ Final Design (Recommended Implementation)

```
╔══════════════════════════════════════════════════════════════════╗
║                          OPENCLI                          v0.3.0 ║
║                                                                  ║
║              AI-Powered Development Assistant                    ║
╚══════════════════════════════════════════════════════════════════╝

Essential Commands:
──────────────────────────────────────────────────────────────────
  /help            Show all available commands
  /tree            Explore your project structure
  /mode plan       Enable auto-execution mode
  /mode normal     Enable interactive approval mode

Keyboard Shortcuts:
──────────────────────────────────────────────────────────────────
  Ctrl+K           Open command palette (quick access)
  @filename        Mention files in prompts
  /command         Execute slash commands

Current Session:
──────────────────────────────────────────────────────────────────
  Directory: ~/OpenCLI
  User: quocnghi
  Mode: NORMAL (requires approval for operations)

```

---

## 🎯 Why This Design Works

1. **Professional Banner** - Clear branding without being over the top
2. **Organized Sections** - Information grouped logically
3. **Visual Hierarchy** - Dividers separate sections clearly
4. **Essential Info Only** - Not overwhelming, just what's needed
5. **Elegant Typography** - Box drawing for structure, clean alignment
6. **Context Aware** - Shows user, directory, mode
7. **Actionable** - Clear commands and shortcuts to get started

---

*Ready to implement the banner-style welcome screen!*
