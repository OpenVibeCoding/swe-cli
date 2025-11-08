"""Context management system for swecli.

This module implements the ACE (Agentic Context Engine) framework directly,
providing intelligent context management through learned strategies.

ACE Components:
    - Playbook: Structured storage for learned strategies (Bullet objects)
    - Generator: Produces answers using playbook strategies
    - Reflector: Analyzes execution outcomes (LLM-powered)
    - Curator: Evolves playbook through delta operations
    - SwecliLLMClient: Adapter for swecli's LLM infrastructure

Based on: Agentic Context Engine (ACE)
Paper: https://arxiv.org/abs/2510.04618
Repository: https://github.com/kayba-ai/agentic-context-engine
"""

import sys
from pathlib import Path

# Add ACE to Python path
_ace_path = Path(__file__).parent.parent.parent.parent / "agentic-context-engine"
if _ace_path.exists() and str(_ace_path) not in sys.path:
    sys.path.insert(0, str(_ace_path))

# Import ACE components directly
from ace import (
    Playbook,
    Bullet,
    Generator,
    Reflector,
    Curator,
    GeneratorOutput,
    ReflectorOutput,
    CuratorOutput,
    DeltaOperation,
    DeltaBatch,
    OfflineAdapter,
    OnlineAdapter,
    Sample,
    TaskEnvironment,
    EnvironmentResult,
)

# Import swecli-specific adapter
from swecli.core.context_management.ace_wrapper import SwecliLLMClient

# Legacy imports for backwards compatibility (deprecated)
from swecli.core.context_management.playbook import SessionPlaybook, Strategy
from swecli.core.context_management.reflection import ExecutionReflector, ReflectionResult

__all__ = [
    # ACE Core Components (recommended)
    "Playbook",
    "Bullet",
    "Generator",
    "Reflector",
    "Curator",
    "GeneratorOutput",
    "ReflectorOutput",
    "CuratorOutput",
    "DeltaOperation",
    "DeltaBatch",
    "OfflineAdapter",
    "OnlineAdapter",
    "Sample",
    "TaskEnvironment",
    "EnvironmentResult",
    # swecli Adapter
    "SwecliLLMClient",
    # Legacy (deprecated, for backwards compatibility)
    "SessionPlaybook",
    "Strategy",
    "ExecutionReflector",
    "ReflectionResult",
]
