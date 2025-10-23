"""Context management system for swecli.

This module implements an ACE-inspired context management system that maintains
useful learnings across sessions without accumulating noisy conversation history.

Key Components:
    - Playbook: Structured storage for learned strategies
    - Reflector: Extracts patterns from tool executions
    - Strategy: Individual learned best practice

Inspired by: Agentic Context Engine (ACE)
Paper: https://arxiv.org/abs/2510.04618
"""

from swecli.core.context_management.playbook import SessionPlaybook, Strategy
from swecli.core.context_management.reflection import ExecutionReflector, ReflectionResult

__all__ = [
    "SessionPlaybook",
    "Strategy",
    "ExecutionReflector",
    "ReflectionResult",
]
