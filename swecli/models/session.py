"""Session management models."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from swecli.models.message import ChatMessage

if TYPE_CHECKING:
    from swecli.core.context_management import SessionPlaybook


class SessionMetadata(BaseModel):
    """Session metadata for listing and searching."""

    id: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    total_tokens: int
    summary: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    working_directory: Optional[str] = None


class Session(BaseModel):
    """Represents a conversation session.

    The session now includes a playbook for storing learned strategies
    extracted from tool executions, inspired by ACE (Agentic Context Engine).
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: list[ChatMessage] = Field(default_factory=list)
    context_files: list[str] = Field(default_factory=list)
    working_directory: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    playbook: Optional[dict] = Field(default_factory=dict)  # Serialized SessionPlaybook

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )

    def get_playbook(self) -> "SessionPlaybook":
        """Get the session's playbook, creating if needed."""
        from swecli.core.context_management import SessionPlaybook

        if not self.playbook:
            self.playbook = {}
        return SessionPlaybook.from_dict(self.playbook)

    def update_playbook(self, playbook: "SessionPlaybook") -> None:
        """Update the session's playbook."""
        self.playbook = playbook.to_dict()
        self.updated_at = datetime.now()

    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the session."""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def total_tokens(self) -> int:
        """Calculate total token count."""
        return sum(msg.token_estimate() for msg in self.messages)

    def get_metadata(self) -> SessionMetadata:
        """Get session metadata."""
        return SessionMetadata(
            id=self.id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            message_count=len(self.messages),
            total_tokens=self.total_tokens(),
            summary=self.metadata.get("summary"),
            tags=self.metadata.get("tags", []),
            working_directory=self.working_directory,
        )

    def to_api_messages(self, window_size: Optional[int] = None) -> list[dict[str, str]]:
        """Convert to API-compatible message format.

        Args:
            window_size: If provided, only include last N interactions (user+assistant pairs).
                        Following ACE architecture: use small window (3-5) instead of full history.

        Returns:
            List of API messages with tool_calls and tool results preserved.
        """
        # Select messages based on window size
        messages_to_convert = self.messages

        if window_size is not None and len(self.messages) > 0:
            # Count interactions (user+assistant pairs) from the end
            interaction_count = 0
            cutoff_index = 0  # Default: include all messages

            # Walk backwards counting user messages (each starts an interaction)
            for i in range(len(self.messages) - 1, -1, -1):
                if self.messages[i].role.value == "user":
                    interaction_count += 1
                    if interaction_count > window_size:
                        cutoff_index = i + 1  # Don't include this user message
                        break

            messages_to_convert = self.messages[cutoff_index:]

        # Convert selected messages to API format
        result = []
        for msg in messages_to_convert:
            api_msg = {"role": msg.role.value, "content": msg.content}
            # Include tool_calls if present
            if msg.tool_calls:
                api_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.parameters)
                        }
                    }
                    for tc in msg.tool_calls
                ]
                # Add the assistant message with tool_calls
                result.append(api_msg)

                # Add tool result messages for each tool call
                for tc in msg.tool_calls:
                    tool_content = tc.error if tc.error else (tc.result or "")
                    if tc.error:
                        tool_content = f"Error: {tool_content}"
                    result.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_content
                    })
            else:
                result.append(api_msg)
        return result
