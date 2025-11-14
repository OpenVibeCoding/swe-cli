"""Test script for DeepLangChainAgent with tool calls.

Tests tool execution functionality.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from swecli.core.agents.deep_langchain_agent import DeepLangChainAgent
from swecli.core.management import ModeManager
from swecli.core.tools.registry import ToolRegistry
from swecli.models.config import AppConfig


def test_with_simple_tool():
    """Test Deep Agent with a simple tool call (read_file)."""
    print("\n" + "="*80)
    print("Testing DeepLangChainAgent with simple tool call (read_file)")
    print("="*80 + "\n")

    # Create a test file to read
    test_file = Path(__file__).parent / "test_sample.txt"
    test_file.write_text("Hello from test file! This is a simple test.")
    print(f"Created test file: {test_file}")
    print()

    # Create config
    config = AppConfig(
        model_provider="fireworks",
        model="accounts/fireworks/models/llama-v3p1-8b-instruct",
        api_key=os.getenv("FIREWORKS_API_KEY"),
        temperature=0.7,
        max_tokens=1000,
    )

    # Create real tool registry
    tool_registry = ToolRegistry()

    # Create mode manager
    mode_manager = ModeManager()

    # Create agent
    print("Creating DeepLangChainAgent with real tools...")
    agent = DeepLangChainAgent(
        config=config,
        tool_registry=tool_registry,
        mode_manager=mode_manager,
        working_dir=test_file.parent,
    )

    print(f"Agent created: {agent}")
    print(f"Deep agent available: {agent._deep_agent is not None}")
    print(f"Available tools: {agent.get_available_tools()}")
    print()

    # Test with tool call request
    test_message = f"Please read the file at {test_file} and tell me what it contains."

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

        # Cleanup
        test_file.unlink(missing_ok=True)
        print(f"Cleaned up test file: {test_file}")

        return result.get('success', False)

    except Exception as e:
        import traceback
        print("\n" + "-"*80)
        print("ERROR:")
        print("-"*80)
        print(f"Exception: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print("-"*80 + "\n")

        # Cleanup
        test_file.unlink(missing_ok=True)
        return False


if __name__ == "__main__":
    success = test_with_simple_tool()
    sys.exit(0 if success else 1)
