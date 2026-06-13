# HyperAgents Repository Map

This map describes the current research implementation at upstream commit
`59a68f672dfb92c74aeb7e61535d776fb36e172d`. It is intended to ground the
framework planning work in the code that exists today.

## High-Level Shape

HyperAgents is currently organized as a research prototype around one primary
evolution loop:

1. Prepare a copied repository and seed evaluation outputs.
2. Select an archive parent.
3. Run a meta-agent inside a Docker container.
4. Save the generated git diff as a patch.
5. Apply the parent lineage patches to a fresh container.
6. Check imports for generated agents.
7. Run staged and full evaluations.
8. Save per-generation metadata and update the archive.
9. Plot score progress and archive lineage.

The codebase has valuable primitives for self-modifying agents, archive-based
evolution, parent/child lineage, patch generation, benchmark adapters, and
Docker execution. These primitives are currently coupled through scripts and
filesystem conventions rather than explicit framework interfaces.

## Entry Points

- `generate_loop.py`
  - `generate_loop.py:719` defines `generate_loop`, the top-level orchestration
    function.
  - `generate_loop.py:1025` defines the CLI parser for `python generate_loop.py`.
  - The parser handles domain names, generation count, eval samples/workers,
    parent selection, resume paths, baseline modes, initial patches, and
    staged/test evaluation options.
- `run_meta_agent.py`
  - `run_meta_agent.py:9` defines the helper CLI that runs the meta-agent and
    writes `model_patch.diff`.
- `run_task_agent.py`
  - `run_task_agent.py:8` defines a Polyglot-specific repair-agent entry point.
- `domains/harness.py`
  - `domains/harness.py:60` defines the general evaluation harness for text
    domains plus explicit Balrog and Genesis branches.
- `domains/report.py`
  - `domains/report.py:14` defines the generic report path for text domains.
- `domains/polyglot/harness.py`
  - `domains/polyglot/harness.py:236` defines a separate Polyglot evaluation
    harness with per-instance Docker execution.
- `analysis/plot_progress.py` and `analysis/visualize_archive.py`
  - These scripts consume archive and metadata files to generate plots.

## Execution Flow

`generate_loop.py` is the center of the current system.

- Initialization happens in `generate_loop.py:719`.
  - Creates or resumes an output directory under `outputs/generate_<run_id>/`.
  - Calls `utils/gl_utils.py:211` `setup_initial_gen` to copy initial evals and
    create a working repository under `gen_initial/HyperAgents`.
  - Creates initial archive entries in `archive.jsonl`.
- Per-generation execution happens in `generate_loop.py:427` `generate`.
  - Creates `gen_<id>/`.
  - Builds and starts a Docker container through `utils/docker_utils.py:102`.
  - Applies meta patches and parent lineage patches.
  - Runs the meta-agent unless the generation is an initial/eval-only path.
  - Copies `agent_output/` and `model_patch.diff` back to the host.
  - Checks imports for `MetaAgent`, `TaskAgent`, and optionally
    `select_next_parent`.
  - Runs staged and full domain evaluations.
  - Writes `gen_<id>/metadata.json`.
- Parent selection happens through either:
  - `utils/gl_utils.py:511` `select_parent`, for built-in strategies.
  - `generate_loop.py:99` `select_next_parent_container`, when generated code is
    allowed to edit the selection mechanism.
- Archive updates happen in `utils/gl_utils.py:160` `update_and_save_archive`.
- Static analysis artifacts are generated after each generation by
  `analysis/plot_progress.py:168`, `analysis/plot_progress.py:186`,
  `analysis/visualize_archive.py:230`, and
  `analysis/visualize_archive.py:239`.

## Agent Generation

- `meta_agent.py:6` defines `MetaAgent`, which inherits from
  `agent/base_agent.py::AgentSystem`.
  - `MetaAgent.forward` prompts the model with "Modify any part of the codebase"
    and enables all local tools.
- `run_meta_agent.py:9` runs `MetaAgent.forward`.
  - It then calls `utils/git_utils.py::reset_paths_to_commit` for `domains/`.
  - It saves the diff from `utils/git_utils.py::diff_versus_commit` to
    `model_patch.diff`.
- `agent/llm.py:36` defines `get_response_from_llm`.
  - Uses LiteLLM.
  - Loads `.env`.
  - Defines concrete model constants in code.
  - Handles model-specific token and temperature differences inline.
- `agent/llm_withtools.py:91` defines `chat_with_agent`.
  - Loads tool modules dynamically from `agent/tools/`.
  - Asks the model to emit JSON with `tool_name` and `tool_input`.
  - Runs one tool call per model response by default.
- `agent/tools/bash.py:27` defines a persistent bash session.
  - It inherits the process environment.
  - It has a fixed 120 second timeout.
- `agent/tools/edit.py:113` defines the file editing tool.
  - It supports view, create, replace, insert, and undo.
  - It validates absolute paths but does not enforce a framework-level write
    allowlist.

## Task Execution

- `task_agent.py:5` defines `TaskAgent`.
  - `TaskAgent.forward` receives a domain input dictionary.
  - It asks the model to return JSON with a `response`.
  - It extracts the last JSON response using `utils/common.py::extract_jsons`.
- `domains/harness.py:26` `run_agent` instantiates `TaskAgent` for each row and
  writes per-question chat history.
- `domains/harness.py:35` `load_task_agent` loads a `TaskAgent` class either
  from a file path or module path.
- `run_task_agent.py:8` is not a general framework entry point.
  - It is used by Polyglot to solve coding repair tasks and write a diff.

## Patch And Lineage Flow

- `utils/gl_utils.py:120` `get_patch_files` reads parent and current patch paths
  from `metadata.json`.
- `utils/gl_utils.py:110` `get_parent_genid` reads a node's parent from
  `metadata.json`.
- `utils/gl_utils.py:134` `update_node_metadata` mutates `metadata.json` in
  place.
- `utils/gl_utils.py:438` `apply_diffs_container`:
  - Reads patch files from the host.
  - Filters changes with `filter_patch_by_files`.
  - Copies a temporary patch file into the container.
  - Runs `patch -p1 < parent_patch.txt`.
  - Stages all changes with `git add --all`.
  - Commits the result with a placeholder commit message.
- `utils/gl_utils.py:608` `run_commands_to_check_compilation` only checks Python
  imports for generated modules.
- `select_next_parent.py` is itself editable when `--edit_select_parent` is set,
  and `generate_loop.py:99` runs it in a container.

## Archive And Metadata

The archive is spread across several filesystem conventions:

- `archive.jsonl`
  - Written by `utils/gl_utils.py:160`.
  - Each line records `current_genid` and a full archive list snapshot.
- `gen_<id>/metadata.json`
  - Written by `generate_loop.py:427` `generate`.
  - Stores fields such as `parent_genid`, `prev_patch_files`,
    `curr_patch_files`, `parent_agent_success`, `run_eval`, `run_full_eval`,
    `valid_parent`, and `can_select_next_parent`.
- `gen_<id>/<domain>_eval*/report.json`
  - Written by `domains/report.py` or domain-specific report functions.
  - Read through `utils/gl_utils.py:65` `get_score` and
    `utils/gl_utils.py:32` `get_saved_score`.
- Ensemble reports use `gen_<id>/report_ensemble_<domain>_<split>.json`.

Lineage is reconstructed by joining `archive.jsonl` snapshots with
`metadata.json` parent IDs. There is no single authoritative lineage table.

## Evaluation

Evaluation paths differ by domain family:

- Text-like domains: `search_arena`, `paper_review`, `imo_grading`,
  `imo_proof`.
  - `domains/harness.py:18` loads datasets.
  - `domains/harness.py:60` imports `domains.<domain>.utils`.
  - Each utils module supplies `QUESTION_ID`, `GROUND_TRUTH_KEY`, `MODEL`, and
    `format_input_dict`.
  - `domains/report.py:14` writes accuracy-oriented reports.
- Balrog domains:
  - `domains/harness.py` branches explicitly on `"balrog"`.
  - `domains/balrog/eval.py` uses Hydra config and an `EvaluatorManager`.
- Genesis domains:
  - `domains/harness.py` branches explicitly on `"genesis"`.
  - `domains/genesis/eval.py` uses Hydra config, GPU-oriented dependencies, and
    an `EvaluatorManager`.
- Polyglot:
  - `generate_loop.py:49` `run_harness_polyglot` bypasses the shared harness.
  - `domains/polyglot/harness.py:33` processes each benchmark instance in its
    own Docker container.
  - `domains/polyglot/harness.py:236` builds environment images and aggregates
    resolved/unresolved/error results.

## Sandbox And Docker Behavior

- `utils/docker_utils.py:102` `build_container` is the main sandbox constructor.
  - Builds the image with `network_mode="host"`.
  - Runs containers with `network_mode="host"`.
  - Mounts the repository read/write at `/<REPO_NAME>`.
  - Enables GPU device requests for Genesis-like domains when available.
  - Passes proxy build args for internal network environments.
- `generate_loop.py:427` and helpers run commands inside that container using
  shell timeouts such as 5 minutes, 3 hours, 5 hours, or 6 hours.
- `utils/docker_utils.py:369` and `utils/docker_utils.py:441` copy files in and
  out using tar archives.
- Polyglot duplicates sandbox lifecycle and copy helpers under
  `domains/polyglot/`.

Generated code is isolated from the host by Docker, but defaults are not yet
framework-safe: host networking is enabled, the repo mount is read/write, and
secrets can be inherited or explicitly passed.

## Domain Plugging Today

Domain behavior is not centralized behind a plugin interface.

- Domain score keys, splits, staged-eval sizes, test subsets, and ensemble
  support are hardcoded in `utils/domain_utils.py`.
- Text domains are convention-based modules under `domains/<name>/utils.py`.
- Balrog and Genesis are explicit branches in `domains/harness.py` and
  `domains/report.py`.
- Polyglot has separate orchestration, Docker, report, and patch filtering.
- CLI domain choices are duplicated in `generate_loop.py`, `domains/harness.py`,
  and `domains/report.py`.

## Analysis And Inspectability

- `analysis/plot_progress.py` reads archive snapshots, scores, metadata, and
  lineage to write PNG plots and text summaries.
- `analysis/visualize_archive.py` builds NetworkX graphs from archive and
  metadata files.
- These scripts are useful inspection primitives, but they rely on implicit file
  layouts and cannot currently query a normalized run database or event stream.

## Summary Of Current Seams

The most important extraction seams for a framework are:

- `generate_loop.py:719` -> core runner.
- `generate_loop.py:427` -> candidate generation lifecycle.
- `utils/gl_utils.py:438` -> patch manager.
- `utils/gl_utils.py:160`, `:179`, `:511` -> archive, storage, and parent
  selection.
- `utils/docker_utils.py:102` -> sandbox runner and policy.
- `domains/harness.py`, `domains/report.py`, and `domains/polyglot/*` -> domain
  plugin compatibility adapters.
- `agent/llm.py`, `agent/llm_withtools.py`, and `agent/tools/*` -> model
  provider, agent plugin, and tool policy interfaces.
- `analysis/*` -> future inspect/dashboard data consumers.
