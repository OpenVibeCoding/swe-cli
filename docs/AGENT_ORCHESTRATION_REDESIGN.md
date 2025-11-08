# Agent Orchestration Redesign (Agent-lightning Alignment)

## Why This Redesign
- SWE-CLI currently wires agents through `RuntimeService` → `AgentFactory` → `SwecliAgent`/`PlanningAgent`, then lets `QueryProcessor` hand-roll the ReAct loop (`swecli/repl/query_processor.py`). This works for interactive sessions but it cannot (1) treat each request as a **Task**, (2) persist **Rollouts/Spans** for learning, or (3) coordinate training loops that optimize prompts or behaviors.
- The [*Train the First Agent with Agent-lightning* guide](https://microsoft.github.io/agent-lightning/stable/how-to/train-first-agent/) shows a minimal-yet-powerful recipe: `Task` → `Rollout` → `Span` → `Algorithm` (APO) → `Trainer`. Aligning SWE-CLI to that recipe gives us prompt tuning, automated regression evaluation, and reusable traces for ACE.
- Goal: keep the interactive UX intact while splitting orchestration concerns into explicit, testable layers that can run locally (REPL), in the upcoming UI, or in offline training jobs.

---

## Current-State Observations & Gaps
| Area | Current Behavior (files) | Gaps |
| --- | --- | --- |
| Agent lifecycle | `RuntimeService.build_suite()` and `AgentFactory` tie the system to two concrete agents and expose them directly to REPL/query processor (`swecli/core/services/runtime_service.py`, `swecli/core/factories/agent_factory.py`). | No abstraction for runners, no pluggable orchestration, no notion of task batches or concurrent rollouts. |
| Execution tracing | Tool calls stream through `QueryProcessor._handle_tool_calls()` while ACE reflection happens afterwards (`swecli/repl/query_processor.py`). | We log results but never emit structured spans that algorithms like APO expect (LLM calls, tools, rewards, metadata). |
| Prompt templates | `SystemPromptBuilder` and `PlanningPromptBuilder` generate strings at instantiation time; session playbooks (ACE) are appended inline. | Templates are not versioned, cannot be swapped during training, and cannot be optimized automatically. |
| Learning loop | ACE adaptation exists (`agentic-context-engine/ace`) but is detached from SWE-CLI’s agent entry points. Training requires ad-hoc scripts and can’t re-use REPL traces. | No `Trainer` abstraction, no task datasets, no automated evaluation/reward pipeline. |
| Observability | `SessionManager` stores raw messages; undo/history is separate (`swecli/core/management`). | We have no unified trace store, reward metrics, or hooks for Opik/LangSmith spans. |

---

## Design Pillars (inspired by Agent-lightning)
1. **Everything is a Task** – Every user prompt, GitHub issue, or scripted scenario is represented as a `TaskSpec`. Tasks can be queued, replayed, or sampled for offline training.
2. **Rollouts emit Spans** – Each autonomous attempt (LLM+tools) is a `Rollout` composed of nested `Span` objects (LLM call, tool invocation, evaluator, reward). Spans always include structured metadata so adapters like `TraceToMessages` (from the Agent-lightning APO tutorial) can consume them.
3. **Prompt templates are resources** – Templates (baseline + ACE-augmented + experimental) live in a repository with version IDs, metadata, and diffable edits produced by algorithms.
4. **Trainer orchestrates algorithms** – A new Trainer service feeds tasks → runner → trace store → algorithm updates (APO, ACE, RL), mirroring the `Trainer.fit()` loop in the tutorial.
5. **Runtime parity** – The same runner stack powers interactive REPL, Textual UI, and offline jobs. Differences (approval dialogs, UI callbacks, concurrency) become adapters instead of copy/paste logic.

---

## Terminology Mapping

| Agent-lightning Concept | SWE-CLI Redesign Counterpart |
| --- | --- |
| Task (dataset sample) | `TaskSpec` / `TaskInstance` (`swecli/core/orchestration/tasks.py`) – structured wrapper over user prompts, GitHub issues, or scripted benchmarks. |
| Rollout | `Rollout` (`swecli/core/orchestration/rollouts.py`) – captures one full attempt, including prompt template ID, runner metadata, success flags, and reward. |
| Span | `Span` entities emitted by `SpanRecorder` (`swecli/core/orchestration/spans.py`) whenever an LLM call, tool execution, approval, or evaluator runs. |
| Prompt Template | `PromptTemplate` (`swecli/core/orchestration/prompts.py`) – versioned template that can inject ACE playbook sections and experimental edits. |
| Algorithm (APO, RL, ACE) | `TrainingAlgorithm` interface (`swecli/core/orchestration/algorithms/base.py`) with adapters like `ApoAlgorithm` (wraps Agent-lightning APO) or `AceAdapter`. |
| Trainer | `TrainerService` (`swecli/core/orchestration/trainer.py`) – coordinates tasks, runner pool, trace store, validation datasets, and algorithm updates with `trainer.fit(agent=..., train_dataset=..., val_dataset=...)`. |
| Runner | `AgentRunner` (`swecli/core/orchestration/runner.py`) – thin wrapper around `SwecliAgent`/`PlanningAgent` plus approvals, context builders, and message compaction. |
| Store | `TraceStore` (`swecli/core/orchestration/store.py`) – persists rollouts + spans for replay, reward audits, ACE learning, and algorithm adapters. |

---

## Proposed Architecture

```
┌───────────────┐      ┌──────────────────────┐      ┌───────────────────┐
│ Task Sources  │ ───▶ │ TaskGraph / Queue    │ ───▶ │ Runner Pool       │
│  (REPL, GH,   │      │  (batching, retries) │      │  (n parallel)     │
│   datasets)   │      └────────┬─────────────┘      └────────┬──────────┘
└───────────────┘               │                             │
                                ▼                             ▼
                       ┌────────────────┐             ┌──────────────────┐
                       │ Span Recorder  │◀────────────│ Agent Interface  │
                       └────────┬───────┘             └──────────────────┘
                                │
                                ▼
                       ┌────────────────┐
                       │ Trace Store    │──┐
                       └────────┬───────┘  │   ┌───────────────────────┐
                                │          ├──▶│ Training Algorithms    │
                                ▼          │   │ (APO, ACE, RL)        │
                       ┌────────────────┐  │   └──────────┬────────────┘
                       │ Reward Engine  │──┘              │
                       └────────┬───────┘                 ▼
                                │                ┌──────────────────┐
                                ▼                │ Prompt Registry   │
                       ┌────────────────┐        │ (versioned templates)
                       │ TrainerService │◀───────┴──────────────────┘
                       └────────────────┘
```

### 1. TaskGraph (`swecli/core/orchestration/tasks.py`)
- Ingests tasks from interactive REPL, Github issue resolver, scripted datasets, or HTTP API.
- Normalizes into `TaskSpec` dataclasses (fields: `task_id`, `kind`, `inputs`, `repo_snapshot`, `evaluation_plan`, `metadata`).
- Provides iterators for `trainer.fit(...)` and handles priority queues (e.g., validation vs. training).
- Backed by lightweight persistence (SQLite or JSONL) so offline jobs can resume unfinished tasks.

### 2. AgentRunner + RunnerPool (`runner.py`)
- Wraps existing `SwecliAgent` and `PlanningAgent` but hides the LLM loop behind a `run(task: TaskInstance, template: PromptTemplate) -> Rollout`.
- Handles approvals, interrupts, tool display formatting by delegating to adapters (`CliRunAdapter`, `HeadlessRunAdapter`).
- RunnerPool manages `n_runners` concurrency like Agent-lightning’s `Trainer(n_runners=8)`, enabling fast evaluation sweeps.

### 3. SpanRecorder (`spans.py`)
- Hooks into provider adapters (`swecli/core/providers`) and tool registry execution path to produce structured spans:
  ```python
  Span(
      span_id="tool:write_file:123",
      parent_id="rollout:456",
      kind="tool",
      name="write_file",
      input=tool_args,
      output=tool_result,
      start_ts=...,
      end_ts=...,
      metrics={"latency_ms": 220},
      tags={"file_path": "..."}
  )
  ```
- Emits JSON serializable events so TraceToMessages (from Agent-lightning APO) can sample conversation snippets automatically.
- Optional Opik/LangSmith exporters plug in here instead of inside random tools.

### 4. TraceStore & Reward Engine (`store.py`, `rewards.py`)
- TraceStore persists task metadata, rollouts, spans, and final rewards; supports querying by task, template version, or metric.
- Reward Engine evaluates rollouts per task definition: run tests, diff outputs, compare to `ground_truth`, or call rubric graders (LLM-as-judge). Returns scalar reward (0–1) and structured feedback, matching Agent-lightning’s “grader function”.
- Stored feedback feeds ACE’s playbook tagging and algorithm critiques.

### 5. PromptTemplate Registry (`prompts.py`)
- Abstracts system prompt assembly: baseline builder + ACE playbook + experiment-specific injections.
- Tracks versions (`prompt_template://baseline@v3`, `prompt_template://apo/2024-12-01T02`). Each rollout stores the template version it used.
- Supports diff + apply operations so APO’s textual gradients can patch templates directly.

### 6. Training Algorithms (`algorithms/`)
- `TrainingAlgorithm` protocol exposes `propose_updates(rollouts: list[Rollout]) -> PromptDelta`.
- `ApoAlgorithm` wraps Agent-lightning’s APO flow: it calls `TraceToMessages` on spans, asks LLMs for critiques/rewrites (`gpt-5-mini` -> textual gradient, `gpt-4.1-mini` -> rewrite), then emits a delta.
- `AceAdapter` surfaces the existing playbook/curator loop as an algorithm option (tag strategies, add bullets).
- Future slot for RLHF/VERL style algorithms without touching runners.

### 7. TrainerService (`trainer.py`)
- API mirrors Agent-lightning:
  ```python
  trainer = TrainerService(
      algorithm=ApoAlgorithm(...),
      task_graph=TaskGraph(...),
      runner_pool=RunnerPool(...),
      trace_store=TraceStore(...),
      prompt_registry=PromptRegistry(...),
  )
  trainer.fit(train_dataset, val_dataset)
  ```
- Handles evaluation cadence (train batches, gradient batches, beam search / branch factor like the tutorial), stores metrics, and surfaces progress via CLI/Textual dashboards.
- Supports offline batch jobs (headless) and “train on latest session” button inside REPL.

### 8. Integration with Existing Modules
- `RuntimeService` now assembles `RunnerSuite` instead of direct agent objects; REPL uses `runner_pool.acquire()` to execute a single task interactively.
- `QueryProcessor` becomes a thin adapter that converts user input → `TaskSpec`, invokes `AgentRunner` once, then streams span events back to the UI.
- `SessionManager` stores references to rollouts (by ID) rather than embedding every raw message, enabling replay/resume.
- ACE playbook integration moves into `PromptTemplate` injection + `TraceStore` tagging so we no longer bolt ACE logic onto the REPL after the fact.

---

## Data & Control Flow
1. **Task creation** – User prompt (REPL), GitHub issue, or benchmark sample becomes a `TaskSpec`. Metadata includes approvals policy, evaluation plan, and repo snapshot hash.
2. **Prompt selection** – `PromptRegistry` returns the active prompt template version (baseline, APO candidate, fallback). ACE playbook context is appended here.
3. **Rollout execution** – Runner spins up the appropriate agent (normal vs. planning) and executes ReAct steps. Every LLM call and tool execution passes through `SpanRecorder`.
4. **Reward evaluation** – After the rollout, `RewardEngine` executes the grader (tests, heuristics, LLM judge) and stores reward + textual feedback as a span.
5. **Trace persistence** – `TraceStore` writes `(TaskSpec, Rollout, Spans, Reward)`; SessionManager links this rollout ID with the user-visible transcript.
6. **Algorithm update** – Trainer requests rollouts from TraceStore, converts spans to messages with `TraceToMessages`, runs APO (or ACE/RL) to propose prompt edits, then submits the delta to `PromptRegistry`.
7. **Validation** – RunnerPool replays validation tasks with the new prompt; metrics decide whether to adopt the template version.

---

## Implementation Roadmap
### Phase 1 – Instrumentation & Data Model
1. Create `swecli/core/orchestration/` package with Task/Rollout/Span dataclasses and registries.
2. Embed `SpanRecorder` hooks inside `SwecliAgent.run_sync` and the tool executor path (`swecli/repl/query_processor.py`) so interactive sessions already emit spans, even before Trainer exists.
3. Introduce `TraceStore` (start with SQLite/JSONL) and update `SessionManager` to reference rollout IDs.

### Phase 2 – RunnerPool + Prompt Registry
1. Refactor `RuntimeService` to build `RunnerSuite` (`normal_runner`, `planning_runner`, `runner_pool`).
2. Wrap system prompt builders in `PromptTemplate` objects with version metadata; add persistence under `~/.swecli/prompts/`.
3. Update REPL/Textual to request rollouts through `AgentRunner` (ensuring approvals + interrupts travel through adapters).

### Phase 3 – Trainer + Algorithm Adapters
1. Implement `TrainingAlgorithm` interface and `ApoAlgorithm` adapter that shells out to Agent-lightning components (`TraceToMessages`, textual gradient, rewrite LLMs).
2. Build `TrainerService` with `trainer.fit()` matching the tutorial’s API (supports `n_runners`, `val_batch_size`, etc.).
3. Provide CLI entry points (e.g., `swecli train --algo apo --dataset examples/room_selector.jsonl`) and UI toggles to launch optimization runs.

### Phase 4 – Advanced Integrations
1. Connect ACE playbook updates to TraceStore spans instead of ad-hoc reflection.
2. Add Opik/LangSmith exporters to `SpanRecorder` for deep observability.
3. Implement task importers for GitHub issues, regression suites, and Paper2Code specs so they automatically populate the TaskGraph.

---

## Risks & Open Questions
- **Reward fidelity** – We must define deterministic graders for coding tasks (tests, static analysis) so APO doesn’t overfit to noisy LLM judges.
- **Storage overhead** – Spans + diffs for long sessions can be large; TraceStore needs pruning/compaction policies.
- **Approval semantics** – Automated runner batches must respect approval settings (auto-approve in headless mode, prompt user in interactive mode).
- **Template safety** – Prompt rewrites must be validated (linting, guardrails) before entering user-facing sessions; PromptRegistry should support staged rollout (canary, full).
- **Concurrency** – RunnerPool introduces concurrency in a codebase built for single-threaded REPL. Need async-safe tool execution wrappers or job queues.

---

## Immediate Next Steps
1. Bootstrap `swecli/core/orchestration/` with data classes + registries and migrate `SessionManager` to store rollout IDs.
2. Instrument LLM/tool calls with SpanRecorder events and write them to a temporary JSONL trace store.
3. Prototype `TrainerService` running APO over a small dataset (room selector sample) to ensure TraceToMessages integration works end-to-end.

