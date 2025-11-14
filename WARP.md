# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**SWE-CLI** is an AI-powered command-line coding assistant built on SOLID principles with dependency injection and interface-driven design. The project supports multi-provider LLM integration (Anthropic, OpenAI, Fireworks), MCP (Model Context Protocol), shell command execution, and advanced context management.

Key capabilities:
- Interactive coding agent with codebase understanding
- Multi-provider LLM support via native HTTP clients and LangChain
- Session management with conversation persistence
- Dual operation modes: Normal (full tool access) and Planning (thinking only)
- MCP integration for external tool connectivity
- GitHub issue resolution (in development)

## Development Commands

### Installation & Setup
```bash
# Install in development mode
pip install -e .

# Install with dev dependencies (includes pytest, black, ruff, mypy)
pip install -e ".[dev]"

# Set up virtual environment (recommended)
python -m venv .venv && source .venv/bin/activate
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

### Code Quality Tools
```bash
# Format code (100-char line length)
black swecli/ tests/ --line-length 100

# Check formatting without changes
black swecli/ tests/ --check

# Linting
ruff check swecli/ tests/

# Linting with auto-fix
ruff check swecli/ tests/ --fix

# Type checking
mypy swecli/
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_session_manager.py

# Run specific test function
pytest tests/test_file.py::test_name

# Verbose output
pytest -v tests/

# Run tests with async support
pytest tests/ -v --asyncio-mode=auto
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
- **SOLID principles**: Single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion
- **Dependency injection**: Services injected into agents via `AgentDependencies`
- **Interface-driven**: Loose coupling through abstract base classes
- **Service-oriented**: Modular services with clear responsibilities
- **Tool registry pattern**: Dynamic tool registration and execution

### Key Architectural Layers

**1. Core Layer (`swecli/core/`)**
- **Abstract Base Classes** (`core/abstract/`): Define interfaces for agents, managers, monitors, and tools
- **Agents** (`core/agents/`): 
  - `SWE-CLIAgent`: Primary agent using ReAct pattern (Reason + Act) with full tool access
  - `PlanningAgent`: Specialized agent for planning mode with limited tools
  - Component-based design: HTTP client, response processing, system prompts, tool schemas separated
- **Management** (`core/management/`): Configuration, session, mode, and undo managers
- **Approval System** (`core/approval/`): Fine-grained operation approval with rule-based auto-approval
- **Context System** (`core/context/`): Codebase indexing, retrieval, and token monitoring
- **Tool Registry** (`core/tools/`): Dynamic tool registration, validation, and execution
- **Factories** (`core/factories/`): Service instantiation and dependency wiring

**2. REPL Layer (`swecli/repl/`)**
- **Main REPL** (`repl.py`): Interactive loop orchestration and command routing
- **Chat Integration** (`repl_chat.py`): Alternative chat UI using prompt_toolkit
- **Query Processor** (`query_processor.py`): User query handling and agent coordination
- **Command Handlers** (`repl/commands/`): Slash command implementations
  - Session management: `/sessions`, `/resume`, `/clear`
  - File operations: `/read`, `/write`
  - Mode switching: `/mode`
  - MCP: `/mcp`
  - Help: `/help`
- **UI Components** (`repl/ui/`): Message printing, input frames, prompt building, toolbar, context display

**3. UI Layer (`swecli/ui_textual/`)**
- **Chat Application** (`chat_app.py`): Main chat interface using prompt_toolkit
- **Components** (`ui_textual/components/`): Reusable UI elements (animations, status, task progress, welcome screen)
- **Formatters** (`ui_textual/formatters_internal/`): Output formatting for different tool types (bash, file ops, markdown)
- **Autocomplete** (`ui_textual/autocomplete_internal/`): File and command completion with @ mentions and / commands
- **Modals** (`ui_textual/modals/`): Approval dialogs and rules editor

**4. Tools Layer (`swecli/tools/`)**
- File operations: read, write, edit with diff preview
- Bash command execution with approval flow
- Web fetching for external resources
- MCP tool integration

**5. MCP Integration (`swecli/mcp/`)**
- Server configuration and lifecycle management
- Tool discovery and registration from MCP servers
- Transport layer (stdio) for server communication

### Critical Patterns

**ReAct Pattern (Reason + Act)**
The agent uses an iterative loop:
1. User provides query
2. Agent reasons about task and decides on tool calls
3. Tools execute (with approval if needed)
4. Results added to message history
5. Loop continues until task completion (max 10 iterations)

**Dependency Injection**
Core services are injected into agents via `AgentDependencies`:
- Mode manager (normal/planning)
- Approval manager (operation approval)
- Undo manager (operation history)
- Session manager (conversation persistence)
- Working directory and configuration

**Tool Registry**
- Tools register themselves with schemas (name, description, parameters)
- Registry handles tool discovery, validation, and execution
- MCP tools dynamically integrate into registry
- Approval rules can be defined per tool

**Dual-Agent System**
- `SWE-CLIAgent`: Full tool access for execution (Normal mode)
- `PlanningAgent`: Limited to thinking/planning tools (Plan mode)
- Switch between modes with `/mode` command or Shift+Tab

## Configuration

Configuration is loaded from multiple sources (in order of precedence):
1. `~/.swecli/settings.json` (global settings)
2. `.swecli/config.json` (project-specific)
3. Environment variables (e.g., `$FIREWORKS_API_KEY`, `$ANTHROPIC_API_KEY`, `$OPENAI_API_KEY`)

Example configuration (`~/.swecli/settings.json`):
```json
{
  "providers": {
    "fireworks": {
      "api_key": "$FIREWORKS_API_KEY",
      "default_model": "accounts/fireworks/models/llama-v3p1-70b-instruct"
    },
    "anthropic": {
      "api_key": "$ANTHROPIC_API_KEY",
      "default_model": "claude-3-5-sonnet-20241022"
    },
    "openai": {
      "api_key": "$OPENAI_API_KEY",
      "default_model": "gpt-4"
    }
  },
  "experimental": {
    "use_pydantic_ai": false
  },
  "permissions": {
    "skip_requests": true
  },
  "enable_bash": true,
  "max_undo_history": 10,
  "auto_save_interval": 5,
  "session_dir": "~/.swecli/sessions/"
}
```

## Session Management

Sessions persist conversation history with metadata:
- Session ID (8-character hash)
- Working directory
- Message history (user, assistant, system, tool)
- Token usage tracking
- Created/updated timestamps

Sessions are stored in `~/.swecli/sessions/` as JSON files.

REPL commands:
- `/sessions` - List all sessions
- `/resume SESSION_ID` - Resume a specific session
- `/clear` - Start fresh (archives current session)

## Code Organization

### Entry Points
1. `swecli/cli.py`: Main CLI entry point, argument parsing, MCP command handling
2. `swecli/repl/repl.py`: Interactive REPL initialization and command routing
3. `swecli/repl/repl_chat.py`: Alternative chat UI (prompt_toolkit-based)

### Agent Flow
1. User input → REPL command router
2. If slash command → route to appropriate handler
3. If query → `QueryProcessor`
4. `QueryProcessor` → `Agent.run_sync()`
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

## Code Style

- **Line length**: 100 characters
- **Python**: >=3.10, strict typing with mypy
- **Formatting**: Black formatter
- **Linting**: Ruff linter
- **Imports**: Group standard library, third-party, local
- **Naming**: 
  - `snake_case` for functions, variables, modules
  - `PascalCase` for classes
  - `ALL_CAPS` for constants
  - `kebab-case` for CLI option names
- **Error handling**: Use specific exceptions, avoid bare `except`
- **Docstrings**: Google-style with Args/Returns sections
- **Type hints**: Required on public APIs

## Known Limitations

- Planning mode is intentionally limited (no file write/bash execution by design)
- MCP integration requires servers to implement stdio transport
- Async operations in REPL context require careful event loop management
- Context compaction uses simple truncation (LSP-based retrieval is planned)

## Special Directories

- `_archived_docs/`: Archived documentation
- `_archived_tests/`: Archived experimental tests
- `agent-squad/`: Multi-agent coordination experiments
- `agentic-context-engine/`: ACE framework integration (separate project)
- `any-llm/`: LLM abstraction layer experiments
- `claude-code-mcp/`: MCP server for Claude Code integration
- `opencode/`: Alternative implementations/experiments
- `web-ui/`: Web interface (in development)
- `docs/`: Documentation including root_notes with CLAUDE.md and AGENTS.md

## Commit & Pull Request Guidelines

- Keep commits atomic with present-tense imperative subjects
- Reference related issues in commit body when applicable
- Avoid bundling formatting churn with logic changes
- PRs should include: concise summary, verification steps, screenshots for UI changes, confirmation that lint/type check/tests passed
