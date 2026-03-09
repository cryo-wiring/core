"""Load and resolve `.cryo-wiring.yaml` project configuration."""

from __future__ import annotations

from pathlib import Path

import yaml


CONFIG_FILENAME = ".cryo-wiring.yaml"


def find_config(start: Path | None = None) -> Path | None:
    """Walk up from *start* (default: cwd) looking for `.cryo-wiring.yaml`.

    Returns the config file path, or ``None`` if not found.
    """
    current = (start or Path.cwd()).resolve()
    for parent in (current, *current.parents):
        candidate = parent / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Path) -> dict:
    """Load a `.cryo-wiring.yaml` file and return its contents."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def resolve_template_path(
    explicit: Path | None = None,
    search_from: Path | None = None,
) -> Path | None:
    """Determine the template directory to use.

    Priority:
    1. *explicit* — passed via CLI ``--template-path`` or API parameter.
    2. ``template_path`` in the nearest `.cryo-wiring.yaml`.
    3. ``None`` — caller falls back to bundled templates.

    Relative paths in the config are resolved relative to the config file's
    directory.
    """
    if explicit is not None:
        p = Path(explicit)
        if p.is_dir():
            return p
        return None

    config_path = find_config(search_from)
    if config_path is None:
        return None

    cfg = load_config(config_path)
    raw = cfg.get("template_path")
    if raw is None:
        return None

    resolved = (config_path.parent / raw).resolve()
    if resolved.is_dir():
        return resolved
    return None
