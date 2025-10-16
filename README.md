<p align="center">
  <h1 align="center">OpenCLI</h1>
</p>
<p align="center">One-Stop CLI-based Coding Agents for Vibe Coding</p>
<p align="center">
  <a href="#"><img alt="Technical Report" src="https://img.shields.io/badge/technical%20report-coming%20soon-blue?style=flat-square" /></a>
  <a href="#"><img alt="Website" src="https://img.shields.io/badge/website-coming%20soon-blue?style=flat-square" /></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green?style=flat-square" /></a>
  <a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/python-3.9+-blue?style=flat-square" /></a>
</p>

---

OpenCLI is a sophisticated command-line interface that integrates LLM-powered AI agents directly into your development environment. Designed for "vibe coding" - a fluid, intuitive development experience where AI assistance feels natural and seamless - OpenCLI combines powerful AI capabilities with a beautiful, responsive terminal UI.

### Features

- **Elegant Split-Screen Interface** - Chat-style interaction with scrollable conversation history and fixed input at the bottom
- **Dual Operating Modes** - Normal Mode for direct code execution with interactive approval, Plan Mode for strategic planning and analysis
- **Real-Time Interruption** - Press `ESC` to instantly interrupt any running operation
- **Smart File Mentions** - Use `@filename` to reference files with intelligent autocomplete
- **Tool Integration** - Seamless file operations, command execution, and project navigation
- **Session Management** - Automatic session saving and restoration across sessions
- **Context Awareness** - Real-time token counting and intelligent context management
- **MCP Server Support** - Extensible architecture with Model Context Protocol integration

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/OpenCLI.git
cd OpenCLI

# Install dependencies
pip install -r requirements.txt

# Set up your API key
export ANTHROPIC_API_KEY="your-api-key-here"
# Or use other providers
# export OPENAI_API_KEY="your-api-key-here"

# Start OpenCLI
python -m opencli.main
```

> [!TIP]
> Requires Python 3.9+ and a terminal with 256-color support for optimal display.

### Documentation

For more info on how to use OpenCLI [**head over to our docs**](./docs).

### Usage

Simply type your coding requests naturally:

```
› build a python script to analyze log files
› refactor the authentication module to use JWT
› explain what this code does @src/main.py
```

| Shortcut | Action |
|----------|--------|
| `Shift+Tab` | Toggle between Plan/Normal mode |
| `ESC` | Interrupt current operation |
| `Ctrl+C` (twice) | Exit application |
| `Ctrl+L` | Clear conversation |
| `↑` / `↓` | Navigate command history |
| `@` | Trigger file autocomplete |
| `/` | Trigger slash command autocomplete |

#### Operating Modes

- **Normal Mode** (`▶`) - Direct code execution with interactive command approval, best for iterative development
- **Plan Mode** (`⏸`) - Strategic analysis and planning without automatic execution, ideal for understanding complex problems

Toggle between modes with `Shift+Tab` or use `/mode plan` and `/mode normal`.

#### Slash Commands

```
/help        Show available commands
/mode        Switch operating mode
/session     Manage sessions
/tree        Show project structure
/clear       Clear conversation
```

### Contributing

OpenCLI is designed to be extensible and community-driven.

> [!IMPORTANT]
> We encourage contributions for bug fixes, performance improvements, documentation, and provider support.

To run OpenCLI locally:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black opencli/
```

### Architecture

OpenCLI is built with a modular architecture:

- **Async Query Processor** - Handles LLM interactions with ReAct loop
- **Tool Executor** - Manages tool execution with approval flow
- **Context Compactor** - Intelligent context window management
- **Chat UI** - Beautiful split-screen terminal interface
- **Key Binding Manager** - Sophisticated keyboard interaction handling

### Configuration

Configure OpenCLI through environment variables or config file:

```bash
# Environment Variables
export ANTHROPIC_API_KEY="your-key"
export OPENCLI_MODEL="your-model-name"
```

Or use `.opencli/config.json`:

```json
{
  "model": "your-model-name",
  "auto_save_interval": 5,
  "context_limit": 256000
}
```

---

**Made for vibe coding** • [License: MIT](LICENSE)
