# Textual POC - Testing Instructions

## Quick Start

```bash
# Run the full-screen chat UI
python test_textual_ui_clear.py
```

## What's New (Mouse Scrolling Support Added!)

✅ **Full-screen display** - Terminal completely taken over
✅ **Mouse wheel scrolling** - Scroll through long conversations
✅ **Keyboard scrolling** - Page Up/Down to navigate
✅ **Color-coded messages** - User, assistant, tools, errors
✅ **Status bar** - Mode, context, model info
✅ **Commands** - /help, /clear, /demo, /scroll, /quit

---

## Testing Checklist

### 1. Full-Screen Display

**Run:**
```bash
python test_textual_ui_clear.py
```

**Expected:**
- ✅ Terminal immediately clears
- ✅ NO previous terminal history visible
- ✅ Chat interface fills entire screen
- ✅ Clean borders and layout

---

### 2. Mouse Scrolling

**Steps:**
1. Run the app: `python test_textual_ui_clear.py`
2. Type: `/scroll` and press Enter
3. Wait for 50 messages to be generated
4. Use **mouse wheel** to scroll up
5. Use **mouse wheel** to scroll down

**Expected:**
- ✅ Mouse wheel scrolls the conversation area
- ✅ Can scroll to the top (oldest messages)
- ✅ Can scroll to the bottom (newest messages)
- ✅ Scrolling is smooth

---

### 3. Keyboard Scrolling

**Steps:**
1. After running `/scroll`, click on the conversation area
2. Press **Page Up** to scroll up
3. Press **Page Down** to scroll down

**Expected:**
- ✅ Page Up/Down keys work for scrolling
- ✅ Can navigate through the entire conversation

---

### 4. Message Types

**Run:** `/demo`

**Expected:**
- ✅ User messages (cyan › symbol)
- ✅ Assistant messages (white ⏺ symbol)
- ✅ Tool calls (bright cyan, bold)
- ✅ Tool results (green ⎿ symbol)
- ✅ Errors (red ❌)
- ✅ System messages (gray, italic)

---

### 5. Keyboard Shortcuts

**Test:**
- `Ctrl+L` - Clear conversation
- `Ctrl+C` - Exit application
- `ESC` - Interrupt (shows message)

**Expected:**
- ✅ All shortcuts work as expected
- ✅ Exit is clean (previous terminal restored)

---

### 6. Commands

**Test:**
```
/help       - Shows all commands
/clear      - Clears conversation
/demo       - Shows message types demo
/scroll     - Generates 50 messages for scroll testing
/quit       - Exits application
```

**Expected:**
- ✅ All commands execute correctly
- ✅ Help shows scrolling instructions

---

### 7. Input Field

**Test:**
1. Type a message and press Enter
2. Try typing a long message (multiple lines)
3. Press Enter to send

**Expected:**
- ✅ Messages are sent on Enter
- ✅ Input clears after sending
- ✅ User message appears in conversation
- ✅ Assistant echoes back

---

### 8. Status Bar

**Check:**
- Mode indicator (⏵⏵ normal mode)
- Context percentage (increases as you chat)
- Model name (claude-sonnet-4)
- Help text (Ctrl+C to exit)

**Expected:**
- ✅ All status elements visible
- ✅ Context % updates on messages

---

## Known Issues / Limitations (POC Phase)

**Current limitations (will be fixed in Phase 2):**

1. ❌ **Multi-line input** - Input is single-line only (will add TextArea)
2. ❌ **Command history** - No Up/Down arrow history yet
3. ❌ **Paste detection** - No large paste handling yet
4. ❌ **Autocomplete** - No @ mentions or / command completion yet
5. ❌ **Spinner** - No loading animation during processing
6. ❌ **Modals** - No approval/model selector dialogs yet

**What works perfectly:**
- ✅ Full-screen display
- ✅ Mouse scrolling
- ✅ Keyboard scrolling
- ✅ Message formatting
- ✅ Color coding
- ✅ Commands
- ✅ Status bar
- ✅ Keyboard shortcuts

---

## Troubleshooting

### Problem: Mouse scrolling doesn't work

**Solution 1:** Click on the conversation area first, then try scrolling

**Solution 2:** Use keyboard scrolling (Page Up/Down)

**Solution 3:** Your terminal might not support mouse events. Try:
- iTerm2 (macOS)
- Alacritty (cross-platform)
- Modern Terminal.app (macOS)

### Problem: Still see terminal history

**Solution:** Use `test_textual_ui_clear.py` instead of `test_textual_ui.py`

### Problem: Colors look wrong

**Solution:** Check your terminal supports 256 colors:
```bash
echo $TERM
```
Should show `xterm-256color` or similar.

---

## Next Steps

If all tests pass, we're ready for **Phase 2: Core Features!**

Phase 2 will add:
- Multi-line input (TextArea)
- Command history (Up/Down arrows)
- Paste detection
- Enhanced message formatting
- Real-time updates

**Estimated time:** 1 week

---

## Feedback

Does everything work? Any issues?

Report problems with:
- Terminal emulator name and version
- What doesn't work
- Screenshots if possible

---

**Last Updated:** 2025-01-27
**Status:** Phase 1 POC Complete - Testing Phase
**Next:** Phase 2 Core Features
