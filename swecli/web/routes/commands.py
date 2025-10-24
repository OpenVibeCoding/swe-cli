"""Commands API endpoints for exposing terminal commands to web UI."""

from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/commands", tags=["commands"])


def get_command_list() -> List[Dict[str, Any]]:
    """Get list of available commands from the same source as terminal.

    Returns a structured list of commands grouped by category.
    """
    return [
        {
            "category": "Operations",
            "commands": [
                {
                    "name": "/run",
                    "args": "<command>",
                    "description": "Execute a bash command safely"
                },
                {
                    "name": "/mode",
                    "args": "<name>",
                    "description": "Switch mode: normal or plan"
                },
                {
                    "name": "/undo",
                    "args": "",
                    "description": "Undo the last operation"
                },
                {
                    "name": "/init",
                    "args": "[path]",
                    "description": "Analyze codebase and generate AGENTS.md with repository guidelines"
                },
                {
                    "name": "/history",
                    "args": "",
                    "description": "Show operation history"
                }
            ]
        },
        {
            "category": "File Operations",
            "commands": [
                {
                    "name": "/tree",
                    "args": "[path]",
                    "description": "Show directory tree"
                }
            ]
        },
        {
            "category": "Session Management",
            "commands": [
                {
                    "name": "/clear",
                    "args": "",
                    "description": "Clear current session context"
                },
                {
                    "name": "/sessions",
                    "args": "",
                    "description": "List all saved sessions"
                },
                {
                    "name": "/resume",
                    "args": "<id>",
                    "description": "Resume a previous session"
                }
            ]
        },
        {
            "category": "Configuration",
            "commands": [
                {
                    "name": "/models",
                    "args": "",
                    "description": "Interactive model/provider selector (use ↑/↓ arrows to choose)"
                }
            ]
        },
        {
            "category": "MCP (Model Context Protocol)",
            "commands": [
                {
                    "name": "/mcp list",
                    "args": "",
                    "description": "List configured MCP servers"
                },
                {
                    "name": "/mcp connect",
                    "args": "<name>",
                    "description": "Connect to an MCP server"
                },
                {
                    "name": "/mcp disconnect",
                    "args": "<name>",
                    "description": "Disconnect from a server"
                },
                {
                    "name": "/mcp tools",
                    "args": "[<name>]",
                    "description": "Show available tools from server(s)"
                },
                {
                    "name": "/mcp test",
                    "args": "<name>",
                    "description": "Test connection to a server"
                }
            ]
        },
        {
            "category": "General",
            "commands": [
                {
                    "name": "/help",
                    "args": "",
                    "description": "Show help message"
                },
                {
                    "name": "/exit",
                    "args": "",
                    "description": "Exit SWE-CLI"
                }
            ]
        }
    ]


@router.get("")
async def list_commands() -> List[Dict[str, Any]]:
    """Get all available commands grouped by category.

    Returns:
        List of command groups with their commands

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        return get_command_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/help")
async def get_help() -> Dict[str, Any]:
    """Get formatted help text similar to terminal /help command.

    Returns:
        Help text and command list

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        commands = get_command_list()
        return {
            "title": "Available Commands",
            "commands": commands,
            "note": "Type commands in the chat input to execute them"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
