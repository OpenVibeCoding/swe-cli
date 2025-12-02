"""Factory helpers for assembling agent instances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union

from swecli.core.agents import SwecliAgent
from swecli.core.agents.subagents import SubAgentManager
from swecli.core.base.interfaces import AgentInterface, ToolRegistryInterface
from swecli.core.runtime import ModeManager
from swecli.core.agents import PlanningAgent
from swecli.models.config import AppConfig


@dataclass
class AgentSuite:
    """Pair of agents used across modes."""

    normal: AgentInterface
    planning: AgentInterface
    subagent_manager: Union[SubAgentManager, None] = None


class AgentFactory:
    """Creates conversational agents bound to a shared mode manager and tools."""

    def __init__(
        self,
        config: AppConfig,
        tool_registry: ToolRegistryInterface,
        mode_manager: ModeManager,
        working_dir: Any = None,
        enable_subagents: bool = True,
    ) -> None:
        self._config = config
        self._tool_registry = tool_registry
        self._mode_manager = mode_manager
        self._working_dir = working_dir
        self._enable_subagents = enable_subagents
        self._subagent_manager: Union[SubAgentManager, None] = None

    def create_agents(self) -> AgentSuite:
        """Instantiate both normal and planning agents.

        If subagents are enabled, also creates and registers the SubAgentManager
        with default subagents (general-purpose, researcher, code-reviewer, etc.).
        """
        # Create subagent manager if enabled
        if self._enable_subagents:
            self._subagent_manager = SubAgentManager(
                config=self._config,
                tool_registry=self._tool_registry,
                mode_manager=self._mode_manager,
                working_dir=self._working_dir,
            )
            # Register default subagents
            self._subagent_manager.register_defaults()
            # Register manager with tool registry for task tool execution
            self._tool_registry.set_subagent_manager(self._subagent_manager)

        # Create main agents
        normal = SwecliAgent(self._config, self._tool_registry, self._mode_manager, self._working_dir)
        planning = PlanningAgent(self._config, self._tool_registry, self._mode_manager, self._working_dir)

        return AgentSuite(
            normal=normal,
            planning=planning,
            subagent_manager=self._subagent_manager,
        )

    def refresh_tools(self, suite: AgentSuite) -> None:
        """Refresh tool metadata for both agents."""
        if hasattr(suite.normal, "refresh_tools"):
            suite.normal.refresh_tools()
        if hasattr(suite.planning, "refresh_tools"):
            suite.planning.refresh_tools()
