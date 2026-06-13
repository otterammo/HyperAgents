# 008 Observability Events

## Problem

Current observability is spread across text logs, chat history files, JSON
reports, metadata files, and static plots. There is no structured event stream
for replay, inspection, dashboards, or debugging.

## Current behavior

- `utils/docker_utils.py` writes thread-local log files.
- Agent chat histories are written as markdown.
- Reports are JSON files under evaluation folders.
- Archive plots are generated from filesystem state.
- Metadata booleans capture some failure states.

## Proposed behavior

Add append-only `events.jsonl` with schema-versioned events. Events should be
written for run lifecycle, candidate lifecycle, patch lifecycle, sandbox runs,
model calls, evaluations, parent selection, and failures.

## Public API

```python
class EventSink:
    def emit(self, event: Event) -> None: ...
    def close(self) -> None: ...

class Event:
    type: str
    version: int
    run_id: str
    timestamp: str
    payload: dict
```

## Data model

Required event fields:

- `type`
- `version`
- `run_id`
- `timestamp`
- `payload`

Initial event types:

- `run.started`
- `run.completed`
- `candidate.created`
- `parent.selected`
- `patch.generated`
- `patch.applied`
- `patch.rejected`
- `sandbox.started`
- `sandbox.completed`
- `sandbox.failed`
- `eval.started`
- `eval.completed`
- `model.call.completed`
- `failure.recorded`

## Config fields

- `observability.events.enabled`
- `observability.events.path`
- `observability.logs.redact_secrets`
- `observability.dashboard.enabled`

## Failure modes

- Event sink cannot open file.
- Event write fails.
- Event payload is not JSON serializable.
- Redaction fails.

Event write failure should be fatal during run initialization and configurable
during later execution.

## Security considerations

Events must redact secrets and avoid raw prompts/responses by default unless
explicitly configured. Environment values should not be stored; only env key
names and redaction status should be recorded.

## Acceptance criteria

- A one-generation fake run writes valid JSONL events.
- Events include parent-selection rationale and patch status.
- Sandbox events include network mode, limits, mounts, and exit status.
- Secret-like values are redacted.

## Migration notes

Add event emission around existing function calls first. Later, use events as
the source for `inspect` and dashboard views.
