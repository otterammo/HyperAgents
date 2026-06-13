"""YAML config loading, resolution, and validation."""

from __future__ import annotations

import copy
import os
import re
from dataclasses import dataclass, field
from typing import Any

from .defaults import DEFAULT_CONFIG
from .schema import (
    ALLOWED_DOMAINS,
    ALLOWED_MODEL_PROVIDERS,
    DOMAIN_ALLOWED_KEYS,
    PATH_FIELDS,
    PATH_LIST_FIELDS,
    REQUIRED_FIELDS,
    SCHEMA,
)
from utils.domain_utils import get_domain_eval_subset

PLACEHOLDER_PATTERN = re.compile(r"\$\{([^}]+)\}")


@dataclass
class ConfigError:
    path: str
    message: str
    severity: str = "error"


class ConfigValidationError(ValueError):
    def __init__(self, errors: list[ConfigError]):
        self.errors = errors
        message = "; ".join(f"{error.path}: {error.message}" for error in errors)
        super().__init__(message)


@dataclass
class ResolvedConfig:
    raw: dict[str, Any]
    values: dict[str, Any]
    sources: dict[str, str] = field(default_factory=dict)
    config_path: str | None = None


def _load_yaml_module():
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyYAML is required for --config support. Install dependencies from requirements.txt."
        ) from exc
    return yaml


def load_config(
    path: str,
    overrides: dict[str, Any] | None = None,
    cwd: str | None = None,
) -> ResolvedConfig:
    yaml = _load_yaml_module()
    config_path = os.path.abspath(path)
    with open(config_path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ConfigValidationError(
            [ConfigError(path="<root>", message="Config file must contain a mapping")]
        )
    return resolve_config(raw, config_path=config_path, overrides=overrides, cwd=cwd)


def resolve_config(
    config: dict[str, Any],
    *,
    config_path: str | None = None,
    overrides: dict[str, Any] | None = None,
    cwd: str | None = None,
) -> ResolvedConfig:
    merged = copy.deepcopy(DEFAULT_CONFIG)
    sources = _seed_sources(DEFAULT_CONFIG)
    _merge_with_sources(merged, config, sources, source="config", path_prefix="")
    _normalize_domain_entries(merged)

    errors = validate_config(merged)
    if errors:
        raise ConfigValidationError(errors)

    resolved = _resolve_placeholders(
        merged,
        root=merged,
        cwd=os.path.abspath(cwd or os.getcwd()),
    )

    override_errors = _apply_overrides(resolved, overrides or {}, sources)
    if override_errors:
        raise ConfigValidationError(override_errors)

    _normalize_paths(resolved, config_path=config_path)

    errors = validate_config(resolved)
    if errors:
        raise ConfigValidationError(errors)

    return ResolvedConfig(
        raw=copy.deepcopy(config),
        values=resolved,
        sources=sources,
        config_path=config_path,
    )


def validate_config(config: dict[str, Any]) -> list[ConfigError]:
    errors: list[ConfigError] = []
    _validate_schema(config, SCHEMA, errors, "")
    for required_field in REQUIRED_FIELDS:
        if _get_value(config, required_field) is None:
            errors.append(
                ConfigError(
                    path=required_field,
                    message="Missing required field",
                )
            )

    domains = config.get("domains")
    if not isinstance(domains, list) or not domains:
        errors.append(ConfigError(path="domains", message="At least one domain is required"))
    else:
        for index, domain in enumerate(domains):
            path = f"domains.{index}"
            if not isinstance(domain, dict):
                errors.append(ConfigError(path=path, message="Domain entries must be strings or mappings"))
                continue
            if domain.get("name") not in ALLOWED_DOMAINS:
                errors.append(
                    ConfigError(path=f"{path}.name", message=f"Unknown domain '{domain.get('name')}'")
                )
            unknown = sorted(set(domain.keys()) - DOMAIN_ALLOWED_KEYS)
            for key in unknown:
                errors.append(
                    ConfigError(path=f"{path}.{key}", message="Unknown field")
                )

    provider = _get_value(config, "models.default.provider")
    if provider is not None and provider not in ALLOWED_MODEL_PROVIDERS:
        errors.append(
            ConfigError(
                path="models.default.provider",
                message=f"Unknown model provider '{provider}'",
            )
        )

    network = _get_value(config, "sandbox.network")
    if network not in {"disabled", "enabled"}:
        errors.append(
            ConfigError(
                path="sandbox.network",
                message="Sandbox network must be 'disabled' or 'enabled'",
            )
        )

    return errors


def save_resolved_config(output_path: str, resolved_config: ResolvedConfig) -> None:
    yaml = _load_yaml_module()
    payload = {
        "values": resolved_config.values,
        "sources": resolved_config.sources,
        "config_path": resolved_config.config_path,
    }
    with open(output_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def resolved_config_to_legacy_kwargs(resolved_config: ResolvedConfig) -> dict[str, Any]:
    values = resolved_config.values
    domain_entries = values["domains"]

    domains = []
    eval_subsets = []
    eval_samples = []
    for entry in domain_entries:
        domains.append(entry["name"])
        eval_subsets.append(entry.get("eval_subset") or get_domain_eval_subset(entry["name"]))
        eval_samples.append(entry.get("eval_samples", -1))

    legacy = values["legacy"]
    return {
        "domains": domains,
        "run_id": values["experiment"].get("run_id"),
        "max_generation": values["experiment"]["iterations"],
        "eval_samples": eval_samples,
        "eval_workers": legacy["eval_workers"],
        "eval_subsets": eval_subsets,
        "parent_selection": values["parent_selection"]["strategy"],
        "resume_from": legacy["resume_from"],
        "output_dir_parent": legacy["output_dir_parent"],
        "meta_patch_files": legacy["meta_patch_files"],
        "reset_task_agent": legacy["reset_task_agent"],
        "reset_meta_agent": legacy["reset_meta_agent"],
        "copy_root_dir": legacy["copy_root_dir"],
        "run_baseline": legacy["run_baseline"],
        "optimize_option": legacy["optimize_option"],
        "agent_archive_path": legacy["agent_archive_path"],
        "eval_test": legacy["eval_test"],
        "skip_staged_eval": legacy["skip_staged_eval"],
        "edit_select_parent": legacy["edit_select_parent"],
    }


def _seed_sources(config: dict[str, Any], path_prefix: str = "") -> dict[str, str]:
    sources: dict[str, str] = {}
    for key, value in config.items():
        dotted_path = f"{path_prefix}.{key}" if path_prefix else key
        if isinstance(value, dict):
            sources.update(_seed_sources(value, dotted_path))
        else:
            sources[dotted_path] = "default"
    return sources


def _merge_with_sources(
    target: dict[str, Any],
    updates: dict[str, Any],
    sources: dict[str, str],
    *,
    source: str,
    path_prefix: str,
) -> None:
    for key, value in updates.items():
        dotted_path = f"{path_prefix}.{key}" if path_prefix else key
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_with_sources(
                target[key],
                value,
                sources,
                source=source,
                path_prefix=dotted_path,
            )
            continue
        target[key] = copy.deepcopy(value)
        _mark_source(dotted_path, value, sources, source)


def _mark_source(
    dotted_path: str,
    value: Any,
    sources: dict[str, str],
    source: str,
) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _mark_source(f"{dotted_path}.{key}", nested, sources, source)
        return
    sources[dotted_path] = source


def _validate_schema(
    value: Any,
    schema: Any,
    errors: list[ConfigError],
    path: str,
) -> None:
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            errors.append(
                ConfigError(path=path or "<root>", message="Expected mapping")
            )
            return
        allowed_keys = set(schema.keys())
        for key in value.keys():
            if key not in allowed_keys:
                errors.append(
                    ConfigError(
                        path=f"{path}.{key}" if path else key,
                        message="Unknown field",
                    )
                )
        for key, nested_schema in schema.items():
            if key in value:
                nested_path = f"{path}.{key}" if path else key
                _validate_schema(value[key], nested_schema, errors, nested_path)
        return

    if isinstance(schema, list):
        if not isinstance(value, list):
            errors.append(
                ConfigError(path=path, message="Expected list")
            )
            return
        item_schema = schema[0]
        for index, item in enumerate(value):
            _validate_schema(item, item_schema, errors, f"{path}.{index}")
        return

    if isinstance(schema, tuple):
        if not isinstance(value, schema):
            errors.append(
                ConfigError(path=path, message=f"Expected {schema}")
            )
        return

    if not isinstance(value, schema):
        errors.append(
            ConfigError(path=path, message=f"Expected {schema.__name__}")
        )


def _normalize_domain_entries(config: dict[str, Any]) -> None:
    domains = config.get("domains")
    if not isinstance(domains, list):
        return

    normalized = []
    for entry in domains:
        if isinstance(entry, str):
            normalized.append(
                {
                    "name": entry,
                    "eval_subset": None,
                    "eval_samples": -1,
                }
            )
            continue
        if isinstance(entry, dict):
            item = copy.deepcopy(entry)
            item.setdefault("eval_subset", None)
            item.setdefault("eval_samples", -1)
            normalized.append(item)
            continue
        normalized.append(entry)
    config["domains"] = normalized


def _resolve_placeholders(root_value: Any, *, root: dict[str, Any], cwd: str) -> Any:
    def resolve(value: Any, path: str, stack: tuple[str, ...]) -> Any:
        if isinstance(value, dict):
            return {
                key: resolve(
                    nested,
                    f"{path}.{key}" if path else key,
                    stack,
                )
                for key, nested in value.items()
            }
        if isinstance(value, list):
            return [
                resolve(item, f"{path}.{index}" if path else str(index), stack)
                for index, item in enumerate(value)
            ]
        if not isinstance(value, str):
            return value

        def replace(match: re.Match[str]) -> str:
            token = match.group(1)
            if token == "cwd":
                return cwd
            if token.startswith("env:"):
                env_name = token.split(":", 1)[1]
                env_value = os.environ.get(env_name)
                if env_value is None:
                    raise ConfigValidationError(
                        [ConfigError(path=path, message=f"Missing environment variable '{env_name}'")]
                    )
                return env_value
            if token in stack:
                raise ConfigValidationError(
                    [ConfigError(path=path, message=f"Interpolation cycle detected through '{token}'")]
                )
            reference = _get_value(root, token)
            if reference is None:
                raise ConfigValidationError(
                    [ConfigError(path=path, message=f"Unknown interpolation reference '{token}'")]
                )
            resolved_reference = resolve(reference, token, stack + (token,))
            if isinstance(resolved_reference, (dict, list)):
                raise ConfigValidationError(
                    [ConfigError(path=path, message=f"Interpolation reference '{token}' must resolve to a scalar")]
                )
            return str(resolved_reference)

        return PLACEHOLDER_PATTERN.sub(replace, value)

    return resolve(root_value, "", ())


def _apply_overrides(
    config: dict[str, Any],
    overrides: dict[str, Any],
    sources: dict[str, str],
) -> list[ConfigError]:
    errors: list[ConfigError] = []
    for dotted_path, value in overrides.items():
        if value is None:
            continue
        if not _path_exists_in_schema(dotted_path):
            errors.append(
                ConfigError(path=dotted_path, message="Unknown CLI override target")
            )
            continue
        _set_value(config, dotted_path, value)
        sources[dotted_path] = "override"
    return errors


def _normalize_paths(config: dict[str, Any], *, config_path: str | None) -> None:
    if config_path is None:
        return
    base_dir = os.path.dirname(os.path.abspath(config_path))
    for dotted_path in PATH_FIELDS:
        value = _get_value(config, dotted_path)
        if isinstance(value, str) and value and not os.path.isabs(value):
            _set_value(config, dotted_path, os.path.normpath(os.path.join(base_dir, value)))
    for dotted_path in PATH_LIST_FIELDS:
        value = _get_value(config, dotted_path)
        if isinstance(value, list):
            normalized = [
                os.path.normpath(os.path.join(base_dir, item))
                if isinstance(item, str) and item and not os.path.isabs(item)
                else item
                for item in value
            ]
            _set_value(config, dotted_path, normalized)


def _get_value(config: dict[str, Any], dotted_path: str) -> Any:
    current: Any = config
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_value(config: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    current = config
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _path_exists_in_schema(dotted_path: str) -> bool:
    current: Any = SCHEMA
    for part in dotted_path.split("."):
        if isinstance(current, list):
            current = current[0]
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True
