"""ACE (Adaptive Context Engine) component initialization."""

from swecli.core.context_engineering.memory import Reflector, Curator


class AgentClientAdapter:
    """Adapts agent interface to LLM client interface expected by ACE components."""

    def __init__(self, agent):
        """Initialize adapter.

        Args:
            agent: Agent to adapt
        """
        self.agent = agent

    def chat_completion(self, messages):
        """Call agent's LLM with messages.

        Args:
            messages: List of message dictionaries

        Returns:
            Response dictionary
        """
        response = self.agent.call_llm(messages)
        return response


class ACEIntegration:
    """Manages ACE components for playbook evolution."""

    def __init__(self):
        """Initialize ACE integration."""
        self._reflector = None
        self._curator = None

    def initialize_components(self, agent):
        """Initialize ACE components lazily on first use.

        Args:
            agent: Agent to use for LLM calls

        Returns:
            Tuple of (reflector, curator)
        """
        if self._reflector is None:
            # Create adapter to convert agent interface to LLM client interface
            client_adapter = AgentClientAdapter(agent)

            # Initialize ACE roles with adapted client
            self._reflector = Reflector(client_adapter)
            self._curator = Curator(client_adapter)

        return self._reflector, self._curator

    @property
    def reflector(self):
        """Get the reflector component."""
        return self._reflector

    @property
    def curator(self):
        """Get the curator component."""
        return self._curator
