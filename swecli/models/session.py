"""Session management models."""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from swecli.models.message import ChatMessage


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
    """Represents a conversation session."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: list[ChatMessage] = Field(default_factory=list)
    context_files: list[str] = Field(default_factory=list)
    working_directory: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )

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

    def to_api_messages(self) -> list[dict[str, str]]:
        """Convert to API-compatible message format."""
        return [{"role": msg.role.value, "content": msg.content} for msg in self.messages]
