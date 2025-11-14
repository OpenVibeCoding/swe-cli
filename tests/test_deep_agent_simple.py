"""Simple test script for DeepLangChainAgent.

Tests basic functionality without tool calls.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from swecli.core.agents.deep_langchain_agent import DeepLangChainAgent
from swecli.core.management import ModeManager
from swecli.models.config import AppConfig


class MockToolRegistry:
    """Mock tool registry for testing."""

    def get_all_tools(self):
        """Return empty tool list for simple tests."""
        return []


def test_simple_query():
    """Test Deep Agent with a simple query (no tools)."""
    print("\n" + "="*80)
    print("Testing DeepLangChainAgent with simple query (no tools)")
    print("="*80 + "\n")

    # Create config
    config = AppConfig(
        model_provider="fireworks",
        model="accounts/fireworks/models/llama-v3p1-8b-instruct",
        api_key=os.getenv("FIREWORKS_API_KEY"),
        temperature=0.7,
        max_tokens=1000,
    )

    # Create mock dependencies
    tool_registry = MockToolRegistry()
    mode_manager = ModeManager()

    # Create agent
    print("Creating DeepLangChainAgent...")
    agent = DeepLangChainAgent(
        config=config,
        tool_registry=tool_registry,
        mode_manager=mode_manager,
        working_dir=os.getcwd(),
    )

    print(f"Agent created: {agent}")
    print(f"Deep agent available: {agent._deep_agent is not None}")
    print()

    # Test simple query
    test_message = "What is 2 + 2? Answer in one short sentence."

    print(f"Testing with message: '{test_message}'")
    print()

    try:
        result = agent.run_sync(
            message=test_message,
            deps=None,
            message_history=[],
        )

        print("\n" + "-"*80)
        print("RESULT:")
        print("-"*80)
        print(f"Success: {result.get('success')}")
        print(f"Content: {result.get('content')}")
        print(f"Error: {result.get('error')}")
        print("-"*80 + "\n")

        return result.get('success', False)

    except Exception as e:
        import traceback
        print("\n" + "-"*80)
        print("ERROR:")
        print("-"*80)
        print(f"Exception: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print("-"*80 + "\n")
        return False


if __name__ == "__main__":
    success = test_simple_query()
    sys.exit(0 if success else 1)
