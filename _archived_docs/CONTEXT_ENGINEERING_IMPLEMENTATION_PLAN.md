# Context Engineering Implementation Plan

**Based on:** `CONTEXT_ENGINEERING_DESIGN.md`
**Date:** 2025-10-07
**Status:** Implementation Ready

---

## 🎯 Overview

This plan implements Anthropic's context engineering principles in SWE-CLI by enhancing the existing `Session`, `ChatMessage`, and `SessionManager` infrastructure.

**Existing Foundation:**
- ✅ `Session` model with messages and metadata
- ✅ `ChatMessage` model with role, content, tool_calls
- ✅ `SessionManager` for persistence
- ❌ Accurate token counting (currently uses rough len/4)
- ❌ Compaction when context gets large
- ❌ Just-in-time context retrieval
- ❌ Codebase summary (OPENCLI.md)

---

## 📐 Architecture Integration

### Existing vs New Components

```
EXISTING:
┌────────────────────────────────────────┐
│  SessionManager                         │
│  ├─ Session                            │
│  │  ├─ messages: List[ChatMessage]    │
│  │  ├─ context_files: List[str]       │
│  │  └─ metadata: Dict                 │
│  └─ save/load from .swecli/sessions/ │
└────────────────────────────────────────┘

NEW (ADDITIONS):
┌────────────────────────────────────────┐
│  ContextEngine (NEW)                    │
│  ├─ TokenMonitor (tiktoken)           │
│  ├─ Compactor (AI-driven)             │
│  └─ ContextRetriever (just-in-time)   │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  CodebaseIndex (NEW)                    │
│  └─ OPENCLI.md generation & loading    │
└────────────────────────────────────────┘
```

---

## 🔧 Phase 1: Token Monitoring (Week 1)

### Goal
Replace rough token estimation with accurate tiktoken-based counting.

### Files to Create/Modify

#### 1. Create `swecli/core/token_monitor.py`

```python
"""Accurate token counting using tiktoken."""

import tiktoken
from typing import List, Dict, Any
from swecli.models.message import ChatMessage, ToolCall


class TokenMonitor:
    """Monitor and count tokens accurately using tiktoken."""

    def __init__(self, model: str = "gpt-4"):
        """Initialize with tiktoken encoding.

        Args:
            model: Model name for tiktoken encoding
        """
        self.encoding = tiktoken.encoding_for_model(model)
        self.context_limit = 256000  # 256k tokens for Claude 3.5
        self.compaction_threshold = 0.8  # Compact at 80%

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        return len(self.encoding.encode(text))

    def count_message_tokens(self, message: ChatMessage) -> int:
        """Count tokens in a complete message.

        Args:
            message: Chat message

        Returns:
            Total token count including tool calls
        """
        total = self.count_tokens(message.content)

        # Add tool call tokens
        for tool_call in message.tool_calls:
            total += self._count_tool_call_tokens(tool_call)

        return total

    def _count_tool_call_tokens(self, tool_call: ToolCall) -> int:
        """Count tokens in a tool call.

        Args:
            tool_call: Tool call to count

        Returns:
            Token count
        """
        # Tool name + parameters + result
        total = self.count_tokens(tool_call.name)
        total += self.count_tokens(str(tool_call.parameters))

        if tool_call.result:
            total += self.count_tokens(str(tool_call.result))

        return total

    def count_messages_total(self, messages: List[ChatMessage]) -> int:
        """Count total tokens across all messages.

        Args:
            messages: List of messages

        Returns:
            Total token count
        """
        return sum(self.count_message_tokens(msg) for msg in messages)

    def needs_compaction(self, current_tokens: int) -> bool:
        """Check if compaction is needed.

        Args:
            current_tokens: Current token count

        Returns:
            True if compaction needed
        """
        return current_tokens >= (self.context_limit * self.compaction_threshold)

    def get_usage_stats(self, current_tokens: int) -> Dict[str, Any]:
        """Get token usage statistics.

        Args:
            current_tokens: Current token count

        Returns:
            Usage statistics dict
        """
        return {
            "current_tokens": current_tokens,
            "limit": self.context_limit,
            "available": self.context_limit - current_tokens,
            "usage_percent": (current_tokens / self.context_limit) * 100,
            "needs_compaction": self.needs_compaction(current_tokens),
        }
```

#### 2. Modify `swecli/models/session.py`

Add token_monitor integration:

```python
from swecli.core.token_monitor import TokenMonitor

class Session(BaseModel):
    """Represents a conversation session."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: list[ChatMessage] = Field(default_factory=list)
    context_files: list[str] = Field(default_factory=list)
    working_directory: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # NEW: Token tracking
    _token_monitor: Optional[TokenMonitor] = None
    total_tokens_cached: int = 0

    def get_token_monitor(self) -> TokenMonitor:
        """Get or create token monitor."""
        if not self._token_monitor:
            self._token_monitor = TokenMonitor()
        return self._token_monitor

    def add_message(self, message: ChatMessage) -> None:
        """Add a message and update token count."""
        self.messages.append(message)
        self.updated_at = datetime.now()

        # Update token count using tiktoken
        token_monitor = self.get_token_monitor()
        message.tokens = token_monitor.count_message_tokens(message)
        self.total_tokens_cached = token_monitor.count_messages_total(self.messages)

    def needs_compaction(self) -> bool:
        """Check if session needs compaction."""
        token_monitor = self.get_token_monitor()
        return token_monitor.needs_compaction(self.total_tokens_cached)

    def get_token_stats(self) -> Dict[str, Any]:
        """Get token usage statistics."""
        token_monitor = self.get_token_monitor()
        return token_monitor.get_usage_stats(self.total_tokens_cached)
```

#### 3. Add tiktoken to dependencies

```bash
pip install tiktoken
```

Add to `pyproject.toml` or `requirements.txt`:
```
tiktoken>=0.5.0
```

### Testing

Create `test_token_monitor.py`:

```python
#!/usr/bin/env python3
"""Test TokenMonitor."""

from swecli.core.token_monitor import TokenMonitor
from swecli.models.message import ChatMessage, Role, ToolCall

def test_basic_counting():
    """Test basic token counting."""
    monitor = TokenMonitor()

    # Simple text
    text = "Hello, world!"
    tokens = monitor.count_tokens(text)
    print(f"'{text}' = {tokens} tokens")
    assert tokens > 0

    # Message
    msg = ChatMessage(role=Role.USER, content=text)
    msg_tokens = monitor.count_message_tokens(msg)
    print(f"Message tokens: {msg_tokens}")
    assert msg_tokens == tokens

def test_tool_call_counting():
    """Test tool call token counting."""
    monitor = TokenMonitor()

    tool_call = ToolCall(
        id="tc_123",
        name="write_file",
        parameters={"file_path": "test.py", "content": "print('hello')"},
        result="File written successfully"
    )

    tokens = monitor._count_tool_call_tokens(tool_call)
    print(f"Tool call tokens: {tokens}")
    assert tokens > 10  # Should be substantial

def test_compaction_threshold():
    """Test compaction threshold detection."""
    monitor = TokenMonitor()

    # Below threshold
    assert not monitor.needs_compaction(100000)  # 39%

    # Above threshold
    assert monitor.needs_compaction(210000)  # 82%

def test_usage_stats():
    """Test usage statistics."""
    monitor = TokenMonitor()

    stats = monitor.get_usage_stats(150000)
    print(f"\nUsage stats for 150k tokens:")
    print(f"  Usage: {stats['usage_percent']:.1f}%")
    print(f"  Available: {stats['available']} tokens")
    print(f"  Needs compaction: {stats['needs_compaction']}")

    assert stats["current_tokens"] == 150000
    assert stats["available"] == 106000

if __name__ == "__main__":
    print("Testing TokenMonitor...\n")
    test_basic_counting()
    test_tool_call_counting()
    test_compaction_threshold()
    test_usage_stats()
    print("\n✅ All tests passed!")
```

---

## 🗜️ Phase 2: Compaction Engine (Week 2)

### Goal
Implement AI-driven context compaction that reduces token usage by 60-80%.

### Files to Create

#### 1. Create `swecli/core/compactor.py`

```python
"""AI-driven context compaction."""

from typing import List, Dict, Any
from datetime import datetime
from swecli.models.message import ChatMessage, Role
from swecli.core.agent import SWE-CLIAgent


class ContextCompactor:
    """Compact conversation history using AI summarization."""

    def __init__(self, agent: SWE-CLIAgent):
        """Initialize compactor.

        Args:
            agent: SWE-CLI agent for LLM calls
        """
        self.agent = agent

    async def compact_messages(
        self,
        messages: List[ChatMessage],
        keep_recent: int = 20
    ) -> List[ChatMessage]:
        """Compact messages using AI summarization.

        Strategy:
        - Keep last N messages as-is (recent context)
        - Summarize older messages into dense summary
        - Aim for 60-80% token reduction

        Args:
            messages: Full message history
            keep_recent: Number of recent messages to keep unmodified

        Returns:
            Compacted message list: [summary_message] + recent_messages
        """
        if len(messages) <= keep_recent:
            return messages  # No compaction needed

        # Split messages
        to_compact = messages[:-keep_recent]
        recent = messages[-keep_recent:]

        # Build compaction prompt
        prompt = self._build_compaction_prompt(to_compact)

        # Call LLM to generate summary
        summary_content = await self._generate_summary(prompt)

        # Create summary message
        summary_msg = ChatMessage(
            role=Role.SYSTEM,
            content=f"""
=== CONVERSATION HISTORY SUMMARY ===
Compacted {len(to_compact)} messages at {datetime.now().isoformat()}

{summary_content}

=== END SUMMARY ===

Recent conversation follows below (unmodified)...
""",
            timestamp=datetime.now(),
            metadata={
                "compaction": True,
                "original_message_count": len(to_compact),
                "compacted_at": datetime.now().isoformat(),
            }
        )

        # Return summary + recent messages
        return [summary_msg] + recent

    def _build_compaction_prompt(self, messages: List[ChatMessage]) -> str:
        """Build prompt for compaction LLM call.

        Args:
            messages: Messages to compact

        Returns:
            Compaction prompt
        """
        # Format messages for compaction
        formatted = []
        for i, msg in enumerate(messages):
            role = msg.role.value.upper()
            content = msg.content[:500]  # Truncate long messages
            tool_summary = ""

            if msg.tool_calls:
                tool_names = [tc.name for tc in msg.tool_calls]
                tool_summary = f" [Tools: {', '.join(tool_names)}]"

            formatted.append(f"{i+1}. {role}{tool_summary}: {content}")

        messages_text = "\n".join(formatted)

        return f"""You are a context compaction assistant. Summarize this conversation history
while preserving ALL critical information.

PRESERVE (extract and keep):
- Key decisions and their rationale
- Bug fixes with file paths and solutions
- Feature implementations and design choices
- Important file paths, function names, code patterns
- Current project state and goals
- Error messages and debugging insights

REMOVE (omit or compress):
- Verbose explanations already acted upon
- Full tool outputs (keep only key results/references)
- Conversational pleasantries
- Repeated or redundant information

Original History ({len(messages)} messages):

{messages_text}

Generate a DENSE, STRUCTURED summary that reduces tokens by 70% while preserving
all critical context. Use bullet points and clear sections. Be concise but complete.
"""

    async def _generate_summary(self, prompt: str) -> str:
        """Generate summary using LLM.

        Args:
            prompt: Compaction prompt

        Returns:
            Generated summary text
        """
        # Build messages for LLM call
        llm_messages = [{"role": "user", "content": prompt}]

        # Call LLM (reuse existing agent)
        response = await self.agent.call_llm(llm_messages)

        if not response.get("success"):
            raise RuntimeError(f"Compaction failed: {response.get('error')}")

        return response["content"]

    def estimate_reduction(
        self,
        original_tokens: int,
        compacted_tokens: int
    ) -> Dict[str, Any]:
        """Estimate compaction effectiveness.

        Args:
            original_tokens: Token count before compaction
            compacted_tokens: Token count after compaction

        Returns:
            Compaction statistics
        """
        reduction = original_tokens - compacted_tokens
        reduction_percent = (reduction / original_tokens) * 100

        return {
            "original_tokens": original_tokens,
            "compacted_tokens": compacted_tokens,
            "tokens_saved": reduction,
            "reduction_percent": reduction_percent,
            "success": 60 <= reduction_percent <= 85,  # Target range
        }
```

#### 2. Modify `swecli/core/session_manager.py`

Add compaction support:

```python
from swecli.core.compactor import ContextCompactor

class SessionManager:
    """Manages session persistence and retrieval."""

    def __init__(self, session_dir: Path, agent: Optional[SWE-CLIAgent] = None):
        """Initialize session manager.

        Args:
            session_dir: Directory to store session files
            agent: SWE-CLI agent for compaction (optional)
        """
        self.session_dir = Path(session_dir).expanduser()
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[Session] = None
        self.turn_count = 0

        # NEW: Compactor
        self.compactor = ContextCompactor(agent) if agent else None

    async def check_and_compact(self) -> bool:
        """Check if compaction is needed and perform it.

        Returns:
            True if compaction was performed
        """
        if not self.current_session or not self.compactor:
            return False

        # Check if compaction needed
        if not self.current_session.needs_compaction():
            return False

        print("\n⏱️  Context approaching limit, compacting history...")

        # Get token stats before
        stats_before = self.current_session.get_token_stats()

        # Compact messages
        compacted = await self.compactor.compact_messages(
            self.current_session.messages
        )

        # Update session
        self.current_session.messages = compacted

        # Recalculate tokens
        token_monitor = self.current_session.get_token_monitor()
        self.current_session.total_tokens_cached = token_monitor.count_messages_total(
            compacted
        )

        # Get stats after
        stats_after = self.current_session.get_token_stats()

        # Calculate reduction
        reduction = self.compactor.estimate_reduction(
            stats_before["current_tokens"],
            stats_after["current_tokens"]
        )

        # Update metadata
        self.current_session.metadata["last_compaction"] = datetime.now().isoformat()
        self.current_session.metadata["compaction_count"] = (
            self.current_session.metadata.get("compaction_count", 0) + 1
        )
        self.current_session.metadata["compaction_stats"] = reduction

        # Save
        self.save_session()

        print(f"✅ Compacted: {reduction['tokens_saved']} tokens saved "
              f"({reduction['reduction_percent']:.1f}% reduction)")

        return True
```

### Testing

Create `test_compactor.py`:

```python
#!/usr/bin/env python3
"""Test ContextCompactor."""

import asyncio
from swecli.core.compactor import ContextCompactor
from swecli.models.message import ChatMessage, Role

async def test_compaction():
    """Test message compaction."""
    # Create test messages
    messages = []

    # Simulate conversation
    messages.append(ChatMessage(
        role=Role.USER,
        content="Create a user authentication system"
    ))
    messages.append(ChatMessage(
        role=Role.ASSISTANT,
        content="I'll create an authentication system with JWT tokens..."
    ))

    # Add many more messages...
    for i in range(30):
        messages.append(ChatMessage(
            role=Role.USER,
            content=f"Update step {i}"
        ))
        messages.append(ChatMessage(
            role=Role.ASSISTANT,
            content=f"Updated step {i} successfully"
        ))

    print(f"Original: {len(messages)} messages")

    # Create compactor (needs agent)
    from swecli.core.agent import SWE-CLIAgent
    from swecli.models.config import AppConfig

    config = AppConfig()
    agent = SWE-CLIAgent(config, None, None)
    compactor = ContextCompactor(agent)

    # Compact
    compacted = await compactor.compact_messages(messages, keep_recent=10)

    print(f"Compacted: {len(compacted)} messages")
    print(f"Summary message length: {len(compacted[0].content)} chars")

    assert len(compacted) < len(messages)
    assert compacted[0].metadata.get("compaction") == True

if __name__ == "__main__":
    asyncio.run(test_compaction())
```

---

## 🔍 Phase 3: Just-in-Time Retrieval (Week 3)

### Goal
Implement proactive context retrieval based on user intent.

### Files to Create

#### 1. Create `swecli/core/context_retriever.py`

```python
"""Just-in-time context retrieval."""

from typing import List, Dict, Any, Optional
from pathlib import Path
from swecli.tools.file_ops import FileOperations
from swecli.tools.bash_tool import BashTool


class ContextRetriever:
    """Retrieve relevant context based on user input."""

    def __init__(
        self,
        file_ops: FileOperations,
        bash_tool: BashTool
    ):
        """Initialize retriever.

        Args:
            file_ops: File operations tool
            bash_tool: Bash execution tool
        """
        self.file_ops = file_ops
        self.bash_tool = bash_tool

    async def retrieve_for_task(
        self,
        user_input: str,
        working_dir: Path
    ) -> Dict[str, Any]:
        """Retrieve relevant context for a task.

        Strategy:
        1. Parse user input for files, patterns, keywords
        2. Proactively grep for relevant patterns
        3. Read mentioned files
        4. Run discovery commands if needed

        Args:
            user_input: User's request
            working_dir: Current working directory

        Returns:
            Context dict with grep_results, files_read, bash_outputs
        """
        context = {
            "task_description": user_input,
            "grep_results": [],
            "files_read": [],
            "bash_outputs": [],
            "estimated_tokens": 0,
        }

        # 1. Extract entities from user input
        entities = self._extract_entities(user_input)

        # 2. Grep for patterns
        for pattern in entities["patterns"]:
            results = await self._grep_pattern(pattern, working_dir)
            if results:
                context["grep_results"].append({
                    "pattern": pattern,
                    "matches": results[:10],  # Limit to top 10
                    "total_matches": len(results)
                })

        # 3. Read mentioned files
        for file_path in entities["files"]:
            full_path = working_dir / file_path
            if full_path.exists():
                content = await self._read_file(full_path)
                context["files_read"].append({
                    "path": str(file_path),
                    "content": content[:2000],  # Limit size
                    "full_size": len(content)
                })

        # 4. Run discovery commands
        if entities["needs_listing"]:
            output = await self._list_files(working_dir, entities["file_pattern"])
            context["bash_outputs"].append({
                "command": f"find {entities['file_pattern']}",
                "output": output[:1000]
            })

        # Estimate tokens added
        context["estimated_tokens"] = self._estimate_context_tokens(context)

        return context

    def _extract_entities(self, user_input: str) -> Dict[str, Any]:
        """Extract entities from user input.

        Simple rule-based extraction for common patterns.

        Args:
            user_input: User input text

        Returns:
            Entities dict
        """
        entities = {
            "files": [],
            "patterns": [],
            "needs_listing": False,
            "file_pattern": "*.py"
        }

        text_lower = user_input.lower()

        # Extract file mentions (e.g., "main.py", "src/auth.py")
        import re
        file_pattern = r'\b[\w/]+\.(py|js|ts|java|go|rs|cpp|c|h)\b'
        entities["files"] = re.findall(file_pattern, user_input)

        # Extract search patterns
        if any(word in text_lower for word in ["find", "search", "grep", "look for"]):
            # Extract quoted terms
            quoted = re.findall(r'"([^"]+)"', user_input)
            entities["patterns"].extend(quoted)

        # Keywords that trigger pattern searches
        keyword_patterns = {
            "login": ["login", "auth", "authenticate"],
            "error": ["error", "exception", "fail"],
            "api": ["endpoint", "route", "api"],
            "database": ["query", "db", "database", "sql"],
            "test": ["test", "spec", "assert"],
        }

        for keyword, patterns in keyword_patterns.items():
            if keyword in text_lower:
                entities["patterns"].extend(patterns)

        # Check if needs file listing
        if any(word in text_lower for word in ["list", "show", "what files"]):
            entities["needs_listing"] = True

        # Deduplicate
        entities["files"] = list(set(entities["files"]))
        entities["patterns"] = list(set(entities["patterns"]))

        return entities

    async def _grep_pattern(
        self,
        pattern: str,
        working_dir: Path
    ) -> List[Dict[str, str]]:
        """Grep for a pattern.

        Args:
            pattern: Search pattern
            working_dir: Directory to search

        Returns:
            List of matches with file and line
        """
        try:
            result = self.file_ops.search_code(pattern, str(working_dir))
            return result.get("matches", [])
        except Exception:
            return []

    async def _read_file(self, file_path: Path) -> str:
        """Read file contents.

        Args:
            file_path: Path to file

        Returns:
            File contents
        """
        try:
            return self.file_ops.read_file(str(file_path))
        except Exception:
            return ""

    async def _list_files(
        self,
        working_dir: Path,
        pattern: str
    ) -> str:
        """List files matching pattern.

        Args:
            working_dir: Directory to search
            pattern: File pattern (e.g., "*.py")

        Returns:
            Command output
        """
        try:
            result = self.bash_tool.run_command(
                f"find {working_dir} -name '{pattern}' -type f | head -50"
            )
            return result.get("output", "")
        except Exception:
            return ""

    def _estimate_context_tokens(self, context: Dict[str, Any]) -> int:
        """Estimate tokens in retrieved context.

        Args:
            context: Context dict

        Returns:
            Estimated token count
        """
        total = 0

        # Grep results
        for grep in context["grep_results"]:
            total += len(str(grep)) // 4

        # Files read
        for file_info in context["files_read"]:
            total += len(file_info["content"]) // 4

        # Bash outputs
        for bash in context["bash_outputs"]:
            total += len(bash["output"]) // 4

        return total
```

### Testing

Create `test_context_retriever.py`:

```python
#!/usr/bin/env python3
"""Test ContextRetriever."""

import asyncio
from pathlib import Path
from swecli.core.context_retriever import ContextRetriever

async def test_entity_extraction():
    """Test entity extraction."""
    retriever = ContextRetriever(None, None)

    test_cases = [
        ("Fix the login bug in src/auth.py", ["src/auth.py"], ["login", "auth"]),
        ("Find all API endpoints", [], ["endpoint", "route", "api"]),
        ("List all Python files", [], []),
    ]

    for user_input, expected_files, expected_patterns in test_cases:
        entities = retriever._extract_entities(user_input)
        print(f"\nInput: {user_input}")
        print(f"Files: {entities['files']}")
        print(f"Patterns: {entities['patterns']}")

if __name__ == "__main__":
    asyncio.run(test_entity_extraction())
```

---

## 📄 Phase 4: Codebase Index (OPENCLI.md) (Week 4)

### Goal
Generate and maintain OPENCLI.md codebase summary.

### Files to Create

#### 1. Create `swecli/commands/init_command.py`

```python
"""Initialize project with OPENCLI.md generation."""

from pathlib import Path
from typing import Dict, Any
from swecli.tools.file_ops import FileOperations
from swecli.tools.bash_tool import BashTool
from swecli.core.agent import SWE-CLIAgent


class InitCommand:
    """Generate OPENCLI.md codebase summary."""

    def __init__(
        self,
        file_ops: FileOperations,
        bash_tool: BashTool,
        agent: SWE-CLIAgent
    ):
        """Initialize command.

        Args:
            file_ops: File operations
            bash_tool: Bash tool
            agent: SWE-CLI agent
        """
        self.file_ops = file_ops
        self.bash_tool = bash_tool
        self.agent = agent

    async def execute(self, working_dir: Path) -> str:
        """Generate OPENCLI.md.

        Args:
            working_dir: Project directory

        Returns:
            Path to generated OPENCLI.md
        """
        print("📊 Scanning codebase...")

        # 1. Discover project structure
        structure = await self._scan_structure(working_dir)

        # 2. Identify key files
        key_files = await self._identify_key_files(working_dir)

        # 3. Discover patterns
        patterns = await self._discover_patterns(working_dir)

        # 4. Generate summary using LLM
        summary = await self._generate_summary(
            working_dir,
            structure,
            key_files,
            patterns
        )

        # 5. Write OPENCLI.md
        swecli_md_path = working_dir / "OPENCLI.md"
        self.file_ops.write_file(str(swecli_md_path), summary, create_dirs=False)

        print(f"✅ Generated {swecli_md_path}")

        return str(swecli_md_path)

    async def _scan_structure(self, working_dir: Path) -> Dict[str, List[str]]:
        """Scan project structure.

        Args:
            working_dir: Project directory

        Returns:
            Structure dict: folder -> [files]
        """
        # Use tree or find command
        result = self.bash_tool.run_command(
            f"find {working_dir} -type f -name '*.py' ! -path '*/.*' | head -100"
        )

        files = result.get("output", "").strip().split("\n")

        # Group by directory
        structure = {}
        for file in files:
            if not file:
                continue
            file_path = Path(file)
            folder = str(file_path.parent)
            if folder not in structure:
                structure[folder] = []
            structure[folder].append(file_path.name)

        return structure

    async def _identify_key_files(self, working_dir: Path) -> List[str]:
        """Identify key files (high importance).

        Args:
            working_dir: Project directory

        Returns:
            List of key file paths
        """
        # Heuristics: main files, large files, frequently imported
        key_patterns = ["main.py", "app.py", "__init__.py", "api.py", "server.py"]

        result = self.bash_tool.run_command(
            f"find {working_dir} -type f \\( -name 'main.py' -o -name 'app.py' -o -name 'api.py' \\)"
        )

        return result.get("output", "").strip().split("\n")

    async def _discover_patterns(self, working_dir: Path) -> Dict[str, str]:
        """Discover code patterns.

        Args:
            working_dir: Project directory

        Returns:
            Pattern dict: name -> location
        """
        patterns = {}

        # Common patterns to look for
        searches = {
            "Authentication": "auth",
            "Database": "db|database|model",
            "API Routes": "router|endpoint|route",
            "Configuration": "config|settings",
        }

        for name, pattern in searches.items():
            results = self.file_ops.search_code(pattern, str(working_dir))
            if results.get("matches"):
                first_match = results["matches"][0]
                patterns[name] = f"{first_match['file']}:{first_match['line']}"

        return patterns

    async def _generate_summary(
        self,
        working_dir: Path,
        structure: Dict,
        key_files: List[str],
        patterns: Dict
    ) -> str:
        """Generate summary using LLM.

        Args:
            working_dir: Project directory
            structure: Project structure
            key_files: Key file paths
            patterns: Discovered patterns

        Returns:
            OPENCLI.md content
        """
        prompt = f"""Generate a concise codebase summary for OPENCLI.md.

Project Directory: {working_dir}

Structure ({len(structure)} folders):
{self._format_structure(structure)}

Key Files:
{chr(10).join(f'- {f}' for f in key_files[:10])}

Discovered Patterns:
{chr(10).join(f'- {name}: {loc}' for name, loc in patterns.items())}

Generate a MARKDOWN summary with these sections:
1. ## Overview (2-3 sentences about the project)
2. ## Structure (tree-like view of main folders/files)
3. ## Key Files (list with brief descriptions)
4. ## Patterns (common code patterns and their locations)
5. ## Dependencies (if identifiable from imports)

Keep it under 3000 tokens. Be concise but informative.
"""

        response = await self.agent.call_llm([{"role": "user", "content": prompt}])

        if not response.get("success"):
            raise RuntimeError("Failed to generate summary")

        return response["content"]

    def _format_structure(self, structure: Dict) -> str:
        """Format structure for display.

        Args:
            structure: Structure dict

        Returns:
            Formatted string
        """
        lines = []
        for folder, files in list(structure.items())[:10]:  # Limit
            lines.append(f"{folder}/")
            for file in files[:5]:  # Limit files per folder
                lines.append(f"  - {file}")
        return "\n".join(lines)
```

#### 2. Register `/init` command

Add to REPL command handlers.

### Testing

Create `test_init_command.py`:

```python
#!/usr/bin/env python3
"""Test InitCommand."""

import asyncio
from pathlib import Path
from swecli.commands.init_command import InitCommand

async def test_init():
    """Test /init command."""
    working_dir = Path("/Users/quocnghi/codes/test_swecli")

    cmd = InitCommand(file_ops, bash_tool, agent)

    swecli_md = await cmd.execute(working_dir)

    print(f"Generated: {swecli_md}")

    # Verify file exists
    assert Path(swecli_md).exists()

    # Read and display
    with open(swecli_md) as f:
        content = f.read()
        print(f"\n{content[:500]}...")

if __name__ == "__main__":
    asyncio.run(test_init())
```

---

## 🎯 Phase 5: Integration (Week 5)

### Goal
Integrate all components into REPL flow.

### Files to Modify

#### 1. Modify `swecli/repl/repl.py`

Add context management to main loop:

```python
from swecli.core.token_monitor import TokenMonitor
from swecli.core.context_retriever import ContextRetriever

class REPL:
    """Main REPL loop."""

    def __init__(self, ...):
        ...
        self.token_monitor = TokenMonitor()
        self.context_retriever = ContextRetriever(file_ops, bash_tool)

    async def handle_user_input(self, user_input: str):
        """Handle user input with context management."""

        # 1. Check for compaction
        compacted = await self.session_manager.check_and_compact()
        if compacted:
            print("✅ Context compacted, continuing...")

        # 2. Retrieve just-in-time context
        task_context = await self.context_retriever.retrieve_for_task(
            user_input,
            self.working_dir
        )

        # 3. Add context to prompt
        enriched_input = self._enrich_with_context(user_input, task_context)

        # 4. Add user message
        user_msg = ChatMessage(role=Role.USER, content=enriched_input)
        self.session_manager.add_message(user_msg)

        # 5. Get messages for LLM (includes OPENCLI.md)
        messages = self._build_llm_messages()

        # 6. Call LLM
        response = await self.agent.call_llm(messages)

        # 7. Add assistant message
        assistant_msg = ChatMessage(
            role=Role.ASSISTANT,
            content=response["content"],
            tool_calls=response.get("tool_calls", [])
        )
        self.session_manager.add_message(assistant_msg)

        # 8. Display token stats
        stats = self.session_manager.current_session.get_token_stats()
        print(f"[dim]Tokens: {stats['current_tokens']}/{stats['limit']} "
              f"({stats['usage_percent']:.1f}%)[/dim]")

    def _build_llm_messages(self) -> List[Dict]:
        """Build messages for LLM including OPENCLI.md."""
        messages = []

        # 1. System prompt
        messages.append({
            "role": "system",
            "content": self.agent.system_prompt
        })

        # 2. Codebase summary (if exists)
        swecli_md = self.working_dir / "OPENCLI.md"
        if swecli_md.exists():
            with open(swecli_md) as f:
                messages.append({
                    "role": "system",
                    "content": f"# Codebase Context\n\n{f.read()}"
                })

        # 3. Conversation history
        messages.extend(
            self.session_manager.current_session.to_api_messages()
        )

        return messages
```

---

## 📊 Phase 6: Metrics & Monitoring (Week 6)

### Goal
Add metrics dashboard and optimization.

### Files to Create

#### 1. Create `swecli/commands/stats_command.py`

```python
"""/stats command to show context statistics."""

class StatsCommand:
    """Display context statistics."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    def execute(self) -> None:
        """Display stats."""
        session = self.session_manager.current_session

        if not session:
            print("No active session")
            return

        stats = session.get_token_stats()

        print("\n📊 Context Statistics")
        print(f"  Tokens: {stats['current_tokens']:,} / {stats['limit']:,}")
        print(f"  Usage: {stats['usage_percent']:.1f}%")
        print(f"  Available: {stats['available']:,} tokens")
        print(f"  Messages: {len(session.messages)}")

        if session.metadata.get("compaction_count"):
            comp_stats = session.metadata.get("compaction_stats", {})
            print(f"\n  Compactions: {session.metadata['compaction_count']}")
            print(f"  Last Reduction: {comp_stats.get('reduction_percent', 0):.1f}%")

        print()
```

---

## 🎯 Success Metrics

Track these metrics to measure success:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Token Accuracy** | ±5% | Compare tiktoken vs API usage |
| **Compaction Reduction** | 60-80% | Before/after token count |
| **Context Preservation** | >95% | Manual review of summaries |
| **Retrieval Precision** | >85% | Relevant context retrieved |
| **Compaction Frequency** | 1-2 per long session | Count compactions |
| **User Interruptions** | <5% | Compaction disrupts flow |

---

## 📝 Implementation Checklist

### Week 1: Token Monitoring ✓
- [ ] Create `token_monitor.py` with tiktoken
- [ ] Modify `Session` model for token tracking
- [ ] Update `ChatMessage` to cache tokens
- [ ] Test with `test_token_monitor.py`
- [ ] Verify accuracy with real API calls

### Week 2: Compaction ✓
- [ ] Create `compactor.py` with AI summarization
- [ ] Modify `SessionManager` for auto-compaction
- [ ] Add compaction prompt engineering
- [ ] Test with `test_compactor.py`
- [ ] Verify 60-80% reduction target

### Week 3: Just-in-Time Retrieval ✓
- [ ] Create `context_retriever.py`
- [ ] Implement entity extraction
- [ ] Add proactive grep/read logic
- [ ] Test with `test_context_retriever.py`
- [ ] Measure retrieval precision

### Week 4: Codebase Index ✓
- [ ] Create `init_command.py`
- [ ] Implement structure scanning
- [ ] Add pattern discovery
- [ ] Generate OPENCLI.md via LLM
- [ ] Test with test project

### Week 5: Integration ✓
- [ ] Modify REPL to use all components
- [ ] Add OPENCLI.md to LLM context
- [ ] Integrate just-in-time retrieval
- [ ] Auto-compaction in conversation flow
- [ ] Display token stats

### Week 6: Metrics & Polish ✓
- [ ] Create `/stats` command
- [ ] Add performance logging
- [ ] Optimize compaction prompts
- [ ] User testing and feedback
- [ ] Documentation

---

## 🚀 Next Steps

1. **Start with Week 1** - Token monitoring is foundational
2. **Test each phase** before moving to next
3. **Iterate on prompts** - Compaction prompt is critical
4. **Gather metrics** - Track success criteria
5. **User feedback** - Get real-world testing

---

**Ready to implement!** Start with Phase 1: Token Monitoring.
