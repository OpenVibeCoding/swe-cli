# Textual Migration - Next Phase Plan

## Current Status ✅
**Multi-line input is now working!**
- ✅ Enter sends messages
- ✅ Shift+Enter creates real line breaks
- ✅ Custom `ChatTextArea` implementation successful
- ✅ Cross-terminal key handling implemented

## Next Phase: Command History & Enhanced Features

### Priority 1: Command History ✅ Completed (March 2025)
**Goal**: Up/Down arrow navigation through message history

#### Implementation Plan
```python
class SWECLIChatApp(App):
    def __init__(self):
        self._history_index = -1  # Current position in history
        self._current_input = ""   # Buffer for current unsent message

    def action_history_up(self) -> None:
        """Navigate to previous command in history."""
        if self._history and self._history_index < len(self._history) - 1:
            if self._history_index == -1:
                self._current_input = self.input_field.text
            self._history_index += 1
            self.input_field.text = self._history[-(self._history_index + 1)]

    def action_history_down(self) -> None:
        """Navigate to next command in history."""
        if self._history_index > 0:
            self._history_index -= 1
            self.input_field.text = self._history[-(self._history_index + 1)]
        elif self._history_index == 0:
            self._history_index = -1
            self.input_field.text = self._current_input
```

#### Key Bindings to Add
```python
BINDINGS = [
    # ... existing bindings ...
    Binding("up", "history_up", "Previous Command", show=False),
    Binding("down", "history_down", "Next Command", show=False),
]
```

#### Implementation Notes
- `_history_index` and `_current_input` track position; reset on submission
- Up/Down intercepted in `ChatTextArea._on_key`, invoking `action_history_up/down`
- History entries restore text via `load_text` and move cursor to the end

#### Tests
- `pytest tests/test_command_history.py`
- Manual verification via `python test_textual_ui_clear.py`

### Priority 2: Paste Detection ✅ Completed (March 2025)
**Goal**: Handle large paste operations gracefully

#### Implementation Plan
```python
class ChatTextArea(TextArea):
    def on_paste(self, event: Paste) -> None:
        """Handle paste events and show placeholder for large content."""
        paste_content = event.text
        if len(paste_content) > 100:  # Threshold for "large" paste
            # Show placeholder and store actual content
            self._pasted_content = paste_content
            self.insert_text("[[Pasted Content: " + str(len(paste_content)) + " chars]]")
        else:
            # Handle small pastes normally
            self.insert_text(paste_content)
```

#### Implementation Notes
- `ChatTextArea.on_paste` registers large blocks with placeholder tokens
- `_submit_message` resolves placeholders and clears cached content post-send
- Placeholder format: `[[PASTE-<n>:<len> chars]]`

#### Tests
- `pytest tests/test_paste_handling.py`
- Manual: paste > threshold via `python test_textual_ui_clear.py`

### Priority 3: Enhanced Message Formatting ⚙️ In Progress
**Goal**: Better display of code blocks and structured content

#### Implementation Plan
```python
class ConversationLog(RichLog):
    def add_code_block(self, code: str, language: str = "") -> None:
        """Add formatted code block to conversation."""
        # Create syntax-highlighted panel
        panel = Panel(
            Syntax(code, language, theme="monokai", line_numbers=True),
            title=f"Code: {language}" if language else "Code",
            border_style="blue"
        )
        self.write(panel)

    def add_assistant_message(self, message: str) -> None:
        """Enhanced message with markdown-like formatting."""
        # Detect code blocks with ```language markers
        # Split message and format code blocks separately
        # Handle bold, italic, lists etc.
```

#### Implementation Steps
Status: initial implementation landed (`ConversationLog` detects code fences, uses `Syntax` panels, and applies basic markdown heuristics). Future work: broaden markdown coverage, add copy buttons, improve styling for list prefixes.

### Priority 4: Integration with SWE-CLI Core
**Goal**: Connect Textual UI to existing SWE-CLI functionality

#### Implementation Plan
```python
# In main swecli CLI
def launch_textual_mode(config: Config) -> None:
    """Launch SWE-CLI with Textual UI."""
    app = create_chat_app(
        on_message=lambda msg: process_swecli_command(msg, config),
        model=config.model,
        context_limit=config.context_limit
    )
    app.run()

def process_swecli_command(message: str, config: Config) -> str:
    """Process command through SWE-CLI core logic."""
    # Connect to existing REPL query processor
    # Handle tool execution, API calls, etc.
    # Return formatted response
```

#### Implementation Steps
1. **Create integration layer** between Textual UI and SWE-CLI core
- ✅ `swecli/ui_textual/runner.py` scaffolded with placeholder queue (March 2025)
- ✅ Runner now boots real REPL, captures console output, and mirrors replies into Textual log
- ✅ Textual approval modal added; `/mcp` and other commands stream output in the chat log
2. **Connect message processing** to existing `QueryProcessor`
3. **Handle tool execution** through existing tool registry
4. **Maintain session management** with existing `SessionManager`
5. **Add configuration support** for model selection, API keys
6. **Test**: Full workflow from command to response

## Testing Strategy

### Automated Tests
```python
# test_command_history.py
def test_history_navigation():
    """Test Up/Down arrow history navigation."""
    app = create_chat_app()
    # Simulate message submission
    # Test Up/Down navigation
    # Verify history state

# test_paste_detection.py
def test_paste_handling():
    """Test paste event handling."""
    textarea = ChatTextArea()
    # Test small paste (normal)
    # Test large paste (placeholder)
    # Verify submission behavior
```

### Manual Testing Checklist
- [ ] Command history: Up/Down navigation
- [ ] Command history: Current input preservation
- [ ] Command history: Empty history handling
- [ ] Paste detection: Small pastes (< 100 chars)
- [ ] Paste detection: Large pastes (> 100 chars)
- [ ] Paste detection: Multi-line pastes
- [ ] Message formatting: Code blocks
- [ ] Message formatting: Mixed content
- [ ] Integration: Full SWE-CLI workflow
- [ ] Cross-platform: macOS, Linux, Windows

### Cross-Platform Validation
1. **macOS**: Terminal.app, iTerm2
2. **Linux**: gnome-terminal, konsole
3. **Windows**: Windows Terminal, PowerShell
4. **WSL**: Windows Subsystem for Linux
5. **Docker**: Containerized environments

## Estimated Timeline

### Phase 1: Command History (2-3 days)
- Day 1: Implementation and basic testing
- Day 2: Edge cases and refinement
- Day 3: Cross-platform validation

### Phase 2: Paste Detection (1-2 days)
- Day 1: Implementation and testing
- Day 2: Edge cases and integration

### Phase 3: Enhanced Formatting (2-3 days)
- Day 1: Syntax highlighting implementation
- Day 2: Markdown parsing
- Day 3: Integration and testing

### Phase 4: Core Integration (3-5 days)
- Day 1-2: Integration layer development
- Day 3-4: Testing and refinement
- Day 5: Documentation and deployment

**Total Estimated: 8-13 days**

## Success Criteria

### Phase Complete When:
- ✅ Command history works with Up/Down arrows
- ✅ Large pastes show placeholders and handle correctly
- ✅ Code blocks display with syntax highlighting
- ✅ Full SWE-CLI functionality works through Textual UI
- ✅ All features tested across platforms
- ✅ Documentation updated
- ✅ Ready for production deployment

## Risk Mitigation

### Technical Risks
- **Key Event Conflicts**: Test early with Up/Down history vs existing scrolling
- **Paste Event Handling**: Verify Textual paste events work consistently
- **Performance**: Large message history shouldn't impact UI responsiveness
- **Integration Complexity**: May need adapter pattern for SWE-CLI core

### Mitigation Strategies
- **Incremental Development**: Implement and test one feature at a time
- **Fallback Mechanisms**: Keep working versions at each milestone
- **Cross-Platform Testing**: Test on multiple terminals early and often
- **Documentation**: Document implementation decisions and trade-offs

## Next Actions

1. **Start with Command History** - Highest value, lowest risk
2. **Create feature branch** for each major component
3. **Test thoroughly** before merging to main branch
4. **Update documentation** as features are implemented
5. **Plan integration testing** with SWE-CLI core functionality

---
**Ready to begin Phase 1: Command History Implementation** 🚀
