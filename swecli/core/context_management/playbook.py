"""Playbook for storing learned strategies across sessions.

Inspired by ACE (Agentic Context Engine) architecture, this module provides
a structured way to store and manage learned patterns and best practices
instead of accumulating verbose conversation history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Strategy:
    """A learned pattern or best practice.

    Strategies are distilled learnings from tool executions, stored in a
    structured format that's more context-efficient than raw conversation messages.

    Attributes:
        id: Unique identifier (e.g., "fil-00042")
        category: Strategy category (e.g., "file_operations", "error_handling")
        content: The actual strategy description
        helpful_count: Number of times this strategy led to success
        harmful_count: Number of times this strategy caused errors
        neutral_count: Number of times with no clear impact
        created_at: When the strategy was first learned
        last_used: When the strategy was last referenced
    """

    id: str
    category: str
    content: str
    helpful_count: int = 0
    harmful_count: int = 0
    neutral_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)

    def tag(self, tag: str) -> None:
        """Update effectiveness counter.

        Args:
            tag: One of "helpful", "harmful", or "neutral"

        Raises:
            ValueError: If tag is not one of the valid options
        """
        if tag == "helpful":
            self.helpful_count += 1
        elif tag == "harmful":
            self.harmful_count += 1
        elif tag == "neutral":
            self.neutral_count += 1
        else:
            raise ValueError(f"Invalid tag: {tag}. Must be helpful, harmful, or neutral")
        self.last_used = datetime.now()

    @property
    def effectiveness_score(self) -> float:
        """Calculate effectiveness score (-1 to 1).

        Returns:
            Score where positive is helpful, negative is harmful
        """
        total = self.helpful_count + self.harmful_count + self.neutral_count
        if total == 0:
            return 0.0
        return (self.helpful_count - self.harmful_count) / total

    def to_dict(self) -> dict:
        """Serialize strategy to dictionary."""
        return {
            "id": self.id,
            "category": self.category,
            "content": self.content,
            "helpful_count": self.helpful_count,
            "harmful_count": self.harmful_count,
            "neutral_count": self.neutral_count,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Strategy":
        """Deserialize strategy from dictionary."""
        return cls(
            id=data["id"],
            category=data["category"],
            content=data["content"],
            helpful_count=data.get("helpful_count", 0),
            harmful_count=data.get("harmful_count", 0),
            neutral_count=data.get("neutral_count", 0),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            ),
            last_used=datetime.fromisoformat(
                data.get("last_used", datetime.now().isoformat())
            ),
        )


class SessionPlaybook:
    """Stores learned strategies for a session.

    The playbook maintains a collection of strategies learned from tool executions.
    Instead of storing raw conversation messages, it stores distilled patterns
    that can be efficiently included in system prompts.

    Example:
        >>> playbook = SessionPlaybook()
        >>> strategy = playbook.add_strategy(
        ...     category="file_operations",
        ...     content="List directory before reading files"
        ... )
        >>> print(playbook.as_context())
        ## Learned Strategies
        ### File Operations
        - [fil-00000] List directory before reading files (helpful=0, harmful=0)
    """

    def __init__(self):
        """Initialize empty playbook."""
        self.strategies: Dict[str, Strategy] = {}
        self._next_id = 0

    def add_strategy(
        self,
        category: str,
        content: str,
        strategy_id: Optional[str] = None,
    ) -> Strategy:
        """Add new strategy to playbook.

        Args:
            category: Strategy category (e.g., "file_operations")
            content: Strategy description
            strategy_id: Optional custom ID (auto-generated if None)

        Returns:
            The created Strategy object

        Example:
            >>> playbook = SessionPlaybook()
            >>> strategy = playbook.add_strategy(
            ...     category="error_handling",
            ...     content="Check parent directory exists before file operations"
            ... )
            >>> strategy.id
            'err-00000'
        """
        if strategy_id is None:
            # Generate ID from category prefix + counter
            prefix = category[:3].lower()
            strategy_id = f"{prefix}-{self._next_id:05d}"
            self._next_id += 1

        strategy = Strategy(id=strategy_id, category=category, content=content)
        self.strategies[strategy_id] = strategy
        return strategy

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get strategy by ID.

        Args:
            strategy_id: Strategy identifier

        Returns:
            Strategy object if found, None otherwise
        """
        return self.strategies.get(strategy_id)

    def tag_strategy(self, strategy_id: str, tag: str) -> bool:
        """Tag a strategy as helpful/harmful/neutral.

        Args:
            strategy_id: Strategy to tag
            tag: One of "helpful", "harmful", or "neutral"

        Returns:
            True if strategy was found and tagged, False otherwise
        """
        strategy = self.strategies.get(strategy_id)
        if strategy:
            strategy.tag(tag)
            return True
        return False

    def remove_strategy(self, strategy_id: str) -> bool:
        """Remove a strategy from the playbook.

        Args:
            strategy_id: Strategy to remove

        Returns:
            True if strategy was found and removed, False otherwise
        """
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            return True
        return False

    def get_strategies_by_category(self, category: str) -> List[Strategy]:
        """Get all strategies in a category.

        Args:
            category: Category name

        Returns:
            List of strategies in that category
        """
        return [s for s in self.strategies.values() if s.category == category]

    def prune_harmful_strategies(self, threshold: float = -0.3) -> int:
        """Remove strategies with negative effectiveness score.

        Args:
            threshold: Effectiveness score threshold (default: -0.3)

        Returns:
            Number of strategies removed

        Example:
            >>> playbook = SessionPlaybook()
            >>> strategy = playbook.add_strategy("test", "Bad strategy")
            >>> strategy.tag("harmful")
            >>> strategy.tag("harmful")
            >>> strategy.tag("helpful")  # Score: (1-2)/3 = -0.33
            >>> removed = playbook.prune_harmful_strategies()
            >>> removed
            1
        """
        to_remove = [
            sid
            for sid, s in self.strategies.items()
            if s.effectiveness_score < threshold and (s.helpful_count + s.harmful_count) > 2
        ]
        for sid in to_remove:
            del self.strategies[sid]
        return len(to_remove)

    def as_context(self, max_strategies: int = 50) -> str:
        """Format strategies for inclusion in system prompt.

        Args:
            max_strategies: Maximum number of strategies to include

        Returns:
            Markdown-formatted string of strategies grouped by category

        Example:
            >>> playbook = SessionPlaybook()
            >>> playbook.add_strategy("file_operations", "List before read")
            >>> print(playbook.as_context())
            ## Learned Strategies
            ### File Operations
            - [fil-00000] List before read (helpful=0, harmful=0)
        """
        if not self.strategies:
            return ""

        # Sort strategies by effectiveness score (best first)
        sorted_strategies = sorted(
            self.strategies.values(),
            key=lambda s: (s.effectiveness_score, s.helpful_count),
            reverse=True,
        )

        # Limit number of strategies
        strategies_to_show = sorted_strategies[:max_strategies]

        # Group by category
        by_category: Dict[str, List[Strategy]] = {}
        for strategy in strategies_to_show:
            by_category.setdefault(strategy.category, []).append(strategy)

        # Format as markdown
        lines = ["\n## Learned Strategies\n"]
        for category, strategies in sorted(by_category.items()):
            category_title = category.replace("_", " ").title()
            lines.append(f"\n### {category_title}\n")
            for s in strategies:
                effectiveness = f"(helpful={s.helpful_count}, harmful={s.harmful_count})"
                lines.append(f"- [{s.id}] {s.content} {effectiveness}\n")

        return "".join(lines)

    def stats(self) -> dict:
        """Get playbook statistics.

        Returns:
            Dictionary with strategy counts and effectiveness metrics
        """
        if not self.strategies:
            return {
                "total_strategies": 0,
                "categories": 0,
                "avg_effectiveness": 0.0,
                "helpful_total": 0,
                "harmful_total": 0,
                "neutral_total": 0,
            }

        categories = set(s.category for s in self.strategies.values())
        effectiveness_scores = [s.effectiveness_score for s in self.strategies.values()]

        return {
            "total_strategies": len(self.strategies),
            "categories": len(categories),
            "avg_effectiveness": sum(effectiveness_scores) / len(effectiveness_scores)
            if effectiveness_scores
            else 0.0,
            "helpful_total": sum(s.helpful_count for s in self.strategies.values()),
            "harmful_total": sum(s.harmful_count for s in self.strategies.values()),
            "neutral_total": sum(s.neutral_count for s in self.strategies.values()),
        }

    def to_dict(self) -> dict:
        """Serialize playbook to dictionary for session storage.

        Returns:
            Dictionary representation of the playbook
        """
        return {
            "strategies": {sid: s.to_dict() for sid, s in self.strategies.items()},
            "next_id": self._next_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionPlaybook":
        """Deserialize playbook from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Reconstructed SessionPlaybook instance
        """
        playbook = cls()
        playbook._next_id = data.get("next_id", 0)

        for sid, sdata in data.get("strategies", {}).items():
            try:
                strategy = Strategy.from_dict(sdata)
                playbook.strategies[sid] = strategy
            except (KeyError, ValueError) as e:
                # Skip malformed strategies
                print(f"Warning: Skipping malformed strategy {sid}: {e}")
                continue

        return playbook

    def __len__(self) -> int:
        """Return number of strategies in playbook."""
        return len(self.strategies)

    def __repr__(self) -> str:
        """Return string representation of playbook."""
        stats = self.stats()
        return (
            f"SessionPlaybook(strategies={stats['total_strategies']}, "
            f"categories={stats['categories']}, "
            f"avg_effectiveness={stats['avg_effectiveness']:.2f})"
        )
