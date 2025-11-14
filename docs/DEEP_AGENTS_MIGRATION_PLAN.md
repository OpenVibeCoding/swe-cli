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

## Current Status (Updated 2025-01-XX)

### ✅ Completed Steps (1-13)

**Phase 0 - Foundation:**
- Steps 1-6: Created `DeepLangChainAgent` skeleton with message conversion, tool integration, and interrupt handling
- Successfully integrated with existing `ToolRegistryAdapter` (22+ tools)
- Implemented basic `call_llm()` method

**Phase 1 - Feature Flag & Streaming:**
- Step 7: Added `agent_type` config flag ("swecli" or "deep_langchain")
- `AgentFactory` now supports both agent types
- Step 8-11: Implemented streaming with Deep Agent's `.stream()` API
- Proper message history management and tool call tracking
- Tested with simple queries ✅ and tool calls ✅

**Phase 2 - Production Ready:**
- Step 12: Replaced debug prints with proper Python logging
- Step 13: Added comprehensive error handling (input validation, interrupts, empty responses)

### Current State

- **DeepLangChainAgent is fully functional** and available via config
- **SwecliAgent remains the default** for stability
- Both agents coexist peacefully in `AgentFactory`
- Users can switch by setting `config.agent_type = "deep_langchain"`

### How to Use Deep Agent

**Method 1: Config File**
```python
# In your config
agent_type = "deep_langchain"  # Options: "swecli" (default) or "deep_langchain"
```

**Method 2: Environment/CLI**
```bash
# Set in your configuration before starting SWE-CLI
export SWECLI_AGENT_TYPE="deep_langchain"
```

**What You Get:**
- Advanced task planning with LangGraph
- Built-in file system operations
- All 22+ existing SWE-CLI tools
- Robust error handling and logging
- Interrupt support

### Remaining Work

1. **Optional**: Switch default to Deep Agent after more real-world testing
2. **Optional**: Remove SwecliAgent entirely (full migration)
3. Continue enhancing Deep Agent features:
   - Streaming progress updates to UI
   - Advanced interrupt propagation
   - Approval flow integration

## API Keys

- Deep Agents now respect the existing `AppConfig.model_provider` value. Provide credentials via the standard environment variables that `AppConfig.get_api_key()` looks for:
  - `FIREWORKS_API_KEY` for `model_provider="fireworks"`
  - `OPENAI_API_KEY` for `model_provider="openai"`
  - `ANTHROPIC_API_KEY` for `model_provider="anthropic"`
- Optional overrides such as `api_base_url`, `temperature`, and `max_tokens` are honored when instantiating the LangChain chat model.

This document will grow as we iterate on the migration.
