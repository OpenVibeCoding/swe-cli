# Trackpad Scrolling - How to Use

## The Issue
Trackpad scrolling requires the conversation area to be **focused** first. By default, the input field has focus (so you can type).

## The Solution ✅

### **Method 1: Focus Switch (Recommended for Trackpad)**

1. Run the app:
   ```bash
   python test_textual_ui_clear.py
   ```

2. Generate some messages:
   ```
   /scroll
   ```

3. **Press `Ctrl+Up`** to focus the conversation area
   - You'll see: "📜 Conversation focused - use arrow keys or trackpad to scroll"

4. Now use your **trackpad** to scroll up and down!
   - Two-finger swipe up/down
   - Should work smoothly

5. When done scrolling, press **`Ctrl+Down`** to return focus to input field

---

### **Method 2: Arrow Keys (Always Works)**

1. Press `Ctrl+Up` to focus conversation
2. Use **Arrow Up/Down** keys to scroll line by line
3. Use **Page Up/Down** to scroll by page
4. Press `Ctrl+Down` to return to input

---

### **Method 3: Click to Focus**

1. Generate messages with `/scroll`
2. **Click** on the conversation area with your mouse/trackpad
3. Now trackpad scrolling should work
4. Click on input field when you want to type again

---

## Quick Reference

| Key Combo | Action |
|-----------|--------|
| **`Ctrl+Up`** | Focus conversation (for scrolling) |
| **`Ctrl+Down`** | Focus input (for typing) |
| `Arrow Up` | Scroll up one line |
| `Arrow Down` | Scroll down one line |
| `Page Up` | Scroll up one page |
| `Page Down` | Scroll down one page |

---

## Why This Happens

Textual (like most TUI frameworks) uses **keyboard focus** to determine which widget receives events. When the input field has focus, it captures arrow keys for cursor movement. When the conversation has focus, those same keys scroll the text.

The trackpad gestures work the same way - they only scroll the focused widget.

---

## Test It Now!

```bash
python test_textual_ui_clear.py
```

Then:
1. Type: `/scroll`
2. Press: `Ctrl+Up`
3. Use trackpad to scroll!

---

## Still Not Working?

**Check your terminal:**
- Some terminals don't support trackpad events properly
- Try: iTerm2 (macOS), Alacritty, or modern Terminal.app

**Alternative:**
- Use arrow keys instead (`Ctrl+Up` then arrow up/down)
- Page Up/Down always works

---

Let me know if trackpad scrolling works now! 🎯
