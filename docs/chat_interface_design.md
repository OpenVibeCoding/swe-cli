# Chat Interface Redesign

## Problem Statement

Current REPL uses blocking `prompt()` calls in a loop, creating new input boxes each time. This creates visual clutter and doesn't match modern chat UI expectations (like ChatGPT, Slack, Discord).

## Requirements

1. **Fixed input box** always at bottom of terminal
2. **Scrollable conversation** area above input
3. When user presses Enter:
   - Message moves to conversation area
   - Input box clears
   - Input box stays at bottom
4. No frames/boxes appearing for each message
5. Live updates during LLM processing

## Architecture

### Current (Blocking Loop)
```python
while running:
    input = prompt_session.prompt()  # Blocks, creates new line
    print(input in frame)            # Creates visual clutter
    process(input)
    print(response)
```

### New (Event-Driven Application)
```
┌────────────────────────────────────────────┐
│  Conversation History (scrollable)         │
│                                            │
│  › Hello                                   │
│  I'll help you with that...                │
│                                            │
│  › Create a file                           │
│  ⠋ Creating file... (2s)                   │
│                                            │
│  (grows upward, scrolls automatically)     │
├────────────────────────────────────────────┤
│ ⏵⏵ normal • Context: 95%                   │  <- Status bar
├────────────────────────────────────────────┤
│ › [user types here]_                       │  <- Fixed input (always here)
└────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Create Chat Application Framework

**New file**: `swecli/ui/chat_app.py`

Components needed:
1. **ConversationBuffer**: Manages message history
2. **ConversationControl**: Renders scrollable conversation
3. **InputField**: Fixed input at bottom
4. **StatusBar**: Shows mode, context, etc.
5. **ChatApplication**: Main application with layout

### Phase 2: Message Flow

```python
# User presses Enter in input field
def on_enter():
    text = input_buffer.text
    if text.strip():
        # Add to conversation
        conversation.add_user_message(text)

        # Clear input
        input_buffer.reset()

        # Process message (async)
        asyncio.create_task(process_message(text))

# During processing
async def process_message(text):
    # Show thinking indicator
    conversation.add_assistant_thinking()

    # Get LLM response
    response = await agent.process(text)

    # Update conversation with response
    conversation.update_assistant_message(response)
```

### Phase 3: Live Updates

- Use `Application.invalidate()` to refresh display
- Update conversation buffer during LLM streaming
- Show spinner/progress in conversation area
- Input box stays fixed and responsive

## Technical Details

### Using prompt_toolkit Application

```python
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.key_binding import KeyBindings

# Conversation display (read-only, scrollable)
conversation_area = TextArea(
    text="",
    multiline=True,
    scrollbar=True,
    read_only=True,
    focusable=False,
)

# Status bar
status_bar = Window(height=1, content=...)

# Input field (fixed at bottom)
input_field = TextArea(
    height=1,
    multiline=False,
    prompt="› ",
)

# Layout: conversation on top, status bar, input at bottom
layout = Layout(
    HSplit([
        conversation_area,  # Grows to fill space
        status_bar,         # Fixed height
        input_field,        # Fixed height
    ])
)

# Key bindings
kb = KeyBindings()

@kb.add('enter')
def on_enter(event):
    # Handle message submission
    pass

# Create application
app = Application(
    layout=layout,
    key_bindings=kb,
    full_screen=True,
)

# Run
app.run()
```

### Integration with Existing REPL

The existing REPL class will be refactored:
1. Remove blocking `prompt_session.prompt()` loop
2. Use `ChatApplication` instead
3. Connect message handlers to existing `_process_query()`
4. Keep all existing functionality (commands, modes, etc.)

## Migration Strategy

1. **Create new `ChatApplication` class** with basic layout
2. **Test independently** with simple echo functionality
3. **Gradually migrate REPL** to use new application
4. **Keep existing REPL** as fallback during transition
5. **Add feature flag** to switch between old/new UI

## Benefits

✅ Fixed input box (like ChatGPT, Slack, Discord)
✅ No visual clutter from repeated frames
✅ Scrollable conversation history
✅ Live updates during processing
✅ Better UX and feel
✅ Modern chat interface

## Testing

Create test script:
```python
# test_chat_app.py
from swecli.ui.chat_app import ChatApplication

app = ChatApplication()

# Simulate messages
app.add_user_message("Hello")
app.add_assistant_message("Hi there!")
app.add_user_message("Create a file")
app.add_assistant_thinking("Creating file...")

app.run()
```
