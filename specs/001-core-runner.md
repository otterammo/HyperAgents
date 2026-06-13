# 001 Core Runner

## Problem

The generation loop is concentrated in `generate_loop.py`, which combines CLI
parsing, run setup, Docker lifecycle, parent selection, patch generation,
evaluation, archive updates, and plotting. This makes it hard to test or reuse
the loop as a framework component.

## Current behavior

- `generate_loop.py::generate_loop` initializes or resumes an output directory.
- `generate_loop.py::generate` runs one generation inside a container.
- Archive state is updated by appending to `archive.jsonl`.
- Candidate status is stored in `gen_<id>/metadata.json`.
- Staged and full evaluation are executed inline.
- Plotting runs after each generation.

## Proposed behavior

Introduce a `Runner` that owns the lifecycle and delegates specialized work to
interfaces:

- `Archive` for state and lineage.
- `ParentSelector` for parent choice.
- `MetaAgent` for patch generation.
- `PatchManager` for patch validation/application.
- `Evaluator` for domain evaluation.
- `Sandbox` for command execution.
- `EventSink` for structured observability.

The runner should preserve the current algorithm first, then expose cleaner
configuration and test seams.

## Public API

```python
class Runner:
    def __init__(self, config, archive, sandbox, domains, meta_agent, events): ...
    def initialize_run(self) -> RunId: ...
    def run(self) -> RunResult: ...
    def run_generation(self, generation: int) -> CandidateResult: ...
```

`RunResult` includes run ID, best candidate, final archive size, status, and
failure summary.

## Data model

- `Run`: ID, config path/hash, status, started/finished timestamps.
- `Candidate`: ID, parent ID, generation, patch ID, state, worktree reference.
- `CandidateResult`: candidate ID, patch result, compile result, eval results,
  failure class, artifact paths.

## Config fields

- `experiment.name`
- `experiment.iterations`
- `experiment.seed`
- `domains`
- `models.default`
- `sandbox`
- `archive`
- `parent_selection`
- `runner.fail_fast`

## Failure modes

- Invalid config.
- No selectable parent.
- Meta-agent failure.
- Empty or invalid patch.
- Patch apply rejection.
- Compile/import failure.
- Sandbox timeout or resource failure.
- Domain evaluation failure.
- Storage write failure.

Each failure becomes a typed candidate state unless it prevents run
initialization.

## Security considerations

The runner must not execute generated code directly. All generated-code paths
must pass through `Sandbox` with a validated policy. Missing sandbox policy,
unknown capabilities, unsafe mounts, or unauthorized network access should fail
closed.

## Acceptance criteria

- A fake meta-agent and fake domain can run one deterministic generation.
- The current `generate_loop.py` behavior can be represented by runner calls.
- Candidate failures are stored without crashing the full run unless configured.
- Events are emitted for run start/end, candidate create, parent select, patch,
  compile, eval, and failure.

## Migration notes

Start with a compatibility runner that calls existing functions. Move logic out
of `generate_loop.py` only after tests cover current staged/full evaluation,
parent selection, and metadata behavior.
