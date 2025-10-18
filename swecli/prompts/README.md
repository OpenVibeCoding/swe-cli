# SWE-CLI System Prompts

This directory contains all system prompts used by SWE-CLI agents. Prompts are stored as separate text files for easy editing and version control.

## Available Prompts

### 1. `agent_normal.txt`
**Purpose**: Base system prompt for the normal/execution agent
**Used by**: `SystemPromptBuilder` in normal mode
**Description**: Defines the ReAct pattern, lists available tools, and sets the tone for interactive coding sessions.

**Key sections**:
- Interaction style (ReAct pattern)
- Available built-in tools
- Tool usage examples

### 2. `agent_normal_guidelines.txt`
**Purpose**: Guidelines and best practices for the normal agent
**Used by**: `SystemPromptBuilder` (appended to base prompt)
**Description**: Provides operational guidelines, best practices, and behavioral rules.

**Key sections**:
- General guidelines (reasoning, observation, summarization)
- Best practices (code conventions, project structure)
- Special instructions (background processes, etc.)

### 3. `agent_planning.txt`
**Purpose**: System prompt for the planning/analysis agent
**Used by**: `PlanningPromptBuilder` in plan mode
**Description**: Defines the planning agent's role as a strategic advisor without execution capabilities.

**Key sections**:
- Role definition (analysis-only, no tools)
- Planning workflow
- Output format template
- Smart mode detection

### 4. `agent_compact.txt`
**Purpose**: Context compaction/summarization prompt
**Used by**: `CompactAgent` for conversation summarization
**Description**: Instructions for summarizing conversation history while preserving critical information.

**Key sections**:
- What to preserve vs. discard
- Output format (structured markdown)
- Compaction targets (60-80% reduction)

## How to Edit Prompts

### Direct Editing
Simply edit the `.txt` files in this directory. Changes take effect immediately on next reload.

```bash
# Edit a prompt
vim swecli/prompts/agent_normal.txt

# Changes are loaded automatically on next agent initialization
```

### Programmatic Access

```python
from swecli.prompts import load_prompt, save_prompt, get_prompt_path

# Load a prompt
prompt = load_prompt("agent_normal")

# Get file path
path = get_prompt_path("agent_planning")

# Save a modified prompt
save_prompt("agent_normal", modified_content)
```

## Prompt Design Guidelines

When modifying prompts, follow these guidelines:

1. **Be Specific**: Clearly define the agent's role and capabilities
2. **Provide Examples**: Include concrete examples of desired behavior
3. **Set Boundaries**: Explicitly state what the agent should NOT do
4. **Use Formatting**: Markdown headings and lists improve readability
5. **Test Thoroughly**: Test prompts with various user queries

## Architecture

### Prompt Loading Flow

```
Agent Initialization
  ↓
SystemPromptBuilder.build()
  ↓
load_prompt("agent_normal")
  ↓
Read from agent_normal.txt
  ↓
Return prompt string
```

### Components

- **`loader.py`**: Prompt loading utilities
  - `load_prompt(name)`: Load a prompt from file
  - `get_prompt_path(name)`: Get path to a prompt file
  - `save_prompt(name, content)`: Save/update a prompt

- **`system_prompt.py`**: Prompt builders
  - `SystemPromptBuilder`: Builds normal mode prompt with MCP integration
  - `PlanningPromptBuilder`: Builds planning mode prompt

- **`compact_agent.py`**: Compaction agent
  - Uses `agent_compact.txt` for summarization instructions

## Customization Tips

### Adding Dynamic Sections

To add dynamic content (like MCP tools), modify the builder class:

```python
class SystemPromptBuilder:
    def build(self) -> str:
        prompt = load_prompt("agent_normal")

        # Add custom dynamic section
        prompt += self._build_custom_section()

        prompt += load_prompt("agent_normal_guidelines")
        return prompt
```

### Multi-Language Support

To support multiple languages, create language-specific prompt files:

```
prompts/
├── agent_normal.txt          # Default (English)
├── agent_normal_es.txt       # Spanish
├── agent_normal_zh.txt       # Chinese
└── loader.py                 # Add language parameter
```

### User-Specific Customization

Allow users to override prompts:

```python
# In loader.py
def load_prompt(name, user_override_dir=None):
    if user_override_dir:
        user_path = Path(user_override_dir) / f"{name}.txt"
        if user_path.exists():
            return user_path.read_text()

    # Fall back to default
    return get_prompt_path(name).read_text()
```

## Version Control

Prompts are version controlled alongside code, making it easy to:
- Track prompt evolution over time
- Revert problematic changes
- Review prompt modifications in PRs
- Branch prompts for experiments

## Testing

Always test prompt changes with real interactions:

```bash
# Start SWE-CLI with modified prompts
swecli

# Test various scenarios
> create a hello world python script
> explain the code you just wrote
> switch to plan mode and analyze this
```

## Troubleshooting

### Prompt Not Loading

```python
# Check if file exists
from swecli.prompts import get_prompt_path
path = get_prompt_path("agent_normal")
print(path.exists())  # Should be True

# Manually read to debug
print(path.read_text())
```

### Caching Issues

Prompts are loaded on agent initialization. To force a reload:
1. Restart the SWE-CLI session
2. Or programmatically recreate the agent

### Encoding Problems

All prompts use UTF-8 encoding. If you see encoding errors:

```python
# Ensure UTF-8
prompt_file.write_text(content, encoding="utf-8")
```

## Future Enhancements

Potential improvements to the prompts system:

1. **Prompt Templates**: Support for variable substitution
2. **Prompt Versioning**: Track and rollback prompt versions
3. **A/B Testing**: Compare different prompt variations
4. **Prompt Analytics**: Track which prompts work best
5. **User Profiles**: Different prompts for different user types
6. **Context-Aware**: Dynamic prompts based on project type
