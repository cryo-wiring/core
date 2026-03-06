"""JSON Schema validation for cryo-wiring configuration files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

_SCHEMA_DIR = Path(__file__).parent / "schemas"

_schema_cache: dict[str, dict[str, Any]] = {}


def _load_schema(name: str) -> dict[str, Any]:
    if name not in _schema_cache:
        path = _SCHEMA_DIR / name
        _schema_cache[name] = json.loads(path.read_text())
    return _schema_cache[name]


def validate_wiring(data: dict[str, Any]) -> None:
    """Validate wiring configuration data against the schema.

    Raises ``jsonschema.ValidationError`` on failure.
    """
    jsonschema.validate(data, _load_schema("wiring.schema.json"))


def validate_metadata(data: dict[str, Any]) -> None:
    """Validate cooldown metadata against the schema.

    Raises ``jsonschema.ValidationError`` on failure.
    """
    jsonschema.validate(data, _load_schema("metadata.schema.json"))


def validate_components(data: dict[str, Any]) -> None:
    """Validate component catalog data against the schema.

    Raises ``jsonschema.ValidationError`` on failure.
    """
    jsonschema.validate(data, _load_schema("components.schema.json"))


def validate_chip(data: dict[str, Any]) -> None:
    """Validate chip metadata against the schema.

    Raises ``jsonschema.ValidationError`` on failure.
    """
    jsonschema.validate(data, _load_schema("chip.schema.json"))


def validate_cooldown(data: dict[str, Any]) -> None:
    """Validate a resolved cooldown against the schema.

    Raises ``jsonschema.ValidationError`` on failure.
    """
    jsonschema.validate(data, _load_schema("cooldown.schema.json"))
