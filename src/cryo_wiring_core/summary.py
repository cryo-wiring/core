"""Wiring summary computation (presentation-agnostic)."""

from __future__ import annotations

from cryo_wiring_core.models import (
    Amplifier,
    Attenuator,
    ControlLine,
    Filter,
    Isolator,
    ReadoutLine,
    Stage,
    STAGE_ORDER,
    WiringConfig,
)

_SECTIONS: list[tuple[str, str]] = [
    ("Control", "control"),
    ("Readout Send", "readout_send"),
    ("Readout Return", "readout_return"),
]


def line_summary(line: ControlLine | ReadoutLine) -> dict:
    """Compute summary info for a single line."""
    is_control = isinstance(line, ControlLine)
    qubits = line.qubit if is_control else ", ".join(line.qubits)
    total_atten = 0.0
    total_gain = 0.0
    stage_components: dict[Stage, list[str]] = {s: [] for s in STAGE_ORDER}

    for stage, components in line.stages.items():
        for comp in components:
            if isinstance(comp, Attenuator):
                total_atten += comp.value_dB
                stage_components[stage].append(f"ATT {comp.value_dB:.0f}dB")
            elif isinstance(comp, Filter):
                ft = comp.filter_type or "filter"
                stage_components[stage].append(ft)
            elif isinstance(comp, Isolator):
                stage_components[stage].append("ISO")
            elif isinstance(comp, Amplifier):
                total_gain += comp.gain_dB
                at = comp.amplifier_type or "AMP"
                stage_components[stage].append(f"{at} +{comp.gain_dB:.0f}dB")

    return {
        "line_id": line.line_id,
        "qubits": qubits,
        "total_atten": total_atten,
        "total_gain": total_gain,
        "stage_components": stage_components,
    }


def grouped_summaries(
    control: WiringConfig,
    readout_send: WiringConfig,
    readout_return: WiringConfig,
    line_type: str = "all",
) -> list[tuple[str, list[dict]]]:
    """Return list of (section_label, summaries) with non-empty sections."""
    configs = {"control": control, "readout_send": readout_send, "readout_return": readout_return}
    groups: list[tuple[str, list[dict]]] = []
    for label, key in _SECTIONS:
        if line_type not in ("all", key):
            continue
        lines = configs[key].lines
        if not lines:
            continue
        groups.append((label, [line_summary(l) for l in lines]))
    return groups
