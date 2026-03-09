"""Wiring summary computation and formatting."""

from __future__ import annotations

from pathlib import Path

from cryowire.models import (
    ControlLine,
    CooldownMetadata,
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
            total_atten += comp.attenuation
            total_gain += comp.gain
            stage_components[stage].append(comp.summary_label)

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

def _metadata_markdown(metadata: CooldownMetadata | None) -> list[str]:
    """Generate metadata header lines for Markdown output."""
    if metadata is None:
        return []
    parts: list[str] = ["## Cooldown Info", ""]
    parts.append(f"| Key | Value |")
    parts.append("|---|---|")
    parts.append(f"| Cooldown ID | `{metadata.cooldown_id}` |")
    parts.append(f"| Date | {metadata.date} |")
    parts.append(f"| Cryo | {metadata.cryo} |")
    if metadata.operator:
        parts.append(f"| Operator | {metadata.operator} |")
    if metadata.purpose:
        parts.append(f"| Purpose | {metadata.purpose} |")
    if metadata.notes:
        parts.append(f"| Notes | {metadata.notes} |")
    parts.append("")
    return parts


def _metadata_html(metadata: CooldownMetadata | None) -> list[str]:
    """Generate metadata header for HTML output."""
    if metadata is None:
        return []
    rows = [
        f"<tr><td><b>Cooldown ID</b></td><td><code>{metadata.cooldown_id}</code></td></tr>",
        f"<tr><td><b>Date</b></td><td>{metadata.date}</td></tr>",
        f"<tr><td><b>Cryo</b></td><td>{metadata.cryo}</td></tr>",
    ]
    if metadata.operator:
        rows.append(f"<tr><td><b>Operator</b></td><td>{metadata.operator}</td></tr>")
    if metadata.purpose:
        rows.append(f"<tr><td><b>Purpose</b></td><td>{metadata.purpose}</td></tr>")
    if metadata.notes:
        rows.append(f"<tr><td><b>Notes</b></td><td>{metadata.notes}</td></tr>")
    return [
        "<h2>Cooldown Info</h2>",
        "<table border='1' cellpadding='4' cellspacing='0'>",
        *rows,
        "</table>",
        "",
    ]


def generate_markdown_table(
    control: WiringConfig,
    readout_send: WiringConfig,
    readout_return: WiringConfig,
    line_type: str = "all",
    metadata: CooldownMetadata | None = None,
    diagram: str | None = None,
) -> str:
    """Generate a Markdown summary with separate tables per section.

    Parameters
    ----------
    diagram
        Relative path to a diagram image (e.g. ``"wiring.svg"``).
        If provided, an ``![Wiring Diagram]`` reference is added.
    """
    groups = grouped_summaries(control, readout_send, readout_return, line_type)

    stage_headers = " | ".join(s.value for s in STAGE_ORDER)
    table_header = f"| Line ID | Qubit(s) | Atten (dB) | Gain (dB) | {stage_headers} |"
    n_cols = 4 + len(STAGE_ORDER)
    table_sep = "|" + "|".join(["---"] * n_cols) + "|"

    parts: list[str] = _metadata_markdown(metadata)

    if diagram is not None:
        parts.append("## Wiring Diagram")
        parts.append("")
        parts.append(f"![Wiring Diagram]({diagram})")
        parts.append("")

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
    metadata: CooldownMetadata | None = None,
) -> str:
    """Generate an HTML summary with separate tables per section."""
    groups = grouped_summaries(control, readout_send, readout_return, line_type)

    stage_headers = "".join(f"<th>{s.value}</th>" for s in STAGE_ORDER)
    table_header = (
        "<table border='1' cellpadding='4' cellspacing='0'>"
        f"<tr><th>Line ID</th><th>Qubit(s)</th>"
        f"<th>Atten (dB)</th><th>Gain (dB)</th>{stage_headers}</tr>\n"
    )
    parts: list[str] = _metadata_html(metadata)
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
    metadata: CooldownMetadata | None = None,
) -> None:
    """Print or export a wiring summary table.

    Formats: ``terminal`` (rich), ``html``, ``markdown``.
    """
    if fmt == "terminal":
        from rich.console import Console
        from rich.table import Table

        groups = grouped_summaries(control, readout_send, readout_return, line_type)
        console = Console()

        if metadata is not None:
            meta_table = Table(title="Cooldown Info", show_lines=True)
            meta_table.add_column("Key", style="bold")
            meta_table.add_column("Value")
            meta_table.add_row("Cooldown ID", metadata.cooldown_id)
            meta_table.add_row("Date", metadata.date)
            meta_table.add_row("Cryo", metadata.cryo)
            if metadata.operator:
                meta_table.add_row("Operator", metadata.operator)
            if metadata.purpose:
                meta_table.add_row("Purpose", metadata.purpose)
            if metadata.notes:
                meta_table.add_row("Notes", metadata.notes)
            console.print(meta_table)
            console.print()

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
        html = generate_html_table(control, readout_send, readout_return, line_type, metadata=metadata)
        if output:
            Path(output).write_text(html)
        else:
            print(html)

    elif fmt == "markdown":
        md = generate_markdown_table(control, readout_send, readout_return, line_type, metadata=metadata)
        if output:
            Path(output).write_text(md)
        else:
            print(md)
