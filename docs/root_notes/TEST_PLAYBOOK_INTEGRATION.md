# Test Playbook Integration

## ✅ Integration Complete!

The ACE-inspired playbook system is now fully integrated into swecli.

## What Was Changed

### 1. `swecli/repl/chat/async_query_processor.py`

**Added:**
- Import: `from swecli.core.context_management import ExecutionReflector`
- Reflector initialization in `__init__`
- Playbook context in `_prepare_messages()` - adds learned strategies to system prompt
- Reflection call after tool execution
- `_reflect_and_learn()` method

**Changes are minimal and safe:**
- All reflection code is wrapped in try/except to prevent breaking main flow
- Playbook failures gracefully fall back to base system prompt
- Total changes: ~30 lines of code

### 2. `swecli/models/session.py`

**Added:**
- `playbook` field (dict for serialization)
- `get_playbook()` method
- `update_playbook()` method

## Testing Instructions

**IMPORTANT**: You must restart swecli after making changes for them to take effect (Python module caching).

### Test 1: Basic Tool Execution (Should Work)

```bash
# Start fresh swecli session
swecli

# Test basic commands
> list files
> run app.py
```

**Expected**: Tools execute normally with nice formatted boxes.

### Test 2: Pattern Recognition

Execute a multi-step workflow that the reflector can learn from:

```bash
> list files and then read main.py
```

**Expected**:
- Agent calls `list_files`
- Agent calls `read_file`
- Reflection extracts pattern: "List directory before reading files"
- Strategy saved to session playbook (silent, no UI feedback)

### Test 3: Verify Learning

Check if strategy was learned:

```python
# In Python
from swecli.models.session import Session

# Load most recent session
session = Session.load_from_file("~/.swecli/sessions/SESSION_ID.json")
playbook = session.get_playbook()

print(f"Strategies learned: {len(playbook)}")
for strategy in playbook.strategies.values():
    print(f"  [{strategy.id}] {strategy.category}: {strategy.content}")
```

### Test 4: Strategy Usage

In the SAME session (so playbook has strategies), try another query:

```bash
> check the config file
```

**Expected**: System prompt now includes learned strategies, which may influence agent behavior.

### Test 5: Check Debug Logs

```bash
cat ~/.swecli/sessions/*.json | grep playbook
```

Should show playbook data in session files.

## Pattern Examples

The reflector automatically detects these patterns:

### File Operations
- `list_files` → `read_file`: "List directory before reading"
- `read_file` → `write_file`: "Read before write to preserve data"
- Multiple `read_file` calls: "Read multiple files for complete picture"

### Code Navigation
- `search` → `read_file`: "Search before read for targeted access"
- Multiple `search` calls: "Multiple searches for thorough exploration"

### Testing
- `write_file` → `run_command(pytest)`: "Run tests after code changes"
- `read_file(test_*.py)` → `run_command`: "Review tests before running"

### Shell Commands
- `run_command(pip install)` → `run_command(python)`: "Install dependencies before run"
- `run_command(git status)` → `run_command(git ...)`: "Check status before git operations"

### Error Handling
- `read_file` fails → suggests: "List directory to verify file exists"
- `run_command` fails → suggests: "Verify environment and dependencies"

## Troubleshooting

### Issue: Tools don't execute after changes

**Cause**: Python module caching - running swecli process hasn't reloaded modified files.

**Solution**:
1. Exit swecli
2. Delete cache: `rm -rf swecli/**/__pycache__`
3. Start fresh swecli session

### Issue: ImportError for ExecutionReflector

**Cause**: Context management module not in Python path.

**Solution**:
```bash
pip install -e .  # Reinstall in development mode
```

### Issue: Session playbook field missing

**Cause**: Old session files don't have playbook field.

**Solution**: Start a new session - old sessions auto-upgrade on load.

### Issue: No strategies being extracted

**Check**:
1. Are you using multi-step tool sequences? (min 2 tools required)
2. Is confidence threshold met? (default: 0.65)
3. Check reflector settings in `async_query_processor.py` line 31

**Lower thresholds for testing**:
```python
self.reflector = ExecutionReflector(min_tool_calls=1, min_confidence=0.5)
```

## Success Criteria

✅ Tools execute with formatted boxes
✅ Multi-step workflows complete successfully
✅ Session playbook field exists and serializes
✅ Strategies extracted after qualifying tool sequences
✅ Playbook context included in system prompt
✅ No errors or exceptions in normal operation

## Performance Impact

- **Negligible**: Reflection runs async after tool execution
- **Bounded context**: Max 30 strategies in system prompt
- **Graceful degradation**: Errors don't break main flow

## Next Steps

After verifying integration works:

1. **Monitor learning**: Check session files for accumulated strategies
2. **Tune thresholds**: Adjust confidence/min_tool_calls based on quality
3. **Add user feedback**: UI to rate strategies as helpful/harmful
4. **Cross-session sharing**: Repository-level playbooks
5. **LLM-powered reflection**: Replace pattern matching with LLM analysis

---

**Status**: Ready for testing
**Date**: 2025-10-23
**Integration**: Complete
