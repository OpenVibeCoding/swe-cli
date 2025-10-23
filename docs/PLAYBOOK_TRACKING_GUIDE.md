# Playbook Tracking Guide

## Overview

The playbook stores learned strategies that evolve as the agent executes tasks. This guide explains where the playbook is stored, how it evolves, and how to track its evolution.

## Storage Architecture

### 1. In-Memory Storage (Runtime)

During a swecli session, the playbook lives in memory:

```python
# Loaded from session
session = session_manager.current_session
playbook = session.get_playbook()  # SessionPlaybook object

# Contains:
playbook.strategies = {
    "fil-00000": Strategy(id="fil-00000", category="file_operations", ...),
    "tes-00001": Strategy(id="tes-00001", category="testing", ...),
}
```

### 2. Persistent Storage (Disk)

The playbook is serialized as part of the session JSON file:

**Location**: `~/.swecli/sessions/<SESSION_ID>.json`

**Structure**:
```json
{
  "id": "abc123def456",
  "created_at": "2025-10-23T10:30:00",
  "updated_at": "2025-10-23T11:45:00",
  "working_directory": "/path/to/project",
  "messages": [...],
  "playbook": {
    "strategies": {
      "fil-00000": {
        "id": "fil-00000",
        "category": "file_operations",
        "content": "List directory before reading files to understand structure",
        "helpful_count": 3,
        "harmful_count": 0,
        "neutral_count": 0,
        "created_at": "2025-10-23T10:32:00.123456",
        "last_used": "2025-10-23T11:40:15.789012"
      },
      "tes-00001": {
        "id": "tes-00001",
        "category": "testing",
        "content": "Run tests after making code changes to verify correctness",
        "helpful_count": 2,
        "harmful_count": 0,
        "neutral_count": 1,
        "created_at": "2025-10-23T10:35:22.456789",
        "last_used": "2025-10-23T11:30:45.123456"
      }
    },
    "next_id": 2
  }
}
```

### 3. Auto-Save Mechanism

The playbook is automatically saved to disk when:
1. A new strategy is added
2. A strategy is tagged (helpful/harmful/neutral)
3. The session is updated

```python
# In async_query_processor.py:
playbook.add_strategy(category="file_operations", content="...")
session.update_playbook(playbook)  # ← Triggers auto-save
```

## Evolution Flow

### Step-by-Step Evolution

```
1. User submits query
   ↓
2. Agent executes tools (e.g., list_files, read_file)
   ↓
3. Tools complete successfully
   ↓
4. ExecutionReflector analyzes tool sequence
   ↓
5. Pattern detected? (e.g., "list before read")
   ↓
6. Confidence > threshold? (0.65)
   ↓
7. Create ReflectionResult
   ↓
8. Add strategy to playbook (in memory)
   ↓
9. session.update_playbook() called
   ↓
10. Playbook serialized to session JSON
    ↓
11. Session file saved to disk
```

### Code Flow

```python
# In async_query_processor.py, after tool execution:

# 1. Reflect on what happened
result = self.reflector.reflect(
    query="check the app file",
    tool_calls=[list_files, read_file],
    outcome="success"
)

# 2. If learning extracted
if result:
    session = self.repl.session_manager.current_session
    playbook = session.get_playbook()

    # Before: 3 strategies
    before_count = len(playbook.strategies)

    # 3. Add new strategy
    strategy = playbook.add_strategy(
        category=result.category,      # "file_operations"
        content=result.content         # "List directory before reading..."
    )

    # 4. Save to disk
    session.update_playbook(playbook)

    # After: 4 strategies
    after_count = len(playbook.strategies)

    # Logged: "Playbook size: 3 → 4 strategies"
```

## Tracking Methods

### Method 1: Real-Time Log File

**Location**: `/tmp/swecli_debug/playbook_evolution.log`

**What it logs**:
- When a new strategy is added
- What query triggered it
- What tools were executed
- The extracted strategy content
- Confidence score
- Reasoning behind extraction
- Current playbook state (all strategies)

**Example log entry**:
```
============================================================
🧠 PLAYBOOK EVOLUTION - 2025-10-23T11:40:15.789012
============================================================
Query: check the test file
Outcome: success
Category: file_operations
Strategy ID: fil-00002
Content: List directory contents before reading files to understand structure
Confidence: 0.75
Reasoning: Sequential list_files -> read_file pattern shows exploratory file access

Playbook size: 1 → 2 strategies
Session: abc123def456

Current playbook strategies:
  [fil-00000] file_operations: List directory before reading files
       (+3/-0/~0)
  [fil-00002] file_operations: List directory contents before reading files to understand structure
       (+0/-0/~0)
```

**How to monitor**:
```bash
# Watch the log in real-time
tail -f /tmp/swecli_debug/playbook_evolution.log

# See all evolution events
cat /tmp/swecli_debug/playbook_evolution.log
```

### Method 2: Session File Inspection

**Use the provided script**:
```bash
# Check playbook in most recent session
python /tmp/check_playbook.py

# Check specific session
python /tmp/check_playbook.py ~/.swecli/sessions/SESSION_ID.json
```

**Output example**:
```
📂 Session file: /Users/quocnghi/.swecli/sessions/abc123def456.json

📋 Playbook contains 4 strategies

### File Operations
  [fil-00000] List directory before reading files
      Effectiveness: +3/-0/~0
      Created: 2025-10-23T10:32:00.123456
      Last used: 2025-10-23T11:40:15.789012

  [fil-00002] Read files before writing to preserve data
      Effectiveness: +1/-0/~0
      Created: 2025-10-23T10:35:00.456789
      Last used: 2025-10-23T11:30:00.123456

### Testing
  [tes-00001] Run tests after code changes
      Effectiveness: +2/-0/~1
      Created: 2025-10-23T10:40:00.789012
      Last used: 2025-10-23T11:45:00.456789

📊 Summary:
   Total strategies: 4
   Categories: 2
   Total helpful tags: 6
   Total harmful tags: 0
```

### Method 3: Direct JSON Inspection

```bash
# View raw playbook data
cat ~/.swecli/sessions/SESSION_ID.json | jq '.playbook'

# Count strategies
cat ~/.swecli/sessions/SESSION_ID.json | jq '.playbook.strategies | length'

# List all strategy IDs
cat ~/.swecli/sessions/SESSION_ID.json | jq '.playbook.strategies | keys'

# Get specific strategy
cat ~/.swecli/sessions/SESSION_ID.json | jq '.playbook.strategies["fil-00000"]'

# Find most helpful strategies
cat ~/.swecli/sessions/SESSION_ID.json | jq '.playbook.strategies | to_entries | sort_by(.value.helpful_count) | reverse | .[0:3]'
```

### Method 4: Programmatic Access

```python
#!/usr/bin/env python3
import json
from pathlib import Path

# Load session
session_file = Path.home() / ".swecli" / "sessions" / "SESSION_ID.json"
with open(session_file) as f:
    session = json.load(f)

# Access playbook
playbook = session["playbook"]
strategies = playbook["strategies"]

print(f"Total strategies: {len(strategies)}")

# Analyze effectiveness
for sid, strategy in strategies.items():
    helpful = strategy["helpful_count"]
    harmful = strategy["harmful_count"]
    score = helpful - harmful
    print(f"{sid}: {strategy['content'][:50]}... (score: {score})")
```

## Playbook Lifecycle

### Creation
```python
# When session is created
session = Session(id="abc123", working_directory="/tmp")
playbook = session.get_playbook()  # Returns empty SessionPlaybook()
```

### Growth
```python
# After each qualifying tool execution
playbook.add_strategy(category="file_operations", content="...")
# Playbook grows: 0 → 1 → 2 → 3 strategies
```

### Effectiveness Tracking (Future)
```python
# When a strategy proves helpful/harmful
playbook.tag_strategy("fil-00000", "helpful")  # +1 helpful
playbook.tag_strategy("fil-00001", "harmful")  # +1 harmful
```

### Pruning (Future)
```python
# Remove low-value strategies
playbook.prune_harmful_strategies(threshold=-0.3)
# Removes strategies with effectiveness score < -0.3
```

### Cross-Session Sharing (Future)
```python
# Load strategies from other sessions in same repo
repo_playbook = merge_session_playbooks(working_directory)
# Combine learnings across sessions
```

## Monitoring Playbook Health

### Key Metrics

1. **Growth Rate**: How fast strategies accumulate
   ```bash
   # Count strategies per session
   for f in ~/.swecli/sessions/*.json; do
     count=$(jq '.playbook.strategies | length' "$f")
     echo "$(basename $f): $count strategies"
   done
   ```

2. **Effectiveness Score**: helpful - harmful
   ```python
   for strategy in playbook.strategies.values():
       score = strategy.helpful_count - strategy.harmful_count
       total = strategy.helpful_count + strategy.harmful_count + strategy.neutral_count
       if total > 0:
           effectiveness = score / total
           print(f"{strategy.id}: {effectiveness:.2f}")
   ```

3. **Category Distribution**: Which types of strategies dominate
   ```python
   from collections import Counter
   categories = [s.category for s in playbook.strategies.values()]
   print(Counter(categories))
   # Output: {'file_operations': 5, 'testing': 3, 'shell_commands': 2}
   ```

4. **Strategy Age**: How old are strategies?
   ```python
   from datetime import datetime
   for strategy in playbook.strategies.values():
       age = datetime.now() - strategy.created_at
       print(f"{strategy.id}: {age.days} days old")
   ```

## Debugging Playbook Issues

### Issue: Playbook not growing

**Check**:
1. Are tool calls being made?
   ```bash
   cat /tmp/swecli_debug/debug.log | grep "tool_calls"
   ```

2. Are reflections triggering?
   ```bash
   cat /tmp/swecli_debug/playbook_evolution.log
   ```

3. Is confidence threshold too high?
   ```python
   # In async_query_processor.py line 31:
   self.reflector = ExecutionReflector(
       min_tool_calls=2,     # Lower to 1 for more learning
       min_confidence=0.65   # Lower to 0.5 for more learning
   )
   ```

### Issue: Duplicate strategies

**Solution**: Add deduplication in playbook.py
```python
def add_strategy(self, category: str, content: str) -> Strategy:
    # Check for similar existing strategies
    for existing in self.strategies.values():
        if existing.category == category and self._is_similar(existing.content, content):
            return existing  # Don't add duplicate

    # Add new strategy
    ...
```

### Issue: Playbook not persisting

**Check**:
1. Is `session.update_playbook()` being called?
2. Is session file writable?
   ```bash
   ls -la ~/.swecli/sessions/
   ```

## Best Practices

### 1. Regular Monitoring
```bash
# Add to your shell profile for quick checks
alias playbook-check='python /tmp/check_playbook.py'
alias playbook-log='tail -20 /tmp/swecli_debug/playbook_evolution.log'
```

### 2. Periodic Cleanup
```bash
# Remove sessions older than 30 days
find ~/.swecli/sessions/ -name "*.json" -mtime +30 -delete
```

### 3. Backup Important Playbooks
```bash
# Before major changes
cp ~/.swecli/sessions/IMPORTANT_SESSION.json ~/backups/
```

### 4. Export Strategies
```python
# Extract all strategies across sessions
import json
from pathlib import Path

all_strategies = {}
sessions_dir = Path.home() / ".swecli" / "sessions"

for session_file in sessions_dir.glob("*.json"):
    with open(session_file) as f:
        session = json.load(f)
        strategies = session.get("playbook", {}).get("strategies", {})
        all_strategies.update(strategies)

# Save to master playbook
with open("master_playbook.json", "w") as f:
    json.dump(all_strategies, f, indent=2)

print(f"Exported {len(all_strategies)} strategies")
```

## Future Enhancements

### 1. UI Display
Show playbook in swecli UI:
```
┌─ Playbook (4 strategies) ─────────────────┐
│ File Operations (2)                        │
│ Testing (1)                                │
│ Shell Commands (1)                         │
└────────────────────────────────────────────┘
```

### 2. Strategy Effectiveness Feedback
Let user rate strategies:
```
> Was this strategy helpful? [y/n]
✓ Tagged fil-00000 as helpful
```

### 3. Cross-Session Sharing
```python
# Load repo-level playbook
repo_playbook = Playbook.load_for_repository("/path/to/project")
# Merge with session playbook
session.playbook.merge(repo_playbook)
```

### 4. Strategy Search
```bash
swecli playbook search "file operations"
swecli playbook stats
swecli playbook prune --harmful
```

---

**Last Updated**: 2025-10-23
**Related Docs**:
- `docs/ACE_ARCHITECTURE_ANALYSIS.md` - ACE architecture overview
- `docs/CONTEXT_MANAGEMENT_IMPLEMENTATION.md` - Implementation details
- `BUG_FIX_TOOL_CALLS.md` - Tool call preservation fix
