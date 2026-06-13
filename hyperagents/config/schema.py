"""Schema and validation helpers for configuration loading."""

from __future__ import annotations

from typing import Any

ALLOWED_MODEL_PROVIDERS = {
    "anthropic",
    "azure",
    "google",
    "ollama",
    "openai",
    "openrouter",
}

ALLOWED_DOMAINS = {
    "search_arena",
    "paper_review",
    "balrog_babyai",
    "balrog_babaisai",
    "balrog_minihack",
    "balrog_nle",
    "genesis_go2walking",
    "genesis_go2walkback",
    "genesis_go2hop",
    "polyglot",
    "imo_grading",
    "imo_proof",
}

SCHEMA: dict[str, Any] = {
    "experiment": {
        "name": str,
        "iterations": int,
        "seed": int,
        "run_id": (str, type(None)),
    },
    "runner": {
        "fail_fast": bool,
        "fail_on_eval_failure": bool,
    },
    "agents": {
        "meta": {
            "plugin": str,
        },
        "task": {
            "plugin": str,
        },
    },
    "models": {
        "default": {
            "provider": str,
            "model": str,
            "temperature": (int, float),
            "max_completion_tokens": (int, type(None)),
        }
    },
    "sandbox": {
        "network": str,
        "timeout_seconds": int,
        "memory_mb": int,
        "cpu_count": int,
    },
    "archive": {
        "storage": str,
        "path": str,
        "artifact_root": str,
    },
    "parent_selection": {
        "strategy": str,
        "exploration_bonus": bool,
    },
    "domains": [
        {
            "name": str,
            "eval_subset": (str, type(None)),
            "eval_samples": int,
        }
    ],
    "observability": {
        "level": str,
        "events": {
            "path": str,
        },
    },
    "outputs": {
        "run_root": str,
    },
    "legacy": {
        "output_dir_parent": (str, type(None)),
        "eval_workers": int,
        "resume_from": (str, type(None)),
        "meta_patch_files": [str],
        "reset_task_agent": bool,
        "reset_meta_agent": bool,
        "copy_root_dir": (str, type(None)),
        "run_baseline": (str, type(None)),
        "optimize_option": str,
        "agent_archive_path": (str, type(None)),
        "eval_test": bool,
        "skip_staged_eval": bool,
        "edit_select_parent": bool,
    },
}

REQUIRED_FIELDS = [
    "experiment.name",
    "experiment.iterations",
    "experiment.seed",
    "models.default.provider",
    "models.default.model",
    "sandbox",
    "archive",
    "parent_selection.strategy",
    "domains",
]

PATH_FIELDS = {
    "archive.path",
    "archive.artifact_root",
    "outputs.run_root",
    "observability.events.path",
    "legacy.output_dir_parent",
    "legacy.resume_from",
    "legacy.copy_root_dir",
    "legacy.agent_archive_path",
}

PATH_LIST_FIELDS = {
    "legacy.meta_patch_files",
}

DOMAIN_ALLOWED_KEYS = {"name", "eval_subset", "eval_samples"}
