"""Tests for the DeepLangChainAgent provider/model wiring."""

from __future__ import annotations

import sys
import threading
import types
from typing import Any

import pytest

import swecli.core.agents.deep_langchain_agent as dla
from swecli.models.config import AppConfig


class _StubToolAdapter:
    """Simple tool adapter that records execution context updates."""

    def __init__(self, registry: Any):
        self.registry = registry
        self.context_history: list[dict[str, Any]] = []
        self.tools: list[Any] = []

    def get_langchain_tools(self) -> list[Any]:  # pragma: no cover - trivial
        return self.tools

    def update_execution_context(self, **context: Any) -> None:
        self.context_history.append(context)


@pytest.fixture
def stub_tool_adapter(monkeypatch: pytest.MonkeyPatch):
    """Patch ToolRegistryAdapter with a stubbed version we can inspect."""

    instances: list[_StubToolAdapter] = []

    def factory(registry: Any) -> _StubToolAdapter:
        adapter = _StubToolAdapter(registry)
        instances.append(adapter)
        return adapter

    monkeypatch.setattr(dla, "ToolRegistryAdapter", factory)
    return instances


def _install_deepagents_stub(monkeypatch: pytest.MonkeyPatch, agent_factory):
    """Install a stub deepagents module that returns agent_factory()."""

    module = types.SimpleNamespace()

    def create_deep_agent(**kwargs):
        agent = agent_factory(kwargs)
        module.last_call = kwargs
        module.last_agent = agent
        return agent

    module.create_deep_agent = create_deep_agent
    monkeypatch.setitem(sys.modules, "deepagents", module)
    return module


@pytest.mark.parametrize(
    ("provider", "module_name", "class_name", "key_field"),
    [
        ("fireworks", "langchain_fireworks", "ChatFireworks", "api_key"),
        ("openai", "langchain_openai", "ChatOpenAI", "api_key"),
        ("anthropic", "langchain_anthropic", "ChatAnthropic", "anthropic_api_key"),
    ],
)
def test_deep_agent_uses_provider_specific_model(monkeypatch, stub_tool_adapter, provider, module_name, class_name, key_field):
    captured_model_kwargs = {}

    class StubModel:
        def __init__(self, **kwargs: Any):
            captured_model_kwargs.update(kwargs)

    module = types.SimpleNamespace()
    setattr(module, class_name, StubModel)
    monkeypatch.setitem(sys.modules, module_name, module)

    def agent_factory(kwargs: dict[str, Any]):
        class DummyAgent:
            def __init__(self):
                self.kwargs = kwargs

            def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
                return {"messages": payload["messages"] + [{"role": "assistant", "content": "ok"}]}

        return DummyAgent()

    deepagents_module = _install_deepagents_stub(monkeypatch, agent_factory)

    config = AppConfig(
        model_provider=provider,
        model="provider-model",
        api_key="secret-key",
        temperature=0.3,
        max_tokens=1234,
    )

    agent = dla.DeepLangChainAgent(config, tool_registry=object(), mode_manager="mode")

    # Model kwargs include provider-specific key and standard settings.
    assert captured_model_kwargs["model"] == "provider-model"
    assert captured_model_kwargs[key_field] == "secret-key"
    assert captured_model_kwargs["temperature"] == 0.3
    assert captured_model_kwargs["max_tokens"] == 1234

    # Deep agent should have received the stub model and tools list.
    assert "model" in deepagents_module.last_call
    assert deepagents_module.last_call["tools"] == []

    # Runtime dependency updates reach the adapter.
    agent.update_runtime_dependencies(
        mode_manager="MODE",
        approval_manager="APPROVAL",
        undo_manager="UNDO",
        session_manager="SESSION",
    )
    adapter = stub_tool_adapter[0]
    assert adapter.context_history[-1]["mode_manager"] == "MODE"
    assert adapter.context_history[-1]["approval_manager"] == "APPROVAL"

    # call_llm should succeed with the dummy deep agent.
    response = agent.call_llm([{"role": "system", "content": "hello"}])
    assert response["success"]
    assert response["message"]["role"] == "assistant"


def test_call_llm_returns_interrupt(monkeypatch, stub_tool_adapter):
    class CountingAgent:
        def __init__(self):
            self.calls = 0

        def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
            self.calls += 1
            return {"messages": payload["messages"]}

    module = _install_deepagents_stub(monkeypatch, lambda kwargs: CountingAgent())

    class StubModel:
        def __init__(self, **kwargs: Any):
            self.kwargs = kwargs

    bridge = types.SimpleNamespace()
    bridge.ChatFireworks = StubModel
    monkeypatch.setitem(sys.modules, "langchain_fireworks", bridge)

    config = AppConfig(model_provider="fireworks", model="m", api_key="k")
    agent = dla.DeepLangChainAgent(config, tool_registry=object(), mode_manager="mode")

    class InterruptMonitor:
        def __init__(self):
            self.called = 0

        def should_interrupt(self) -> bool:
            self.called += 1
            return True

    monitor = InterruptMonitor()
    response = agent.call_llm([{"role": "system", "content": "hi"}], task_monitor=monitor)
    assert not response["success"]
    assert response.get("interrupted")
    assert monitor.called == 1
    assert module.last_agent.calls == 0
