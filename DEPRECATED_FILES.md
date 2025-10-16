# Deprecated Files - UI Refactoring

This document lists files that have been superseded by the new modular UI architecture.
These files are candidates for removal once the new architecture is fully integrated.

## Files Superseded by New Architecture

### Core Infrastructure
**OLD:** N/A (new functionality)
**NEW:** `opencli/ui/core/`
- `component.py` - Base component class
- `renderer.py` - Renderer interface
- `event_handler.py` - Event handling

### Formatters
**OLD:** `opencli/ui/formatters.py` (612 lines)
**NEW:** `opencli/ui/formatters/`
- `base.py` - BaseFormatter abstract class
- `file_formatter.py` - File operation formatters
- `command_formatter.py` - Command execution formatters
- `plan_formatter.py` - Plan mode formatters
- `syntax_highlighter.py` - Language detection

**Status:** Old file should be removed after confirming all imports updated

### Widgets
**OLD:** Individual widget files scattered across UI
**NEW:** `opencli/ui/widgets/`
- `status_bar.py` - Extracted from `status_line.py`
- `spinner.py` - Extracted from `animations.py`
- `progress.py` - Extracted from `animations.py` and `task_progress.py`
- `scrollable_text.py` - Cleaned version of `scrollable_formatted_text.py`

**Deprecated files:**
- `opencli/ui/animations.py` (187 lines) - Functionality moved to widgets
- `opencli/ui/status_line.py` (164 lines) - Functionality moved to widgets
- `opencli/ui/task_progress.py` (193 lines) - Functionality moved to widgets
- `opencli/ui/scrollable_formatted_text2.py` (61 lines) - Duplicate, unused

### Chat Application
**OLD:** `opencli/ui/chat_app.py` (1155 lines)
**NEW:** `opencli/ui/chat/`
- `conversation.py` - ConversationBuffer
- `approval_handler.py` - Approval modal logic
- `key_bindings.py` - Key binding management
- `application.py` - Main ChatApplication

**Deprecated files:**
- `opencli/ui/conversation_buffer.py` (74 lines) - Embedded in chat_app, now separate

### Autocomplete
**OLD:** `opencli/ui/autocomplete.py` (411 lines)
**NEW:** `opencli/ui/autocomplete/`
- `completer.py` - OpenCLICompleter
- `slash_commands.py` - Slash command system
- `file_mentions.py` - File mention completion

### Unused/Deprecated Files (Never Integrated)
These files were found to be unused or superseded:

1. **`opencli/ui/approval_modal.py`** (209 lines)
   - Old approval modal implementation
   - Superseded by inline approval in chat

2. **`opencli/ui/approval_modal_v2.py`** (173 lines)
   - Second version of approval modal
   - Also superseded

3. **`opencli/ui/approval_modal_pt.py`** (84 lines)
   - prompt_toolkit version
   - Also superseded

4. **`opencli/ui/rules_editor_modal.py`** (411 lines)
   - Never imported or used in codebase
   - Safe to remove

5. **`opencli/ui/notifications.py`** (74 lines)
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
