"""YAML loading and module expansion for wiring configurations."""

from __future__ import annotations

import copy
import importlib.resources
from pathlib import Path

import yaml

from cryo_wiring_core.models import ChipConfig, CooldownMetadata, WiringConfig


def bundled_templates_dir() -> Path:
    """Return the path to the bundled templates directory."""
    return Path(str(importlib.resources.files("cryo_wiring_core") / "templates"))


def templates_dir() -> Path:
    """Return the path to the bundled templates directory.

    .. deprecated::
        Use :func:`bundled_templates_dir` or :func:`resolve_templates_dir`
        for explicit control.
    """
    return bundled_templates_dir()


def resolve_templates_dir(template_path: Path | None = None) -> Path:
    """Return *template_path* if provided, otherwise the bundled templates."""
    if template_path is not None and template_path.is_dir():
        return template_path
    return bundled_templates_dir()


def default_components_path() -> Path:
    """Return the path to the bundled components.yaml."""
    return templates_dir() / "components.yaml"


def load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_components(path: Path) -> dict:
    """Load the shared component catalog from a YAML file."""
    if not path.exists():
        return {}
    return load_yaml(path)


def _resolve_component(comp: str | dict, catalog: dict) -> dict:
    """Resolve a component entry: string key -> catalog lookup, dict -> as-is."""
    if isinstance(comp, str):
        if comp not in catalog:
            raise ValueError(f"Unknown component key '{comp}' in components.yaml")
        return copy.deepcopy(catalog[comp])
    return comp


def _resolve_components_in_stages(stages: dict, catalog: dict) -> dict:
    """Resolve component references in a stages dict, returning a new dict."""
    resolved: dict = {}
    for stage_name, components in stages.items():
        resolved[stage_name] = [
            _resolve_component(c, catalog) for c in (components or [])
        ]
    return resolved


def expand_modules(data: dict, catalog: dict | None = None) -> dict:
    """Expand module-format YAML into flat format.

    If *data* has no ``modules`` key the dict is returned unchanged
    (backward-compatible with the flat format).

    Component entries that are plain strings are resolved against the
    provided component *catalog*.
    """
    if catalog is None:
        catalog = {}

    modules = data.get("modules")
    if modules is None:
        return data

    expanded_lines: list[dict] = []
    for line in data.get("lines", []):
        module_name = line.get("module")
        if module_name is None:
            # Already flat – keep as-is
            expanded_lines.append(line)
            continue

        if module_name not in modules:
            raise ValueError(f"Unknown module '{module_name}' in line '{line.get('line_id')}'")

        module_def = modules[module_name]
        stages = copy.deepcopy(module_def.get("stages", {}))

        # Resolve component key references in module stages
        stages = _resolve_components_in_stages(stages, catalog)

        # --- apply stage-level add/remove ---
        stages_patch = line.get("stages", {})
        for stage_name, patch in stages_patch.items():
            if stage_name not in stages:
                stages[stage_name] = []
            if isinstance(patch, dict):
                # patch with add/remove
                for rm in patch.get("remove", []):
                    rm_resolved = _resolve_component(rm, catalog) if isinstance(rm, str) else rm
                    rm_model = rm_resolved.get("model", rm_resolved) if isinstance(rm_resolved, dict) else rm_resolved
                    stages[stage_name] = [
                        c for c in stages[stage_name]
                        if c.get("model") != rm_model
                    ]
                for add_comp in patch.get("add", []):
                    stages[stage_name].append(_resolve_component(add_comp, catalog))
            elif isinstance(patch, list):
                # direct replacement
                stages[stage_name] = [_resolve_component(c, catalog) for c in patch]

        # Build the flat line dict
        flat_line: dict = {}
        for key, value in line.items():
            if key not in ("module", "stages"):
                flat_line[key] = value
        flat_line["stages"] = stages

        expanded_lines.append(flat_line)

    return {"lines": expanded_lines}


def load_cooldown(
    cooldown_dir: str | Path,
    components_path: Path | None = None,
) -> tuple[CooldownMetadata, WiringConfig, WiringConfig, WiringConfig]:
    """Load a cooldown directory.

    Returns (metadata, control_config, readout_send_config, readout_return_config).

    Backward compatibility: if ``readout_send.yaml`` does not exist, the old
    ``readout_return.yaml`` is treated as the readout_send (input) path and readout_return
    (output) is returned as an empty config.
    """
    d = Path(cooldown_dir)
    catalog = load_components(components_path or default_components_path())

    metadata = CooldownMetadata.model_validate(load_yaml(d / "metadata.yaml"))
    control = WiringConfig.from_raw(expand_modules(load_yaml(d / "control.yaml"), catalog))

    readout_send_path = d / "readout_send.yaml"
    readout_return_path = d / "readout_return.yaml"

    if readout_send_path.exists():
        readout_send = WiringConfig.from_raw(expand_modules(load_yaml(readout_send_path), catalog))
        if readout_return_path.exists():
            readout_return = WiringConfig.from_raw(expand_modules(load_yaml(readout_return_path), catalog))
        else:
            readout_return = WiringConfig(lines=[])
    else:
        # Backward compat: old readout_return.yaml is the readout_send (input) path
        readout_send = WiringConfig.from_raw(expand_modules(load_yaml(readout_return_path), catalog))
        readout_return = WiringConfig(lines=[])

    return metadata, control, readout_send, readout_return


def load_chip(path: Path) -> ChipConfig:
    """Load a chip.yaml file and return the ChipConfig."""
    data = load_yaml(path)
    return ChipConfig.model_validate(data)
