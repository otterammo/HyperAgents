# 005 Sandbox Policy

## Problem

Generated code is untrusted, but the current Docker defaults use host
networking, read/write repo mounts, and environment inheritance paths that are
too permissive for a reusable framework.

## Current behavior

- `utils/docker_utils.py::build_container` builds with host networking.
- Runtime containers use `network_mode="host"`.
- The repository is mounted read/write.
- GPU access is conditionally requested for Genesis-like domains.
- Polyglot has separate Docker helpers and per-instance containers.

## Proposed behavior

Introduce a declarative `SandboxPolicy` and a `Sandbox` interface. Docker should
be the default backend. The default policy is no network, minimal mounts,
resource limits, and secret redaction.

## Public API

```python
class Sandbox:
    def run(self, command, mounts, limits, env) -> SandboxResult: ...

class SandboxPolicy:
    network: str
    mounts: list[MountPolicy]
    limits: ResourceLimits
    blocked_paths: list[str]
    blocked_env: list[str]
```

## Data model

- `SandboxRun`: command, working directory, image, network mode, mounts, limits,
  env keys, status, exit code, duration.
- `SandboxResult`: stdout path, stderr path, exit code, timed out, failure class.
- `MountPolicy`: source, target, mode, purpose.
- `ResourceLimits`: timeout seconds, memory MB, CPU count, process limit,
  output limit.

## Config fields

```yaml
sandbox:
  backend: docker
  network: disabled
  timeout_seconds: 300
  memory_mb: 4096
  cpu_count: 2
  blocked_env:
    - OPENAI_API_KEY
    - ANTHROPIC_API_KEY
```

## Failure modes

- Docker unavailable.
- Image build failure.
- Unsafe policy requested.
- Mount path denied.
- Network requested without opt-in.
- Timeout.
- Memory/process/output limit exceeded.
- Container cleanup failure.

## Security considerations

The framework must fail closed on missing or invalid policy. Secrets should be
blocked by default. Network requires explicit opt-in. Write mounts must be
minimal and scoped to candidate artifacts. Audit logs must capture policy and
execution details.

## Acceptance criteria

- Default sandbox runs with network disabled.
- A blocked host path cannot be mounted.
- A secret env var is redacted from logs/events.
- Timeout enforcement produces a typed failure.
- Domain-specific capability requests are visible in config and audit events.

## Migration notes

Wrap `utils/docker_utils.py` first, then replace direct `container.exec_run`
calls with `Sandbox.run`. Polyglot can keep its specialized container build
logic behind the same policy object during migration.
