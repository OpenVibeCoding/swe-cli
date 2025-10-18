"""Tool schema builders used by SWE-CLI agents."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence


class ToolSchemaBuilder:
    """Assemble tool schemas for NORMAL mode agents."""

    def __init__(self, tool_registry: Union[Any, None]) -> None:
        self._tool_registry = tool_registry

    def build(self) -> list[dict[str, Any]]:
        """Return tool schema definitions including MCP extensions."""
        schemas: list[dict[str, Any]] = deepcopy(_BUILTIN_TOOL_SCHEMAS)

        mcp_schemas = self._build_mcp_schemas()
        if mcp_schemas:
            schemas.extend(mcp_schemas)
        return schemas

    def _build_mcp_schemas(self) -> Sequence[dict[str, Any]]:
        if not self._tool_registry or not getattr(self._tool_registry, "mcp_manager", None):
            return []

        mcp_tools = self._tool_registry.mcp_manager.get_all_tools()  # type: ignore[attr-defined]
        schemas: list[dict[str, Any]] = []
        for tool in mcp_tools:
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description"),
                        "parameters": tool.get("input_schema", {}),
                    },
                }
            )
        return schemas


_BUILTIN_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file with the specified content. Use this when the user asks to create, write, or save a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path where the file should be created (e.g., 'app.py', 'src/main.js')",
                    },
                    "content": {
                        "type": "string",
                        "description": "The complete content to write to the file",
                    },
                    "create_dirs": {
                        "type": "boolean",
                        "description": "Whether to create parent directories if they don't exist",
                        "default": True,
                    },
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit an existing file by replacing old content with new content. Use this to modify, update, or fix code in existing files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to edit",
                    },
                    "old_content": {
                        "type": "string",
                        "description": "The exact text to find and replace in the file",
                    },
                    "new_content": {
                        "type": "string",
                        "description": "The new text to replace the old content with",
                    },
                    "match_all": {
                        "type": "boolean",
                        "description": "Whether to replace all occurrences (true) or just the first one (false)",
                        "default": False,
                    },
                },
                "required": ["file_path", "old_content", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use this when you need to see what's in a file before editing it or to answer questions about file contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to read",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory or search for files matching a pattern. Use this to explore the codebase structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to list",
                        "default": ".",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Optional glob pattern to filter files (e.g., '*.py', '**/*.js')",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search for a pattern in files using ripgrep. Fast and efficient. CRITICAL: NEVER use '.' as path - always use specific files or subdirectories to avoid timeouts. First explore with list_files, then search specific locations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The search pattern (supports regex)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Specific file or directory to search. NEVER use '.' or './'. First list directories, then search specific targets like 'src/', 'opencli/core/', or 'package.json'.",
                    },
                },
                "required": ["pattern", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a bash command. Only use this when explicitly requested by the user. Commands are subject to safety checks and may require approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute (e.g., 'ls -la', 'python test.py')",
                    },
                    "background": {
                        "type": "boolean",
                        "description": "Run command in background (returns immediately with PID). Use for long-running commands like servers.",
                        "default": False,
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_processes",
            "description": "List all running background processes started by run_command with background=true.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_process_output",
            "description": "Get output from a background process. Returns stdout, stderr, status, and exit code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {
                        "type": "integer",
                        "description": "Process ID returned by run_command with background=true",
                    },
                },
                "required": ["pid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kill_process",
            "description": "Kill a background process. Use signal 15 (SIGTERM) for graceful shutdown, or 9 (SIGKILL) to force kill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {
                        "type": "integer",
                        "description": "Process ID to kill",
                    },
                    "signal": {
                        "type": "integer",
                        "description": "Signal to send (15=SIGTERM, 9=SIGKILL)",
                        "default": 15,
                    },
                },
                "required": ["pid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch content from a URL. Useful for reading documentation, APIs, or web pages. Automatically extracts text from HTML.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch (must start with http:// or https://)",
                    },
                    "extract_text": {
                        "type": "boolean",
                        "description": "Whether to extract text from HTML (default: true)",
                        "default": True,
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "Maximum content length in characters (default: 50000)",
                        "default": 50000,
                    },
                },
                "required": ["url"],
            },
        },
    },
]
