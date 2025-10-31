# SWE-CLI Textual UI Redesign Plan

## Objective

Redesign the Textual UI to achieve a more elegant, simple, and clean aesthetic similar to Claude Code's interface. Focus on minimalism, readability, and professional appearance.

---

## Current Design Analysis

### Current State

**Color Palette:**
- Background: `#0a0e14` (very dark blue)
- Accent: `#00ffff` (bright cyan) - **Too bright and harsh**
- Text: `#ffffff` (white)
- Muted text: `#888888` (gray)

**Layout Issues:**
1. ❌ **Bright cyan borders everywhere** - Too visually aggressive
2. ❌ **Solid border on conversation panel** - Creates visual clutter
3. ❌ **Solid border on input area** - Adds unnecessary emphasis
4. ❌ **High contrast cyan accents** - Tiring to look at
5. ✅ Good: Dark background, clean structure
6. ✅ Good: Proper spacing with padding

**Typography:**
- Status bar uses emojis (⏵⏵) and dots (•) as separators
- Mix of bold, dim, and colored text styles

---

## Design Goals (Claude Code Style)

### Principles

1. **Minimalism**: Remove unnecessary visual elements
2. **Subtle accents**: Use muted, professional colors
3. **Borderless design**: No harsh borders, use subtle separators instead
4. **Clean typography**: Consistent, readable fonts without excessive styling
5. **Professional appearance**: Looks like a tool, not a toy
6. **Focus on content**: UI should fade into background, content should shine

### Claude Code Characteristics

- **Minimal borders**: No borders around main panels
- **Subtle separators**: Thin, barely visible lines to separate sections
- **Muted color palette**: Grays, subtle blues, not bright colors
- **Clean status bar**: Simple, unobtrusive information display
- **Generous padding**: Content has breathing room
- **Smooth transitions**: Subtle focus indicators

---

## Redesign Plan

### Phase 1: Color Palette Refinement ⭐ HIGH PRIORITY

**New Color Scheme:**

```scss
// Background colors
$background-primary: #1e1e1e;        // Slightly lighter dark gray
$background-secondary: #252526;      // Subtle variation for depth
$background-elevated: #2d2d2d;       // For focused/hover states

// Text colors
$text-primary: #cccccc;              // Softer white (easier on eyes)
$text-secondary: #808080;            // Muted gray for less important text
$text-muted: #6a6a6a;                // Very subtle text

// Accent colors (muted and professional)
$accent-primary: #007acc;            // Muted blue (VS Code inspired)
$accent-secondary: #4a9eff;          // Lighter blue for highlights
$accent-subtle: #3a3d41;             // Barely visible accent

// Semantic colors
$color-user: #569cd6;                // Muted blue for user messages
$color-assistant: #cccccc;           // Clean white for assistant
$color-system: #6a6a6a;              // Subtle gray for system messages
$color-error: #f48771;               // Soft red for errors
$color-success: #89d185;             // Soft green for success
```

**Changes:**
- Replace bright cyan (`#00ffff`) with muted blue (`#007acc`)
- Softer white for text (`#cccccc` instead of `#ffffff`)
- More nuanced gray tones for hierarchy

### Phase 2: Remove Conversation Panel Border ⭐ HIGH PRIORITY

**Current:**
```css
#conversation {
    border: solid #00ffff;  /* ❌ Harsh cyan border */
    background: #0a0e14;
    padding: 0 1;
}
```

**New:**
```css
#conversation {
    border: none;                     /* ✅ No border */
    background: $background-primary;  /* Clean dark background */
    padding: 1 2;                     /* More generous padding */
}
```

**Rationale:**
- Removes visual clutter
- Makes content the focus
- Cleaner, more professional look
- Matches Claude Code's borderless design

### Phase 3: Simplify Input Area Design ⭐ MEDIUM PRIORITY

**Current:**
```css
#input {
    border: solid #00ffff;  /* ❌ Bright border */
    background: #0a0e14;
}

#input:focus {
    border: solid #00ffff;  /* ❌ Same harsh border */
}
```

**New:**
```css
#input {
    border: none;                      /* ✅ No border by default */
    background: $background-secondary; /* Subtle depth */
    padding: 1 2;
}

#input:focus {
    background: $background-elevated;  /* ✅ Subtle highlight on focus */
    border-left: thin $accent-primary; /* ✅ Subtle left accent only */
}
```

**Features:**
- No border when not focused (cleaner)
- Subtle left accent bar when focused (elegant indicator)
- Background color change for focus feedback
- More professional appearance

### Phase 4: Redesign Status Bar ⭐ MEDIUM PRIORITY

**Current Status Bar:**
```
⏵⏵ normal mode  •  Context: 15%  •  Model: fireworks/...  •  Ctrl+C to exit
```

**Issues:**
- Too many separators (bullets)
- Emojis feel playful, not professional
- Too much information crammed in
- Inconsistent styling

**New Status Bar Design:**

```
NORMAL  │  Context 15%  │  fireworks/kimi-k2-instruct  │  ^C quit
```

**Changes:**
- Remove emoji arrows (⏵⏵)
- Use pipe separators (│) instead of bullets (•)
- Uppercase mode for clarity
- Shorter, cleaner labels
- More consistent spacing
- Professional appearance

**Implementation:**
```python
def update_status(self) -> None:
    mode_style = "bold blue" if self.mode == "normal" else "bold green"
    status = Text()
    status.append(f"{self.mode.upper()}", style=mode_style)
    status.append("  │  ", style="dim")
    status.append(f"Context {self.context_pct}%", style="dim")
    status.append("  │  ", style="dim")
    status.append(self.model, style="dim cyan")
    status.append("  │  ", style="dim")
    status.append("^C quit", style="dim")
    self.update(status)
```

### Phase 5: Improve Typography and Spacing 📝 LOW PRIORITY

**Header:**
```css
Header {
    background: $background-primary;
    color: $text-secondary;          /* ✅ More subtle */
    padding: 0 2;                    /* Better spacing */
}
```

**Footer:**
```css
Footer {
    background: $background-primary;
    color: $text-muted;
}

Footer .footer--key {
    color: $accent-primary;          /* ✅ Muted blue instead of cyan */
    background: transparent;
}
```

**Conversation Log:**
```css
RichLog {
    background: transparent;          /* ✅ Blend with parent */
    color: $text-primary;
    padding: 1 2;                    /* More breathing room */
    scrollbar-gutter: stable;
}
```

### Phase 6: Subtle Focus Indicators 📝 LOW PRIORITY

**Problem:** Current focus uses bright cyan borders

**Solution:** Subtle background changes and minimal accents

```css
/* Conversation focus */
#conversation:focus {
    background: $background-secondary;  /* ✅ Subtle depth change */
    border: none;                       /* ✅ Still no border */
}

/* Input focus - already covered in Phase 3 */
#input:focus {
    background: $background-elevated;
    border-left: thin $accent-primary;
}
```

### Phase 7: Remove Input Label (Optional) 📝 LOW PRIORITY

**Current:**
```
› Type your message (Enter to send, Shift+Enter for new line):
```

**Consideration:** This might be unnecessary visual clutter

**Options:**
1. **Keep but simplify**: `Type your message...`
2. **Remove entirely**: Let placeholder text handle it
3. **Make it subtle**: Use muted gray, smaller text

**Recommendation:** Remove the label, use placeholder in TextArea instead

```python
# In compose method:
yield ChatTextArea(
    id="input",
    placeholder="Type your message (Enter to send, Shift+Enter for new line)",
    soft_wrap=True,
)
```

---

## Implementation Phases

### Phase 1: Quick Wins (30 minutes)

**File:** `swecli/ui_textual/styles/chat.tcss`

1. ✅ Remove conversation panel border
2. ✅ Update color palette variables
3. ✅ Soften text colors
4. ✅ Remove input border

### Phase 2: Status Bar Redesign (20 minutes)

**File:** `swecli/ui_textual/chat_app.py`

1. ✅ Simplify status bar format
2. ✅ Remove emojis
3. ✅ Use pipe separators
4. ✅ Apply muted colors

### Phase 3: Polish and Refinement (20 minutes)

**Files:** Both CSS and Python

1. ✅ Adjust spacing and padding
2. ✅ Test focus states
3. ✅ Verify scrollbar styling
4. ✅ Remove input label (optional)

### Phase 4: Testing (15 minutes)

1. ✅ Visual inspection
2. ✅ Test all interactions
3. ✅ Verify readability
4. ✅ Check focus indicators

---

## Before and After Comparison

### Current Design Issues

```
┌──────────────────────────────────────────┐  ← Bright cyan border
│ [bright cyan text everywhere]            │
│ ⏵⏵ mode • info • more • stuff            │  ← Too busy
│                                           │
│ › Type your message (Enter to send...): │  ← Redundant label
│ ┌────────────────────────────────────┐   │  ← Another bright border
│ │ input text here                     │   │
│ └────────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

### New Design

```
                                              ← No border (clean!)

  [Subtle gray text with muted accents]

  NORMAL │ Context 15% │ model │ ^C quit      ← Clean, professional


  input text here                             ← Subtle focus indicator
  ▌                                           ← Minimal left accent bar



```

---

## Color Comparison

### Current Palette
- `#00ffff` - Bright cyan (harsh, eye-strain)
- `#0a0e14` - Very dark blue background
- `#ffffff` - Pure white text

### New Palette
- `#007acc` - Muted blue (professional)
- `#1e1e1e` - Neutral dark gray (easier to read)
- `#cccccc` - Soft white (less eye-strain)

---

## Expected Benefits

1. **Reduced Eye Strain**: Softer colors are easier on the eyes for long sessions
2. **Professional Appearance**: Looks like enterprise-grade tooling
3. **Better Focus**: Content stands out, UI fades into background
4. **Cleaner Look**: Less visual clutter and noise
5. **Modern Aesthetic**: Matches current design trends (VS Code, GitHub, etc.)
6. **Improved Usability**: Clearer hierarchy and information architecture

---

## Risk Assessment

### Low Risk Changes ✅
- Color palette updates
- Border removal
- Status bar simplification
- Padding adjustments

### Medium Risk Changes ⚠️
- Input label removal (might confuse first-time users)
- Focus indicator changes (must remain visible)

### Mitigation
- Test with real users
- Keep changes reversible
- Document all changes for easy rollback

---

## Success Metrics

After implementation, the UI should:

1. ✅ **Look elegant**: Clean, professional, minimal
2. ✅ **Feel light**: No visual weight or clutter
3. ✅ **Be readable**: Clear hierarchy, good contrast
4. ✅ **Stay functional**: All features remain accessible
5. ✅ **Match brand**: Similar to Claude Code's aesthetic

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Get approval** on color palette changes
3. **Implement Phase 1** (quick wins)
4. **Test and iterate** based on feedback
5. **Deploy remaining phases** incrementally

---

## Files to Modify

1. **`swecli/ui_textual/styles/chat.tcss`** - Main stylesheet
   - Color variables
   - Border removal
   - Spacing updates
   - Focus states

2. **`swecli/ui_textual/chat_app.py`** - Application code
   - Status bar formatting
   - Input label removal (optional)
   - Color references in code

---

## Timeline Estimate

- **Phase 1 (Quick Wins)**: 30 minutes
- **Phase 2 (Status Bar)**: 20 minutes
- **Phase 3 (Polish)**: 20 minutes
- **Phase 4 (Testing)**: 15 minutes

**Total**: ~1.5 hours for complete redesign

---

## Conclusion

This redesign plan transforms the Textual UI from a functional but visually noisy interface into an elegant, professional, Claude Code-inspired terminal application. The focus is on minimalism, subtle design elements, and letting the content shine.

The removal of bright cyan borders, simplification of the status bar, and adoption of a muted color palette will create a more pleasant, professional user experience while maintaining all functionality.

---

**Status**: 📋 **PLAN READY FOR IMPLEMENTATION**
**Priority**: ⭐ **HIGH** (User-requested improvement)
**Effort**: 🕐 **~1.5 hours**
**Risk**: ✅ **LOW** (Purely visual, easily reversible)