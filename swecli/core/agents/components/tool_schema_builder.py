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
            "description": "Fetch content from a URL or perform a deep crawl across linked pages. Useful for reading documentation, APIs, or entire site sections. Automatically extracts text from HTML.",
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
                    "deep_crawl": {
                        "type": "boolean",
                        "description": "Follow links and crawl multiple pages starting from the seed URL.",
                        "default": False,
                    },
                    "crawl_strategy": {
                        "type": "string",
                        "enum": ["bfs", "dfs", "best_first"],
                        "description": "Traversal strategy when deep_crawl is true. best_first (default) prioritizes relevance, bfs covers broadly, dfs follows a single branch.",
                        "default": "best_first",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth (beyond the seed page) to crawl when deep_crawl is enabled. Depth 0 is the starting page. Defaults to 1.",
                        "default": 1,
                    },
                    "include_external": {
                        "type": "boolean",
                        "description": "Allow crawling links that leave the starting domain when deep_crawl is enabled.",
                        "default": False,
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Optional cap on the total number of pages to crawl when deep_crawl is enabled.",
                    },
                    "allowed_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional allow-list of domains to keep while deep crawling.",
                    },
                    "blocked_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional block-list of domains to skip while deep crawling.",
                    },
                    "url_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional glob-style URL patterns the crawler must match (e.g., '*docs*').",
                    },
                    "stream": {
                        "type": "boolean",
                        "description": "When true (and deep_crawl is enabled) stream pages as they are discovered before aggregation.",
                        "default": False,
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_todo",
            "description": "Create a new to-do entry that appears in the live inline plan. Always call this before executing a new step.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Human-readable summary of the step you are about to perform.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["todo", "doing", "done"],
                        "description": "Optional initial state. Defaults to todo.",
                        "default": "todo",
                    },
                    "log": {
                        "type": "string",
                        "description": "Optional log entry describing additional context for this task.",
                    },
                    "expanded": {
                        "type": "boolean",
                        "description": "Whether to show log entries under this task in the panel.",
                        "default": True,
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_todo",
            "description": "Update the status/title/log/expanded state of an existing to-do item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "ID of the to-do to update (shown in the panel).",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title for this to-do item.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["todo", "doing", "done"],
                        "description": "Set to 'doing' when you start, 'done' when you finish.",
                    },
                    "log": {
                        "type": "string",
                        "description": "Append a log entry while working on this task.",
                    },
                    "expanded": {
                        "type": "boolean",
                        "description": "Show or hide logs beneath this to-do.",
                    },
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todo",
            "description": "Mark a to-do item as done and optionally append a final log entry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "ID of the to-do item to mark complete.",
                    },
                    "log": {
                        "type": "string",
                        "description": "Optional completion note.",
                    },
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_todos",
            "description": "Render the current to-do panel inside the console output.",
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
            "name": "open_browser",
            "description": "Opens a URL or local file in the user's default web browser. Useful for showing web applications during development (e.g., 'open http://localhost:3000' or 'open index.html'). Automatically handles localhost URLs and converts local file paths to file:// URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL or file path to open in the browser. Supports: full URLs (http://example.com), localhost addresses (localhost:3000), and local file paths (index.html, ./app.html, /path/to/file.html). Local files are automatically converted to file:// URLs.",
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
            "description": "Capture a full-page screenshot (and optionally PDF) of a web page using Crawl4AI. Uses advanced web crawling with Playwright under the hood. Waits for page load, handles dynamic content, and captures full scrollable pages reliably. More robust than Playwright alone for complex pages. Use this when user wants to screenshot a website or web application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the web page to capture (must start with http:// or https://)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional path to save screenshot (relative to working directory or absolute). If not provided, auto-generates filename in temp directory. For PDF, the .pdf extension will be automatically used.",
                    },
                    "capture_pdf": {
                        "type": "boolean",
                        "description": "If true, also capture a PDF version of the page. PDF is more reliable for very long pages. Both screenshot and PDF will be saved if enabled. Default: false",
                        "default": False,
                    },
                    "timeout_ms": {
                        "type": "integer",
                        "description": "Maximum time to wait for page load in milliseconds. Default: 90000 (90 seconds). Complex sites with heavy JavaScript (like SaaS platforms, dashboards) may need 120000-180000ms.",
                        "default": 90000,
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
