# SWE-CLI Web UI Documentation

## Overview

SWE-CLI includes a built-in web interface that runs alongside the terminal REPL, providing a modern browser-based alternative to interact with your AI coding assistant.

## Key Advantages

Unlike third-party tools (like opcode for Claude Code), the SWE-CLI web UI is:

✅ **Native Integration** - Direct access to all SWE-CLI internals, no IPC complexity
✅ **Zero Setup** - No separate installation, just a command flag
✅ **Consistent State** - Shares same session/config as terminal CLI
✅ **Real-time Sync** - Both terminal and web UI stay in sync
✅ **Single Package** - Updates come with SWE-CLI, not separate releases

## Installation

### Install Web Dependencies

```bash
pip install "swecli[web]"
```

This installs:
- `fastapi` - Web server framework
- `uvicorn` - ASGI server
- `websockets` - Real-time communication

## Usage

### Basic Usage

Start SWE-CLI with web UI enabled:

```bash
swecli --enable-ui
```

This will:
1. Start the terminal REPL
2. Launch web server on `http://localhost:8080`
3. Automatically open your browser

### Custom Port

```bash
swecli --enable-ui --ui-port 3000
```

### Custom Host (Allow External Access)

```bash
swecli --enable-ui --ui-host 0.0.0.0
```

⚠️ **Security Warning**: Only use `0.0.0.0` on trusted networks

### Disable Auto-Open Browser

```bash
swecli --enable-ui --no-browser
```

## Features

### Phase 1 (Current) ✅

- **Real-time Chat** - Send queries and receive streaming responses
- **WebSocket Communication** - Live updates without page refresh
- **Message History** - View full conversation history
- **Markdown Rendering** - Formatted code blocks and text
- **Connection Status** - Visual indicator for WebSocket state
- **Dark Theme** - Optimized for coding at night

### Phase 2 (Planned) 🚧

- **Session Management** - List, resume, and switch sessions
- **Session Timeline** - Visual history with branching
- **Export Sessions** - Download as markdown or JSON

### Phase 3 (Planned) 🚧

- **Project Browser** - File tree for working directory
- **Quick Switch** - Change projects from UI
- **Recent Projects** - Easy access to common directories

### Phase 4 (Planned) 🚧

- **Configuration UI** - Provider and model settings
- **MCP Management** - Add/remove/configure servers
- **Analytics Dashboard** - Token usage and cost tracking
- **Visual Charts** - Usage trends over time

### Phase 5 (Planned) 🚧

- **Multi-tab Support** - Multiple simultaneous chats
- **Custom Agents** - Create specialized agents via UI
- **Approval Rules Editor** - Fine-tune auto-approval
- **Codebase Search** - Search files from web UI
- **Diff Viewer** - Syntax-highlighted file changes

## Architecture

### Backend (FastAPI)

```
swecli/web/
├── server.py           # FastAPI application
├── websocket.py        # WebSocket handler
├── state.py            # Shared state manager
└── routes/
    ├── chat.py         # Chat endpoints
    ├── sessions.py     # Session management
    └── config.py       # Configuration
```

### Frontend (React + TypeScript)

```
web-ui/
├── src/
│   ├── components/     # UI components
│   ├── api/            # API client
│   ├── stores/         # State management
│   └── types/          # TypeScript types
└── ...
```

### Communication Flow

```
┌─────────────────┐         ┌─────────────────┐
│  Terminal REPL  │◄───────►│  Shared State   │
└─────────────────┘         └─────────────────┘
                                      ▲
                                      │
                            ┌─────────┴─────────┐
                            │                    │
                       ┌────▼──────┐      ┌─────▼──────┐
                       │ WebSocket │      │  REST API   │
                       └────┬──────┘      └─────┬──────┘
                            │                    │
                       ┌────▼────────────────────▼────┐
                       │      Web UI (Browser)        │
                       └─────────────────────────────┘
```

### State Synchronization

Both terminal and web UI share:
- Session manager (conversation history)
- Configuration manager (settings)
- Mode manager (normal/planning mode)
- Approval manager (tool approval rules)
- Undo manager (operation history)

Changes in one interface immediately reflect in the other.

## API Reference

### REST Endpoints

#### Chat

```
POST   /api/chat/query        # Send query to AI
GET    /api/chat/messages     # Get message history
DELETE /api/chat/clear        # Clear current session
```

#### Sessions

```
GET    /api/sessions          # List all sessions
GET    /api/sessions/current  # Get current session
POST   /api/sessions/{id}/resume   # Resume session
GET    /api/sessions/{id}/export   # Export as JSON
```

#### Configuration

```
GET    /api/config            # Get current config
PUT    /api/config            # Update config
GET    /api/config/providers  # List AI providers
```

### WebSocket Events

#### Client → Server

```typescript
{
  type: "query",
  data: { message: string }
}

{
  type: "approve",
  data: { toolCallId: string, approved: boolean }
}
```

#### Server → Client

```typescript
{
  type: "user_message",
  data: { role: "user", content: string }
}

{
  type: "message_chunk",
  data: { messageId: string, content: string }
}

{
  type: "tool_call",
  data: {
    id: string,
    name: string,
    arguments: object,
    requiresApproval: boolean
  }
}

{
  type: "error",
  data: { message: string }
}
```

## Development

### Running Frontend in Dev Mode

For frontend development with hot reload:

```bash
# Terminal 1: Start SWE-CLI with UI
swecli --enable-ui

# Terminal 2: Start Vite dev server
cd web-ui
npm install
npm run dev
```

Access at `http://localhost:5173` (Vite dev server with hot reload)

### Building Frontend for Production

```bash
cd web-ui
npm run build
```

This builds to `swecli/web/static/` which FastAPI serves.

## Security Considerations

### Local-only by Default

Web server binds to `127.0.0.1` (localhost) by default, preventing external access.

### External Access

To allow external connections:

```bash
swecli --enable-ui --ui-host 0.0.0.0
```

**⚠️ WARNING**: Only use on trusted networks. Anyone with network access can:
- View your conversations
- Send queries to your AI
- Execute approved tool operations

### Future: Token-based Authentication

Planned for external access scenarios:

```bash
swecli --enable-ui --ui-host 0.0.0.0 --ui-token
# Generates: http://localhost:8080?token=abc123xyz
```

## Troubleshooting

### Web UI Won't Start

**Error**: `ImportError: No module named 'fastapi'`

**Solution**: Install web dependencies:
```bash
pip install "swecli[web]"
```

### Port Already in Use

**Error**: `OSError: [Errno 48] Address already in use`

**Solution**: Use a different port:
```bash
swecli --enable-ui --ui-port 3000
```

### WebSocket Connection Failed

**Symptoms**: "Disconnected" status in UI

**Solutions**:
1. Ensure backend is running with `--enable-ui`
2. Check browser console for errors
3. Verify firewall isn't blocking port
4. Try refreshing the page

### Terminal and Web UI Out of Sync

**Symptoms**: Messages appear in terminal but not web UI

**Solutions**:
1. Refresh web page
2. Check WebSocket connection status
3. Restart SWE-CLI with `--enable-ui`

## Comparison with Third-party Tools

| Feature | SWE-CLI Web (Built-in) | opcode (Third-party) |
|---------|----------------------|----------------------|
| Installation | `pip install swecli[web]` | Separate Tauri app download |
| State Sync | Direct (shared memory) | IPC/polling |
| Sessions | Unified | Duplicate config |
| Tool Approval | Shared approval manager | Re-implementation |
| MCP Config | Same config file | Separate config |
| Updates | With SWE-CLI | Separate releases |
| Platform Deps | Python only | Rust + Tauri toolchain |
| Performance | Native Python calls | IPC overhead |

## Roadmap

### Q1 2025
- ✅ Phase 1: Basic chat interface
- 🚧 Phase 2: Session management
- 📅 Phase 3: Project browser

### Q2 2025
- 📅 Phase 4: Configuration & analytics
- 📅 Phase 5: Advanced features
- 📅 Token-based authentication

### Q3 2025
- 📅 Mobile-responsive design
- 📅 Keyboard shortcuts
- 📅 Theme customization

## Contributing

The web UI is part of the main SWE-CLI repository. To contribute:

1. Fork the repository
2. Make changes in `swecli/web/` (backend) or `web-ui/` (frontend)
3. Test locally with `swecli --enable-ui`
4. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.
