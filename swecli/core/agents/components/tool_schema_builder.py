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
            "description": "Execute any bash/shell command. Use this whenever the user asks you to run a command. Commands are subject to safety checks and may require approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
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
    {
        "type": "function",
        "function": {
            "name": "open_browser",
            "description": "Opens a URL in the user's default web browser. Useful for showing web applications during development (e.g., 'open http://localhost:3000'). Automatically handles localhost URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to open in the browser. Can be a full URL (http://example.com) or localhost address (localhost:3000)",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_screenshot",
            "description": "Capture a screenshot and save it to a temporary location. The user can then reference this screenshot in their queries by mentioning the file path. Useful when the user wants to discuss or analyze a screenshot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "monitor": {
                        "type": "integer",
                        "description": "Monitor number to capture (default: 1 for primary monitor)",
                        "default": 1,
                    },
                    "region": {
                        "type": "object",
                        "description": "Optional region to capture (x, y, width, height). If not provided, captures full screen.",
                        "properties": {
                            "x": {"type": "integer", "description": "X coordinate"},
                            "y": {"type": "integer", "description": "Y coordinate"},
                            "width": {"type": "integer", "description": "Width in pixels"},
                            "height": {"type": "integer", "description": "Height in pixels"},
                        },
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_screenshots",
            "description": "List all captured screenshots in the temporary directory. Shows the 10 most recent screenshots with their paths, sizes, and timestamps.",
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
            "name": "clear_screenshots",
            "description": "Clear old screenshots from the temporary directory to free up disk space. By default, keeps the 5 most recent screenshots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keep_recent": {
                        "type": "integer",
                        "description": "Number of recent screenshots to keep (default: 5)",
                        "default": 5,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_image",
            "description": "Analyze an image using the configured Vision Language Model (VLM). Supports both local image files and online URLs. Only available if user has configured a VLM model via /models command. Use this when user asks to analyze, describe, or extract information from images.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt describing what to analyze in the image (e.g., 'Describe this image', 'What errors do you see?', 'Extract text from this image')",
                    },
                    "image_path": {
                        "type": "string",
                        "description": "Path to local image file (relative to working directory or absolute). Supports .jpg, .jpeg, .png, .gif, .webp. Takes precedence over image_url if both provided.",
                    },
                    "image_url": {
                        "type": "string",
                        "description": "URL of online image (must start with http:// or https://). Used only if image_path not provided.",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response (optional, defaults to config value)",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_web_screenshot",
            "description": "Capture a full-page screenshot of a web page using Playwright. Better than capture_screenshot for web pages as it waits for page load, handles dynamic content, and captures full scrollable pages. Automatically clips to actual content height to avoid excessive whitespace. Use this when user wants to screenshot a website or web application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the web page to capture (must start with http:// or https://)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional path to save screenshot (relative to working directory or absolute). If not provided, auto-generates filename in temp directory.",
                    },
                    "wait_until": {
                        "type": "string",
                        "description": "When to consider page loaded: 'load' (load event), 'domcontentloaded' (DOM ready), or 'networkidle' (no requests for 500ms, recommended). Default: 'networkidle'",
                        "enum": ["load", "domcontentloaded", "networkidle"],
                        "default": "networkidle",
                    },
                    "timeout_ms": {
                        "type": "integer",
                        "description": "Maximum time to wait for page load in milliseconds. Default: 30000 (30 seconds)",
                        "default": 30000,
                    },
                    "full_page": {
                        "type": "boolean",
                        "description": "Whether to capture full scrollable page (true) or just viewport (false). Default: true",
                        "default": True,
                    },
                    "viewport_width": {
                        "type": "integer",
                        "description": "Browser viewport width in pixels. Default: 1920",
                        "default": 1920,
                    },
                    "viewport_height": {
                        "type": "integer",
                        "description": "Browser viewport height in pixels. Default: 1080",
                        "default": 1080,
                    },
                    "clip_to_content": {
                        "type": "boolean",
                        "description": "If true, automatically detect actual content height and clip to avoid excessive whitespace. Only works with full_page=true. Default: true. Set to false if you need the full scrollable area including whitespace.",
                        "default": True,
                    },
                    "max_height": {
                        "type": "integer",
                        "description": "Optional maximum screenshot height in pixels. Prevents extremely tall screenshots. If content height exceeds this, screenshot will be clipped to this height.",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_web_screenshots",
            "description": "List all captured web screenshots in the temporary directory. Shows the 10 most recent web screenshots with their paths, sizes, and timestamps.",
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
            "name": "clear_web_screenshots",
            "description": "Clear old web screenshots from the temporary directory to free up disk space. By default, keeps the 5 most recent web screenshots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keep_recent": {
                        "type": "integer",
                        "description": "Number of recent web screenshots to keep (default: 5)",
                        "default": 5,
                    },
                },
                "required": [],
            },
        },
    },
]
