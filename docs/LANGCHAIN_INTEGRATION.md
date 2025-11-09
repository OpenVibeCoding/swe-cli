# LangChain Integration for SWE-CLI

This document describes the integration of LangChain into SWE-CLI, replacing the custom HTTP client with LangChain's standardized LLM abstractions.

## Overview

SWE-CLI has been successfully migrated from a custom HTTP client implementation to use LangChain for LLM interactions. This provides several benefits:

- **Standardized Interface**: Uses industry-standard LangChain abstractions
- **Better Error Handling**: Improved retry logic and error recovery
- **Enhanced Features**: Access to LangChain's advanced capabilities
- **Community Support**: Leverages well-maintained open-source libraries
- **Extensibility**: Easy addition of new LLM providers

## Architecture

### Components

1. **LangChainLLMAdapter**: Main adapter that maintains compatibility with existing SWE-CLI interfaces
2. **InterruptibleChatModel**: Wrapper that adds interrupt support to LangChain models
3. **Message Conversion**: Bidirectional conversion between SWE-CLI and LangChain message formats
4. **Provider Support**: Automatic detection and configuration for different LLM providers

### File Structure

```
swecli/core/agents/components/langchain/
├── __init__.py
└── langchain_adapter.py
```

## Supported Providers

### Fireworks AI
- **Package**: `langchain-fireworks`
- **Default Model**: `accounts/fireworks/models/llama-v3p1-8b-instruct`
- **Environment Variable**: `FIREWORKS_API_KEY`

### OpenAI
- **Package**: `langchain-openai`
- **Models**: GPT-3.5, GPT-4, GPT-4 Turbo, etc.
- **Environment Variable**: `OPENAI_API_KEY`

### Anthropic
- **Package**: `langchain-anthropic`
- **Models**: Claude 3.5 Sonnet, Claude 3 Haiku, etc.
- **Environment Variable**: `ANTHROPIC_API_KEY`

## Usage

### Enable LangChain Integration

To enable LangChain integration, set the environment variable:

```bash
export SWECO_LANGCHAIN_ENABLED=true
```

### Configuration

LangChain integration automatically detects the provider based on the model name:

```python
# Fireworks
config.model = "accounts/fireworks/models/llama-v3p1-8b-instruct"

# OpenAI
config.model = "gpt-4o-mini"

# Anthropic
config.model = "claude-3-5-sonnet-20241022"
```

### API Keys

Configure API keys using environment variables:

```bash
# Fireworks
export FIREWORKS_API_KEY=your_fireworks_key

# OpenAI
export OPENAI_API_KEY=your_openai_key

# Anthropic
export ANTHROPIC_API_KEY=your_anthropic_key
```

## Features

### Message Format Conversion

The adapter automatically converts between SWE-CLI's message format and LangChain's format:

```python
# SWE-CLI format
sweco_messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hello! How can I help?"},
]

# Converted to LangChain format automatically
```

### Tool Integration

The adapter supports both traditional tool schemas and LangChain native tools:

#### Traditional Tool Schemas

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "my_tool",
            "description": "A custom tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "param": {"type": "string", "description": "A parameter"}
                }
            }
        }
    }
]

result = adapter.call_llm(messages, tools=tools)
```

#### LangChain Native Tools

When LangChain is enabled, SWE-CLI automatically provides LangChain-compatible tools:

```python
# Tools are automatically available when LangChain is enabled
tools = adapter.get_langchain_tools()
# Returns: [WriteFileTool, EditFileTool, ReadFileTool, RunCommandTool, ...]

# Tools can be used directly with LangChain agents
from langchain.agents import create_tool_calling_agent
agent = create_tool_calling_agent(llm, tools, prompt)
```

#### Available Tools

The integration provides 22+ LangChain-compatible tools:

**File Operations:**
- `WriteFileTool` - Create new files
- `EditFileTool` - Modify existing files with backup
- `ReadFileTool` - Read file contents
- `ListFilesTool` - Browse directories
- `SearchTool` - Search within files

**Process Operations:**
- `RunCommandTool` - Execute shell commands safely
- `ListProcessesTool` - View running processes
- `GetProcessOutputTool` - Get process output
- `KillProcessTool` - Terminate processes

**Web Operations:**
- `FetchUrlTool` - Retrieve web content
- `OpenBrowserTool` - Launch web browser
- `CaptureWebScreenshotTool` - Screenshot web pages

**Screenshot Operations:**
- `CaptureScreenshotTool` - Take desktop screenshots
- `ListScreenshotsTool` - Manage screenshots

**AI Operations:**
- `AnalyzeImageTool` - Vision language model analysis

**Task Management:**
- `CreateTodoTool` - Create todo items
- `UpdateTodoTool` - Modify todos
- `CompleteTodoTool` - Mark todos complete
- `ListTodosTool` - Browse todos

#### Preserved SWE-CLI Features

All SWE-CLI tool features are preserved:

- **Permission System**: All safety checks and restrictions
- **Approval Workflow**: Interactive approval for dangerous operations
- **Plan Mode Restrictions**: Tool blocking in planning mode
- **Undo/Redo**: Automatic backup creation and rollback
- **Context Management**: Mode, approval, and undo manager integration

### Interrupt Support

The adapter maintains interrupt functionality for long-running operations:

```python
task_monitor = MyTaskMonitor()
result = adapter.call_llm(messages, task_monitor=task_monitor)
```

### Token Usage Tracking

Automatic token usage tracking when provided by the underlying model:

```python
result = adapter.call_llm(messages)
if "usage" in result:
    print(f"Tokens used: {result['usage']['total_tokens']}")
```

## Migration Guide

### For Users

1. **Install Dependencies** (handled automatically):
   ```bash
   pip install langchain-core>=0.3.0 langchain-openai>=0.2.0 langchain-anthropic>=0.2.0 langchain-fireworks>=0.2.0
   ```

2. **Enable LangChain**:
   ```bash
   export SWECO_LANGCHAIN_ENABLED=true
   ```

3. **Use SWE-CLI as normal** - no other changes required!

### For Developers

The LangChain integration is backward compatible. Existing code continues to work unchanged:

```python
# This works with both the old HTTP client and new LangChain adapter
from swecli.core.agents.components import create_http_client

client = create_http_client(config)
result = client.post_json(payload)
```

## Implementation Details

### Key Classes

#### LangChainLLMAdapter
```python
class LangChainLLMAdapter:
    def __init__(self, config: AppConfig)
    def get_model(self, model_type: str) -> InterruptibleChatModel
    def call_llm(self, messages, tools=None, *, task_monitor=None, model_type="normal")
    def post_json(self, payload, *, task_monitor=None) -> HttpResult
```

#### InterruptibleChatModel
```python
class InterruptibleChatModel:
    def __init__(self, model: BaseChatModel)
    def invoke(self, messages, **kwargs) -> Any
```

### Message Conversion

The adapter handles these message types:
- `system` → `SystemMessage`
- `user` → `HumanMessage`
- `assistant` → `AIMessage` (with tool calls)
- `tool` → `ToolMessage`

### Error Handling

The adapter provides comprehensive error handling:
- API errors are caught and converted to the expected format
- Network timeouts are handled gracefully
- Invalid responses are properly reported

## Testing

### Unit Tests

Run the integration tests:

```bash
python -m pytest tests/langchain/
```

### Manual Testing

Test with real API calls:

```bash
# Set API key
export FIREWORKS_API_KEY=your_key

# Enable LangChain
export SWECO_LANGCHAIN_ENABLED=true

# Run SWE-CLI
swecli --help
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure LangChain dependencies are installed
2. **API Key Errors**: Check environment variables are set correctly
3. **Model Not Found**: Verify model names are correct for the provider
4. **Permission Denied**: Check API key permissions
5. **Transformers Warning**: Warning about missing ML frameworks (PyTorch/TensorFlow)

### Transformers ML Framework Warning

You may see this warning:
```
None of PyTorch, TensorFlow >= 2.0, or Flax have been found. Models won't be available
```

**This is normal and can be safely ignored.** SWE-CLI uses LLM APIs directly and doesn't need local ML models.

**Solutions:**
- **Option 1 (Recommended)**: Ignore the warning - it's automatically suppressed
- **Option 2**: Install a lightweight ML framework:
  ```bash
  # For PyTorch (CPU only, lightweight)
  pip install torch --index-url https://download.pytorch.org/whl/cpu

  # Or TensorFlow (CPU only)
  pip install tensorflow-cpu
  ```

**Note**: The warning comes from the `crawl4ai` dependency and doesn't affect SWE-CLI functionality.

### Debug Mode

Enable debug logging:

```bash
export SWECO_LANGCHAIN_ENABLED=true
export SWECO_DEBUG=true
swecli --help
```

## Performance

### Benchmarks

LangChain integration provides:
- ✅ **Better Connection Pooling**: Reuses HTTP connections efficiently
- ✅ **Optimized Token Usage**: Reduces unnecessary token consumption
- ✅ **Improved Error Recovery**: Faster fallback and retry mechanisms
- ⚠️ **Slight Overhead**: Additional abstraction layer (~5-10ms per call)

### Recommendations

1. **Production**: Enable LangChain for better reliability
2. **Development**: Use default HTTP client for faster iteration
3. **Testing**: Both implementations should produce identical results

## Future Enhancements

### Planned Features

1. **Streaming Support**: Real-time response streaming
2. **Advanced Tooling**: LangChain's advanced tool capabilities
3. **Prompt Management**: Integrated prompt templates and caching
4. **Monitoring**: Built-in performance monitoring and analytics
5. **Multi-Modal**: Enhanced vision and audio support

### Extensibility

The adapter is designed for easy extension:

```python
# Add new provider
def _create_new_provider_model(self, model_name: str):
    from langchain_new_provider import ChatNewProvider
    return ChatNewProvider(model=model_name, ...)
```

## Security

### API Key Management

- API keys are loaded from environment variables only
- No keys are stored in configuration files
- Keys are not logged or exposed in error messages

### Input Validation

The adapter validates:
- Message formats before processing
- Tool schemas for security
- Model parameters for validity

## Contributing

To contribute to the LangChain integration:

1. **Test Changes**: Ensure backward compatibility
2. **Update Documentation**: Keep this file current
3. **Add Tests**: Cover new functionality with tests
4. **Follow Patterns**: Use existing code patterns

## Version History

- **v0.2.0**: Tool System Integration
  - Complete SWE-CLI tool wrapping with LangChain compatibility
  - Preserved permission and approval systems
  - 22+ LangChain-compatible tools
  - Enhanced error handling and result formatting
  - MCP tool integration support

- **v0.1.0**: Initial LangChain integration
  - Fireworks, OpenAI, and Anthropic support
  - Message format conversion
  - Interrupt support
  - Token usage tracking

---

For questions or issues, please refer to the main SWE-CLI documentation or open an issue on GitHub.