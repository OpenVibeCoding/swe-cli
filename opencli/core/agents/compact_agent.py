"""Agent specialized in context compaction and summarization."""

from __future__ import annotations

from typing import Dict, List

import requests


class CompactAgent:
    """Agent specialized in context compaction and summarization."""

    SYSTEM_PROMPT = """You are a context compaction specialist for OpenCLI, an AI-powered CLI tool.

Your task: Summarize conversation history while preserving critical information for continuity.

# What to Preserve:
- Files created/edited (paths and purposes)
- Key decisions and user choices made
- Current task and its status
- Important errors encountered and their solutions
- User preferences or requirements stated
- Technical context needed for the next steps
- Unfinished work or pending tasks

# What to Discard:
- Verbose tool outputs (keep only summaries)
- Intermediate reasoning steps
- Redundant information
- Successfully completed sub-tasks that don't need follow-up

# Output Format:
Return a concise structured summary in markdown:

## Files Modified
- `path/to/file.py`: Brief description of changes
- `path/to/another.js`: What was implemented

## Current Task
[Brief description of what we're currently working on]

## Key Context
[Important technical details, decisions, or preferences that affect future work]

## Recent Issues (if any)
[Any errors or blockers that are relevant]

## Next Steps (if clear)
[What should happen next, if it was discussed]

Target: 60-80% token reduction while maintaining conversation continuity.
Be extremely concise but accurate. The user should be able to continue naturally."""

    def __init__(self, config) -> None:
        self.config = config
        self.api_url, self.headers = self._get_api_config()

    def _get_api_config(self) -> tuple[str, dict[str, str]]:
        api_key = self.config.get_api_key()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        if self.config.model_provider == "fireworks":
            api_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        elif self.config.model_provider == "openai":
            api_url = "https://api.openai.com/v1/chat/completions"
        else:
            api_url = f"{self.config.api_base_url}/chat/completions"

        return api_url, headers

    def compact(self, messages: List[Dict]) -> str:
        compactor_messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self._format_history(messages)},
        ]

        payload = {
            "model": self.config.model,
            "messages": compactor_messages,
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=payload,
            timeout=60,
        )
        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")

        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]

    def _format_history(self, messages: List[Dict]) -> str:
        lines = ["# Conversation History to Compact\n"]
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "system":
                continue

            if role == "user":
                lines.append(f"\n**User:** {content[:1000]}")
            elif role == "assistant":
                if msg.get("tool_calls"):
                    tool_names = [tc["function"]["name"] for tc in msg["tool_calls"]]
                    lines.append(
                        f"\n**Assistant:** {content[:500]} [Tools: {', '.join(tool_names)}]"
                    )
                else:
                    lines.append(f"\n**Assistant:** {content[:1000]}")
            elif role == "tool":
                lines.append(f"\n**Tool Result:** {content[:200]}...")

        return "\n".join(lines)
