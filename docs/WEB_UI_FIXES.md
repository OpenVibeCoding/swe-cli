# Web UI Fixes & Redesign Plan

## Issues to Fix

### 1. Chat Functionality Not Working ❌

**Current State:**
- Messages sent from UI don't actually process
- WebSocket handler has TODO comment: "Trigger agent query processing"
- No response comes back from the AI

**Root Cause:**
The WebSocket handler (`_handle_query`) doesn't integrate with the actual agent. It just:
1. Adds message to state
2. Broadcasts to clients
3. Sends "not yet implemented" acknowledgment

**Solution:**

#### A. Create Agent Executor Service
```python
# swecli/web/agent_executor.py
class AgentExecutor:
    """Executes agent queries in background with WebSocket streaming"""

    def __init__(self, state: WebState):
        self.state = state
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def execute_query(self, message: str, ws_manager: WebSocketManager):
        """Execute query and stream results via WebSocket"""
        # 1. Create agent with current config
        # 2. Execute in thread pool
        # 3. Stream chunks back via WebSocket
        # 4. Handle tool calls with approval
```

#### B. Integrate with Existing Agent
- Reuse `swecli.core.agents.SwecliAgent`
- Use same `RuntimeService` as REPL
- Share `SessionManager` for persistence
- Handle tool approval via WebSocket

#### C. Stream Response Chunks
```python
# In agent execution loop:
for chunk in agent.stream_response():
    await ws_manager.broadcast({
        "type": "message_chunk",
        "data": {"content": chunk}
    })
```

---

### 2. UI Styling - Too Dark & Ugly 🎨

**Current State:**
- Dark theme (gray-950 background)
- Heavy, cluttered look
- Not elegant or minimalist

**Desired Style:**
- ✅ Elegant and clean
- ✅ Minimalist
- ✅ Light color scheme (not dark)
- ✅ Monochrome palette
- ✅ Professional

**Design Inspiration:**
- **Linear** - Clean, minimal, professional
- **Notion** - Light, spacious, readable
- **Apple.com** - Elegant typography, whitespace

---

## UI Redesign Plan

### Color Palette (Monochrome + Accent)

```css
/* Base - Light monochrome */
--white: #FFFFFF
--gray-50: #F9FAFB
--gray-100: #F3F4F6
--gray-200: #E5E7EB
--gray-300: #D1D5DB
--gray-400: #9CA3AF
--gray-500: #6B7280
--gray-600: #4B5563
--gray-700: #374151
--gray-800: #1F2937
--gray-900: #111827

/* Accent - Subtle blue */
--blue-50: #EFF6FF
--blue-100: #DBEAFE
--blue-500: #3B82F6
--blue-600: #2563EB

/* Semantic colors */
--background: #FFFFFF
--surface: #F9FAFB
--border: #E5E7EB
--text-primary: #111827
--text-secondary: #6B7280
--accent: #2563EB
```

### Typography

```css
/* Font stack - System fonts for performance */
font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI",
             "Helvetica Neue", Arial, sans-serif;

/* Scale */
--text-xs: 0.75rem    /* 12px */
--text-sm: 0.875rem   /* 14px */
--text-base: 1rem     /* 16px */
--text-lg: 1.125rem   /* 18px */
--text-xl: 1.25rem    /* 20px */
--text-2xl: 1.5rem    /* 24px */

/* Weight */
--font-normal: 400
--font-medium: 500
--font-semibold: 600
```

### Spacing System

```css
/* Consistent spacing scale */
--space-1: 0.25rem   /* 4px */
--space-2: 0.5rem    /* 8px */
--space-3: 0.75rem   /* 12px */
--space-4: 1rem      /* 16px */
--space-6: 1.5rem    /* 24px */
--space-8: 2rem      /* 32px */
--space-12: 3rem     /* 48px */
```

### Component Redesign

#### 1. Header
**Before:** Dark gray with blue accent
**After:**
```
- White background with subtle border
- Clean logo with light weight font
- Connection status: subtle gray dot
- Minimal padding (16px vertical)
```

#### 2. Chat Messages
**Before:** Dark bubbles with emojis
**After:**
```
User messages:
- Light blue background (#EFF6FF)
- Aligned right
- Subtle shadow
- No emojis, just clean text

Assistant messages:
- White background
- Aligned left
- Border instead of background
- Clean monospace for code
```

#### 3. Input Box
**Before:** Dark gray with textarea
**After:**
```
- White background
- Single-line border on top
- Clean textarea with focus ring
- Minimalist send button
- Subtle placeholder text
```

#### 4. Code Blocks
```
- Light gray background (#F9FAFB)
- Monospace font (JetBrains Mono, Fira Code, or system)
- Subtle border
- Copy button on hover
```

### Layout Improvements

#### Spacing
```
Header:        64px height
Chat area:     Flexible with max-width 900px centered
Message gap:   24px between messages
Input:         80px height, sticky bottom
Side padding:  48px on large screens, 16px on mobile
```

#### Borders & Shadows
```
Borders:  1px solid --border (subtle)
Shadows:  Only on interactive elements
          shadow-sm: 0 1px 2px rgba(0,0,0,0.05)
          shadow-md: 0 4px 6px rgba(0,0,0,0.07)
```

### Animation & Transitions

```css
/* Smooth transitions */
transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);

/* Loading animation - subtle pulse */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Message appear animation */
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

---

## Implementation Steps

### Phase 1: Fix Chat Functionality ⚡ (Priority)

1. **Create `agent_executor.py`**
   - Background agent execution
   - WebSocket streaming integration
   - Error handling

2. **Update `websocket.py`**
   - Call agent executor in `_handle_query`
   - Stream response chunks
   - Handle tool calls

3. **Update `server.py`**
   - Initialize agent executor
   - Pass to WebSocket handler

4. **Test end-to-end**
   - Send message → See streaming response
   - Multiple messages in conversation
   - Error handling

### Phase 2: UI Redesign 🎨

1. **Update `tailwind.config.ts`**
   - Add custom color palette
   - Configure typography
   - Add spacing scale

2. **Redesign Components**
   - `Header.tsx` - Light, minimal
   - `MessageList.tsx` - Clean bubbles, better spacing
   - `InputBox.tsx` - Single border, clean input
   - Add animations

3. **Update `index.css`**
   - Remove dark theme
   - Add light monochrome base
   - Custom scrollbar (subtle)
   - Focus styles

4. **Typography & Icons**
   - Remove emojis (👤🤖) - use initials instead
   - Clean, readable fonts
   - Proper hierarchy

### Phase 3: Polish ✨

1. **Smooth Animations**
   - Message slide-in
   - Loading states
   - Hover effects

2. **Responsive Design**
   - Mobile-friendly
   - Tablet breakpoints
   - Desktop max-width

3. **Accessibility**
   - Proper ARIA labels
   - Keyboard navigation
   - Focus indicators

---

## Mockup (Text-based)

```
┌─────────────────────────────────────────────────────────────┐
│  SWE-CLI               Web Interface              ● Connected│  White bg, subtle border
├─────────────────────────────────────────────────────────────┤
│                                                                │
│                                                                │
│   [User Message]                                 ┌───────────┐ Light blue bg
│   Create a Python script for hello world         │ You       │
│                                                   └───────────┘
│                                                                │
│  ┌───────────┐                                                │
│  │ Assistant │  I'll create a simple Python script...        │ White bg, border
│  └───────────┘                                                │
│                 ```python                                      │ Light gray code
│                 print("Hello, World!")                         │
│                 ```                                            │
│                                                                │
│   [User Message]                                 ┌───────────┐
│   Add error handling                             │ You       │
│                                                   └───────────┘
│                                                                │
│  ┌───────────┐                                                │
│  │ Assistant │  I'll add try-except...                        │
│  └───────────┘                                                │
│                                                                │
├─────────────────────────────────────────────────────────────┤ Single border
│                                                                │
│  Type your message...                              [Send]     │ Clean, minimal
│                                                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Expected Outcomes

After fixes:
✅ Chat actually works - messages get AI responses
✅ Streaming responses - see text appear in real-time
✅ Elegant light UI - professional, minimal, clean
✅ Monochrome palette - easy on the eyes
✅ Better typography - readable, hierarchical
✅ Smooth animations - polished feel
✅ Mobile responsive - works on all devices

---

## Timeline

**Day 1:** Fix chat functionality (agent integration)
**Day 2:** UI redesign (colors, layout, components)
**Day 3:** Polish (animations, responsive, testing)

Total: ~3 days for complete transformation
