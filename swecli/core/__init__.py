"""Core functionality for SWE-CLI."""

from swecli.core.agents import SwecliAgent
from swecli.core.approval import ApprovalChoice, ApprovalManager, ApprovalResult
from swecli.core.management import ConfigManager, ModeManager, OperationMode, SessionManager, UndoManager
from swecli.core.monitoring import ErrorAction, ErrorHandler
from swecli.core.tools import ToolRegistry

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
