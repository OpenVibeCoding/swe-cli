"""Approval rules system for pattern-based command approval."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class RuleAction(Enum):
    AUTO_APPROVE = "auto_approve"
    AUTO_DENY = "auto_deny"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_EDIT = "require_edit"


class RuleType(Enum):
    PATTERN = "pattern"
    COMMAND = "command"
    PREFIX = "prefix"
    DANGER = "danger"


@dataclass
class ApprovalRule:
    id: str
    name: str
    description: str
    rule_type: RuleType
    pattern: str
    action: RuleAction
    enabled: bool = True
    priority: int = 0
    created_at: Optional[str] = None
    modified_at: Optional[str] = None

    def matches(self, command: str) -> bool:
        if not self.enabled:
            return False

        if self.rule_type == RuleType.PATTERN:
            try:
                return bool(re.search(self.pattern, command))
            except re.error:
                return False
        if self.rule_type == RuleType.COMMAND:
            return command == self.pattern
        if self.rule_type == RuleType.PREFIX:
            return command.startswith(self.pattern)
        if self.rule_type == RuleType.DANGER:
            try:
                return bool(re.search(self.pattern, command))
            except re.error:
                return False
        return False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["rule_type"] = self.rule_type.value
        data["action"] = self.action.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRule":
        data["rule_type"] = RuleType(data["rule_type"])
        data["action"] = RuleAction(data["action"])
        return cls(**data)


@dataclass
class CommandHistory:
    command: str
    approved: bool
    edited_command: Optional[str] = None
    timestamp: Optional[str] = None
    rule_matched: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommandHistory":
        return cls(**data)


class ApprovalRulesManager:
    """Manager for approval rules and command history.

    Rules and history are session-scoped (in-memory only), not persisted to disk.
    Each conversation session has its own isolated set of rules.
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize with empty in-memory rules (session-scoped).

        Args:
            config_dir: Unused - kept for backward compatibility
        """
        self.rules: List[ApprovalRule] = []
        self.history: List[CommandHistory] = []

        # Initialize default safety rules
        self._initialize_default_rules()

    def _load_rules(self) -> None:
        """No-op: Rules are session-scoped, not persisted to disk."""
        pass

    def _save_rules(self) -> None:
        """No-op: Rules are session-scoped, not persisted to disk."""
        pass

    def _load_history(self) -> None:
        """No-op: History is session-scoped, not persisted to disk."""
        pass

    def _save_history(self) -> None:
        """No-op: History is session-scoped, not persisted to disk."""
        pass

    def _initialize_default_rules(self) -> None:
        if self.rules:
            return

        default_rules = [
            ApprovalRule(
                id="default_danger_rm",
                name="Dangerous rm commands",
                description="Require approval for dangerous rm commands",
                rule_type=RuleType.DANGER,
                pattern=r"rm\s+(-rf?|-fr?)\s+(/|\*|~)",
                action=RuleAction.REQUIRE_APPROVAL,
                priority=100,
                created_at=datetime.now().isoformat(),
            ),
            ApprovalRule(
                id="default_danger_chmod",
                name="Dangerous chmod 777",
                description="Require approval for chmod 777",
                rule_type=RuleType.DANGER,
                pattern=r"chmod\s+777",
                action=RuleAction.REQUIRE_APPROVAL,
                priority=100,
                created_at=datetime.now().isoformat(),
            ),
            ApprovalRule(
                id="default_safe_ls",
                name="Auto-approve ls commands",
                description="Automatically approve safe ls commands",
                rule_type=RuleType.PREFIX,
                pattern="ls ",
                action=RuleAction.AUTO_APPROVE,
                priority=10,
                created_at=datetime.now().isoformat(),
            ),
        ]

        self.rules.extend(default_rules)
        self._save_rules()

    def evaluate_command(self, command: str) -> Optional[ApprovalRule]:
        enabled_rules = [r for r in self.rules if r.enabled]
        for rule in sorted(enabled_rules, key=lambda r: r.priority, reverse=True):
            if rule.matches(command):
                return rule
        return None

    def add_rule(self, rule: ApprovalRule) -> None:
        self.rules.append(rule)
        self._save_rules()

    def update_rule(self, rule_id: str, **updates: Any) -> bool:
        for rule in self.rules:
            if rule.id == rule_id:
                for key, value in updates.items():
                    setattr(rule, key, value)
                rule.modified_at = datetime.now().isoformat()
                self._save_rules()
                return True
        return False

    def remove_rule(self, rule_id: str) -> bool:
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]
        if len(self.rules) != before:
            self._save_rules()
            return True
        return False

    def add_history(self, command: str, approved: bool, *, edited_command: Optional[str] = None, rule_matched: Optional[str] = None) -> None:
        entry = CommandHistory(
            command=command,
            approved=approved,
            edited_command=edited_command,
            timestamp=datetime.now().isoformat(),
            rule_matched=rule_matched,
        )
        self.history.append(entry)
        self._save_history()
