"""Smoke-test OpenCLI agent wiring (requires real API access)."""

import os
from pathlib import Path

import pytest

from opencli.models.config import AppConfig
from opencli.core.tools import ToolRegistry
from opencli.tools.file_ops import FileOperations
from opencli.tools.write_tool import WriteTool
from opencli.tools.edit_tool import EditTool
from opencli.tools.bash_tool import BashTool
from opencli.core.agents import OpenCLIAgent
from opencli.core.management import ModeManager, OperationMode
from opencli.core.approval import ApprovalManager
from opencli.core.management import UndoManager
from opencli.core.management import SessionManager
from opencli.models.agent_deps import AgentDependencies
from rich.console import Console


pytestmark = pytest.mark.skipif(
    not os.getenv("FIREWORKS_API_KEY"),
    reason="requires FIREWORKS_API_KEY and network access",
)


def test_agent_creates_file(tmp_path: Path) -> None:
    """Run a minimal end-to-end agent invocation that writes a file."""
    config = AppConfig()
    file_ops = FileOperations(config, tmp_path)
    write_tool = WriteTool(config, tmp_path)
    edit_tool = EditTool(config, tmp_path)
    bash_tool = BashTool(config, tmp_path)

    tool_registry = ToolRegistry(
        file_ops=file_ops,
        write_tool=write_tool,
        edit_tool=edit_tool,
        bash_tool=bash_tool,
    )

    mode_manager = ModeManager()
    mode_manager.set_mode(OperationMode.PLAN)  # Avoid interactive approvals

    agent = OpenCLIAgent(config, tool_registry, mode_manager)
    console = Console()

    deps = AgentDependencies(
        mode_manager=mode_manager,
        approval_manager=ApprovalManager(console),
        undo_manager=UndoManager(10),
        session_manager=SessionManager(Path(config.session_dir)),
        working_dir=tmp_path,
        console=console,
        config=config,
    )

    result = agent.run_sync(
        'create a file called test_custom.txt with content "Hello from custom agent!"',
        deps=deps,
    )

    test_file = tmp_path / "test_custom.txt"
    assert test_file.exists(), "expected agent to create target file"
    assert "Hello from custom agent!" in test_file.read_text()
    assert result["success"]
