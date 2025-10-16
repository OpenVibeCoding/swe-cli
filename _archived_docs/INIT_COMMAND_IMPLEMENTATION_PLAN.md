# OpenCLI /init Command - Implementation Plan

## Date: 2025-10-07
## Status: Planning Phase
## Architecture: Pydantic AI-based

---

## Executive Summary

The `/init` command will create an intelligent codebase memory system by automatically scanning, analyzing, and summarizing projects into `OPENCLI.md` files. This provides persistent context for the AI agent, improving autonomy and reducing token waste.

**Core Philosophy: FULLY AUTOMATIC**
- ✨ **Zero Configuration**: Just type `/init` - agent decides everything
- 🤖 **Intelligent Adaptation**: Agent analyzes repo size and adjusts strategy
- 🔄 **Auto-Update Detection**: Recognizes existing OPENCLI.md and updates smartly
- 🎯 **No Manual Flags**: No `--depth`, `--update`, or other cognitive load

**Key Benefits:**
- 🧠 **Persistent Memory**: Agent remembers project structure across sessions
- 🚀 **Proactive Learning**: Auto-scans without manual intervention
- 🎯 **Context-Aware**: Uses summaries for better task execution
- 📊 **Hierarchical**: Global → Project → Subdir layering
- ⚡ **Efficient**: <30s for medium repos, token-optimized summaries
- 🎨 **Adaptive Detail**: Small repos get detailed analysis, large repos get smart summaries

**Alignment with Current Architecture:**
- Uses Pydantic AI agent system (OpenCLIAgent)
- Leverages existing tools (bash, grep, read, write)
- Integrates with mode_manager (NORMAL/PLAN)
- Follows AgentDependencies pattern

---

## Architecture Overview

### Current OpenCLI Architecture (Post Pydantic AI Refactor)

```
User Input
    ↓
REPL → Parse Command (/init)
    ↓
CommandHandler → Create Task
    ↓
OpenCLIAgent (Pydantic AI)
    ↓
Tools: bash_tool, file_ops, read, write, grep
    ↓
Generate OPENCLI.md
    ↓
Load as Context for Future Sessions
```

### /init Command Flow

```
/init [path]  # Optional path only - agent decides the rest
    ↓
InitCommandHandler
    ↓
Create Specialized Task: "Analyze and summarize codebase"
    ↓
Pydantic AI Agent Loop (Intelligent & Adaptive):
    1. Assess Repo Size (quick file count)
       ↓
    2. Decide Strategy (depth, detail level)
       ↓
    3. Scan Structure (bash: tree with adaptive depth)
       ↓
    4. Identify Dependencies (grep patterns)
       ↓
    5. Read Key Files (adaptive number based on size)
       ↓
    6. Check Existing OPENCLI.md (auto-detect update vs new)
       ↓
    7. Analyze Patterns (AI reasoning)
       ↓
    8. Generate Summary (AI synthesis)
    ↓
Write OPENCLI.md (write_tool - create or update)
    ↓
Register in ContextLoader
    ↓
Available for all future tasks
```

---

## Core Components

### 1. Command Handler (`opencli/commands/init_command.py`)

**Purpose**: Parse `/init` command and orchestrate codebase analysis

**Implementation:**
```python
"""Init command for codebase analysis and memory creation."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel

class InitCommandArgs(BaseModel):
    """Arguments for /init command."""
    path: Path = Path.cwd()
    skip_patterns: list[str] = [".git", "node_modules", "__pycache__", "venv", ".venv", "build", "dist"]

class InitCommandHandler:
    """Handles /init command execution."""

    def __init__(self, agent: OpenCLIAgent, console: Console):
        self.agent = agent
        self.console = console

    def parse_args(self, command: str) -> InitCommandArgs:
        """Parse /init command arguments."""
        # Parse: /init [path] (optional path only)
        pass

    def execute(self, args: InitCommandArgs, deps: AgentDependencies) -> dict:
        """Execute init command.

        Fully automatic - the AI agent decides:
        - How deep to scan (based on repo size)
        - What files to prioritize
        - Level of detail needed
        - Whether to update existing or create new
        """
        # 1. Let agent analyze and decide strategy
        # 2. Run agent with analysis task
        # 3. Agent automatically writes OPENCLI.md
        pass
```

**File Structure:**
```
opencli/commands/
    __init__.py
    init_command.py      # Main handler
    init_analyzer.py     # Analysis logic
    init_template.py     # OPENCLI.md templates
```

### 2. Codebase Analyzer (`opencli/commands/init_analyzer.py`)

**Purpose**: Specialized logic for analyzing codebase structure

**Key Functions:**
```python
class CodebaseAnalyzer:
    """Analyzes codebase structure and patterns."""

    def scan_structure(self, path: Path, depth: int) -> dict:
        """Scan directory structure using tree."""
        # bash: tree -L {depth} -a -I 'node_modules|.git'
        pass

    def detect_language(self, path: Path) -> str:
        """Detect primary language from file extensions."""
        # Count files by extension
        pass

    def extract_dependencies(self, path: Path, language: str) -> list[str]:
        """Extract dependencies based on language."""
        # Python: requirements.txt, setup.py, pyproject.toml
        # JS: package.json
        # Rust: Cargo.toml
        # Go: go.mod
        pass

    def find_entry_points(self, path: Path) -> list[Path]:
        """Find main entry points (main.py, index.js, etc.)."""
        # grep for common patterns
        pass

    def analyze_architecture(self, path: Path) -> dict:
        """Analyze architecture patterns."""
        # Detect: monolith, microservices, MVC, etc.
        # Look for folders like api/, models/, views/, services/
        pass

    def extract_coding_standards(self, path: Path) -> dict:
        """Extract coding standards from config files."""
        # .editorconfig, .pylintrc, .eslintrc, etc.
        pass

    def find_documentation(self, path: Path) -> list[Path]:
        """Find existing documentation files."""
        # README.md, CONTRIBUTING.md, docs/, etc.
        pass
```

### 3. AI-Powered Summarization System

**Purpose**: Use Pydantic AI agent to synthesize analysis into coherent summary

**System Prompt for /init:**
```python
INIT_SYSTEM_PROMPT = """You are an intelligent codebase analyzer for OpenCLI.

Your task: Analyze a software project and create a comprehensive OPENCLI.md file.

CRITICAL: Follow the strategic 4-phase scanning approach (see INIT_SCANNING_STRATEGY.md)

═══════════════════════════════════════════════════════════════════
PHASE 1: RECONNAISSANCE (Quick Assessment)
═══════════════════════════════════════════════════════════════════

First, gather metrics WITHOUT reading content:

1. Count files and directories:
   bash("find . -type f | wc -l")               # Total files
   bash("find . -type d | wc -l")               # Total dirs
   bash("du -sh .")                             # Size

2. Count by language:
   bash("find . -type f -name '*.py' | wc -l")  # Python
   bash("find . -type f -name '*.js' | wc -l")  # JavaScript
   bash("find . -type f -name '*.ts' | wc -l")  # TypeScript
   bash("find . -type f -name '*.go' | wc -l")  # Go
   bash("find . -type f -name '*.rs' | wc -l")  # Rust

3. Detect project type:
   bash("find . -maxdepth 2 -name 'package.json' -o -name 'requirements.txt' -o -name 'Cargo.toml'")

4. Check git context (if git repo):
   bash("git log --oneline -5 2>/dev/null")

DECISION POINT: Based on total file count, decide strategy:
- < 500 files  → DETAILED scan (read ~25 files)
- 500-5k files → BALANCED scan (read ~15 files)
- 5k-50k files → SELECTIVE scan (read ~10 files)
- > 50k files  → STRUCTURAL scan (read ~3 files)

═══════════════════════════════════════════════════════════════════
PHASE 2: PRIORITIZATION (Build Target List)
═══════════════════════════════════════════════════════════════════

Scan in priority order. Find files but DON'T read yet:

PRIORITY 1: Documentation (most efficient info source)
   bash("find . -maxdepth 1 -iname 'README*'")
   bash("find . -maxdepth 1 -iname 'CONTRIBUTING*'")
   bash("find . -maxdepth 2 -name '*.md' | head -10")

PRIORITY 2: Configuration (critical metadata)
   bash("find . -maxdepth 2 -name 'package.json' -o -name 'requirements.txt' -o -name 'Cargo.toml' -o -name 'go.mod'")
   bash("find . -maxdepth 2 -name 'Dockerfile' -o -name 'Makefile'")

PRIORITY 3: Entry Points (where code starts)
   # Python:
   bash("grep -r \"if __name__ == '__main__':\" --include='*.py' -l | head -5")
   bash("find . -name 'main.py' -o -name 'app.py' | head -3")

   # JavaScript:
   bash("grep -r 'export default' --include='*.js' -l | head -5")
   bash("find . -name 'index.js' -o -name 'main.js' | head -3")

   # Go:
   bash("find . -name 'main.go'")

   # Rust:
   bash("find . -name 'main.rs'")

PRIORITY 4: Core Structure (key architectural files)
   bash("find . -type d -name 'src' -o -name 'lib' -o -name 'core' -maxdepth 2")
   bash("find ./src -name '*.py' | head -5")  # Sample core files

PRIORITY 5: Tests (behavior expectations)
   bash("find . -name 'test_*.py' -o -name '*.test.js' | head -3")

═══════════════════════════════════════════════════════════════════
PHASE 3: TARGETED READING (Strategic File Reads)
═══════════════════════════════════════════════════════════════════

Based on your strategy decision, read files from priority list:

DETAILED scan (< 500 files): Read ~25 files
  - All docs found (Priority 1)
  - All configs found (Priority 2)
  - All entry points found (Priority 3)
  - 10 core files (Priority 4)
  - 5 test files (Priority 5)

BALANCED scan (500-5k files): Read ~15 files
  - Top 5 docs (Priority 1)
  - Top 5 configs (Priority 2)
  - Top 3 entry points (Priority 3)
  - 5 core files (Priority 4)
  - 2 test files (Priority 5)

SELECTIVE scan (5k-50k files): Read ~10 files
  - Top 3 docs (Priority 1)
  - Top 3 configs (Priority 2)
  - Top 2 entry points (Priority 3)
  - 3 core files (Priority 4)
  - 0 tests

STRUCTURAL scan (> 50k files): Read ~3 files
  - README only (Priority 1)
  - Main config only (Priority 2)
  - 1 entry point (Priority 3)
  - 0 core files
  - 0 tests

Use targeted grep for patterns (limit results):
  bash("grep -r '^class ' --include='*.py' -l | head -20")
  bash("grep -r 'TODO|FIXME' --include='*.py' -n | head -10")

═══════════════════════════════════════════════════════════════════
PHASE 4: SYNTHESIS (Generate Summary)
═══════════════════════════════════════════════════════════════════

Synthesize all findings into OPENCLI.md with relevant sections:

Standard sections (include if relevant):
  - Project Overview (name, language, description)
  - Folder Structure (high-level organization)
  - Dependencies (frameworks, libraries)
  - Architecture (patterns, design)
  - Key Files (entry points, configs)
  - Coding Standards (linters, formatters)
  - Development Workflow (build, test, deploy)
  - Known Issues (TODOs, FIXMEs)

Token budget based on repo size:
  - Small: 4000-5000 tokens
  - Medium: 3000-4000 tokens
  - Large: 2000-3000 tokens
  - Huge: 1500-2000 tokens

═══════════════════════════════════════════════════════════════════

IMPORTANT REMINDERS:
- ALWAYS exclude: node_modules/, .git/, __pycache__/, venv/, build/, dist/
- Use head/limit on all find/grep to avoid overwhelming results
- Check if OPENCLI.md exists first (read it to decide update vs rewrite)
- Call tools immediately without explanatory text first
- Time target: <30s for most repos

Output: Well-structured OPENCLI.md via write_file tool.
"""
```

**Tool Calling Strategy (Intelligent & Adaptive):**
```python
# Agent decides strategy based on repo size:

# Step 1: Quick assessment
1. bash("find . -type f | wc -l")  # File count
2. bash("du -sh .")  # Total size

# Step 2: Decide depth (agent's internal reasoning)
# Small repo (<500 files): depth=4, read 20 files
# Medium repo (500-5k files): depth=3, read 10 files
# Large repo (>5k files): depth=2, read 5 key files

# Step 3: Adaptive scanning
3. bash("tree -L {adaptive_depth} -a -I 'node_modules|.git|__pycache__'")
4. read("OPENCLI.md")  # Check if exists first
5. bash("find . -name 'requirements.txt' -o -name 'package.json' -o -name 'Cargo.toml'")
6. read("{detected_dependency_file}")
7. read("README.md")  # If exists
8. grep("{language_specific_pattern}", ".", recursive=True, limit={adaptive_limit})
9. bash("git log --oneline -10")  # Recent changes if git repo

# Step 4: Synthesize and write
10. write_file("OPENCLI.md", "{synthesized_content}")

# Agent adjusts each step based on previous results
```

### 4. OPENCLI.md Template (`opencli/commands/init_template.py`)

**Purpose**: Provide structured templates for generated files

**Template Structure:**
```markdown
# {Project Name}

> Generated by OpenCLI /init on {date}

## Project Overview

**Language**: {primary_language}
**Type**: {project_type}
**Description**: {brief_description}

## Folder Structure

```
{tree_output}
```

## Dependencies

### Production
{production_deps}

### Development
{dev_deps}

## Architecture

**Pattern**: {architecture_pattern}
**Key Components**:
- {component_1}: {description}
- {component_2}: {description}

## Key Files

- **Entry Point**: `{entry_point}`
- **Configuration**: `{config_files}`
- **Main Modules**: `{main_modules}`

## Coding Standards

- **Linter**: {linter}
- **Formatter**: {formatter}
- **Style Guide**: {style_guide}

## Development Workflow

### Build
```bash
{build_command}
```

### Test
```bash
{test_command}
```

### Run
```bash
{run_command}
```

## Known Issues

{todos_and_fixmes}

## Recent Changes

{git_log}

---

*This file is auto-generated. Edit manually or re-run `/init --update` to refresh.*
```

### 5. Context Loader (`opencli/core/context_loader.py`)

**Purpose**: Load and merge hierarchical OPENCLI.md files

**Implementation:**
```python
"""Context loader for hierarchical OPENCLI.md files."""

from pathlib import Path
from typing import Optional

class ContextLoader:
    """Loads and merges OPENCLI.md context files."""

    CONTEXT_FILENAME = "OPENCLI.md"

    def __init__(self):
        self.global_context: Optional[str] = None
        self.project_context: Optional[str] = None
        self.subdir_context: Optional[str] = None

    def load_contexts(self, working_dir: Path) -> str:
        """Load all context files hierarchically.

        Order: Global → Project → Subdir
        """
        contexts = []

        # 1. Global context (~/.opencli/OPENCLI.md)
        global_path = Path.home() / ".opencli" / self.CONTEXT_FILENAME
        if global_path.exists():
            self.global_context = global_path.read_text()
            contexts.append(f"# Global Context\n\n{self.global_context}")

        # 2. Project root context (git root or closest parent)
        project_root = self._find_project_root(working_dir)
        if project_root:
            project_path = project_root / self.CONTEXT_FILENAME
            if project_path.exists():
                self.project_context = project_path.read_text()
                contexts.append(f"# Project Context\n\n{self.project_context}")

        # 3. Current directory context
        local_path = working_dir / self.CONTEXT_FILENAME
        if local_path.exists() and local_path != project_path:
            self.subdir_context = local_path.read_text()
            contexts.append(f"# Directory Context\n\n{self.subdir_context}")

        return "\n\n---\n\n".join(contexts) if contexts else ""

    def _find_project_root(self, path: Path) -> Optional[Path]:
        """Find project root (git repo or first OPENCLI.md)."""
        current = path.absolute()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            if (current / self.CONTEXT_FILENAME).exists():
                return current
            current = current.parent
        return None
```

### 6. Integration with REPL (`opencli/repl/repl.py`)

**Changes needed:**

```python
class REPL:
    def __init__(self, ...):
        # ... existing init ...

        # Add context loader
        self.context_loader = ContextLoader()

        # Load contexts at startup
        self._load_project_context()

    def _load_project_context(self):
        """Load OPENCLI.md contexts into session."""
        context = self.context_loader.load_contexts(Path.cwd())
        if context:
            self.console.print("[dim]Loaded project context from OPENCLI.md[/dim]")
            # Add to session as system context
            self.session_manager.set_system_context(context)

    def _handle_command(self, command: str) -> bool:
        """Handle special commands."""
        # ... existing commands ...

        if command.startswith("/init"):
            return self._handle_init_command(command)

        # ... rest ...

    def _handle_init_command(self, command: str) -> bool:
        """Handle /init command."""
        from opencli.commands.init_command import InitCommandHandler

        handler = InitCommandHandler(self.pydantic_agent, self.console)
        args = handler.parse_args(command)

        deps = AgentDependencies(
            mode_manager=self.mode_manager,
            approval_manager=self.approval_manager,
            undo_manager=self.undo_manager,
            session_manager=self.session_manager,
            working_dir=Path.cwd(),
            console=self.console,
            config=self.config,
        )

        result = handler.execute(args, deps)

        if result["success"]:
            self.console.print(f"[green]✓[/green] {result['message']}")
            # Reload context
            self._load_project_context()
        else:
            self.console.print(f"[red]✗[/red] {result['message']}")

        return True
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1 - ~400 LOC)

**Goal**: Basic /init command structure

**Tasks:**
1. Create `opencli/commands/` directory structure
2. Implement `InitCommandHandler` with arg parsing
3. Implement `CodebaseAnalyzer` basic methods:
   - `scan_structure()` using bash tool
   - `detect_language()` by file extensions
   - `extract_dependencies()` for Python/JS
4. Create basic `init_template.py` with Markdown template
5. Add `/init` command routing in REPL

**Deliverables:**
- `/init` command recognized and parsed
- Basic directory structure scan works
- Template OPENCLI.md generated

**Testing:**
```bash
cd test_project
opencli
> /init
# Should generate basic OPENCLI.md with structure
```

### Phase 2: AI-Powered Analysis (Week 2 - ~300 LOC)

**Goal**: Integrate Pydantic AI for intelligent summarization

**Tasks:**
1. Create specialized system prompt for codebase analysis
2. Implement tool calling strategy:
   - bash for structure
   - grep for patterns
   - read for key files
3. Implement AI synthesis logic
4. Add error handling and validation
5. Support multiple languages (Python, JS, Rust, Go)

**Deliverables:**
- AI-generated summaries with proper sections
- Multi-language support
- Accurate dependency extraction

**Testing:**
```bash
# Test on various projects
/init ~/codes/python_project
/init ~/codes/js_react_app
/init ~/codes/rust_cli
```

### Phase 3: Hierarchical Context (Week 3 - ~250 LOC)

**Goal**: Implement context loading and merging

**Tasks:**
1. Implement `ContextLoader` class
2. Add hierarchical context loading (global → project → local)
3. Integrate with session_manager
4. Add context display in REPL startup
5. Implement `--update` flag for refreshing

**Deliverables:**
- Contexts loaded automatically at startup
- Hierarchical merging works correctly
- Update mechanism refreshes context

**Testing:**
```bash
# Create hierarchical contexts
echo "Global standards" > ~/.opencli/OPENCLI.md
/init  # Creates project OPENCLI.md
cd subdir
/init  # Creates subdir OPENCLI.md

# Test merging
opencli
# Should show: "Loaded 3 context files"
```

### Phase 4: Intelligence & Optimization (Week 4 - ~300 LOC)

**Goal**: Make agent truly intelligent and optimize performance

**Tasks:**
1. Implement intelligent size detection and adaptive scanning
2. Add progress indicators for large repos
3. Implement smart update detection (auto-detect if OPENCLI.md exists)
4. Add validation metrics (coverage, accuracy)
5. Performance optimization (<30s target)
6. Handle edge cases (empty repos, binary-heavy repos, etc.)

**Deliverables:**
- Agent adapts scan strategy automatically
- Fast scanning even for large repos
- Smart update mechanism (auto-detects changes)
- User-friendly progress display

**Testing:**
```bash
# Test adaptive behavior
/init  # On small repo (should do detailed scan)
/init  # On large repo (should do high-level scan)
/init  # Run twice (should detect existing and update)

# Performance benchmark
time opencli --prompt "/init" --working-dir large_repo
# Target: <30s for 10k LOC
```

### Phase 5: Integration & Polish (Week 5 - ~150 LOC)

**Goal**: Complete integration and documentation

**Tasks:**
1. Add help text for `/init` command
2. Update main README with /init examples
3. Create user guide for OPENCLI.md customization
4. Add unit tests for all components
5. E2E tests on sample projects
6. Performance benchmarks

**Deliverables:**
- Complete documentation
- Test coverage >80%
- Performance validated

---

## Technical Specifications

### Tool Usage Patterns

**For Python Projects:**
```python
# 1. Find dependency files
bash("find . -name 'requirements.txt' -o -name 'setup.py' -o -name 'pyproject.toml'")

# 2. Read dependencies
read("requirements.txt")

# 3. Find Python files
bash("find . -name '*.py' | wc -l")

# 4. Find entry points
grep("if __name__ == '__main__':", ".", recursive=True)

# 5. Find classes and functions
grep("^(class|def) ", ".", recursive=True, limit=50)
```

**For JavaScript Projects:**
```python
# 1. Read package.json
read("package.json")

# 2. Find JS/TS files
bash("find . -name '*.js' -o -name '*.ts' -o -name '*.jsx' -o -name '*.tsx' | wc -l")

# 3. Find entry points
grep("export default|module.exports", ".", recursive=True)

# 4. Detect framework
grep("import.*from ['\"]react|vue|angular", ".", recursive=True)
```

### Performance Targets

| Codebase Size | Target Time | Max Tokens |
|---------------|-------------|------------|
| Small (<1k LOC) | <5s | 2k tokens |
| Medium (1-10k LOC) | <15s | 4k tokens |
| Large (10-100k LOC) | <30s | 6k tokens |
| Huge (>100k LOC) | <60s | 8k tokens |

**Optimization Strategies:**
- Limit file reads (max 20 files)
- Sample large directories
- Use token-efficient summaries
- Cache results for `--update`

### Error Handling

```python
class InitError(Exception):
    """Base exception for init command."""
    pass

class NoProjectFoundError(InitError):
    """No valid project found at path."""
    pass

class ScanTimeoutError(InitError):
    """Scanning took too long."""
    pass

# Usage in handler
try:
    result = analyzer.scan_structure(path)
except NoProjectFoundError:
    console.print("[yellow]Warning: No recognizable project structure found.[/yellow]")
    # Generate minimal template
except ScanTimeoutError:
    console.print("[yellow]Scan timed out. Using partial results.[/yellow]")
    # Use what we have
```

---

## Testing Strategy

### Unit Tests (`tests/commands/test_init_command.py`)

```python
def test_parse_init_args():
    """Test argument parsing."""
    handler = InitCommandHandler(mock_agent, mock_console)

    args = handler.parse_args("/init")
    assert args.path == Path.cwd()
    assert args.update == False

    args = handler.parse_args("/init /tmp --update --depth 2")
    assert args.path == Path("/tmp")
    assert args.update == True
    assert args.depth == 2

def test_detect_language():
    """Test language detection."""
    analyzer = CodebaseAnalyzer()

    # Mock file structure
    with temp_project(files=["main.py", "test.py", "setup.py"]):
        lang = analyzer.detect_language(Path.cwd())
        assert lang == "Python"

def test_extract_python_dependencies():
    """Test Python dependency extraction."""
    analyzer = CodebaseAnalyzer()

    with temp_file("requirements.txt", "flask==2.0.1\nrequests==2.26.0"):
        deps = analyzer.extract_dependencies(Path.cwd(), "Python")
        assert "flask" in deps
        assert "requests" in deps
```

### Integration Tests (`tests/integration/test_init_e2e.py`)

```python
def test_init_python_project():
    """Test /init on sample Python project."""
    with sample_python_project() as project_dir:
        # Run init
        result = run_opencli_command(f"/init {project_dir}")

        # Check OPENCLI.md exists
        opencli_md = project_dir / "OPENCLI.md"
        assert opencli_md.exists()

        # Validate content
        content = opencli_md.read_text()
        assert "Project Overview" in content
        assert "Python" in content
        assert "Dependencies" in content

def test_init_hierarchical_loading():
    """Test hierarchical context loading."""
    with temp_project_hierarchy() as (global_dir, project_dir, subdir):
        # Create contexts at each level
        (global_dir / "OPENCLI.md").write_text("Global: Standards")
        (project_dir / "OPENCLI.md").write_text("Project: Architecture")
        (subdir / "OPENCLI.md").write_text("Subdir: Module X")

        # Load contexts
        loader = ContextLoader()
        context = loader.load_contexts(subdir)

        # Verify all three are present
        assert "Global: Standards" in context
        assert "Project: Architecture" in context
        assert "Subdir: Module X" in context
```

### Performance Tests

```python
def test_init_performance_medium_repo():
    """Test performance on medium repo (10k LOC)."""
    with sample_repo(size="medium") as repo_dir:
        start = time.time()
        run_opencli_command(f"/init {repo_dir}")
        duration = time.time() - start

        assert duration < 15.0  # <15s for medium repos
```

---

## Usage Examples

### Basic Usage

```bash
# Initialize current project (agent decides everything)
opencli
> /init
Analyzing codebase...
[Agent reasoning: Small repo (47 files) → detailed scan, depth=4]
✓ Detected: Python project (Flask API)
✓ Found 47 files across 8 directories
✓ Extracted 12 dependencies
✓ Generated OPENCLI.md (3.2k tokens)

# View generated summary
> /read OPENCLI.md
```

### Re-run on Same Project

```bash
# Agent automatically detects existing OPENCLI.md
> /init
Analyzing codebase...
[Agent: OPENCLI.md exists, checking for changes...]
[Agent: 3 new files, 2 new dependencies → updating existing file]
✓ Updated OPENCLI.md with recent changes
```

### Different Project Sizes

```bash
# Small project
> /init
[Agent: 100 files → detailed scan, reading 15 files]
✓ Generated comprehensive OPENCLI.md (4.5k tokens)

# Large project
> /init
[Agent: 10,000 files → high-level scan, sampling key files]
✓ Generated overview OPENCLI.md (3.8k tokens)
```

### Custom Path

```bash
> /init ~/projects/my-app
Analyzing ~/projects/my-app...
[Agent: Medium repo (1,200 files) → balanced scan]
✓ Generated OPENCLI.md at ~/projects/my-app/OPENCLI.md
```

---

## Future Enhancements

### Phase 6+ (Post-Launch)

1. **Auto-Refresh on Git Events**
   - Watch `.git` for changes
   - Auto-update OPENCLI.md on pull/merge

2. **MCP Integration**
   - Fetch external docs (from URLs, APIs)
   - Include in context

3. **Interactive Editing**
   ```bash
   > /init --interactive
   Generated summary. Add details? [y/n/edit]
   > edit
   # Opens AI-assisted editor
   ```

4. **Multi-Language Documentation**
   - Generate OPENCLI.md in user's language
   - Support i18n

5. **Visual Context Browser**
   ```bash
   > /context
   # Shows hierarchical tree of contexts
   # Allows toggling sections on/off
   ```

6. **Smart Compression**
   - AI-powered summarization for huge repos
   - Focus on frequently-accessed modules

7. **Integration with Other Commands**
   ```bash
   > /explain auth
   # Agent uses OPENCLI.md: "From context: Auth in src/auth.py"

   > /implement new feature
   # Agent: "Based on project structure, I'll add to src/features/"
   ```

---

## Success Metrics

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Summary Accuracy** | >90% | Manual review: key elements present |
| **Dependency Coverage** | >95% | Compare to actual deps |
| **Language Detection** | >98% | Test on diverse projects |
| **Entry Point Detection** | >85% | Verify correct main files |

### Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Scan Time (Medium)** | <15s | Automated benchmarks |
| **Scan Time (Large)** | <30s | Automated benchmarks |
| **Token Efficiency** | <5k tokens | Monitor output size |
| **Update Speed** | <5s | Incremental updates |

### User Experience Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Success Rate** | >95% | % of successful scans |
| **User Edits** | <10% | % needing manual fixes |
| **Context Usefulness** | >80% | User survey: helpful? |
| **Adoption Rate** | >60% | % of users using /init |

---

## Risk Mitigation

### Technical Risks

1. **Large Codebase Performance**
   - **Risk**: Scanning 1M+ LOC takes too long
   - **Mitigation**:
     - Implement depth limits
     - Use sampling strategies
     - Add timeout mechanism

2. **Inaccurate Summaries**
   - **Risk**: AI generates wrong/incomplete summaries
   - **Mitigation**:
     - Extensive testing on diverse projects
     - User feedback loop
     - Allow manual corrections

3. **Tool Failures**
   - **Risk**: bash/grep tools fail on certain platforms
   - **Mitigation**:
     - Fallback mechanisms
     - Cross-platform testing
     - Graceful degradation

### User Experience Risks

1. **Overwhelming Output**
   - **Risk**: Too much information in OPENCLI.md
   - **Mitigation**:
     - Progressive disclosure (basic → detailed)
     - Collapsible sections
     - Summary-first approach

2. **Stale Context**
   - **Risk**: Users forget to update, context becomes outdated
   - **Mitigation**:
     - Auto-detect staleness (check git log)
     - Prompt for updates
     - Show last updated timestamp

---

## Conclusion

The `/init` command will transform OpenCLI into a context-aware, proactive AI assistant by automatically building and maintaining project memory. This aligns perfectly with the Pydantic AI architecture and leverages existing tools effectively.

**Next Steps:**
1. ✅ Review and approve this plan
2. 🔄 Create implementation branch: `feature/init-command`
3. 🚀 Begin Phase 1: Foundation (Week 1)
4. 📊 Track progress in project board

**Timeline**: 5 weeks for complete implementation
**Effort**: ~1400 LOC total
**Impact**: High - fundamental feature for proactive AI assistance

---

*This plan is a living document. Update as implementation progresses.*
