# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SWE-CLI** (also referred to internally as "swecli") is an AI-powered command-line coding assistant designed to democratize how coding agents are built and optimized. The project aims to be comparable to state-of-the-art CLI tools while remaining fully open-source.

Key capabilities include:
- Interactive coding agent with codebase understanding
- Shell command execution through LLMs
- Session and context management with automatic compaction
- MCP (Model Context Protocol) integration for external tools
- Multi-provider LLM support (Anthropic, OpenAI, Fireworks, etc.)
- Dual operation modes: Normal and Planning mode

## Development Commands

### Installation and Setup
```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running the Application
```bash
# Start interactive session
swecli

# Non-interactive mode (single prompt)
swecli -p "create hello.py"

# Resume a specific session
swecli -r SESSION_ID

# Continue most recent session for current repo
swecli --continue

# Set working directory
swecli -d /path/to/project
```

### Development Tools
```bash
# Code formatting
black swecli/ --line-length 100

# Linting
ruff check swecli/

# Type checking
mypy swecli/

# Run tests
pytest tests/

# Run specific test file
pytest tests/test_session_manager.py

# Run with verbose output
pytest -v tests/
```

### MCP Server Management
```bash
# List all MCP servers
swecli mcp list

# Add an MCP server
swecli mcp add myserver uvx mcp-server-sqlite

# Add server with environment variables
swecli mcp add api python api.py --env API_KEY=xyz

# Enable/disable servers
swecli mcp enable myserver
swecli mcp disable myserver

# Remove a server
swecli mcp remove myserver
```

## Architecture Overview

### Core Design Principles

SWE-CLI is built on **SOLID principles** with **dependency injection** and **interface-driven design**. The architecture emphasizes:
- Clear separation of concerns through abstract base classes
- Loose coupling via interface abstractions
- Service-oriented architecture with modular responsibilities
- Tool registry pattern for extensibility

### Key Architectural Layers

**1. Core Layer (`swecli/core/`)**
- **Abstract Base Classes** (`core/abstract/`): Define interfaces for agents, managers, monitors, and tools
- **Agents** (`core/agents/`): LLM interaction orchestration
  - `SWE-CLIAgent`: Primary agent for interactive sessions using ReAct pattern
  - `PlanningAgent`: Specialized agent for planning mode
  - Component-based design with separated concerns (HTTP client, response processing, system prompts, tool schemas)
- **Management** (`core/management/`): Configuration, session, mode, and undo managers
- **Approval System** (`core/approval/`): Fine-grained operation approval with rule-based auto-approval
- **Context System** (`core/context/`): Codebase indexing, retrieval, and token monitoring
- **Tool Registry** (`core/tools/`): Dynamic tool registration and execution

**2. REPL Layer (`swecli/repl/`)**
- **Main REPL** (`repl.py`): Interactive loop orchestration
- **Chat Integration** (`repl_chat.py`): Chat UI integration
- **Query Processor** (`query_processor.py`): User query handling and agent coordination
- **Command Handlers** (`repl/commands/`): Slash command implementations (session, file, mode, MCP, help)
- **UI Components** (`repl/ui/`): Message printing, input frames, prompt building, toolbar, context display

**3. UI Layer (`swecli/ui/`)**
- **Chat Application** (`chat_app.py`): Main chat interface using prompt_toolkit
- **Components** (`ui/components/`): Reusable UI elements (animations, status line, task progress, welcome screen)
- **Formatters** (`ui/formatters_internal/`): Output formatting for different tool types (bash, file ops, markdown)
- **Autocomplete** (`ui/autocomplete_internal/`): File and command completion with @ mentions and / commands
- **Modals** (`ui/modals_internal/`): Approval dialogs and rules editor

**4. Tools Layer (`swecli/tools/`)**
- File operations: read, write, edit with diff preview
- Bash command execution with approval flow
- Web fetching for external resources
- MCP tool integration

**5. MCP Integration (`swecli/mcp/`)**
- Server configuration and lifecycle management
- Tool discovery and registration from MCP servers
- Transport layer (stdio) for server communication

### Critical Architectural Patterns

**ReAct Pattern (Reason + Act)**
The agent uses an iterative ReAct loop:
1. User provides a query
2. Agent reasons about the task and decides on tool calls
3. Tools execute (with approval if needed)
4. Results are added to message history
5. Loop continues until task completion (max 10 iterations)

**Dependency Injection**
Core services are injected into the agent via `AgentDependencies`:
- Mode manager (normal/planning)
- Approval manager (operation approval)
- Undo manager (operation history)
- Session manager (conversation persistence)
- Working directory and configuration

**Tool Registry Pattern**
- Tools register themselves with schemas (name, description, parameters)
- Registry handles tool discovery, validation, and execution
- MCP tools dynamically integrate into the registry
- Approval rules can be defined per tool

**Dual-Agent System**
- `SWE-CLIAgent`: Full tool access for execution (Normal mode)
- `PlanningAgent`: Limited to thinking/planning tools (Plan mode)
- Switch between modes with `/mode` command or Shift+Tab

## Configuration

Configuration is loaded from multiple sources (in order of precedence):
1. `~/.swecli/settings.json` (global settings)
2. `.swecli/config.json` (project-specific)
3. Environment variables (e.g., `$FIREWORKS_API_KEY`)

Key configuration options:
- `providers`: LLM provider configurations
- `model`: Model identifier
- `enable_bash`: Enable/disable bash execution
- `permissions.skip_requests`: Skip approval prompts
- `max_undo_history`: Maximum undo operations to track
- `auto_save_interval`: Session auto-save frequency
- `session_dir`: Where to store session files

## Session Management

Sessions persist conversation history with metadata:
- Session ID (8-character hash)
- Working directory
- Message history (user, assistant, system, tool)
- Token usage tracking
- Created/updated timestamps

Sessions are stored in `~/.swecli/sessions/` as JSON files.

Commands:
- `/sessions` - List all sessions
- `/resume SESSION_ID` - Resume a specific session
- `/clear` - Start fresh (archives current session)

## Code Organization Notes

### Entry Points
1. `swecli/cli.py`: Main CLI entry point, argument parsing, MCP command handling
2. `swecli/repl/repl.py`: Interactive REPL initialization and command routing
3. `swecli/repl/repl_chat.py`: Chat UI application (alternative to classic REPL)

### Agent Flow
1. User input → REPL command router
2. If slash command → route to appropriate handler
3. If query → QueryProcessor
4. QueryProcessor → Agent.run_sync()
5. Agent → LLM API call with tool schemas
6. Tool calls → Tool Registry → Tool execution (with approval)
7. Results → back to agent → repeat or finish

### Adding New Tools
1. Implement tool class inheriting from `BaseTool`
2. Define schema (name, description, parameters)
3. Implement `execute()` method
4. Register in `ToolRegistry`
5. Configure approval rules if needed

### Approval System
Operations can be:
- Auto-approved (based on rules)
- User-prompted (modal dialog)
- Denied (based on rules)

Approval rules support:
- Tool name matching
- Parameter patterns (e.g., file path allowlists)
- Mode-specific rules (normal vs. planning)

## Testing Structure

Tests are located in `tests/` with archived experimental tests in `_archived_tests/`.

Current test coverage:
- `test_session_manager.py`: Session creation, loading, message management
- `test_cli_non_interactive.py`: Non-interactive mode execution
- `test_context_compaction.py`: Context compression for long conversations
- `test_session_commands.py`: Slash command handlers

## Known Limitations

- Planning mode is intentionally limited (no file write/bash execution)
- MCP integration requires servers to implement stdio transport
- Async operations in REPL context require careful event loop management
- Context compaction uses simple truncation (LSP-based retrieval planned)
