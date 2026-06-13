# 003 Domain Plugin API

## Problem

Domains are currently plugged in through hardcoded metadata functions, dynamic
imports, and explicit branches. This prevents external domains from being added
without editing core files.

## Current behavior

- `utils/domain_utils.py` hardcodes score keys, splits, staged eval sizes,
  subsets, and ensemble support.
- `domains/harness.py` dynamically imports text-domain utils but explicitly
  branches for Balrog and Genesis.
- `domains/report.py` branches by domain family.
- Polyglot bypasses the shared harness with `domains/polyglot/harness.py`.

## Proposed behavior

Introduce a `Domain` interface and registry. Existing domains should be wrapped
as compatibility plugins before their internals are refactored.

## Public API

```python
class Domain:
    name: str
    def stage_eval(self, candidate) -> EvalResult: ...
    def full_eval(self, candidate) -> EvalResult: ...
    def test_eval(self, candidate) -> EvalResult: ...

class DomainRegistry:
    def register(self, domain: Domain) -> None: ...
    def get(self, name: str) -> Domain: ...
    def list(self) -> list[str]: ...
```

`EvalResult` includes phase, score, metrics, status, report path, artifact
paths, and failure class.

## Data model

- `DomainSpec`: name, plugin path, sandbox profile, eval phases, score key,
  staged/full sample counts.
- `EvalResult`: candidate ID, domain name, phase, score, metrics JSON, report
  artifact, status.

## Config fields

```yaml
domains:
  - name: paper_review
    stage_eval_tasks: 10
    full_eval_tasks: 100
    sandbox_profile: default
```

## Failure modes

- Unknown domain.
- Plugin import failure.
- Domain config validation failure.
- Missing dataset or benchmark dependency.
- Eval command timeout.
- Report cannot be parsed or normalized.

## Security considerations

Each domain must declare required sandbox capabilities. Network, GPU, write
mounts, and long timeouts require explicit config and audit events.

## Acceptance criteria

- Current text domains can be wrapped behind `Domain`.
- Balrog, Genesis, and Polyglot can expose adapter plugins without rewriting
  their evaluators.
- Adding a toy domain does not require editing `utils/domain_utils.py`.
- Eval results are normalized consistently across domain families.

## Migration notes

First build adapters that call `domains.harness`, `domains.report`, and
Polyglot helpers. Later, move domain-specific metadata from `utils/domain_utils`
into plugin declarations.
