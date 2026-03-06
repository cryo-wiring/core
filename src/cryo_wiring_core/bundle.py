"""Export cooldown data as a single resolved YAML file (cooldown.yaml)."""

from __future__ import annotations

from pathlib import Path

import yaml

from cryo_wiring_core.loader import load_chip, load_cooldown, load_yaml
from cryo_wiring_core.models import (
    ChipConfig,
    ControlLine,
    CooldownMetadata,
    ReadoutLine,
    Stage,
    STAGE_ORDER,
    WiringConfig,
)
from cryo_wiring_core.summary import grouped_summaries


def _serialize_component(comp: object) -> dict:
    """Serialize a component model to a dict with summary_label."""
    d = comp.model_dump()  # type: ignore[union-attr]
    d["summary_label"] = comp.summary_label  # type: ignore[union-attr]
    return d


def _serialize_line(line: ControlLine | ReadoutLine) -> dict:
    """Serialize a line to a resolved dict."""
    result: dict = {"line_id": line.line_id}
    if isinstance(line, ControlLine):
        result["qubit"] = line.qubit
    else:
        result["qubits"] = line.qubits
    stages: dict[str, list[dict]] = {}
    for stage in STAGE_ORDER:
        comps = line.stages.get(stage, [])
        stages[stage.value] = [_serialize_component(c) for c in comps]
    result["stages"] = stages
    return result


def _serialize_wiring(config: WiringConfig) -> dict:
    """Serialize a WiringConfig to a resolved dict."""
    return {"lines": [_serialize_line(line) for line in config.lines]}


def _serialize_summary(
    control: WiringConfig,
    readout_send: WiringConfig,
    readout_return: WiringConfig,
) -> dict:
    """Build pre-computed summary."""
    groups = grouped_summaries(control, readout_send, readout_return)
    sections = []
    for label, summaries in groups:
        lines = []
        for s in summaries:
            stage_components: dict[str, list[str]] = {}
            for stage in STAGE_ORDER:
                stage_components[stage.value] = s["stage_components"][stage]
            lines.append({
                "line_id": s["line_id"],
                "qubits": s["qubits"],
                "total_atten": s["total_atten"],
                "total_gain": s["total_gain"],
                "stage_components": stage_components,
            })
        sections.append({"label": label, "lines": lines})
    return {"sections": sections}


def export_cooldown(
    cooldown_dir: str | Path,
    components_path: Path | None = None,
) -> dict:
    """Export a cooldown directory as a single resolved dict.

    Parameters
    ----------
    cooldown_dir
        Path to the cooldown directory containing metadata.yaml, control.yaml, etc.
    components_path
        Path to components.yaml. Falls back to the bundled default.

    Returns
    -------
    dict
        Fully resolved cooldown conforming to the cooldown schema.
    """
    d = Path(cooldown_dir)
    metadata, control, readout_send, readout_return = load_cooldown(d, components_path)

    chip: ChipConfig | None = None
    for cp in [d / "chip.yaml", d.parent / "chip.yaml"]:
        if cp.exists():
            chip = load_chip(cp)
            break

    result: dict = {
        "metadata": metadata.model_dump(),
        "chip": chip.model_dump() if chip else None,
        "control": _serialize_wiring(control),
        "readout_send": _serialize_wiring(readout_send),
        "readout_return": _serialize_wiring(readout_return),
        "summary": _serialize_summary(control, readout_send, readout_return),
    }
    return result


def write_cooldown(
    cooldown_dir: str | Path,
    output: str | Path | None = None,
    components_path: Path | None = None,
) -> Path:
    """Export a cooldown directory to a single resolved YAML file.

    Parameters
    ----------
    cooldown_dir
        Path to the cooldown directory.
    output
        Output file path. Defaults to ``cooldown_dir / "cooldown.yaml"``.
    components_path
        Path to components.yaml.

    Returns
    -------
    Path
        Path to the written file.
    """
    data = export_cooldown(cooldown_dir, components_path)
    out = Path(output) if output else Path(cooldown_dir) / "cooldown.yaml"
    out.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    )
    return out
