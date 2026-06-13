# HyperAgents Framework Plan

This plan describes how to evolve HyperAgents from a research implementation
into a polished, reusable framework for controlled agent-evolution
experiments. The first implementation pass should remain docs/spec-only. Major
refactors should start only after the relevant spec under `specs/` exists.

## Current Architecture

The current codebase is a research prototype with a valuable set of primitives:

- Self-modification through `meta_agent.py` and `run_meta_agent.py`.
- Archive-based evolution through `archive.jsonl` and per-generation metadata.
- Parent/child lineage through `metadata.json` parent IDs.
- Patch generation and application through git diffs and
  `utils/gl_utils.py::apply_diffs_container`.
- Evaluation loops in `generate_loop.py`, `domains/harness.py`,
  `domains/report.py`, and `domains/polyglot/*`.
- Docker-based execution through `utils/docker_utils.py` and Polyglot-specific
  Docker helpers.
- Domain-specific benchmark adapters for text classification, Balrog, Genesis,
  IMO, and Polyglot.

The architecture is currently centered on `generate_loop.py`, which combines
orchestration, storage, Docker lifecycle, parent selection, patch handling,
evaluation, plotting, and baseline-specific behavior. The future framework
should preserve behavior through adapters first, then extract stable
interfaces.

## Key Files And Responsibilities

- `generate_loop.py`
  - Primary CLI and generation loop.
  - Creates run directories under `outputs/`.
  - Selects parents, invokes the meta-agent, applies lineage patches, evaluates
    generated agents, updates archive metadata, runs ensemble evals, and emits
    plots.
- `meta_agent.py`
  - Defines the current self-modifying meta-agent.
  - Uses unrestricted tool access in the copied repository.
- `task_agent.py`
  - Defines the current task agent contract for benchmark rows.
  - Expects the model to produce JSON with a `response`.
- `agent/`
  - `llm.py` wraps LiteLLM and hardcoded model constants.
  - `llm_withtools.py` implements JSON-formatted tool calls.
  - `tools/bash.py` and `tools/edit.py` expose shell and file-editing actions.
- `utils/gl_utils.py`
  - Stores archive helpers, lineage helpers, score readers, initial copy setup,
    patch application, parent selection, and compilation checks.
- `utils/docker_utils.py`
  - Builds and runs Docker containers, copies files through tar archives, logs
    output, verifies GPU support, and cleans containers.
- `utils/domain_utils.py`
  - Hardcodes domain score keys, splits, staged eval sizes, test subsets, and
    ensemble support.
- `domains/`
  - Provides benchmark datasets, formatters, harnesses, reports, and
    domain-specific evaluators.
- `analysis/`
  - Reads implicit archive/report file layouts to create plots and lineage
    visualizations.
- `baselines/`
  - Contains baseline implementations and compatibility paths used by
    `generate_loop.py`.

## Pain Points

- `generate_loop.py` is monolithic orchestration. It mixes runner lifecycle,
  archive mutation, Docker setup, patch handling, staged/full evaluation,
  plotting, baseline handling, and CLI parsing.
- `utils/domain_utils.py` hardcodes domain metadata in `if/elif` chains.
  Adding a domain requires changing core utilities and duplicated CLI choices.
- `utils/gl_utils.py::apply_diffs_container` uses ad hoc patch filtering and
  `patch -p1`, then commits everything with a placeholder message. It has no
  explicit dry-run, review, structured rejection result, or policy object.
- `utils/docker_utils.py::build_container` builds and runs with host networking
  and a read/write repository mount. That is useful for research but unsafe as a
  framework default.
- `agent/llm.py` hardcodes provider/model constants and model-specific parameter
  behavior in a single function.
- `setup_initial.sh` and `utils/gl_utils.py::setup_initial_gen` depend on
  precomputed `outputs/initial_*` folders and copy filtered repository trees
  using implicit exclusion lists.
- `domains/harness.py` mixes a dynamic import convention for text domains with
  explicit Balrog and Genesis branches.
- `domains/polyglot/harness.py` duplicates sandbox/copy logic and mutates patch
  files before evaluation.
- `analysis/*` depends on undocumented JSON file layouts instead of a queryable
  run store or event stream.
- Failure handling is mostly exception logging plus metadata booleans. There is
  no typed failure taxonomy for patch rejection, compile failure, sandbox
  timeout, evaluation failure, or model failure.
- Observability is file-oriented logs and static plots. There is no structured
  event stream that can support inspection, replay, or dashboards.

## Proposed Framework Architecture

Target package layout:

```text
hyperagents/
  core/
    runner.py
    archive.py
    lineage.py
    evaluator.py
    parent_selection.py
    candidate.py
    patch_manager.py
    result.py
  agents/
    base.py
    task_agent.py
    meta_agent.py
    tool_agent.py
  domains/
    base.py
    registry.py
  sandbox/
    docker.py
    policy.py
    mounts.py
    limits.py
  storage/
    sqlite.py
    filesystem.py
    artifacts.py
  config/
    schema.py
    loader.py
    defaults.py
  cli/
    main.py
    init.py
    run.py
    inspect.py
  observability/
    events.py
    logs.py
    traces.py
    dashboard.py
```

The framework should separate these responsibilities:

- Orchestration: one runner owns lifecycle and state transitions.
- Agent generation: meta-agent plugins return patch results.
- Patch application: patch manager validates, dry-runs, applies, and persists.
- Evaluation: evaluator invokes domain plugins for stage/full/test phases.
- Storage: SQLite holds normalized run state; filesystem holds large artifacts.
- Sandboxing: sandbox runner enforces a policy by default.
- Domain plugins: domains own task staging, evaluation, score normalization, and
  artifact collection.
- Model providers: LiteLLM becomes one provider behind an interface.
- Observability: events, logs, traces, and dashboard data are append-only and
  queryable.

## Proposed Module Boundaries

- `core.runner`
  - Loads config, creates the run directory, initializes storage, runs
    generations, emits events, and delegates all external work.
- `core.candidate`
  - Represents a candidate agent version, parent, generation, patch set, and
    working tree reference.
- `core.archive` and `core.lineage`
  - Provide candidate insertion, parent lookup, lineage traversal, and archive
    queries without reading raw JSON files directly.
- `core.parent_selection`
  - Implements built-in strategies and records selection rationale.
- `core.patch_manager`
  - Owns patch validation, policy checks, dry-run application, application,
    rejection capture, and persisted patch artifacts.
- `core.evaluator`
  - Runs staged/full/test phases through domain plugins and normalizes results.
- `sandbox`
  - Converts declarative policy into Docker execution settings, mounts, limits,
    environment, and audit records.
- `storage`
  - Stores normalized run records in SQLite and artifacts on disk.
- `observability`
  - Writes `events.jsonl`, structured logs, model call summaries, and dashboard
    snapshots.
- `cli`
  - Provides the user-facing contract:
    - `hyperagents init`
    - `hyperagents run --config experiment.yaml`
    - `hyperagents inspect runs/<run_id>`
    - `hyperagents dashboard`

## Proposed Plugin Interfaces

The stable public interfaces should be specified before implementation:

```python
class Domain:
    name: str
    def stage_eval(self, candidate) -> EvalResult: ...
    def full_eval(self, candidate) -> EvalResult: ...
    def test_eval(self, candidate) -> EvalResult: ...

class MetaAgent:
    def generate_patch(self, context: ImprovementContext) -> PatchResult: ...

class Archive:
    def add_candidate(self, candidate, evaluation, metadata) -> AgentId: ...
    def select_parent(self, strategy) -> AgentId: ...
    def lineage(self, agent_id) -> list[AgentId]: ...

class Sandbox:
    def run(self, command, mounts, limits, env) -> SandboxResult: ...
```

Additional interfaces:

- `PatchManager`
  - Validates patch format.
  - Applies include/exclude policies.
  - Supports dry-run and review modes.
  - Persists accepted/rejected patches.
  - Emits patch lifecycle events.
- `ParentSelector`
  - Provides deterministic selection from archive state.
  - Records scores, weights, child-count penalties, randomness seed, and final
    rationale.
- `ModelProvider`
  - Encapsulates provider name, model name, token limits, retries, cost
    estimates, and raw call metadata.
- `EventSink`
  - Appends schema-versioned JSONL events such as `candidate.created`,
    `patch.applied`, `eval.completed`, and `sandbox.failed`.

## Configuration Design

Experiments should be reproducible from one config file:

```yaml
experiment:
  name: paper_review_v1
  iterations: 100
  seed: 42
models:
  default:
    provider: openai
    model: gpt-5.5
sandbox:
  network: disabled
  timeout_seconds: 300
  memory_mb: 4096
  cpu_count: 2
archive:
  storage: sqlite
  path: runs/${experiment.name}/archive.sqlite
parent_selection:
  strategy: performance_weighted
  exploration_bonus: true
domains:
  - name: paper_review
    stage_eval_tasks: 10
    full_eval_tasks: 100
```

The config loader should validate:

- Required experiment name, iteration count, domains, model, archive, sandbox,
  and parent-selection fields.
- Domain names against the registry.
- Sandbox policy defaults before execution.
- Output paths under the run directory unless explicitly allowed.
- Seed handling for reproducible parent selection and deterministic fake tests.

## Safety Model

Generated code must be treated as untrusted.

Default safety requirements:

- Docker isolation is mandatory unless a domain explicitly declares a safer
  local mode for tests.
- Network is disabled by default and requires explicit config opt-in.
- Write mounts are allowlisted and minimal.
- Read mounts are allowlisted and should be read-only by default.
- Resource limits include timeout, memory, CPU, process count where available,
  and output-size limits.
- Secrets are not passed into generated-code environments by default.
- Secret-like environment variables are blocked and redacted in logs/events.
- Patch diffs are persisted and reviewable before application.
- Dry-run mode validates and stages a plan without mutating candidate state.
- Audit logs record commands, mounts, network mode, limits, env key names,
  exit status, and failure class.
- Blocked paths include host home directories, `.git` internals when not needed,
  run storage internals outside the candidate artifact area, and configured
  secret paths.
- Per-domain sandbox profiles can request extra capabilities such as GPU, but
  requests must be explicit and visible in config and audit logs.

The framework should fail closed: missing policy, unknown domain, rejected
patch, unsafe mount, or unapproved network access should stop the candidate and
record a typed failure.

## Storage And Observability Model

Run directory:

```text
runs/
  <run_id>/
    config.yaml
    archive.sqlite
    agents/
    patches/
    evaluations/
    logs/
    artifacts/
    events.jsonl
```

SQLite should track:

- Run ID, config hash, git base commit, seed, and status.
- Agent/candidate ID, parent ID, generation, state, and timestamps.
- Patch path, patch hash, apply status, rejection reason, and review status.
- Evaluation phase, domain, score, raw report path, and normalized metrics.
- Model calls, provider/model names, token estimates, cost estimates, and
  failure information.
- Sandbox command records, limits, network mode, mounts, exit code, timeout,
  and logs.
- Compile/import failures and evaluation failures.
- Parent-selection candidates, scores, weights, seed, and selected rationale.

`events.jsonl` should be append-only and schema-versioned:

```json
{"type":"candidate.created","agent_id":"...","parent_id":"..."}
{"type":"patch.applied","agent_id":"...","patch":"..."}
{"type":"eval.completed","agent_id":"...","score":0.42}
```

Large artifacts remain on the filesystem and are referenced from SQLite/events
by relative path and content hash.

## CLI Design

- `hyperagents init`
  - Creates a minimal project layout, example config, toy domain, and local run
    directory.
- `hyperagents run --config experiment.yaml`
  - Validates config.
  - Creates `runs/<run_id>/`.
  - Copies the resolved config to the run directory.
  - Executes the runner with structured events.
- `hyperagents inspect runs/<run_id>`
  - Prints run status, best candidates, failures, lineage, scores, and artifact
    paths.
- `hyperagents dashboard`
  - Starts a lightweight local inspection UI backed by SQLite and
    `events.jsonl`.

CLI commands should return non-zero exit codes for invalid config, unsafe
sandbox policy, failed run initialization, and internal errors. Candidate-level
failures should usually be recorded in the run and not crash the full run unless
policy/config declares them fatal.

## Testing Strategy

Tests should be added before refactoring behavior:

- Unit tests:
  - Archive insertion and lineage traversal.
  - Config loading, interpolation, and validation.
  - Patch manager dry-run, apply, rejection, and blocked-path behavior.
  - Parent selection strategies and recorded rationale.
  - Sandbox policy construction and denial behavior.
- Integration tests:
  - Fake domain.
  - Fake meta-agent.
  - One full local run with no expensive model calls.
  - Failed patch handling.
  - Failed evaluation handling.
- Security tests:
  - Blocked filesystem write.
  - Blocked network access.
  - Timeout enforcement.
  - Secret redaction.
- Toy domain:
  - Deterministic.
  - Fast.
  - No network.
  - No paid model calls.
  - Sufficient to exercise archive, patch, eval, events, and inspect flows.

## Spec-Driven Development Plan

All major implementation work should start from an accepted spec under
`specs/`:

- `specs/001-core-runner.md`
- `specs/002-archive-storage.md`
- `specs/003-domain-plugin-api.md`
- `specs/004-agent-plugin-api.md`
- `specs/005-sandbox-policy.md`
- `specs/006-config-schema.md`
- `specs/007-cli-contract.md`
- `specs/008-observability-events.md`
- `specs/009-test-strategy.md`

Each spec must describe the problem, current behavior, proposed behavior,
public API, data model, config fields, failure modes, security considerations,
acceptance criteria, and migration notes.

Implementation rule: do not start a major refactor until the relevant spec
exists and the first tests for that seam are planned.

## Phased Roadmap

### Phase 1: Codebase Map And Specs

- Fork the repo and create the planning branch.
- Document current architecture and data flow.
- Write framework plan and specs.
- Define target public interfaces.

### Phase 2: Extract Core Runner

- Split `generate_loop.py` into a runner and adapters.
- Preserve current behavior.
- Add tests around existing flow before changing behavior.
- Keep the old CLI as a compatibility entry point while new CLI is introduced.

### Phase 3: Add Config And Storage

- Add declarative experiment config.
- Create `runs/<run_id>/` directories.
- Add SQLite archive storage.
- Add `events.jsonl`.
- Migrate current `archive.jsonl` and `metadata.json` reads through storage
  adapters.

### Phase 4: Add Plugin APIs

- Define and implement the domain interface.
- Define and implement the meta-agent and task-agent interfaces.
- Define sandbox and parent-selector interfaces.
- Wrap existing domains and agents as compatibility plugins.

### Phase 5: Harden Sandboxing

- Default to no-network execution.
- Enforce mount allowlists and blocked paths.
- Add time, memory, CPU, and output limits.
- Add audit logs and failure classes.
- Require explicit per-domain capability requests.

### Phase 6: Improve Usability

- Add `hyperagents init`.
- Add `hyperagents run --config`.
- Add examples and templates.
- Add quickstart docs around the toy domain.
- Preserve current research commands as advanced compatibility paths.

### Phase 7: Add Inspection Tools

- Add archive graph and lineage explorer.
- Add patch viewer.
- Add score charts.
- Add run comparison.
- Build dashboard data from SQLite and events instead of implicit JSON layouts.

## Non-Goals For The First Pass

- Do not optimize benchmark performance.
- Do not add new research domains.
- Do not change the paper's experimental claims.
- Do not replace the model stack.
- Do not build a full web app.
- Do not make the agent fully autonomous.
- Do not allow unrestricted self-modification.

## Productization Considerations

The upstream repository is licensed under CC BY-NC-SA 4.0. Any future product
or redistribution plan must review license implications before treating this as
a commercial framework. This planning PR does not change license terms or make
commercial-use claims.
