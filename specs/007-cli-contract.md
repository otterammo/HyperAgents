# 007 CLI Contract

## Problem

The current user interface is `python generate_loop.py` plus separate setup,
eval, report, and analysis scripts. A framework needs stable commands for
initialization, running, inspection, and dashboard use.

## Current behavior

- `python generate_loop.py --domains ...` is the primary run command.
- `setup_initial.sh` prepares initial evals manually.
- `domains.harness`, `domains.report`, `domains.run_eval`, and analysis scripts
  are invoked separately.
- Output paths are mostly under `outputs/`.

## Proposed behavior

Add a `hyperagents` CLI with explicit subcommands:

- `hyperagents init`
- `hyperagents run --config experiment.yaml`
- `hyperagents inspect runs/<run_id>`
- `hyperagents dashboard`

## Public API

Command contract:

```text
hyperagents init [--template toy|paper_review] [--output DIR]
hyperagents run --config experiment.yaml [--run-id ID] [--dry-run]
hyperagents inspect runs/<run_id> [--json] [--candidate ID]
hyperagents dashboard [--run runs/<run_id>] [--host HOST] [--port PORT]
```

## Data model

CLI commands read and write:

- Resolved config.
- Run directory.
- SQLite archive.
- Events JSONL.
- Artifacts.

## Config fields

The CLI should not define hidden behavior outside config except direct command
flags such as `--dry-run`, `--json`, host, and port.

## Failure modes

- Config missing or invalid.
- Run directory exists and cannot be resumed.
- Archive cannot be opened.
- Dashboard port unavailable.
- Unknown candidate.

## Security considerations

`run` must validate sandbox policy before execution. `inspect` and `dashboard`
must not render raw secret values from logs/events. `init` should create safe
defaults with no network.

## Acceptance criteria

- `hyperagents init` creates an example config and toy domain scaffold.
- `hyperagents run --config` creates a run directory and starts a run.
- `hyperagents inspect` prints run status, best candidate, failures, and
  artifact paths.
- Commands return documented non-zero exit codes for invalid config and runtime
  initialization failures.

## Migration notes

Keep `generate_loop.py` working during migration. The new CLI can call
compatibility adapters until core modules are extracted.
