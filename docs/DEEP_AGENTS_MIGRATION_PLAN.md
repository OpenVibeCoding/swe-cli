# LangChain Deep Agents Migration Plan

## Context

- LangChain’s [Deep Agents quickstart](https://docs.langchain.com/oss/python/deepagents/quickstart) demonstrates `create_deep_agent` which wraps a LangGraph-powered workflow that already includes planning (`write_todos`), file-system tools, Tavily search, and optional subagents.
- The example agent is invoked with an OpenAI-style chat payload: `agent.invoke({"messages": [{"role": "user", "content": "..."}]})` and returns LangChain `BaseMessage` objects in the response (`result["messages"][-1].content`).
- The reference implementation depends on `deepagents` plus an external search tool (`tavily-python`) and requires API keys (Anthropic/OpenAI + Tavily) to be configured via environment variables.

## Migration Goals

1. **Parity with SwecliAgent inputs/outputs** – Continue accepting OpenAI-format chat messages and produce the same structure the rest of SWE-CLI expects.
2. **Tool Reuse** – Reuse the existing tool registry (filesystem, bash, MCP, etc.) by exposing LangChain-compatible `BaseTool` wrappers so Deep Agents can call them directly.
3. **Feature Flags** – Keep the current HTTP/LangChain adapter path as the default while introducing Deep Agents behind an opt-in flag for iterative rollout.
4. **Interrupt & Monitoring** – Preserve task monitors / interrupt hooks as Deep Agents move long-running work into LangGraph.

## Phased Approach

| Phase | Focus | Key Tasks |
| --- | --- | --- |
| 0 | **Scaffolding** | Add `deepagents` & `tavily-python` dependencies, document plan, introduce `SWECO_DEEPAGENT_ENABLED` feature flag. |
| 1 | **Adapter** | Implement `DeepLangChainAgent` that wraps `create_deep_agent`, converts LangChain messages back to SWE-CLI dictionaries, and plugs into `AgentFactory` when the flag is enabled. |
| 2 | **Tool Bridging** | Feed LangChain `BaseTool` objects from `ToolRegistryAdapter` into the deep agent so built-in SWE-CLI tools remain available. Provide graceful fallbacks when Tavily/API keys are missing. |
| 3 | **Parity & Enhancements** | Add interrupt propagation, streaming hooks, and richer telemetry; align planning agent / mode manager with Deep Agent behaviors. |
| 4 | **Default Rollout** | After validation, flip the default to Deep Agents and ultimately retire the legacy HTTP client. |

## Current Status

- Phase 1 is complete: `DeepLangChainAgent` is now the default normal agent and the legacy `SwecliAgent`/HTTP path has been removed.
- Phase 0/1 artifacts (dependencies, tool adapters) are merged; remaining work focuses on feature parity (interrupts, approvals, config-driven model selection).

## Immediate Next Steps

1. Thread mode/approval/undo managers through the LangChain tool adapters so Deep Agents honor plan-mode and approval flows.
2. Propagate task monitors / interrupt hooks into the LangGraph runtime (streaming or cooperative cancellation) to regain stop support.
3. Add regression tests ensuring provider-specific model construction works (Fireworks/OpenAI/Anthropic) and document the configuration knobs in the README.

## API Keys

- Deep Agents now respect the existing `AppConfig.model_provider` value. Provide credentials via the standard environment variables that `AppConfig.get_api_key()` looks for:
  - `FIREWORKS_API_KEY` for `model_provider="fireworks"`
  - `OPENAI_API_KEY` for `model_provider="openai"`
  - `ANTHROPIC_API_KEY` for `model_provider="anthropic"`
- Optional overrides such as `api_base_url`, `temperature`, and `max_tokens` are honored when instantiating the LangChain chat model.

This document will grow as we iterate on the migration.
