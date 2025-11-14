"""Factory helpers for assembling agent instances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from swecli.core.agents import SwecliAgent
from swecli.core.agents.deep_langchain_agent import DeepLangChainAgent
from swecli.core.interfaces import AgentInterface, ToolRegistryInterface
from swecli.core.management import ModeManager
from swecli.core.agents import PlanningAgent
from swecli.models.config import AppConfig


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
        working_dir: Any = None,
    ) -> None:
        self._config = config
        self._tool_registry = tool_registry
        self._mode_manager = mode_manager
        self._working_dir = working_dir

    def create_agents(self) -> AgentSuite:
        """Instantiate both normal and planning agents.

        Agent type can be controlled via config.agent_type:
        - "deep_langchain" (default): LangChain Deep Agents implementation
        - "swecli": Traditional SwecliAgent (opt-out)
        """
        # Get agent type, with safe fallback
        agent_type = getattr(self._config, 'agent_type', 'deep_langchain')

        # Select agent class based on config
        if agent_type == "deep_langchain":
            normal = DeepLangChainAgent(
                self._config, self._tool_registry, self._mode_manager, self._working_dir
            )
        elif agent_type == "swecli":
            # Traditional SwecliAgent for backward compatibility
            normal = SwecliAgent(
                self._config, self._tool_registry, self._mode_manager, self._working_dir
            )
        else:
            # Unknown agent type - default to Deep Agent with warning
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Unknown agent_type '{agent_type}', defaulting to deep_langchain")
            normal = DeepLangChainAgent(
                self._config, self._tool_registry, self._mode_manager, self._working_dir
            )

        planning = PlanningAgent(
            self._config, self._tool_registry, self._mode_manager, self._working_dir
        )
        return AgentSuite(normal=normal, planning=planning)

    def refresh_tools(self, suite: AgentSuite) -> None:
        """Refresh tool metadata for both agents."""
        if hasattr(suite.normal, "refresh_tools"):
            suite.normal.refresh_tools()
        if hasattr(suite.planning, "refresh_tools"):
            suite.planning.refresh_tools()
