"""Factory helpers for assembling agent instances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opencli.core.agents import OpenCLIAgent
from opencli.core.interfaces import AgentInterface, ToolRegistryInterface
from opencli.core.management import ModeManager
from opencli.core.agents import PlanningAgent
from opencli.models.config import AppConfig


@dataclass
class AgentSuite:
    """Pair of agents used across modes."""

    normal: AgentInterface
    planning: AgentInterface


class AgentFactory:
    """Creates conversational agents bound to a shared mode manager and tools."""

    def __init__(
        self,
        config: AppConfig,
        tool_registry: ToolRegistryInterface,
        mode_manager: ModeManager,
    ) -> None:
        self._config = config
        self._tool_registry = tool_registry
        self._mode_manager = mode_manager

    def create_agents(self) -> AgentSuite:
        """Instantiate both normal and planning agents."""
        normal = OpenCLIAgent(self._config, self._tool_registry, self._mode_manager)
        planning = PlanningAgent(self._config, self._tool_registry, self._mode_manager)
        return AgentSuite(normal=normal, planning=planning)

    def refresh_tools(self, suite: AgentSuite) -> None:
        """Refresh tool metadata for both agents."""
        if hasattr(suite.normal, "refresh_tools"):
            suite.normal.refresh_tools()
        if hasattr(suite.planning, "refresh_tools"):
            suite.planning.refresh_tools()
