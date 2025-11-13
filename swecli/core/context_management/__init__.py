"""Native swecli ACE (Agentic Context Engine) implementation.

This module provides a complete native re-implementation of the ACE framework
within swecli, without external dependencies.

ACE Components:
    - Playbook: Structured storage for learned strategies (Bullet objects)
    - Generator: Produces answers using playbook strategies
    - Reflector: Analyzes execution outcomes (LLM-powered)
    - Curator: Evolves playbook through delta operations
    - Delta operations: ADD, UPDATE, TAG, REMOVE mutations

Based on: Agentic Context Engine (ACE)
Paper: https://arxiv.org/abs/2510.04618
Repository: https://github.com/kayba-ai/agentic-context-engine
"""

# Import native ACE components
from swecli.core.context_management.playbook import Playbook, Bullet
from swecli.core.context_management.delta import DeltaOperation, DeltaBatch
from swecli.core.context_management.roles import (
    AgentResponse,
    Reflector,
    Curator,
    ReflectorOutput,
    CuratorOutput,
)

# Legacy imports for backwards compatibility (deprecated)
from swecli.core.context_management.playbook import SessionPlaybook, Strategy
from swecli.core.context_management.reflection import ExecutionReflector, ReflectionResult

__all__ = [
    # Native ACE Components (recommended)
    "Playbook",
    "Bullet",
    "AgentResponse",
    "Reflector",
    "Curator",
    "ReflectorOutput",
    "CuratorOutput",
    "DeltaOperation",
    "DeltaBatch",
    # Legacy (deprecated, for backwards compatibility)
    "SessionPlaybook",
    "Strategy",
    "ExecutionReflector",
    "ReflectionResult",
]
