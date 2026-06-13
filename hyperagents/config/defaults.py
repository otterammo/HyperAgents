"""Default configuration values for the framework compatibility layer."""

DEFAULT_CONFIG = {
    "experiment": {
        "run_id": None,
        "seed": 0,
    },
    "runner": {
        "fail_fast": True,
        "fail_on_eval_failure": True,
    },
    "agents": {
        "meta": {
            "plugin": "legacy-meta-agent",
        },
        "task": {
            "plugin": "legacy-task-agent",
        },
    },
    "models": {
        "default": {
            "temperature": 0,
            "max_completion_tokens": None,
        }
    },
    "sandbox": {
        "network": "disabled",
        "timeout_seconds": 300,
        "memory_mb": 4096,
        "cpu_count": 2,
    },
    "archive": {
        "storage": "sqlite",
        "artifact_root": "artifacts",
    },
    "parent_selection": {
        "exploration_bonus": False,
    },
    "observability": {
        "level": "info",
        "events": {
            "path": "events.jsonl",
        },
    },
    "outputs": {
        "run_root": "runs/${experiment.name}",
    },
    "legacy": {
        "output_dir_parent": None,
        "eval_workers": 10,
        "resume_from": None,
        "meta_patch_files": [],
        "reset_task_agent": False,
        "reset_meta_agent": False,
        "copy_root_dir": None,
        "run_baseline": None,
        "optimize_option": "only_agent",
        "agent_archive_path": None,
        "eval_test": False,
        "skip_staged_eval": False,
        "edit_select_parent": False,
    },
}
