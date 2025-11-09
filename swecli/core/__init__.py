"""Core functionality for SWE-CLI."""

import os
import warnings
from importlib import import_module
from typing import Dict, Tuple

# Suppress transformers warning about missing ML frameworks
# SWE-CLI uses LLM APIs directly and doesn't need local models
os.environ["TRANSFORMERS_VERBOSITY"] = "error"  # Only show errors, not warnings
warnings.filterwarnings("ignore", message=".*None of PyTorch, TensorFlow.*found.*")
warnings.filterwarnings("ignore", message=".*Models won't be available.*")

__all__ = [
    "ConfigManager",
    "SessionManager",
    "SwecliAgent",
    "ModeManager",
    "OperationMode",
    "ApprovalManager",
    "ApprovalChoice",
    "ApprovalResult",
    "ErrorHandler",
    "ErrorAction",
    "UndoManager",
    "ToolRegistry",
]

_EXPORTS: Dict[str, Tuple[str, str]] = {
    "SwecliAgent": ("swecli.core.agents", "SwecliAgent"),
    "ConfigManager": ("swecli.core.management", "ConfigManager"),
    "SessionManager": ("swecli.core.management", "SessionManager"),
    "ModeManager": ("swecli.core.management", "ModeManager"),
    "OperationMode": ("swecli.core.management", "OperationMode"),
    "UndoManager": ("swecli.core.management", "UndoManager"),
    "ApprovalManager": ("swecli.core.approval", "ApprovalManager"),
    "ApprovalChoice": ("swecli.core.approval", "ApprovalChoice"),
    "ApprovalResult": ("swecli.core.approval", "ApprovalResult"),
    "ErrorHandler": ("swecli.core.monitoring", "ErrorHandler"),
    "ErrorAction": ("swecli.core.monitoring", "ErrorAction"),
    "ToolRegistry": ("swecli.core.tools", "ToolRegistry"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module 'swecli.core' has no attribute '{name}'")
    module_path, attr_name = _EXPORTS[name]
    module = import_module(module_path)
    attr = getattr(module, attr_name)
    globals()[name] = attr
    return attr
