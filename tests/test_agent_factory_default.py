"""Test AgentFactory behavior after full migration to Deep Agent."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from swecli.core.factories.agent_factory import AgentFactory
from swecli.core.management import ModeManager
from swecli.core.tools.registry import ToolRegistry
from swecli.models.config import AppConfig


def test_always_creates_deep_agent():
    """Test that AgentFactory always creates DeepLangChainAgent."""
    print("\n" + "="*80)
    print("TEST: AgentFactory always creates DeepLangChainAgent")
    print("="*80 + "\n")

    # Create config
    config = AppConfig(
        model_provider="fireworks",
        model="accounts/fireworks/models/llama-v3p1-8b-instruct",
        api_key=os.getenv("FIREWORKS_API_KEY", "dummy"),
    )

    # Verify agent_type field no longer exists
    has_agent_type = hasattr(config, 'agent_type')
    print(f"Config has agent_type field: {has_agent_type}")
    assert not has_agent_type, "agent_type field should be removed from config"

    # Create factory
    tool_registry = ToolRegistry()
    mode_manager = ModeManager()
    factory = AgentFactory(config, tool_registry, mode_manager)

    # Create agents
    suite = factory.create_agents()

    # Check normal agent type
    normal_agent_type = type(suite.normal).__name__
    print(f"Normal agent type: {normal_agent_type}")
    assert normal_agent_type == "DeepLangChainAgent", f"Expected DeepLangChainAgent, got {normal_agent_type}"

    # Check planning agent type
    planning_agent_type = type(suite.planning).__name__
    print(f"Planning agent type: {planning_agent_type}")
    assert planning_agent_type == "PlanningAgent", f"Expected PlanningAgent, got {planning_agent_type}"

    print("✅ AgentFactory always creates DeepLangChainAgent (with PlanningAgent)\n")
    return True


if __name__ == "__main__":
    try:
        success = test_always_creates_deep_agent()

        if success:
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
