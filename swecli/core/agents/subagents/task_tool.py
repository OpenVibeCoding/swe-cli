"""Tool for spawning subagents."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import SubAgentManager

TASK_TOOL_NAME = "spawn_subagent"

TASK_TOOL_DESCRIPTION = """Spawn an ephemeral subagent to handle complex, multi-step tasks with isolated context.

## When to Use
- Complex tasks requiring multiple steps that can be delegated
- Tasks that benefit from isolated context (research, analysis, code review)
- Independent tasks that can run in parallel
- Tasks requiring focused reasoning or heavy token usage

## When NOT to Use
- Simple tasks that can be completed with a few tool calls
- Tasks requiring intermediate feedback or clarification
- Tasks where you need to see the reasoning process

## Available Subagent Types
{subagent_descriptions}

## Usage Notes
1. Each subagent runs with fresh context - provide all necessary information in the description
2. The subagent returns a single result - you won't see intermediate steps
3. Use specific, detailed task descriptions for best results
4. Multiple spawn_subagent calls can run in parallel for independent work"""


def create_task_tool_schema(manager: "SubAgentManager") -> dict[str, Any]:
    """Create the task tool schema with available subagent types.

    Args:
        manager: The SubAgentManager with registered subagents

    Returns:
        OpenAI-compatible tool schema dict
    """
    available_types = manager.get_available_types()
    descriptions = manager.get_descriptions()

    # Build subagent descriptions for tool description
    subagent_lines = []
    for name in available_types:
        desc = descriptions.get(name, "No description")
        subagent_lines.append(f"- **{name}**: {desc}")

    subagent_descriptions = "\n".join(subagent_lines)

    return {
        "type": "function",
        "function": {
            "name": TASK_TOOL_NAME,
            "description": TASK_TOOL_DESCRIPTION.format(
                subagent_descriptions=subagent_descriptions
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": (
                            "Detailed task description for the subagent. "
                            "Include all context needed since the subagent has no access "
                            "to the conversation history."
                        ),
                    },
                    "subagent_type": {
                        "type": "string",
                        "description": "Type of subagent to use for this task",
                        "enum": available_types,
                    },
                },
                "required": ["description", "subagent_type"],
            },
        },
    }


def format_task_result(result: dict[str, Any], subagent_type: str) -> str:
    """Format the task result for display.

    Args:
        result: The result from subagent execution
        subagent_type: The type of subagent that was used

    Returns:
        Formatted result string
    """
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        return f"[{subagent_type}] Task failed: {error}"

    content = result.get("content", "")
    if not content:
        return f"[{subagent_type}] Task completed (no output)"

    return f"[{subagent_type}] {content}"
