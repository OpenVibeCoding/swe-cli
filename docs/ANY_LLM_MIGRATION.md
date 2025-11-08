# any-llm Framework Integration

This document explains how SWE-CLI integrates with Mozilla's [any-llm](https://github.com/mozilla-ai/any-llm) framework to support 35+ LLM providers with a unified interface.

## Overview

SWE-CLI now supports two provider adapter modes:

1. **Legacy Mode** (default): Uses the original HTTP client implementation supporting Fireworks, OpenAI, and Anthropic
2. **any-llm Mode** (optional): Leverages the any-llm SDK for access to 35+ providers

The system uses an adapter pattern that allows seamless switching between modes without breaking existing functionality.

## Installation

### Basic Installation (Legacy Mode Only)

```bash
pip install swe-cli
```

This installs the core package with support for Fireworks, OpenAI, and Anthropic via the legacy HTTP client.

### Full Installation (with any-llm Support)

```bash
pip install 'swe-cli[llm-providers]'
```

This installs the any-llm SDK and enables support for all providers.

## Configuration

### Using Legacy Mode (Default)

No configuration changes needed. Your existing config works as-is:

```json
{
  "model_provider": "fireworks",
  "model": "accounts/fireworks/models/kimi-k2-instruct-0905",
  "api_key": "your-api-key"
}
```

### Enabling any-llm Mode

Add `use_anyllm_framework: true` to your config:

```json
{
  "use_anyllm_framework": true,
  "model_provider": "anthropic",
  "model": "claude-3-5-sonnet-20241022",
  "api_key": "your-api-key"
}
```

Or via environment variable:
```bash
export SWECLI_USE_ANYLLM=true
```

## Supported Providers

### Legacy Mode Providers

- **Fireworks** - Default, high-performance models
- **OpenAI** - GPT-4, GPT-3.5, etc.
- **Anthropic** - Claude models (via custom adapter)

### any-llm Mode Providers

When `use_anyllm_framework=true`, you get access to 35+ providers:

**Major Cloud Providers:**
- **Anthropic** - Claude 3.5 Sonnet, Claude 3 Opus, etc.
- **OpenAI** - GPT-4, GPT-4 Turbo, GPT-3.5
- **Google Gemini** - Gemini 1.5 Pro, Gemini 1.5 Flash
- **Mistral** - Mistral Large, Mixtral, etc.
- **AWS Bedrock** - Access to multiple models via AWS
- **Azure OpenAI** - Enterprise OpenAI deployment
- **Vertex AI** - Google Cloud AI models

**Specialized Providers:**
- **Groq** - Ultra-fast inference
- **Fireworks** - High-performance models
- **Together AI** - Open-source models
- **DeepSeek** - DeepSeek-V2, DeepSeek-Coder
- **Cohere** - Command models
- **Perplexity** - Online models with web search

**Local / Self-Hosted:**
- **Ollama** - Run models locally (Llama 3, Mistral, etc.)
- **LM Studio** - Local model management
- **llama.cpp** - C++ inference engine
- **llamafile** - Single-file executables

[See full list](https://mozilla-ai.github.io/any-llm/providers/)

## Usage Examples

### Example 1: Using Anthropic with any-llm

```json
{
  "use_anyllm_framework": true,
  "model_provider": "anthropic",
  "model": "claude-3-5-sonnet-20241022"
}
```

Set environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Example 2: Using Google Gemini

```json
{
  "use_anyllm_framework": true,
  "model_provider": "gemini",
  "model": "gemini-1.5-pro"
}
```

Set environment variable:
```bash
export GEMINI_API_KEY="AIza..."
```

### Example 3: Using Ollama (Local)

```bash
# Start Ollama server
ollama serve

# Pull a model
ollama pull llama3
```

Config:
```json
{
  "use_anyllm_framework": true,
  "model_provider": "ollama",
  "model": "llama3"
}
```

No API key needed for local Ollama!

### Example 4: Using Groq for Fast Inference

```json
{
  "use_anyllm_framework": true,
  "model_provider": "groq",
  "model": "llama-3.1-70b-versatile"
}
```

Set environment variable:
```bash
export GROQ_API_KEY="gsk_..."
```

## Architecture

### Adapter Pattern

SWE-CLI uses a provider adapter pattern with three layers:

1. **ProviderAdapter (Interface)**: Abstract base class defining the contract
2. **LegacyProviderAdapter**: Wraps the original HTTP client (backward compatible)
3. **AnyLLMAdapter**: Wraps the any-llm SDK (new functionality)

```python
# Factory creates the appropriate adapter based on config
from swecli.core.providers import create_provider_adapter

adapter = create_provider_adapter(config)
response = adapter.completion(
    model="claude-3-5-sonnet",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Agent Integration

All agents now use the provider adapter:

- **SwecliAgent**: Main agent for interactive sessions
- **PlanningAgent**: Planning mode agent
- **CompactAgent**: Context compaction agent

```python
class SwecliAgent(BaseAgent):
    def __init__(self, config, ...):
        self._provider_adapter = create_provider_adapter(config)

    def call_llm(self, messages, ...):
        return self._provider_adapter.completion(
            model=self.config.model,
            messages=messages,
            ...
        )
```

## Migration Guide

### For Existing Users

**Your existing setup will continue to work without any changes!**

The default behavior uses the legacy adapter, so:
- No code changes required
- No config changes required
- No reinstallation required

### To Opt-In to any-llm

1. **Install with llm-providers extra:**
   ```bash
   pip install --upgrade 'swe-cli[llm-providers]'
   ```

2. **Update your config:**
   ```bash
   # Edit ~/.swecli/settings.json
   {
     "use_anyllm_framework": true,
     ...
   }
   ```

3. **Test it:**
   ```bash
   swecli
   > /test
   ```

4. **Rollback if needed:**
   Set `use_anyllm_framework: false` to revert to legacy mode.

### Switching Providers

With any-llm enabled, you can easily switch providers:

```bash
# Use Anthropic
swecli --provider anthropic --model claude-3-5-sonnet-20241022

# Use OpenAI
swecli --provider openai --model gpt-4

# Use local Ollama
swecli --provider ollama --model llama3
```

## Provider Capabilities

Different providers support different features. Query capabilities:

```python
from swecli.core.providers import create_provider_adapter

adapter = create_provider_adapter(config)
info = adapter.get_provider_info()

print(f"Streaming: {info.get('supports_streaming')}")
print(f"Vision: {info.get('supports_vision')}")
print(f"Reasoning: {info.get('supports_reasoning')}")
```

Example output for Anthropic:
```json
{
  "name": "anthropic",
  "supports_streaming": true,
  "supports_vision": true,
  "supports_reasoning": false,
  "supports_embedding": false
}
```

## Troubleshooting

### "any-llm not installed" Warning

```
Warning: any-llm framework enabled but not installed.
Falling back to legacy provider adapter
```

**Solution:**
```bash
pip install 'swe-cli[llm-providers]'
```

### Provider Not Supported in Legacy Mode

```
ValueError: model_provider must be one of ['fireworks', 'anthropic', 'openai']
```

**Solution:** Enable any-llm mode:
```json
{
  "use_anyllm_framework": true,
  "model_provider": "gemini"
}
```

### API Key Not Found

```
Error: No API key found. Set ANTHROPIC_API_KEY environment variable
```

**Solution:** Set the appropriate environment variable:
```bash
export ANTHROPIC_API_KEY="your-key"
# or set in config:
{
  "api_key": "your-key"
}
```

### Import Errors

If you see import errors related to `any_llm`:

1. Check installation: `pip show any-llm-sdk`
2. Reinstall: `pip install --force-reinstall 'swe-cli[llm-providers]'`
3. Or disable any-llm mode: `use_anyllm_framework: false`

## Performance Considerations

### Connection Pooling

The `AnyLLMAdapter` reuses provider instances for better performance:

```python
# Good: Creates one client instance, reused across requests
adapter = AnyLLMAdapter(config)
adapter.completion(...)  # Uses cached client
adapter.completion(...)  # Reuses same client
```

### Legacy vs any-llm Mode

- **Legacy Mode**: Direct HTTP requests, minimal overhead
- **any-llm Mode**: Slight overhead from SDK layer, but provides unified interface

For most use cases, the difference is negligible (< 10ms per request).

## Future Roadmap

Planned enhancements:

- [ ] Streaming support in agents
- [ ] Vision/multimodal support
- [ ] Embedding support for RAG
- [ ] Cost tracking per provider
- [ ] Automatic provider failover
- [ ] Provider-specific optimizations

## References

- [any-llm GitHub](https://github.com/mozilla-ai/any-llm)
- [any-llm Documentation](https://mozilla-ai.github.io/any-llm/)
- [Supported Providers](https://mozilla-ai.github.io/any-llm/providers/)
- [SWE-CLI Documentation](../README.md)
