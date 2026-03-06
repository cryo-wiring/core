"""Wiring summary computation and formatting."""

from __future__ import annotations

from pathlib import Path

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


# -- Formatting (no extra deps) --

def generate_markdown_table(
    control: WiringConfig,
    readout_send: WiringConfig,
    readout_return: WiringConfig,
    line_type: str = "all",
) -> str:
    """Generate a Markdown summary with separate tables per section."""
    groups = grouped_summaries(control, readout_send, readout_return, line_type)

    stage_headers = " | ".join(s.value for s in STAGE_ORDER)
    table_header = f"| Line ID | Qubit(s) | Atten (dB) | Gain (dB) | {stage_headers} |"
    n_cols = 4 + len(STAGE_ORDER)
    table_sep = "|" + "|".join(["---"] * n_cols) + "|"

    parts: list[str] = []
    for label, summaries in groups:
        parts.append(f"### {label}")
        parts.append("")
        parts.append(table_header)
        parts.append(table_sep)
        for s in summaries:
            atten = f"{s['total_atten']:.0f}" if s["total_atten"] else "-"
            gain = f"{s['total_gain']:.0f}" if s["total_gain"] else "-"
            stage_cells = " | ".join(
                ", ".join(s["stage_components"][stage]) if s["stage_components"][stage] else "-"
                for stage in STAGE_ORDER
            )
            parts.append(f"| {s['line_id']} | {s['qubits']} | {atten} | {gain} | {stage_cells} |")
        parts.append("")

    return "\n".join(parts).rstrip()


def generate_html_table(
    control: WiringConfig,
    readout_send: WiringConfig,
    readout_return: WiringConfig,
    line_type: str = "all",
) -> str:
    """Generate an HTML summary with separate tables per section."""
    groups = grouped_summaries(control, readout_send, readout_return, line_type)

    stage_headers = "".join(f"<th>{s.value}</th>" for s in STAGE_ORDER)
    table_header = (
        "<table border='1' cellpadding='4' cellspacing='0'>"
        f"<tr><th>Line ID</th><th>Qubit(s)</th>"
        f"<th>Atten (dB)</th><th>Gain (dB)</th>{stage_headers}</tr>\n"
    )
    parts: list[str] = []
    for label, summaries in groups:
        parts.append(f"<h3>{label}</h3>")
        rows = []
        for s in summaries:
            atten = f"{s['total_atten']:.0f}" if s["total_atten"] else "-"
            gain = f"{s['total_gain']:.0f}" if s["total_gain"] else "-"
            stage_cells = ""
            for stage in STAGE_ORDER:
                comps = s["stage_components"][stage]
                stage_cells += f"<td>{'<br>'.join(comps) if comps else '-'}</td>"
            rows.append(
                f"<tr><td>{s['line_id']}</td><td>{s['qubits']}</td>"
                f"<td>{atten}</td><td>{gain}</td>"
                f"{stage_cells}</tr>"
            )
        parts.append(table_header + "\n".join(rows) + "\n</table>")
    return "\n".join(parts)


# -- Rich printing (requires `rich` extra) --

def print_summary(
    control: WiringConfig,
    readout_send: WiringConfig,
    readout_return: WiringConfig,
    line_type: str = "all",
    fmt: str = "terminal",
    output: str | Path | None = None,
) -> None:
    """Print or export a wiring summary table.

    Formats: ``terminal`` (rich), ``html``, ``markdown``.
    """
    if fmt == "terminal":
        from rich.console import Console
        from rich.table import Table

        groups = grouped_summaries(control, readout_send, readout_return, line_type)
        console = Console()
        for label, summaries in groups:
            table = Table(title=label, show_lines=True)
            table.add_column("Line ID", style="bold")
            table.add_column("Qubit(s)")
            table.add_column("Atten (dB)", justify="right")
            table.add_column("Gain (dB)", justify="right")
            for stage in STAGE_ORDER:
                table.add_column(stage.value, justify="center")

            for s in summaries:
                row = [
                    s["line_id"],
                    s["qubits"],
                    f"{s['total_atten']:.0f}" if s["total_atten"] else "-",
                    f"{s['total_gain']:.0f}" if s["total_gain"] else "-",
                ]
                for stage in STAGE_ORDER:
                    comps = s["stage_components"][stage]
                    row.append("\n".join(comps) if comps else "-")
                table.add_row(*row)
            console.print(table)
            console.print()

    elif fmt == "html":
        html = generate_html_table(control, readout_send, readout_return, line_type)
        if output:
            Path(output).write_text(html)
        else:
            print(html)

    elif fmt == "markdown":
        md = generate_markdown_table(control, readout_send, readout_return, line_type)
        if output:
            Path(output).write_text(md)
        else:
            print(md)
