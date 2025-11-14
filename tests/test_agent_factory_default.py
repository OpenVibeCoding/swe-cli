"""Test AgentFactory default behavior after switching to Deep Agent."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from swecli.core.factories.agent_factory import AgentFactory
from swecli.core.management import ModeManager
from swecli.core.tools.registry import ToolRegistry
from swecli.models.config import AppConfig


def test_default_is_deep_agent():
    """Test that default agent is Deep Agent when agent_type not specified."""
    print("\n" + "="*80)
    print("TEST 1: Default agent (no agent_type specified)")
    print("="*80 + "\n")

    # Create config without agent_type
    config = AppConfig(
        model_provider="fireworks",
        model="accounts/fireworks/models/llama-v3p1-8b-instruct",
        api_key=os.getenv("FIREWORKS_API_KEY", "dummy"),
    )

    # Verify default
    print(f"Config agent_type: {getattr(config, 'agent_type', 'NOT SET')}")
    assert config.agent_type == "deep_langchain", "Default should be deep_langchain"

    # Create factory
    tool_registry = ToolRegistry()
    mode_manager = ModeManager()
    factory = AgentFactory(config, tool_registry, mode_manager)

    # Create agents
    suite = factory.create_agents()

    # Check type
    agent_type = type(suite.normal).__name__
    print(f"Created agent type: {agent_type}")

    assert agent_type == "DeepLangChainAgent", f"Expected DeepLangChainAgent, got {agent_type}"
    print("✅ Default is Deep Agent\n")
    return True


def test_swecli_opt_out():
    """Test that SwecliAgent works when explicitly set."""
    print("="*80)
    print("TEST 2: Opt-out to SwecliAgent (agent_type='swecli')")
    print("="*80 + "\n")

    # Create config WITH agent_type = "swecli"
    config = AppConfig(
        agent_type="swecli",  # Explicit opt-out
        model_provider="fireworks",
        model="accounts/fireworks/models/llama-v3p1-8b-instruct",
        api_key=os.getenv("FIREWORKS_API_KEY", "dummy"),
    )

    print(f"Config agent_type: {config.agent_type}")

    # Create factory
    tool_registry = ToolRegistry()
    mode_manager = ModeManager()
    factory = AgentFactory(config, tool_registry, mode_manager)

    # Create agents
    suite = factory.create_agents()

    # Check type
    agent_type = type(suite.normal).__name__
    print(f"Created agent type: {agent_type}")

    assert agent_type == "SwecliAgent", f"Expected SwecliAgent, got {agent_type}"
    print("✅ Opt-out to SwecliAgent works\n")
    return True


if __name__ == "__main__":
    try:
        success1 = test_default_is_deep_agent()
        success2 = test_swecli_opt_out()

        if success1 and success2:
            print("="*80)
            print("✅ ALL TESTS PASSED")
            print("="*80)
            sys.exit(0)
        else:
            print("❌ TESTS FAILED")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
