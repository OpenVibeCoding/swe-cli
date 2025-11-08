"""ACE (Agentic Context Engine) integration for swecli.

This module provides adapters to use ACE components directly with swecli's
LLM infrastructure, enabling the full Generator/Reflector/Curator workflow.
"""

import sys
from pathlib import Path
from typing import Any, Optional

# Add ACE to Python path
ace_path = Path(__file__).parent.parent.parent.parent / "agentic-context-engine"
if ace_path.exists() and str(ace_path) not in sys.path:
    sys.path.insert(0, str(ace_path))

from ace import LLMClient
from ace.llm import LLMResponse


class SwecliLLMClient(LLMClient):
    """Adapts swecli's AnyLLMClient to ACE's LLMClient interface.

    This allows ACE roles (Generator/Reflector/Curator) to use swecli's
    existing LLM infrastructure without code duplication.

    Example:
        >>> from swecli.core.agents.any_llm_client import AnyLLMClient
        >>> swecli_client = AnyLLMClient(model_name="claude-3-5-sonnet-20241022")
        >>> ace_client = SwecliLLMClient(swecli_client)
        >>>
        >>> # Use with ACE components
        >>> from ace import Generator
        >>> generator = Generator(ace_client)
    """

    def __init__(self, swecli_client: Any):
        """Initialize ACE client adapter.

        Args:
            swecli_client: Instance of swecli's AnyLLMClient or compatible client
        """
        super().__init__(model=getattr(swecli_client, 'model_name', 'unknown'))
        self.client = swecli_client

    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Execute completion using swecli's LLM client.

        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional arguments (ignored for now, ACE uses them for refinement_round)

        Returns:
            LLMResponse with text and raw response data
        """
        # Build messages for swecli client
        messages = [{"role": "user", "content": prompt}]

        # Call swecli's client
        response = self.client.chat_completion(messages)

        # Extract text from response
        if hasattr(response, 'choices') and len(response.choices) > 0:
            text = response.choices[0].message.content
        else:
            # Fallback for different response formats
            text = str(response)

        # Build raw dict
        raw = {}
        if hasattr(response, 'model_dump'):
            raw = response.model_dump()
        elif hasattr(response, 'dict'):
            raw = response.dict()

        return LLMResponse(text=text, raw=raw)
