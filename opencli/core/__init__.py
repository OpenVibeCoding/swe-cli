"""Core functionality for OpenCLI."""

from opencli.core.agents import OpenCLIAgent
from opencli.core.approval import ApprovalChoice, ApprovalManager, ApprovalResult
from opencli.core.management import ConfigManager, ModeManager, OperationMode, SessionManager, UndoManager
from opencli.core.monitoring import ErrorAction, ErrorHandler
from opencli.core.tools import ToolRegistry

__all__ = [
    "ConfigManager",
    "SessionManager",
    "OpenCLIAgent",
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
