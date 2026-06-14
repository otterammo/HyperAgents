import os
import tempfile
import unittest

from hyperagents.config import (
    ConfigValidationError,
    resolve_config,
    resolved_config_to_legacy_kwargs,
)


class ConfigLoaderTests(unittest.TestCase):
    def test_resolve_config_applies_defaults_interpolation_and_overrides(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "experiment": {
                    "name": "paper_review_v1",
                    "iterations": 5,
                    "seed": 42,
                },
                "models": {
                    "default": {
                        "provider": "openai",
                        "model": "gpt-5.5",
                    }
                },
                "sandbox": {
                    "network": "disabled",
                    "timeout_seconds": 60,
                    "memory_mb": 1024,
                    "cpu_count": 1,
                },
                "archive": {
                    "path": "runs/${experiment.name}/archive.sqlite",
                },
                "parent_selection": {
                    "strategy": "score_prop",
                },
                "domains": [
                    {
                        "name": "paper_review",
                    }
                ],
            }

            resolved = resolve_config(
                config,
                config_path=os.path.join(temp_dir, "experiment.yaml"),
                overrides={"experiment.run_id": "run-123"},
                cwd=temp_dir,
            )

            self.assertEqual(resolved.values["experiment"]["run_id"], "run-123")
            self.assertEqual(resolved.sources["experiment.run_id"], "override")
            self.assertEqual(resolved.values["domains"][0]["eval_samples"], -1)
            self.assertIsNone(resolved.values["domains"][0]["eval_subset"])
            self.assertEqual(
                resolved.values["archive"]["path"],
                os.path.join(temp_dir, "runs", "paper_review_v1", "archive.sqlite"),
            )
            self.assertEqual(
                resolved.values["outputs"]["run_root"],
                os.path.join(temp_dir, "runs", "paper_review_v1"),
            )

    def test_resolve_config_rejects_unknown_fields(self):
        config = {
            "experiment": {
                "name": "paper_review_v1",
                "iterations": 5,
                "seed": 42,
                "unexpected": True,
            },
            "models": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-5.5",
                }
            },
            "sandbox": {
                "network": "disabled",
                "timeout_seconds": 60,
                "memory_mb": 1024,
                "cpu_count": 1,
            },
            "archive": {
                "path": "archive.sqlite",
            },
            "parent_selection": {
                "strategy": "score_prop",
            },
            "domains": ["paper_review"],
        }

        with self.assertRaises(ConfigValidationError) as ctx:
            resolve_config(config)

        self.assertIn("experiment.unexpected", str(ctx.exception))

    def test_resolve_config_rejects_unknown_override_targets(self):
        config = {
            "experiment": {
                "name": "paper_review_v1",
                "iterations": 5,
                "seed": 42,
            },
            "models": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-5.5",
                }
            },
            "sandbox": {
                "network": "disabled",
                "timeout_seconds": 60,
                "memory_mb": 1024,
                "cpu_count": 1,
            },
            "archive": {
                "path": "archive.sqlite",
            },
            "parent_selection": {
                "strategy": "score_prop",
            },
            "domains": ["paper_review"],
        }

        with self.assertRaises(ConfigValidationError) as ctx:
            resolve_config(config, overrides={"experiment.unknown": "x"})

        self.assertIn("Unknown CLI override target", str(ctx.exception))

    def test_resolve_config_rejects_interpolation_cycles(self):
        config = {
            "experiment": {
                "name": "paper_review_v1",
                "iterations": 5,
                "seed": 42,
            },
            "models": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-5.5",
                }
            },
            "sandbox": {
                "network": "disabled",
                "timeout_seconds": 60,
                "memory_mb": 1024,
                "cpu_count": 1,
            },
            "archive": {
                "path": "${outputs.run_root}",
            },
            "parent_selection": {
                "strategy": "score_prop",
            },
            "domains": ["paper_review"],
            "outputs": {
                "run_root": "${archive.path}",
            },
        }

        with self.assertRaises(ConfigValidationError) as ctx:
            resolve_config(config)

        self.assertIn("Interpolation cycle detected", str(ctx.exception))

    def test_resolved_config_to_legacy_kwargs_maps_legacy_fields(self):
        config = {
            "experiment": {
                "name": "paper_review_v1",
                "iterations": 3,
                "seed": 42,
                "run_id": "run-123",
            },
            "models": {
                "default": {
                    "provider": "openai",
                    "model": "gpt-5.5",
                }
            },
            "sandbox": {
                "network": "disabled",
                "timeout_seconds": 60,
                "memory_mb": 1024,
                "cpu_count": 1,
            },
            "archive": {
                "path": "archive.sqlite",
            },
            "parent_selection": {
                "strategy": "latest",
            },
            "domains": [
                {
                    "name": "paper_review",
                    "eval_subset": "_filtered_100_train",
                    "eval_samples": 7,
                },
                "imo_grading",
            ],
        }

        resolved = resolve_config(config)
        kwargs = resolved_config_to_legacy_kwargs(resolved)

        self.assertEqual(kwargs["domains"], ["paper_review", "imo_grading"])
        self.assertEqual(kwargs["eval_subsets"][0], "_filtered_100_train")
        self.assertEqual(kwargs["eval_samples"], [7, -1])
        self.assertEqual(kwargs["parent_selection"], "latest")
        self.assertEqual(kwargs["max_generation"], 3)
        self.assertEqual(kwargs["run_id"], "run-123")


if __name__ == "__main__":
    unittest.main()
