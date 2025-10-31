# SWE-CLI Textual UI - Usage Guide

## 🎉 P1 Runtime Integration Complete!

The Textual UI is now fully integrated with SWE-CLI's core runtime. You can use it for interactive coding sessions with full tool calling support!

## Quick Start

### Installation
The package is already installed with Textual dependencies. If you need to reinstall:

```bash
pip install -e .
```

### Launch Textual UI

There are three ways to launch the Textual UI:

#### Option 1: Direct Command (Recommended)
```bash
swecli-textual
```

#### Option 2: Test Script
```bash
python test_textual_runner.py
```

#### Option 3: From Python
```python
from swecli.ui_textual.runner import launch_textual_cli

launch_textual_cli()
```

## Features

### ✅ Working Features

1. **Full-Screen Chat Interface**
   - Clean, modern terminal UI
   - Multi-line input support (Enter to send, Shift+Enter for new lines)
   - Scrollable conversation history
   - Color-coded messages (user/assistant/system)

2. **Tool Calling Integration**
   - Full REPL integration
   - All SWE-CLI tools available (file operations, bash commands, web fetch, etc.)
   - Real-time tool execution with output display

3. **Approval System**
   - Interactive approval modals for bash commands
   - Edit commands before execution
   - "Approve similar" option for repeated commands
   - Rule-based auto-approval system

4. **Session Management**
   - Session persistence across runs
   - Resume previous sessions
   - Continue mode for returning to recent work

5. **Console Output Bridging**
   - All REPL output appears in conversation
   - Proper ANSI color rendering
   - Rich formatting support

### 🚧 Pending Enhancements

1. **Tool Progress Streaming**
   - Live spinners during tool execution
   - Partial output streaming
   - Progress indicators

2. **Enhanced Tool Output Rendering**
   - Syntax-highlighted code blocks
   - Structured panels for complex outputs
   - Better formatting for diffs and logs

3. **Feature Parity**
   - Mode switching UI (PLAN/NORMAL modes)
   - Status bar updates with live context info
   - Advanced shortcuts and quick commands

## Usage Examples

### Basic Chat
```
› hello
⏺ Hello! I'm SWE-CLI with the new Textual UI. How can I help you today?
```

### File Operations
```
› create a file called test.py with a hello world function
⏺ I'll create a Python file with a hello world function.
[Approval modal appears if bash commands are needed]
[File is created and shown]
```

### Running Commands
```
› run ls -la
[Approval modal appears]
[Command output shown in conversation]
```

### Multi-line Messages
```
› create a function that:
  - takes a list of numbers
  - filters out negatives
  - returns the sum
[Press Enter to send the multi-line message]
```

## Keyboard Shortcuts

### Input Area
- **Enter** - Send message
- **Shift+Enter** - New line (multi-line input)
- **Ctrl+Down** - Focus input field

### Conversation Area
- **Ctrl+Up** - Focus conversation (for scrolling)
- **Arrow Up/Down** - Scroll line by line
- **Page Up/Down** - Scroll by page

### Application
- **Ctrl+C** - Quit application
- **Ctrl+L** - Clear conversation
- **ESC** - Interrupt current processing

### Approval Modal
- **Enter** - Approve command (when in text field)
- **Tab** - Navigate between buttons
- **Space** - Activate selected button

## Advanced Usage

### Resume Previous Session
```bash
swecli-textual --resume SESSION_ID
```

### Continue Latest Session
```bash
swecli-textual --continue
```

### Specify Working Directory
```bash
swecli-textual --working-dir /path/to/project
```

## Troubleshooting

### Issue: Textual UI not launching
**Solution**: Ensure textual is installed:
```bash
pip show textual
pip install textual>=0.60.0
```

### Issue: Approval modals not appearing
**Check**: The approval manager integration in the runner.
**Workaround**: Check console for fallback approval prompts.

### Issue: Tool outputs not appearing
**Check**: Console output bridging is working. Look for captured output in conversation.
**Debug**: Check `_console_queue` and `_render_console_output` in runner.

### Issue: Multi-line input not working
**Key mapping**: Shift+Enter may be detected as Ctrl+J on some terminals.
**Workaround**: The ChatTextArea should handle both. Check terminal key bindings.

## Configuration

### Environment Variables
- `ANTHROPIC_API_KEY` - Required for Claude API access
- `OPENAI_API_KEY` - Required if using OpenAI models
- `SWECLI_LOG_LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR)

### Config Files
- `~/.swecli/settings.json` - Global settings
- `.swecli/config.json` - Project-specific settings

### Session Storage
Sessions are stored in: `~/.swecli/sessions/`

## Development

### Running Tests
```bash
# Basic POC tests
pytest tests/test_textual_runner.py -v

# Integration tests
pytest tests/test_command_history.py -v
pytest tests/test_paste_handling.py -v
```

### Debugging
Set debug mode in the runner:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Known Limitations

1. **Trackpad scrolling**: Not supported in TUI apps. Use keyboard navigation instead.
2. **Tool progress**: Current implementation shows results after completion, not live progress.
3. **Large outputs**: May cause lag if tool produces very large outputs (>10MB).
4. **Terminal compatibility**: Some terminals may have different key mappings.

## Feedback

Found a bug or have a feature request?
- Check existing issues: https://github.com/swe-cli/swe-cli/issues
- Create new issue with "textual-ui" label

## Next Steps

See [TEXTUAL_FULL_MIGRATION_PLAN.md](./TEXTUAL_FULL_MIGRATION_PLAN.md) for:
- Roadmap for remaining features
- P2 feature parity tasks
- Beta launch timeline
- Migration to default UI plan

---
**Status**: ✅ P1 Complete - Fully functional for basic usage
**Last Updated**: 2025-03-26
