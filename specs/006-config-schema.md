# 006 Config Schema

## Problem

Experiment configuration is currently split across CLI flags, hardcoded domain
metadata, setup scripts, output conventions, model constants, and Docker helper
defaults. Runs are not reproducible from a single file.

## Current behavior

- `generate_loop.py` parses many CLI flags.
- Domain defaults come from `utils/domain_utils.py`.
- Model defaults come from `agent/llm.py` and domain utils modules.
- Sandbox defaults come from `utils/docker_utils.py`.
- Initial data setup depends on `setup_initial.sh` and `outputs/initial_*`.

## Proposed behavior

Add a YAML experiment config with schema validation, defaults, interpolation,
and a resolved copy saved into each run directory.

## Public API

```python
def load_config(path: str) -> ExperimentConfig: ...
def resolve_config(config: ExperimentConfig) -> ResolvedConfig: ...
def validate_config(config: ResolvedConfig) -> list[ConfigError]: ...
```

## Data model

- `ExperimentConfig`: user-provided YAML.
- `ResolvedConfig`: defaults and interpolations applied.
- `ConfigError`: path, message, severity.

## Config fields

Required:

- `experiment.name`
- `experiment.iterations`
- `experiment.seed`
- `models.default.provider`
- `models.default.model`
- `sandbox`
- `archive`
- `parent_selection.strategy`
- `domains`

Optional:

- `runner.fail_fast`
- `agents.meta.plugin`
- `agents.task.plugin`
- `observability.level`
- `outputs.run_root`

## Failure modes

- Missing required field.
- Unknown domain.
- Unknown model provider.
- Invalid sandbox policy.
- Invalid path interpolation.
- Config references files outside allowed roots.

## Security considerations

Config validation must reject unsafe sandbox defaults, unauthorized network
access, unallowlisted write mounts, and secret-like values in plain config fields
where possible.

## Acceptance criteria

- The example config from the framework plan validates.
- The resolved config is copied to `runs/<run_id>/config.yaml`.
- Defaults are deterministic and visible.
- Unknown fields are either rejected or clearly warned according to schema
  policy.

## Migration notes

First map existing CLI flags to config fields and allow the old CLI to create a
resolved config internally. Later, make `hyperagents run --config` the primary
entry point.
