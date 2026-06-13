# 002 Archive Storage

## Problem

Archive state is split across `archive.jsonl`, per-generation `metadata.json`,
patch files, report files, and analysis outputs. There is no normalized store
for lineage, candidate state, evaluation scores, or parent-selection rationale.

## Current behavior

- `utils/gl_utils.py::update_and_save_archive` appends archive snapshots to
  `archive.jsonl`.
- `utils/gl_utils.py::load_archive_data` parses JSONL snapshots.
- `utils/gl_utils.py::get_parent_genid` reads parent IDs from
  `gen_<id>/metadata.json`.
- `utils/gl_utils.py::get_score` reads `report.json` from evaluation folders.
- Analysis scripts reconstruct lineage and scores from those files.

## Proposed behavior

Use SQLite as the authoritative archive store and keep large artifacts on disk.
The filesystem remains the artifact store, but all queryable run state is
normalized in `archive.sqlite`.

## Public API

```python
class Archive:
    def add_candidate(self, candidate, evaluation, metadata) -> AgentId: ...
    def get_candidate(self, agent_id) -> CandidateRecord: ...
    def select_parent(self, strategy) -> AgentId: ...
    def lineage(self, agent_id) -> list[AgentId]: ...
    def children(self, agent_id) -> list[AgentId]: ...
    def scores(self, agent_id) -> list[EvalScore]: ...
```

## Data model

Tables:

- `runs`: run ID, config hash, base commit, seed, status.
- `candidates`: candidate ID, parent ID, generation, state, timestamps.
- `patches`: patch ID, candidate ID, path, hash, status, rejection reason.
- `evaluations`: eval ID, candidate ID, domain, phase, status, score, report path.
- `artifacts`: artifact ID, candidate ID, type, path, hash.
- `parent_selections`: generation, selected parent, strategy, rationale JSON.
- `failures`: candidate ID, phase, class, message, artifact path.

## Config fields

- `archive.storage: sqlite`
- `archive.path`
- `archive.artifact_root`
- `archive.migrate_legacy_outputs`

## Failure modes

- SQLite database cannot be created.
- Schema migration fails.
- Candidate insert violates lineage constraints.
- Artifact path points outside the run directory.
- Legacy JSON data is malformed.

## Security considerations

Artifact paths stored in SQLite must be relative to the run directory unless an
explicit allowlist permits external paths. Events and database records must not
store raw secrets.

## Acceptance criteria

- A candidate can be inserted and queried by ID.
- Parent lineage returns ordered ancestors.
- Scores can be queried by candidate/domain/phase.
- Parent-selection rationale is persisted.
- A legacy `archive.jsonl` plus `metadata.json` run can be imported in read-only
  mode for inspection.

## Migration notes

Keep `archive.jsonl` writing during the compatibility phase if needed, but read
through an archive adapter. Once SQLite is authoritative, legacy files become
export artifacts rather than framework state.
