# Deprecated Files - UI Refactoring

This document lists files that have been superseded by the new modular UI architecture.
These files are candidates for removal once the new architecture is fully integrated.

## Files Superseded by New Architecture

### Core Infrastructure
**OLD:** N/A (new functionality)
**NEW:** `swecli/ui/core/`
- `component.py` - Base component class
- `renderer.py` - Renderer interface
- `event_handler.py` - Event handling

### Formatters
**OLD:** `swecli/ui/formatters.py` (612 lines)
**NEW:** `swecli/ui/formatters/`
- `base.py` - BaseFormatter abstract class
- `file_formatter.py` - File operation formatters
- `command_formatter.py` - Command execution formatters
- `plan_formatter.py` - Plan mode formatters
- `syntax_highlighter.py` - Language detection

**Status:** Old file should be removed after confirming all imports updated

### Widgets
**OLD:** Individual widget files scattered across UI
**NEW:** `swecli/ui/widgets/`
- `status_bar.py` - Extracted from `status_line.py`
- `spinner.py` - Extracted from `animations.py`
- `progress.py` - Extracted from `animations.py` and `task_progress.py`
- `scrollable_text.py` - Cleaned version of `scrollable_formatted_text.py`

**Deprecated files:**
- `swecli/ui/animations.py` (187 lines) - Functionality moved to widgets
- `swecli/ui/status_line.py` (164 lines) - Functionality moved to widgets
- `swecli/ui/task_progress.py` (193 lines) - Functionality moved to widgets
- `swecli/ui/scrollable_formatted_text2.py` (61 lines) - Duplicate, unused

### Chat Application
**OLD:** `swecli/ui/chat_app.py` (1155 lines)
**NEW:** `swecli/ui/chat/`
- `conversation.py` - ConversationBuffer
- `approval_handler.py` - Approval modal logic
- `key_bindings.py` - Key binding management
- `application.py` - Main ChatApplication

**Deprecated files:**
- `swecli/ui/conversation_buffer.py` (74 lines) - Embedded in chat_app, now separate

### Autocomplete
**OLD:** `swecli/ui/autocomplete.py` (411 lines)
**NEW:** `swecli/ui/autocomplete/`
- `completer.py` - SWE-CLICompleter
- `slash_commands.py` - Slash command system
- `file_mentions.py` - File mention completion

### Unused/Deprecated Files (Never Integrated)
These files were found to be unused or superseded:

1. **`swecli/ui/approval_modal.py`** (209 lines)
   - Old approval modal implementation
   - Superseded by inline approval in chat

2. **`swecli/ui/approval_modal_v2.py`** (173 lines)
   - Second version of approval modal
   - Also superseded

3. **`swecli/ui/approval_modal_pt.py`** (84 lines)
   - prompt_toolkit version
   - Also superseded

4. **`swecli/ui/rules_editor_modal.py`** (411 lines)
   - Never imported or used in codebase
   - Safe to remove

5. **`swecli/ui/notifications.py`** (74 lines)
   - Barely used, can be integrated into status system

## Migration Checklist

Before removing old files, verify:

- [ ] All imports updated to new locations
- [ ] Tests updated to use new modules
- [ ] REPL integration uses new modules
- [ ] No circular dependencies created
- [ ] Backward compatibility shims in place if needed

## Removal Order

Safest removal order:
1. Completely unused files (rules_editor_modal, approval modals, notifications)
2. Duplicate files (scrollable_formatted_text2)
3. Superseded single-purpose files (animations, status_line, task_progress)
4. Large refactored files (chat_app, autocomplete, formatters) - LAST

## Estimated Impact

**Total lines removed:** ~2500 lines
**Files removed:** 7-10 files
**New files created:** 29 files
**Net change:** ~2500 lines organized into modular structure
