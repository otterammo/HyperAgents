# 009 Test Strategy

## Problem

The repository has no visible first-class test suite or package metadata. The
current code is difficult to test because core behavior depends on Docker,
external models, benchmark datasets, and filesystem conventions.

## Current behavior

- No `tests/` directory is present.
- No `pyproject.toml` or test runner configuration is present.
- Behavior is exercised through scripts and benchmark runs.
- Many useful seams are hidden inside `generate_loop.py`.

## Proposed behavior

Add tests before refactoring behavior. Use a deterministic toy domain and fake
agents to cover the framework without paid model calls or heavy Docker
benchmarks.

## Public API

Test-facing helpers:

```python
class FakeDomain(Domain): ...
class FakeMetaAgent(MetaAgent): ...
class InMemorySandbox(Sandbox): ...
class TempRunStore: ...
```

These helpers should exercise the same public interfaces used by production
code.

## Data model

Test fixtures should create:

- Temporary run directories.
- Minimal configs.
- Fake candidates.
- Small patches.
- Deterministic eval reports.
- Captured events.

## Config fields

Test configs should cover:

- Toy domain.
- No-network sandbox.
- SQLite archive under a temp directory.
- Deterministic seed.
- Fake model provider.

## Failure modes

Tests must cover:

- Invalid config.
- Failed patch application.
- Failed compile/import check.
- Failed staged evaluation.
- Sandbox timeout.
- Blocked filesystem write.
- Blocked network access.
- Secret redaction.

## Security considerations

Security tests should verify fail-closed behavior. The toy domain must not need
network access or real secrets. Tests should avoid writing outside temporary
directories.

## Acceptance criteria

Required test groups:

- `unit/archive`
- `unit/lineage`
- `unit/config_loader`
- `unit/patch_manager`
- `unit/parent_selection`
- `unit/sandbox_policy`
- `integration/fake_domain`
- `integration/fake_meta_agent`
- `integration/one_full_local_run`
- `integration/failed_patch_handling`
- `integration/failed_evaluation_handling`
- `security/blocked_filesystem_write`
- `security/blocked_network_access`
- `security/timeout_enforcement`
- `security/secret_redaction`

## Migration notes

Start with tests around adapters that preserve current behavior. Add the toy
domain early so future extraction work can run in CI without Docker-heavy
benchmarks or model calls.
